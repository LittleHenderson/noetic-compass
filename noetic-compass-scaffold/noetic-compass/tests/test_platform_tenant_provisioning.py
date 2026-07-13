"""Platform-only tenant provisioning and customer-tenant isolation regressions."""

from __future__ import annotations

import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.services.accounts.models import ACCOUNT_KIND, Account
from api.services.accounts.store import AccountStore
from api.services.accounts.tenant_provisioning import (
    TENANT_PROVISIONING_KIND,
    TENANT_PROVISIONING_RECEIPT_KIND,
    TenantProvisioningError,
    provision_tenant_owner,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore


PEPPER = "test-account-credential-pepper-0123456789"
PLATFORM_SECRET = "test-platform-provisioning-secret-0123456789"


def _credential() -> str:
    return f"casak_{secrets.token_urlsafe(32)}"


def _store(backend, *, failure_injector=None) -> AccountStore:
    return AccountStore(
        backend,
        credential_pepper=PEPPER,
        failure_injector=failure_injector,
    )


def _tenant_accounts(store: AccountStore, tenant_id: str) -> list[Account]:
    return [
        Account.from_payload(record.payload)
        for record in store._store.list(store._tenant, ACCOUNT_KIND)
        if str(record.payload.get("tenant_id") or "") == tenant_id
    ]


def test_platform_service_provisions_second_tenant_with_hash_only_receipt(
    tmp_path,
) -> None:
    backend = SqliteStateStore(tmp_path / "second-tenant.db")
    store = _store(backend)
    primary_key = _credential()
    secondary_key = _credential()
    primary = store.bootstrap_owner(
        email_or_username="owner@primary.example",
        tenant_id="primary",
        api_credential=primary_key,
    )

    result = provision_tenant_owner(
        store,
        tenant_id="tenant-two",
        email_or_username="owner@two.example",
        api_credential=secondary_key,
        request_id="request-platform-001",
    )

    assert primary.tenant_id == "primary"
    assert result.account.role == "owner"
    assert result.account.tenant_id == "tenant-two"
    assert result.account.account_id != primary.account_id
    assert store.authenticate_account("owner@two.example", secondary_key) == result.account
    assert store.authenticate_account("owner@two.example", primary_key) is None
    assert len(_tenant_accounts(store, "primary")) == 1
    assert len(_tenant_accounts(store, "tenant-two")) == 1

    markers = backend.list(store._tenant, TENANT_PROVISIONING_KIND)
    receipts = backend.list(store._tenant, TENANT_PROVISIONING_RECEIPT_KIND)
    assert len(markers) == len(receipts) == 1
    assert markers[0].payload["status"] == "completed"
    assert receipts[0].payload["tenant_id"] == "tenant-two"
    assert receipts[0].payload["owner_account_id"] == result.account.account_id
    assert receipts[0].payload["platform_request_id"] == "request-platform-001"
    persisted = repr(
        [
            markers[0].payload,
            receipts[0].payload,
            backend.get(store._tenant, ACCOUNT_KIND, result.account.account_id).payload,
        ]
    )
    assert secondary_key not in persisted


@pytest.mark.parametrize(
    "boundary",
    [
        "after_tenant_provisioning_reservation_write",
        "after_tenant_provisioning_email_write",
        "after_tenant_provisioning_account_write",
        "after_tenant_provisioning_completion_write",
        "after_tenant_provisioning_receipt_write",
    ],
)
def test_platform_provisioning_recovers_after_every_write_boundary(
    tmp_path, boundary: str
) -> None:
    path = tmp_path / f"{boundary}.db"
    backend = SqliteStateStore(path)
    crashed = False

    def crash_once(name: str) -> None:
        nonlocal crashed
        if name == boundary and not crashed:
            crashed = True
            raise RuntimeError("injected platform provisioning crash")

    key = _credential()
    with pytest.raises(RuntimeError, match="injected platform"):
        provision_tenant_owner(
            _store(backend, failure_injector=crash_once),
            tenant_id="tenant-recovery",
            email_or_username="recover@example.com",
            api_credential=key,
            request_id="request-before-crash",
        )
    backend.close()

    reopened_backend = SqliteStateStore(path)
    reopened = _store(reopened_backend)
    recovered = provision_tenant_owner(
        reopened,
        tenant_id="tenant-recovery",
        email_or_username="recover@example.com",
        api_credential=key,
        request_id="request-after-crash",
    )
    repeated = provision_tenant_owner(
        reopened,
        tenant_id="tenant-recovery",
        email_or_username="recover@example.com",
        api_credential=key,
    )

    assert recovered.account.account_id == repeated.account.account_id
    assert recovered.provisioning_id == repeated.provisioning_id
    assert recovered.receipt_id == repeated.receipt_id
    assert len(_tenant_accounts(reopened, "tenant-recovery")) == 1
    assert len(
        reopened_backend.list(
            reopened._tenant, TENANT_PROVISIONING_RECEIPT_KIND
        )
    ) == 1


def test_retry_requires_same_client_credential_and_owner_identity(tmp_path) -> None:
    store = _store(SqliteStateStore(tmp_path / "retry-identity.db"))
    key = _credential()
    first = provision_tenant_owner(
        store,
        tenant_id="tenant-fixed",
        email_or_username="fixed@example.com",
        api_credential=key,
    )

    with pytest.raises(
        TenantProvisioningError, match="provisioning_credential_mismatch"
    ):
        provision_tenant_owner(
            store,
            tenant_id="tenant-fixed",
            email_or_username="fixed@example.com",
            api_credential=_credential(),
        )
    with pytest.raises(TenantProvisioningError, match="tenant_already_reserved"):
        provision_tenant_owner(
            store,
            tenant_id="tenant-fixed",
            email_or_username="attacker@example.com",
            api_credential=key,
        )

    assert _tenant_accounts(store, "tenant-fixed") == [first.account]


def test_concurrent_distinct_tenants_remain_isolated(tmp_path) -> None:
    store = _store(SqliteStateStore(tmp_path / "concurrent-tenants.db"))
    key_a = _credential()
    key_b = _credential()

    def create(tenant_id: str, email: str, key: str):
        return provision_tenant_owner(
            store,
            tenant_id=tenant_id,
            email_or_username=email,
            api_credential=key,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(create, "tenant-alpha", "owner@alpha.example", key_a)
        future_b = pool.submit(create, "tenant-beta", "owner@beta.example", key_b)
        result_a = future_a.result()
        result_b = future_b.result()

    assert result_a.account.tenant_id == "tenant-alpha"
    assert result_b.account.tenant_id == "tenant-beta"
    assert result_a.account.account_id != result_b.account.account_id
    assert result_a.receipt_id != result_b.receipt_id
    assert store.authenticate_account("owner@alpha.example", key_a) == result_a.account
    assert store.authenticate_account("owner@alpha.example", key_b) is None
    assert store.authenticate_account("owner@beta.example", key_b) == result_b.account
    assert store.authenticate_account("owner@beta.example", key_a) is None
    assert len(_tenant_accounts(store, "tenant-alpha")) == 1
    assert len(_tenant_accounts(store, "tenant-beta")) == 1


def test_account_config_rejects_short_platform_provisioning_secret(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "jwt_secret", "j" * 32)
    monkeypatch.setattr(settings, "account_credential_pepper", "p" * 32)
    monkeypatch.setattr(settings, "platform_tenant_provisioning_secret", "short")
    monkeypatch.setattr(settings, "accounts_allow_single_host_sqlite", True)
    monkeypatch.setattr(settings, "state_ledger_path", str(tmp_path / "state.db"))
    with pytest.raises(
        RuntimeError, match="NC_PLATFORM_TENANT_PROVISIONING_SECRET"
    ):
        settings.validate_account_storage()


@pytest.fixture
def platform_client(tmp_path, monkeypatch):
    from api.main import app

    backend = SqliteStateStore(tmp_path / "platform-route.db")
    account_store = _store(backend)
    session_store = SessionStore(backend)
    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        monkeypatch.setattr(
            settings, "platform_tenant_provisioning_secret", PLATFORM_SECRET
        )
        monkeypatch.setattr(settings, "accounts_bootstrap_tenant_id", "primary")
        app.state.account_store = account_store
        app.state.session_store = session_store
        try:
            yield client, account_store
        finally:
            app.state.account_store = None
            app.state.session_store = None


def _platform_body(
    tenant_id: str, email: str, api_credential: str
) -> dict[str, str]:
    return {
        "tenant_id": tenant_id,
        "email_or_username": email,
        "api_credential": api_credential,
    }


def _login(client: TestClient, email: str, api_credential: str) -> str:
    response = client.post(
        "/auth/token",
        json={"username": email, "api_credential": api_credential},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["token"])


def test_platform_route_is_exact_public_and_requires_platform_secret(
    platform_client,
) -> None:
    client, store = platform_client
    owner_key = _credential()
    provision_tenant_owner(
        store,
        tenant_id="tenant-customer",
        email_or_username="owner@customer.example",
        api_credential=owner_key,
    )
    customer_token = _login(client, "owner@customer.example", owner_key)
    target_body = _platform_body(
        "tenant-second", "owner@second.example", _credential()
    )

    # A customer owner JWT is not platform authority.
    no_platform_secret = client.post(
        "/platform/tenants",
        json=target_body,
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert no_platform_secret.status_code == 401
    assert no_platform_secret.json() == {
        "detail": "Platform provisioning credentials are invalid."
    }

    wrong_platform_secret = client.post(
        "/platform/tenants",
        json=target_body,
        headers={"X-Platform-Provisioning-Secret": "x" * 40},
    )
    assert wrong_platform_secret.status_code == 401
    assert wrong_platform_secret.json() == no_platform_secret.json()

    # Only the exact endpoint is public; a neighboring path still hits JWT auth first.
    neighboring = client.post(
        "/platform/tenants/tenant-second",
        json=target_body,
        headers={"X-Platform-Provisioning-Secret": PLATFORM_SECRET},
    )
    assert neighboring.status_code == 401
    assert neighboring.json()["detail"] == "Missing or invalid Authorization header"


def test_platform_non_ascii_configured_secret_fails_closed_without_500(
    platform_client, monkeypatch
) -> None:
    client, _store = platform_client
    monkeypatch.setattr(settings, "platform_tenant_provisioning_secret", "🔐" * 32)

    response = client.post(
        "/platform/tenants",
        json=_platform_body(
            "tenant-unicode", "owner@unicode.example", _credential()
        ),
        headers={"X-Platform-Provisioning-Secret": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Platform provisioning credentials are invalid."
    }


def test_platform_route_provisions_and_retries_second_tenant_without_secret_echo(
    platform_client,
) -> None:
    client, store = platform_client
    second_key = _credential()
    body = _platform_body("tenant-second", "owner@second.example", second_key)
    headers = {"X-Platform-Provisioning-Secret": PLATFORM_SECRET}

    first = client.post("/platform/tenants", json=body, headers=headers)
    repeated = client.post("/platform/tenants", json=body, headers=headers)

    assert first.status_code == repeated.status_code == 200
    assert first.headers["Cache-Control"] == "no-store"
    assert first.json()["provisioning_id"] == repeated.json()["provisioning_id"]
    assert first.json()["receipt_id"] == repeated.json()["receipt_id"]
    assert first.json()["owner"]["tenant_id"] == "tenant-second"
    assert first.json()["owner"]["role"] == "owner"
    assert "api_credential" not in first.json()["owner"]
    assert second_key not in first.text
    assert store.authenticate_account("owner@second.example", second_key) is not None
    assert len(_tenant_accounts(store, "tenant-second")) == 1


def test_platform_route_refuses_bootstrap_tenant_and_customer_cross_tenant_invite(
    platform_client,
) -> None:
    client, store = platform_client
    platform_headers = {"X-Platform-Provisioning-Secret": PLATFORM_SECRET}
    bootstrap_overlap = client.post(
        "/platform/tenants",
        json=_platform_body("primary", "other@primary.example", _credential()),
        headers=platform_headers,
    )
    assert bootstrap_overlap.status_code == 409
    assert bootstrap_overlap.json() == {
        "detail": "Tenant could not be provisioned."
    }
    assert _tenant_accounts(store, "primary") == []

    owner_key = _credential()
    provision_tenant_owner(
        store,
        tenant_id="tenant-owner",
        email_or_username="owner@owner.example",
        api_credential=owner_key,
    )
    token = _login(client, "owner@owner.example", owner_key)
    auth = {"Authorization": f"Bearer {token}"}

    same_tenant = client.post(
        "/accounts/invite",
        json={"role": "member", "tenant_id": "tenant-owner"},
        headers=auth,
    )
    assert same_tenant.status_code == 200, same_tenant.text

    cross_tenant = client.post(
        "/accounts/invite",
        json={"role": "member", "tenant_id": "tenant-victim"},
        headers=auth,
    )
    assert cross_tenant.status_code == 403
    assert cross_tenant.json()["detail"] == "Cross-tenant invites are not permitted."
