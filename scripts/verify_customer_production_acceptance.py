#!/usr/bin/env python3
"""Fail-closed, authoritative CAS Harness customer-production acceptance.

The checked-in manifest is intentionally ``OPEN``.  ``--validate-only`` checks
that this contract is well formed without promoting it.  A normal invocation
returns success only for a complete public-production ``ACCEPT`` backed by
dereferenced, hash-verified evidence that is either live from an allowlisted
origin or cryptographically signed by a pinned issuer.

Never put passwords, tokens, cookies, card data, private keys, raw share links,
or provider secrets in the manifest, evidence, receipts, or report.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path(".production/customer-production-acceptance.json")
TRUSTED_ISSUER_REGISTRY = Path(
    ".production/customer-production-trusted-issuers.json"
)
SCHEMA_VERSION = "cas_harness_customer_production_acceptance.v2"
REPORT_SCHEMA_VERSION = "cas_harness_customer_production_acceptance_report.v2"
EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v2"
RECEIPT_SCHEMA_VERSION = "cas_harness_authoritative_receipt.v1"
REGISTRY_SCHEMA_VERSION = "cas_harness_trusted_issuer_registry.v2"
MANIFEST_ID = "cas-harness-customer-production"
REPOSITORY = "LittleHenderson/noetic-compass"
REPOSITORY_ID = 1203465584
REPOSITORY_NODE_ID = "R_kgDOR7ttcA"
REPOSITORY_URL = "https://github.com/LittleHenderson/noetic-compass"
REPOSITORY_API_URL = "https://api.github.com/repos/LittleHenderson/noetic-compass"
PRODUCTION_APP_ORIGIN = "https://atlas.noeticcompass.com"
PRODUCTION_API_ORIGIN = "https://noetic-compass-api.onrender.com"
LANDING_ORIGIN = "https://cascompass.ai"
GITHUB_ORIGIN = "https://github.com"
GITHUB_API_ORIGIN = "https://api.github.com"
RENDER_API_ORIGIN = "https://api.render.com"
PRODUCTION_SERVICE_ID = "srv-d82ph683kofs73d210e0"
PRODUCTION_SERVICE_NAME = "noetic-compass-api"
PRIVATE_CANARY_SERVICE_ID = "srv-d9akoolaeets73bp3e7g"
PRIVATE_CANARY_BRANCH = "release/accounts-canary-20260713"
EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
EXPECTED_REALMODE_VERDICT = "REAL_PYTHIA_WEIGHTS_LOADED"
GITHUB_ACTIONS_APP = {
    "id": 15368,
    "node_id": "MDM6QXBwMTUzNjg=",
    "slug": "github-actions",
}
PRODUCT_STATUSES = frozenset({"OPEN", "ACCEPT"})
EVIDENCE_STATUSES = frozenset({"OPEN", "present"})
RESEARCH_VERDICTS = frozenset(
    {"ACCEPT", "FLAG_FOR_HUMAN_REVIEW", "SUPPRESS"}
)
REQUIRED_CHECKS = (
    "cas-ci-gate",
    "cas-postgres-live-gate",
    "render-blueprint-control-offline",
)
WORKFLOW_CONTRACTS = {
    "cas-ci-gate": {
        "workflow_id": 312407214,
        "workflow_name": "CAS CI",
        "workflow_path": ".github/workflows/ci.yml",
        "job_key": "required_gate",
    },
    "cas-postgres-live-gate": {
        "workflow_id": 312407213,
        "workflow_name": "CAS Postgres State Substrate",
        "workflow_path": ".github/workflows/postgres-state-substrate.yml",
        "job_key": "postgres_state_live",
    },
    "render-blueprint-control-offline": {
        "workflow_id": 312587430,
        "workflow_name": "Render Blueprint Control",
        "workflow_path": ".github/workflows/render-blueprint-control.yml",
        "job_key": "offline",
    },
}
REQUIRED_GATES = (
    "runtime_worm",
    "root_ci_protected_deploy",
    "hosted_customer_journey",
    "accounts_billing",
    "legal_publication_approval",
    "support_crm",
    "incident_tabletop",
    "alert_delivery",
    "claim_honesty",
)
AUTHORITY_GATES = frozenset((*REQUIRED_GATES, "release_decision"))
FRESHNESS_POLICY = {
    "runtime_worm_max_age_minutes": 30,
    "root_ci_protected_deploy_max_age_minutes": 1440,
    "hosted_customer_journey_max_age_minutes": 4320,
    "accounts_billing_max_age_minutes": 4320,
    "legal_publication_approval_max_age_minutes": 43200,
    "support_crm_max_age_minutes": 4320,
    "incident_tabletop_max_age_minutes": 129600,
    "alert_delivery_max_age_minutes": 1440,
    "claim_honesty_max_age_minutes": 1440,
    "worm_configured_min_retention_days": 31,
    "worm_min_remaining_retention_minutes": 43200,
}
GATE_FRESHNESS_KEYS = {
    gate: f"{gate}_max_age_minutes" for gate in REQUIRED_GATES
}
STATUS_MEANING = {
    "OPEN": "Required customer-production evidence is missing, stale, invalid, or awaiting approval.",
    "present": "Required customer-production evidence exists and passes this manifest contract; it is not a research verdict.",
}
AUTHORITY_POLICY = {
    "mode": "authoritative_only",
    "trusted_issuer_registry": "repo://.production/customer-production-trusted-issuers.json",
    "https_requires": "signed_receipt_or_live_verification",
    "private_canary_satisfies_public_gate": False,
}
RELEASE_APPROVER_ROLES = frozenset(
    {"legal_owner", "operations_owner", "product_owner", "security_owner"}
)
LEGAL_DOCUMENT_KINDS = frozenset({"legal", "privacy", "terms"})
LEGAL_APPROVER_ROLES = frozenset(
    {"legal_counsel", "privacy_owner", "product_owner"}
)
CLAIM_SURFACE_KINDS = frozenset(
    {"product_app", "audit_console", "landing", "legal", "privacy", "terms"}
)
CLAIM_APPROVER_ROLES = frozenset(
    {"legal_owner", "product_owner", "research_owner"}
)
TABLETOP_ROLES = frozenset(
    {"incident_commander", "legal", "operations", "security", "support"}
)
TABLETOP_SCENARIOS = frozenset(
    {
        "account_compromise",
        "billing_webhook_failure",
        "data_subject_request",
        "worker_outage",
        "worm_authentication_failure",
    }
)
ALERT_DESTINATIONS = frozenset({"incident_channel", "primary_on_call"})
CLAIM_STATUS_VOCABULARY = (
    "ACCEPT",
    "FLAG_FOR_HUMAN_REVIEW",
    "LICENSED",
    "NOT LICENSED",
    "OPEN",
    "present",
    "unavailable",
)
GATE_ALLOWED_ORIGINS = {
    "runtime_worm": frozenset({PRODUCTION_API_ORIGIN, RENDER_API_ORIGIN}),
    "root_ci_protected_deploy": frozenset(
        {GITHUB_ORIGIN, GITHUB_API_ORIGIN, RENDER_API_ORIGIN}
    ),
    "hosted_customer_journey": frozenset(
        {PRODUCTION_APP_ORIGIN, PRODUCTION_API_ORIGIN}
    ),
    "accounts_billing": frozenset({PRODUCTION_API_ORIGIN}),
    # The human-facing legal pages stay on cascompass.ai, while their
    # secret-free machine authority is canonical JSON from the production API.
    "legal_publication_approval": frozenset(
        {LANDING_ORIGIN, PRODUCTION_API_ORIGIN}
    ),
    "support_crm": frozenset({LANDING_ORIGIN, PRODUCTION_API_ORIGIN}),
    "incident_tabletop": frozenset({PRODUCTION_API_ORIGIN}),
    "alert_delivery": frozenset({PRODUCTION_API_ORIGIN}),
    "claim_honesty": frozenset(
        {PRODUCTION_APP_ORIGIN, PRODUCTION_API_ORIGIN, LANDING_ORIGIN}
    ),
    "release_decision": frozenset({PRODUCTION_API_ORIGIN}),
}
LIVE_AUTHORITY_ENDPOINTS = {
    "runtime_worm": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/runtime-worm",
    },
    # Aggregated GitHub/Render proof must use a signed receipt. Their native
    # APIs do not expose this verifier's complete gate-evidence schema at one
    # fixed endpoint, so no root-CI live authority is deliberately configured.
    "root_ci_protected_deploy": {},
    "hosted_customer_journey": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/customer-journey",
    },
    "accounts_billing": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/accounts-billing",
    },
    "legal_publication_approval": {
        "noetic-production-live": (
            f"{PRODUCTION_API_ORIGIN}/internal/acceptance/"
            "legal-publication-approval"
        ),
    },
    "support_crm": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/support-crm",
    },
    "incident_tabletop": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/incident-tabletop",
    },
    "alert_delivery": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/alert-delivery",
    },
    "claim_honesty": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/claim-honesty",
    },
    "release_decision": {
        "noetic-production-live": f"{PRODUCTION_API_ORIGIN}/internal/acceptance/release-decision",
    },
}
COMMON_EVIDENCE_KEYS = {
    "schema_version",
    "gate",
    "environment",
    "repository",
    "master_head_sha",
    "deploy_id",
    "event_at_utc",
    "observed_at_utc",
    "artifact_uri",
    "artifact_sha256",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TAGGED_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PRIVACY_NOTICE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
AUDIT_ID_RE = re.compile(r"^cas-audit-[0-9a-f]{16}$")
PROBE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
INCIDENT_ID_RE = re.compile(r"^IR-\d{4}-\d{2}-\d{2}-\d{3}$")
MAX_EVIDENCE_BYTES = 2_000_000
RSA_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
PROHIBITED_SECRET_FIELD_NAMES = frozenset(
    {
        "access_key",
        "api_key",
        "authorization",
        "bearer_token",
        "card_number",
        "client_secret",
        "cookie",
        "credential",
        "cvv",
        "password",
        "private_key",
        "secret",
        "secret_access_key",
        "session_cookie",
        "share_token",
        "token",
        "webhook_secret",
    }
)
PROHIBITED_PII_FIELD_NAMES = frozenset(
    {
        "address",
        "customer_email",
        "email",
        "full_name",
        "ip_address",
        "name",
        "phone",
        "postal_address",
        "user_email",
    }
)
SUSPICIOUS_SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "JWT": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    ),
    "bearer credential": re.compile(
        r"(?i)Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{12,}"
    ),
    "Stripe secret": re.compile(
        r"\b(?:sk_(?:live|test)_[A-Za-z0-9]{12,}|whsec_[A-Za-z0-9]{12,})\b"
    ),
    "private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "email address": re.compile(
        r"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    ),
}


class DuplicateJsonKeyError(ValueError):
    """A JSON object contained the same key more than once."""


class ManifestLoadError(RuntimeError):
    """A manifest or evidence document could not be loaded safely."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass
class ValidationContext:
    repo_root: Path
    evidence_root: Path
    verification_time: datetime
    generated_at: datetime | None
    expected_master_head: str | None
    expected_deploy_id: str | None
    repository_commit: str | None
    live: bool
    trusted_issuers: dict[tuple[str, str], dict[str, Any]]
    registry_sha256: str
    errors: list[str] = field(default_factory=list)
    observed_times: dict[str, datetime] = field(default_factory=dict)
    evidence_hashes: dict[str, str] = field(default_factory=dict)
    subject_hashes: dict[str, str] = field(default_factory=dict)
    authorities: dict[str, dict[str, Any]] = field(default_factory=dict)
    resolved_documents: dict[str, bytes] = field(default_factory=dict)


def _error(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _require(condition: bool, path: str, message: str, errors: list[str]) -> None:
    if not condition:
        _error(errors, path, message)


def _json_scalar_equals(value: Any, expected: Any) -> bool:
    """Compare JSON scalars without Python's bool/int aliasing."""

    if isinstance(expected, bool):
        return value is expected
    if isinstance(expected, int):
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value == expected
        )
    return value == expected


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise DuplicateJsonKeyError(f"duplicate JSON key {key!r}")
        value[key] = child
    return value


def _loads_json(raw: bytes, source: str) -> Mapping[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_pairs_without_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        raise ManifestLoadError(
            f"{source}: invalid JSON ({type(exc).__name__})"
        ) from exc
    if not isinstance(value, Mapping):
        raise ManifestLoadError(f"{source}: top-level JSON must be an object")
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _is_mapping(value: Any, path: str, errors: list[str]) -> bool:
    if not isinstance(value, Mapping):
        _error(errors, path, "must be an object")
        return False
    return True


def _exact_keys(
    value: Mapping[str, Any], expected: set[str], path: str, errors: list[str]
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        _error(errors, path, f"missing fields: {', '.join(missing)}")
    if unknown:
        _error(errors, path, f"unknown fields: {', '.join(unknown)}")


def _nonempty_string(value: Any, path: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        _error(errors, path, "must be a non-empty string")
        return None
    return value


def _sha256(value: Any, path: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        _error(errors, path, "must be a lowercase SHA-256 digest")
        return None
    return value


def _tagged_sha256(value: Any, path: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or TAGGED_SHA256_RE.fullmatch(value) is None:
        _error(errors, path, "must be sha256:<64 lowercase hex>")
        return None
    return value


def _commit_sha(value: Any, path: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or SHA1_RE.fullmatch(value) is None:
        _error(errors, path, "must be a lowercase 40-character Git commit SHA")
        return None
    return value


def _positive_int(value: Any, path: str, errors: list[str]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _error(errors, path, "must be a positive integer")
        return None
    return value


def _nonnegative_int(value: Any, path: str, errors: list[str]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _error(errors, path, "must be a non-negative integer")
        return None
    return value


def _timestamp(value: Any, path: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        _error(errors, path, "must use exact UTC form YYYY-MM-DDTHH:MM:SSZ")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        _error(errors, path, "is not a valid UTC timestamp")
        return None


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _origin(value: str) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(value)
        port_value = parsed.port
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
    port = f":{port_value}" if port_value else ""
    return f"https://{parsed.hostname.lower()}{port}"


def _safe_https_url(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allowed_origins: frozenset[str] | set[str] | None = None,
) -> str | None:
    if not isinstance(value, str):
        _error(errors, path, "must be an HTTPS URL")
        return None
    url_origin = _origin(value)
    if url_origin is None:
        _error(
            errors,
            path,
            "must be credential-free HTTPS without query parameters or fragments",
        )
        return None
    if allowed_origins is not None and url_origin not in set(allowed_origins):
        _error(errors, path, "origin is not allowlisted for this evidence class")
        return None
    parsed = urllib.parse.urlsplit(value)
    decoded_path = urllib.parse.unquote(parsed.path)
    if decoded_path != parsed.path:
        _error(errors, path, "must not use encoded path material")
        return None
    if any(part == ".." for part in decoded_path.split("/")):
        _error(errors, path, "must not contain path traversal")
        return None
    return value


def _safe_repo_path(
    uri: Any, root: Path, path: str, errors: list[str]
) -> Path | None:
    if not isinstance(uri, str) or not uri.startswith("repo://"):
        _error(errors, path, "must be a repo:// reference")
        return None
    relative = uri.removeprefix("repo://").replace("\\", "/")
    if not relative or relative.startswith("/"):
        _error(errors, path, "repo:// reference must be relative")
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        _error(errors, path, "repo:// reference escapes its evidence root")
        return None
    return candidate


def _set_of_strings(
    value: Any, expected: frozenset[str], path: str, errors: list[str]
) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _error(errors, path, "must be a string list")
        return set()
    actual = set(value)
    if len(actual) != len(value):
        _error(errors, path, "must not contain duplicates")
    if actual != set(expected):
        _error(errors, path, f"must contain exactly: {', '.join(sorted(expected))}")
    return actual


def _list_by_key(
    value: Any,
    key: str,
    expected: frozenset[str],
    path: str,
    errors: list[str],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        _error(errors, path, "must be a list")
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _is_mapping(item, item_path, errors):
            continue
        identity = item.get(key)
        if not isinstance(identity, str):
            _error(errors, f"{item_path}.{key}", "must be a string")
            continue
        if identity in result:
            _error(errors, path, f"duplicate {key}: {identity}")
        result[identity] = item
    if set(result) != set(expected):
        _error(errors, path, f"must contain exactly: {', '.join(sorted(expected))}")
    return result


def _read_bounded(path: Path, source: str) -> bytes:
    try:
        size = path.stat().st_size
        if size > MAX_EVIDENCE_BYTES:
            raise ManifestLoadError(f"{source}: exceeds evidence size limit")
        return path.read_bytes()
    except OSError as exc:
        raise ManifestLoadError(
            f"{source}: cannot read evidence ({type(exc).__name__})"
        ) from exc


def _repository_text_sha256(raw: bytes) -> str:
    """Hash tracked text independently of checkout newline conversion."""

    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _rsa_verify_rs256(payload: bytes, signature_text: str, n: int, e: int) -> bool:
    try:
        signature = _b64url_decode(signature_text)
    except (ValueError, TypeError):
        return False
    key_size = (n.bit_length() + 7) // 8
    if len(signature) != key_size:
        return False
    value = int.from_bytes(signature, "big")
    if value >= n:
        return False
    encoded = pow(value, e, n).to_bytes(key_size, "big")
    digest_info = RSA_SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(payload).digest()
    padding_size = key_size - len(digest_info) - 3
    if padding_size < 8:
        return False
    expected = b"\x00\x01" + (b"\xff" * padding_size) + b"\x00" + digest_info
    return hmac.compare_digest(encoded, expected)


def _repository_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip().lower()
    return value if SHA1_RE.fullmatch(value) else None


def _load_trusted_issuer_registry(
    repo_root: Path,
) -> tuple[dict[tuple[str, str], dict[str, Any]], str]:
    path = repo_root / TRUSTED_ISSUER_REGISTRY
    raw = _read_bounded(path, str(TRUSTED_ISSUER_REGISTRY))
    registry_hash = hashlib.sha256(raw).hexdigest()
    payload = _loads_json(raw, str(TRUSTED_ISSUER_REGISTRY))
    if set(payload) != {"schema_version", "issuers"}:
        raise ManifestLoadError("trusted issuer registry has missing or unknown fields")
    if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ManifestLoadError("trusted issuer registry schema_version drifted")
    issuers = payload.get("issuers")
    if not isinstance(issuers, list):
        raise ManifestLoadError("trusted issuer registry issuers must be a list")
    normalized: dict[tuple[str, str], dict[str, Any]] = {}
    expected_keys = {
        "issuer",
        "key_id",
        "algorithm",
        "n_base64url",
        "e",
        "allowed_subjects",
        "valid_from_utc",
        "valid_until_utc",
    }
    for index, item in enumerate(issuers):
        if not isinstance(item, Mapping) or set(item) != expected_keys:
            raise ManifestLoadError(
                f"trusted issuer registry issuers[{index}] has invalid fields"
            )
        issuer = item.get("issuer")
        key_id = item.get("key_id")
        if not isinstance(issuer, str) or not issuer or not isinstance(key_id, str) or not key_id:
            raise ManifestLoadError(
                f"trusted issuer registry issuers[{index}] identity is invalid"
            )
        identity = (issuer, key_id)
        if identity in normalized:
            raise ManifestLoadError("trusted issuer registry contains a duplicate identity")
        if item.get("algorithm") != "RS256":
            raise ManifestLoadError("trusted issuer algorithm must be RS256")
        try:
            n = int.from_bytes(_b64url_decode(str(item.get("n_base64url"))), "big")
        except (ValueError, TypeError) as exc:
            raise ManifestLoadError("trusted issuer modulus is invalid") from exc
        e = item.get("e")
        if n.bit_length() < 2048 or e != 65537:
            raise ManifestLoadError("trusted issuer key must be RSA-2048+ with e=65537")
        subjects = item.get("allowed_subjects")
        if not isinstance(subjects, list) or not subjects:
            raise ManifestLoadError("trusted issuer allowed_subjects is invalid")
        allowed_subjects: set[tuple[str, str]] = set()
        for subject_index, subject in enumerate(subjects):
            if not isinstance(subject, Mapping) or set(subject) != {"gate", "uri"}:
                raise ManifestLoadError(
                    "trusted issuer allowed_subjects contains invalid fields"
                )
            gate = subject.get("gate")
            uri = subject.get("uri")
            subject_errors: list[str] = []
            if not isinstance(gate, str) or gate not in AUTHORITY_GATES:
                raise ManifestLoadError(
                    "trusted issuer allowed_subjects contains an invalid gate"
                )
            validated_uri = _safe_https_url(
                uri,
                f"allowed_subjects[{subject_index}].uri",
                subject_errors,
                allowed_origins=GATE_ALLOWED_ORIGINS[gate],
            )
            if subject_errors or validated_uri is None:
                raise ManifestLoadError(
                    "trusted issuer allowed_subjects contains an invalid URI"
                )
            grant = (gate, validated_uri)
            if grant in allowed_subjects:
                raise ManifestLoadError(
                    "trusted issuer allowed_subjects contains a duplicate grant"
                )
            allowed_subjects.add(grant)
        timestamp_errors: list[str] = []
        valid_from = _timestamp(item.get("valid_from_utc"), "valid_from_utc", timestamp_errors)
        valid_until = _timestamp(item.get("valid_until_utc"), "valid_until_utc", timestamp_errors)
        if timestamp_errors or valid_from is None or valid_until is None or valid_from >= valid_until:
            raise ManifestLoadError("trusted issuer validity window is invalid")
        normalized[identity] = {
            "n": n,
            "e": e,
            "allowed_subjects": frozenset(allowed_subjects),
            "valid_from": valid_from,
            "valid_until": valid_until,
        }
    return normalized, registry_hash


def _fetch_https(uri: str, allowed_origins: frozenset[str]) -> bytes:
    if _origin(uri) not in allowed_origins:
        raise ManifestLoadError("live evidence origin is not allowlisted")
    request = urllib.request.Request(
        uri,
        headers={
            "Accept": "application/json",
            "User-Agent": "cas-customer-production-acceptance/2",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            final_url = response.geturl()
            if _origin(final_url) not in allowed_origins:
                raise ManifestLoadError("live evidence redirected outside its allowlist")
            if int(response.status) != 200:
                raise ManifestLoadError("live evidence did not return HTTP 200")
            raw = response.read(MAX_EVIDENCE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise ManifestLoadError(
            f"live evidence returned HTTP {exc.code}; response body suppressed"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ManifestLoadError(
            f"live evidence request failed ({type(exc).__name__})"
        ) from exc
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise ManifestLoadError("live evidence exceeds evidence size limit")
    return raw


def _validate_receipt(
    receipt: Mapping[str, Any],
    *,
    gate: str,
    issuer_name: str,
    key_id: str,
    context: ValidationContext,
    path: str,
) -> Mapping[str, Any] | None:
    errors = context.errors
    expected_keys = {
        "schema_version",
        "issuer",
        "key_id",
        "gate",
        "environment",
        "repository",
        "master_head_sha",
        "deploy_id",
        "issued_at_utc",
        "expires_at_utc",
        "subject_uri",
        "subject_sha256",
        "evidence",
        "signature_base64url",
    }
    _exact_keys(receipt, expected_keys, path, errors)
    _require(
        receipt.get("schema_version") == RECEIPT_SCHEMA_VERSION,
        f"{path}.schema_version",
        f"must be {RECEIPT_SCHEMA_VERSION}",
        errors,
    )
    _require(receipt.get("issuer") == issuer_name, f"{path}.issuer", "must match the manifest authority issuer", errors)
    _require(receipt.get("key_id") == key_id, f"{path}.key_id", "must match the manifest authority key_id", errors)
    _require(receipt.get("gate") == gate, f"{path}.gate", "must match the evidence gate", errors)
    _require(receipt.get("environment") == "public-production", f"{path}.environment", "must be public-production", errors)
    _require(receipt.get("repository") == REPOSITORY, f"{path}.repository", f"must be {REPOSITORY}", errors)
    _require(
        context.expected_master_head is not None
        and receipt.get("master_head_sha") == context.expected_master_head,
        f"{path}.master_head_sha",
        "must match the externally supplied expected master HEAD",
        errors,
    )
    _require(
        context.expected_deploy_id is not None
        and receipt.get("deploy_id") == context.expected_deploy_id,
        f"{path}.deploy_id",
        "must match the externally supplied production deployment ID",
        errors,
    )
    issued = _timestamp(receipt.get("issued_at_utc"), f"{path}.issued_at_utc", errors)
    expires = _timestamp(receipt.get("expires_at_utc"), f"{path}.expires_at_utc", errors)
    if issued is not None and context.generated_at is not None:
        _require(issued <= context.generated_at, f"{path}.issued_at_utc", "must be at or before manifest generation", errors)
    if issued is not None:
        _require(issued <= context.verification_time, f"{path}.issued_at_utc", "must be at or before verification", errors)
    if expires is not None:
        _require(expires >= context.verification_time, f"{path}.expires_at_utc", "must still be active at verification", errors)
    if issued is not None and expires is not None:
        _require(issued <= expires, f"{path}.expires_at_utc", "must be at or after receipt issuance", errors)
    subject_uri = _safe_https_url(
        receipt.get("subject_uri"),
        f"{path}.subject_uri",
        errors,
        allowed_origins=GATE_ALLOWED_ORIGINS[gate],
    )
    subject_hash = _sha256(receipt.get("subject_sha256"), f"{path}.subject_sha256", errors)
    identity = (issuer_name, key_id)
    issuer = context.trusted_issuers.get(identity)
    if issuer is None:
        _error(errors, f"{path}.issuer", "issuer/key_id is not pinned in the trusted registry")
    else:
        if subject_uri is not None:
            _require(
                (gate, subject_uri) in issuer["allowed_subjects"],
                f"{path}.subject_uri",
                "must match one exact issuer gate/subject grant",
                errors,
            )
        if issued is not None:
            _require(issuer["valid_from"] <= issued <= issuer["valid_until"], f"{path}.issued_at_utc", "is outside the issuer key validity window", errors)
        _require(context.verification_time <= issuer["valid_until"], f"{path}.expires_at_utc", "issuer key is expired at verification", errors)
        signature = receipt.get("signature_base64url")
        unsigned = {key: value for key, value in receipt.items() if key != "signature_base64url"}
        valid_signature = isinstance(signature, str) and _rsa_verify_rs256(
            _canonical_bytes(unsigned), signature, issuer["n"], issuer["e"]
        )
        _require(valid_signature, f"{path}.signature_base64url", "RS256 signature verification failed", errors)
    evidence = receipt.get("evidence")
    if not _is_mapping(evidence, f"{path}.evidence", errors):
        return None
    evidence_observed = _timestamp(
        evidence.get("observed_at_utc"),
        f"{path}.evidence.observed_at_utc",
        errors,
    )
    if issued is not None and evidence_observed is not None:
        _require(
            issued >= evidence_observed,
            f"{path}.issued_at_utc",
            "must be at or after evidence observation",
            errors,
        )
    if subject_uri is not None:
        _require(evidence.get("artifact_uri") == subject_uri, f"{path}.evidence.artifact_uri", "must be bound to the signed subject_uri", errors)
    if subject_hash is not None:
        _require(evidence.get("artifact_sha256") == subject_hash, f"{path}.evidence.artifact_sha256", "must be bound to the signed subject_sha256", errors)
        context.subject_hashes[gate] = subject_hash
    context.authorities[gate] = {
        "mode": "signed_receipt",
        "issuer": issuer_name,
        "key_id": key_id,
        "subject_origin": _origin(subject_uri) if subject_uri else None,
        "subject_uri": subject_uri,
    }
    return evidence


def _resolve_authoritative_evidence(
    reference: Mapping[str, Any], gate: str, context: ValidationContext
) -> Mapping[str, Any] | None:
    path = (
        "$.product.release_decision.evidence"
        if gate == "release_decision"
        else f"$.required_gates.{gate}.evidence"
    )
    errors = context.errors
    _exact_keys(reference, {"uri", "sha256", "authority"}, path, errors)
    uri = reference.get("uri")
    expected_hash = _sha256(reference.get("sha256"), f"{path}.sha256", errors)
    authority = reference.get("authority")
    if not _is_mapping(authority, f"{path}.authority", errors):
        return None
    _exact_keys(authority, {"mode", "issuer", "key_id"}, f"{path}.authority", errors)
    mode = authority.get("mode")
    issuer = authority.get("issuer")
    key_id = authority.get("key_id")
    if mode not in {"signed_receipt", "live_https"}:
        _error(errors, f"{path}.authority.mode", "must be signed_receipt or live_https")
        return None
    if not isinstance(issuer, str) or not issuer:
        _error(errors, f"{path}.authority.issuer", "must be a non-empty string")
        return None
    raw: bytes | None = None
    if mode == "signed_receipt":
        if not isinstance(key_id, str) or not key_id:
            _error(errors, f"{path}.authority.key_id", "is required for signed_receipt")
            return None
        receipt_path = _safe_repo_path(uri, context.evidence_root, f"{path}.uri", errors)
        if receipt_path is None:
            return None
        try:
            raw = _read_bounded(receipt_path, str(uri))
        except ManifestLoadError as exc:
            _error(errors, f"{path}.uri", str(exc))
            return None
    else:
        _require(key_id is None, f"{path}.authority.key_id", "must be null for live_https", errors)
        if not context.live:
            _error(errors, f"{path}.authority.mode", "live_https requires --live verification")
            return None
        expected_endpoint = LIVE_AUTHORITY_ENDPOINTS.get(gate, {}).get(issuer)
        if expected_endpoint is None or uri != expected_endpoint:
            _error(
                errors,
                f"{path}.uri",
                "must match the exact live issuer endpoint bound to this gate",
            )
            return None
        if not isinstance(uri, str) or _safe_https_url(
            uri,
            f"{path}.uri",
            errors,
            allowed_origins=frozenset({_origin(expected_endpoint)}),
        ) is None:
            return None
        try:
            raw = _fetch_https(uri, frozenset({_origin(expected_endpoint)}))
        except ManifestLoadError as exc:
            _error(errors, f"{path}.uri", str(exc))
            return None
    if raw is None:
        return None
    actual_hash = hashlib.sha256(raw).hexdigest()
    if expected_hash is not None:
        _require(actual_hash == expected_hash, f"{path}.sha256", "does not match the dereferenced evidence bytes", errors)
    context.evidence_hashes[gate] = actual_hash
    try:
        document = _loads_json(raw, str(uri))
    except ManifestLoadError as exc:
        _error(errors, f"{path}.uri", str(exc))
        return None
    errors.extend(
        _find_prohibited_fields(
            document,
            f"{path}.document",
            # The live authority service has no root-CI route. Its other gate
            # schemas prohibit PII-named fields, while root-CI legitimately
            # contains workflow ``name`` and repository ``full_name`` keys.
            include_pii=gate != "root_ci_protected_deploy",
        )
    )
    errors.extend(_scan_secret_shapes(document, f"{path}.document"))
    context.resolved_documents[gate] = raw
    if mode == "signed_receipt":
        return _validate_receipt(
            document,
            gate=gate,
            issuer_name=issuer,
            key_id=str(key_id),
            context=context,
            path=f"{path}.receipt",
        )
    context.authorities[gate] = {
        "mode": "live_https",
        "issuer": issuer,
        "key_id": None,
        "subject_origin": _origin(str(uri)),
        "subject_uri": str(uri),
    }
    return document


def _validate_common_evidence(
    evidence: Mapping[str, Any], gate: str, context: ValidationContext
) -> tuple[datetime | None, datetime | None]:
    path = (
        "$.product.release_decision.evidence.payload"
        if gate == "release_decision"
        else f"$.required_gates.{gate}.evidence.payload"
    )
    errors = context.errors
    _require(evidence.get("schema_version") == EVIDENCE_SCHEMA_VERSION, f"{path}.schema_version", f"must be {EVIDENCE_SCHEMA_VERSION}", errors)
    _require(evidence.get("gate") == gate, f"{path}.gate", "must match its manifest gate", errors)
    _require(evidence.get("environment") == "public-production", f"{path}.environment", "must be public-production; private canary proof is forbidden", errors)
    _require(evidence.get("repository") == REPOSITORY, f"{path}.repository", f"must be {REPOSITORY}", errors)
    _require(
        context.expected_master_head is not None
        and evidence.get("master_head_sha") == context.expected_master_head,
        f"{path}.master_head_sha",
        "must match the externally supplied expected master HEAD",
        errors,
    )
    _require(
        context.expected_deploy_id is not None
        and evidence.get("deploy_id") == context.expected_deploy_id,
        f"{path}.deploy_id",
        "must match the externally supplied production deployment ID",
        errors,
    )
    event = _timestamp(evidence.get("event_at_utc"), f"{path}.event_at_utc", errors)
    observed = _timestamp(evidence.get("observed_at_utc"), f"{path}.observed_at_utc", errors)
    if event is not None and observed is not None:
        _require(event <= observed, f"{path}.event_at_utc", "must be at or before observation", errors)
    if event is not None:
        _require(event <= context.verification_time, f"{path}.event_at_utc", "must be at or before verification", errors)
        if gate in GATE_FRESHNESS_KEYS:
            max_age = FRESHNESS_POLICY[GATE_FRESHNESS_KEYS[gate]]
            _require(
                context.verification_time - event <= timedelta(minutes=max_age),
                f"{path}.event_at_utc",
                f"is stale; maximum age is {max_age} minutes",
                errors,
            )
    if observed is not None:
        if context.generated_at is not None:
            _require(observed <= context.generated_at, f"{path}.observed_at_utc", "must be at or before manifest generation", errors)
        _require(observed <= context.verification_time, f"{path}.observed_at_utc", "must be at or before verification", errors)
        if gate in GATE_FRESHNESS_KEYS:
            max_age = FRESHNESS_POLICY[GATE_FRESHNESS_KEYS[gate]]
            _require(context.verification_time - observed <= timedelta(minutes=max_age), f"{path}.observed_at_utc", f"is stale; maximum age is {max_age} minutes", errors)
        context.observed_times[gate] = observed
    artifact_uri = _safe_https_url(
        evidence.get("artifact_uri"),
        f"{path}.artifact_uri",
        errors,
        allowed_origins=GATE_ALLOWED_ORIGINS[gate],
    )
    artifact_hash = _sha256(evidence.get("artifact_sha256"), f"{path}.artifact_sha256", errors)
    serialized = json.dumps(evidence, sort_keys=True).lower()
    _require(PRIVATE_CANARY_SERVICE_ID not in serialized, path, "private canary service proof cannot satisfy a public gate", errors)
    _require(PRIVATE_CANARY_BRANCH not in serialized, path, "private canary branch proof cannot satisfy a public gate", errors)
    _require("accounts-canary" not in serialized, path, "private canary evidence cannot satisfy a public gate", errors)
    if artifact_hash is not None:
        context.subject_hashes.setdefault(gate, artifact_hash)
    if artifact_uri is not None and gate in context.authorities:
        subject_uri = context.authorities[gate].get("subject_uri")
        _require(
            isinstance(subject_uri, str) and artifact_uri == subject_uri,
            f"{path}.artifact_uri",
            "must match the exact authoritative receipt/live source",
            errors,
        )
    return event, observed


def _critical_proof_timestamp(
    value: Any,
    *,
    gate: str,
    event: datetime | None,
    observed: datetime | None,
    context: ValidationContext,
    path: str,
) -> datetime | None:
    errors = context.errors
    timestamp = _timestamp(value, path, errors)
    if timestamp is not None:
        if event is not None:
            _require(
                timestamp >= event,
                path,
                "must be at or after the gate event",
                errors,
            )
        if observed is not None:
            _require(
                timestamp <= observed,
                path,
                "must be at or before evidence observation",
                errors,
            )
        _require(
            timestamp <= context.verification_time,
            path,
            "must be at or before verification",
            errors,
        )
        if gate in GATE_FRESHNESS_KEYS:
            max_age = FRESHNESS_POLICY[GATE_FRESHNESS_KEYS[gate]]
            _require(
                context.verification_time - timestamp
                <= timedelta(minutes=max_age),
                path,
                f"is stale; maximum age is {max_age} minutes",
                errors,
            )
    return timestamp


def _validate_runtime_worm(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.runtime_worm.evidence.payload"
    errors = context.errors
    _exact_keys(
        evidence,
        COMMON_EVIDENCE_KEYS
        | {"api_base_url", "deployment", "readiness", "worker", "worm"},
        path,
        errors,
    )
    event, observed = _validate_common_evidence(evidence, "runtime_worm", context)
    _require(evidence.get("api_base_url") == PRODUCTION_API_ORIGIN, f"{path}.api_base_url", f"must be {PRODUCTION_API_ORIGIN}", errors)

    deployment = evidence.get("deployment")
    if _is_mapping(deployment, f"{path}.deployment", errors):
        _exact_keys(
            deployment,
            {
                "service_id",
                "service_name",
                "service_type",
                "branch",
                "deploy_id",
                "commit_sha",
                "status",
                "deployed_at_utc",
            },
            f"{path}.deployment",
            errors,
        )
        for field, expected in {
            "service_id": PRODUCTION_SERVICE_ID,
            "service_name": PRODUCTION_SERVICE_NAME,
            "service_type": "web_service",
            "branch": "master",
            "status": "live",
        }.items():
            _require(_json_scalar_equals(deployment.get(field), expected), f"{path}.deployment.{field}", f"must equal {expected!r}", errors)
        _require(deployment.get("deploy_id") == context.expected_deploy_id, f"{path}.deployment.deploy_id", "must match expected production deployment", errors)
        _require(deployment.get("commit_sha") == context.expected_master_head, f"{path}.deployment.commit_sha", "must match expected master HEAD", errors)
        _critical_proof_timestamp(deployment.get("deployed_at_utc"), gate="runtime_worm", event=event, observed=observed, context=context, path=f"{path}.deployment.deployed_at_utc")

    readiness = evidence.get("readiness")
    if _is_mapping(readiness, f"{path}.readiness", errors):
        _exact_keys(readiness, {"path", "http_status", "ready", "status", "authority", "verified_at_utc"}, f"{path}.readiness", errors)
        for field, expected in {
            "path": "/health/ready",
            "http_status": 200,
            "ready": True,
            "status": "ok",
            "authority": "verified",
        }.items():
            _require(_json_scalar_equals(readiness.get(field), expected), f"{path}.readiness.{field}", f"must equal {expected!r}", errors)
        _critical_proof_timestamp(readiness.get("verified_at_utc"), gate="runtime_worm", event=event, observed=observed, context=context, path=f"{path}.readiness.verified_at_utc")

    worker = evidence.get("worker")
    if _is_mapping(worker, f"{path}.worker", errors):
        _exact_keys(
            worker,
            {
                "path",
                "http_status",
                "verdict",
                "is_real_model",
                "fake_runtime_env",
                "model_loaded",
                "load_error",
                "manifest_is_real_model",
                "model_id",
                "worker_id",
                "verified_at_utc",
            },
            f"{path}.worker",
            errors,
        )
        expected = {
            "path": "/atlas/live/health/realmode",
            "http_status": 200,
            "verdict": EXPECTED_REALMODE_VERDICT,
            "is_real_model": True,
            "fake_runtime_env": False,
            "model_loaded": True,
            "load_error": None,
            "manifest_is_real_model": True,
            "model_id": EXPECTED_MODEL_ID,
        }
        for field, value in expected.items():
            _require(_json_scalar_equals(worker.get(field), value), f"{path}.worker.{field}", f"must equal {value!r}", errors)
        _nonempty_string(worker.get("worker_id"), f"{path}.worker.worker_id", errors)
        _critical_proof_timestamp(worker.get("verified_at_utc"), gate="runtime_worm", event=event, observed=observed, context=context, path=f"{path}.worker.verified_at_utc")

    worm = evidence.get("worm")
    if _is_mapping(worm, f"{path}.worm", errors):
        _exact_keys(
            worm,
            {
                "status",
                "authority",
                "configured_retention_days",
                "write_verified",
                "readback_verified",
                "object_lock_mode",
                "probe_id",
                "object_key_sha256",
                "version_id_sha256",
                "written_at_utc",
                "verified_at_utc",
                "retention_until_utc",
                "receipt_sha256",
            },
            f"{path}.worm",
            errors,
        )
        for field, expected in {
            "status": "ok",
            "authority": "verified",
            "write_verified": True,
            "readback_verified": True,
        }.items():
            _require(_json_scalar_equals(worm.get(field), expected), f"{path}.worm.{field}", f"must equal {expected!r}", errors)
        configured_days = _positive_int(worm.get("configured_retention_days"), f"{path}.worm.configured_retention_days", errors)
        if configured_days is not None:
            _require(configured_days >= FRESHNESS_POLICY["worm_configured_min_retention_days"], f"{path}.worm.configured_retention_days", f"must be at least {FRESHNESS_POLICY['worm_configured_min_retention_days']}", errors)
        _require(worm.get("object_lock_mode") in {"GOVERNANCE", "COMPLIANCE"}, f"{path}.worm.object_lock_mode", "must be GOVERNANCE or COMPLIANCE", errors)
        _require(isinstance(worm.get("probe_id"), str) and PROBE_ID_RE.fullmatch(str(worm.get("probe_id"))) is not None, f"{path}.worm.probe_id", "must be a non-secret unique probe ID", errors)
        for field in ("object_key_sha256", "version_id_sha256", "receipt_sha256"):
            _sha256(worm.get(field), f"{path}.worm.{field}", errors)
        written = _critical_proof_timestamp(worm.get("written_at_utc"), gate="runtime_worm", event=event, observed=observed, context=context, path=f"{path}.worm.written_at_utc")
        verified = _critical_proof_timestamp(worm.get("verified_at_utc"), gate="runtime_worm", event=event, observed=observed, context=context, path=f"{path}.worm.verified_at_utc")
        retention = _timestamp(worm.get("retention_until_utc"), f"{path}.worm.retention_until_utc", errors)
        if written is not None and verified is not None:
            _require(written <= verified, f"{path}.worm.verified_at_utc", "must be after the unique write", errors)
        if written is not None and retention is not None and configured_days is not None:
            _require(retention - written >= timedelta(days=configured_days), f"{path}.worm.retention_until_utc", "receipt window must cover the configured retention period", errors)
        if retention is not None:
            min_remaining = FRESHNESS_POLICY["worm_min_remaining_retention_minutes"]
            _require(retention - context.verification_time >= timedelta(minutes=min_remaining), f"{path}.worm.retention_until_utc", f"must remain active for at least {min_remaining} minutes after verification", errors)


def _validate_root_ci(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.root_ci_protected_deploy.evidence.payload"
    errors = context.errors
    _exact_keys(
        evidence,
        COMMON_EVIDENCE_KEYS
        | {
            "github_repository",
            "branch",
            "workflow_directory",
            "misplaced_workflow_count",
            "github_app",
            "branch_protection",
            "checks",
            "deployment",
        },
        path,
        errors,
    )
    event, observed = _validate_common_evidence(
        evidence, "root_ci_protected_deploy", context
    )
    repository = evidence.get("github_repository")
    if _is_mapping(repository, f"{path}.github_repository", errors):
        _exact_keys(repository, {"id", "node_id", "full_name", "html_url", "api_url"}, f"{path}.github_repository", errors)
        expected = {
            "id": REPOSITORY_ID,
            "node_id": REPOSITORY_NODE_ID,
            "full_name": REPOSITORY,
            "html_url": REPOSITORY_URL,
            "api_url": REPOSITORY_API_URL,
        }
        for field, value in expected.items():
            _require(_json_scalar_equals(repository.get(field), value), f"{path}.github_repository.{field}", f"must equal {value!r}", errors)
    _require(evidence.get("branch") == "master", f"{path}.branch", "must be master", errors)
    _require(evidence.get("workflow_directory") == ".github/workflows", f"{path}.workflow_directory", "must be repository-root .github/workflows", errors)
    _require(_json_scalar_equals(evidence.get("misplaced_workflow_count"), 0), f"{path}.misplaced_workflow_count", "must be zero", errors)
    app = evidence.get("github_app")
    if _is_mapping(app, f"{path}.github_app", errors):
        _exact_keys(app, set(GITHUB_ACTIONS_APP), f"{path}.github_app", errors)
        _require(dict(app) == GITHUB_ACTIONS_APP, f"{path}.github_app", "must be the pinned GitHub Actions App identity", errors)

    protection = evidence.get("branch_protection")
    if _is_mapping(protection, f"{path}.branch_protection", errors):
        _exact_keys(protection, {"strict", "required_checks", "source", "observed_at_utc"}, f"{path}.branch_protection", errors)
        _require(protection.get("strict") is True, f"{path}.branch_protection.strict", "must be true", errors)
        _set_of_strings(protection.get("required_checks"), frozenset(REQUIRED_CHECKS), f"{path}.branch_protection.required_checks", errors)
        _require(protection.get("source") == "github-api", f"{path}.branch_protection.source", "must be github-api", errors)
        _critical_proof_timestamp(protection.get("observed_at_utc"), gate="root_ci_protected_deploy", event=event, observed=observed, context=context, path=f"{path}.branch_protection.observed_at_utc")

    checks = _list_by_key(evidence.get("checks"), "name", frozenset(REQUIRED_CHECKS), f"{path}.checks", errors)
    run_ids: set[int] = set()
    check_run_ids: set[int] = set()
    for name, check in checks.items():
        item_path = f"{path}.checks[{name}]"
        _exact_keys(
            check,
            {
                "name",
                "workflow_id",
                "workflow_name",
                "workflow_path",
                "job_key",
                "run_id",
                "run_attempt",
                "event",
                "status",
                "conclusion",
                "head_branch",
                "head_sha",
                "check_run_id",
                "check_suite_id",
                "app_id",
                "app_node_id",
                "app_slug",
                "details_url",
                "completed_at_utc",
            },
            item_path,
            errors,
        )
        contract = WORKFLOW_CONTRACTS[name]
        for field, value in contract.items():
            _require(_json_scalar_equals(check.get(field), value), f"{item_path}.{field}", f"must equal {value!r}", errors)
        for field, value in {
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "master",
            "head_sha": context.expected_master_head,
            "app_id": GITHUB_ACTIONS_APP["id"],
            "app_node_id": GITHUB_ACTIONS_APP["node_id"],
            "app_slug": GITHUB_ACTIONS_APP["slug"],
        }.items():
            _require(_json_scalar_equals(check.get(field), value), f"{item_path}.{field}", f"must equal {value!r}", errors)
        run_id = _positive_int(check.get("run_id"), f"{item_path}.run_id", errors)
        _positive_int(check.get("run_attempt"), f"{item_path}.run_attempt", errors)
        check_run_id = _positive_int(check.get("check_run_id"), f"{item_path}.check_run_id", errors)
        _positive_int(check.get("check_suite_id"), f"{item_path}.check_suite_id", errors)
        if run_id is not None:
            _require(run_id not in run_ids, f"{item_path}.run_id", "must be unique across required workflows", errors)
            run_ids.add(run_id)
            if check_run_id is not None:
                expected_details_url = f"{REPOSITORY_URL}/actions/runs/{run_id}/job/{check_run_id}"
                _require(check.get("details_url") == expected_details_url, f"{item_path}.details_url", "must bind the check to its exact workflow run and check-run job", errors)
        if check_run_id is not None:
            _require(check_run_id not in check_run_ids, f"{item_path}.check_run_id", "must be unique", errors)
            check_run_ids.add(check_run_id)
        _critical_proof_timestamp(check.get("completed_at_utc"), gate="root_ci_protected_deploy", event=event, observed=observed, context=context, path=f"{item_path}.completed_at_utc")

    deployment = evidence.get("deployment")
    if _is_mapping(deployment, f"{path}.deployment", errors):
        _exact_keys(
            deployment,
            {
                "provider",
                "service_id",
                "service_name",
                "service_type",
                "repository",
                "branch",
                "deploy_id",
                "status",
                "commit_sha",
                "auto_deploy_trigger",
                "health_check_path",
                "deployed_at_utc",
            },
            f"{path}.deployment",
            errors,
        )
        expected = {
            "provider": "Render",
            "service_id": PRODUCTION_SERVICE_ID,
            "service_name": PRODUCTION_SERVICE_NAME,
            "service_type": "web_service",
            "repository": REPOSITORY_URL,
            "branch": "master",
            "deploy_id": context.expected_deploy_id,
            "status": "live",
            "commit_sha": context.expected_master_head,
            "auto_deploy_trigger": "checksPass",
            "health_check_path": "/health",
        }
        for field, value in expected.items():
            _require(_json_scalar_equals(deployment.get(field), value), f"{path}.deployment.{field}", f"must equal {value!r}", errors)
        _critical_proof_timestamp(deployment.get("deployed_at_utc"), gate="root_ci_protected_deploy", event=event, observed=observed, context=context, path=f"{path}.deployment.deployed_at_utc")


def _validate_hosted_customer(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.hosted_customer_journey.evidence.payload"
    errors = context.errors
    _exact_keys(
        evidence,
        COMMON_EVIDENCE_KEYS
        | {
            "app_url",
            "api_base_url",
            "service_id",
            "customer_lane",
            "tenant_subject_sha256",
            "account_subject_sha256",
            "audit",
            "packet_download",
            "share",
            "tenant_isolation",
        },
        path,
        errors,
    )
    event, observed = _validate_common_evidence(
        evidence, "hosted_customer_journey", context
    )
    for field, value in {
        "app_url": f"{PRODUCTION_APP_ORIGIN}/audit-console",
        "api_base_url": PRODUCTION_API_ORIGIN,
        "service_id": PRODUCTION_SERVICE_ID,
        "customer_lane": "public-customer",
    }.items():
        _require(_json_scalar_equals(evidence.get(field), value), f"{path}.{field}", f"must equal {value!r}", errors)
    _sha256(evidence.get("tenant_subject_sha256"), f"{path}.tenant_subject_sha256", errors)
    _sha256(evidence.get("account_subject_sha256"), f"{path}.account_subject_sha256", errors)
    audit = evidence.get("audit")
    audit_id: str | None = None
    if _is_mapping(audit, f"{path}.audit", errors):
        _exact_keys(audit, {"audit_id", "create_http_status", "terminal_status", "verdict", "model_id", "mode", "completed_at_utc"}, f"{path}.audit", errors)
        audit_id = audit.get("audit_id") if isinstance(audit.get("audit_id"), str) else None
        _require(audit_id is not None and AUDIT_ID_RE.fullmatch(audit_id) is not None, f"{path}.audit.audit_id", "must be a production audit ID", errors)
        _require(audit.get("create_http_status") in {200, 201}, f"{path}.audit.create_http_status", "must be 200 or 201", errors)
        _require(audit.get("terminal_status") == "completed", f"{path}.audit.terminal_status", "must be completed", errors)
        _require(audit.get("verdict") in RESEARCH_VERDICTS, f"{path}.audit.verdict", "must be an exact audit verdict", errors)
        _nonempty_string(audit.get("model_id"), f"{path}.audit.model_id", errors)
        _nonempty_string(audit.get("mode"), f"{path}.audit.mode", errors)
        _critical_proof_timestamp(audit.get("completed_at_utc"), gate="hosted_customer_journey", event=event, observed=observed, context=context, path=f"{path}.audit.completed_at_utc")
    packet = evidence.get("packet_download")
    if _is_mapping(packet, f"{path}.packet_download", errors):
        _exact_keys(packet, {"audit_id", "http_status", "content_type", "packet_sha256", "verification_overall", "worm_receipt_bound", "downloaded_at_utc"}, f"{path}.packet_download", errors)
        _require(packet.get("audit_id") == audit_id, f"{path}.packet_download.audit_id", "must match the audit", errors)
        _require(_json_scalar_equals(packet.get("http_status"), 200), f"{path}.packet_download.http_status", "must be 200", errors)
        _require(packet.get("content_type") == "application/json", f"{path}.packet_download.content_type", "must be application/json", errors)
        _sha256(packet.get("packet_sha256"), f"{path}.packet_download.packet_sha256", errors)
        _require(packet.get("verification_overall") == "all_match", f"{path}.packet_download.verification_overall", "must be all_match", errors)
        _require(packet.get("worm_receipt_bound") is True, f"{path}.packet_download.worm_receipt_bound", "must be true", errors)
        _critical_proof_timestamp(packet.get("downloaded_at_utc"), gate="hosted_customer_journey", event=event, observed=observed, context=context, path=f"{path}.packet_download.downloaded_at_utc")
    share = evidence.get("share")
    if _is_mapping(share, f"{path}.share", errors):
        _exact_keys(share, {"create_http_status", "anonymous_fetch_http_status", "scope", "share_token_sha256", "created_at_utc", "fetched_at_utc", "expires_at_utc", "revoke_http_status", "revoked_at_utc", "revoked_fetch_http_status"}, f"{path}.share", errors)
        _require(share.get("create_http_status") in {200, 201}, f"{path}.share.create_http_status", "must be 200 or 201", errors)
        _require(_json_scalar_equals(share.get("anonymous_fetch_http_status"), 200), f"{path}.share.anonymous_fetch_http_status", "must be 200", errors)
        _require(share.get("scope") == "read_only", f"{path}.share.scope", "must be read_only", errors)
        _sha256(share.get("share_token_sha256"), f"{path}.share.share_token_sha256", errors)
        created = _critical_proof_timestamp(share.get("created_at_utc"), gate="hosted_customer_journey", event=event, observed=observed, context=context, path=f"{path}.share.created_at_utc")
        fetched = _critical_proof_timestamp(share.get("fetched_at_utc"), gate="hosted_customer_journey", event=event, observed=observed, context=context, path=f"{path}.share.fetched_at_utc")
        revoked = _critical_proof_timestamp(share.get("revoked_at_utc"), gate="hosted_customer_journey", event=event, observed=observed, context=context, path=f"{path}.share.revoked_at_utc")
        expires = _timestamp(share.get("expires_at_utc"), f"{path}.share.expires_at_utc", errors)
        if created and fetched and revoked:
            _require(created <= fetched <= revoked, f"{path}.share.fetched_at_utc", "must be created, fetched, then revoked", errors)
        if created and expires:
            _require(expires > created, f"{path}.share.expires_at_utc", "must be after share creation", errors)
        _require(share.get("revoke_http_status") in {200, 204}, f"{path}.share.revoke_http_status", "must be 200 or 204", errors)
        _require(share.get("revoked_fetch_http_status") in {404, 410}, f"{path}.share.revoked_fetch_http_status", "must be 404 or 410", errors)
    isolation = evidence.get("tenant_isolation")
    if _is_mapping(isolation, f"{path}.tenant_isolation", errors):
        _exact_keys(isolation, {"foreign_audit_http_status", "foreign_packet_http_status", "verified_at_utc"}, f"{path}.tenant_isolation", errors)
        for field in ("foreign_audit_http_status", "foreign_packet_http_status"):
            _require(_json_scalar_equals(isolation.get(field), 404), f"{path}.tenant_isolation.{field}", "must be 404", errors)
        _critical_proof_timestamp(isolation.get("verified_at_utc"), gate="hosted_customer_journey", event=event, observed=observed, context=context, path=f"{path}.tenant_isolation.verified_at_utc")


def _validate_accounts_billing(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.accounts_billing.evidence.payload"
    errors = context.errors
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"api_base_url", "service_id", "customer_lane", "tenant_subject_sha256", "account_session", "quota", "billing"}, path, errors)
    event, observed = _validate_common_evidence(evidence, "accounts_billing", context)
    for field, value in {
        "api_base_url": PRODUCTION_API_ORIGIN,
        "service_id": PRODUCTION_SERVICE_ID,
        "customer_lane": "public-customer",
    }.items():
        _require(_json_scalar_equals(evidence.get(field), value), f"{path}.{field}", f"must equal {value!r}", errors)
    _sha256(evidence.get("tenant_subject_sha256"), f"{path}.tenant_subject_sha256", errors)
    session = evidence.get("account_session")
    if _is_mapping(session, f"{path}.account_session", errors):
        _exact_keys(session, {"invite_redeem_http_status", "login_http_status", "logout_http_status", "revoked_session_http_status", "durable_session_restart_verified", "disabled_account_http_status", "cross_tenant_http_status", "verified_at_utc"}, f"{path}.account_session", errors)
        expected = {
            "login_http_status": 200,
            "revoked_session_http_status": 401,
            "durable_session_restart_verified": True,
            # Authentication deliberately collapses unknown, bad-credential,
            # and disabled identities to the same non-enumerating 401.
            "disabled_account_http_status": 401,
            "cross_tenant_http_status": 404,
        }
        for field, value in expected.items():
            _require(_json_scalar_equals(session.get(field), value), f"{path}.account_session.{field}", f"must equal {value!r}", errors)
        _require(session.get("invite_redeem_http_status") in {200, 201}, f"{path}.account_session.invite_redeem_http_status", "must be 200 or 201", errors)
        _require(session.get("logout_http_status") in {200, 204}, f"{path}.account_session.logout_http_status", "must be 200 or 204", errors)
        _critical_proof_timestamp(session.get("verified_at_utc"), gate="accounts_billing", event=event, observed=observed, context=context, path=f"{path}.account_session.verified_at_utc")
    quota = evidence.get("quota")
    if _is_mapping(quota, f"{path}.quota", errors):
        _exact_keys(quota, {"monthly_limit", "usage_at_limit", "overflow_http_status", "overflow_error", "idempotent_retry_non_double_consuming", "adjacent_month_isolated", "shared_postgres_restart_verified", "verified_at_utc"}, f"{path}.quota", errors)
        limit = _positive_int(quota.get("monthly_limit"), f"{path}.quota.monthly_limit", errors)
        usage = _positive_int(quota.get("usage_at_limit"), f"{path}.quota.usage_at_limit", errors)
        if limit is not None and usage is not None:
            _require(limit == usage, f"{path}.quota.usage_at_limit", "must equal monthly_limit", errors)
        _require(_json_scalar_equals(quota.get("overflow_http_status"), 429), f"{path}.quota.overflow_http_status", "must be 429", errors)
        _require(quota.get("overflow_error") == "audit_quota_exceeded", f"{path}.quota.overflow_error", "must be audit_quota_exceeded", errors)
        for field in ("idempotent_retry_non_double_consuming", "adjacent_month_isolated", "shared_postgres_restart_verified"):
            _require(quota.get(field) is True, f"{path}.quota.{field}", "must be true", errors)
        _critical_proof_timestamp(quota.get("verified_at_utc"), gate="accounts_billing", event=event, observed=observed, context=context, path=f"{path}.quota.verified_at_utc")
    billing = evidence.get("billing")
    if _is_mapping(billing, f"{path}.billing", errors):
        _exact_keys(billing, {"provider", "mode", "currency", "checkout_status", "subscription_status", "invoice_status", "receipt_download_http_status", "webhook_signature_verified", "entitlement_status", "meter_to_invoice_reconciled", "provider_customer_id_sha256", "provider_subscription_id_sha256", "invoice_id_sha256", "paid_at_utc"}, f"{path}.billing", errors)
        expected = {
            "provider": "stripe",
            "mode": "live",
            "currency": "USD",
            "checkout_status": "complete",
            "subscription_status": "active",
            "invoice_status": "paid",
            "receipt_download_http_status": 200,
            "webhook_signature_verified": True,
            "entitlement_status": "active",
            "meter_to_invoice_reconciled": True,
        }
        for field, value in expected.items():
            _require(_json_scalar_equals(billing.get(field), value), f"{path}.billing.{field}", f"must equal {value!r}", errors)
        for field in ("provider_customer_id_sha256", "provider_subscription_id_sha256", "invoice_id_sha256"):
            _sha256(billing.get(field), f"{path}.billing.{field}", errors)
        _critical_proof_timestamp(billing.get("paid_at_utc"), gate="accounts_billing", event=event, observed=observed, context=context, path=f"{path}.billing.paid_at_utc")


def _validate_legal(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.legal_publication_approval.evidence.payload"
    errors = context.errors
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"public_base_url", "documents", "approvals", "claim_status_vocabulary"}, path, errors)
    event, observed = _validate_common_evidence(evidence, "legal_publication_approval", context)
    _require(evidence.get("public_base_url") == LANDING_ORIGIN, f"{path}.public_base_url", f"must be {LANDING_ORIGIN}", errors)
    documents = _list_by_key(evidence.get("documents"), "kind", LEGAL_DOCUMENT_KINDS, f"{path}.documents", errors)
    for kind, document in documents.items():
        item_path = f"{path}.documents[{kind}]"
        _exact_keys(document, {"kind", "url", "http_status", "content_sha256", "published_at_utc", "verified_at_utc"}, item_path, errors)
        _require(document.get("url") == f"{LANDING_ORIGIN}/{kind}", f"{item_path}.url", f"must be {LANDING_ORIGIN}/{kind}", errors)
        _require(_json_scalar_equals(document.get("http_status"), 200), f"{item_path}.http_status", "must be 200", errors)
        _sha256(document.get("content_sha256"), f"{item_path}.content_sha256", errors)
        published = _critical_proof_timestamp(document.get("published_at_utc"), gate="legal_publication_approval", event=event, observed=observed, context=context, path=f"{item_path}.published_at_utc")
        verified = _critical_proof_timestamp(document.get("verified_at_utc"), gate="legal_publication_approval", event=event, observed=observed, context=context, path=f"{item_path}.verified_at_utc")
        if published and verified:
            _require(published <= verified, f"{item_path}.verified_at_utc", "must be after publication", errors)
    approvals = _list_by_key(evidence.get("approvals"), "role", LEGAL_APPROVER_ROLES, f"{path}.approvals", errors)
    for role, approval in approvals.items():
        item_path = f"{path}.approvals[{role}]"
        _exact_keys(approval, {"role", "approval_artifact_uri", "approval_sha256", "approved_at_utc"}, item_path, errors)
        _safe_https_url(approval.get("approval_artifact_uri"), f"{item_path}.approval_artifact_uri", errors, allowed_origins={LANDING_ORIGIN, PRODUCTION_API_ORIGIN})
        _sha256(approval.get("approval_sha256"), f"{item_path}.approval_sha256", errors)
        _critical_proof_timestamp(approval.get("approved_at_utc"), gate="legal_publication_approval", event=event, observed=observed, context=context, path=f"{item_path}.approved_at_utc")
    _require(evidence.get("claim_status_vocabulary") == list(CLAIM_STATUS_VOCABULARY), f"{path}.claim_status_vocabulary", "must preserve exact claim vocabulary and casing", errors)


def _validate_support_crm(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.support_crm.evidence.payload"
    errors = context.errors
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"public_support_url", "api_base_url", "service_id", "support_ticket", "crm_lead", "consent"}, path, errors)
    event, observed = _validate_common_evidence(evidence, "support_crm", context)
    _require(evidence.get("public_support_url") == f"{LANDING_ORIGIN}/contact", f"{path}.public_support_url", f"must be {LANDING_ORIGIN}/contact", errors)
    _require(evidence.get("api_base_url") == PRODUCTION_API_ORIGIN, f"{path}.api_base_url", f"must be {PRODUCTION_API_ORIGIN}", errors)
    _require(evidence.get("service_id") == PRODUCTION_SERVICE_ID, f"{path}.service_id", "must be the public production service", errors)
    ticket = evidence.get("support_ticket")
    if _is_mapping(ticket, f"{path}.support_ticket", errors):
        _exact_keys(ticket, {"ticket_id_sha256", "create_http_status", "persisted", "routed", "acknowledged", "first_response_minutes", "sla_minutes", "resolution_recorded", "resolved_at_utc"}, f"{path}.support_ticket", errors)
        _sha256(ticket.get("ticket_id_sha256"), f"{path}.support_ticket.ticket_id_sha256", errors)
        _require(ticket.get("create_http_status") in {200, 201, 202}, f"{path}.support_ticket.create_http_status", "must be 200, 201, or 202", errors)
        for field in ("persisted", "routed", "acknowledged", "resolution_recorded"):
            _require(ticket.get(field) is True, f"{path}.support_ticket.{field}", "must be true", errors)
        response = _nonnegative_int(ticket.get("first_response_minutes"), f"{path}.support_ticket.first_response_minutes", errors)
        sla = _positive_int(ticket.get("sla_minutes"), f"{path}.support_ticket.sla_minutes", errors)
        if response is not None and sla is not None:
            _require(response <= sla, f"{path}.support_ticket.first_response_minutes", "must be within SLA", errors)
        _critical_proof_timestamp(ticket.get("resolved_at_utc"), gate="support_crm", event=event, observed=observed, context=context, path=f"{path}.support_ticket.resolved_at_utc")
    lead = evidence.get("crm_lead")
    lead_verified: datetime | None = None
    if _is_mapping(lead, f"{path}.crm_lead", errors):
        _exact_keys(lead, {"system", "provider", "lead_id_sha256", "airtable_record_id_sha256", "adapter_response_digest", "source_receipt_sha256", "persisted", "readback_verified", "deduplicated", "owner_assigned", "lifecycle_stage", "verified_at_utc"}, f"{path}.crm_lead", errors)
        _require(lead.get("system") == "airtable", f"{path}.crm_lead.system", "must be exact airtable", errors)
        _require(lead.get("provider") == "airtable", f"{path}.crm_lead.provider", "must be exact airtable", errors)
        _sha256(lead.get("lead_id_sha256"), f"{path}.crm_lead.lead_id_sha256", errors)
        _sha256(lead.get("airtable_record_id_sha256"), f"{path}.crm_lead.airtable_record_id_sha256", errors)
        _tagged_sha256(lead.get("adapter_response_digest"), f"{path}.crm_lead.adapter_response_digest", errors)
        _sha256(lead.get("source_receipt_sha256"), f"{path}.crm_lead.source_receipt_sha256", errors)
        for field in ("persisted", "readback_verified", "deduplicated", "owner_assigned"):
            _require(lead.get(field) is True, f"{path}.crm_lead.{field}", "must be true", errors)
        _require(lead.get("lifecycle_stage") in {"new", "contacted", "qualified", "won", "lost"}, f"{path}.crm_lead.lifecycle_stage", "must be an exact canonical CRM lifecycle stage", errors)
        lead_verified = _critical_proof_timestamp(lead.get("verified_at_utc"), gate="support_crm", event=event, observed=observed, context=context, path=f"{path}.crm_lead.verified_at_utc")
    consent = evidence.get("consent")
    if _is_mapping(consent, f"{path}.consent", errors):
        _exact_keys(consent, {"capture_consent_recorded", "consent_to_contact", "source_attribution_recorded", "privacy_notice_linked", "privacy_notice_url", "privacy_notice_version", "consent_schema_version", "recorded_at_utc"}, f"{path}.consent", errors)
        for field in ("capture_consent_recorded", "consent_to_contact", "source_attribution_recorded", "privacy_notice_linked"):
            _require(consent.get(field) is True, f"{path}.consent.{field}", "must be true", errors)
        _require(consent.get("privacy_notice_url") == f"{LANDING_ORIGIN}/privacy", f"{path}.consent.privacy_notice_url", f"must be {LANDING_ORIGIN}/privacy", errors)
        _require(isinstance(consent.get("privacy_notice_version"), str) and PRIVACY_NOTICE_VERSION_RE.fullmatch(str(consent.get("privacy_notice_version"))) is not None, f"{path}.consent.privacy_notice_version", "must be an exact privacy notice version identifier", errors)
        _require(consent.get("consent_schema_version") == "noetic_crm_consent.v1", f"{path}.consent.consent_schema_version", "must be exact noetic_crm_consent.v1", errors)
        consent_recorded = _critical_proof_timestamp(consent.get("recorded_at_utc"), gate="support_crm", event=event, observed=observed, context=context, path=f"{path}.consent.recorded_at_utc")
        if consent_recorded is not None and lead_verified is not None:
            _require(consent_recorded <= lead_verified, f"{path}.consent.recorded_at_utc", "must be at or before Airtable readback verification", errors)


def _validate_incident_tabletop(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.incident_tabletop.evidence.payload"
    errors = context.errors
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"api_base_url", "service_id", "incident", "tabletop"}, path, errors)
    event, observed = _validate_common_evidence(evidence, "incident_tabletop", context)
    _require(evidence.get("api_base_url") == PRODUCTION_API_ORIGIN, f"{path}.api_base_url", f"must be {PRODUCTION_API_ORIGIN}", errors)
    _require(evidence.get("service_id") == PRODUCTION_SERVICE_ID, f"{path}.service_id", "must be the public production service", errors)
    incident = evidence.get("incident")
    if _is_mapping(incident, f"{path}.incident", errors):
        _exact_keys(incident, {"record_id", "status", "closed_at_utc", "open_actions", "postmortem_uri", "postmortem_sha256", "credential_rotation_complete", "recovery_verified"}, f"{path}.incident", errors)
        _require(isinstance(incident.get("record_id"), str) and INCIDENT_ID_RE.fullmatch(str(incident.get("record_id"))) is not None, f"{path}.incident.record_id", "must match IR-YYYY-MM-DD-NNN", errors)
        _require(incident.get("status") == "CLOSED", f"{path}.incident.status", "must be CLOSED", errors)
        _critical_proof_timestamp(incident.get("closed_at_utc"), gate="incident_tabletop", event=event, observed=observed, context=context, path=f"{path}.incident.closed_at_utc")
        _require(_json_scalar_equals(incident.get("open_actions"), 0), f"{path}.incident.open_actions", "must be zero", errors)
        _safe_https_url(incident.get("postmortem_uri"), f"{path}.incident.postmortem_uri", errors, allowed_origins={PRODUCTION_API_ORIGIN})
        _sha256(incident.get("postmortem_sha256"), f"{path}.incident.postmortem_sha256", errors)
        for field in ("credential_rotation_complete", "recovery_verified"):
            _require(incident.get(field) is True, f"{path}.incident.{field}", "must be true", errors)
    tabletop = evidence.get("tabletop")
    if _is_mapping(tabletop, f"{path}.tabletop", errors):
        _exact_keys(tabletop, {"tabletop_id", "completed_at_utc", "participant_roles", "scenarios", "open_actions", "evidence_uri", "evidence_sha256"}, f"{path}.tabletop", errors)
        _require(isinstance(tabletop.get("tabletop_id"), str) and PROBE_ID_RE.fullmatch(str(tabletop.get("tabletop_id"))) is not None, f"{path}.tabletop.tabletop_id", "must be a non-secret tabletop ID", errors)
        _critical_proof_timestamp(tabletop.get("completed_at_utc"), gate="incident_tabletop", event=event, observed=observed, context=context, path=f"{path}.tabletop.completed_at_utc")
        _set_of_strings(tabletop.get("participant_roles"), TABLETOP_ROLES, f"{path}.tabletop.participant_roles", errors)
        _set_of_strings(tabletop.get("scenarios"), TABLETOP_SCENARIOS, f"{path}.tabletop.scenarios", errors)
        _require(_json_scalar_equals(tabletop.get("open_actions"), 0), f"{path}.tabletop.open_actions", "must be zero", errors)
        _safe_https_url(tabletop.get("evidence_uri"), f"{path}.tabletop.evidence_uri", errors, allowed_origins={PRODUCTION_API_ORIGIN})
        _sha256(tabletop.get("evidence_sha256"), f"{path}.tabletop.evidence_sha256", errors)


def _validate_alert_delivery(
    evidence: Mapping[str, Any], context: ValidationContext
) -> None:
    path = "$.required_gates.alert_delivery.evidence.payload"
    errors = context.errors
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"api_base_url", "service_id", "alert", "deliveries", "acknowledgement", "escalation"}, path, errors)
    event, observed = _validate_common_evidence(evidence, "alert_delivery", context)
    _require(evidence.get("api_base_url") == PRODUCTION_API_ORIGIN, f"{path}.api_base_url", f"must be {PRODUCTION_API_ORIGIN}", errors)
    _require(evidence.get("service_id") == PRODUCTION_SERVICE_ID, f"{path}.service_id", "must be the public production service", errors)
    alert = evidence.get("alert")
    emitted: datetime | None = None
    if _is_mapping(alert, f"{path}.alert", errors):
        _exact_keys(alert, {"alert_id_sha256", "severity", "emitted_at_utc", "source"}, f"{path}.alert", errors)
        _sha256(alert.get("alert_id_sha256"), f"{path}.alert.alert_id_sha256", errors)
        _require(alert.get("severity") == "P1", f"{path}.alert.severity", "must be P1", errors)
        emitted = _critical_proof_timestamp(alert.get("emitted_at_utc"), gate="alert_delivery", event=event, observed=observed, context=context, path=f"{path}.alert.emitted_at_utc")
        _nonempty_string(alert.get("source"), f"{path}.alert.source", errors)
    deliveries = _list_by_key(evidence.get("deliveries"), "destination_role", ALERT_DESTINATIONS, f"{path}.deliveries", errors)
    for role, delivery in deliveries.items():
        item_path = f"{path}.deliveries[{role}]"
        _exact_keys(delivery, {"destination_role", "status", "delivered_at_utc", "receipt_sha256"}, item_path, errors)
        _require(delivery.get("status") == "delivered", f"{item_path}.status", "must be delivered", errors)
        delivered = _critical_proof_timestamp(delivery.get("delivered_at_utc"), gate="alert_delivery", event=event, observed=observed, context=context, path=f"{item_path}.delivered_at_utc")
        if delivered and emitted:
            _require(delivered >= emitted, f"{item_path}.delivered_at_utc", "must not precede alert emission", errors)
        _sha256(delivery.get("receipt_sha256"), f"{item_path}.receipt_sha256", errors)
    acknowledgement = evidence.get("acknowledgement")
    if _is_mapping(acknowledgement, f"{path}.acknowledgement", errors):
        _exact_keys(acknowledgement, {"status", "acknowledged_at_utc", "actor_role", "latency_seconds"}, f"{path}.acknowledgement", errors)
        _require(acknowledgement.get("status") == "acknowledged", f"{path}.acknowledgement.status", "must be acknowledged", errors)
        acknowledged = _critical_proof_timestamp(acknowledgement.get("acknowledged_at_utc"), gate="alert_delivery", event=event, observed=observed, context=context, path=f"{path}.acknowledgement.acknowledged_at_utc")
        if acknowledged and emitted:
            _require(acknowledged >= emitted, f"{path}.acknowledgement.acknowledged_at_utc", "must not precede alert emission", errors)
        _require(acknowledgement.get("actor_role") == "incident_commander", f"{path}.acknowledgement.actor_role", "must be incident_commander", errors)
        latency = _nonnegative_int(acknowledgement.get("latency_seconds"), f"{path}.acknowledgement.latency_seconds", errors)
        if latency is not None:
            _require(latency <= 600, f"{path}.acknowledgement.latency_seconds", "must be at most 600 seconds", errors)
        if latency is not None and acknowledged is not None and emitted is not None:
            actual_latency = int((acknowledged - emitted).total_seconds())
            _require(
                actual_latency == latency,
                f"{path}.acknowledgement.latency_seconds",
                "must equal the actual acknowledgement clock delta",
                errors,
            )
            _require(
                actual_latency <= 600,
                f"{path}.acknowledgement.acknowledged_at_utc",
                "actual acknowledgement must be within 600 seconds",
                errors,
            )
    escalation = evidence.get("escalation")
    if _is_mapping(escalation, f"{path}.escalation", errors):
        _exact_keys(escalation, {"triggered", "delivered", "destination_role", "receipt_sha256", "delivered_at_utc"}, f"{path}.escalation", errors)
        _require(escalation.get("triggered") is True, f"{path}.escalation.triggered", "must be true", errors)
        _require(escalation.get("delivered") is True, f"{path}.escalation.delivered", "must be true", errors)
        _require(escalation.get("destination_role") == "secondary_on_call", f"{path}.escalation.destination_role", "must be secondary_on_call", errors)
        _sha256(escalation.get("receipt_sha256"), f"{path}.escalation.receipt_sha256", errors)
        escalated = _critical_proof_timestamp(escalation.get("delivered_at_utc"), gate="alert_delivery", event=event, observed=observed, context=context, path=f"{path}.escalation.delivered_at_utc")
        if escalated is not None and emitted is not None:
            _require(
                escalated >= emitted,
                f"{path}.escalation.delivered_at_utc",
                "must not precede alert emission",
                errors,
            )


def _validate_claim_honesty(
    evidence: Mapping[str, Any], context: ValidationContext, product_status: Any
) -> None:
    path = "$.required_gates.claim_honesty.evidence.payload"
    errors = context.errors
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"scanned_surfaces", "scan", "boundaries", "approvals"}, path, errors)
    event, observed = _validate_common_evidence(evidence, "claim_honesty", context)
    surfaces = _list_by_key(evidence.get("scanned_surfaces"), "kind", CLAIM_SURFACE_KINDS, f"{path}.scanned_surfaces", errors)
    expected_urls = {
        "product_app": PRODUCTION_APP_ORIGIN,
        "audit_console": f"{PRODUCTION_APP_ORIGIN}/audit-console",
        "landing": LANDING_ORIGIN,
        "legal": f"{LANDING_ORIGIN}/legal",
        "privacy": f"{LANDING_ORIGIN}/privacy",
        "terms": f"{LANDING_ORIGIN}/terms",
    }
    for kind, surface in surfaces.items():
        item_path = f"{path}.scanned_surfaces[{kind}]"
        _exact_keys(surface, {"kind", "url", "http_status", "content_sha256", "verified_at_utc"}, item_path, errors)
        _require(surface.get("url") == expected_urls[kind], f"{item_path}.url", f"must equal {expected_urls[kind]!r}", errors)
        _require(_json_scalar_equals(surface.get("http_status"), 200), f"{item_path}.http_status", "must be 200", errors)
        _sha256(surface.get("content_sha256"), f"{item_path}.content_sha256", errors)
        _critical_proof_timestamp(surface.get("verified_at_utc"), gate="claim_honesty", event=event, observed=observed, context=context, path=f"{item_path}.verified_at_utc")
    scan = evidence.get("scan")
    if _is_mapping(scan, f"{path}.scan", errors):
        _exact_keys(scan, {"misleading_claim_count", "unsupported_compliance_claim_count", "unsupported_universality_claim_count", "status_vocabulary_exact"}, f"{path}.scan", errors)
        for field in ("misleading_claim_count", "unsupported_compliance_claim_count", "unsupported_universality_claim_count"):
            _require(_json_scalar_equals(scan.get(field), 0), f"{path}.scan.{field}", "must be zero", errors)
        _require(scan.get("status_vocabulary_exact") is True, f"{path}.scan.status_vocabulary_exact", "must be true", errors)
    boundaries = evidence.get("boundaries")
    if _is_mapping(boundaries, f"{path}.boundaries", errors):
        _exact_keys(boundaries, {"research_scope_disclosed", "research_accept_not_product_accept", "worm_retention_not_verdict_upgrade", "flag_for_human_review_not_accept", "compliance_certification_claims_absent", "rendered_product_status"}, f"{path}.boundaries", errors)
        for field in ("research_scope_disclosed", "research_accept_not_product_accept", "worm_retention_not_verdict_upgrade", "flag_for_human_review_not_accept", "compliance_certification_claims_absent"):
            _require(boundaries.get(field) is True, f"{path}.boundaries.{field}", "must be true", errors)
        _require(boundaries.get("rendered_product_status") == product_status, f"{path}.boundaries.rendered_product_status", "must match the declared product status", errors)
    approvals = _list_by_key(evidence.get("approvals"), "role", CLAIM_APPROVER_ROLES, f"{path}.approvals", errors)
    for role, approval in approvals.items():
        item_path = f"{path}.approvals[{role}]"
        _exact_keys(approval, {"role", "approval_artifact_uri", "approval_sha256", "approved_at_utc"}, item_path, errors)
        _safe_https_url(approval.get("approval_artifact_uri"), f"{item_path}.approval_artifact_uri", errors, allowed_origins={PRODUCTION_API_ORIGIN, LANDING_ORIGIN})
        _sha256(approval.get("approval_sha256"), f"{item_path}.approval_sha256", errors)
        _critical_proof_timestamp(approval.get("approved_at_utc"), gate="claim_honesty", event=event, observed=observed, context=context, path=f"{item_path}.approved_at_utc")


GateValidator = Callable[[Mapping[str, Any], ValidationContext], None]
GATE_VALIDATORS: dict[str, GateValidator] = {
    "runtime_worm": _validate_runtime_worm,
    "root_ci_protected_deploy": _validate_root_ci,
    "hosted_customer_journey": _validate_hosted_customer,
    "accounts_billing": _validate_accounts_billing,
    "legal_publication_approval": _validate_legal,
    "support_crm": _validate_support_crm,
    "incident_tabletop": _validate_incident_tabletop,
    "alert_delivery": _validate_alert_delivery,
}


def _find_prohibited_fields(
    value: Any,
    path: str = "$",
    *,
    include_pii: bool = False,
) -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            normalized = str(key).lower()
            if normalized in PROHIBITED_SECRET_FIELD_NAMES:
                errors.append(f"{child_path}: raw-secret field is prohibited")
            if include_pii and normalized in PROHIBITED_PII_FIELD_NAMES:
                errors.append(f"{child_path}: raw-PII field is prohibited")
            errors.extend(
                _find_prohibited_fields(
                    child,
                    child_path,
                    include_pii=include_pii,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(
                _find_prohibited_fields(
                    child,
                    f"{path}[{index}]",
                    include_pii=include_pii,
                )
            )
    return errors


def _scan_secret_shapes(value: Mapping[str, Any], source: str = "$") -> list[str]:
    serialized = json.dumps(value, sort_keys=True)
    errors: list[str] = []
    for label, pattern in SUSPICIOUS_SECRET_PATTERNS.items():
        if pattern.search(serialized):
            errors.append(
                f"{source}: possible {label} is prohibited; store only a SHA-256 digest"
            )
    return errors


def _validate_research_boundary(
    boundary: Mapping[str, Any], repo_root: Path, errors: list[str]
) -> str | None:
    path = "$.claim_boundary"
    _exact_keys(
        boundary,
        {
            "research_verdict",
            "research_accept_does_not_imply_customer_production_accept",
            "product_accept_requires_all_gates_present",
            "evidence_status_meaning",
        },
        path,
        errors,
    )
    _require(boundary.get("research_accept_does_not_imply_customer_production_accept") is True, f"{path}.research_accept_does_not_imply_customer_production_accept", "must be true", errors)
    _require(boundary.get("product_accept_requires_all_gates_present") is True, f"{path}.product_accept_requires_all_gates_present", "must be true", errors)
    _require(boundary.get("evidence_status_meaning") == STATUS_MEANING, f"{path}.evidence_status_meaning", "must preserve exact OPEN/present meanings", errors)
    research = boundary.get("research_verdict")
    if not _is_mapping(research, f"{path}.research_verdict", errors):
        return None
    _exact_keys(research, {"verdict", "scope", "artifact_path", "artifact_sha256", "customer_production_effect"}, f"{path}.research_verdict", errors)
    _require(research.get("verdict") == "ACCEPT", f"{path}.research_verdict.verdict", "must preserve the scoped research ACCEPT", errors)
    scope = _nonempty_string(research.get("scope"), f"{path}.research_verdict.scope", errors)
    _require(research.get("customer_production_effect") == "none", f"{path}.research_verdict.customer_production_effect", "must be none", errors)
    expected_hash = _sha256(research.get("artifact_sha256"), f"{path}.research_verdict.artifact_sha256", errors)
    relative = research.get("artifact_path")
    if not isinstance(relative, str) or not relative:
        _error(errors, f"{path}.research_verdict.artifact_path", "must be repository-relative")
        return expected_hash
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        _error(errors, f"{path}.research_verdict.artifact_path", "must stay within the repository")
        return expected_hash
    try:
        raw = _read_bounded(candidate, relative)
        payload = _loads_json(raw, relative)
    except ManifestLoadError as exc:
        _error(errors, f"{path}.research_verdict.artifact_path", str(exc))
        return expected_hash
    actual_hash = _repository_text_sha256(raw)
    if expected_hash is not None:
        _require(actual_hash == expected_hash, f"{path}.research_verdict.artifact_sha256", "does not match the dereferenced research artifact", errors)
    decision = payload.get("explicit_verifier_decision")
    if not _is_mapping(decision, f"{path}.research_verdict.artifact_path", errors):
        return expected_hash
    _require(decision.get("verdict") == "ACCEPT", f"{path}.research_verdict.artifact_path", "artifact verdict must be ACCEPT", errors)
    if scope is not None:
        _require(decision.get("decision_scope") == scope, f"{path}.research_verdict.scope", "must match artifact decision scope", errors)
    return expected_hash


def _validate_workflow_separation(repo_root: Path, errors: list[str]) -> None:
    ci_path = repo_root / ".github/workflows/ci.yml"
    accept_path = repo_root / ".github/workflows/customer-production-accept.yml"
    if not ci_path.is_file():
        _error(errors, "$.repository_contract", "root CAS CI workflow is missing")
        return
    if not accept_path.is_file():
        _error(errors, "$.repository_contract", "separate customer-production ACCEPT workflow is missing")
        return
    ci_text = ci_path.read_text(encoding="utf-8")
    accept_text = accept_path.read_text(encoding="utf-8")
    _require("Validate customer-production contract (OPEN permitted)" in ci_text, "$.repository_contract.ci", "must clearly label OPEN-permitted contract validation", errors)
    _require("python scripts/verify_customer_production_acceptance.py --validate-only" in ci_text, "$.repository_contract.ci", "must run only --validate-only in ordinary CI", errors)
    gate_marker = "  required_gate:"
    gate_block = ci_text.split(gate_marker, 1)[1] if gate_marker in ci_text else ""
    _require("customer-production-accept" not in gate_block and "customer_production_accept" not in gate_block, "$.repository_contract.ci", "cas-ci-gate must not aggregate customer-production ACCEPT", errors)
    for required in (
        "name: Customer Production ACCEPT",
        "workflow_dispatch:",
        "evidence_run_id:",
        "evidence_artifact_name:",
        "expected_master_head:",
        "expected_deploy_id:",
        "customer_production_accept:",
        "name: customer-production-accept",
        "Fail closed unless dispatched from protected master in the exact repository",
        'test "$DISPATCH_REF" = "refs/heads/master"',
        'test "$DISPATCH_REF_PROTECTED" = "true"',
        "python scripts/verify_customer_production_acceptance.py",
        "--expected-master-head",
        "--expected-deploy-id",
        "--evidence-root",
        "--sanitized-bundle-path",
        "path: customer-production-archive",
        "include-hidden-files: true",
    ):
        _require(required in accept_text, "$.repository_contract.customer_production_accept", f"missing required workflow binding: {required}", errors)
    normal_lines = [line.strip() for line in accept_text.splitlines() if "python scripts/verify_customer_production_acceptance.py" in line]
    _require(bool(normal_lines) and all("--validate-only" not in line for line in normal_lines), "$.repository_contract.customer_production_accept", "must run the normal fail-closed verifier, not --validate-only", errors)
    accept_job_marker = "  customer_production_accept:"
    accept_job_block = (
        accept_text.split(accept_job_marker, 1)[1]
        if accept_job_marker in accept_text
        else ""
    )
    _require(
        not any(line.startswith("    if:") for line in accept_job_block.splitlines()),
        "$.repository_contract.customer_production_accept",
        "job-level repository/ref conditions can skip green; use a fail-closed preflight step",
        errors,
    )


def _validate_product_shell(
    product: Mapping[str, Any], errors: list[str]
) -> tuple[str | None, Mapping[str, Any] | None]:
    path = "$.product"
    _exact_keys(product, {"name", "environment", "status", "status_reason", "release_decision"}, path, errors)
    _require(product.get("name") == "CAS Harness", f"{path}.name", "must be CAS Harness", errors)
    _require(product.get("environment") == "public-production", f"{path}.environment", "must be public-production", errors)
    status = product.get("status")
    _require(status in PRODUCT_STATUSES, f"{path}.status", "must be exact OPEN or ACCEPT", errors)
    _nonempty_string(product.get("status_reason"), f"{path}.status_reason", errors)
    decision = product.get("release_decision")
    if not _is_mapping(decision, f"{path}.release_decision", errors):
        return status if isinstance(status, str) else None, None
    _exact_keys(decision, {"status", "evidence"}, f"{path}.release_decision", errors)
    _require(decision.get("status") in PRODUCT_STATUSES, f"{path}.release_decision.status", "must be exact OPEN or ACCEPT", errors)
    _require(decision.get("status") == status, f"{path}.release_decision.status", "must match product.status", errors)
    if decision.get("status") == "OPEN":
        _require(decision.get("evidence") is None, f"{path}.release_decision.evidence", "must be null while OPEN", errors)
    elif decision.get("status") == "ACCEPT":
        _is_mapping(decision.get("evidence"), f"{path}.release_decision.evidence", errors)
    return status if isinstance(status, str) else None, decision


def _validate_release_decision(
    reference: Mapping[str, Any], context: ValidationContext, newest_gate_observed: datetime
) -> None:
    evidence = _resolve_authoritative_evidence(reference, "release_decision", context)
    if evidence is None:
        return
    path = "$.product.release_decision.evidence.payload"
    _exact_keys(evidence, COMMON_EVIDENCE_KEYS | {"status", "approved_at_utc", "approver_roles", "decision_record_uri", "decision_record_sha256"}, path, context.errors)
    event, observed = _validate_common_evidence(
        evidence, "release_decision", context
    )
    _require(evidence.get("status") == "ACCEPT", f"{path}.status", "must be ACCEPT", context.errors)
    approved = _critical_proof_timestamp(
        evidence.get("approved_at_utc"),
        gate="release_decision",
        event=event,
        observed=observed,
        context=context,
        path=f"{path}.approved_at_utc",
    )
    if approved is not None:
        _require(approved >= newest_gate_observed, f"{path}.approved_at_utc", "must be at or after the newest gate evidence", context.errors)
    _set_of_strings(evidence.get("approver_roles"), RELEASE_APPROVER_ROLES, f"{path}.approver_roles", context.errors)
    _safe_https_url(evidence.get("decision_record_uri"), f"{path}.decision_record_uri", context.errors, allowed_origins={PRODUCTION_API_ORIGIN})
    _sha256(evidence.get("decision_record_sha256"), f"{path}.decision_record_sha256", context.errors)


def _cross_validate(
    gate_payloads: Mapping[str, Mapping[str, Any]], context: ValidationContext
) -> None:
    errors = context.errors
    runtime = gate_payloads.get("runtime_worm")
    ci = gate_payloads.get("root_ci_protected_deploy")
    if runtime and ci and isinstance(runtime.get("deployment"), Mapping) and isinstance(ci.get("deployment"), Mapping):
        _require(runtime["deployment"].get("commit_sha") == ci["deployment"].get("commit_sha"), "$.required_gates.runtime_worm.evidence.payload.deployment.commit_sha", "must match protected deploy evidence", errors)
        _require(runtime["deployment"].get("deploy_id") == ci["deployment"].get("deploy_id"), "$.required_gates.runtime_worm.evidence.payload.deployment.deploy_id", "must match protected deploy evidence", errors)
    legal = gate_payloads.get("legal_publication_approval")
    honesty = gate_payloads.get("claim_honesty")
    if legal and honesty and isinstance(legal.get("documents"), list) and isinstance(honesty.get("scanned_surfaces"), list):
        docs = {item.get("kind"): item.get("content_sha256") for item in legal["documents"] if isinstance(item, Mapping)}
        surfaces = {item.get("kind"): item.get("content_sha256") for item in honesty["scanned_surfaces"] if isinstance(item, Mapping)}
        for kind in LEGAL_DOCUMENT_KINDS:
            _require(docs.get(kind) == surfaces.get(kind), f"$.required_gates.claim_honesty.evidence.payload.scanned_surfaces[{kind}].content_sha256", "must match the authoritative legal publication hash", errors)
    hashes = [context.evidence_hashes.get(gate) for gate in REQUIRED_GATES if context.evidence_hashes.get(gate)]
    _require(len(hashes) == len(set(hashes)), "$.required_gates", "each gate must have a distinct authoritative evidence receipt", errors)


def verify_manifest(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    evidence_root: Path | None = None,
    verification_time: datetime | None = None,
    expected_master_head: str | None = None,
    expected_deploy_id: str | None = None,
    repository_commit: str | None = None,
    live: bool = False,
    trusted_issuers: dict[tuple[str, str], dict[str, Any]] | None = None,
    registry_sha256: str | None = None,
    manifest_raw: bytes | None = None,
    resolved_documents: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    verification_time = (verification_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
    evidence_root = (evidence_root or repo_root).resolve()
    errors: list[str] = []
    _exact_keys(manifest, {"schema_version", "manifest_id", "generated_at_utc", "product", "claim_boundary", "authority_policy", "freshness_policy", "required_gates"}, "$", errors)
    _require(manifest.get("schema_version") == SCHEMA_VERSION, "$.schema_version", f"must be {SCHEMA_VERSION}", errors)
    _require(manifest.get("manifest_id") == MANIFEST_ID, "$.manifest_id", f"must be {MANIFEST_ID}", errors)
    generated = _timestamp(manifest.get("generated_at_utc"), "$.generated_at_utc", errors)
    if generated is not None:
        _require(generated <= verification_time, "$.generated_at_utc", "must be at or before verification", errors)
    authority_policy = manifest.get("authority_policy")
    if _is_mapping(authority_policy, "$.authority_policy", errors):
        _exact_keys(authority_policy, set(AUTHORITY_POLICY), "$.authority_policy", errors)
        _require(dict(authority_policy) == AUTHORITY_POLICY, "$.authority_policy", "must preserve the authoritative-only policy", errors)
    freshness = manifest.get("freshness_policy")
    if _is_mapping(freshness, "$.freshness_policy", errors):
        _exact_keys(freshness, set(FRESHNESS_POLICY), "$.freshness_policy", errors)
        _require(dict(freshness) == FRESHNESS_POLICY, "$.freshness_policy", "must not weaken fixed freshness or WORM policy", errors)
    product_status: str | None = None
    release_decision: Mapping[str, Any] | None = None
    product = manifest.get("product")
    if _is_mapping(product, "$.product", errors):
        product_status, release_decision = _validate_product_shell(product, errors)
    research_hash: str | None = None
    boundary = manifest.get("claim_boundary")
    if _is_mapping(boundary, "$.claim_boundary", errors):
        research_hash = _validate_research_boundary(boundary, repo_root.resolve(), errors)
    _validate_workflow_separation(repo_root.resolve(), errors)
    if trusted_issuers is None:
        try:
            trusted_issuers, loaded_registry_hash = _load_trusted_issuer_registry(repo_root.resolve())
            registry_sha256 = registry_sha256 or loaded_registry_hash
        except ManifestLoadError as exc:
            errors.append(str(exc))
            trusted_issuers = {}
            registry_sha256 = registry_sha256 or ("0" * 64)
    context = ValidationContext(
        repo_root=repo_root.resolve(),
        evidence_root=evidence_root,
        verification_time=verification_time,
        generated_at=generated,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        repository_commit=repository_commit,
        live=live,
        trusted_issuers=trusted_issuers,
        registry_sha256=registry_sha256 or ("0" * 64),
        errors=errors,
        resolved_documents=(
            resolved_documents if resolved_documents is not None else {}
        ),
    )
    open_gates: list[str] = []
    gate_payloads: dict[str, Mapping[str, Any]] = {}
    gates = manifest.get("required_gates")
    if _is_mapping(gates, "$.required_gates", errors):
        _exact_keys(gates, set(REQUIRED_GATES), "$.required_gates", errors)
        any_present = any(isinstance(gates.get(gate), Mapping) and gates[gate].get("status") == "present" for gate in REQUIRED_GATES)
        if any_present:
            _require(expected_master_head is not None and SHA1_RE.fullmatch(expected_master_head or "") is not None, "$.verification.expected_master_head", "is required for any present evidence", errors)
            _require(isinstance(expected_deploy_id, str) and expected_deploy_id.startswith("dep-"), "$.verification.expected_deploy_id", "is required for any present evidence", errors)
        for gate in REQUIRED_GATES:
            gate_path = f"$.required_gates.{gate}"
            entry = gates.get(gate)
            if not _is_mapping(entry, gate_path, errors):
                open_gates.append(gate)
                continue
            _exact_keys(entry, {"status", "evidence"}, gate_path, errors)
            status = entry.get("status")
            _require(status in EVIDENCE_STATUSES, f"{gate_path}.status", "must be exact OPEN or present", errors)
            if status == "OPEN":
                open_gates.append(gate)
                _require(entry.get("evidence") is None, f"{gate_path}.evidence", "must be null while OPEN", errors)
                continue
            reference = entry.get("evidence")
            if not _is_mapping(reference, f"{gate_path}.evidence", errors):
                open_gates.append(gate)
                continue
            if research_hash is not None:
                _require(
                    reference.get("sha256") != research_hash,
                    f"{gate_path}.evidence.sha256",
                    "must not reuse the scoped research ACCEPT artifact",
                    errors,
                )
            payload = _resolve_authoritative_evidence(reference, gate, context)
            if payload is None:
                continue
            gate_payloads[gate] = payload
            if gate == "claim_honesty":
                _validate_claim_honesty(payload, context, product_status)
            else:
                GATE_VALIDATORS[gate](payload, context)
            if research_hash is not None:
                _require(context.evidence_hashes.get(gate) != research_hash, f"{gate_path}.evidence.sha256", "must not reuse the scoped research ACCEPT artifact", errors)
    _cross_validate(gate_payloads, context)
    if product_status == "ACCEPT":
        _require(not open_gates, "$.product.status", "cannot be ACCEPT while any gate is OPEN", errors)
        _require(repository_commit is not None and repository_commit == expected_master_head, "$.verification.repository_commit", "normal ACCEPT must run from the exact expected master HEAD", errors)
        if context.observed_times:
            newest = max(context.observed_times.values())
            if release_decision and isinstance(release_decision.get("evidence"), Mapping):
                _validate_release_decision(release_decision["evidence"], context, newest)
            else:
                _error(errors, "$.product.release_decision.evidence", "authoritative release evidence is required")
    errors.extend(_find_prohibited_fields(manifest))
    errors.extend(_scan_secret_shapes(manifest))
    errors = sorted(set(errors))
    accepted = product_status == "ACCEPT" and not open_gates and not errors
    result = "INVALID" if errors else ("ACCEPT" if accepted else "OPEN")
    raw = manifest_raw if manifest_raw is not None else _canonical_bytes(manifest)
    verifier_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest_id": manifest.get("manifest_id"),
        "declared_product_status": product_status,
        "result": result,
        "accepted": accepted,
        "verification_time_utc": _format_timestamp(verification_time),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "verifier_sha256": verifier_hash,
        "repository_commit": repository_commit,
        "expected_master_head": expected_master_head,
        "expected_deploy_id": expected_deploy_id,
        "trusted_issuer_registry_sha256": context.registry_sha256,
        "evidence_sha256": dict(sorted(context.evidence_hashes.items())),
        "subject_sha256": dict(sorted(context.subject_hashes.items())),
        "authorities": dict(sorted(context.authorities.items())),
        "open_gates": open_gates,
        "errors": errors,
    }


def load_manifest(path: Path) -> tuple[Mapping[str, Any], bytes]:
    raw = _read_bounded(path, str(path))
    return _loads_json(raw, str(path)), raw


def _invalid_report(errors: list[str], verification_time: datetime) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest_id": None,
        "declared_product_status": None,
        "result": "INVALID",
        "accepted": False,
        "verification_time_utc": _format_timestamp(verification_time),
        "manifest_sha256": None,
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "repository_commit": None,
        "expected_master_head": None,
        "expected_deploy_id": None,
        "trusted_issuer_registry_sha256": None,
        "evidence_sha256": {},
        "subject_sha256": {},
        "authorities": {},
        "open_gates": list(REQUIRED_GATES),
        "errors": errors,
    }


def _write_sanitized_bundle(
    *,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
    repo_root: Path,
    output_root: Path,
    resolved_documents: Mapping[str, bytes],
    report: Mapping[str, Any],
) -> None:
    """Write only verifier-approved, referenced evidence into a new bundle."""

    if report.get("accepted") is not True:
        raise ManifestLoadError(
            "sanitized evidence bundle requires an authoritative ACCEPT"
        )
    references: dict[str, Mapping[str, Any]] = {}
    gates = manifest.get("required_gates")
    if isinstance(gates, Mapping):
        for gate in REQUIRED_GATES:
            entry = gates.get(gate)
            if isinstance(entry, Mapping) and isinstance(entry.get("evidence"), Mapping):
                references[gate] = entry["evidence"]
    product = manifest.get("product")
    if isinstance(product, Mapping):
        decision = product.get("release_decision")
        if isinstance(decision, Mapping) and isinstance(decision.get("evidence"), Mapping):
            references["release_decision"] = decision["evidence"]
    if set(references) != AUTHORITY_GATES or set(resolved_documents) != AUTHORITY_GATES:
        raise ManifestLoadError(
            "sanitized evidence bundle is missing authoritative documents"
        )

    planned: list[tuple[Path, bytes]] = []
    manifest_target = output_root / "customer-production-acceptance.json"
    registry_target = output_root / TRUSTED_ISSUER_REGISTRY
    index_target = output_root / "sanitized-bundle-index.json"
    planned.append((manifest_target, manifest_raw))
    index_entries: dict[str, dict[str, Any]] = {}
    seen_targets: set[Path] = {
        manifest_target.resolve(),
        registry_target.resolve(),
        index_target.resolve(),
    }
    for gate in sorted(AUTHORITY_GATES):
        reference = references[gate]
        document = resolved_documents[gate]
        actual_hash = hashlib.sha256(document).hexdigest()
        if actual_hash != report.get("evidence_sha256", {}).get(gate):
            raise ManifestLoadError(
                f"sanitized evidence hash drifted for {gate}"
            )
        authority = reference.get("authority")
        mode = authority.get("mode") if isinstance(authority, Mapping) else None
        uri = reference.get("uri")
        if mode == "signed_receipt":
            target_errors: list[str] = []
            target = _safe_repo_path(
                uri,
                output_root,
                f"sanitized_bundle.{gate}.uri",
                target_errors,
            )
            if target is None or target_errors:
                raise ManifestLoadError(
                    f"sanitized evidence path is invalid for {gate}"
                )
        elif mode == "live_https":
            target = output_root / "live-evidence" / f"{gate}.json"
        else:
            raise ManifestLoadError(
                f"sanitized evidence authority is invalid for {gate}"
            )
        resolved_target = target.resolve()
        if resolved_target in seen_targets:
            raise ManifestLoadError(
                f"sanitized evidence target is duplicated for {gate}"
            )
        seen_targets.add(resolved_target)
        planned.append((target, document))
        index_entries[gate] = {
            "archive_path": target.relative_to(output_root).as_posix(),
            "authority_mode": mode,
            "source_uri": uri,
            "sha256": actual_hash,
        }

    registry_raw = _read_bounded(
        repo_root / TRUSTED_ISSUER_REGISTRY,
        str(TRUSTED_ISSUER_REGISTRY),
    )
    registry_hash = hashlib.sha256(registry_raw).hexdigest()
    if registry_hash != report.get("trusted_issuer_registry_sha256"):
        raise ManifestLoadError("trusted issuer registry hash drifted during archive")
    planned.append((registry_target, registry_raw))
    index = {
        "schema_version": "cas_harness_sanitized_evidence_bundle.v1",
        "manifest_sha256": report.get("manifest_sha256"),
        "trusted_issuer_registry_sha256": registry_hash,
        "evidence": index_entries,
    }
    planned.append(
        (
            index_target,
            json.dumps(index, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        )
    )

    try:
        output_root.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise ManifestLoadError(
            f"cannot create sanitized evidence bundle ({type(exc).__name__})"
        ) from exc
    try:
        for target, raw in planned:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    except OSError as exc:
        raise ManifestLoadError(
            f"cannot write sanitized evidence bundle ({type(exc).__name__})"
        ) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / DEFAULT_MANIFEST, help="manifest path; production ACCEPT normally uses a downloaded evidence bundle")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="checked-out repository root")
    parser.add_argument("--evidence-root", type=Path, default=None, help="root used to dereference repo:// signed receipts")
    parser.add_argument("--expected-master-head", help="externally bound protected master HEAD SHA")
    parser.add_argument("--expected-deploy-id", help="externally bound public Render deployment ID")
    parser.add_argument("--live", action="store_true", help="allow dereferencing allowlisted live HTTPS evidence")
    parser.add_argument("--validate-only", action="store_true", help="validate the contract while permitting truthful OPEN")
    parser.add_argument("--json", action="store_true", help="emit only the machine-readable report")
    parser.add_argument("--report-path", type=Path, help="also write the machine-readable report to this path")
    parser.add_argument("--sanitized-bundle-path", type=Path, help="on a normal ACCEPT, archive only the verified manifest, referenced evidence, registry, and hash index into a new directory")
    parser.add_argument("--now", help="fixed UTC verification time; allowed only with --validate-only")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    actual_now = datetime.now(timezone.utc)
    preflight_errors: list[str] = []
    verification_time = actual_now
    repo_root = args.repo_root.resolve()
    manifest: Mapping[str, Any] | None = None
    raw: bytes | None = None
    resolved_documents: dict[str, bytes] = {}
    if args.now:
        if not args.validate_only:
            preflight_errors.append("--now is forbidden for normal customer-production ACCEPT")
        else:
            parsed = _timestamp(args.now, "--now", preflight_errors)
            if parsed is not None:
                verification_time = parsed
    if args.expected_master_head is not None and SHA1_RE.fullmatch(args.expected_master_head) is None:
        preflight_errors.append("--expected-master-head must be a lowercase 40-character SHA")
    if args.expected_deploy_id is not None and not args.expected_deploy_id.startswith("dep-"):
        preflight_errors.append("--expected-deploy-id must be a Render deployment ID")
    if args.sanitized_bundle_path is not None and args.validate_only:
        preflight_errors.append(
            "--sanitized-bundle-path is forbidden with --validate-only"
        )
    if preflight_errors:
        report = _invalid_report(preflight_errors, verification_time)
    else:
        try:
            manifest, raw = load_manifest(args.manifest.resolve())
            evidence_root = (args.evidence_root or args.manifest.resolve().parent).resolve()
            report = verify_manifest(
                manifest,
                repo_root=repo_root,
                evidence_root=evidence_root,
                verification_time=verification_time,
                expected_master_head=args.expected_master_head,
                expected_deploy_id=args.expected_deploy_id,
                repository_commit=_repository_commit(repo_root),
                live=bool(args.live),
                manifest_raw=raw,
                resolved_documents=resolved_documents,
            )
        except ManifestLoadError as exc:
            report = _invalid_report([str(exc)], verification_time)
    if args.sanitized_bundle_path and report.get("accepted") is True:
        try:
            if manifest is None or raw is None:
                raise ManifestLoadError("accepted manifest bytes are unavailable")
            _write_sanitized_bundle(
                manifest=manifest,
                manifest_raw=raw,
                repo_root=repo_root,
                output_root=args.sanitized_bundle_path.resolve(),
                resolved_documents=resolved_documents,
                report=report,
            )
        except ManifestLoadError as exc:
            report["accepted"] = False
            report["result"] = "INVALID"
            report["errors"] = sorted(
                set([*report.get("errors", []), f"sanitized archive: {exc}"])
            )
    rendered = json.dumps(report, sort_keys=True)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(rendered + "\n", encoding="utf-8")
    if args.json:
        print(rendered)
    elif report["result"] == "INVALID":
        print("customer-production acceptance INVALID", file=sys.stderr)
        for error in report["errors"]:
            print(f"- {error}", file=sys.stderr)
    elif report["accepted"]:
        print("customer-production ACCEPT")
    elif report["open_gates"]:
        print("customer-production OPEN; gates OPEN: " + ", ".join(report["open_gates"]))
    else:
        print("customer-production OPEN; all evidence gates present; release decision OPEN")
    if report["result"] == "INVALID":
        return 1
    if args.validate_only:
        return 0
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
