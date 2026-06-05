"""Per-tenant evidence isolation — the launch/paid-tenant-isolation security layer.

Two layers, both load-bearing:

* **Dark-mode no-regression** (default, ``accounts_enabled`` off): GET / verify / anchor on known
  dev + Stage 9 traces behave EXACTLY as today with the legacy shared-secret token. No ownership
  enforcement, anchor still reachable (HTTP 200). This proves the security layer is a complete
  no-op in the legacy posture — the non-negotiable invariant. (These overlap intentionally with
  ``test_evidence_routes.py`` so a regression shows up here too.)

* **Account-mode enforcement** (``accounts_enabled`` True): per-tenant ownership is enforced on the
  evidence routes, and the anchor route additionally requires an operator/admin/owner role.
  Tenant A can read/verify a trace it owns; tenant B gets 404 (never 403 — existence is not leaked);
  a member-role identity cannot anchor even its own owned trace.

Plus direct UNIT tests of the store functions and the conditional role gate against a real
``SqliteStateStore``, covering cross-tenant isolation and the ``accounts_enabled`` branch.

Run ONLY this file:
    python -m pytest tests/test_evidence_ownership.py -q
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from api.config import settings
from api.dependencies.authz import require_role, require_role_in_account_mode
from api.services.accounts.store import AccountStore
from api.services.evidence_ownership import (
    EVIDENCE_OWNERSHIP_KIND,
    record_evidence_ownership,
    tenant_owns_trace,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore

# Trace ids reused from test_evidence_routes.py so the dark-mode assertions track the real routes.
_DEV_TRACE_ID = "dev_example_001"
_STAGE9_40E_PYTHIA_TRACE_ID = "pythia-160m-stage9-40e-readout-20260531"


@pytest.fixture
def isolated_anchor_store(tmp_path, monkeypatch):
    """Isolate the evidence-packet store and force the honest default anchor mode (NOT WORM).

    A local copy of the fixture in test_evidence_routes.py (it is defined there, not in conftest):
    anchoring writes the anchored copy to the packet store, so point it at a tmp dir and clear the
    S3 anchor envs so the mode is the safe default (disabled). Used only by the anchor tests that
    expect to reach the handler.
    """
    from api.services.cas_harness_merged_evidence_packets import (
        reset_merged_fleet_evidence_packets_for_tests,
    )

    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    for var in (
        "CAS_HARNESS_EVIDENCE_ANCHOR_MODE",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS",
    ):
        monkeypatch.delenv(var, raising=False)
    reset_merged_fleet_evidence_packets_for_tests()
    yield tmp_path
    reset_merged_fleet_evidence_packets_for_tests()


# ===========================================================================
# (E) UNIT TESTS — store functions + the conditional role gate.
# ===========================================================================


@pytest.fixture
def backend(tmp_path) -> SqliteStateStore:
    """A fresh durable SQLite-backed StateStore per test (mirrors test_accounts_invites.py)."""
    store = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    try:
        yield store
    finally:
        store.close()


def test_tenant_owns_trace_false_before_record(backend):
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="traceX") is False


def test_record_then_owns_is_true(backend):
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id="acct-A", trace_id="traceX"
    )
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="traceX") is True


def test_cross_tenant_get_returns_none(backend):
    """The isolation primitive: a trace owned by tenant A is invisible to tenant B's read."""
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id="acct-A", trace_id="traceX"
    )
    # Direct store read: cross-tenant get is None (indistinguishable from absent).
    assert backend.get("tenant-B", EVIDENCE_OWNERSHIP_KIND, "traceX") is None
    # And the helper reports the same: tenant B does not own tenant A's trace.
    assert tenant_owns_trace(backend, tenant_id="tenant-B", trace_id="traceX") is False
    # Tenant A still owns it.
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="traceX") is True


def test_record_is_idempotent_no_raise_on_duplicate(backend):
    """Recording ownership twice for the same (tenant, trace) is a no-op, never a VersionConflict."""
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id="acct-A", trace_id="traceX"
    )
    # Second call must not raise and must not mint a second record.
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id="acct-A", trace_id="traceX"
    )
    rows = backend.list("tenant-A", EVIDENCE_OWNERSHIP_KIND)
    assert len(rows) == 1
    assert rows[0].record_id == "traceX"
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="traceX") is True


def test_record_carries_traceability_envelope(backend):
    """Every object knows where it came from: source / trace_id / version / created_at present."""
    record_evidence_ownership(
        backend,
        tenant_id="tenant-A",
        account_id="acct-A",
        trace_id="traceX",
        source="cas_harness_audit",
    )
    rec = backend.get("tenant-A", EVIDENCE_OWNERSHIP_KIND, "traceX")
    assert rec is not None
    assert rec.source == "cas_harness_audit"
    assert rec.trace_id == "traceX"
    assert rec.version == 1  # put(expected_version=0) promotes a v0 record to v1
    assert rec.created_at is not None
    assert rec.payload["account_id"] == "acct-A"
    assert rec.payload["trace_id"] == "traceX"


def test_same_trace_id_distinct_tenants_are_independent(backend):
    """Two tenants may legitimately own the SAME trace_id string as unrelated rows."""
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id="acct-A", trace_id="shared"
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-B", account_id="acct-B", trace_id="shared"
    )
    assert tenant_owns_trace(backend, tenant_id="tenant-A", trace_id="shared") is True
    assert tenant_owns_trace(backend, tenant_id="tenant-B", trace_id="shared") is True
    a = backend.get("tenant-A", EVIDENCE_OWNERSHIP_KIND, "shared")
    b = backend.get("tenant-B", EVIDENCE_OWNERSHIP_KIND, "shared")
    assert a is not None and b is not None
    assert a.payload["account_id"] == "acct-A"
    assert b.payload["account_id"] == "acct-B"


# --- conditional role gate: the accounts_enabled branch --------------------


def _request_with_role(role: str | None) -> Request:
    """Minimal ASGI Request whose request.state.role is `role` (or absent when None)."""
    req = Request({"type": "http", "headers": [], "method": "POST", "path": "/x"})
    if role is not None:
        req.state.role = role
    return req


def test_require_role_in_account_mode_is_noop_when_accounts_disabled(monkeypatch):
    """Dark default: the gate returns None and does NOT 401, even with no identity on the request."""
    monkeypatch.setattr(settings, "accounts_enabled", False)
    gate = require_role_in_account_mode("operator", "admin", "owner")
    # No request.state.role at all — in dark mode this must be a pass-through (None), not a 401.
    assert gate(_request_with_role(None)) is None


def test_require_role_in_account_mode_enforces_when_accounts_enabled(monkeypatch):
    """Account mode: behaves exactly like require_role — 401 no identity, 403 wrong role, role ok."""
    monkeypatch.setattr(settings, "accounts_enabled", True)
    gate = require_role_in_account_mode("operator", "admin", "owner")

    # No identity -> 401.
    with pytest.raises(HTTPException) as no_identity:
        gate(_request_with_role(None))
    assert no_identity.value.status_code == 401

    # Identity present but not permitted -> 403.
    with pytest.raises(HTTPException) as wrong_role:
        gate(_request_with_role("member"))
    assert wrong_role.value.status_code == 403

    # Permitted role -> returns the role.
    assert gate(_request_with_role("operator")) == "operator"


def test_require_role_in_account_mode_rejects_empty_roles():
    """Same programming-error guard as require_role: a gate that admits everyone is refused."""
    with pytest.raises(ValueError):
        require_role_in_account_mode()


# ===========================================================================
# (E) DARK-MODE NO-REGRESSION — accounts off (default), legacy token.
# ===========================================================================


def test_dark_mode_get_dev_fixture_still_200(client, auth_headers):
    """With accounts off, GET on a known trace behaves exactly as today (no ownership gate)."""
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["trace_id"] == _DEV_TRACE_ID


def test_dark_mode_verify_dev_fixture_still_reachable(client, auth_headers):
    """Verify is reachable and never 401/404-from-ownership in dark mode (200, real verify body)."""
    resp = client.post(f"/evidence/{_DEV_TRACE_ID}/verify", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["trace_id"] == _DEV_TRACE_ID


def test_dark_mode_anchor_still_reachable_with_legacy_token(
    client, auth_headers, isolated_anchor_store
):
    """The load-bearing dark-mode check: anchor (an operator action in account mode) is STILL
    reachable with the legacy shared-secret token when accounts are off — the conditional role gate
    must NOT 401/403 here. Honest default is NOT WORM, console stays at human review."""
    resp = client.post(
        f"/evidence/{_STAGE9_40E_PYTHIA_TRACE_ID}/anchor", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trace_id"] == _STAGE9_40E_PYTHIA_TRACE_ID
    assert body["worm_retained"] is False
    assert body["console_state"] == "flag_for_human_review"


def test_dark_mode_unknown_trace_still_404(client, auth_headers):
    """Unknown trace contract is preserved byte-for-byte in dark mode."""
    resp = client.get("/evidence/this_trace_id_does_not_exist_xyz_42", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "trace_id not found"


# ===========================================================================
# (E) ACCOUNT-MODE INTEGRATION — accounts_enabled True, per-tenant isolation.
# ===========================================================================


@pytest.fixture
def tenant_iso_client(tmp_path, monkeypatch):
    """A TestClient with accounts_enabled=True, durable account/session stores AND a state ledger
    on app.state, all sharing ONE SqliteStateStore backend.

    Mirrors test_accounts_invites.py's accounts_login_client, and additionally installs
    ``app.state.state_ledger`` (a handle exposing ``.store``) so the evidence ownership ledger that
    ``_require_evidence_access`` reads is live. Enter with the flag OFF (lifespan installs nothing),
    then flip ``accounts_enabled`` on and install temp-path stores directly — the route/middleware
    code reads ``settings.accounts_enabled`` per request, so the flip takes effect for every call.

    Yields ``(client, account_store, backend)``.
    """
    from api.main import app

    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    acct_store = AccountStore(backend)
    session_store = SessionStore(backend)

    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        prev_ledger = getattr(app.state, "state_ledger", None)
        app.state.account_store = acct_store
        app.state.session_store = session_store
        # The evidence guard reads app.state.state_ledger.store. Install a minimal handle exposing
        # the SAME backend so ownership rows written below are visible to the route guard.
        app.state.state_ledger = SimpleNamespace(store=backend)
        try:
            yield client, acct_store, backend
        finally:
            app.state.account_store = None
            app.state.session_store = None
            app.state.state_ledger = prev_ledger
            backend.close()


def _provision_login(client, store, *, code, identity, role, tenant_id):
    """Create+redeem an invite and log in; returns the account-mode bearer headers + account."""
    invite = store.create_invite(code=code, role=role, tenant_id=tenant_id)
    account = store.redeem_invite(code=invite.code, email_or_username=identity)
    resp = client.post("/auth/token", json={"username": identity})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}, account


def test_account_mode_owner_can_get_and_verify_its_trace(tenant_iso_client):
    """Tenant A records ownership of the dev trace, then A's GET and verify succeed (200)."""
    client, store, backend = tenant_iso_client
    headers_a, account_a = _provision_login(
        client, store, code="iso-a-1", identity="a@example.com", role="member",
        tenant_id="tenant-A",
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id=account_a.account_id,
        trace_id=_DEV_TRACE_ID,
    )

    got = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=headers_a)
    assert got.status_code == 200, got.text
    assert got.json()["trace_id"] == _DEV_TRACE_ID

    verified = client.post(f"/evidence/{_DEV_TRACE_ID}/verify", headers=headers_a)
    assert verified.status_code == 200, verified.text
    assert verified.json()["trace_id"] == _DEV_TRACE_ID


def test_account_mode_other_tenant_gets_404_not_403(tenant_iso_client):
    """Tenant B has NOT recorded ownership of A's trace -> GET and anchor return 404 (no 403 leak)."""
    client, store, backend = tenant_iso_client
    # Tenant A owns the dev trace.
    _, account_a = _provision_login(
        client, store, code="iso-a-2", identity="a2@example.com", role="member",
        tenant_id="tenant-A",
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id=account_a.account_id,
        trace_id=_DEV_TRACE_ID,
    )
    # Tenant B logs in but owns nothing.
    headers_b, _account_b = _provision_login(
        client, store, code="iso-b-1", identity="b@example.com", role="operator",
        tenant_id="tenant-B",
    )

    got = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=headers_b)
    assert got.status_code == 404
    assert got.json()["detail"] == "trace_id not found"

    # Anchor too: B is an operator (passes the role gate) but does not own the trace -> 404.
    anchored = client.post(
        f"/evidence/{_STAGE9_40E_PYTHIA_TRACE_ID}/anchor", headers=headers_b
    )
    assert anchored.status_code == 404
    assert anchored.json()["detail"] == "trace_id not found"


def test_account_mode_no_identity_is_401(tenant_iso_client):
    """Account mode + no bearer token -> the middleware 401s before the ownership guard even runs."""
    client, _store, _backend = tenant_iso_client
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}")
    assert resp.status_code == 401


def test_account_mode_member_cannot_anchor_owned_trace_403(tenant_iso_client):
    """A member-role identity that OWNS its trace still cannot anchor: the role gate returns 403.

    Ownership passes (member owns the Stage 9 trace), so the only thing that can deny is the
    operator/admin/owner role gate — proving the gate is live and enforced in account mode.
    """
    client, store, backend = tenant_iso_client
    headers_member, account_m = _provision_login(
        client, store, code="iso-m-1", identity="member-anchor@example.com",
        role="member", tenant_id="tenant-M",
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-M", account_id=account_m.account_id,
        trace_id=_STAGE9_40E_PYTHIA_TRACE_ID,
    )
    resp = client.post(
        f"/evidence/{_STAGE9_40E_PYTHIA_TRACE_ID}/anchor", headers=headers_member
    )
    assert resp.status_code == 403, resp.text


def test_account_mode_operator_anchor_not_blocked_by_role_gate(
    tenant_iso_client, isolated_anchor_store
):
    """An operator-role identity that owns its trace is NOT blocked by the role gate (reaches the
    handler -> 200, honest NOT-WORM default). Contrast with the member 403 above."""
    client, store, backend = tenant_iso_client
    headers_op, account_op = _provision_login(
        client, store, code="iso-op-1", identity="operator-anchor@example.com",
        role="operator", tenant_id="tenant-OP",
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-OP", account_id=account_op.account_id,
        trace_id=_STAGE9_40E_PYTHIA_TRACE_ID,
    )
    resp = client.post(
        f"/evidence/{_STAGE9_40E_PYTHIA_TRACE_ID}/anchor", headers=headers_op
    )
    # Not a 403 from the gate, and not a 401: the operator passed both ownership and role checks.
    assert resp.status_code == 200, resp.text
    assert resp.json()["trace_id"] == _STAGE9_40E_PYTHIA_TRACE_ID
