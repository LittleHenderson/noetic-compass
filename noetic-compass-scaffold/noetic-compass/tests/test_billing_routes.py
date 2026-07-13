from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from api.config import settings
from api.middleware.auth import is_public_path
from api.middleware.rate_limit import RateLimitMiddleware
from api.routes import billing
from api.services.billing_entitlements import (
    BILLING_PLATFORM_TENANT,
    WEBHOOK_EVENT_KIND,
    BillingEntitlementStore,
)
from api.services.production.state_substrate import InMemoryStateStore
from api.services.stripe_billing import (
    CheckoutSessionResult,
    PortalSessionResult,
    SubscriptionSnapshot,
)


class _AccountStore:
    def __init__(self) -> None:
        self.accounts = {
            "acct-a": SimpleNamespace(
                account_id="acct-a",
                tenant_id="tenant-a",
                email_or_username="owner@example.com",
                is_active=True,
            ),
            "acct-b": SimpleNamespace(
                account_id="acct-b",
                tenant_id="tenant-b",
                email_or_username="other@example.com",
                is_active=True,
            ),
        }

    def get_account_by_id(self, account_id: str):
        return self.accounts.get(account_id)

    def tenant_has_account(self, tenant_id: str, *, active_only: bool = True) -> bool:
        del active_only
        return any(account.tenant_id == tenant_id for account in self.accounts.values())


class _Provider:
    def __init__(self) -> None:
        self.checkout_calls: list[dict[str, object]] = []
        self.portal_calls: list[dict[str, object]] = []
        self.webhook_event: dict[str, object] | None = None
        self.latest_subscription: dict[str, object] | None = None
        self.observed_payload: bytes | None = None
        self.retrieved_subscription_ids: list[str] = []
        self.retrieve_error = False

    async def create_checkout_session(self, **kwargs: object) -> CheckoutSessionResult:
        self.checkout_calls.append(kwargs)
        return CheckoutSessionResult(
            session_id="cs_test_server_derived",
            url="https://checkout.stripe.com/c/pay/cs_test_server_derived",
        )

    async def create_portal_session(self, **kwargs: object) -> PortalSessionResult:
        self.portal_calls.append(kwargs)
        return PortalSessionResult(url="https://billing.stripe.com/p/session/test")

    def construct_webhook_event(self, *, payload: bytes, signature: str):
        assert signature == "signed-test-event"
        self.observed_payload = payload
        assert self.webhook_event is not None
        return self.webhook_event

    async def retrieve_subscription(self, *, external_subscription_id: str):
        self.retrieved_subscription_ids.append(external_subscription_id)
        if self.retrieve_error:
            from api.services.stripe_billing import StripeBillingProviderError

            raise StripeBillingProviderError("simulated Stripe refresh outage")
        assert self.webhook_event is not None
        return SubscriptionSnapshot(
            payload=(
                self.latest_subscription
                or self.webhook_event["data"]["object"]  # type: ignore[index]
            ),
            provider_request_id="req_refresh_test",
        )


@pytest.fixture
def billing_client(monkeypatch):
    monkeypatch.setattr(settings, "billing_entitlements_enabled", True)
    monkeypatch.setattr(settings, "billing_provider", "stripe")
    monkeypatch.setattr(settings, "billing_admin_secret", "s" * 32)
    monkeypatch.setattr(settings, "stripe_professional_price_id", "price_pro")
    monkeypatch.setattr(settings, "stripe_enterprise_price_id", "price_ent")

    app = FastAPI()
    provider = _Provider()
    store = BillingEntitlementStore(InMemoryStateStore())
    app.state.billing_entitlement_store = store
    app.state.billing_provider = provider
    app.state.account_store = _AccountStore()

    @app.middleware("http")
    async def server_identity(request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant", "tenant-a")
        request.state.account_id = request.headers.get("X-Test-Account", "acct-a")
        request.state.role = request.headers.get("X-Test-Role", "owner")
        return await call_next(request)

    app.include_router(billing.router)
    with TestClient(app) as client:
        yield client, store, provider


def test_public_exceptions_are_exact_and_adjacent_routes_stay_protected() -> None:
    assert is_public_path("/billing/webhook/stripe") is True
    assert is_public_path("/platform/billing/manual-comped-subscription") is True
    assert is_public_path("/billing/checkout") is False
    assert is_public_path("/billing/webhook/stripe/attacker-suffix") is False
    assert is_public_path("/platform/billing/manual-comped-subscription/extra") is False


def test_public_manual_grant_is_rate_limited() -> None:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/platform/billing/manual-comped-subscription")
    async def probe():
        return {"ok": True}

    with TestClient(app) as client:
        responses = [
            client.post("/platform/billing/manual-comped-subscription")
            for _ in range(61)
        ]
    assert responses[-1].status_code == 429


def test_catalog_omits_platform_comped_plan_and_disables_cache(billing_client) -> None:
    client, _, _ = billing_client
    response = client.get("/billing/plans")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    plan_ids = {plan["plan_id"] for plan in response.json()["plans"]}
    assert plan_ids == {
        "free_reference",
        "professional_live",
        "enterprise_live",
    }


def test_entitlement_is_tenant_derived_and_not_request_selected(billing_client) -> None:
    client, store, _ = billing_client
    store.grant_manual_comped(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        expires_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
    )
    tenant_a = client.get("/billing/entitlement")
    tenant_b = client.get(
        "/billing/entitlement", headers={"X-Test-Tenant": "tenant-b", "X-Test-Account": "acct-b"}
    )
    assert tenant_a.json()["plan"]["plan_id"] == "beta_comped"
    assert tenant_b.json()["plan"]["plan_id"] == "free_reference"


def test_checkout_requires_role_and_uses_server_identity(billing_client) -> None:
    client, _, provider = billing_client
    body = {"plan_id": "professional_live", "request_id": "request_0123456789"}
    forbidden = client.post(
        "/billing/checkout", json=body, headers={"X-Test-Role": "viewer"}
    )
    assert forbidden.status_code == 403
    response = client.post("/billing/checkout", json=body)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["checkout_session_id"] == "cs_test_server_derived"
    assert provider.checkout_calls == [
        {
            "tenant_id": "tenant-a",
            "account_id": "acct-a",
            "email": "owner@example.com",
            "plan_id": "professional_live",
            "external_customer_id": None,
            "idempotency_key": (
                "cas-checkout:tenant-a:professional_live:request_0123456789"
            ),
        }
    ]
    duplicate = client.post("/billing/checkout", json=body)
    assert duplicate.status_code == 200
    assert duplicate.json() == response.json()
    assert len(provider.checkout_calls) == 1
    conflict = client.post(
        "/billing/checkout",
        json={"plan_id": "professional_live", "request_id": "different_0123456789"},
    )
    assert conflict.status_code == 409


def test_portal_requires_server_linked_customer(billing_client) -> None:
    client, store, provider = billing_client
    assert client.post("/billing/portal").status_code == 409
    store.apply_stripe_subscription(
        tenant_id="tenant-a",
        plan_id="professional_live",
        status="active",
        external_customer_id="cus_a",
        external_subscription_id="sub_a",
        event_id="evt_portal",
        event_created=1,
        current_period_start=datetime.now(UTC).isoformat(),
        current_period_end=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        cancel_at_period_end=False,
    )
    response = client.post("/billing/portal")
    assert response.status_code == 200
    assert provider.portal_calls == [{"external_customer_id": "cus_a"}]
    blocked_checkout = client.post(
        "/billing/checkout",
        json={"plan_id": "professional_live", "request_id": "resubscribe_012345"},
    )
    assert blocked_checkout.status_code == 409
    assert "use the billing portal" in blocked_checkout.text


def test_webhook_requires_signature_and_applies_only_verified_event(billing_client) -> None:
    client, store, provider = billing_client
    assert client.post("/billing/webhook/stripe", content=b"{}").status_code == 400
    assert (
        client.post(
            "/billing/webhook/stripe",
            content=b"{}",
            headers={
                "Stripe-Signature": "signed-test-event",
                "Content-Length": "2000001",
            },
        ).status_code
        == 413
    )
    provider.webhook_event = {
        "id": "evt_route",
        "type": "customer.subscription.updated",
        "created": 1,
        "data": {
            "object": {
                "id": "sub_route",
                "customer": "cus_route",
                "status": "active",
                "metadata": {"cas_tenant_id": "tenant-a"},
                "items": {
                    "data": [
                        {
                            "price": {"id": "price_pro"},
                            "current_period_start": 1_700_000_000,
                            "current_period_end": 4_000_000_000,
                        }
                    ]
                },
            }
        },
    }
    # Snapshot says active, but Stripe's current resource says canceled. The
    # latter must win because webhook delivery order is not guaranteed.
    provider.latest_subscription = {
        **provider.webhook_event["data"]["object"],  # type: ignore[index]
        "status": "canceled",
    }
    raw = b'{"the":"raw body must survive"}'
    response = client.post(
        "/billing/webhook/stripe",
        content=raw,
        headers={"Stripe-Signature": "signed-test-event"},
    )
    assert response.status_code == 200
    assert provider.observed_payload == raw
    assert provider.retrieved_subscription_ids == ["sub_route"]
    decision = store.resolve_entitlement("tenant-a")
    assert decision.subscription_status == "canceled"
    assert decision.plan.plan_id == "free_reference"
    receipt = store._store.get(  # noqa: SLF001 - receipt contract assertion
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_route"
    )
    assert receipt is not None
    assert receipt.payload["provider_refreshes"][0]["provider_request_id"] == (
        "req_refresh_test"
    )
    duplicate = client.post(
        "/billing/webhook/stripe",
        content=raw,
        headers={"Stripe-Signature": "signed-test-event"},
    )
    assert duplicate.json()["duplicate"] is True
    assert provider.retrieved_subscription_ids == ["sub_route"]


def test_webhook_receipt_precedes_provider_refresh_failure(billing_client) -> None:
    client, store, provider = billing_client
    provider.webhook_event = {
        "id": "evt_refresh_crash",
        "type": "customer.subscription.updated",
        "created": 1,
        "data": {"object": {"id": "sub_refresh_crash"}},
    }
    provider.retrieve_error = True
    raw = b'{"signed":"snapshot"}'
    response = client.post(
        "/billing/webhook/stripe",
        content=raw,
        headers={"Stripe-Signature": "signed-test-event"},
    )
    assert response.status_code == 502
    receipt = store._store.get(  # noqa: SLF001
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_refresh_crash"
    )
    assert receipt is not None
    assert receipt.payload["state"] == "unresolved"
    assert receipt.payload["payload_sha256"]
    assert store.get_subscription("tenant-a") is None


def test_manual_comped_route_is_secret_gated_expiring_and_tenant_checked(
    billing_client,
) -> None:
    client, _, _ = billing_client
    body = {
        "tenant_id": "tenant-a",
        "billing_account_id": "acct-a",
        "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
    }
    assert (
        client.post("/platform/billing/manual-comped-subscription", json=body).status_code
        == 401
    )
    mismatch = dict(body, billing_account_id="acct-b")
    assert (
        client.post(
            "/platform/billing/manual-comped-subscription",
            json=mismatch,
            headers={"X-Billing-Admin-Secret": "s" * 32},
        ).status_code
        == 404
    )
    response = client.post(
        "/platform/billing/manual-comped-subscription",
        json=body,
        headers={"X-Billing-Admin-Secret": "s" * 32},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["source"] == "manual_comped"
    assert response.json()["plan_id"] == "beta_comped"
