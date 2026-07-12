"""Audit-session identity scope — the launch/paid-audit-identity security layer.

Three layers, all load-bearing:

* **Dark-mode no-regression** (default, ``accounts_enabled`` off): the audit-session routes stay on
  the auth allowlist, so the live console keeps calling ``/session`` + ``/session/{id}/run`` WITHOUT
  a login exactly as today. ``is_public_path`` reports them public; the always-public prefixes stay
  public; and the per-tenant ownership write is a complete no-op. This is the non-negotiable
  invariant: dark mode is byte-for-byte unchanged.

* **Account-mode gating** (``accounts_enabled`` True): the audit-session routes LEAVE the allowlist
  (``is_public_path`` False) so the middleware demands identity (401 with no Bearer), while the
  always-public prefixes (/atlas/live, target/verify, scale-plan, live-worker/health, crm/public)
  STAY public.

* **Ownership wiring** (``accounts_enabled`` True): running an audit with a server-derived account
  identity + a state-ledger store installed records an ``evidence_ownership`` row for the produced
  trace_id under the caller's tenant — so a later evidence GET/verify/anchor by that tenant is
  admitted and another tenant's is 404'd.

Run ONLY this file:
    python -m pytest tests/test_audit_identity_scope.py -q
"""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from api.config import settings
from api.middleware.auth import (
    ACCOUNT_GATED_PUBLIC_PREFIXES,
    ALWAYS_PUBLIC_PREFIXES,
    is_public_path,
)
from api.routes.cas_harness_audit import _record_audit_evidence_ownership
from api.services.accounts.store import AccountStore
from api.services.cas_harness_audit_sessions import (
    configure_audit_session_store,
    get_session as get_audit_session,
    reset_audit_sessions_for_tests,
)
from api.services.cas_harness_merged_evidence_packets import (
    reset_merged_fleet_evidence_packets_for_tests,
)
from api.services.evidence_ownership import (
    EVIDENCE_OWNERSHIP_KIND,
    tenant_owns_trace,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.quotas import USAGE_COUNTER_KIND, get_usage, monthly_period_key
from api.services.sessions import SessionStore

# An audit-session route path (the create/run/get/list family) and a representative member of every
# ALWAYS-public prefix that must never start requiring identity.
_AUDIT_SESSION_PATH = "/api/cas-harness/audit/session"
_AUDIT_SESSIONS_PATH = "/api/cas-harness/audit/sessions"
_AUDIT_SESSION_SUBPATH = "/api/cas-harness/audit/sessions/cas-audit-123"
_ALWAYS_PUBLIC_SAMPLES = (
    "/atlas/live/session",
    "/api/cas-harness/audit/target/verify",
    "/api/cas-harness/audit/scale-plan",
    "/api/cas-harness/live-worker/health",
    "/api/crm/public/leads",
)


def setup_function() -> None:
    reset_audit_sessions_for_tests()


@pytest.fixture(autouse=True)
def _isolated_evidence_store(tmp_path, monkeypatch):
    """Pin the Evidence Packet store to an empty per-test dir (mirrors test_cas_harness_audit.py)."""
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", raising=False)
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_merged_fleet_evidence_packets_for_tests()


# ===========================================================================
# (A) is_public_path — DARK MODE (accounts off, the default + live posture).
# ===========================================================================


def test_dark_mode_audit_session_is_public(monkeypatch):
    """With accounts OFF, the audit-session create/list/sub routes are public (no identity)."""
    monkeypatch.setattr(settings, "accounts_enabled", False)
    assert is_public_path(_AUDIT_SESSION_PATH) is True
    assert is_public_path(_AUDIT_SESSIONS_PATH) is True
    assert is_public_path(_AUDIT_SESSION_SUBPATH) is True
    assert is_public_path(f"{_AUDIT_SESSION_PATH}/cas-audit-123/run") is True
    assert is_public_path(f"{_AUDIT_SESSION_PATH}/cas-audit-123/status") is True


def test_dark_mode_always_public_prefixes_are_public(monkeypatch):
    """The always-public prefixes are public in dark mode, exactly as today."""
    monkeypatch.setattr(settings, "accounts_enabled", False)
    for path in _ALWAYS_PUBLIC_SAMPLES:
        assert is_public_path(path) is True, path


# ===========================================================================
# (A) is_public_path — ACCOUNT MODE (accounts on, monkeypatched).
# ===========================================================================


def test_account_mode_audit_session_is_not_public(monkeypatch):
    """With accounts ON, the audit-session routes leave the allowlist -> identity required."""
    monkeypatch.setattr(settings, "accounts_enabled", True)
    assert is_public_path(_AUDIT_SESSION_PATH) is False
    assert is_public_path(_AUDIT_SESSIONS_PATH) is False
    assert is_public_path(_AUDIT_SESSION_SUBPATH) is False
    assert is_public_path(f"{_AUDIT_SESSION_PATH}/cas-audit-123/run") is False


def test_account_mode_always_public_prefixes_still_public(monkeypatch):
    """The always-public prefixes STAY public even with accounts on — no auth added to them."""
    monkeypatch.setattr(settings, "accounts_enabled", True)
    for path in _ALWAYS_PUBLIC_SAMPLES:
        assert is_public_path(path) is True, path


def test_prefix_tuples_are_disjoint_and_correctly_split():
    """The two prefix groups carry exactly the intended split (no overlap, no drift)."""
    assert _AUDIT_SESSION_PATH in ACCOUNT_GATED_PUBLIC_PREFIXES
    assert _AUDIT_SESSIONS_PATH in ACCOUNT_GATED_PUBLIC_PREFIXES
    # Always-public set must NOT contain the gated session prefixes...
    assert _AUDIT_SESSION_PATH not in ALWAYS_PUBLIC_PREFIXES
    assert _AUDIT_SESSIONS_PATH not in ALWAYS_PUBLIC_PREFIXES
    # ...and must still carry the unchanged always-public ones.
    for prefix in (
        "/atlas/live",
        "/api/cas-harness/audit/target/verify",
        "/api/cas-harness/audit/scale-plan",
        "/api/cas-harness/live-worker/health",
        "/api/crm/public",
    ):
        assert prefix in ALWAYS_PUBLIC_PREFIXES, prefix
    assert set(ALWAYS_PUBLIC_PREFIXES).isdisjoint(ACCOUNT_GATED_PUBLIC_PREFIXES)


# ===========================================================================
# (B) DARK-MODE REACHABILITY — the live posture must be unchanged.
# ===========================================================================


def test_dark_mode_run_route_reachable_without_token(client):
    """Default posture: create + run an audit-session with NO Authorization header and it is
    reachable (not 401/403 from auth). Proves the route stays public in dark mode for the live
    console, which calls it without a login today."""
    created = client.post(
        _AUDIT_SESSION_PATH,
        json={
            "model_id": "openai:gpt-4.1-mini",
            "audit_mode": "BALANCED",
            "prompt": "Assess whether this answer should be accepted or suppressed.",
            "selected_modules": ["cognitive_bias", "provenance_trace"],
        },
    )
    assert created.status_code == 200, created.text
    audit_id = created.json()["audit_id"]

    ran = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run")
    # No model artifacts on this host, but the point is auth-reachability: never 401/403.
    assert ran.status_code not in (401, 403), ran.text
    assert ran.status_code == 200, ran.text


def test_dark_mode_list_route_reachable_without_token(client):
    """List endpoint stays public in dark mode (no token -> reachable, anonymous-owned bucket)."""
    resp = client.get(_AUDIT_SESSIONS_PATH)
    assert resp.status_code == 200, resp.text


# ===========================================================================
# (C) UNIT — the ownership-write branch (_record_audit_evidence_ownership).
# ===========================================================================


def _fake_request(*, tenant_id=None, account_id=None, store=None) -> Request:
    """A minimal ASGI Request with request.state.{tenant_id,account_id} and an app.state.state_ledger
    whose ``.store`` is ``store`` (or no ledger when store is None)."""
    ledger = SimpleNamespace(store=store) if store is not None else None
    app = SimpleNamespace(state=SimpleNamespace(state_ledger=ledger))
    req = Request({"type": "http", "headers": [], "method": "POST", "path": "/x", "app": app})
    if tenant_id is not None:
        req.state.tenant_id = tenant_id
    if account_id is not None:
        req.state.account_id = account_id
    return req


@pytest.fixture
def backend(tmp_path) -> SqliteStateStore:
    store = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    try:
        yield store
    finally:
        store.close()


def test_ownership_write_is_noop_in_dark_mode(backend, monkeypatch):
    """Dark default: even with a full identity + store present, NOTHING is written."""
    monkeypatch.setattr(settings, "accounts_enabled", False)
    req = _fake_request(tenant_id="tenant-A", account_id="acct-A", store=backend)
    _record_audit_evidence_ownership(req, "trace-dark")
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="trace-dark") is False
    assert len(backend.list("tenant-A", EVIDENCE_OWNERSHIP_KIND)) == 0


def test_ownership_write_fails_closed_without_identity(backend, monkeypatch):
    monkeypatch.setattr(settings, "accounts_enabled", True)
    req = _fake_request(tenant_id=None, account_id=None, store=backend)
    with pytest.raises(HTTPException) as exc:
        _record_audit_evidence_ownership(req, "trace-no-identity")
    assert exc.value.status_code == 503
    assert len(backend.list("tenant-A", EVIDENCE_OWNERSHIP_KIND)) == 0


def test_ownership_write_fails_closed_without_store(monkeypatch):
    monkeypatch.setattr(settings, "accounts_enabled", True)
    req = _fake_request(tenant_id="tenant-A", account_id="acct-A", store=None)
    with pytest.raises(HTTPException) as exc:
        _record_audit_evidence_ownership(req, "trace-no-store")
    assert exc.value.status_code == 503


def test_ownership_write_records_in_account_mode(backend, monkeypatch):
    """Account mode + identity + store + trace -> ownership row recorded under the caller's tenant."""
    monkeypatch.setattr(settings, "accounts_enabled", True)
    req = _fake_request(tenant_id="tenant-A", account_id="acct-A", store=backend)
    _record_audit_evidence_ownership(req, "trace-owned")
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="trace-owned") is True
    # And it is invisible to a different tenant (the isolation primitive).
    assert tenant_owns_trace(backend, tenant_id="tenant-B", trace_id="trace-owned") is False


def test_ownership_write_is_idempotent(backend, monkeypatch):
    """Re-running an audit (the hook fires twice) records exactly one row, never raises."""
    monkeypatch.setattr(settings, "accounts_enabled", True)
    req = _fake_request(tenant_id="tenant-A", account_id="acct-A", store=backend)
    _record_audit_evidence_ownership(req, "trace-twice")
    _record_audit_evidence_ownership(req, "trace-twice")
    rows = backend.list("tenant-A", EVIDENCE_OWNERSHIP_KIND)
    assert len(rows) == 1
    assert rows[0].record_id == "trace-twice"


# ===========================================================================
# (D) ACCOUNT-MODE INTEGRATION — full run records ownership for the produced trace.
# ===========================================================================


@pytest.fixture
def account_audit_client(tmp_path, monkeypatch):
    """A TestClient with accounts_enabled=True, durable account/session stores AND a state ledger on
    app.state, all sharing ONE SqliteStateStore backend (mirrors test_evidence_ownership.py's
    tenant_iso_client).

    Enter with the flag OFF (lifespan installs nothing), then flip ``accounts_enabled`` on and install
    temp-path stores directly — the route/middleware code reads ``settings.accounts_enabled`` per
    request, so the flip takes effect for every call.

    Yields ``(client, account_store, backend)``.
    """
    from api.main import app

    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    acct_store = AccountStore(
        backend, credential_pepper="test-account-credential-pepper-0123456789"
    )
    session_store = SessionStore(backend)

    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        prev_ledger = getattr(app.state, "state_ledger", None)
        app.state.account_store = acct_store
        app.state.session_store = session_store
        app.state.state_ledger = SimpleNamespace(store=backend)
        configure_audit_session_store(backend)
        try:
            yield client, acct_store, backend
        finally:
            configure_audit_session_store(None)
            app.state.account_store = None
            app.state.session_store = None
            app.state.state_ledger = prev_ledger
            backend.close()


def _provision_login(client, store, *, code, identity, role, tenant_id):
    """Create+redeem an invite and log in; returns account-mode bearer headers + account."""
    invite = store.create_invite(code=code, role=role, tenant_id=tenant_id)
    api_credential = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
    account = store.redeem_invite(
        code=invite.code, email_or_username=identity, api_credential=api_credential
    )
    resp = client.post(
        "/auth/token", json={"username": identity, "api_credential": api_credential}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}, account


def _fake_live_result(trace_id: str):
    """A LiveResult-shaped object identical in shape to the runner's, with a fixed trace_id."""
    return type(
        "LiveResult",
        (),
        {
            "trace_id": trace_id,
            "proof_chips": [
                {
                    "id": "model_proof",
                    "name": "Model proof",
                    "status": "present",
                    "detail": "Hosted open-weight live worker ran model target EleutherAI/pythia-160m.",
                },
                {
                    "id": "cas_readout",
                    "name": "CAS readout",
                    "status": "present",
                    "detail": "Live worker emitted token-level activation/readout events.",
                },
                {
                    "id": "causal_proof",
                    "name": "Causal proof",
                    "status": "unavailable",
                    "detail": "No ablation/intervention proof was run in this live-worker slice.",
                },
                {
                    "id": "control_proof",
                    "name": "Control proof",
                    "status": "unavailable",
                    "detail": "No matched-control proof was run in this live-worker slice.",
                },
                {
                    "id": "output_proof",
                    "name": "Output proof",
                    "status": "present",
                    "detail": "Live worker output text is recorded in the Evidence Packet.",
                },
                {
                    "id": "packet_proof",
                    "name": "Packet proof",
                    "status": "present",
                    "detail": f"Live Evidence Packet {trace_id} was written.",
                },
            ],
            "verifier_decision": None,
            "audit_scope": {
                "kind": "open_weight_live_trace",
                "label": (
                    "Open-weight live trace · activations + readout captured · "
                    "causal/control not yet run · verdict held for review"
                ),
                "internal_activation_access": True,
                "verdict_disposition": "held_for_human_review",
            },
            "message": "Live hosted open-weight worker ran and wrote an Evidence Packet.",
        },
    )()


def test_account_mode_run_records_ownership_for_produced_trace(
    account_audit_client, monkeypatch
):
    """STRONGEST feasible assertion: a full audit RUN in account mode (account-mode identity + a state
    ledger store installed) records an evidence_ownership row for the produced trace_id under the
    caller's tenant. The live runner is monkeypatched so no real model artifacts are needed — exactly
    the lever test_cas_harness_audit.py uses for the hosted-open-weight run path."""
    client, store, backend = account_audit_client
    headers_a, _account_a = _provision_login(
        client, store, code="audit-iso-a", identity="audit-a@example.com",
        role="member", tenant_id="tenant-A",
    )

    trace_id = "cas-live-ownit-001"

    async def fake_live_worker_audit(**kwargs):
        assert kwargs["model_id"] == "EleutherAI/pythia-160m"
        return _fake_live_result(trace_id)

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.run_live_worker_audit",
        fake_live_worker_audit,
    )

    created = client.post(
        _AUDIT_SESSION_PATH,
        json={
            "model_id": "EleutherAI/pythia-160m",
            "audit_mode": "BALANCED",
            "prompt": "Audit this live prompt.",
            "selected_modules": ["active_trace", "confidence_margin"],
        },
        headers=headers_a,
    )
    assert created.status_code == 200, created.text
    audit_id = created.json()["audit_id"]

    ran = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers_a)
    assert ran.status_code == 200, ran.text
    assert ran.json()["evidence_packet_trace_id"] == trace_id

    # The wiring under test: tenant A now OWNS the produced trace.
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id=trace_id) is True
    # And no other tenant does (isolation holds end to end).
    assert tenant_owns_trace(backend, tenant_id="tenant-B", trace_id=trace_id) is False
    assert not backend.list("tenant-A", USAGE_COUNTER_KIND)


def test_quota_run_is_idempotent_capped_and_tenant_isolated(
    account_audit_client, monkeypatch
):
    client, store, backend = account_audit_client
    monkeypatch.setattr(settings, "quotas_enabled", True)
    monkeypatch.setattr("api.routes.cas_harness_audit.get_quota_limit", lambda: 1)
    headers_a, _ = _provision_login(
        client,
        store,
        code="quota-a",
        identity="quota-a@example.com",
        role="member",
        tenant_id="tenant-A",
    )
    calls = 0

    async def fake_live_worker_audit(**_kwargs):
        nonlocal calls
        calls += 1
        return _fake_live_result(f"quota-trace-{calls}")

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.run_live_worker_audit", fake_live_worker_audit
    )

    def create(headers, prompt):
        response = client.post(
            _AUDIT_SESSION_PATH,
            json={
                "model_id": "EleutherAI/pythia-160m",
                "audit_mode": "BALANCED",
                "prompt": prompt,
                "selected_modules": ["active_trace"],
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        return response.json()

    first = create(headers_a, "first quota audit")
    first_run = client.post(
        f"{_AUDIT_SESSION_PATH}/{first['audit_id']}/run", headers=headers_a
    )
    assert first_run.status_code == 200, first_run.text
    retry = client.post(
        f"{_AUDIT_SESSION_PATH}/{first['audit_id']}/run", headers=headers_a
    )
    assert retry.status_code == 200
    assert calls == 1
    period = monthly_period_key(
        datetime.fromisoformat(first["created_at"].replace("Z", "+00:00"))
    )
    assert get_usage(backend, tenant_id="tenant-A", period_key=period) == 1

    second = create(headers_a, "second quota audit")
    capped = client.post(
        f"{_AUDIT_SESSION_PATH}/{second['audit_id']}/run", headers=headers_a
    )
    assert capped.status_code == 429
    assert capped.json()["detail"]["code"] == "audit_quota_exceeded"
    assert "tenant" not in capped.text.lower()
    assert calls == 1

    headers_b, _ = _provision_login(
        client,
        store,
        code="quota-b",
        identity="quota-b@example.com",
        role="member",
        tenant_id="tenant-B",
    )
    tenant_b = create(headers_b, "tenant B quota audit")
    allowed_b = client.post(
        f"{_AUDIT_SESSION_PATH}/{tenant_b['audit_id']}/run", headers=headers_b
    )
    assert allowed_b.status_code == 200, allowed_b.text
    assert calls == 2
    assert get_usage(backend, tenant_id="tenant-B", period_key=period) == 1


def test_ownership_failure_marks_claimed_attempt_failed_and_releases_lease(
    account_audit_client, monkeypatch
):
    client, store, _backend = account_audit_client
    headers, account = _provision_login(
        client,
        store,
        code="ownership-fail",
        identity="ownership-fail@example.com",
        role="member",
        tenant_id="tenant-A",
    )
    calls = 0

    async def fake_live_worker_audit(**_kwargs):
        nonlocal calls
        calls += 1
        return _fake_live_result("trace-ownership-fail")

    def fail_ownership(*_args, **_kwargs):
        raise HTTPException(
            status_code=503, detail="Evidence ownership persistence is unavailable."
        )

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.run_live_worker_audit", fake_live_worker_audit
    )
    monkeypatch.setattr(
        "api.routes.cas_harness_audit._record_audit_evidence_ownership", fail_ownership
    )
    created = client.post(
        _AUDIT_SESSION_PATH,
        json={
            "model_id": "EleutherAI/pythia-160m",
            "audit_mode": "BALANCED",
            "prompt": "ownership write must fail closed",
            "selected_modules": ["active_trace"],
        },
        headers=headers,
    )
    assert created.status_code == 200
    audit_id = created.json()["audit_id"]
    failed = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert failed.status_code == 503

    record = get_audit_session(
        audit_id, tenant_id="tenant-A", account_id=account.account_id
    )
    assert record is not None and record.status == "FAILED"
    assert record.run_state is None and record.run_lease_until is None
    retried = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["status"] == "FAILED"
    assert calls == 1


def test_account_mode_no_token_run_is_401(account_audit_client, monkeypatch):
    """Account mode + no Bearer token on the run route -> the middleware 401s (route left the
    allowlist). No ownership row, no run."""
    client, _store, _backend = account_audit_client
    resp = client.post(f"{_AUDIT_SESSION_PATH}/whatever/run")
    assert resp.status_code == 401, resp.text
