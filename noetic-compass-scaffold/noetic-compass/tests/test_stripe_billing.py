from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import httpx
import pytest

from api.services import stripe_billing as stripe_billing_module
from api.services.billing_reconciliation import UsageDispatchContract
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
        meter_response = {
            "object": "billing.meter_event",
            "created": 1_900_000_060,
            "event_name": "cas.accelerator_milliseconds",
            "identifier": "cas_usage_abc123",
            "livemode": False,
            "payload": {
                "stripe_customer_id": "cus_bound",
                "value": "900000",
            },
            "timestamp": 1_900_000_000,
        }
        meter_body = json.dumps(meter_response, separators=(",", ":"))
        meter_event = _StripeObject(meter_response)
        meter_event.last_response = SimpleNamespace(
            body=meter_body,
            request_id="req_MeterEvent",
        )
        self.meter_events = _AsyncCreate(meter_event)
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=self.checkout),
            billing_portal=SimpleNamespace(sessions=self.portal),
            billing=SimpleNamespace(meter_events=self.meter_events),
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
    assert provider.meter_event_contract.usage_price_id == "price_usage"
    assert provider.meter_event_contract.livemode is False
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
        plan_id="professional_live",
        external_customer_id="cus_bound",
        idempotency_key="req-professional",
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


@pytest.mark.asyncio
async def test_enterprise_price_is_optional_and_non_checkout_plan_stays_closed(
    monkeypatch,
) -> None:
    _install_fake_stripe(monkeypatch)
    provider = StripeBillingProvider(
        secret_key="sk_test_private",
        webhook_secret="whsec_private",
        price_by_plan={"professional_live": "price_pro"},
        livemode=False,
        success_url="https://app.example.com/billing/success",
        cancel_url="https://app.example.com/billing/cancel",
        portal_return_url="https://app.example.com/billing",
    )

    with pytest.raises(StripeBillingProviderError, match="no Stripe price"):
        await provider.create_checkout_session(
            tenant_id="tenant-a",
            account_id="acct-a",
            email="owner@example.com",
            plan_id="enterprise_live",
            external_customer_id=None,
            idempotency_key="req-enterprise",
        )
    assert _StripeClient.instances[0].checkout.calls == []


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


def _paid_invoice_payload(*, clock: int | None = None) -> dict[str, object]:
    now = int(time.time()) if clock is None else clock
    return {
        "id": "in_paid_exact",
        "object": "invoice",
        "livemode": False,
        "status": "paid",
        "created": now - 7_200,
        "customer": "cus_bound",
        "parent": {
            "type": "subscription_details",
            "subscription_details": {"subscription": "sub_bound"},
        },
        "currency": "usd",
        "amount_due": 4999,
        "amount_paid": 4999,
        "status_transitions": {
            "finalized_at": now - 240,
            "paid_at": now - 180,
        },
        "hosted_invoice_url": (
            "https://invoice.stripe.test/i/in_paid_exact?token=opaque"
        ),
        "invoice_pdf": (
            "https://invoice.stripe.test/i/in_paid_exact/pdf?token=opaque"
        ),
        "lines": {
            "object": "list",
            "has_more": False,
            "data": [
                {
                    "id": "il_usage_exact",
                    "object": "line_item",
                    "invoice": "in_paid_exact",
                    "livemode": False,
                    "currency": "usd",
                    "pricing": {
                        "type": "price_details",
                        "price_details": {
                            "price": "price_usage",
                            "product": "prod_usage",
                        },
                    },
                    "parent": {
                        "type": "subscription_item_details",
                        "subscription_item_details": {
                            "subscription": "sub_bound",
                            "subscription_item": "si_usage_exact",
                            "proration": False,
                        },
                    },
                    "period": {"start": now - 3_600, "end": now - 300},
                    "quantity": 900_000,
                    "quantity_decimal": "900000",
                }
            ],
        },
    }


def _paid_invoice_event(*, clock: int | None = None) -> dict[str, object]:
    now = int(time.time()) if clock is None else clock
    return {
        "id": "evt_paid_exact",
        "object": "event",
        "api_version": STRIPE_API_VERSION,
        "type": "invoice.paid",
        "created": now - 120,
        "livemode": False,
        "data": {
            "object": {
                "id": "in_paid_exact",
                "object": "invoice",
            }
        },
    }


def _install_paid_invoice_response(
    provider: StripeBillingProvider,
    payload: dict[str, object],
    *, raw_payload: dict[str, object] | None = None,
) -> _AsyncRetrieve:
    response = _StripeObject(payload)
    response.last_response = SimpleNamespace(
        body=json.dumps(
            payload if raw_payload is None else raw_payload,
            sort_keys=True,
            separators=(",", ":"),
        ),
        request_id="req_PaidInvoiceExact",
    )
    retriever = _AsyncRetrieve(response)
    provider._client.v1.invoices = retriever
    return retriever


@pytest.mark.asyncio
async def test_paid_invoice_is_freshly_read_and_pdf_bytes_are_hash_bound(provider) -> None:
    clock = int(time.time())
    invoice = _paid_invoice_payload(clock=clock)
    retriever = _install_paid_invoice_response(provider, invoice)
    pdf = b"%PDF-1.7\nexact customer receipt\n%%EOF\n"
    requests: list[httpx.Request] = []

    def fetch(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(len(pdf)),
            },
            stream=httpx.ByteStream(pdf),
        )

    provider._receipt_transport = httpx.MockTransport(fetch)
    raw_event = json.dumps(
        _paid_invoice_event(clock=clock), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    result = await provider.retrieve_paid_invoice(
        event=_paid_invoice_event(clock=clock),
        raw_event_sha256=hashlib.sha256(raw_event).hexdigest(),
        contract=UsageDispatchContract(
            meter_event_name="cas.accelerator_milliseconds",
            meter_event_version="stripe_meter_event.v1",
            usage_price_id="price_usage",
            currency="usd",
            livemode=False,
        ),
        customer_receipt_allowed_hosts=("invoice.stripe.test",),
    )

    assert retriever.calls == ["in_paid_exact"]
    assert [str(request.url) for request in requests] == [invoice["invoice_pdf"]]
    assert requests[0].headers["accept-encoding"] == "identity"
    assert result.external_invoice_id == "in_paid_exact"
    assert result.external_customer_id == "cus_bound"
    assert result.external_subscription_id == "sub_bound"
    assert result.usage_quantity_milliseconds == 900_000
    assert result.invoice_pdf_sha256 == hashlib.sha256(pdf).hexdigest()
    assert result.invoice_pdf_size_bytes == len(pdf)
    assert result.provider_request_id == "req_PaidInvoiceExact"
    assert result.provider_snapshot_sha256 == hashlib.sha256(
        response_body := json.dumps(
            invoice, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    assert response_body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda payload: payload["lines"].update(has_more=True), "incomplete"),
        (lambda payload: payload["lines"].update(object="attacker"), "incomplete"),
        (
            lambda payload: payload["lines"]["data"][0].update(
                invoice="in_different"
            ),
            "different invoice",
        ),
        (
            lambda payload: payload["lines"]["data"][0]["parent"][
                "subscription_item_details"
            ].update(proration=True),
            "may not be a proration",
        ),
        (
            lambda payload: payload["lines"]["data"][0].update(
                quantity_decimal="900000.5"
            ),
            "quantity views are contradictory",
        ),
    ),
)
async def test_paid_invoice_rejects_incomplete_or_ambiguous_usage_lines(
    provider, mutation, message: str
) -> None:
    clock = int(time.time())
    invoice = deepcopy(_paid_invoice_payload(clock=clock))
    mutation(invoice)
    _install_paid_invoice_response(provider, invoice)
    fetches = 0

    def fetch(_request: httpx.Request) -> httpx.Response:
        nonlocal fetches
        fetches += 1
        return httpx.Response(
            200, stream=httpx.ByteStream(b"%PDF-1.7\nshould not fetch")
        )

    provider._receipt_transport = httpx.MockTransport(fetch)
    with pytest.raises(StripeBillingProviderError, match=message):
        await provider.retrieve_paid_invoice(
            event=_paid_invoice_event(clock=clock),
            raw_event_sha256="a" * 64,
            contract=UsageDispatchContract(
                meter_event_name="cas.accelerator_milliseconds",
                meter_event_version="stripe_meter_event.v1",
                usage_price_id="price_usage",
                currency="usd",
                livemode=False,
            ),
            customer_receipt_allowed_hosts=("invoice.stripe.test",),
        )
    assert fetches == 0


@pytest.mark.asyncio
async def test_paid_invoice_raw_provider_receipt_must_match_converted_object(
    provider,
) -> None:
    clock = int(time.time())
    invoice = _paid_invoice_payload(clock=clock)
    raw_invoice = deepcopy(invoice)
    raw_invoice["amount_paid"] = 1
    _install_paid_invoice_response(provider, invoice, raw_payload=raw_invoice)
    with pytest.raises(StripeBillingProviderError, match="contradicts"):
        await provider.retrieve_paid_invoice(
            event=_paid_invoice_event(clock=clock),
            raw_event_sha256="b" * 64,
            contract=UsageDispatchContract(
                meter_event_name="cas.accelerator_milliseconds",
                meter_event_version="stripe_meter_event.v1",
                usage_price_id="price_usage",
                currency="usd",
                livemode=False,
            ),
            customer_receipt_allowed_hosts=("invoice.stripe.test",),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "status", "headers", "content", "message"),
    (
        (
            "https://attacker.example/receipt.pdf",
            200,
            {"Content-Type": "application/pdf"},
            b"%PDF-1.7\nreceipt",
            "outside the allowlist",
        ),
        (
            "https://invoice.stripe.test/redirect.pdf",
            302,
            {
                "Location": "https://attacker.example/receipt.pdf",
                "Content-Type": "application/pdf",
            },
            b"%PDF-1.7\nreceipt",
            "HTTP 200",
        ),
        (
            "https://invoice.stripe.test/html.pdf",
            200,
            {"Content-Type": "text/html"},
            b"%PDF-1.7\nreceipt",
            "not application/pdf",
        ),
        (
            "https://invoice.stripe.test/compressed.pdf",
            200,
            {
                "Content-Type": "application/pdf",
                "Content-Encoding": "gzip",
            },
            b"%PDF-1.7\nreceipt",
            "content encoding",
        ),
        (
            "https://invoice.stripe.test/not-pdf.pdf",
            200,
            {"Content-Type": "application/pdf"},
            b"not actually a pdf",
            "PDF signature",
        ),
    ),
)
async def test_customer_receipt_download_refuses_redirects_and_unsafe_responses(
    provider, url: str, status: int, headers: dict[str, str], content: bytes, message: str
) -> None:
    fetches: list[str] = []

    def fetch(request: httpx.Request) -> httpx.Response:
        fetches.append(str(request.url))
        return httpx.Response(
            status, headers=headers, stream=httpx.ByteStream(content)
        )

    provider._receipt_transport = httpx.MockTransport(fetch)
    with pytest.raises(StripeBillingProviderError, match=message):
        await provider.download_invoice_receipt(
            url=url,
            expected_sha256=hashlib.sha256(content).hexdigest(),
            expected_size_bytes=len(content),
            customer_receipt_allowed_hosts=("invoice.stripe.test",),
        )
    assert fetches == ([] if "attacker.example" in url else [url])


@pytest.mark.asyncio
async def test_customer_receipt_download_requires_immutable_size_and_digest(
    provider,
) -> None:
    pdf = b"%PDF-1.7\nreceipt-v2\n%%EOF\n"
    provider._receipt_transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            stream=httpx.ByteStream(pdf),
        )
    )
    with pytest.raises(StripeBillingProviderError, match="no longer matches"):
        await provider.download_invoice_receipt(
            url="https://invoice.stripe.test/receipt.pdf",
            expected_sha256="c" * 64,
            expected_size_bytes=len(pdf),
            customer_receipt_allowed_hosts=("invoice.stripe.test",),
        )


@pytest.mark.parametrize(
    ("address", "expected"),
    (
        ("8.8.8.8", True),
        ("2606:4700:4700::1111", True),
        ("127.0.0.1", False),
        ("10.0.0.1", False),
        ("169.254.169.254", False),
        ("::1", False),
        ("not-an-address", False),
    ),
)
def test_customer_receipt_network_boundary_recognizes_only_global_ips(
    address: str, expected: bool
) -> None:
    assert stripe_billing_module._is_global_ip(address) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("addresses", "allowed"),
    (
        (("8.8.8.8", "2606:4700:4700::1111"), True),
        (("8.8.8.8", "127.0.0.1"), False),
        (("169.254.169.254",), False),
        ((), False),
    ),
)
async def test_customer_receipt_dns_rejects_any_non_public_answer(
    monkeypatch, addresses: tuple[str, ...], allowed: bool
) -> None:
    class _Loop:
        async def getaddrinfo(self, *_args, **_kwargs):
            return [
                (0, 0, 0, "", (address, 443)) for address in addresses
            ]

    monkeypatch.setattr(
        stripe_billing_module.asyncio, "get_running_loop", lambda: _Loop()
    )
    if allowed:
        await stripe_billing_module._require_public_receipt_dns(
            "invoice.stripe.com"
        )
    else:
        with pytest.raises(StripeBillingProviderError, match="public Internet"):
            await stripe_billing_module._require_public_receipt_dns(
                "invoice.stripe.com"
            )


def test_customer_receipt_socket_peer_must_still_be_public_after_dns() -> None:
    class _Stream:
        def __init__(self, address: str) -> None:
            self.address = address

        def get_extra_info(self, _name: str):
            return (self.address, 443)

    public = httpx.Response(
        200, extensions={"network_stream": _Stream("8.8.8.8")}
    )
    stripe_billing_module._require_public_receipt_peer(public)
    private = httpx.Response(
        200, extensions={"network_stream": _Stream("127.0.0.1")}
    )
    with pytest.raises(StripeBillingProviderError, match="public Internet"):
        stripe_billing_module._require_public_receipt_peer(private)


def _real_sdk_provider(
    *, webhook_secret: str, usage_price_id: str | None = None
) -> StripeBillingProvider:
    return StripeBillingProvider(
        secret_key="sk_test_offline",
        webhook_secret=webhook_secret,
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


@pytest.mark.asyncio
async def test_real_sdk_paid_invoice_object_preserves_pinned_dahlia_contract() -> None:
    import stripe
    from stripe._stripe_response import StripeResponse

    clock = int(time.time())
    invoice_payload = _paid_invoice_payload(clock=clock)
    response_body = json.dumps(invoice_payload, separators=(",", ":"))
    invoice = stripe.Invoice.construct_from(
        invoice_payload,
        "sk_test_offline",
        stripe_version=STRIPE_API_VERSION,
        last_response=StripeResponse(
            response_body,
            200,
            {"request-id": "req_RealPaidInvoice"},
        ),
    )
    retriever = _AsyncRetrieve(invoice)
    provider = _real_sdk_provider(
        webhook_secret="whsec_paid_invoice_regression",
        usage_price_id="price_usage",
    )
    provider._client = SimpleNamespace(v1=SimpleNamespace(invoices=retriever))
    pdf = b"%PDF-1.7\nreal sdk contract\n%%EOF\n"
    provider._receipt_transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            stream=httpx.ByteStream(pdf),
        )
    )

    result = await provider.retrieve_paid_invoice(
        event=_paid_invoice_event(clock=clock),
        raw_event_sha256="e" * 64,
        contract=UsageDispatchContract(
            meter_event_name="cas.accelerator_milliseconds",
            meter_event_version="stripe_meter_event.v1",
            usage_price_id="price_usage",
            currency="usd",
            livemode=False,
        ),
        customer_receipt_allowed_hosts=("invoice.stripe.test",),
    )

    assert retriever.calls == ["in_paid_exact"]
    assert result.provider_request_id == "req_RealPaidInvoice"
    assert result.provider_snapshot_sha256 == hashlib.sha256(
        response_body.encode("utf-8")
    ).hexdigest()
    assert result.invoice_pdf_sha256 == hashlib.sha256(pdf).hexdigest()
    assert result.usage_quantity_milliseconds == 900_000


@pytest.mark.asyncio
async def test_meter_event_is_one_exact_no_retry_idempotent_provider_attempt(provider) -> None:
    request = {
        "event_name": "cas.accelerator_milliseconds",
        "payload": {
            "stripe_customer_id": "cus_bound",
            "value": "900000",
        },
        "identifier": "cas_usage_abc123",
        "timestamp": 1_900_000_000,
    }
    receipt = await provider.submit_meter_event(request=request)
    client = _StripeClient.instances[0]

    assert client.meter_events.calls == [
        (
            request,
            {
                "idempotency_key": "cas-meter:cas_usage_abc123",
                "max_network_retries": 0,
            },
        )
    ]
    event = client.meter_events.response
    body = event.last_response.body.encode()
    assert receipt.response == event.payload
    assert event.to_dict_calls == [(True, True)]
    assert receipt.provider_request_id == "req_MeterEvent"
    assert receipt.response_sha256 == hashlib.sha256(body).hexdigest()


@pytest.mark.asyncio
async def test_real_sdk_meter_event_object_is_converted_offline_without_network() -> None:
    import stripe
    from stripe._stripe_response import StripeResponse

    provider = _real_sdk_provider(webhook_secret="whsec_meter_event_regression")
    response_payload = {
        "object": "billing.meter_event",
        "created": 1_900_000_060,
        "event_name": "cas.accelerator_milliseconds",
        "identifier": "cas_usage_abc123",
        "livemode": False,
        "payload": {
            "stripe_customer_id": "cus_bound",
            "value": "900000",
        },
        "timestamp": 1_900_000_000,
    }
    response_body = json.dumps(response_payload, separators=(",", ":"))
    event = stripe.billing.MeterEvent.construct_from(
        response_payload,
        "sk_test_offline",
        stripe_version=STRIPE_API_VERSION,
        last_response=StripeResponse(
            response_body,
            200,
            {"request-id": "req_RealMeterEvent"},
        ),
    )
    meter_events = _AsyncCreate(event)
    provider._client = SimpleNamespace(
        v1=SimpleNamespace(
            billing=SimpleNamespace(meter_events=meter_events)
        )
    )
    request = {
        "event_name": "cas.accelerator_milliseconds",
        "payload": {
            "stripe_customer_id": "cus_bound",
            "value": "900000",
        },
        "identifier": "cas_usage_abc123",
        "timestamp": 1_900_000_000,
    }

    receipt = await provider.submit_meter_event(request=request)

    assert not hasattr(event, "to_dict_recursive")
    assert meter_events.calls == [
        (
            request,
            {
                "idempotency_key": "cas-meter:cas_usage_abc123",
                "max_network_retries": 0,
            },
        )
    ]
    assert receipt.response == response_payload
    assert receipt.provider_request_id == "req_RealMeterEvent"
    assert receipt.response_sha256 == hashlib.sha256(
        response_body.encode("utf-8")
    ).hexdigest()


@pytest.mark.asyncio
async def test_meter_event_provider_refuses_invalid_request_without_network(provider) -> None:
    with pytest.raises(StripeBillingProviderError, match="request schema"):
        await provider.submit_meter_event(
            request={
                "event_name": "cas.accelerator_milliseconds",
                "payload": {
                    "stripe_customer_id": "cus_bound",
                    "value": "900000",
                },
                "identifier": "cas_usage_abc123",
                "timestamp": 1_900_000_000,
                "unexpected": "field",
            }
        )
    assert _StripeClient.instances[0].meter_events.calls == []


@pytest.mark.asyncio
async def test_meter_event_raw_receipt_mismatch_fails_uncertain_without_retry(provider) -> None:
    client = _StripeClient.instances[0]
    response = client.meter_events.response
    response.last_response.body = json.dumps(
        {**response.payload, "identifier": "cas_usage_other"}
    )
    request = {
        "event_name": "cas.accelerator_milliseconds",
        "payload": {
            "stripe_customer_id": "cus_bound",
            "value": "900000",
        },
        "identifier": "cas_usage_abc123",
        "timestamp": 1_900_000_000,
    }
    with pytest.raises(StripeBillingProviderError, match="contradicts"):
        await provider.submit_meter_event(request=request)
    assert len(client.meter_events.calls) == 1


@pytest.mark.asyncio
async def test_meter_event_provider_exception_is_not_retried(provider) -> None:
    class _FailingCreate:
        def __init__(self):
            self.calls = 0

        async def create_async(self, *_args, **_kwargs):
            self.calls += 1
            raise TimeoutError("ambiguous timeout")

    failing = _FailingCreate()
    _StripeClient.instances[0].v1.billing.meter_events = failing
    with pytest.raises(StripeBillingProviderError, match="outcome is uncertain"):
        await provider.submit_meter_event(
            request={
                "event_name": "cas.accelerator_milliseconds",
                "payload": {
                    "stripe_customer_id": "cus_bound",
                    "value": "900000",
                },
                "identifier": "cas_usage_abc123",
                "timestamp": 1_900_000_000,
            }
        )
    assert failing.calls == 1


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
