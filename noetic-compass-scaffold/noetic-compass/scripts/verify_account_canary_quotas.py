#!/usr/bin/env python3
"""Bounded two-phase quota proof for the private CAS Harness account canary.

This script is intentionally unable to run against public production. It requires the
``accounts-canary`` deployment profile, the private canary's account/quota flags, billing dark,
a loopback HTTP URL, the expected Render service id, and the canary's shared Postgres DSN.

Run ``pre`` on the live private service, restart/redeploy that service, then run ``post`` with the
same proof id. Temporary credentials are derived in memory from the platform provisioning secret;
they are never printed. The post phase rotates them to unknown random values and verifies that the
old credentials and sessions are invalid.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.services.production.state_substrate.interface import LedgerRecord, VersionConflict
from api.services.production.state_substrate.postgres_store import PostgresStateStore
from api.services.quotas import (
    USAGE_COUNTER_KIND,
    consume_audit_quota,
    current_monthly_period_key,
    get_usage,
    monthly_period_key,
)
from api.state_ledger_bootstrap import _postgres_state_store_dsn


AUDIT_SESSION_PATH = "/api/cas-harness/audit/session"
AUDIT_SESSIONS_PATH = "/api/cas-harness/audit/sessions"
PROOF_KIND = "account_canary_quota_proof"
PROOF_SCHEMA_VERSION = 1
ACCOUNT_CANARY_SERVICE_ID = "srv-d9akoolaeets73bp3e7g"
ACCOUNT_CANARY_SERVICE_TYPE = "pserv"
ACCOUNT_CANARY_GIT_BRANCH = "release/accounts-canary-20260713"
ACCOUNT_CANARY_DATABASE_HOST = "dpg-d9akobtaeets73bp29kg-a"
ACCOUNT_CANARY_DATABASE_USER = "cas_harness_canary"
ACCOUNT_CANARY_DATABASE_NAME = "cas_harness_accounts_canary"
ACCOUNT_CANARY_QUOTA_LIMIT = 2
ACCOUNT_CANARY_MODEL_ID = "quota-proof-local-no-provider"
ACCOUNT_CANARY_OBJECT_STORE_PREFIX = "cas-harness/accounts-canary/evidence-anchors"
ACCOUNT_CANARY_OBJECT_STORE_REGION = "us-west-2"
ACCOUNT_CANARY_OBJECT_LOCK_MODE = "GOVERNANCE"
ACCOUNT_CANARY_OBJECT_LOCK_RETENTION_DAYS = 31
_PROOF_ID = re.compile(r"^[a-z0-9][a-z0-9-]{5,23}$")
_SERVICE_ID = re.compile(r"^srv-[a-z0-9]{8,64}$")
_RESTART_RECEIPT = re.compile(r"^dep-[a-z0-9]{8,64}$")
_AUDIT_ID = re.compile(r"^cas-audit-[0-9a-f]{16}$")
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bcasak_[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"\bbearer\s+\S+", re.IGNORECASE),
    re.compile(
        r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@",
        re.IGNORECASE,
    ),
)


class ProofFailure(RuntimeError):
    """The canary did not earn one of the required proof assertions."""


def _redact(value: Any) -> Any:
    """Return a JSON-safe projection that cannot emit credentials or bearer tokens."""
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS)
                else _redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str) and any(
        pattern.search(value) for pattern in _SENSITIVE_VALUE_PATTERNS
    ):
        return "[REDACTED]"
    return value


def _response_body(response: httpx.Response) -> Any:
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError):
        payload = {"body": response.text[:500]}
    return _redact(payload)


def _expect_status(response: httpx.Response, expected: int, label: str) -> Any:
    if response.status_code != expected:
        raise ProofFailure(
            f"{label}: expected HTTP {expected}, received {response.status_code}"
        )
    return _response_body(response)


def _credential(platform_secret: str, proof_id: str, lane: str) -> str:
    """Derive a retry-stable API credential without persisting or printing it."""
    digest = hmac.new(
        platform_secret.encode("utf-8"),
        f"account-canary-quota-proof:{proof_id}:{lane}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"casak_{encoded}"


def _random_credential() -> str:
    return f"casak_{secrets.token_urlsafe(32)}"


def _safe_loopback_url(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ProofFailure("base URL must use http or https")
    if parsed.hostname not in {"127.0.0.1", "::1"}:
        raise ProofFailure("quota proof refuses non-loopback HTTP targets")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProofFailure("base URL must not contain credentials, a query, or a fragment")
    return raw.rstrip("/")


def _is_true(name: str) -> bool:
    return os.getenv(name, "") == "true"


def _is_false(name: str) -> bool:
    return os.getenv(name, "") == "false"


def _require_canary_database_url(raw: str) -> str:
    """Require the dedicated canary Postgres target without echoing its DSN."""
    try:
        parsed = urlparse(raw)
        port = parsed.port
        username = unquote(parsed.username or "", errors="strict")
        database_path = unquote(parsed.path, errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProofFailure(
            "NC_DATABASE_URL is not a valid dedicated account-canary Postgres URL"
        ) from exc

    if (
        parsed.scheme != "postgresql"
        or parsed.hostname != ACCOUNT_CANARY_DATABASE_HOST
        or username != ACCOUNT_CANARY_DATABASE_USER
        or not parsed.password
        or database_path != f"/{ACCOUNT_CANARY_DATABASE_NAME}"
        or ";" in parsed.path
        or port not in {None, 5432}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ProofFailure(
            "NC_DATABASE_URL does not target the dedicated account-canary Postgres host"
        )
    return raw


def _require_canary_environment(*, expected_limit: int, expected_service_id: str) -> tuple[str, str]:
    libpq_environment_is_clean = not any(
        name.upper().startswith("PG") for name in os.environ
    )
    receipt_attestation_key = os.getenv(
        "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY", ""
    )
    assertions = {
        "NC_DEPLOYMENT_PROFILE=accounts-canary": (
            os.getenv("NC_DEPLOYMENT_PROFILE", "").strip() == "accounts-canary"
        ),
        "NC_ACCOUNTS_ENABLED=true": _is_true("NC_ACCOUNTS_ENABLED"),
        "NC_QUOTAS_ENABLED=true": _is_true("NC_QUOTAS_ENABLED"),
        "NC_BILLING_ENTITLEMENTS_ENABLED=false": _is_false(
            "NC_BILLING_ENTITLEMENTS_ENABLED"
        ),
        "NC_BILLING_PROVIDER=null": (
            os.getenv("NC_BILLING_PROVIDER", "").strip().lower() == "null"
        ),
        "NC_FLEET_SERVICE_AUTH_ENABLED=false": _is_false(
            "NC_FLEET_SERVICE_AUTH_ENABLED"
        ),
        "NC_DEBUG=false": _is_false("NC_DEBUG"),
        "NC_STATE_LEDGER_ENABLED=true": _is_true("NC_STATE_LEDGER_ENABLED"),
        "NC_STATE_LEDGER_READ_AUTHORITY=true": _is_true(
            "NC_STATE_LEDGER_READ_AUTHORITY"
        ),
        "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE=false": _is_false(
            "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE"
        ),
        "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true": _is_true(
            "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED"
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_MODE=disabled": (
            os.getenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "").strip().lower()
            == "disabled"
        ),
        "NC_DEFAULT_LLM_PROVIDER=mock": (
            os.getenv("NC_DEFAULT_LLM_PROVIDER", "").strip().lower() == "mock"
        ),
        "NC_ACCOUNT_BOOTSTRAP_SECRET is absent": (
            os.getenv("NC_ACCOUNT_BOOTSTRAP_SECRET", "") == ""
        ),
        "ACCOUNT_BOOTSTRAP_SECRET is absent": (
            os.getenv("ACCOUNT_BOOTSTRAP_SECRET", "") == ""
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX is account-canary scoped": (
            os.getenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX", "").strip()
            == ACCOUNT_CANARY_OBJECT_STORE_PREFIX
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION=us-west-2": (
            os.getenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "").strip()
            == ACCOUNT_CANARY_OBJECT_STORE_REGION
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE=GOVERNANCE": (
            os.getenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "").strip()
            == ACCOUNT_CANARY_OBJECT_LOCK_MODE
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS=31": (
            os.getenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "").strip()
            == str(ACCOUNT_CANARY_OBJECT_LOCK_RETENTION_DAYS)
        ),
        "Object Lock receipt attestation authority has safe syntax": (
            len(receipt_attestation_key) >= 32
            and receipt_attestation_key == receipt_attestation_key.strip()
            and all(
                0x21 <= ord(character) <= 0x7E
                for character in receipt_attestation_key
            )
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET is present": bool(
            os.getenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "").strip()
        ),
        "AWS_ACCESS_KEY_ID is present": bool(
            os.getenv("AWS_ACCESS_KEY_ID", "").strip()
        ),
        "AWS_SECRET_ACCESS_KEY is present": bool(
            os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
        ),
        "NC_MOCK_LLM=true": _is_true("NC_MOCK_LLM"),
        "expected Render service id is the stable account canary": (
            expected_service_id == ACCOUNT_CANARY_SERVICE_ID
        ),
        "RENDER_SERVICE_ID is the stable account canary": (
            os.getenv("RENDER_SERVICE_ID", "").strip()
            == ACCOUNT_CANARY_SERVICE_ID
        ),
        "RENDER_SERVICE_TYPE=pserv": (
            os.getenv("RENDER_SERVICE_TYPE", "").strip()
            == ACCOUNT_CANARY_SERVICE_TYPE
        ),
        "RENDER_GIT_BRANCH=release/accounts-canary-20260713": (
            os.getenv("RENDER_GIT_BRANCH", "").strip()
            == ACCOUNT_CANARY_GIT_BRANCH
        ),
        "expected quota limit is the pinned account canary limit": (
            expected_limit == ACCOUNT_CANARY_QUOTA_LIMIT
        ),
        "NC_QUOTA_MONTHLY_AUDIT_LIMIT=2": (
            os.getenv("NC_QUOTA_MONTHLY_AUDIT_LIMIT", "").strip()
            == str(ACCOUNT_CANARY_QUOTA_LIMIT)
        ),
        "no libpq PG* environment overrides": libpq_environment_is_clean,
    }
    failed = [label for label, passed in assertions.items() if not passed]
    if failed:
        raise ProofFailure("unsafe or unexpected deployment posture: " + "; ".join(failed))

    database_url = os.getenv("NC_DATABASE_URL", "").strip()
    platform_secret = os.getenv("NC_PLATFORM_TENANT_PROVISIONING_SECRET", "")
    if not database_url:
        raise ProofFailure("NC_DATABASE_URL is required for the shared-Postgres proof")
    _require_canary_database_url(database_url)
    if (
        len(platform_secret) < 32
        or platform_secret != platform_secret.strip()
        or any(not 0x21 <= ord(character) <= 0x7E for character in platform_secret)
    ):
        raise ProofFailure("platform provisioning authority has an unsafe syntax")
    return database_url, platform_secret


def _host_fingerprint() -> str:
    host = (
        os.getenv("RENDER_INSTANCE_ID", "").strip()
        or os.getenv("HOSTNAME", "").strip()
    )
    if not host:
        raise ProofFailure("Render instance/container identity is unavailable")
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:20]


def _tenant_id(proof_id: str, lane: str) -> str:
    return f"quota-{proof_id}-{lane}"


def _identity(proof_id: str, lane: str) -> str:
    return f"quota-proof-{proof_id}-{lane}@example.invalid"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _provision(
    client: httpx.Client,
    *,
    platform_secret: str,
    proof_id: str,
    lane: str,
    credential: str,
) -> dict[str, Any]:
    response = client.post(
        "/platform/tenants",
        headers={"X-Platform-Provisioning-Secret": platform_secret},
        json={
            "tenant_id": _tenant_id(proof_id, lane),
            "email_or_username": _identity(proof_id, lane),
            "api_credential": credential,
            "display_name": f"Quota proof {proof_id} {lane.upper()}",
        },
    )
    body = _expect_status(response, 200, f"provision tenant {lane}")
    owner = body.get("owner", {}) if isinstance(body, dict) else {}
    if owner.get("tenant_id") != _tenant_id(proof_id, lane):
        raise ProofFailure(f"tenant {lane} provisioning returned the wrong tenant")
    return body


def _login(
    client: httpx.Client, *, proof_id: str, lane: str, credential: str
) -> str:
    response = client.post(
        "/auth/token",
        json={
            "username": _identity(proof_id, lane),
            "api_credential": credential,
        },
    )
    if response.status_code != 200:
        _expect_status(response, 200, f"login tenant {lane}")
    raw = response.json()
    token = raw.get("token") if isinstance(raw, dict) else None
    if not isinstance(token, str) or not token:
        raise ProofFailure(f"login tenant {lane} did not return a bearer token")
    return token


def _sessions(client: httpx.Client, token: str) -> list[dict[str, Any]]:
    body = _expect_status(
        client.get(AUDIT_SESSIONS_PATH, headers=_headers(token)),
        200,
        "list audit sessions",
    )
    sessions = body.get("sessions") if isinstance(body, dict) else None
    if not isinstance(sessions, list):
        raise ProofFailure("audit-session list response was malformed")
    return [item for item in sessions if isinstance(item, dict)]


def _prompt(proof_id: str, lane: str, ordinal: int) -> str:
    return f"quota-proof:{proof_id}:{lane}:{ordinal}"


def _ensure_session(
    client: httpx.Client,
    *,
    token: str,
    proof_id: str,
    lane: str,
    ordinal: int,
) -> dict[str, Any]:
    prompt = _prompt(proof_id, lane, ordinal)
    # The public session contract deliberately redacts prompt_text. Proof prompts
    # are shorter than the summary limit, so prompt_summary is exact here.
    matches = [row for row in _sessions(client, token) if row.get("prompt_summary") == prompt]
    if len(matches) > 1:
        raise ProofFailure(f"duplicate durable sessions exist for {prompt}")
    if matches:
        return matches[0]
    response = client.post(
        AUDIT_SESSION_PATH,
        headers=_headers(token),
        json={
            "model_id": ACCOUNT_CANARY_MODEL_ID,
            "audit_mode": "BALANCED",
            "prompt": prompt,
            "selected_modules": ["active_trace"],
        },
    )
    return _expect_status(response, 200, f"create audit {lane}/{ordinal}")


def _run(client: httpx.Client, token: str, audit_id: str) -> httpx.Response:
    return client.post(f"{AUDIT_SESSION_PATH}/{audit_id}/run", headers=_headers(token))


def _safe_quota_contract_projection(
    detail: Any, *, expected_period: str
) -> dict[str, Any]:
    """Project only non-secret quota-contract scalars for mismatch diagnostics."""
    if not isinstance(detail, dict):
        detail = {}
    code = detail.get("code")
    limit = detail.get("limit")
    count = detail.get("count")
    return {
        "code": (
            "audit_quota_exceeded"
            if code == "audit_quota_exceeded"
            else "[INVALID]"
        ),
        "limit": limit if type(limit) is int else "[INVALID]",
        "count": count if type(count) is int else "[INVALID]",
        "period_matches": detail.get("period") == expected_period,
    }


def _expect_quota_429(response: httpx.Response, *, expected_limit: int) -> dict[str, Any]:
    body = _expect_status(response, 429, "quota overflow")
    detail = body.get("detail") if isinstance(body, dict) else None
    expected = {
        "code": "audit_quota_exceeded",
        "limit": expected_limit,
        "count": expected_limit,
        "period": current_monthly_period_key(),
    }
    if detail != expected:
        observed = _safe_quota_contract_projection(
            detail, expected_period=expected["period"]
        )
        raise ProofFailure(
            "quota overflow body did not match the exact contract; "
            f"expected={json.dumps(expected, sort_keys=True)} "
            f"observed={json.dumps(observed, sort_keys=True)}"
        )
    return detail


def _proof_client(*, base_url: str, timeout: float) -> httpx.Client:
    """Create a loopback-only client that ignores proxies and never follows redirects."""
    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
        trust_env=False,
        follow_redirects=False,
    )


def _assert_cross_tenant_404(
    client: httpx.Client, *, other_token: str, audit_id: str
) -> None:
    response = client.get(
        f"{AUDIT_SESSION_PATH}/{audit_id}/status", headers=_headers(other_token)
    )
    _expect_status(response, 404, "cross-tenant audit read")


def _upsert_pre_marker(
    store: PostgresStateStore,
    *,
    tenant_id: str,
    proof_id: str,
    host_fingerprint: str,
    expected_limit: int,
) -> None:
    existing = store.get(tenant_id, PROOF_KIND, proof_id)
    if existing is not None:
        payload = dict(existing.payload)
        if payload.get("pre_host_fingerprint") != host_fingerprint:
            raise ProofFailure("pre phase was already recorded on a different instance")
        if payload.get("expected_limit") != expected_limit:
            raise ProofFailure("pre marker was recorded with a different quota limit")
        return
    record = LedgerRecord.new(
        tenant_id=tenant_id,
        kind=PROOF_KIND,
        record_id=proof_id,
        payload={
            "schema_version": PROOF_SCHEMA_VERSION,
            "phase": "pre_started",
            "pre_host_fingerprint": host_fingerprint,
            "expected_limit": expected_limit,
            "execution_period": current_monthly_period_key(),
        },
        source="scripts.verify_account_canary_quotas",
        trace_id=f"quota-proof-{proof_id}",
    )
    try:
        store.put(record, expected_version=0)
    except VersionConflict as exc:
        raise ProofFailure("quota proof marker raced with another pre phase") from exc


def _update_marker(
    store: PostgresStateStore,
    *,
    tenant_id: str,
    proof_id: str,
    updates: dict[str, Any],
) -> None:
    existing = store.get(tenant_id, PROOF_KIND, proof_id)
    if existing is None:
        raise ProofFailure("quota proof marker is missing from shared Postgres")
    payload = dict(existing.payload)
    payload.update(updates)
    try:
        store.put(existing.with_payload(payload), expected_version=existing.version)
    except VersionConflict as exc:
        raise ProofFailure("quota proof marker changed concurrently") from exc


def _month_boundary_probe(
    store: PostgresStateStore, *, tenant_id: str, proof_id: str, expected_limit: int
) -> dict[str, Any]:
    december = monthly_period_key(datetime(2099, 12, 31, 23, 59, tzinfo=UTC))
    january = monthly_period_key(datetime(2100, 1, 1, 0, 0, tzinfo=UTC))
    audit_id = f"quota-month-boundary-{proof_id}"
    december_count = consume_audit_quota(
        store,
        tenant_id=tenant_id,
        period_key=december,
        audit_id=audit_id,
        limit=expected_limit,
        source="account_canary_quota_month_boundary_proof",
    )
    december_retry_count = consume_audit_quota(
        store,
        tenant_id=tenant_id,
        period_key=december,
        audit_id=audit_id,
        limit=expected_limit,
        source="account_canary_quota_month_boundary_proof",
    )
    january_count = consume_audit_quota(
        store,
        tenant_id=tenant_id,
        period_key=january,
        audit_id=audit_id,
        limit=expected_limit,
        source="account_canary_quota_month_boundary_proof",
    )
    result = {
        "previous_period": december,
        "next_period": january,
        "previous_count": get_usage(store, tenant_id=tenant_id, period_key=december),
        "previous_retry_count": december_retry_count,
        "next_count": get_usage(store, tenant_id=tenant_id, period_key=january),
    }
    if (
        december_count != 1
        or result["previous_count"] != 1
        or result["previous_retry_count"] != 1
        or january_count != 1
        or result["next_count"] != 1
    ):
        raise ProofFailure("adjacent hosted Postgres month buckets were not independent")
    return result


def _assert_boundary_survived(
    store: PostgresStateStore, *, tenant_id: str, proof_id: str
) -> dict[str, Any]:
    december = monthly_period_key(datetime(2099, 12, 31, 23, 59, tzinfo=UTC))
    january = monthly_period_key(datetime(2100, 1, 1, 0, 0, tzinfo=UTC))
    result = {
        "previous_period": december,
        "next_period": january,
        "previous_count": get_usage(store, tenant_id=tenant_id, period_key=december),
        "next_count": get_usage(store, tenant_id=tenant_id, period_key=january),
    }
    if result["previous_count"] != 1 or result["next_count"] != 1:
        raise ProofFailure("month-boundary counters did not survive restart in shared Postgres")
    marker = store.get(tenant_id, PROOF_KIND, proof_id)
    if marker is None:
        raise ProofFailure("pre-restart proof marker did not survive in shared Postgres")
    return result


def _rotate_and_invalidate(
    client: httpx.Client,
    *,
    token: str,
    proof_id: str,
    lane: str,
    old_credential: str,
) -> None:
    response = client.post(
        "/accounts/credential/rotate",
        headers=_headers(token),
        json={"api_credential": _random_credential()},
    )
    _expect_status(response, 200, f"rotate temporary tenant {lane} credential")
    old_login = client.post(
        "/auth/token",
        json={
            "username": _identity(proof_id, lane),
            "api_credential": old_credential,
        },
    )
    _expect_status(old_login, 401, f"old tenant {lane} credential invalidation")
    revoked_session = client.get(AUDIT_SESSIONS_PATH, headers=_headers(token))
    _expect_status(revoked_session, 401, f"tenant {lane} session invalidation")


def _run_pre(
    client: httpx.Client,
    store: PostgresStateStore,
    *,
    proof_id: str,
    platform_secret: str,
    expected_limit: int,
    host_fingerprint: str,
) -> dict[str, Any]:
    tenant_a = _tenant_id(proof_id, "a")
    credential_a = _credential(platform_secret, proof_id, "a")
    credential_b = _credential(platform_secret, proof_id, "b")
    _provision(
        client,
        platform_secret=platform_secret,
        proof_id=proof_id,
        lane="a",
        credential=credential_a,
    )
    _provision(
        client,
        platform_secret=platform_secret,
        proof_id=proof_id,
        lane="b",
        credential=credential_b,
    )
    token_a = _login(client, proof_id=proof_id, lane="a", credential=credential_a)
    token_b = _login(client, proof_id=proof_id, lane="b", credential=credential_b)
    _upsert_pre_marker(
        store,
        tenant_id=tenant_a,
        proof_id=proof_id,
        host_fingerprint=host_fingerprint,
        expected_limit=expected_limit,
    )

    allowed_a: list[str] = []
    for ordinal in range(1, expected_limit + 1):
        session = _ensure_session(
            client,
            token=token_a,
            proof_id=proof_id,
            lane="a",
            ordinal=ordinal,
        )
        audit_id = str(session.get("audit_id") or "")
        if not audit_id:
            raise ProofFailure("tenant A audit creation omitted audit_id")
        _expect_status(_run(client, token_a, audit_id), 200, f"run tenant A audit {ordinal}")
        allowed_a.append(audit_id)
        if ordinal == 1:
            _expect_status(
                _run(client, token_a, audit_id),
                200,
                "idempotent retry of tenant A first audit",
            )

    overflow_a = _ensure_session(
        client,
        token=token_a,
        proof_id=proof_id,
        lane="a",
        ordinal=expected_limit + 1,
    )
    overflow_a_id = str(overflow_a.get("audit_id") or "")
    overflow_detail = _expect_quota_429(
        _run(client, token_a, overflow_a_id), expected_limit=expected_limit
    )

    first_b = _ensure_session(
        client, token=token_b, proof_id=proof_id, lane="b", ordinal=1
    )
    first_b_id = str(first_b.get("audit_id") or "")
    _expect_status(_run(client, token_b, first_b_id), 200, "run tenant B first audit")
    _assert_cross_tenant_404(client, other_token=token_b, audit_id=allowed_a[0])

    period = current_monthly_period_key()
    usage_a = get_usage(store, tenant_id=tenant_a, period_key=period)
    usage_b = get_usage(
        store, tenant_id=_tenant_id(proof_id, "b"), period_key=period
    )
    if usage_a != expected_limit or usage_b != 1:
        raise ProofFailure(
            f"unexpected current usage before restart: tenant_a={usage_a}, tenant_b={usage_b}"
        )
    boundary = _month_boundary_probe(
        store,
        tenant_id=tenant_a,
        proof_id=proof_id,
        expected_limit=expected_limit,
    )
    _update_marker(
        store,
        tenant_id=tenant_a,
        proof_id=proof_id,
        updates={
            "phase": "awaiting_restart",
            "tenant_a_audit_ids": allowed_a,
            "tenant_a_overflow_audit_id": overflow_a_id,
            "tenant_b_first_audit_id": first_b_id,
        },
    )
    return {
        "status": "present_pre_restart",
        "proof_id": proof_id,
        "deployment_profile": "accounts-canary",
        "billing_entitlements": False,
        "billing_provider": "null",
        "quota_limit": expected_limit,
        "execution_period": period,
        "tenant_a_usage": usage_a,
        "tenant_b_usage": usage_b,
        "idempotent_retry": "present",
        "exact_429": overflow_detail,
        "tenant_isolation_404": "present",
        "month_boundary": boundary,
        "restart_shared_postgres": "pending_post_phase",
        "temporary_credentials": "retained_in_memory_derivation_until_post_phase",
    }


def _marker_audit_ids(
    payload: dict[str, Any], *, expected_limit: int
) -> tuple[list[str], str, str]:
    allowed_a = payload.get("tenant_a_audit_ids")
    overflow_a = payload.get("tenant_a_overflow_audit_id")
    first_b = payload.get("tenant_b_first_audit_id")
    if (
        payload.get("schema_version") != PROOF_SCHEMA_VERSION
        or not isinstance(allowed_a, list)
        or len(allowed_a) != expected_limit
        or any(
            not isinstance(item, str) or not _AUDIT_ID.fullmatch(item)
            for item in allowed_a
        )
        or not isinstance(overflow_a, str)
        or not _AUDIT_ID.fullmatch(overflow_a)
        or not isinstance(first_b, str)
        or not _AUDIT_ID.fullmatch(first_b)
    ):
        raise ProofFailure("pre-restart durable audit references are missing or malformed")
    references = [*allowed_a, overflow_a, first_b]
    if len(set(references)) != len(references):
        raise ProofFailure("pre-restart durable audit references are not unique")
    return allowed_a, overflow_a, first_b


def _load_durable_session(
    client: httpx.Client,
    *,
    token: str,
    audit_id: str,
    expected_prompt: str,
    label: str,
) -> dict[str, Any]:
    body = _expect_status(
        client.get(
            f"{AUDIT_SESSION_PATH}/{audit_id}/status", headers=_headers(token)
        ),
        200,
        f"load {label} after restart",
    )
    if (
        not isinstance(body, dict)
        or body.get("audit_id") != audit_id
        or body.get("prompt_summary") != expected_prompt
        or body.get("model_id") != ACCOUNT_CANARY_MODEL_ID
        or body.get("audit_mode") != "BALANCED"
        or body.get("selected_modules") != ["active_trace"]
        or body.get("endpoint_url") is not None
        or body.get("provider") is not None
    ):
        raise ProofFailure(f"{label} durable session contract mismatch after restart")
    return body


def _run_post(
    client: httpx.Client,
    store: PostgresStateStore,
    *,
    proof_id: str,
    platform_secret: str,
    expected_limit: int,
    host_fingerprint: str,
    restart_receipt: str,
) -> dict[str, Any]:
    tenant_a = _tenant_id(proof_id, "a")
    tenant_b = _tenant_id(proof_id, "b")
    marker = store.get(tenant_a, PROOF_KIND, proof_id)
    if marker is None or marker.payload.get("phase") != "awaiting_restart":
        raise ProofFailure("pre-restart phase is absent or not ready")
    pre_host = str(marker.payload.get("pre_host_fingerprint") or "")
    if not pre_host or pre_host == host_fingerprint:
        raise ProofFailure("Render instance/container identity did not change across restart")
    if marker.payload.get("expected_limit") != expected_limit:
        raise ProofFailure("post phase quota limit differs from the pre phase")
    if marker.payload.get("execution_period") != current_monthly_period_key():
        raise ProofFailure(
            "pre and post phases crossed a UTC month boundary; use a fresh proof id so the "
            "restart/cap assertion and the separate synthetic month-boundary assertion stay "
            "unambiguous"
        )
    allowed_a_ids, overflow_a_id, first_b_id = _marker_audit_ids(
        marker.payload, expected_limit=expected_limit
    )

    credential_a = _credential(platform_secret, proof_id, "a")
    credential_b = _credential(platform_secret, proof_id, "b")
    _provision(
        client,
        platform_secret=platform_secret,
        proof_id=proof_id,
        lane="a",
        credential=credential_a,
    )
    _provision(
        client,
        platform_secret=platform_secret,
        proof_id=proof_id,
        lane="b",
        credential=credential_b,
    )
    token_a = _login(client, proof_id=proof_id, lane="a", credential=credential_a)
    token_b = _login(client, proof_id=proof_id, lane="b", credential=credential_b)

    for ordinal, audit_id in enumerate(allowed_a_ids, start=1):
        _load_durable_session(
            client,
            token=token_a,
            audit_id=audit_id,
            expected_prompt=_prompt(proof_id, "a", ordinal),
            label=f"tenant A allowed audit {ordinal}",
        )
    _load_durable_session(
        client,
        token=token_a,
        audit_id=overflow_a_id,
        expected_prompt=_prompt(proof_id, "a", expected_limit + 1),
        label="tenant A overflow audit",
    )
    _load_durable_session(
        client,
        token=token_b,
        audit_id=first_b_id,
        expected_prompt=_prompt(proof_id, "b", 1),
        label="tenant B first audit",
    )
    first_a_id = allowed_a_ids[0]
    _expect_status(
        _run(client, token_a, first_a_id),
        200,
        "post-restart idempotent retry of tenant A audit",
    )
    overflow_a_detail = _expect_quota_429(
        _run(client, token_a, overflow_a_id), expected_limit=expected_limit
    )
    _expect_status(
        _run(client, token_b, first_b_id),
        200,
        "post-restart idempotent retry of tenant B audit",
    )
    _assert_cross_tenant_404(client, other_token=token_b, audit_id=first_a_id)

    for ordinal in range(2, expected_limit + 1):
        session = _ensure_session(
            client,
            token=token_b,
            proof_id=proof_id,
            lane="b",
            ordinal=ordinal,
        )
        audit_id = str(session.get("audit_id") or "")
        _expect_status(_run(client, token_b, audit_id), 200, f"run tenant B audit {ordinal}")
    overflow_b = _ensure_session(
        client,
        token=token_b,
        proof_id=proof_id,
        lane="b",
        ordinal=expected_limit + 1,
    )
    overflow_b_detail = _expect_quota_429(
        _run(client, token_b, str(overflow_b.get("audit_id") or "")),
        expected_limit=expected_limit,
    )

    period = current_monthly_period_key()
    usage_a = get_usage(store, tenant_id=tenant_a, period_key=period)
    usage_b = get_usage(store, tenant_id=tenant_b, period_key=period)
    if usage_a != expected_limit or usage_b != expected_limit:
        raise ProofFailure(
            f"unexpected post-restart usage: tenant_a={usage_a}, tenant_b={usage_b}"
        )
    boundary = _assert_boundary_survived(
        store, tenant_id=tenant_a, proof_id=proof_id
    )

    # This is deliberately last among HTTP assertions. Rotation revokes every session, and the
    # replacement secrets are discarded immediately, leaving no reusable proof credential.
    _rotate_and_invalidate(
        client,
        token=token_a,
        proof_id=proof_id,
        lane="a",
        old_credential=credential_a,
    )
    _rotate_and_invalidate(
        client,
        token=token_b,
        proof_id=proof_id,
        lane="b",
        old_credential=credential_b,
    )
    _update_marker(
        store,
        tenant_id=tenant_a,
        proof_id=proof_id,
        updates={
            "phase": "complete",
            "post_host_fingerprint": host_fingerprint,
            "restart_receipt": restart_receipt,
            "temporary_credentials_rotated": True,
        },
    )
    return {
        "status": "present",
        "proof_id": proof_id,
        "deployment_profile": "accounts-canary",
        "billing_entitlements": False,
        "billing_provider": "null",
        "quota_limit": expected_limit,
        "execution_period": period,
        "tenant_a_usage": usage_a,
        "tenant_b_usage": usage_b,
        "idempotent_retry_non_double_consumption": "present",
        "exact_429_tenant_a": overflow_a_detail,
        "exact_429_tenant_b": overflow_b_detail,
        "tenant_isolation_404": "present",
        "month_boundary": boundary,
        "restart_shared_postgres": "present",
        "render_restart_receipt": restart_receipt,
        "temporary_credentials_rotated_and_sessions_revoked": "present",
        "customer_production_accept": False,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("pre", "post"))
    parser.add_argument("--proof-id", required=True)
    parser.add_argument("--expected-service-id", required=True)
    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "NC_QUOTA_PROOF_BASE_URL",
            f"http://127.0.0.1:{os.getenv('PORT', '10000')}",
        ),
    )
    parser.add_argument(
        "--expected-limit",
        type=int,
        default=ACCOUNT_CANARY_QUOTA_LIMIT,
    )
    parser.add_argument("--restart-receipt")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not _PROOF_ID.fullmatch(args.proof_id):
        raise ProofFailure("proof id must be 6-24 lowercase letters, digits, or hyphens")
    if not _SERVICE_ID.fullmatch(args.expected_service_id):
        raise ProofFailure("expected Render service id is malformed")
    if args.expected_limit < 1 or args.expected_limit > 10:
        raise ProofFailure("hosted proof limit must stay between 1 and 10")
    if args.timeout_seconds <= 0 or args.timeout_seconds > 120:
        raise ProofFailure("timeout must stay between 0 and 120 seconds")
    if args.phase == "post":
        if not args.restart_receipt or not _RESTART_RECEIPT.fullmatch(
            args.restart_receipt
        ):
            raise ProofFailure("post phase requires a safe Render restart/deploy receipt")
    elif args.restart_receipt:
        raise ProofFailure("restart receipt belongs only to the post phase")

    base_url = _safe_loopback_url(args.base_url)
    database_url, platform_secret = _require_canary_environment(
        expected_limit=args.expected_limit,
        expected_service_id=args.expected_service_id,
    )
    store = PostgresStateStore(_postgres_state_store_dsn(database_url))
    try:
        with _proof_client(base_url=base_url, timeout=args.timeout_seconds) as client:
            if args.phase == "pre":
                report = _run_pre(
                    client,
                    store,
                    proof_id=args.proof_id,
                    platform_secret=platform_secret,
                    expected_limit=args.expected_limit,
                    host_fingerprint=_host_fingerprint(),
                )
            else:
                report = _run_post(
                    client,
                    store,
                    proof_id=args.proof_id,
                    platform_secret=platform_secret,
                    expected_limit=args.expected_limit,
                    host_fingerprint=_host_fingerprint(),
                    restart_receipt=args.restart_receipt,
                )
    finally:
        store.close()
    print(json.dumps(_redact(report), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProofFailure as exc:
        print(json.dumps({"status": "failed", "detail": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - operational fail-safe
        # Unexpected driver/network errors can carry connection context. Emit only the exception
        # type so a console transcript can never become a credential handoff.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "detail": f"unexpected {type(exc).__name__}; inspect private service logs",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
