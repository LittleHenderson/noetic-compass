from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from api.services.stripe_billing import (
    StripeBillingConfigurationError,
    StripeBillingProvider,
    StripeBillingProviderError,
)


class _AsyncCreate:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[dict[str, object], dict[str, object] | None]] = []

    async def create_async(
        self,
        params: dict[str, object],
        options: dict[str, object] | None = None,
    ) -> object:
        self.calls.append((params, options))
        return self.response


class _AsyncRetrieve:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[str] = []

    async def retrieve_async(self, resource_id: str) -> object:
        self.calls.append(resource_id)
        return self.response


class _StripeClient:
    instances: list["_StripeClient"] = []

    def __init__(self, secret_key: str, *, max_network_retries: int) -> None:
        self.secret_key = secret_key
        self.max_network_retries = max_network_retries
        self.checkout = _AsyncCreate(
            SimpleNamespace(
                id="cs_server",
                url="https://checkout.stripe.com/c/pay/cs_server",
            )
        )
        self.portal = _AsyncCreate(
            SimpleNamespace(url="https://billing.stripe.com/p/session/server")
        )
        self.subscriptions = _AsyncRetrieve(
            SimpleNamespace(
                to_dict_recursive=lambda: {
                    "id": "sub_current",
                    "customer": "cus_bound",
                    "status": "active",
                }
            )
        )
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=self.checkout),
            billing_portal=SimpleNamespace(sessions=self.portal),
            subscriptions=self.subscriptions,
        )
        self.construct_calls: list[tuple[bytes, str, str]] = []
        self.event = {"id": "evt_verified", "type": "test"}
        self.instances.append(self)

    def construct_event(self, payload: bytes, signature: str, secret: str):
        self.construct_calls.append((payload, signature, secret))
        return SimpleNamespace(to_dict_recursive=lambda: self.event)


@pytest.fixture
def provider(monkeypatch) -> StripeBillingProvider:
    _StripeClient.instances.clear()
    stripe = ModuleType("stripe")
    stripe.StripeClient = _StripeClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "stripe", stripe)
    return StripeBillingProvider(
        secret_key="sk_test_private",
        webhook_secret="whsec_private",
        price_by_plan={
            "professional_live": "price_pro",
            "enterprise_live": "price_ent",
        },
        success_url="https://app.example.com/billing/success",
        cancel_url="https://app.example.com/billing/cancel",
        portal_return_url="https://app.example.com/billing",
    )


@pytest.mark.asyncio
async def test_checkout_parameters_are_server_derived_and_idempotent(provider) -> None:
    result = await provider.create_checkout_session(
        tenant_id="tenant-a",
        account_id="acct-a",
        email="owner@example.com",
        plan_id="professional_live",
        external_customer_id=None,
        idempotency_key="cas-checkout:tenant-a:professional_live:req_1",
    )
    client = _StripeClient.instances[0]
    params, options = client.checkout.calls[0]
    assert result.session_id == "cs_server"
    assert client.secret_key == "sk_test_private"
    assert client.max_network_retries == 2
    assert params["line_items"] == [{"price": "price_pro", "quantity": 1}]
    assert params["client_reference_id"] == "tenant-a"
    assert params["customer_email"] == "owner@example.com"
    assert params["metadata"] == {
        "cas_tenant_id": "tenant-a",
        "cas_account_id": "acct-a",
        "cas_plan_id": "professional_live",
    }
    assert params["subscription_data"] == {"metadata": params["metadata"]}
    assert options == {
        "idempotency_key": "cas-checkout:tenant-a:professional_live:req_1"
    }


@pytest.mark.asyncio
async def test_existing_customer_and_portal_use_bound_customer(provider) -> None:
    await provider.create_checkout_session(
        tenant_id="tenant-a",
        account_id="acct-a",
        email="ignored@example.com",
        plan_id="enterprise_live",
        external_customer_id="cus_bound",
        idempotency_key="req-enterprise",
    )
    portal = await provider.create_portal_session(external_customer_id="cus_bound")
    client = _StripeClient.instances[0]
    checkout_params, _ = client.checkout.calls[0]
    portal_params, portal_options = client.portal.calls[0]
    assert checkout_params["customer"] == "cus_bound"
    assert "customer_email" not in checkout_params
    assert portal.url.startswith("https://billing.stripe.com/")
    assert portal_params == {
        "customer": "cus_bound",
        "return_url": "https://app.example.com/billing",
    }
    assert portal_options is None


def test_raw_webhook_signature_is_verified_by_sdk_client(provider) -> None:
    payload = b'{"id":"evt_verified"}'
    event = provider.construct_webhook_event(payload=payload, signature="t=1,v1=abc")
    client = _StripeClient.instances[0]
    assert event == {"id": "evt_verified", "type": "test"}
    assert client.construct_calls == [(payload, "t=1,v1=abc", "whsec_private")]


@pytest.mark.asyncio
async def test_subscription_webhook_refresh_reads_latest_provider_state(provider) -> None:
    latest = await provider.retrieve_subscription(
        external_subscription_id="sub_current"
    )
    client = _StripeClient.instances[0]
    assert latest.payload["status"] == "active"
    assert client.subscriptions.calls == ["sub_current"]


def test_incomplete_configuration_fails_loud_without_importing_sdk() -> None:
    with pytest.raises(StripeBillingConfigurationError) as exc_info:
        StripeBillingProvider(
            secret_key="secret-not-printed",
            webhook_secret="",
            price_by_plan={},
            success_url="",
            cancel_url="",
            portal_return_url="",
        )
    message = str(exc_info.value)
    assert "NC_STRIPE_WEBHOOK_SECRET" in message
    assert "secret-not-printed" not in message


@pytest.mark.asyncio
async def test_unknown_plan_and_invalid_sdk_response_fail_closed(provider) -> None:
    with pytest.raises(StripeBillingProviderError, match="no Stripe price"):
        await provider.create_checkout_session(
            tenant_id="tenant-a",
            account_id="acct-a",
            email="owner@example.com",
            plan_id="attacker_plan",
            external_customer_id=None,
            idempotency_key="req",
        )
    _StripeClient.instances[0].checkout.response = SimpleNamespace(
        id="cs_bad", url="javascript:alert(1)"
    )
    with pytest.raises(StripeBillingProviderError, match="invalid Checkout"):
        await provider.create_checkout_session(
            tenant_id="tenant-a",
            account_id="acct-a",
            email="owner@example.com",
            plan_id="professional_live",
            external_customer_id=None,
            idempotency_key="req",
        )
