#!/usr/bin/env python3
"""Collect an unsigned, fail-closed claim-honesty machine-evidence draft.

The collector performs credential-free GET requests against exactly six pinned
public surfaces.  It records the HTTP status and SHA-256 of the exact response
bytes, then scans only text that is visibly present in the returned HTML body.
It does not execute JavaScript.  A client-rendered shell therefore remains a
coverage blocker instead of being reported as a clean page.

This document is deliberately not acceptance evidence: it is unsigned, always
keeps the gate OPEN, contains no approval records, and cannot promote any
customer-production decision.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


REPORT_SCHEMA_VERSION = "cas_harness_claim_honesty_machine_report.v2"
DRAFT_SCHEMA_VERSION = "cas_harness_claim_honesty_machine_evidence_draft.v2"
MACHINE_SUBJECT_SCHEMA_VERSION = "cas_harness_claim_honesty_machine_subject.v1"
RULESET_VERSION = "cas_harness_claim_honesty_rules.v1"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 1_000_000
MAX_RESPONSE_BYTES = 2_000_000
MIN_VISIBLE_TEXT_CHARACTERS = 32
MIN_VISIBLE_WORDS = 5

PINNED_SURFACES: tuple[tuple[str, str], ...] = (
    ("product_app", "https://atlas.noeticcompass.com"),
    ("audit_console", "https://atlas.noeticcompass.com/audit-console"),
    ("landing", "https://cascompass.ai"),
    ("legal", "https://cascompass.ai/legal"),
    ("privacy", "https://cascompass.ai/privacy"),
    ("terms", "https://cascompass.ai/terms"),
)
PINNED_SURFACE_MAP = dict(PINNED_SURFACES)

SUPPRESSED_ELEMENTS = frozenset(
    {"canvas", "head", "noscript", "script", "style", "svg", "template"}
)
APPLICATION_MOUNT_IDS = frozenset(
    {"__next", "app", "app-root", "application", "root"}
)
PRERENDER_SCHEMA_VERSION = "cas_claim_surface.v1"
ROUTE_HEADING_PATTERNS: dict[str, re.Pattern[str]] = {
    "product_app": re.compile(
        r"\b(?:atlas|audit\s+cockpit|model\s+audit|neural\s+network\s+cockpit)\b",
        re.IGNORECASE,
    ),
    "audit_console": re.compile(
        r"\b(?:audit\s+console|run\s+(?:an?\s+)?audit|model\s+audit)\b",
        re.IGNORECASE,
    ),
    "landing": re.compile(
        r"\b(?:CAS|Noetic\s+Compass|measure\s+how\s+AI\s+thinks?)\b",
        re.IGNORECASE,
    ),
    "legal": re.compile(r"\blegal\b", re.IGNORECASE),
    "privacy": re.compile(r"\bprivacy\b", re.IGNORECASE),
    "terms": re.compile(r"\bterms\b", re.IGNORECASE),
}

NEGATION_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|is\s+not|are\s+not|not|no|never|without)\b",
    re.IGNORECASE,
)
CLAUSE_BREAK_RE = re.compile(r"(?:[.!?;]|\b(?:but|however|although)\b)", re.IGNORECASE)


@dataclass(frozen=True)
class ClaimRule:
    category: str
    rule_id: str
    pattern: re.Pattern[str]


def _rule(category: str, rule_id: str, pattern: str) -> ClaimRule:
    return ClaimRule(category, rule_id, re.compile(pattern, re.IGNORECASE))


CLAIM_RULES: tuple[ClaimRule, ...] = (
    _rule(
        "misleading_claim",
        "customer_production_ready",
        r"\b(?:customer[- ]production|production)[- ](?:ready|approved|certified)\b",
    ),
    _rule(
        "misleading_claim",
        "automatic_product_promotion",
        r"\bautomatic(?:ally)?\b.{0,48}\b(?:customer[- ]production|product)\b.{0,24}\b(?:accept|approval|ready)\b",
    ),
    _rule(
        "misleading_claim",
        "worm_verdict_promotion",
        r"\b(?:WORM|object\s+lock|retention)\b.{0,64}\b(?:upgrade|promote|turns?)\b.{0,48}\b(?:verdict|accept|approval)\b",
    ),
    _rule(
        "misleading_claim",
        "human_review_not_required",
        r"\b(?:no|without)\s+human\s+review(?:\s+is)?\s+required\b",
    ),
    _rule(
        "misleading_claim",
        "anthropomorphic_measurement",
        r"\bmeasure(?:s|d|ment|ing)?\s+(?:exactly\s+)?how\s+(?:an?\s+)?AI\s+thinks?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "soc2_claim",
        r"\bSOC\s*2(?:\s+Type\s*(?:I{1,2}|[12]))?(?:\s+(?:certified|compliant|attested))?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "hipaa_claim",
        r"\bHIPAA(?:[- ](?:certified|compliant))?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "gdpr_claim",
        r"\bGDPR(?:[- ](?:certified|compliant))?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "iso27001_claim",
        r"\bISO\s*27001(?:[- ](?:certified|compliant))?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "fedramp_claim",
        r"\bFedRAMP(?:\s+(?:authorized|certified|compliant))?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "pci_dss_claim",
        r"\bPCI[- ]?DSS(?:[- ](?:certified|compliant))?\b",
    ),
    _rule(
        "unsupported_compliance_claim",
        "regulatory_approval",
        r"\bregulatory\s+(?:approval|approved|certification|certified)\b",
    ),
    _rule(
        "unsupported_universality_claim",
        "absolute_accuracy",
        r"\b100\s*%\s+(?:accurate|correct|reliable|safe|secure)\b",
    ),
    _rule(
        "unsupported_universality_claim",
        "always_never_performance",
        r"\b(?:always|never)\s+(?:works?|fails?|detects?|catches?|correct|accurate|safe|secure|reliable)\b",
    ),
    _rule(
        "unsupported_universality_claim",
        "all_models",
        r"\b(?:all|every)\s+(?:AI\s+)?models?\b",
    ),
    _rule(
        "unsupported_universality_claim",
        "guarantee",
        r"\bguarantee(?:d|s)?\b",
    ),
    _rule(
        "unsupported_universality_claim",
        "eliminates_risk",
        r"\beliminate(?:s|d)?\s+(?:all\s+)?(?:risk|bias|hallucinations?)\b",
    ),
    _rule(
        "unsupported_ip_claim",
        "patent_pending",
        r"\bpatents?\s+pending\b",
    ),
    _rule(
        "unsupported_ip_claim",
        "patented",
        r"\bpatented\b",
    ),
)

STATUS_TERMS_PATTERN = (
    r"FLAG[_ -]FOR[_ -]HUMAN[_ -]REVIEW|NOT[_ -]LICENSED|"
    r"ACCEPT(?:ED)?|LICENSED|OPEN|PRESENT|UNAVAILABLE|"
    r"PASS(?:ED)?|READY|APPROVED|CERTIFIED"
)
STATUS_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        rf"\b(?:claim|customer[- ]production|evidence|verdict|license)"
        rf"(?:\s+(?:status|decision|gate))?\s*"
        rf"(?:(?::|=|—|-)|\bis\b)?\s*"
        rf"(?P<term>{STATUS_TERMS_PATTERN})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<term>{STATUS_TERMS_PATTERN})\b\s+"
        rf"(?:claim|customer[- ]production|evidence|verdict|license)"
        rf"(?:\s+(?:status|decision|gate))?\b",
        re.IGNORECASE,
    ),
)
EXACT_STATUS_TERMS = frozenset(
    {
        "ACCEPT",
        "FLAG_FOR_HUMAN_REVIEW",
        "LICENSED",
        "NOT LICENSED",
        "OPEN",
        "present",
        "unavailable",
    }
)


class CollectorError(RuntimeError):
    """The collector configuration is unsafe or invalid."""


class ResponseTooLarge(RuntimeError):
    """A response cannot be hashed exactly within the configured bound."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass
class SurfaceFetch:
    kind: str
    url: str
    verified_at_utc: str
    http_status: int | None = None
    final_url_matches_requested: bool | None = None
    content_type: str | None = None
    declared_content_length: int | None = None
    byte_length: int | None = None
    raw_content_sha256: str | None = None
    raw: bytes | None = field(default=None, repr=False)
    errors: list[str] = field(default_factory=list)


@dataclass
class SurfaceAnalysis:
    fetch: SurfaceFetch
    coverage_established: bool
    visibility_basis: str
    visible_text_sha256: str | None
    visible_text_characters: int
    visible_word_count: int
    client_rendered_shell_detected: bool
    prerendered_application_mount_detected: bool
    prerender_contract_matches_requested_route: bool
    route_identity_established: bool
    errors: list[str]
    visible_text: str = field(default="", repr=False)

    def public_record(self) -> dict[str, Any]:
        return {
            "kind": self.fetch.kind,
            "url": self.fetch.url,
            "http_status": self.fetch.http_status,
            "final_url_matches_requested": self.fetch.final_url_matches_requested,
            "content_type": self.fetch.content_type,
            "declared_content_length": self.fetch.declared_content_length,
            "byte_length": self.fetch.byte_length,
            "raw_content_sha256": self.fetch.raw_content_sha256,
            "verified_at_utc": self.fetch.verified_at_utc,
            "coverage_established": self.coverage_established,
            "visibility_basis": self.visibility_basis,
            "visible_text_sha256": self.visible_text_sha256,
            "visible_text_characters": self.visible_text_characters,
            "visible_word_count": self.visible_word_count,
            "client_rendered_shell_detected": self.client_rendered_shell_detected,
            "prerendered_application_mount_detected": self.prerendered_application_mount_detected,
            "prerender_contract_matches_requested_route": self.prerender_contract_matches_requested_route,
            "route_identity_established": self.route_identity_established,
            "errors": list(self.errors),
        }

    def machine_subject_record(self) -> dict[str, Any]:
        """Return the exact secret-free facts covered by the machine subject.

        The raw response bytes are intentionally not copied into an acceptance
        artifact.  Their exact SHA-256 and byte length are, together with the
        visible-text hash, route/coverage facts, and a digest of every error.
        """

        errors = sorted(set(self.errors))
        return {
            "kind": self.fetch.kind,
            "url": self.fetch.url,
            "http_status": self.fetch.http_status,
            "final_url_matches_requested": self.fetch.final_url_matches_requested,
            "content_type": self.fetch.content_type,
            "byte_length": self.fetch.byte_length,
            "content_sha256": self.fetch.raw_content_sha256,
            "verified_at_utc": self.fetch.verified_at_utc,
            "coverage_established": self.coverage_established,
            "visibility_basis": self.visibility_basis,
            "visible_text_sha256": self.visible_text_sha256,
            "visible_text_characters": self.visible_text_characters,
            "visible_word_count": self.visible_word_count,
            "client_rendered_shell_detected": self.client_rendered_shell_detected,
            "prerendered_application_mount_detected": (
                self.prerendered_application_mount_detected
            ),
            "prerender_contract_matches_requested_route": (
                self.prerender_contract_matches_requested_route
            ),
            "route_identity_established": self.route_identity_established,
            "error_count": len(errors),
            "errors_sha256": hashlib.sha256(
                _canonical_json_bytes(errors)
            ).hexdigest(),
        }


class _VisibleBodyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, bool, bool, bool]] = []
        self.body_seen = False
        self.script_seen = False
        self.application_mount_seen = False
        self.application_mount_contracts: list[tuple[str, str]] = []
        self.text_parts: list[str] = []
        self.primary_heading_parts: list[str] = []
        self.prerender_contract_text_parts: list[str] = []
        self.prerender_contract_heading_parts: list[str] = []

    @staticmethod
    def _attribute_map(attrs: Sequence[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): (value or "") for key, value in attrs}

    @staticmethod
    def _explicitly_hidden(attributes: Mapping[str, str]) -> bool:
        if "hidden" in attributes:
            return True
        if attributes.get("aria-hidden", "").strip().lower() == "true":
            return True
        style = re.sub(r"\s+", "", attributes.get("style", "").lower())
        return "display:none" in style or "visibility:hidden" in style

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        normalized_tag = tag.lower()
        attributes = self._attribute_map(attrs)
        parent_hidden = bool(self._stack and self._stack[-1][1])
        parent_inside_application_mount = bool(
            self._stack and self._stack[-1][2]
        )
        parent_inside_prerender_contract_mount = bool(
            self._stack and self._stack[-1][3]
        )
        hidden = (
            parent_hidden
            or normalized_tag in SUPPRESSED_ELEMENTS
            or self._explicitly_hidden(attributes)
        )
        element_id = attributes.get("id", "").strip().lower()
        is_application_mount = (
            element_id in APPLICATION_MOUNT_IDS or "data-reactroot" in attributes
        )
        inside_application_mount = (
            parent_inside_application_mount or is_application_mount
        )
        route = attributes.get("data-cas-prerendered-route", "").strip()
        schema = attributes.get("data-cas-prerender-schema", "").strip()
        is_prerender_contract_mount = is_application_mount and bool(route or schema)
        inside_prerender_contract_mount = (
            parent_inside_prerender_contract_mount or is_prerender_contract_mount
        )
        self._stack.append(
            (
                normalized_tag,
                hidden,
                inside_application_mount,
                inside_prerender_contract_mount,
            )
        )
        if normalized_tag == "body":
            self.body_seen = True
        if normalized_tag == "script":
            self.script_seen = True
        if is_application_mount:
            self.application_mount_seen = True
            if route or schema:
                self.application_mount_contracts.append((route, schema))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == normalized_tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        inside_body = any(
            tag == "body"
            for tag, _hidden, _mount, _contract_mount in self._stack
        )
        hidden = bool(self._stack and self._stack[-1][1])
        if inside_body and not hidden and data.strip():
            self.text_parts.append(data)
            inside_prerender_contract_mount = bool(
                self._stack and self._stack[-1][3]
            )
            if inside_prerender_contract_mount:
                self.prerender_contract_text_parts.append(data)
            if any(
                tag == "h1"
                for tag, _hidden, _mount, _contract_mount in self._stack
            ):
                self.primary_heading_parts.append(data)
                if inside_prerender_contract_mount:
                    self.prerender_contract_heading_parts.append(data)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalized_origin(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None
    port_text = f":{port}" if port is not None else ""
    return f"https://{parsed.hostname.lower()}{port_text}"


def validate_surface_url(kind: str, url: str) -> str:
    expected = PINNED_SURFACE_MAP.get(kind)
    if expected is None:
        raise CollectorError(f"unknown surface kind: {kind}")
    if _normalized_origin(url) is None:
        raise CollectorError(
            "surface URL must be credential-free HTTPS without query or fragment"
        )
    if url != expected:
        raise CollectorError(f"surface URL is not the pinned {kind} route")
    return url


def _parse_content_length(headers: Any) -> tuple[int | None, bool]:
    value = headers.get("Content-Length") if headers is not None else None
    if value is None:
        return None, True
    try:
        parsed = int(str(value), 10)
    except (TypeError, ValueError):
        return None, False
    return (parsed, parsed >= 0)


def _read_response_bounded(response: Any, maximum: int) -> bytes:
    raw = response.read(maximum + 1)
    if not isinstance(raw, bytes):
        raise CollectorError("response body was not bytes")
    if len(raw) > maximum:
        raise ResponseTooLarge("response exceeds byte limit")
    return raw


def fetch_surface(
    kind: str,
    url: str,
    *,
    opener: Any | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    clock: Callable[[], datetime] = _utc_now,
) -> SurfaceFetch:
    validate_surface_url(kind, url)
    if not (0 < timeout_seconds <= MAX_TIMEOUT_SECONDS):
        raise CollectorError("timeout must be greater than zero and at most 30 seconds")
    if not (0 < max_response_bytes <= MAX_RESPONSE_BYTES):
        raise CollectorError("response bound must be between 1 and 2000000 bytes")

    result = SurfaceFetch(kind=kind, url=url, verified_at_utc="")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Encoding": "identity",
            "User-Agent": "cas-claim-honesty-machine-collector/1",
        },
        method="GET",
    )
    active_opener = opener or urllib.request.build_opener(_NoRedirect)
    response: Any | None = None
    try:
        try:
            response = active_opener.open(request, timeout=timeout_seconds)
        except urllib.error.HTTPError as exc:
            response = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            result.errors.append(f"network_error:{type(exc).__name__}")
            return result

        status_value = getattr(response, "status", getattr(response, "code", None))
        try:
            result.http_status = int(status_value)
        except (TypeError, ValueError):
            result.errors.append("http_status_unavailable")

        final_url = response.geturl() if hasattr(response, "geturl") else None
        result.final_url_matches_requested = final_url == url
        if result.final_url_matches_requested is not True:
            result.errors.append("redirect_or_final_url_mismatch")

        headers = getattr(response, "headers", None)
        content_type = headers.get("Content-Type") if headers is not None else None
        result.content_type = str(content_type).strip() if content_type else None
        declared_length, valid_length = _parse_content_length(headers)
        result.declared_content_length = declared_length
        if not valid_length:
            result.errors.append("invalid_content_length")
        if declared_length is not None and declared_length > max_response_bytes:
            result.errors.append("response_too_large")
        else:
            try:
                raw = _read_response_bounded(response, max_response_bytes)
            except ResponseTooLarge:
                result.errors.append("response_too_large")
            except CollectorError:
                result.errors.append("response_body_invalid")
            except (TimeoutError, OSError) as exc:
                result.errors.append(f"body_read_error:{type(exc).__name__}")
            else:
                result.raw = raw
                result.byte_length = len(raw)
                result.raw_content_sha256 = hashlib.sha256(raw).hexdigest()

        if result.http_status is not None and 300 <= result.http_status <= 399:
            result.errors.append("redirect_response_rejected")
        if result.http_status != 200:
            result.errors.append("http_status_not_200")
        return result
    finally:
        result.verified_at_utc = _format_utc(clock())
        if response is not None and hasattr(response, "close"):
            response.close()


def _decode_html(raw: bytes, content_type: str | None) -> tuple[str | None, str | None]:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type not in {"text/html", "application/xhtml+xml"}:
        return None, "unsupported_content_type"
    charset_declarations = list(
        re.finditer(
            r"(?:^|;)\s*charset\s*=",
            content_type or "",
            re.IGNORECASE,
        )
    )
    charset_matches = list(
        re.finditer(
            r"(?:^|;)\s*charset\s*=\s*[\"']?([^;\"']+)",
            content_type or "",
            re.IGNORECASE,
        )
    )
    if len(charset_declarations) != 1 or len(charset_matches) != 1:
        return None, "unsupported_charset"
    charset = charset_matches[0].group(1).strip().lower()
    if charset not in {"utf-8", "utf8"}:
        return None, "unsupported_charset"
    try:
        return raw.decode("utf-8-sig"), None
    except UnicodeDecodeError:
        return None, "invalid_utf8"


def analyze_surface(fetch: SurfaceFetch) -> SurfaceAnalysis:
    errors = list(fetch.errors)
    if fetch.final_url_matches_requested is not True:
        errors.append("exact_route_identity_not_verified")
    if fetch.raw is not None:
        if fetch.byte_length != len(fetch.raw):
            errors.append("raw_byte_length_mismatch")
        actual_raw_hash = hashlib.sha256(fetch.raw).hexdigest()
        if fetch.raw_content_sha256 != actual_raw_hash:
            errors.append("raw_content_sha256_mismatch")
    if fetch.http_status != 200 or fetch.raw is None:
        return SurfaceAnalysis(
            fetch=fetch,
            coverage_established=False,
            visibility_basis="unavailable",
            visible_text_sha256=None,
            visible_text_characters=0,
            visible_word_count=0,
            client_rendered_shell_detected=False,
            prerendered_application_mount_detected=False,
            prerender_contract_matches_requested_route=False,
            route_identity_established=False,
            errors=list(dict.fromkeys(errors)),
        )

    document, decode_error = _decode_html(fetch.raw, fetch.content_type)
    if decode_error is not None or document is None:
        errors.append(decode_error or "html_decode_failed")
        return SurfaceAnalysis(
            fetch=fetch,
            coverage_established=False,
            visibility_basis="unavailable",
            visible_text_sha256=None,
            visible_text_characters=0,
            visible_word_count=0,
            client_rendered_shell_detected=False,
            prerendered_application_mount_detected=False,
            prerender_contract_matches_requested_route=False,
            route_identity_established=False,
            errors=list(dict.fromkeys(errors)),
        )

    parser = _VisibleBodyParser()
    try:
        parser.feed(document)
        parser.close()
    except (ValueError, AssertionError):
        errors.append("html_parse_failed")

    visible_text = " ".join(" ".join(parser.text_parts).split())
    visible_characters = len(visible_text)
    visible_words = len(re.findall(r"\b\w+\b", visible_text, re.UNICODE))
    visible_hash = (
        hashlib.sha256(visible_text.encode("utf-8")).hexdigest()
        if visible_text
        else None
    )
    visible_headings = " ".join(" ".join(parser.primary_heading_parts).split())
    route_identity = (
        ROUTE_HEADING_PATTERNS[fetch.kind].search(visible_headings) is not None
    )
    requested_path = urllib.parse.urlsplit(fetch.url).path or "/"
    prerender_contract_matches_requested_route = (
        parser.application_mount_contracts
        == [(requested_path, PRERENDER_SCHEMA_VERSION)]
    )
    application_mount_text = " ".join(
        " ".join(parser.prerender_contract_text_parts).split()
    )
    application_mount_characters = len(application_mount_text)
    application_mount_words = len(
        re.findall(r"\b\w+\b", application_mount_text, re.UNICODE)
    )
    application_mount_headings = " ".join(
        " ".join(parser.prerender_contract_heading_parts).split()
    )
    application_mount_route_identity = (
        ROUTE_HEADING_PATTERNS[fetch.kind].search(application_mount_headings)
        is not None
    )
    prerendered_application_mount = (
        parser.application_mount_seen
        and prerender_contract_matches_requested_route
        and application_mount_characters >= MIN_VISIBLE_TEXT_CHARACTERS
        and application_mount_words >= MIN_VISIBLE_WORDS
        and application_mount_route_identity
    )
    client_shell = (
        parser.script_seen
        and parser.application_mount_seen
        and not prerendered_application_mount
    )
    if not parser.body_seen:
        errors.append("html_body_missing")
    if (
        visible_characters < MIN_VISIBLE_TEXT_CHARACTERS
        or visible_words < MIN_VISIBLE_WORDS
    ):
        errors.append("insufficient_route_visible_text")
    if client_shell:
        errors.append("client_rendered_route_coverage_not_established")
    if not route_identity:
        errors.append("requested_route_identity_not_established")

    errors = list(dict.fromkeys(errors))
    return SurfaceAnalysis(
        fetch=fetch,
        coverage_established=not errors,
        visibility_basis=(
            "prerendered_same_route_application_mount"
            if prerendered_application_mount
            else "static_same_route_html"
        ),
        visible_text_sha256=visible_hash,
        visible_text_characters=visible_characters,
        visible_word_count=visible_words,
        client_rendered_shell_detected=client_shell,
        prerendered_application_mount_detected=prerendered_application_mount,
        prerender_contract_matches_requested_route=prerender_contract_matches_requested_route,
        route_identity_established=route_identity,
        errors=errors,
        visible_text=visible_text,
    )


def _is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 96) : start]
    clause_breaks = list(CLAUSE_BREAK_RE.finditer(prefix))
    clause = prefix[clause_breaks[-1].end() :] if clause_breaks else prefix
    return NEGATION_RE.search(clause) is not None


def _finding(
    *,
    category: str,
    rule_id: str,
    kind: str,
    matched_text: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    return {
        "category": category,
        "rule_id": rule_id,
        "surface_kind": kind,
        "match_start": start,
        "match_end": end,
        "match_sha256": hashlib.sha256(matched_text.encode("utf-8")).hexdigest(),
    }


def scan_visible_text(analyses: Iterable[SurfaceAnalysis]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int, int]] = set()
    for analysis in analyses:
        if not analysis.coverage_established:
            continue
        text = analysis.visible_text
        for rule in CLAIM_RULES:
            for match in rule.pattern.finditer(text):
                if _is_negated(text, match.start()):
                    continue
                if rule.rule_id == "worm_verdict_promotion" and re.search(
                    r"\b(?:does\s+not|do\s+not|never|not)\s+"
                    r"(?:upgrade|promote|turns?)\b",
                    match.group(0),
                    re.IGNORECASE,
                ):
                    continue
                identity = (
                    analysis.fetch.kind,
                    rule.category,
                    rule.rule_id,
                    match.start(),
                    match.end(),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                findings.append(
                    _finding(
                        category=rule.category,
                        rule_id=rule.rule_id,
                        kind=analysis.fetch.kind,
                        matched_text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                    )
                )

        for context_pattern in STATUS_CONTEXT_PATTERNS:
            for match in context_pattern.finditer(text):
                term = match.group("term")
                if term in EXACT_STATUS_TERMS:
                    continue
                start, end = match.span("term")
                identity = (
                    analysis.fetch.kind,
                    "status_vocabulary",
                    "noncanonical_status_term",
                    start,
                    end,
                )
                if identity in seen:
                    continue
                seen.add(identity)
                findings.append(
                    _finding(
                        category="status_vocabulary",
                        rule_id="noncanonical_status_term",
                        kind=analysis.fetch.kind,
                        matched_text=term,
                        start=start,
                        end=end,
                    )
                )

    return sorted(
        findings,
        key=lambda item: (
            item["surface_kind"],
            item["match_start"],
            item["category"],
            item["rule_id"],
        ),
    )


def _collector_sha256() -> str:
    try:
        raw = Path(__file__).read_bytes()
    except OSError:
        return "unavailable"
    return hashlib.sha256(raw).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def machine_subject_sha256(subject: Mapping[str, Any]) -> str:
    """Hash the exact canonical machine subject embedded in later authority."""

    return hashlib.sha256(_canonical_json_bytes(subject)).hexdigest()


def collect_claim_honesty_report(
    *,
    fetcher: Callable[[str, str], SurfaceFetch] | None = None,
    clock: Callable[[], datetime] = _utc_now,
    opener: Any | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    if fetcher is None:
        active_opener = opener or urllib.request.build_opener(_NoRedirect)

        def fetcher(kind: str, url: str) -> SurfaceFetch:
            return fetch_surface(
                kind,
                url,
                opener=active_opener,
                timeout_seconds=timeout_seconds,
                max_response_bytes=max_response_bytes,
                clock=clock,
            )

    analyses: list[SurfaceAnalysis] = []
    for kind, url in PINNED_SURFACES:
        analyses.append(analyze_surface(fetcher(kind, url)))

    findings = scan_visible_text(analyses)
    coverage_complete = all(item.coverage_established for item in analyses)
    counts = {
        "misleading_claim_count": sum(
            item["category"] == "misleading_claim" for item in findings
        ),
        "unsupported_compliance_claim_count": sum(
            item["category"] == "unsupported_compliance_claim"
            for item in findings
        ),
        "unsupported_universality_claim_count": sum(
            item["category"] == "unsupported_universality_claim"
            for item in findings
        ),
        "unsupported_ip_claim_count": sum(
            item["category"] == "unsupported_ip_claim" for item in findings
        ),
        "status_vocabulary_exact": coverage_complete
        and not any(item["category"] == "status_vocabulary" for item in findings),
        "scanned_surface_count": len(analyses),
        "covered_surface_count": sum(
            item.coverage_established for item in analyses
        ),
    }
    machine_scan_passed = coverage_complete and not findings
    counts.update(
        {
            "finding_count": len(findings),
            "coverage_complete": coverage_complete,
            "machine_scan_passed": machine_scan_passed,
        }
    )
    blockers = [
        f"surface:{item.fetch.kind}:{error}"
        for item in analyses
        for error in item.errors
    ]
    if findings:
        blockers.append("deterministic_claim_findings_detected")
    blockers.append("unsigned_draft_requires_independent_human_review")

    generated_at = _format_utc(clock())
    scanner = {
        "ruleset_version": RULESET_VERSION,
        "collector_sha256": _collector_sha256(),
        "request_method": "GET",
        "redirects_allowed": False,
        "maximum_response_bytes": max_response_bytes,
        "javascript_executed": False,
    }
    machine_subject: dict[str, Any] = {
        "schema_version": MACHINE_SUBJECT_SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "scanner": scanner,
        "scanned_surfaces": [
            item.machine_subject_record() for item in analyses
        ],
        "scan": counts,
        "findings": findings,
    }
    subject_sha256 = machine_subject_sha256(machine_subject)
    draft_payload: dict[str, Any] = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "gate": "claim_honesty",
        "environment": "public-production",
        "gate_status": "OPEN",
        "draft_only": True,
        "authoritative": False,
        "eligible_for_acceptance": False,
        "generated_at_utc": generated_at,
        "machine_subject_schema_version": MACHINE_SUBJECT_SCHEMA_VERSION,
        "machine_subject_sha256": subject_sha256,
        "coverage_complete": coverage_complete,
        "machine_scan_passed": machine_scan_passed,
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "draft_payload": draft_payload,
        "machine_subject": machine_subject,
        "machine_subject_sha256": subject_sha256,
        "blockers": sorted(set(blockers)),
    }


def _write_report(report: Mapping[str, Any], output: Path | None, pretty: bool) -> None:
    indent = 2 if pretty else None
    separators = None if pretty else (",", ":")
    serialized = json.dumps(
        report,
        ensure_ascii=False,
        indent=indent,
        separators=separators,
        sort_keys=True,
    )
    if output is None:
        print(serialized)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="write the unsigned draft report to this path instead of stdout",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="pretty-print JSON (canonical compact JSON is the default)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="per-request timeout, greater than zero and at most 30",
    )
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=DEFAULT_MAX_RESPONSE_BYTES,
        help="per-response bound, greater than zero and at most 2000000",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = collect_claim_honesty_report(
            timeout_seconds=args.timeout_seconds,
            max_response_bytes=args.max_response_bytes,
        )
        _write_report(report, args.output, args.pretty)
    except (CollectorError, OSError) as exc:
        print(f"claim-honesty collector failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0 if report["draft_payload"]["machine_scan_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
