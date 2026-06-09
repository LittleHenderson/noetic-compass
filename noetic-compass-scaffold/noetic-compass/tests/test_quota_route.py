from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.config import settings
from api.main import app
from api.middleware.auth import create_token
from api.services.accounts.store import AccountStore
from api.services.cas_harness_audit_sessions import reset_audit_sessions_for_tests
from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.quotas import current_monthly_period_key, get_usage
from api.services.sessions.store import SessionStore


def _valid_audit_payload(*, prompt: str = "Assess this customer model output.") -> dict:
    return {
        "model_id": "openai:gpt-4.1-mini",
        "audit_mode": "BALANCED",
        "prompt": prompt,
        "selected_modules": ["cognitive_bias", "provenance_trace"],
        "license_key": "placeholder-license",
    }


def _valid_distributed_payload(*, model_id: str = "customer/open-20b") -> dict:
    return {
        "model_id": model_id,
        "parameter_count_b": 20,
        "num_layers": 40,
        "accept_audit_data_capture": True,
    }


@pytest.fixture(autouse=True)
def _reset_audit_state(monkeypatch):
    reset_audit_sessions_for_tests()
    reset_distributed_audits_for_tests()
    monkeypatch.setattr(settings, "accounts_enabled", False)
    monkeypatch.setattr(settings, "quotas_enabled", False, raising=False)
    yield
    reset_audit_sessions_for_tests()
    reset_distributed_audits_for_tests()


@pytest.fixture
def quota_identity(monkeypatch):
    store = InMemoryStateStore()
    account_store = AccountStore(store)
    invite = account_store.create_invite(
        code="quota-route-test-invite",
        tenant_id="tenant-quota-route",
    )
    account = account_store.redeem_invite(
        code=invite.code,
        email_or_username="quota-user@example.com",
    )
    session_store = SessionStore(store)
    session = session_store.create_session(
        account_id=account.account_id,
        tenant_id=account.tenant_id,
        role=account.role,
        expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
    )
    token = create_token(
        sub=account.email_or_username,
        api_key=f"account:{account.account_id}",
        account_id=account.account_id,
        tenant_id=account.tenant_id,
        role=account.role,
        jti=session.session_id,
    )

    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "quotas_enabled", True, raising=False)
    monkeypatch.setattr(app.state, "account_store", account_store, raising=False)
    monkeypatch.setattr(app.state, "session_store", session_store, raising=False)

    return {
        "account": account,
        "headers": {"Authorization": f"Bearer {token}"},
        "store": store,
        "tenant_id": account.tenant_id,
    }


def _usage(quota_identity) -> int:
    return get_usage(
        quota_identity["store"],
        tenant_id=quota_identity["tenant_id"],
        period_key=current_monthly_period_key(),
    )


def test_quotas_disabled_preserves_dark_audit_creation(client):
    resp = client.post("/api/cas-harness/audit/session", json=_valid_audit_payload())

    assert resp.status_code == 200
    assert resp.json()["audit_id"]


def test_metered_audit_session_requires_account_mode_token(client, quota_identity):
    resp = client.post("/api/cas-harness/audit/session", json=_valid_audit_payload())

    assert resp.status_code == 401
    assert _usage(quota_identity) == 0


def test_audit_session_creation_consumes_tenant_quota(client, quota_identity):
    resp = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_audit_payload(),
        headers=quota_identity["headers"],
    )

    assert resp.status_code == 200
    assert _usage(quota_identity) == 1


def test_audit_session_creation_returns_429_when_monthly_quota_is_exhausted(
    client,
    quota_identity,
    monkeypatch,
):
    from api.routes import cas_harness_audit

    monkeypatch.setattr(cas_harness_audit, "get_quota_limit", lambda plan_id=None: 1)

    first = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_audit_payload(prompt="First metered audit."),
        headers=quota_identity["headers"],
    )
    second = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_audit_payload(prompt="Second metered audit."),
        headers=quota_identity["headers"],
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == {
        "error": "quota_exceeded",
        "tenant_id": quota_identity["tenant_id"],
        "period": current_monthly_period_key(),
        "limit": 1,
        "count": 1,
    }
    assert _usage(quota_identity) == 1


def test_distributed_audit_creation_consumes_tenant_quota(client, quota_identity):
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_valid_distributed_payload(),
        headers=quota_identity["headers"],
    )

    assert resp.status_code == 200
    assert _usage(quota_identity) == 1


def test_distributed_audit_creation_returns_429_when_monthly_quota_is_exhausted(
    client,
    quota_identity,
    monkeypatch,
):
    from api.routes import cas_harness_audit

    monkeypatch.setattr(cas_harness_audit, "get_quota_limit", lambda plan_id=None: 1)

    first = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_valid_distributed_payload(model_id="customer/open-20b-first"),
        headers=quota_identity["headers"],
    )
    second = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_valid_distributed_payload(model_id="customer/open-20b-second"),
        headers=quota_identity["headers"],
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["error"] == "quota_exceeded"
    assert second.json()["detail"]["tenant_id"] == quota_identity["tenant_id"]
    assert second.json()["detail"]["limit"] == 1
    assert second.json()["detail"]["count"] == 1
    assert _usage(quota_identity) == 1
