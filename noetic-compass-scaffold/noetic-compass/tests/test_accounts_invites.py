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
from api.middleware.auth import create_token
from api.services.accounts.credentials import (
    CREDENTIAL_VERSION,
    LEGACY_CREDENTIAL_VERSION,
    legacy_hash_account_credential,
)
from api.services.accounts.models import ACCOUNT_KIND, INVITE_KIND, invite_code_hash
from api.services.accounts.store import AccountStore, InviteRedemptionError
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore

TEST_API_CREDENTIAL = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
ROTATED_API_CREDENTIAL = "casak_ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210abcdefgh"


def _install_default_test_credential(account_store: AccountStore) -> AccountStore:
    redeem = account_store.redeem_invite

    def redeem_with_default(*, api_credential: str = TEST_API_CREDENTIAL, **kwargs):
        return redeem(api_credential=api_credential, **kwargs)

    account_store.redeem_invite = redeem_with_default  # type: ignore[method-assign]
    return account_store


# --- store-layer fixtures --------------------------------------------------


@pytest.fixture
def store(tmp_path) -> AccountStore:
    """A durable account store on a fresh per-test SQLite file."""
    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    account_store = AccountStore(
        backend, credential_pepper="test-account-credential-pepper-0123456789"
    )
    return _install_default_test_credential(account_store)


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


def test_invite_payload_stores_hash_not_raw_code(store):
    invite = store.create_invite(code="raw-bearer-secret", role="member", tenant_id="tenant-hash")

    records = store._store.list(store._tenant, INVITE_KIND)
    assert len(records) == 1
    payload = records[0].payload
    assert "code" not in payload
    assert payload["code_hash"] == invite_code_hash(invite.code)
    assert "raw-bearer-secret" not in repr(payload)

    # Lookup/redeem still works because the caller presents the raw code and the store resolves the
    # digest-backed record id; the stored payload never has to reveal the bearer credential.
    refreshed = store.get_invite(invite.code)
    assert refreshed is not None
    assert refreshed.code == ""
    assert refreshed.code_hash == invite_code_hash(invite.code)
    account = store.redeem_invite(code=invite.code, email_or_username="hash@example.com")
    assert account.tenant_id == "tenant-hash"


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
    """A TestClient with accounts_enabled=True and durable account/session stores on app.state.

    Yields ``(client, account_store, session_store)``. We enter the app with the flag still OFF so
    the lifespan installs NO store (and writes no stray ledger file), then flip ``accounts_enabled``
    on and install temp-path stores directly. The route/login/middleware code reads
    ``settings.accounts_enabled`` per request, so the post-startup flip takes effect for every call
    in the test.
    """
    from api.main import app

    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    acct_store = AccountStore(
        backend, credential_pepper="test-account-credential-pepper-0123456789"
    )
    _install_default_test_credential(acct_store)
    session_store = SessionStore(backend)

    # debug stays True (root conftest) so _authorize_mint's open path is permitted; the account
    # existence check is what gates identity in this posture.
    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        app.state.account_store = acct_store
        app.state.session_store = session_store
        try:
            yield client, acct_store, session_store
        finally:
            app.state.account_store = None
            app.state.session_store = None


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def test_unknown_user_cannot_log_in_when_accounts_enabled(accounts_login_client):
    client, _store, _sessions = accounts_login_client
    resp = client.post("/auth/token", json={"username": "ghost@example.com", "api_credential": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid account credentials."


def test_bootstrap_route_is_header_gated_and_recovers_first_owner(
    accounts_login_client, monkeypatch
):
    client, _store, sessions = accounts_login_client
    secret = "bootstrap-secret-at-least-thirty-two-bytes-long"
    monkeypatch.setattr(settings, "account_bootstrap_secret", secret)
    monkeypatch.setattr(settings, "accounts_bootstrap_tenant_id", "primary")
    body = {
        "email_or_username": "first-owner@example.com",
        "api_credential": TEST_API_CREDENTIAL,
    }

    denied = client.post(
        "/accounts/bootstrap",
        json=body,
        headers={"X-Account-Bootstrap-Secret": "wrong"},
    )
    assert denied.status_code == 401
    created = client.post(
        "/accounts/bootstrap",
        json=body,
        headers={"X-Account-Bootstrap-Secret": secret},
    )
    assert created.status_code == 200, created.text
    assert created.headers["cache-control"] == "no-store"
    assert TEST_API_CREDENTIAL not in created.text
    assert created.json()["api_credential"] is None

    token, claims = _login_token(
        client, "first-owner@example.com", TEST_API_CREDENTIAL
    )
    recovered_body = dict(body, api_credential=ROTATED_API_CREDENTIAL)
    recovered = client.post(
        "/accounts/bootstrap",
        json=recovered_body,
        headers={"X-Account-Bootstrap-Secret": secret},
    )
    assert recovered.status_code == 200, recovered.text
    assert ROTATED_API_CREDENTIAL not in recovered.text
    assert sessions.get_session(claims["jti"]).is_revoked
    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 401
    assert client.post(
        "/auth/token",
        json={
            "username": "first-owner@example.com",
            "api_credential": ROTATED_API_CREDENTIAL,
        },
    ).status_code == 200


def test_valid_login_binds_server_derived_claims(accounts_login_client):
    client, store, sessions = accounts_login_client
    invite = store.create_invite(code="login-good", role="member", tenant_id="tenant-L")
    account = store.redeem_invite(code=invite.code, email_or_username="member@example.com")

    resp = client.post(
        "/auth/token",
        json={"username": "member@example.com", "api_credential": account.api_credential},
    )
    assert resp.status_code == 200
    claims = _decode(resp.json()["token"])
    # Server-derived claims, straight from the account record.
    assert claims["account_id"] == account.account_id
    assert claims["tenant_id"] == "tenant-L"
    assert claims["role"] == "member"
    assert claims["sub"] == "member@example.com"
    assert claims["jti"]

    session = sessions.get_session(claims["jti"])
    assert session is not None
    assert session.is_live()
    assert session.account_id == account.account_id
    assert session.tenant_id == "tenant-L"


def test_legacy_v1_credential_is_verified_then_atomically_upgraded(accounts_login_client):
    _client, store, _sessions = accounts_login_client
    invite = store.create_invite(code="legacy-upgrade", role="owner", tenant_id="tenant-old")
    account = store.redeem_invite(
        code=invite.code, email_or_username="legacy-owner@example.com"
    )
    record = store._store.get(store._tenant, ACCOUNT_KIND, account.account_id)
    assert record is not None
    legacy_payload = dict(record.payload)
    legacy_payload["credential_hash"] = legacy_hash_account_credential(
        account.api_credential
    )
    legacy_payload["credential_version"] = LEGACY_CREDENTIAL_VERSION
    store._store.put(
        record.with_payload(legacy_payload), expected_version=record.version
    )

    assert store.has_active_owner() is True
    assert store.authenticate_account(account.email_or_username, "wrong") is None
    still_legacy = store.get_account_by_id(account.account_id)
    assert still_legacy.credential_version == LEGACY_CREDENTIAL_VERSION

    upgraded = store.authenticate_account(
        account.email_or_username, account.api_credential
    )
    assert upgraded is not None
    assert upgraded.credential_version == CREDENTIAL_VERSION
    assert upgraded.auth_epoch == account.auth_epoch + 1
    assert upgraded.credential_hash != legacy_payload["credential_hash"]


def test_disabled_account_cannot_log_in(accounts_login_client, tmp_path):
    client, store, _sessions = accounts_login_client
    invite = store.create_invite(code="to-disable", role="member", tenant_id="t-dis")
    account = store.redeem_invite(code=invite.code, email_or_username="disable-me@example.com")

    # Disable the account directly in the durable store (a real admin path lands in a later PR).
    backend = store._store
    rec = backend.get(store._tenant, ACCOUNT_KIND, account.account_id)
    assert rec is not None
    disabled_payload = dict(rec.payload)
    disabled_payload["status"] = "disabled"
    backend.put(rec.with_payload(disabled_payload), expected_version=rec.version)

    resp = client.post(
        "/auth/token",
        json={"username": "disable-me@example.com", "api_credential": account.api_credential},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid account credentials."


def test_body_supplied_tenant_and_role_are_ignored_on_login(accounts_login_client):
    client, store, _sessions = accounts_login_client
    invite = store.create_invite(code="no-inject", role="member", tenant_id="real-tenant")
    account = store.redeem_invite(code=invite.code, email_or_username="honest@example.com")

    # A client tries to smuggle elevated role + a different tenant in the body.
    resp = client.post(
        "/auth/token",
        json={
            "username": "honest@example.com",
            "api_credential": account.api_credential,
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
    client, store, _sessions = accounts_login_client
    invite = store.create_invite(code="route-code", role="member", tenant_id="t-route")

    # Body tries to inject role/tenant — the redeem model has no such fields, so they are ignored.
    ok = client.post(
        "/accounts/invite/redeem",
        json={
            "code": invite.code,
            "email_or_username": "router@example.com",
            "api_credential": TEST_API_CREDENTIAL,
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
        json={
            "code": invite.code,
            "email_or_username": "late@example.com",
            "api_credential": TEST_API_CREDENTIAL,
        },
    )
    assert bad.status_code == 400


# --- session enforcement + role gate --------------------------------------


def _login_token(client: TestClient, identity: str, api_credential: str) -> tuple[str, dict]:
    resp = client.post("/auth/token", json={"username": identity, "api_credential": api_credential})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return token, _decode(token)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _disable_account(store: AccountStore, account_id: str) -> None:
    backend = store._store
    rec = backend.get(store._tenant, ACCOUNT_KIND, account_id)
    assert rec is not None
    disabled_payload = dict(rec.payload)
    disabled_payload["status"] = "disabled"
    backend.put(rec.with_payload(disabled_payload), expected_version=rec.version)


def test_logout_revokes_current_session_and_blocks_next_request(accounts_login_client):
    client, store, sessions = accounts_login_client
    invite = store.create_invite(code="logout-code", role="member", tenant_id="tenant-logout")
    account = store.redeem_invite(code=invite.code, email_or_username="logout@example.com")
    token, claims = _login_token(client, "logout@example.com", account.api_credential)

    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 200
    logout = client.post("/auth/logout", headers=_auth(token))
    assert logout.status_code == 200
    assert logout.json() == {"revoked": True}

    session = sessions.get_session(claims["jti"])
    assert session is not None
    assert session.is_revoked
    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 401


def test_admin_revoke_blocks_target_session_next_request(accounts_login_client):
    client, store, sessions = accounts_login_client
    member_invite = store.create_invite(code="member-session", role="member", tenant_id="tenant-r")
    operator_invite = store.create_invite(
        code="operator-session", role="operator", tenant_id="tenant-r"
    )
    member = store.redeem_invite(code=member_invite.code, email_or_username="member-r@example.com")
    operator = store.redeem_invite(code=operator_invite.code, email_or_username="operator-r@example.com")
    member_token, member_claims = _login_token(client, "member-r@example.com", member.api_credential)
    operator_token, _operator_claims = _login_token(client, "operator-r@example.com", operator.api_credential)

    revoke = client.post(
        f"/auth/sessions/{member_claims['jti']}/revoke",
        headers=_auth(operator_token),
    )
    assert revoke.status_code == 200
    assert revoke.json() == {"revoked": True}

    session = sessions.get_session(member_claims["jti"])
    assert session is not None
    assert session.is_revoked
    assert client.get("/notation/grammar", headers=_auth(member_token)).status_code == 401


def test_admin_revoke_hides_cross_tenant_session(accounts_login_client):
    client, store, sessions = accounts_login_client
    operator_invite = store.create_invite(
        code="operator-cross", role="operator", tenant_id="tenant-a"
    )
    member_invite = store.create_invite(
        code="member-cross", role="member", tenant_id="tenant-b"
    )
    operator = store.redeem_invite(
        code=operator_invite.code, email_or_username="operator-cross@example.com"
    )
    member = store.redeem_invite(
        code=member_invite.code, email_or_username="member-cross@example.com"
    )
    operator_token, _ = _login_token(
        client, operator.email_or_username, operator.api_credential
    )
    member_token, member_claims = _login_token(
        client, member.email_or_username, member.api_credential
    )

    denied = client.post(
        f"/auth/sessions/{member_claims['jti']}/revoke",
        headers=_auth(operator_token),
    )
    assert denied.status_code == 404
    assert sessions.get_session(member_claims["jti"]).is_live()
    assert client.get("/notation/grammar", headers=_auth(member_token)).status_code == 200


def test_admin_cannot_revoke_same_tenant_owner(accounts_login_client):
    client, store, sessions = accounts_login_client
    admin_invite = store.create_invite(code="admin-rank", role="admin", tenant_id="tenant-rank")
    owner_invite = store.create_invite(code="owner-rank", role="owner", tenant_id="tenant-rank")
    admin = store.redeem_invite(
        code=admin_invite.code, email_or_username="admin-rank@example.com"
    )
    owner = store.redeem_invite(
        code=owner_invite.code, email_or_username="owner-rank@example.com"
    )
    admin_token, _ = _login_token(client, admin.email_or_username, admin.api_credential)
    _owner_token, owner_claims = _login_token(
        client, owner.email_or_username, owner.api_credential
    )

    denied = client.post(
        f"/auth/sessions/{owner_claims['jti']}/revoke",
        headers=_auth(admin_token),
    )
    assert denied.status_code == 403
    assert sessions.get_session(owner_claims["jti"]).is_live()


def test_auth_epoch_rejects_unrevoked_pre_rotation_session(accounts_login_client):
    client, store, sessions = accounts_login_client
    invite = store.create_invite(code="epoch-race", role="member", tenant_id="tenant-epoch")
    account = store.redeem_invite(
        code=invite.code, email_or_username="epoch@example.com"
    )
    token, claims = _login_token(client, account.email_or_username, account.api_credential)
    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 200
    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 200

    rotated = store.rotate_account_credential(
        account.account_id, new_credential=ROTATED_API_CREDENTIAL
    )
    assert rotated is not None and rotated.auth_epoch == account.auth_epoch + 1
    # Simulate a session missed by a concurrent revoke scan: it is still live in the session
    # store, but middleware must reject its stale account epoch on the very next request.
    assert sessions.get_session(claims["jti"]).is_live()
    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 401

    old_login = client.post(
        "/auth/token",
        json={"username": account.email_or_username, "api_credential": account.api_credential},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/auth/token",
        json={"username": account.email_or_username, "api_credential": ROTATED_API_CREDENTIAL},
    )
    assert new_login.status_code == 200


def test_self_rotation_never_echoes_secret_and_revokes_sessions(accounts_login_client):
    client, store, sessions = accounts_login_client
    invite = store.create_invite(code="self-rotate", role="member", tenant_id="tenant-self")
    account = store.redeem_invite(code=invite.code, email_or_username="self@example.com")
    token, claims = _login_token(client, account.email_or_username, account.api_credential)

    response = client.post(
        "/accounts/credential/rotate",
        json={"api_credential": ROTATED_API_CREDENTIAL},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert ROTATED_API_CREDENTIAL not in response.text
    assert response.json()["rotated"] is True
    assert sessions.get_session(claims["jti"]).is_revoked
    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 401


def test_disabled_account_is_rejected_on_next_request(accounts_login_client):
    client, store, _sessions = accounts_login_client
    invite = store.create_invite(code="disable-next", role="member", tenant_id="tenant-disable")
    account = store.redeem_invite(code=invite.code, email_or_username="next-disable@example.com")
    token, _claims = _login_token(client, "next-disable@example.com", account.api_credential)

    assert client.get("/notation/grammar", headers=_auth(token)).status_code == 200
    _disable_account(store, account.account_id)
    blocked = client.get("/notation/grammar", headers=_auth(token))
    assert blocked.status_code == 401
    assert "disabled" in blocked.json()["detail"].lower()


def test_account_token_is_confined_to_explicit_customer_route_allowlist(
    accounts_login_client,
):
    client, store, _sessions = accounts_login_client
    invite = store.create_invite(code="boundary", role="member", tenant_id="tenant-boundary")
    account = store.redeem_invite(
        code=invite.code, email_or_username="boundary@example.com"
    )
    token, _ = _login_token(client, account.email_or_username, account.api_credential)
    headers = _auth(token)

    assert client.get("/notation/grammar", headers=headers).status_code == 200
    for path in (
        "/config",
        "/api/crm/leads",
        "/api/validation/jobs",
        "/api/idea-atlas/maps",
        "/api/cas-harness/fleet/jobs",
        "/api/cas-harness/distributed/workers",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 403, (path, response.text)
        assert response.json()["detail"] == (
            "Route is unavailable to customer account credentials."
        )


def test_invite_create_requires_account_role_not_legacy_mint_secret(accounts_login_client):
    client, store, _sessions = accounts_login_client

    anonymous = client.post("/accounts/invite", json={"role": "member"})
    assert anonymous.status_code == 401

    legacy_token = create_token(sub="legacy", api_key="dashboard:legacy")
    legacy = client.post("/accounts/invite", json={"role": "member"}, headers=_auth(legacy_token))
    assert legacy.status_code == 401

    member_invite = store.create_invite(code="member-role", role="member", tenant_id="tenant-gate")
    operator_invite = store.create_invite(
        code="operator-role", role="operator", tenant_id="tenant-gate"
    )
    member = store.redeem_invite(code=member_invite.code, email_or_username="member-gate@example.com")
    operator = store.redeem_invite(
        code=operator_invite.code, email_or_username="operator-gate@example.com"
    )
    member_token, _member_claims = _login_token(client, "member-gate@example.com", member.api_credential)
    operator_token, _operator_claims = _login_token(client, "operator-gate@example.com", operator.api_credential)

    denied = client.post("/accounts/invite", json={"role": "member"}, headers=_auth(member_token))
    assert denied.status_code == 403

    cross_tenant = client.post(
        "/accounts/invite",
        json={"role": "member", "tenant_id": "tenant-created"},
        headers=_auth(operator_token),
    )
    assert cross_tenant.status_code == 403

    ok = client.post(
        "/accounts/invite",
        json={"role": "member"},
        headers=_auth(operator_token),
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["code"]
    assert body["role"] == "member"
    assert body["tenant_id"] == "tenant-gate"
    assert body["expires_at"]

    records = store._store.list(store._tenant, INVITE_KIND)
    created_payloads = [
        rec.payload
        for rec in records
        if rec.payload.get("code_hash") == invite_code_hash(body["code"])
    ]
    assert len(created_payloads) == 1
    assert "code" not in created_payloads[0]
