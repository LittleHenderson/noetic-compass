from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from api.services.stripe_billing import (
    STRIPE_API_VERSION,
    STRIPE_SDK_VERSION,
    StripeBillingConfigurationError,
    StripeBillingProvider,
    StripeBillingProviderError,
    build_billing_provider,
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


class _StripeObject:
    """Test double that exposes the same public conversion API as stripe v15."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.to_dict_calls: list[tuple[bool, bool]] = []
        self.last_response = None

    def to_dict(
        self, recursive: bool = True, for_json: bool = False
    ) -> dict[str, object]:
        self.to_dict_calls.append((recursive, for_json))
        return dict(self.payload)


class _StripeClient:
    instances: list["_StripeClient"] = []

    def __init__(
        self,
        secret_key: str,
        *,
        stripe_version: str,
        max_network_retries: int,
    ) -> None:
        self.secret_key = secret_key
        self.stripe_version = stripe_version
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
        self.subscription = _StripeObject(
            {
                "id": "sub_current",
                "customer": "cus_bound",
                "status": "active",
            }
        )
        self.subscriptions = _AsyncRetrieve(self.subscription)
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=self.checkout),
            billing_portal=SimpleNamespace(sessions=self.portal),
            subscriptions=self.subscriptions,
        )
        self.construct_calls: list[tuple[bytes, str, str]] = []
        self.event = {
            "id": "evt_verified",
            "type": "test",
            "api_version": STRIPE_API_VERSION,
            "livemode": False,
        }
        self.last_event_object: _StripeObject | None = None
        self.instances.append(self)

    def construct_event(self, payload: bytes, signature: str, secret: str):
        self.construct_calls.append((payload, signature, secret))
        self.last_event_object = _StripeObject(self.event)
        return self.last_event_object


def _install_fake_stripe(monkeypatch) -> None:
    _StripeClient.instances.clear()
    stripe = ModuleType("stripe")
    stripe.VERSION = STRIPE_SDK_VERSION  # type: ignore[attr-defined]
    stripe.StripeClient = _StripeClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "stripe", stripe)


@pytest.fixture
def provider(monkeypatch) -> StripeBillingProvider:
    _install_fake_stripe(monkeypatch)
    return StripeBillingProvider(
        secret_key="sk_test_private",
        webhook_secret="whsec_private",
        price_by_plan={
            "professional_live": "price_pro",
            "enterprise_live": "price_ent",
        },
        livemode=False,
        usage_price_id="price_usage",
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
    assert client.stripe_version == STRIPE_API_VERSION
    assert client.max_network_retries == 2
    assert params["line_items"] == [
        {"price": "price_pro", "quantity": 1},
        {"price": "price_usage"},
    ]
    assert "quantity" not in params["line_items"][1]
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
    assert event == {
        "id": "evt_verified",
        "type": "test",
        "api_version": STRIPE_API_VERSION,
        "livemode": False,
    }
    assert client.construct_calls == [(payload, "t=1,v1=abc", "whsec_private")]
    assert client.last_event_object is not None
    assert client.last_event_object.to_dict_calls == [(True, True)]


@pytest.mark.parametrize(
    ("event", "message"),
    (
        (
            {"livemode": False},
            "webhook API version does not match",
        ),
        (
            {"api_version": "2019-12-03", "livemode": False},
            "webhook API version does not match",
        ),
        (
            {"api_version": STRIPE_API_VERSION},
            "webhook livemode was malformed",
        ),
        (
            {"api_version": STRIPE_API_VERSION, "livemode": "false"},
            "webhook livemode was malformed",
        ),
        (
            {"api_version": STRIPE_API_VERSION, "livemode": True},
            "webhook livemode does not match",
        ),
    ),
)
def test_webhook_rejects_unpinned_schema_and_wrong_provider_mode(
    provider, event: dict[str, object], message: str
) -> None:
    client = _StripeClient.instances[0]
    client.event = {"id": "evt_adversarial", "type": "test", **event}
    with pytest.raises(StripeBillingProviderError, match=message):
        provider.construct_webhook_event(
            payload=b'{"id":"evt_adversarial"}',
            signature="t=1,v1=abc",
        )
    assert client.construct_calls[-1] == (
        b'{"id":"evt_adversarial"}',
        "t=1,v1=abc",
        "whsec_private",
    )


@pytest.mark.asyncio
async def test_subscription_webhook_refresh_reads_latest_provider_state(provider) -> None:
    latest = await provider.retrieve_subscription(
        external_subscription_id="sub_current"
    )
    client = _StripeClient.instances[0]
    assert latest.payload["status"] == "active"
    assert client.subscriptions.calls == ["sub_current"]
    assert client.subscription.to_dict_calls == [(True, True)]


def _real_sdk_provider(*, webhook_secret: str) -> StripeBillingProvider:
    return StripeBillingProvider(
        secret_key="sk_test_offline",
        webhook_secret=webhook_secret,
        price_by_plan={
            "professional_live": "price_pro",
            "enterprise_live": "price_ent",
        },
        livemode=False,
        success_url="https://app.example.com/billing/success",
        cancel_url="https://app.example.com/billing/cancel",
        portal_return_url="https://app.example.com/billing",
    )


def test_real_sdk_verifies_and_converts_offline_signed_webhook() -> None:
    webhook_secret = "whsec_offline_regression"
    provider = _real_sdk_provider(webhook_secret=webhook_secret)
    timestamp = int(time.time())
    payload = json.dumps(
        {
            "id": "evt_real_sdk",
            "object": "event",
            "api_version": STRIPE_API_VERSION,
            "created": timestamp,
            "data": {
                "object": {
                    "id": "sub_real_sdk",
                    "object": "subscription",
                    "status": "active",
                }
            },
            "livemode": False,
            "pending_webhooks": 1,
            "request": {"id": "req_real_sdk", "idempotency_key": None},
            "type": "customer.subscription.updated",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signed_payload = f"{timestamp}.".encode("ascii") + payload
    digest = hmac.new(
        webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()

    event = provider.construct_webhook_event(
        payload=payload,
        signature=f"t={timestamp},v1={digest}",
    )

    assert event["id"] == "evt_real_sdk"
    assert event["data"]["object"]["id"] == "sub_real_sdk"
    assert isinstance(event["data"], dict)


@pytest.mark.asyncio
async def test_real_sdk_subscription_object_is_converted_after_refresh() -> None:
    import stripe

    provider = _real_sdk_provider(webhook_secret="whsec_offline_regression")
    subscription = stripe.Subscription.construct_from(
        {
            "id": "sub_real_sdk",
            "object": "subscription",
            "customer": "cus_real_sdk",
            "status": "active",
            "metadata": {"cas_tenant_id": "tenant-a"},
        },
        "sk_test_offline",
        stripe_version=STRIPE_API_VERSION,
    )
    retriever = _AsyncRetrieve(subscription)
    provider._client = SimpleNamespace(
        v1=SimpleNamespace(subscriptions=retriever)
    )

    snapshot = await provider.retrieve_subscription(
        external_subscription_id="sub_real_sdk"
    )

    assert retriever.calls == ["sub_real_sdk"]
    assert snapshot.payload == {
        "id": "sub_real_sdk",
        "object": "subscription",
        "customer": "cus_real_sdk",
        "status": "active",
        "metadata": {"cas_tenant_id": "tenant-a"},
    }
    assert snapshot.provider_request_id is None


def test_incomplete_configuration_fails_loud_without_importing_sdk() -> None:
    with pytest.raises(StripeBillingConfigurationError) as exc_info:
        StripeBillingProvider(
            secret_key="secret-not-printed",
            webhook_secret="",
            price_by_plan={},
            livemode=False,
            success_url="",
            cancel_url="",
            portal_return_url="",
        )
    message = str(exc_info.value)
    assert "NC_STRIPE_WEBHOOK_SECRET" in message
    assert "secret-not-printed" not in message


@pytest.mark.parametrize(
    ("secret_key", "expected_livemode", "message"),
    (
        ("sk_test_private", True, "does not match NC_STRIPE_LIVEMODE"),
        ("rk_live_private", False, "does not match NC_STRIPE_LIVEMODE"),
        ("untyped-private-key", False, "recognizable Stripe live/test prefix"),
        (" sk_test_private", False, "must not contain surrounding whitespace"),
    ),
)
def test_stripe_provider_rejects_secret_key_mode_mismatch_without_leaking_key(
    monkeypatch, secret_key: str, expected_livemode: bool, message: str
) -> None:
    _install_fake_stripe(monkeypatch)
    with pytest.raises(StripeBillingConfigurationError, match=message) as exc_info:
        StripeBillingProvider(
            secret_key=secret_key,
            webhook_secret="whsec_private",
            price_by_plan={
                "professional_live": "price_pro",
                "enterprise_live": "price_ent",
            },
            livemode=expected_livemode,
            success_url="https://app.example.com/billing/success",
            cancel_url="https://app.example.com/billing/cancel",
            portal_return_url="https://app.example.com/billing",
        )
    assert secret_key not in str(exc_info.value)
    assert _StripeClient.instances == []


@pytest.mark.parametrize("usage_price_id", ("price_pro", "not-a-price"))
def test_usage_billing_requires_a_distinct_canonical_price_before_sdk_import(
    monkeypatch, usage_price_id: str
) -> None:
    _install_fake_stripe(monkeypatch)
    with pytest.raises(
        StripeBillingConfigurationError, match="USAGE_PRICE_ID|usage price"
    ):
        StripeBillingProvider(
            secret_key="sk_test_private",
            webhook_secret="whsec_private",
            price_by_plan={
                "professional_live": "price_pro",
                "enterprise_live": "price_ent",
            },
            livemode=False,
            usage_price_id=usage_price_id,
            success_url="https://app.example.com/billing/success",
            cancel_url="https://app.example.com/billing/cancel",
            portal_return_url="https://app.example.com/billing",
        )
    assert _StripeClient.instances == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reconciliation_enabled", "expected_line_items"),
    (
        (False, [{"price": "price_pro", "quantity": 1}]),
        (
            True,
            [
                {"price": "price_pro", "quantity": 1},
                {"price": "price_usage"},
            ],
        ),
    ),
)
async def test_builder_wires_usage_price_only_when_reconciliation_is_enabled(
    monkeypatch, reconciliation_enabled: bool, expected_line_items: list[dict[str, object]]
) -> None:
    _install_fake_stripe(monkeypatch)
    built = build_billing_provider(
        SimpleNamespace(
            billing_provider="stripe",
            billing_reconciliation_enabled=reconciliation_enabled,
            stripe_secret_key="sk_test_private",
            stripe_webhook_secret="whsec_private",
            stripe_professional_price_id="price_pro",
            stripe_enterprise_price_id="price_ent",
            # A populated dark slot must not silently alter Checkout.
            stripe_usage_price_id="price_usage",
            stripe_livemode=False,
            stripe_checkout_success_url="https://app.example.com/billing/success",
            stripe_checkout_cancel_url="https://app.example.com/billing/cancel",
            stripe_portal_return_url="https://app.example.com/billing",
        )
    )
    await built.create_checkout_session(
        tenant_id="tenant-a",
        account_id="acct-a",
        email="owner@example.com",
        plan_id="professional_live",
        external_customer_id=None,
        idempotency_key="req-builder",
    )
    params, _ = _StripeClient.instances[0].checkout.calls[0]
    assert params["line_items"] == expected_line_items


def test_stripe_financial_contract_is_exactly_pinned() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative_path in ("requirements.txt", "requirements-runtime.txt"):
        requirements = (root / relative_path).read_text(encoding="utf-8")
        dependency_lines = [
            line.split("#", 1)[0].strip()
            for line in requirements.splitlines()
            if line.split("#", 1)[0].strip().startswith("stripe")
        ]
        assert dependency_lines == [f"stripe=={STRIPE_SDK_VERSION}"]
    assert STRIPE_API_VERSION == "2026-06-24.dahlia"


def test_installed_stripe_package_accepts_the_explicit_financial_contract() -> None:
    import stripe

    assert stripe.VERSION == STRIPE_SDK_VERSION
    # stripe-python's package default remains the API revision it was generated
    # against. The adapter deliberately passes the provider-selectable revision
    # to StripeClient instead; the real-client webhook and Subscription tests
    # above prove that v15.2.1 parses that explicit revision offline.
    assert stripe.api_version == "2026-05-27.dahlia"
    provider = _real_sdk_provider(
        webhook_secret="whsec_explicit_version_contract"
    )
    # This is an exact pinned-SDK integration assertion, not a production
    # dependency on private attributes: prove v15.2.1 retained the explicit
    # request version rather than silently falling back to its package default.
    request_options = provider._client._requestor._options
    assert request_options.stripe_version == STRIPE_API_VERSION
    assert request_options.max_network_retries == 2


def test_provider_rejects_an_unpinned_installed_stripe_package(monkeypatch) -> None:
    stripe = ModuleType("stripe")
    stripe.VERSION = "15.2.0"  # type: ignore[attr-defined]
    stripe.StripeClient = _StripeClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "stripe", stripe)

    with pytest.raises(
        StripeBillingConfigurationError, match="pinned financial API contract"
    ):
        StripeBillingProvider(
            secret_key="sk_test_private",
            webhook_secret="whsec_private",
            price_by_plan={
                "professional_live": "price_pro",
                "enterprise_live": "price_ent",
            },
            livemode=False,
            success_url="https://app.example.com/billing/success",
            cancel_url="https://app.example.com/billing/cancel",
            portal_return_url="https://app.example.com/billing",
        )


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
