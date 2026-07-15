#!/usr/bin/env python3
"""Collect a secret-safe, verifier-compatible runtime/WORM evidence draft.

The collector binds one exact public Render deployment to fresh readiness and
real-model reads, then creates one unique hosted audit so the production API
writes and re-reads an Evidence Packet under S3 Object Lock.  It emits a
canonical gate document plus a hashed source receipt.  It never publishes the
acceptance authority document, edits the release manifest, or claims ACCEPT.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Direct ``python scripts/...`` execution adds only the scripts directory to
# ``sys.path``. Add the trusted application root before importing ``api``.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.acceptance_authority_contract import acceptance_authority_url
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityInvalid,
    canonicalize_acceptance_evidence,
)

try:
    from .object_lock_smoke_validation import (
        MAX_CLOCK_SKEW,
        ObjectLockReceiptError,
        validate_object_lock_receipt,
    )
except ImportError:
    try:
        from scripts.object_lock_smoke_validation import (
            MAX_CLOCK_SKEW,
            ObjectLockReceiptError,
            validate_object_lock_receipt,
        )
    except ImportError:  # Direct ``python scripts/...`` execution.
        from object_lock_smoke_validation import (
            MAX_CLOCK_SKEW,
            ObjectLockReceiptError,
            validate_object_lock_receipt,
        )


EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v2"
SAFE_ARTIFACT_SCHEMA_VERSION = "cas_runtime_worm_source_receipt.v2"
REPOSITORY = "LittleHenderson/noetic-compass"
ENVIRONMENT = "public-production"
PRODUCTION_API_ORIGIN = "https://cas-harness-customer-api.onrender.com"
PRODUCTION_SERVICE_ID = "srv-d9bijbjtqb8s73cn4n20"
PRODUCTION_SERVICE_NAME = "cas-harness-customer-api"
AUTHORITY_URI = acceptance_authority_url("runtime_worm")
RENDER_API_ORIGIN = "https://api.render.com"
MODEL_ID = "EleutherAI/pythia-160m"
REALMODE_VERDICT = "REAL_PYTHIA_WEIGHTS_LOADED"
AUDIT_MODE = "BALANCED"
API_TOKEN_ENV = "CAS_HARNESS_API_TOKEN"
RENDER_API_KEY_ENV = "RENDER_API_KEY"
MAX_RESPONSE_BYTES = 2_000_000
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
AUDIT_ID_RE = re.compile(r"^cas-audit-[0-9a-f]{16}$")
TRACE_ID_RE = re.compile(r"^cas-live-[0-9a-f]{16}-[0-9a-f]{12}$")


class RuntimeWormFailure(RuntimeError):
    """A named runtime/WORM collection invariant failed closed."""

    def __init__(self, gate: str, detail: str) -> None:
        self.gate = gate
        super().__init__(f"{gate}: {detail}")


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[..., HttpResult]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeWormFailure("json", "response contains a duplicate JSON key")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> Any:
    raise RuntimeWormFailure("json", f"response contains forbidden number {value}")


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _subject_digest(kind: str, value: str) -> str:
    return _digest_bytes(f"{kind}:{value}".encode("utf-8"))


def _semantic_strings(value: Any) -> Iterator[str]:
    """Yield decoded JSON string semantics, including mapping keys."""

    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _semantic_strings(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _semantic_strings(item)


def _semantic_contains_any(
    outputs: tuple[Mapping[str, Any], ...], raw_values: tuple[str, ...]
) -> bool:
    strings = tuple(
        candidate
        for output in outputs
        for candidate in _semantic_strings(output)
    )
    return any(
        raw_value and any(raw_value in candidate for candidate in strings)
        for raw_value in raw_values
    )


def _parse_timestamp(value: Any, gate: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeWormFailure(gate, "timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeWormFailure(gate, "timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeWormFailure(gate, "timestamp has no timezone")
    return parsed.astimezone(UTC)


def _stamp(value: datetime | Any, gate: str = "timestamp") -> str:
    parsed = value if isinstance(value, datetime) else _parse_timestamp(value, gate)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeWormFailure(gate, "timestamp has no timezone")
    return (
        parsed.astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _decode_object(result: HttpResult, gate: str) -> Mapping[str, Any]:
    if len(result.body) > MAX_RESPONSE_BYTES:
        raise RuntimeWormFailure(gate, "response exceeds the bounded size limit")
    content_type = result.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise RuntimeWormFailure(gate, "response content type is not application/json")
    try:
        value = json.loads(
            result.body.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite_json,
        )
    except RuntimeWormFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise RuntimeWormFailure(gate, "response is not valid UTF-8 JSON") from exc
    if not isinstance(value, Mapping):
        raise RuntimeWormFailure(gate, "response JSON root is not an object")
    return value


class _NoRedirect(HTTPRedirectHandler):
    """Do not forward a bearer token to any redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _default_transport(
    *,
    base_url: str,
    path: str,
    method: str,
    payload: Mapping[str, Any] | None,
    headers: Mapping[str, str],
    timeout: float,
) -> HttpResult:
    body = None if payload is None else _canonical_bytes(payload)
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "CAS-Harness-Runtime-WORM-Collector/1.0",
        **headers,
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - pinned origin
            final = urlparse(str(response.geturl()))
            expected = urlparse(base_url)
            if (
                final.scheme != "https"
                or final.username is not None
                or final.password is not None
                or final.netloc != expected.netloc
            ):
                raise RuntimeWormFailure("redirect", "response origin drifted")
            return HttpResult(
                status=int(response.status),
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read(MAX_RESPONSE_BYTES + 1),
            )
    except HTTPError as exc:
        return HttpResult(
            status=int(exc.code),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=exc.read(MAX_RESPONSE_BYTES + 1),
        )
    except (URLError, OSError, TimeoutError) as exc:
        raise RuntimeWormFailure("network", "public API request failed") from exc


def _mapping(value: Any, gate: str, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeWormFailure(gate, f"response is missing {name}")
    return value


def _required_string(value: Mapping[str, Any], key: str, gate: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise RuntimeWormFailure(gate, f"response is missing {key}")
    return item.strip()


def read_exact_render_deployment(
    *,
    render_api_key: str,
    master_head_sha: str,
    deploy_id: str,
    deployed_at_utc: str | datetime,
    transport: Transport = _default_transport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> tuple[HttpResult, Mapping[str, Any], datetime]:
    """Read one caller-selected exact Render deployment without mutations.

    The hosted wrapper uses this seam before it creates a synthetic account.
    ``RuntimeWormCollector`` also uses it for its pre/post collection reads, so
    both paths enforce the same provider identity, trigger, and timestamp
    contract. Runtime freshness comes from the new readiness, worker, audit,
    and WORM observations, not from forcing an otherwise unchanged service to
    redeploy.
    """

    token = render_api_key.strip()
    if (
        not token
        or len(token) > 8192
        or any(character.isspace() for character in token)
    ):
        raise RuntimeWormFailure("authentication", "Render API key is unavailable")
    if SHA1_RE.fullmatch(master_head_sha) is None:
        raise RuntimeWormFailure("binding", "master head is not a lowercase commit SHA")
    if DEPLOY_ID_RE.fullmatch(deploy_id) is None:
        raise RuntimeWormFailure("binding", "deploy ID is invalid")
    deployed_at = (
        deployed_at_utc.astimezone(UTC)
        if isinstance(deployed_at_utc, datetime)
        and deployed_at_utc.tzinfo is not None
        and deployed_at_utc.utcoffset() is not None
        else _parse_timestamp(deployed_at_utc, "deployment")
    )
    checked_before = clock()
    if checked_before.tzinfo is None or checked_before.utcoffset() is None:
        raise RuntimeWormFailure("clock", "collector clock must be timezone-aware")
    checked_before = checked_before.astimezone(UTC)
    if deployed_at > checked_before:
        raise RuntimeWormFailure("deployment", "deployment timestamp is in the future")
    result = transport(
        base_url=RENDER_API_ORIGIN,
        path=f"/v1/services/{PRODUCTION_SERVICE_ID}/deploys/{deploy_id}",
        method="GET",
        payload=None,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if result.status != 200:
        raise RuntimeWormFailure(
            "render-deployment", f"unexpected HTTP status {result.status}"
        )
    deploy = _decode_object(result, "render-deployment")
    commit = _mapping(deploy.get("commit"), "render-deployment", "commit")
    if (
        deploy.get("id") != deploy_id
        or deploy.get("status") != "live"
        or deploy.get("trigger") != "new_commit"
        or commit.get("id") != master_head_sha
    ):
        raise RuntimeWormFailure(
            "render-deployment", "exact deployment is not live at the pinned commit"
        )
    created = _parse_timestamp(deploy.get("createdAt"), "render-deployment")
    finished = _parse_timestamp(deploy.get("finishedAt"), "render-deployment")
    checked_after = clock()
    if checked_after.tzinfo is None or checked_after.utcoffset() is None:
        raise RuntimeWormFailure("clock", "collector clock must be timezone-aware")
    checked_after = checked_after.astimezone(UTC)
    if checked_after < checked_before:
        raise RuntimeWormFailure("clock", "collector clock moved backwards")
    if finished < created:
        raise RuntimeWormFailure(
            "render-deployment", "deployment finished before it started"
        )
    if finished != deployed_at:
        raise RuntimeWormFailure(
            "render-deployment", "deployment finish time differs from the pinned input"
        )
    if finished > checked_after:
        raise RuntimeWormFailure(
            "render-deployment", "deployment finish time is in the future"
        )
    return result, deploy, finished


class RuntimeWormCollector:
    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str,
        render_api_key: str,
        master_head_sha: str,
        deploy_id: str,
        deployed_at_utc: str,
        transport: Transport = _default_transport,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        nonce: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token.strip()
        self.render_api_key = render_api_key.strip()
        self.master_head_sha = master_head_sha
        self.deploy_id = deploy_id
        self.deployed_at = _parse_timestamp(deployed_at_utc, "deployment")
        self.transport = transport
        self.clock = clock
        self.nonce = nonce or secrets.token_hex(12)
        self._validate_binding()

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise RuntimeWormFailure("clock", "collector clock must be timezone-aware")
        return value.astimezone(UTC)

    def _validate_binding(self) -> None:
        parsed = urlparse(self.base_url)
        expected = urlparse(PRODUCTION_API_ORIGIN)
        if (
            parsed != expected
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeWormFailure("binding", "base URL is not exact public production")
        if SHA1_RE.fullmatch(self.master_head_sha) is None:
            raise RuntimeWormFailure("binding", "master head is not a lowercase commit SHA")
        if DEPLOY_ID_RE.fullmatch(self.deploy_id) is None:
            raise RuntimeWormFailure("binding", "deploy ID is invalid")
        if (
            not self.bearer_token
            or len(self.bearer_token) > 8192
            or any(character.isspace() for character in self.bearer_token)
        ):
            raise RuntimeWormFailure("authentication", "API bearer token is unavailable")
        if (
            not self.render_api_key
            or len(self.render_api_key) > 8192
            or any(character.isspace() for character in self.render_api_key)
        ):
            raise RuntimeWormFailure("authentication", "Render API key is unavailable")
        if not re.fullmatch(r"[0-9a-f]{24}", self.nonce):
            raise RuntimeWormFailure("binding", "probe nonce must be 24 lowercase hex characters")
        checked_at = self._now()
        if self.deployed_at > checked_at:
            raise RuntimeWormFailure("deployment", "deployment timestamp is in the future")

    def _call(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: Mapping[str, Any] | None = None,
        authenticated: bool = False,
        timeout: float = 60.0,
    ) -> HttpResult:
        headers = (
            {"Authorization": f"Bearer {self.bearer_token}"}
            if authenticated
            else {}
        )
        return self.transport(
            base_url=self.base_url,
            path=path,
            method=method,
            payload=payload,
            headers=headers,
            timeout=timeout,
        )

    def _read_render_deploy(self) -> tuple[HttpResult, Mapping[str, Any], datetime]:
        return read_exact_render_deployment(
            render_api_key=self.render_api_key,
            master_head_sha=self.master_head_sha,
            deploy_id=self.deploy_id,
            deployed_at_utc=self.deployed_at,
            transport=self.transport,
            clock=self.clock,
        )

    @staticmethod
    def _expect(
        result: HttpResult, statuses: set[int], gate: str
    ) -> Mapping[str, Any]:
        if result.status not in statuses:
            raise RuntimeWormFailure(gate, f"unexpected HTTP status {result.status}")
        return _decode_object(result, gate)

    @staticmethod
    def _assert_readiness(payload: Mapping[str, Any]) -> None:
        if payload.get("ready") is not True or payload.get("status") != "ok":
            raise RuntimeWormFailure("readiness", "public readiness is not ok")
        checks = _mapping(payload.get("checks"), "readiness", "checks")
        for name in ("api", "cas_engine", "database"):
            check = _mapping(checks.get(name), "readiness", f"checks.{name}")
            if check.get("status") != "ok":
                raise RuntimeWormFailure("readiness", f"checks.{name} is not ok")
        worker = _mapping(checks.get("live_worker"), "readiness", "checks.live_worker")
        if (
            worker.get("status") != "ok"
            or worker.get("authority") != "verified"
            or worker.get("real_weights") is not True
            or worker.get("model_id") != MODEL_ID
        ):
            raise RuntimeWormFailure("readiness", "live-worker readback is not verified")
        worm = _mapping(checks.get("s3_worm"), "readiness", "checks.s3_worm")
        retention_days = worm.get("retention_days")
        if (
            worm.get("status") != "ok"
            or worm.get("authority") != "verified"
            or worm.get("object_lock_mode") not in {"GOVERNANCE", "COMPLIANCE"}
            or not isinstance(retention_days, int)
            or isinstance(retention_days, bool)
            or retention_days < 31
        ):
            raise RuntimeWormFailure("readiness", "S3 WORM readback is not verified")

    @staticmethod
    def _assert_worker(payload: Mapping[str, Any]) -> str:
        expected = {
            "verdict": REALMODE_VERDICT,
            "is_real_model": True,
            "fake_runtime_env": False,
            "model_loaded": True,
            "load_error": None,
            "manifest_is_real_model": True,
            "model_id": MODEL_ID,
        }
        for field, value in expected.items():
            if (
                field not in payload
                or payload.get(field) != value
                or type(payload.get(field)) is not type(value)
            ):
                raise RuntimeWormFailure("worker", f"real-model field {field} is invalid")
        worker_id = payload.get("worker_id") or payload.get("worker_version")
        if not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 200:
            raise RuntimeWormFailure("worker", "worker identity is missing")
        return worker_id.strip()

    @staticmethod
    def _find_anchor_check(verification: Mapping[str, Any]) -> Mapping[str, Any]:
        checks = verification.get("checks")
        matches = (
            [
                item
                for item in checks
                if isinstance(item, Mapping)
                and item.get("artifact") == "merged_packet_external_anchor"
            ]
            if isinstance(checks, list)
            else []
        )
        if len(matches) != 1:
            raise RuntimeWormFailure("worm", "verification has no unique anchor check")
        return matches[0]

    def collect(self) -> tuple[dict[str, Any], dict[str, Any]]:
        render_preflight_result, render_preflight, deployed_at = (
            self._read_render_deploy()
        )
        deployed_at_stamp = _stamp(deployed_at, "deployment")

        readiness_result = self._call("/health/ready")
        readiness = self._expect(readiness_result, {200}, "readiness")
        self._assert_readiness(readiness)
        readiness_verified = self._now()

        worker_result = self._call("/atlas/live/health/realmode")
        worker = self._expect(worker_result, {200}, "worker")
        worker_id = self._assert_worker(worker)
        worker_verified = self._now()
        if readiness_verified > worker_verified:
            raise RuntimeWormFailure(
                "clock", "worker verification precedes readiness verification"
            )

        prompt = (
            "Customer-production runtime WORM evidence probe. Return one short factual "
            f"trace. probe_nonce={self.nonce}"
        )
        selected_modules = ["active_trace", "confidence_margin"]
        create_result = self._call(
            "/api/cas-harness/audit/session",
            method="POST",
            payload={
                "model_id": MODEL_ID,
                "audit_mode": AUDIT_MODE,
                "prompt": prompt,
                "selected_modules": selected_modules,
            },
            authenticated=True,
        )
        created = self._expect(create_result, {200, 201}, "audit-create")
        audit_id = _required_string(created, "audit_id", "audit-create")
        if AUDIT_ID_RE.fullmatch(audit_id) is None:
            raise RuntimeWormFailure("audit-create", "audit ID is invalid")
        if (
            created.get("model_id") != MODEL_ID
            or created.get("audit_mode") != AUDIT_MODE
        ):
            raise RuntimeWormFailure("audit-create", "audit binding is invalid")

        run_result = self._call(
            f"/api/cas-harness/audit/session/{audit_id}/run",
            method="POST",
            authenticated=True,
            timeout=600.0,
        )
        ran = self._expect(run_result, {200}, "audit-run")
        if ran.get("status") != "COMPLETE":
            raise RuntimeWormFailure("audit-run", "audit did not complete")
        if ran.get("verdict") != "FLAG_FOR_HUMAN_REVIEW":
            raise RuntimeWormFailure(
                "audit-run", "runtime probe must remain FLAG_FOR_HUMAN_REVIEW"
            )
        if ran.get("model_id") != MODEL_ID:
            raise RuntimeWormFailure("audit-run", "audit model changed")
        trace_id = _required_string(ran, "evidence_packet_trace_id", "audit-run")
        if TRACE_ID_RE.fullmatch(trace_id) is None:
            raise RuntimeWormFailure("audit-run", "trace ID is invalid")

        packet_result = self._call(
            f"/evidence/{trace_id}", authenticated=True
        )
        packet = self._expect(packet_result, {200}, "packet")
        packet_input = _mapping(packet.get("input"), "packet", "input")
        packet_model = _mapping(packet.get("model"), "packet", "model")
        manifest = _mapping(packet_model.get("manifest"), "packet", "model.manifest")
        scope = _mapping(packet.get("audit_scope"), "packet", "audit_scope")
        packet_verification = _mapping(
            packet.get("verification"), "packet", "verification"
        )
        live_audit = _mapping(packet.get("live_audit"), "packet", "live_audit")
        live_request = _mapping(
            live_audit.get("request"), "packet", "live_audit.request"
        )
        method_config = _mapping(
            live_request.get("method_config"),
            "packet",
            "live_audit.request.method_config",
        )
        provenance = _mapping(packet.get("provenance"), "packet", "provenance")
        packet_bindings = {
            "trace_id": packet.get("trace_id") == trace_id,
            "input.text": packet_input.get("text") == prompt,
            "input.audit_id": packet_input.get("audit_id") == audit_id,
            "input.audit_mode": packet_input.get("audit_mode") == AUDIT_MODE,
            "input.selected_modules": packet_input.get("selected_modules")
            == selected_modules,
            "model.model_key": packet_model.get("model_key") == MODEL_ID,
            "model.runtime": packet_model.get("runtime") == "atlas_live_worker",
            "model.manifest.is_real_model": manifest.get("is_real_model") is True,
            "audit_scope.kind": scope.get("kind") == "open_weight_live_trace",
            "audit_scope.verdict_disposition": scope.get("verdict_disposition")
            == "held_for_human_review",
            "verification.accepted.present": "accepted" in packet_verification,
            "verification.accepted.value": packet_verification.get("accepted") is None,
            "live_audit.audit_id": live_audit.get("audit_id") == audit_id,
            "live_audit.request.prompt": live_request.get("prompt") == prompt,
            "live_audit.request.model_id": live_request.get("model_id") == MODEL_ID,
            "live_audit.request.method_config.audit_mode": method_config.get(
                "audit_mode"
            )
            == AUDIT_MODE,
            "live_audit.request.method_config.selected_modules": method_config.get(
                "selected_modules"
            )
            == selected_modules,
            "live_audit.request.method_config.source": method_config.get("source")
            == "cas_harness_audit_run",
            "provenance.method_label": provenance.get("method_label")
            == "cas_harness_live_worker_v1",
            "provenance.code_commit_sha": provenance.get("code_commit_sha")
            == self.master_head_sha,
        }
        failed_packet_bindings = sorted(
            name for name, matched in packet_bindings.items() if not matched
        )
        if failed_packet_bindings:
            raise RuntimeWormFailure(
                "packet",
                "packet is not the exact nonce-bound real-model audit; mismatched "
                f"bindings: {', '.join(failed_packet_bindings)}",
            )

        verify_result = self._call(
            f"/evidence/{trace_id}/verify",
            method="POST",
            authenticated=True,
        )
        verification = self._expect(verify_result, {200}, "packet-verify")
        if (
            verification.get("overall") != "all_match"
            or verification.get("trace_id") != trace_id
        ):
            raise RuntimeWormFailure("packet-verify", "packet readback is not all_match")

        hashes = _mapping(packet.get("hashes"), "worm", "hashes")
        anchor = _mapping(hashes.get("external_anchor"), "worm", "external_anchor")
        anchor_check = self._find_anchor_check(verification)
        evaluated_at = self._now()
        try:
            lock = validate_object_lock_receipt(
                anchor,
                anchor_check,
                evaluated_at=evaluated_at,
            )
        except ObjectLockReceiptError as exc:
            raise RuntimeWormFailure("worm", str(exc)) from exc
        receipt = _mapping(
            anchor_check.get("object_lock_verification"),
            "worm",
            "object_lock_verification",
        )
        written_at = lock["requested_at"]
        verified_at = _parse_timestamp(receipt.get("verified_at"), "worm")
        if written_at < worker_verified - MAX_CLOCK_SKEW:
            raise RuntimeWormFailure(
                "worm",
                "WORM write predates worker verification beyond allowed clock skew",
            )
        if (
            verified_at < written_at
            or verified_at > evaluated_at + MAX_CLOCK_SKEW
        ):
            raise RuntimeWormFailure("worm", "WORM verification timestamp is invalid")

        render_final_result, render_final, final_deployed_at = (
            self._read_render_deploy()
        )
        if (
            final_deployed_at != deployed_at
            or _canonical_bytes(render_final) != _canonical_bytes(render_preflight)
        ):
            raise RuntimeWormFailure(
                "render-deployment", "deployment record changed during collection"
            )

        # A verified issuer timestamp may be a few seconds ahead of the
        # collector host within the bounded skew accepted above.  Preserve the
        # authoritative proof time as the evidence observation boundary rather
        # than emitting a document whose proof appears to be in its own future.
        observed = max(self._now(), verified_at)
        # The gate event is the beginning of the fresh runtime proof window,
        # not the historical deployment completion. Every current runtime/WORM
        # proof remains at or after this event and inside the fixed 30-minute
        # policy, while the exact deployment stays independently bound as
        # protected provenance.
        event_at = _stamp(
            min(readiness_verified, worker_verified, written_at),
            "runtime evidence event",
        )
        probe_id = f"worm-probe-{self.nonce}"
        object_key_sha = _subject_digest(
            "s3-object-key", f"{lock['bucket']}/{lock['key']}"
        )
        version_id_sha = _subject_digest("s3-version-id", lock["version_id"])
        receipt_sha = _digest_bytes(_canonical_bytes(receipt))
        safe_artifact = {
            "schema_version": SAFE_ARTIFACT_SCHEMA_VERSION,
            "gate": "runtime_worm",
            "environment": ENVIRONMENT,
            "repository": REPOSITORY,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "event_at_utc": event_at,
            "deployed_at_utc": deployed_at_stamp,
            "service_id": PRODUCTION_SERVICE_ID,
            "api_base_url": PRODUCTION_API_ORIGIN,
            "probe_id": probe_id,
            "render_deploy_preflight_http_status": render_preflight_result.status,
            "render_deploy_preflight_sha256": _digest_bytes(
                _canonical_bytes(render_preflight)
            ),
            "render_deploy_final_http_status": render_final_result.status,
            "render_deploy_final_sha256": _digest_bytes(
                _canonical_bytes(render_final)
            ),
            "render_deploy_status": "live",
            "render_deploy_trigger": "new_commit",
            "readiness_http_status": readiness_result.status,
            "readiness_response_sha256": _digest_bytes(_canonical_bytes(readiness)),
            "readiness_verified_at_utc": _stamp(readiness_verified),
            "worker_http_status": worker_result.status,
            "worker_response_sha256": _digest_bytes(_canonical_bytes(worker)),
            "worker_id_sha256": _subject_digest("worker-id", worker_id),
            "worker_verified_at_utc": _stamp(worker_verified),
            "model_id": MODEL_ID,
            "audit_create_http_status": create_result.status,
            "audit_id_sha256": _subject_digest("audit-id", audit_id),
            "audit_run_http_status": run_result.status,
            "audit_prompt_sha256": _subject_digest("audit-prompt", prompt),
            "trace_id_sha256": _subject_digest("trace-id", trace_id),
            "packet_code_commit_sha": self.master_head_sha,
            "packet_sha256": _digest_bytes(_canonical_bytes(packet)),
            "packet_verification_sha256": _digest_bytes(
                _canonical_bytes(verification)
            ),
            "packet_verification_overall": "all_match",
            "object_lock_mode": lock["mode"],
            "configured_retention_days": lock["retention_days"],
            "object_key_sha256": object_key_sha,
            "version_id_sha256": version_id_sha,
            "anchor_manifest_sha256": lock["manifest_sha256"],
            "written_at_utc": _stamp(written_at),
            "verified_at_utc": _stamp(verified_at),
            "retention_until_utc": _stamp(lock["retain_until"]),
            "receipt_sha256": receipt_sha,
            "observed_at_utc": _stamp(observed),
            "authority_published": False,
            "customer_production_status": "OPEN",
        }
        artifact_sha = _digest_bytes(_canonical_bytes(safe_artifact))
        evidence = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "gate": "runtime_worm",
            "environment": ENVIRONMENT,
            "repository": REPOSITORY,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "event_at_utc": event_at,
            "observed_at_utc": _stamp(observed),
            "artifact_uri": AUTHORITY_URI,
            "artifact_sha256": artifact_sha,
            "api_base_url": PRODUCTION_API_ORIGIN,
            "deployment": {
                "service_id": PRODUCTION_SERVICE_ID,
                "service_name": PRODUCTION_SERVICE_NAME,
                "service_type": "web_service",
                "branch": "master",
                "deploy_id": self.deploy_id,
                "commit_sha": self.master_head_sha,
                "status": "live",
                "deployed_at_utc": deployed_at_stamp,
            },
            "readiness": {
                "path": "/health/ready",
                "http_status": readiness_result.status,
                "ready": True,
                "status": "ok",
                "authority": "verified",
                "verified_at_utc": _stamp(readiness_verified),
            },
            "worker": {
                "path": "/atlas/live/health/realmode",
                "http_status": worker_result.status,
                "verdict": REALMODE_VERDICT,
                "is_real_model": True,
                "fake_runtime_env": False,
                "model_loaded": True,
                "load_error": None,
                "manifest_is_real_model": True,
                "model_id": MODEL_ID,
                "worker_id": worker_id,
                "verified_at_utc": _stamp(worker_verified),
            },
            "worm": {
                "status": "ok",
                "authority": "verified",
                "configured_retention_days": lock["retention_days"],
                "write_verified": True,
                "readback_verified": True,
                "object_lock_mode": lock["mode"],
                "probe_id": probe_id,
                "object_key_sha256": object_key_sha,
                "version_id_sha256": version_id_sha,
                "written_at_utc": _stamp(written_at),
                "verified_at_utc": _stamp(verified_at),
                "retention_until_utc": _stamp(lock["retain_until"]),
                "receipt_sha256": receipt_sha,
            },
        }
        _validate_output_pair(evidence, safe_artifact, now=observed)
        raw_identifiers = (
            audit_id,
            trace_id,
            str(lock["bucket"]),
            str(lock["key"]),
            str(lock["version_id"]),
            self.bearer_token,
            self.render_api_key,
        )
        if _semantic_contains_any((evidence, safe_artifact), raw_identifiers):
            raise RuntimeWormFailure("secret-safety", "raw identifier reached output")
        return evidence, safe_artifact


def _validate_output_pair(
    evidence: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    now: datetime,
) -> bytes:
    deployment = _mapping(evidence.get("deployment"), "source-receipt", "deployment")
    readiness = _mapping(evidence.get("readiness"), "source-receipt", "readiness")
    worker = _mapping(evidence.get("worker"), "source-receipt", "worker")
    worm = _mapping(evidence.get("worm"), "source-receipt", "worm")
    if (
        artifact.get("schema_version") != SAFE_ARTIFACT_SCHEMA_VERSION
        or evidence.get("artifact_sha256") != _digest_bytes(_canonical_bytes(artifact))
        or artifact.get("master_head_sha") != evidence.get("master_head_sha")
        or artifact.get("deploy_id") != evidence.get("deploy_id")
        or artifact.get("event_at_utc") != evidence.get("event_at_utc")
        or artifact.get("deployed_at_utc") != deployment.get("deployed_at_utc")
        or artifact.get("render_deploy_preflight_http_status") != 200
        or artifact.get("render_deploy_final_http_status") != 200
        or artifact.get("render_deploy_preflight_sha256")
        != artifact.get("render_deploy_final_sha256")
        or artifact.get("render_deploy_status") != deployment.get("status")
        or artifact.get("render_deploy_trigger") != "new_commit"
        or artifact.get("packet_code_commit_sha") != evidence.get("master_head_sha")
        or artifact.get("readiness_http_status") != readiness.get("http_status")
        or artifact.get("readiness_verified_at_utc")
        != readiness.get("verified_at_utc")
        or artifact.get("worker_http_status") != worker.get("http_status")
        or artifact.get("worker_verified_at_utc") != worker.get("verified_at_utc")
        or artifact.get("model_id") != worker.get("model_id")
        or artifact.get("probe_id") != worm.get("probe_id")
        or artifact.get("configured_retention_days")
        != worm.get("configured_retention_days")
        or artifact.get("object_lock_mode") != worm.get("object_lock_mode")
        or artifact.get("object_key_sha256") != worm.get("object_key_sha256")
        or artifact.get("version_id_sha256") != worm.get("version_id_sha256")
        or artifact.get("written_at_utc") != worm.get("written_at_utc")
        or artifact.get("verified_at_utc") != worm.get("verified_at_utc")
        or artifact.get("retention_until_utc") != worm.get("retention_until_utc")
        or artifact.get("receipt_sha256") != worm.get("receipt_sha256")
        or artifact.get("observed_at_utc") != evidence.get("observed_at_utc")
        or artifact.get("authority_published") is not False
        or artifact.get("customer_production_status") != "OPEN"
    ):
        raise RuntimeWormFailure("source-receipt", "evidence and source receipt diverged")
    for field in (
        "readiness_response_sha256",
        "render_deploy_preflight_sha256",
        "render_deploy_final_sha256",
        "worker_response_sha256",
        "worker_id_sha256",
        "audit_id_sha256",
        "audit_prompt_sha256",
        "trace_id_sha256",
        "packet_sha256",
        "packet_verification_sha256",
        "object_key_sha256",
        "version_id_sha256",
        "anchor_manifest_sha256",
        "receipt_sha256",
    ):
        if SHA256_RE.fullmatch(str(artifact.get(field) or "")) is None:
            raise RuntimeWormFailure("source-receipt", f"{field} is invalid")
    try:
        canonical = canonicalize_acceptance_evidence(
            "runtime_worm", evidence, now=now
        )
    except AcceptanceAuthorityInvalid as exc:
        raise RuntimeWormFailure("acceptance-contract", str(exc)) from exc
    if canonical != _canonical_bytes(evidence):
        raise RuntimeWormFailure("acceptance-contract", "canonical bytes diverged")
    return canonical


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload) + b"\n"
    handle = tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temp_path = Path(handle.name)
    try:
        os.chmod(temp_path, 0o600)
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=PRODUCTION_API_ORIGIN)
    parser.add_argument("--master-head", required=True)
    parser.add_argument("--deploy-id", required=True)
    parser.add_argument("--deployed-at-utc", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--safe-artifact-output", required=True, type=Path)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.output.resolve() == args.safe_artifact_output.resolve():
            raise RuntimeWormFailure("output", "output paths must differ")
        collector = RuntimeWormCollector(
            base_url=args.base_url,
            bearer_token=os.environ.get(API_TOKEN_ENV, ""),
            render_api_key=os.environ.get(RENDER_API_KEY_ENV, ""),
            master_head_sha=args.master_head,
            deploy_id=args.deploy_id,
            deployed_at_utc=args.deployed_at_utc,
        )
        evidence, artifact = collector.collect()
        _atomic_write(args.safe_artifact_output, artifact)
        _atomic_write(args.output, evidence)
        print(
            json.dumps(
                {
                    "artifact_sha256": evidence["artifact_sha256"],
                    "authority_published": False,
                    "customer_production_status": "OPEN",
                    "evidence_sha256": _digest_bytes(_canonical_bytes(evidence)),
                    "gate": "runtime_worm",
                    "status": "validated_draft",
                    "verdict": "FLAG_FOR_HUMAN_REVIEW",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except RuntimeWormFailure as exc:
        print(
            json.dumps(
                {"gate": exc.gate, "status": "OPEN", "error": str(exc)},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
