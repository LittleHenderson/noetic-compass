"""Spine §2 gate — account model + invite redemption + identity login.

Two layers:

* **Store layer** (``AccountStore`` over a temp ``SqliteStateStore``, mirroring
  ``test_state_substrate_sqlite.py``'s tmp_path factory): the fail-closed + atomic redemption
  invariants. Invalid / expired / used / over-limit codes are refused; a valid invite activates
  EXACTLY ONE account with SERVER-DERIVED role/tenant; a single-use code cannot be redeemed twice;
  a body-supplied role/tenant is impossible to inject (the redeem API has no such parameter and the
  account inherits the INVITE's role/tenant).

* **Login layer** (``/auth/token`` with ``accounts_enabled=True`` and a store on ``app.state``):
  an unknown identity cannot log in, a disabled account cannot log in, and a valid login mints a
  token carrying the account's server-derived ``account_id``/``tenant_id``/``role``.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_accounts_invites.py -q
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from api.config import settings
from api.services.accounts.models import ACCOUNT_KIND
from api.services.accounts.store import AccountStore, InviteRedemptionError
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


# --- store-layer fixtures --------------------------------------------------


@pytest.fixture
def store(tmp_path) -> AccountStore:
    """A durable account store on a fresh per-test SQLite file."""
    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    return AccountStore(backend)


def _future_iso(seconds: int = 3600) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()


def _past_iso(seconds: int = 3600) -> str:
    return (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()


# --- redeem: fail-closed cases --------------------------------------------


def test_unknown_code_rejected(store):
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code="does-not-exist", email_or_username="a@example.com")
    assert exc.value.reason == "unknown_code"


def test_expired_invite_rejected(store):
    invite = store.create_invite(code="exp-code", expires_at=_past_iso())
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code=invite.code, email_or_username="a@example.com")
    assert exc.value.reason == "not_redeemable"


def test_used_invite_rejected(store):
    # A single-use invite, redeemed once, cannot be redeemed again by a DIFFERENT identity.
    invite = store.create_invite(code="one-use", max_uses=1)
    store.redeem_invite(code=invite.code, email_or_username="first@example.com")
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code=invite.code, email_or_username="second@example.com")
    assert exc.value.reason == "not_redeemable"


def test_over_limit_invite_rejected(store):
    # max_uses=2: third distinct redemption is refused.
    invite = store.create_invite(code="two-use", max_uses=2)
    store.redeem_invite(code=invite.code, email_or_username="u1@example.com")
    store.redeem_invite(code=invite.code, email_or_username="u2@example.com")
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code=invite.code, email_or_username="u3@example.com")
    assert exc.value.reason == "not_redeemable"


def test_blank_identity_rejected(store):
    invite = store.create_invite(code="blank-id")
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code=invite.code, email_or_username="   ")
    assert exc.value.reason == "invalid_identity"


def test_target_email_mismatch_rejected(store):
    invite = store.create_invite(code="pinned", target_email="invited@example.com")
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code=invite.code, email_or_username="someone-else@example.com")
    assert exc.value.reason == "email_mismatch"


# --- redeem: success + EXACTLY ONE account --------------------------------


def test_valid_invite_activates_exactly_one_account(store):
    invite = store.create_invite(code="good", role="member", tenant_id="tenant-X")
    account = store.redeem_invite(
        code=invite.code, email_or_username="New.User@Example.com", display_name="New User"
    )

    # Server-derived claims come from the INVITE, not the request.
    assert account.role == "member"
    assert account.tenant_id == "tenant-X"
    assert account.status == "active"
    # Email is normalized (lowercased/trimmed) by the store.
    assert account.email_or_username == "new.user@example.com"
    assert account.display_name == "New User"
    assert account.account_id  # server-derived, non-empty

    # Exactly ONE account record exists in the ledger (under the single storage tenant; the
    # granted tenant "tenant-X" lives in the payload/claims, not as the storage key).
    backend = store._store  # the underlying StateStore (test-only introspection)
    accounts = backend.list(store._tenant, ACCOUNT_KIND)
    assert len(accounts) == 1
    assert accounts[0].record_id == account.account_id
    assert accounts[0].payload["tenant_id"] == "tenant-X"


def test_redeem_is_idempotent_for_same_code_and_email(store):
    # A re-delivery of the SAME (code, email) returns the SAME account and never mints a second.
    invite = store.create_invite(code="idem", max_uses=1)
    first = store.redeem_invite(code=invite.code, email_or_username="dup@example.com")
    second = store.redeem_invite(code=invite.code, email_or_username="dup@example.com")
    assert first.account_id == second.account_id
    # The single use was not double-consumed (the second call returned the existing account).
    refreshed = store.get_invite(invite.code)
    assert refreshed is not None
    assert refreshed.uses == 1


def test_single_use_code_cannot_be_redeemed_twice(store):
    # Distinct identities racing a single-use code: the second is refused, and only ONE account
    # exists afterwards.
    invite = store.create_invite(code="single", max_uses=1, tenant_id="t1")
    store.redeem_invite(code=invite.code, email_or_username="winner@example.com")
    with pytest.raises(InviteRedemptionError):
        store.redeem_invite(code=invite.code, email_or_username="loser@example.com")

    accounts = store._store.list(store._tenant, ACCOUNT_KIND)
    assert len(accounts) == 1


def test_email_uniqueness_across_invites(store):
    # The same email cannot be claimed by two different invite codes.
    inv_a = store.create_invite(code="code-a", max_uses=1)
    inv_b = store.create_invite(code="code-b", max_uses=1)
    store.redeem_invite(code=inv_a.code, email_or_username="shared@example.com")
    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(code=inv_b.code, email_or_username="shared@example.com")
    assert exc.value.reason == "email_taken"


def test_use_count_increments_on_redeem(store):
    invite = store.create_invite(code="counter", max_uses=3)
    store.redeem_invite(code=invite.code, email_or_username="c1@example.com")
    store.redeem_invite(code=invite.code, email_or_username="c2@example.com")
    refreshed = store.get_invite(invite.code)
    assert refreshed is not None
    assert refreshed.uses == 2
    assert refreshed.redeemed_by is not None  # first redeemer recorded for traceability


def test_get_account_by_email_resolves_server_derived_identity(store):
    invite = store.create_invite(code="lookup", role="member", tenant_id="t-look")
    account = store.redeem_invite(code=invite.code, email_or_username="Look@Example.com")
    # Lookup is case-insensitive (normalized) and returns the same server-derived account.
    found = store.get_account_by_email("look@example.com")
    assert found is not None
    assert found.account_id == account.account_id
    assert found.role == "member"
    assert found.tenant_id == "t-look"


# --- login layer (/auth/token, accounts_enabled=True) ---------------------


@pytest.fixture
def accounts_login_client(tmp_path, monkeypatch):
    """A TestClient with accounts_enabled=True and a durable account store on app.state.

    Yields ``(client, store)``. We enter the app with the flag still OFF so the lifespan installs
    NO store (and writes no stray ledger file), then flip ``accounts_enabled`` on and install our
    temp-path store directly. The route/login code reads ``settings.accounts_enabled`` per request,
    so the post-startup flip takes effect for every call in the test.
    """
    from api.main import app

    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    acct_store = AccountStore(backend)

    # debug stays True (root conftest) so _authorize_mint's open path is permitted; the account
    # existence check is what gates identity in this posture.
    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        app.state.account_store = acct_store
        yield client, acct_store


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def test_unknown_user_cannot_log_in_when_accounts_enabled(accounts_login_client):
    client, _store = accounts_login_client
    resp = client.post("/auth/token", json={"username": "ghost@example.com"})
    assert resp.status_code == 401
    assert "no account" in resp.json()["detail"].lower()


def test_valid_login_binds_server_derived_claims(accounts_login_client):
    client, store = accounts_login_client
    invite = store.create_invite(code="login-good", role="member", tenant_id="tenant-L")
    account = store.redeem_invite(code=invite.code, email_or_username="member@example.com")

    resp = client.post("/auth/token", json={"username": "member@example.com"})
    assert resp.status_code == 200
    claims = _decode(resp.json()["token"])
    # Server-derived claims, straight from the account record.
    assert claims["account_id"] == account.account_id
    assert claims["tenant_id"] == "tenant-L"
    assert claims["role"] == "member"
    assert claims["sub"] == "member@example.com"


def test_disabled_account_cannot_log_in(accounts_login_client, tmp_path):
    client, store = accounts_login_client
    invite = store.create_invite(code="to-disable", role="member", tenant_id="t-dis")
    account = store.redeem_invite(code=invite.code, email_or_username="disable-me@example.com")

    # Disable the account directly in the durable store (a real admin path lands in a later PR).
    backend = store._store
    rec = backend.get(store._tenant, ACCOUNT_KIND, account.account_id)
    assert rec is not None
    disabled_payload = dict(rec.payload)
    disabled_payload["status"] = "disabled"
    backend.put(rec.with_payload(disabled_payload), expected_version=rec.version)

    resp = client.post("/auth/token", json={"username": "disable-me@example.com"})
    assert resp.status_code == 401
    assert "disabled" in resp.json()["detail"].lower()


def test_body_supplied_tenant_and_role_are_ignored_on_login(accounts_login_client):
    client, store = accounts_login_client
    invite = store.create_invite(code="no-inject", role="member", tenant_id="real-tenant")
    store.redeem_invite(code=invite.code, email_or_username="honest@example.com")

    # A client tries to smuggle elevated role + a different tenant in the body.
    resp = client.post(
        "/auth/token",
        json={
            "username": "honest@example.com",
            "role": "owner",
            "tenant_id": "attacker-tenant",
            "account_id": "acct-attacker",
        },
    )
    assert resp.status_code == 200
    claims = _decode(resp.json()["token"])
    # The injected values are ignored; claims reflect the SERVER-derived account record.
    assert claims["role"] == "member"
    assert claims["tenant_id"] == "real-tenant"
    assert claims["account_id"] != "acct-attacker"


# --- redeem via the public route ------------------------------------------


def test_redeem_route_creates_one_account_and_is_fail_closed(accounts_login_client):
    client, store = accounts_login_client
    invite = store.create_invite(code="route-code", role="member", tenant_id="t-route")

    # Body tries to inject role/tenant — the redeem model has no such fields, so they are ignored.
    ok = client.post(
        "/accounts/invite/redeem",
        json={
            "code": invite.code,
            "email_or_username": "router@example.com",
            "role": "owner",
            "tenant_id": "attacker",
        },
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["role"] == "member"          # server-derived from invite
    assert body["tenant_id"] == "t-route"    # server-derived from invite
    assert body["status"] == "active"

    # Re-redeeming a single-use code with a different identity fails closed (single 400 shape).
    bad = client.post(
        "/accounts/invite/redeem",
        json={"code": invite.code, "email_or_username": "late@example.com"},
    )
    assert bad.status_code == 400
