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
from api.services.quotas import USAGE_COUNTER_KIND, get_usage
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
            "evidence_packet": {
                "trace_id": trace_id,
                "model": {"model_key": "EleutherAI/pythia-160m"},
                "live_audit": {
                    "events": [
                        {
                            "type": "manifest",
                            "manifest": {
                                "model_id": "EleutherAI/pythia-160m",
                                "is_real_model": True,
                            },
                        }
                    ]
                },
            },
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
    execution_period = "audits:2026-07"
    prior_period = "audits:2026-06"
    next_period = "audits:2026-08"
    monkeypatch.setattr(settings, "quotas_enabled", True)
    monkeypatch.setattr(settings, "quota_monthly_audit_limit", 1)
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.current_monthly_period_key",
        lambda: execution_period,
    )
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
    # This draft was left unused in a prior month. Its first execution must consume the current
    # execution month, not the stale creation month.
    first_ledger = backend.get("tenant-A", "cas_audit_session", first["audit_id"])
    assert first_ledger is not None
    prior_payload = dict(first_ledger.payload)
    prior_payload["created_at"] = "2026-06-15T12:00:00+00:00"
    backend.put(
        first_ledger.with_payload(prior_payload), expected_version=first_ledger.version
    )
    first_run = client.post(
        f"{_AUDIT_SESSION_PATH}/{first['audit_id']}/run", headers=headers_a
    )
    assert first_run.status_code == 200, first_run.text
    retry = client.post(
        f"{_AUDIT_SESSION_PATH}/{first['audit_id']}/run", headers=headers_a
    )
    assert retry.status_code == 200
    assert calls == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=prior_period) == 0
    assert get_usage(backend, tenant_id="tenant-A", period_key=execution_period) == 1

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
    assert get_usage(backend, tenant_id="tenant-B", period_key=execution_period) == 1

    # The already-completed audit is retried in a later month. It returns idempotently without
    # consuming the later month's allowance or calling the provider again.
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.current_monthly_period_key",
        lambda: next_period,
    )
    cross_month_retry = client.post(
        f"{_AUDIT_SESSION_PATH}/{first['audit_id']}/run", headers=headers_a
    )
    assert cross_month_retry.status_code == 200
    assert calls == 2
    assert get_usage(backend, tenant_id="tenant-A", period_key=next_period) == 0


def test_ownership_failure_reconciles_persisted_result_without_provider_replay(
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

    from api.routes import cas_harness_audit as audit_routes

    real_ownership_write = audit_routes._record_audit_evidence_ownership
    fail_once = True

    def fail_ownership(*args, **kwargs):
        nonlocal fail_once
        if fail_once:
            raise HTTPException(
                status_code=503, detail="Evidence ownership persistence is unavailable."
            )
        return real_ownership_write(*args, **kwargs)

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
    assert record is not None and record.status == "DRAFT"
    assert record.provider_run_phase == "EVIDENCE_PERSISTED"
    assert record.provider_result_checkpoint is not None
    assert calls == 1

    fail_once = False
    retried = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["status"] == "COMPLETE"
    assert calls == 1
    recovered = get_audit_session(
        audit_id, tenant_id="tenant-A", account_id=account.account_id
    )
    assert recovered is not None
    assert recovered.provider_run_phase == "FINALIZED"
    assert recovered.run_state is None and recovered.run_lease_until is None


def test_ambiguous_provider_failure_is_orphaned_and_retry_never_calls_again(
    account_audit_client, monkeypatch
):
    client, store, backend = account_audit_client
    first_period = "2026-07"
    later_period = "2026-08"
    monkeypatch.setattr(settings, "quotas_enabled", True)
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.get_quota_limit", lambda: 10
    )
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.current_monthly_period_key",
        lambda: first_period,
    )
    headers, account = _provision_login(
        client,
        store,
        code="provider-orphan",
        identity="provider-orphan@example.com",
        role="member",
        tenant_id="tenant-A",
    )
    calls = 0

    async def crash_after_request_started(**kwargs):
        nonlocal calls
        calls += 1
        kwargs["on_request_started"]()
        raise RuntimeError("connection ended after provider may have accepted request")

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.run_live_worker_audit",
        crash_after_request_started,
    )
    created = client.post(
        _AUDIT_SESSION_PATH,
        json={
            "model_id": "EleutherAI/pythia-160m",
            "audit_mode": "BALANCED",
            "prompt": "provider ambiguity must never replay",
            "selected_modules": ["active_trace"],
        },
        headers=headers,
    )
    assert created.status_code == 200
    audit_id = created.json()["audit_id"]

    first = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert first.status_code == 503
    assert first.json()["detail"]["code"] == "provider_run_reconciliation_required"
    record = get_audit_session(
        audit_id, tenant_id="tenant-A", account_id=account.account_id
    )
    assert record is not None
    assert record.provider_run_phase == "ORPHANED"
    assert record.provider_result_checkpoint is None
    assert get_usage(backend, tenant_id="tenant-A", period_key=first_period) == 1

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.current_monthly_period_key",
        lambda: later_period,
    )
    retry = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert retry.status_code == 409
    assert retry.json()["detail"]["code"] == "provider_run_reconciliation_required"
    assert calls == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=later_period) == 0


def test_provider_completed_crash_resumes_checkpoint_without_provider_replay(
    account_audit_client, monkeypatch
):
    client, store, _backend = account_audit_client
    headers, account = _provision_login(
        client,
        store,
        code="provider-completed-recovery",
        identity="provider-completed@example.com",
        role="member",
        tenant_id="tenant-A",
    )
    calls = 0
    trace_id = "trace-provider-completed-recovery"

    async def crash_after_provider_completed(**kwargs):
        nonlocal calls
        calls += 1
        result = _fake_live_result(trace_id)
        kwargs["on_request_started"]()
        kwargs["on_provider_completed"](
            {
                "schema_version": "cas_harness_provider_result_checkpoint.v1",
                "runner": "live_worker",
                "trace_id": trace_id,
                "evidence_packet": result.evidence_packet,
                "proof_chips": result.proof_chips,
                "verifier_decision": result.verifier_decision,
                "message": result.message,
                "audit_scope": result.audit_scope,
            }
        )
        raise RuntimeError("process crashed before Evidence Packet persistence")

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.run_live_worker_audit",
        crash_after_provider_completed,
    )
    # The retry exercises route reconciliation, while this test double avoids
    # requiring a fully formed packet file unrelated to the provider journal.
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.persist_live_worker_result",
        lambda *_args, **_kwargs: None,
    )
    created = client.post(
        _AUDIT_SESSION_PATH,
        json={
            "model_id": "EleutherAI/pythia-160m",
            "audit_mode": "BALANCED",
            "prompt": "resume provider result checkpoint",
            "selected_modules": ["active_trace"],
        },
        headers=headers,
    )
    assert created.status_code == 200
    audit_id = created.json()["audit_id"]

    first = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert first.status_code == 503
    assert first.json()["detail"]["code"] == "provider_evidence_reconciliation_pending"
    checkpointed = get_audit_session(
        audit_id, tenant_id="tenant-A", account_id=account.account_id
    )
    assert checkpointed is not None
    assert checkpointed.provider_run_phase == "PROVIDER_COMPLETED"

    retry = client.post(f"{_AUDIT_SESSION_PATH}/{audit_id}/run", headers=headers)
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "COMPLETE"
    assert calls == 1
    recovered = get_audit_session(
        audit_id, tenant_id="tenant-A", account_id=account.account_id
    )
    assert recovered is not None and recovered.provider_run_phase == "FINALIZED"


def test_account_mode_no_token_run_is_401(account_audit_client, monkeypatch):
    """Account mode + no Bearer token on the run route -> the middleware 401s (route left the
    allowlist). No ownership row, no run."""
    client, _store, _backend = account_audit_client
    resp = client.post(f"{_AUDIT_SESSION_PATH}/whatever/run")
    assert resp.status_code == 401, resp.text
