"""Stripe Checkout/Portal/webhook adapter for CAS Harness billing.

The Stripe SDK is imported only when the operator selects
``NC_BILLING_PROVIDER=stripe``.  A missing SDK or incomplete configuration then
fails loud at startup; the default ``null`` provider performs no network or
money operation.

Official Stripe guidance requires server-side Checkout creation and signature
verification over the *raw* webhook body.  Subscription access is provisioned
from verified asynchronous subscription events, never from the browser's
success redirect.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import ipaddress
import json
import re
import socket
from typing import Any, Mapping, Protocol
from urllib.parse import urlsplit

import httpx

from api.services.billing_entitlements import PLAN_CATALOG
from api.services.billing_meter_dispatch import (
    MeterEventProviderContract,
    MeterEventProviderReceipt,
)
from api.services.billing_reconciliation import (
    MAX_CUSTOMER_RECEIPT_BYTES,
    BillingReconciliationError,
    ProviderPaidInvoice,
    UsageDispatchContract,
    validate_customer_receipt_allowed_hosts,
    validate_customer_receipt_url,
)


STRIPE_SDK_VERSION = "15.2.1"
STRIPE_API_VERSION = "2026-06-24.dahlia"
_STRIPE_PRICE_ID_RE = re.compile(r"^price_[A-Za-z0-9_]{1,249}$")
_STRIPE_CUSTOMER_ID_RE = re.compile(r"^cus_[A-Za-z0-9_]{1,251}$")
_STRIPE_SUBSCRIPTION_ID_RE = re.compile(r"^sub_[A-Za-z0-9_]{1,251}$")
_STRIPE_SUBSCRIPTION_ITEM_ID_RE = re.compile(r"^si_[A-Za-z0-9_]{1,252}$")
_STRIPE_INVOICE_ID_RE = re.compile(r"^in_[A-Za-z0-9_]{1,252}$")
_STRIPE_EVENT_ID_RE = re.compile(r"^evt_[A-Za-z0-9_]{1,251}$")
_METER_EVENT_NAME_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_METER_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_MAX_METER_EVENT_RESPONSE_BYTES = 1_000_000
_MAX_INVOICE_RESPONSE_BYTES = 2_000_000
_MAX_INVOICE_LINES = 100
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class StripeBillingConfigurationError(RuntimeError):
    pass


class StripeBillingProviderError(RuntimeError):
    pass


def validate_stripe_secret_key_mode(
    secret_key: str, *, expected_livemode: bool
) -> None:
    """Bind Stripe billing mode to the configured Stripe credential mode."""

    key = secret_key.strip()
    if key != secret_key:
        raise StripeBillingConfigurationError(
            "NC_STRIPE_SECRET_KEY must not contain surrounding whitespace"
        )
    if key.startswith(("sk_live_", "rk_live_")):
        key_livemode = True
    elif key.startswith(("sk_test_", "rk_test_")):
        key_livemode = False
    else:
        raise StripeBillingConfigurationError(
            "NC_STRIPE_SECRET_KEY must have a recognizable Stripe live/test prefix "
            "when Stripe billing is enabled"
        )
    if key_livemode != expected_livemode:
        raise StripeBillingConfigurationError(
            "NC_STRIPE_SECRET_KEY mode does not match NC_STRIPE_LIVEMODE"
        )


@dataclass(frozen=True, slots=True)
class CheckoutSessionResult:
    session_id: str
    url: str


@dataclass(frozen=True, slots=True)
class PortalSessionResult:
    url: str


@dataclass(frozen=True, slots=True)
class SubscriptionSnapshot:
    payload: Mapping[str, Any]
    provider_request_id: str | None


@dataclass(frozen=True, slots=True)
class CustomerInvoiceReceipt:
    """Exact PDF bytes plus the bounded facts persisted by reconciliation."""

    content: bytes = field(repr=False)
    url: str = field(repr=False)
    http_status: int
    content_type: str
    size_bytes: int
    sha256: str
    retrieved_at: str


class BillingProvider(Protocol):
    @property
    def meter_event_contract(self) -> MeterEventProviderContract: ...

    async def create_checkout_session(
        self,
        *,
        tenant_id: str,
        account_id: str,
        email: str,
        plan_id: str,
        external_customer_id: str | None,
        checkout_request_id: str,
        idempotency_key: str,
    ) -> CheckoutSessionResult: ...

    async def create_portal_session(
        self, *, external_customer_id: str
    ) -> PortalSessionResult: ...

    def construct_webhook_event(
        self, *, payload: bytes, signature: str
    ) -> Mapping[str, Any]: ...

    async def retrieve_subscription(
        self, *, external_subscription_id: str
    ) -> SubscriptionSnapshot: ...

    async def retrieve_paid_invoice(
        self,
        *,
        event: Mapping[str, Any],
        raw_event_sha256: str,
        contract: UsageDispatchContract,
        customer_receipt_allowed_hosts: tuple[str, ...],
    ) -> ProviderPaidInvoice: ...

    async def download_invoice_receipt(
        self,
        *,
        url: str,
        expected_sha256: str,
        expected_size_bytes: int,
        customer_receipt_allowed_hosts: tuple[str, ...],
    ) -> CustomerInvoiceReceipt: ...

    async def submit_meter_event(
        self, *, request: Mapping[str, object]
    ) -> MeterEventProviderReceipt: ...


class NullBillingProvider:
    """Honest default: no checkout, portal, webhook, or money movement."""

    @property
    def meter_event_contract(self) -> MeterEventProviderContract:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def create_checkout_session(self, **_: object) -> CheckoutSessionResult:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def create_portal_session(self, **_: object) -> PortalSessionResult:
        raise StripeBillingProviderError("Stripe billing is not configured")

    def construct_webhook_event(self, **_: object) -> Mapping[str, Any]:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def retrieve_subscription(self, **_: object) -> SubscriptionSnapshot:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def retrieve_paid_invoice(self, **_: object) -> ProviderPaidInvoice:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def download_invoice_receipt(
        self, **_: object
    ) -> CustomerInvoiceReceipt:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def submit_meter_event(self, **_: object) -> MeterEventProviderReceipt:
        raise StripeBillingProviderError("Stripe billing is not configured")


class StripeBillingProvider:
    def __init__(
        self,
        *,
        secret_key: str,
        webhook_secret: str,
        price_by_plan: Mapping[str, str],
        livemode: bool,
        usage_price_id: str | None = None,
        success_url: str,
        cancel_url: str,
        portal_return_url: str,
        receipt_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        required = {
            "NC_STRIPE_SECRET_KEY": secret_key,
            "NC_STRIPE_WEBHOOK_SECRET": webhook_secret,
            "NC_STRIPE_PROFESSIONAL_PRICE_ID": price_by_plan.get(
                "professional_live", ""
            ),
            "NC_STRIPE_CHECKOUT_SUCCESS_URL": success_url,
            "NC_STRIPE_CHECKOUT_CANCEL_URL": cancel_url,
            "NC_STRIPE_PORTAL_RETURN_URL": portal_return_url,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise StripeBillingConfigurationError(
                "Stripe billing configuration is incomplete: " + ", ".join(missing)
            )
        unknown_plans = set(price_by_plan).difference(PLAN_CATALOG)
        if unknown_plans:
            raise StripeBillingConfigurationError(
                "Stripe price mapping contains an unknown server plan"
            )
        normalized_prices: dict[str, str] = {}
        for plan_id, raw_price in price_by_plan.items():
            price_id = str(raw_price or "")
            if not price_id:
                continue
            if price_id != price_id.strip() or not _STRIPE_PRICE_ID_RE.fullmatch(
                price_id
            ):
                raise StripeBillingConfigurationError(
                    "Stripe plan prices must be canonical Stripe price ids"
                )
            normalized_prices[plan_id] = price_id
        checkout_plans = {
            plan.plan_id
            for plan in PLAN_CATALOG.values()
            if plan.paid and plan.checkout_available
        }
        if not checkout_plans.issubset(normalized_prices):
            raise StripeBillingConfigurationError(
                "Stripe billing configuration is missing a checkout-enabled plan price"
            )
        if len(set(normalized_prices.values())) != len(normalized_prices):
            raise StripeBillingConfigurationError(
                "Stripe configured plan price ids must be distinct"
            )
        if not isinstance(livemode, bool):
            raise StripeBillingConfigurationError(
                "NC_STRIPE_LIVEMODE must be a Boolean"
            )
        validate_stripe_secret_key_mode(
            secret_key, expected_livemode=livemode
        )
        if usage_price_id is not None:
            if not _STRIPE_PRICE_ID_RE.fullmatch(usage_price_id):
                raise StripeBillingConfigurationError(
                    "NC_STRIPE_USAGE_PRICE_ID must be a canonical Stripe price id"
                )
            if usage_price_id in set(normalized_prices.values()):
                raise StripeBillingConfigurationError(
                    "Stripe usage price id must be distinct from flat subscription "
                    "price ids"
                )
        for name, url in (
            ("NC_STRIPE_CHECKOUT_SUCCESS_URL", success_url),
            ("NC_STRIPE_CHECKOUT_CANCEL_URL", cancel_url),
            ("NC_STRIPE_PORTAL_RETURN_URL", portal_return_url),
        ):
            if not url.startswith("https://"):
                raise StripeBillingConfigurationError(f"{name} must use https://")
        try:
            from stripe import VERSION as installed_stripe_version
            from stripe import StripeClient
        except ImportError as exc:  # pragma: no cover - exercised through builder tests
            raise StripeBillingConfigurationError(
                "NC_BILLING_PROVIDER=stripe requires stripe-python"
            ) from exc
        if installed_stripe_version != STRIPE_SDK_VERSION:
            raise StripeBillingConfigurationError(
                "installed stripe-python version does not match the pinned "
                "financial API contract"
            )

        self._client = StripeClient(
            secret_key,
            stripe_version=STRIPE_API_VERSION,
            max_network_retries=2,
        )
        self._webhook_secret = webhook_secret
        self._livemode = livemode
        self._price_by_plan = normalized_prices
        self._usage_price_id = usage_price_id
        self._success_url = success_url
        self._cancel_url = cancel_url
        self._portal_return_url = portal_return_url
        self._receipt_transport = receipt_transport

    @property
    def meter_event_contract(self) -> MeterEventProviderContract:
        if self._usage_price_id is None:
            raise StripeBillingProviderError(
                "Stripe usage price is not configured for Meter Event dispatch"
            )
        return MeterEventProviderContract(
            usage_price_id=self._usage_price_id,
            livemode=self._livemode,
        )

    async def create_checkout_session(
        self,
        *,
        tenant_id: str,
        account_id: str,
        email: str,
        plan_id: str,
        external_customer_id: str | None,
        checkout_request_id: str,
        idempotency_key: str,
    ) -> CheckoutSessionResult:
        plan = PLAN_CATALOG.get(plan_id)
        if plan is None or not plan.paid or not plan.checkout_available:
            raise StripeBillingProviderError(
                f"no Stripe price configured for Checkout plan {plan_id}"
            )
        price_id = self._price_by_plan.get(plan_id)
        if not price_id:
            raise StripeBillingProviderError(f"no Stripe price configured for {plan_id}")
        metadata = {
            "cas_tenant_id": tenant_id,
            "cas_account_id": account_id,
            "cas_plan_id": plan_id,
            "cas_checkout_request_id": checkout_request_id,
        }
        line_items = [{"price": price_id, "quantity": 1}]
        if self._usage_price_id is not None:
            line_items.append({"price": self._usage_price_id})
        params: dict[str, object] = {
            "mode": "subscription",
            "line_items": line_items,
            "client_reference_id": tenant_id,
            "success_url": self._success_url,
            "cancel_url": self._cancel_url,
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
            "allow_promotion_codes": True,
        }
        if external_customer_id:
            params["customer"] = external_customer_id
        else:
            params["customer_email"] = email
        try:
            session = await self._client.v1.checkout.sessions.create_async(
                params, options={"idempotency_key": idempotency_key}
            )
        except Exception as exc:  # Stripe exceptions are optional-import types
            raise StripeBillingProviderError("Stripe Checkout session creation failed") from exc
        session_id = str(getattr(session, "id", "") or "")
        url = str(getattr(session, "url", "") or "")
        if not session_id or not url.startswith("https://"):
            raise StripeBillingProviderError("Stripe returned an invalid Checkout session")
        return CheckoutSessionResult(session_id=session_id, url=url)

    async def create_portal_session(
        self, *, external_customer_id: str
    ) -> PortalSessionResult:
        try:
            session = await self._client.v1.billing_portal.sessions.create_async(
                {
                    "customer": external_customer_id,
                    "return_url": self._portal_return_url,
                }
            )
        except Exception as exc:
            raise StripeBillingProviderError("Stripe portal session creation failed") from exc
        url = str(getattr(session, "url", "") or "")
        if not url.startswith("https://"):
            raise StripeBillingProviderError("Stripe returned an invalid portal session")
        return PortalSessionResult(url=url)

    def construct_webhook_event(
        self, *, payload: bytes, signature: str
    ) -> Mapping[str, Any]:
        try:
            event = self._client.construct_event(
                payload, signature, self._webhook_secret
            )
            plain = event.to_dict(recursive=True, for_json=True)
        except Exception as exc:
            raise StripeBillingProviderError(
                "Stripe webhook signature verification failed"
            ) from exc
        if not isinstance(plain, Mapping):
            raise StripeBillingProviderError("Stripe webhook event was malformed")
        if plain.get("api_version") != STRIPE_API_VERSION:
            raise StripeBillingProviderError(
                "Stripe webhook API version does not match the pinned contract"
            )
        event_livemode = plain.get("livemode")
        if not isinstance(event_livemode, bool):
            raise StripeBillingProviderError(
                "Stripe webhook livemode was malformed"
            )
        if event_livemode != self._livemode:
            raise StripeBillingProviderError(
                "Stripe webhook livemode does not match NC_STRIPE_LIVEMODE"
            )
        return plain

    async def retrieve_subscription(
        self, *, external_subscription_id: str
    ) -> SubscriptionSnapshot:
        try:
            subscription = await self._client.v1.subscriptions.retrieve_async(
                external_subscription_id
            )
            plain = subscription.to_dict(recursive=True, for_json=True)
            last_response = getattr(subscription, "last_response", None)
            request_id = str(
                getattr(last_response, "request_id", "") or ""
            ).strip() or None
        except Exception as exc:
            raise StripeBillingProviderError(
                "Stripe subscription refresh failed"
            ) from exc
        if not isinstance(plain, Mapping):
            raise StripeBillingProviderError(
                "Stripe returned a malformed subscription"
            )
        return SubscriptionSnapshot(
            payload=plain,
            provider_request_id=request_id,
        )

    async def retrieve_paid_invoice(
        self,
        *,
        event: Mapping[str, Any],
        raw_event_sha256: str,
        contract: UsageDispatchContract,
        customer_receipt_allowed_hosts: tuple[str, ...],
    ) -> ProviderPaidInvoice:
        """Refresh one signature-verified ``invoice.paid`` and fetch its PDF.

        The webhook route verifies the signature over the original bytes before
        calling this method.  Only the event identity and timestamp come from
        those bytes; all financial and receipt facts come from a fresh Stripe
        invoice readback plus the exact downloaded PDF.
        """

        if not isinstance(contract, UsageDispatchContract):
            raise StripeBillingProviderError(
                "billing invoice reconciliation contract is unavailable"
            )
        if (
            self._usage_price_id is None
            or contract.usage_price_id != self._usage_price_id
            or contract.livemode != self._livemode
        ):
            raise StripeBillingProviderError(
                "billing invoice reconciliation contract contradicts the Stripe provider"
            )
        raw_digest = _sha256_hex(raw_event_sha256, "raw Stripe event")
        event_facts = _invoice_event_identity(event, livemode=self._livemode)
        invoice_id = str(event_facts["invoice_id"])
        try:
            invoice = await self._client.v1.invoices.retrieve_async(invoice_id)
            plain = invoice.to_dict(recursive=True, for_json=True)
            last_response = getattr(invoice, "last_response", None)
            response_body = getattr(last_response, "body", None)
            provider_request_id = str(
                getattr(last_response, "request_id", "") or ""
            ).strip() or None
        except Exception as exc:
            raise StripeBillingProviderError(
                "Stripe paid invoice refresh failed"
            ) from exc
        if not isinstance(plain, Mapping):
            raise StripeBillingProviderError(
                "Stripe returned a malformed paid invoice"
            )
        if not isinstance(response_body, str) or not response_body:
            raise StripeBillingProviderError(
                "Stripe paid invoice response receipt is unavailable"
            )
        response_bytes = response_body.encode("utf-8")
        if len(response_bytes) > _MAX_INVOICE_RESPONSE_BYTES:
            raise StripeBillingProviderError(
                "Stripe paid invoice response receipt exceeds the size limit"
            )
        try:
            raw_snapshot = json.loads(response_body)
        except (TypeError, ValueError) as exc:
            raise StripeBillingProviderError(
                "Stripe paid invoice response receipt is invalid JSON"
            ) from exc
        if not isinstance(raw_snapshot, Mapping) or dict(raw_snapshot) != dict(plain):
            raise StripeBillingProviderError(
                "Stripe paid invoice object contradicts its raw response receipt"
            )
        if self._livemode and provider_request_id is None:
            raise StripeBillingProviderError(
                "live Stripe paid invoice response has no request receipt"
            )

        snapshot_retrieved_at = _now_iso()
        invoice_facts = _paid_invoice_facts(
            plain,
            expected_invoice_id=invoice_id,
            usage_price_id=contract.usage_price_id,
            livemode=self._livemode,
        )
        if invoice_facts["currency"] != contract.currency:
            raise StripeBillingProviderError(
                "Stripe paid invoice currency contradicts the billing contract"
            )
        try:
            normalized_hosts = validate_customer_receipt_allowed_hosts(
                customer_receipt_allowed_hosts
            )
            hosted_invoice_url = validate_customer_receipt_url(
                invoice_facts["hosted_invoice_url"],
                allowed_hosts=normalized_hosts,
            )
        except BillingReconciliationError as exc:
            raise StripeBillingProviderError(
                "Stripe paid invoice receipt URL contract is invalid"
            ) from exc
        receipt = await self._fetch_customer_invoice_receipt(
            str(invoice_facts["invoice_pdf"]),
            allowed_hosts=normalized_hosts,
        )
        return ProviderPaidInvoice(
            provider_event_id=str(event_facts["event_id"]),
            provider_event_created=int(event_facts["event_created"]),
            created=int(invoice_facts["created"]),
            status_transitions_finalized_at=int(
                invoice_facts["status_transitions_finalized_at"]
            ),
            external_invoice_id=invoice_id,
            external_customer_id=str(invoice_facts["customer_id"]),
            external_subscription_id=str(invoice_facts["subscription_id"]),
            provider_status="paid",
            provider_paid=True,
            currency=str(invoice_facts["currency"]),
            amount_due_minor=int(invoice_facts["amount_due_minor"]),
            amount_paid_minor=int(invoice_facts["amount_paid_minor"]),
            usage_price_id=contract.usage_price_id,
            meter_event_name=contract.meter_event_name,
            meter_event_version=contract.meter_event_version,
            livemode=self._livemode,
            usage_quantity_milliseconds=int(
                invoice_facts["usage_quantity_milliseconds"]
            ),
            usage_period_start=_stripe_time_iso(
                invoice_facts["usage_period_start"], "invoice usage period start"
            ),
            usage_period_end=_stripe_time_iso(
                invoice_facts["usage_period_end"], "invoice usage period end"
            ),
            paid_at=_stripe_time_iso(
                invoice_facts["paid_at"], "invoice paid timestamp"
            ),
            raw_event_sha256=raw_digest,
            provider_snapshot_sha256=hashlib.sha256(response_bytes).hexdigest(),
            provider_snapshot_retrieved_at=snapshot_retrieved_at,
            hosted_invoice_url=hosted_invoice_url,
            invoice_pdf=receipt.url,
            invoice_pdf_http_status=receipt.http_status,
            invoice_pdf_content_type=receipt.content_type,
            invoice_pdf_size_bytes=receipt.size_bytes,
            invoice_pdf_sha256=receipt.sha256,
            invoice_pdf_retrieved_at=receipt.retrieved_at,
            provider_request_id=provider_request_id,
        )

    async def download_invoice_receipt(
        self,
        *,
        url: str,
        expected_sha256: str,
        expected_size_bytes: int,
        customer_receipt_allowed_hosts: tuple[str, ...],
    ) -> CustomerInvoiceReceipt:
        """Re-fetch one private ledger URL and require exact immutable bytes."""

        expected_digest = _sha256_hex(
            expected_sha256, "stored customer invoice receipt"
        )
        if (
            not isinstance(expected_size_bytes, int)
            or isinstance(expected_size_bytes, bool)
            or expected_size_bytes <= 0
            or expected_size_bytes > MAX_CUSTOMER_RECEIPT_BYTES
        ):
            raise StripeBillingProviderError(
                "stored customer invoice receipt size is invalid"
            )
        try:
            normalized_hosts = validate_customer_receipt_allowed_hosts(
                customer_receipt_allowed_hosts
            )
        except BillingReconciliationError as exc:
            raise StripeBillingProviderError(
                "customer invoice receipt allowlist is invalid"
            ) from exc
        receipt = await self._fetch_customer_invoice_receipt(
            url, allowed_hosts=normalized_hosts
        )
        if receipt.size_bytes != expected_size_bytes or not hmac.compare_digest(
            receipt.sha256, expected_digest
        ):
            raise StripeBillingProviderError(
                "customer invoice receipt no longer matches its immutable record"
            )
        return receipt

    async def _fetch_customer_invoice_receipt(
        self, url: str, *, allowed_hosts: tuple[str, ...]
    ) -> CustomerInvoiceReceipt:
        try:
            validated_url = validate_customer_receipt_url(
                url, allowed_hosts=allowed_hosts
            )
        except BillingReconciliationError as exc:
            raise StripeBillingProviderError(
                "customer invoice receipt URL is outside the allowlist"
            ) from exc
        if self._receipt_transport is None:
            host = urlsplit(validated_url).hostname
            assert host is not None  # validated canonical HTTPS URL
            await _require_public_receipt_dns(host)
        timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=timeout,
                trust_env=False,
                transport=self._receipt_transport,
                limits=httpx.Limits(
                    max_connections=4,
                    max_keepalive_connections=0,
                ),
            ) as client:
                async with client.stream(
                    "GET",
                    validated_url,
                    headers={
                        "Accept": "application/pdf",
                        "Accept-Encoding": "identity",
                        "User-Agent": "CAS-Harness-Billing-Receipt/1.0",
                    },
                ) as response:
                    if self._receipt_transport is None:
                        _require_public_receipt_peer(response)
                    if response.status_code != 200:
                        raise StripeBillingProviderError(
                            "customer invoice receipt fetch did not return HTTP 200"
                        )
                    content_encoding = response.headers.get("content-encoding", "")
                    if content_encoding not in {"", "identity"}:
                        raise StripeBillingProviderError(
                            "customer invoice receipt used an unsupported content encoding"
                        )
                    content_type = response.headers.get("content-type", "")
                    if content_type != "application/pdf":
                        raise StripeBillingProviderError(
                            "customer invoice receipt is not application/pdf"
                        )
                    declared_size = _content_length(response.headers.get("content-length"))
                    chunks: list[bytes] = []
                    observed_size = 0
                    async for chunk in response.aiter_raw():
                        observed_size += len(chunk)
                        if observed_size > MAX_CUSTOMER_RECEIPT_BYTES:
                            raise StripeBillingProviderError(
                                "customer invoice receipt exceeds the size limit"
                            )
                        chunks.append(chunk)
        except StripeBillingProviderError:
            raise
        except (httpx.HTTPError, OSError) as exc:
            raise StripeBillingProviderError(
                "customer invoice receipt fetch failed"
            ) from exc
        content = b"".join(chunks)
        if declared_size is not None and declared_size != len(content):
            raise StripeBillingProviderError(
                "customer invoice receipt Content-Length is contradictory"
            )
        if not content.startswith(b"%PDF-"):
            raise StripeBillingProviderError(
                "customer invoice receipt does not contain a PDF signature"
            )
        return CustomerInvoiceReceipt(
            content=content,
            url=validated_url,
            http_status=200,
            content_type="application/pdf",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            retrieved_at=_now_iso(),
        )

    async def submit_meter_event(
        self, *, request: Mapping[str, object]
    ) -> MeterEventProviderReceipt:
        """Make one literal Stripe Meter Event request with SDK retries off.

        The durable dispatcher has already quarantined the row before entering
        this method. ``identifier`` is both Stripe's Meter Event identifier and
        the HTTP idempotency key, but local safety does not depend on replaying
        either: this method is invoked once for one reservation.
        """

        payload = _validated_meter_event_request(request)
        identifier = str(payload["identifier"])
        try:
            event = await self._client.v1.billing.meter_events.create_async(
                payload,
                options={
                    "idempotency_key": f"cas-meter:{identifier}",
                    "max_network_retries": 0,
                },
            )
            plain = event.to_dict(recursive=True, for_json=True)
            last_response = getattr(event, "last_response", None)
            response_body = getattr(last_response, "body", None)
            provider_request_id = str(
                getattr(last_response, "request_id", "") or ""
            ).strip() or None
        except Exception as exc:
            raise StripeBillingProviderError(
                "Stripe Meter Event submission outcome is uncertain"
            ) from exc
        if not isinstance(plain, Mapping):
            raise StripeBillingProviderError(
                "Stripe returned a malformed Meter Event"
            )
        if not isinstance(response_body, str) or not response_body:
            raise StripeBillingProviderError(
                "Stripe Meter Event response receipt is unavailable"
            )
        response_bytes = response_body.encode("utf-8")
        if len(response_bytes) > _MAX_METER_EVENT_RESPONSE_BYTES:
            raise StripeBillingProviderError(
                "Stripe Meter Event response receipt exceeds the size limit"
            )
        try:
            raw_payload = json.loads(response_body)
        except (TypeError, ValueError) as exc:
            raise StripeBillingProviderError(
                "Stripe Meter Event response receipt is invalid JSON"
            ) from exc
        if not isinstance(raw_payload, Mapping) or dict(raw_payload) != dict(plain):
            raise StripeBillingProviderError(
                "Stripe Meter Event object contradicts its raw response receipt"
            )
        if self._livemode and provider_request_id is None:
            raise StripeBillingProviderError(
                "live Stripe Meter Event response has no request receipt"
            )
        return MeterEventProviderReceipt(
            response=dict(plain),
            provider_request_id=provider_request_id,
            response_sha256=hashlib.sha256(response_bytes).hexdigest(),
        )


def _invoice_event_identity(
    event: Mapping[str, Any], *, livemode: bool
) -> dict[str, object]:
    if not isinstance(event, Mapping) or event.get("type") != "invoice.paid":
        raise StripeBillingProviderError(
            "paid invoice refresh requires an invoice.paid event"
        )
    if event.get("object") != "event" or event.get("api_version") != STRIPE_API_VERSION:
        raise StripeBillingProviderError(
            "paid invoice event does not match the pinned Stripe contract"
        )
    event_id = _typed_stripe_id(
        event.get("id"), _STRIPE_EVENT_ID_RE, "Stripe event id"
    )
    event_created = _positive_int(event.get("created"), "Stripe event created")
    if event.get("livemode") is not livemode:
        raise StripeBillingProviderError(
            "paid invoice event mode contradicts the Stripe provider"
        )
    data = event.get("data")
    obj = data.get("object") if isinstance(data, Mapping) else None
    if not isinstance(obj, Mapping):
        raise StripeBillingProviderError(
            "paid invoice event data.object is missing"
        )
    if obj.get("object") != "invoice":
        raise StripeBillingProviderError(
            "paid invoice event data.object type is invalid"
        )
    invoice_id = _typed_stripe_id(
        obj.get("id"), _STRIPE_INVOICE_ID_RE, "Stripe invoice id"
    )
    return {
        "event_id": event_id,
        "event_created": event_created,
        "invoice_id": invoice_id,
    }


def _paid_invoice_facts(
    invoice: Mapping[str, Any],
    *,
    expected_invoice_id: str,
    usage_price_id: str,
    livemode: bool,
) -> dict[str, object]:
    if invoice.get("object") != "invoice":
        raise StripeBillingProviderError("Stripe paid invoice object type is invalid")
    invoice_id = _typed_stripe_id(
        invoice.get("id"), _STRIPE_INVOICE_ID_RE, "Stripe invoice id"
    )
    if invoice_id != expected_invoice_id:
        raise StripeBillingProviderError(
            "Stripe refreshed a different paid invoice than requested"
        )
    if invoice.get("livemode") is not livemode:
        raise StripeBillingProviderError(
            "Stripe paid invoice mode contradicts the configured provider"
        )
    if invoice.get("status") != "paid":
        raise StripeBillingProviderError(
            "Stripe refreshed invoice is not provider-paid"
        )
    customer_id = _expanded_stripe_id(
        invoice.get("customer"), _STRIPE_CUSTOMER_ID_RE, "Stripe customer id"
    )
    parent = invoice.get("parent")
    if not isinstance(parent, Mapping) or parent.get("type") != "subscription_details":
        raise StripeBillingProviderError(
            "Stripe paid invoice is not bound to one subscription"
        )
    subscription_details = parent.get("subscription_details")
    if not isinstance(subscription_details, Mapping):
        raise StripeBillingProviderError(
            "Stripe paid invoice subscription details are missing"
        )
    subscription_id = _expanded_stripe_id(
        subscription_details.get("subscription"),
        _STRIPE_SUBSCRIPTION_ID_RE,
        "Stripe subscription id",
    )
    currency = invoice.get("currency")
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isascii()
        or not currency.isalpha()
        or currency != currency.lower()
    ):
        raise StripeBillingProviderError(
            "Stripe paid invoice currency is invalid"
        )
    lines = invoice.get("lines")
    if (
        not isinstance(lines, Mapping)
        or lines.get("object") != "list"
        or lines.get("has_more") is not False
    ):
        raise StripeBillingProviderError(
            "Stripe paid invoice line readback is incomplete"
        )
    line_rows = lines.get("data")
    if (
        not isinstance(line_rows, list)
        or not line_rows
        or len(line_rows) > _MAX_INVOICE_LINES
        or any(not isinstance(row, Mapping) for row in line_rows)
    ):
        raise StripeBillingProviderError(
            "Stripe paid invoice lines are malformed or exceed the bound"
        )
    usage_lines: list[Mapping[str, Any]] = []
    for row in line_rows:
        assert isinstance(row, Mapping)
        pricing = row.get("pricing")
        if not isinstance(pricing, Mapping) or pricing.get("type") != "price_details":
            raise StripeBillingProviderError(
                "Stripe paid invoice line pricing is malformed"
            )
        price_details = pricing.get("price_details")
        if not isinstance(price_details, Mapping):
            raise StripeBillingProviderError(
                "Stripe paid invoice line price details are malformed"
            )
        line_price_id = _expanded_stripe_id(
            price_details.get("price"),
            _STRIPE_PRICE_ID_RE,
            "Stripe invoice line price id",
        )
        if line_price_id == usage_price_id:
            usage_lines.append(row)
    if len(usage_lines) != 1:
        raise StripeBillingProviderError(
            "Stripe paid invoice must contain exactly one configured usage line"
        )
    usage_line = usage_lines[0]
    if usage_line.get("object") != "line_item":
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line object type is invalid"
        )
    if usage_line.get("livemode") is not livemode:
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line mode is invalid"
        )
    if usage_line.get("currency") != currency:
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line currency is contradictory"
        )
    line_invoice_id = _expanded_stripe_id(
        usage_line.get("invoice"),
        _STRIPE_INVOICE_ID_RE,
        "Stripe invoice line invoice id",
    )
    if line_invoice_id != invoice_id:
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line belongs to a different invoice"
        )
    line_parent = usage_line.get("parent")
    if (
        not isinstance(line_parent, Mapping)
        or line_parent.get("type") != "subscription_item_details"
    ):
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line is not subscription-bound"
        )
    item_details = line_parent.get("subscription_item_details")
    if not isinstance(item_details, Mapping):
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line subscription details are missing"
        )
    if item_details.get("proration") is not False:
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line may not be a proration"
        )
    _typed_stripe_id(
        item_details.get("subscription_item"),
        _STRIPE_SUBSCRIPTION_ITEM_ID_RE,
        "Stripe invoice line subscription item id",
    )
    line_subscription_id = _expanded_stripe_id(
        item_details.get("subscription"),
        _STRIPE_SUBSCRIPTION_ID_RE,
        "Stripe invoice line subscription id",
    )
    if line_subscription_id != subscription_id:
        raise StripeBillingProviderError(
            "Stripe paid invoice usage line contradicts its subscription"
        )
    period = usage_line.get("period")
    if not isinstance(period, Mapping):
        raise StripeBillingProviderError(
            "Stripe paid invoice usage period is missing"
        )
    transitions = invoice.get("status_transitions")
    if not isinstance(transitions, Mapping):
        raise StripeBillingProviderError(
            "Stripe paid invoice status transitions are missing"
        )
    hosted_invoice_url = invoice.get("hosted_invoice_url")
    invoice_pdf = invoice.get("invoice_pdf")
    if not isinstance(hosted_invoice_url, str) or not isinstance(invoice_pdf, str):
        raise StripeBillingProviderError(
            "Stripe paid invoice customer receipt URLs are missing"
        )
    return {
        "created": _positive_int(invoice.get("created"), "Stripe invoice created"),
        "status_transitions_finalized_at": _positive_int(
            transitions.get("finalized_at"), "Stripe invoice finalized timestamp"
        ),
        "paid_at": _positive_int(
            transitions.get("paid_at"), "Stripe invoice paid timestamp"
        ),
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "currency": currency,
        "amount_due_minor": _nonnegative_int(
            invoice.get("amount_due"), "Stripe invoice amount due"
        ),
        "amount_paid_minor": _nonnegative_int(
            invoice.get("amount_paid"), "Stripe invoice amount paid"
        ),
        "usage_quantity_milliseconds": _exact_invoice_line_quantity(usage_line),
        "usage_period_start": _positive_int(
            period.get("start"), "Stripe invoice usage period start"
        ),
        "usage_period_end": _positive_int(
            period.get("end"), "Stripe invoice usage period end"
        ),
        "hosted_invoice_url": hosted_invoice_url,
        "invoice_pdf": invoice_pdf,
    }


def _expanded_stripe_id(
    value: object, pattern: re.Pattern[str], label: str
) -> str:
    if isinstance(value, Mapping):
        value = value.get("id")
    return _typed_stripe_id(value, pattern, label)


def _typed_stripe_id(
    value: object, pattern: re.Pattern[str], label: str
) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise StripeBillingProviderError(f"{label} is invalid")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise StripeBillingProviderError(f"{label} is invalid")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise StripeBillingProviderError(f"{label} is invalid")
    return value


def _exact_invoice_line_quantity(line: Mapping[str, Any]) -> int:
    """Require Stripe's integer and full-precision quantity views to agree."""

    quantity = _nonnegative_int(
        line.get("quantity"), "Stripe invoice usage quantity"
    )
    quantity_decimal = line.get("quantity_decimal")
    if quantity_decimal is None:
        return quantity
    if (
        not isinstance(quantity_decimal, str)
        or re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,12})?", quantity_decimal)
        is None
    ):
        raise StripeBillingProviderError(
            "Stripe invoice usage quantity_decimal is invalid"
        )
    try:
        decimal_quantity = Decimal(quantity_decimal)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
        raise StripeBillingProviderError(
            "Stripe invoice usage quantity_decimal is invalid"
        ) from exc
    if decimal_quantity != Decimal(quantity):
        raise StripeBillingProviderError(
            "Stripe invoice usage quantity views are contradictory"
        )
    return quantity


def _stripe_time_iso(value: object, label: str) -> str:
    timestamp = _positive_int(value, label)
    try:
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
    except (OverflowError, OSError, ValueError) as exc:
        raise StripeBillingProviderError(f"{label} is outside the supported range") from exc


def _sha256_hex(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise StripeBillingProviderError(f"{label} digest is invalid")
    return value


def _content_length(value: str | None) -> int | None:
    if value is None:
        return None
    if not value.isdigit():
        raise StripeBillingProviderError(
            "customer invoice receipt Content-Length is invalid"
        )
    size = int(value)
    if size <= 0 or size > MAX_CUSTOMER_RECEIPT_BYTES:
        raise StripeBillingProviderError(
            "customer invoice receipt Content-Length exceeds the size bound"
        )
    return size


async def _require_public_receipt_dns(host: str) -> None:
    """Refuse private/reserved DNS answers before the receipt GET is sent."""

    loop = asyncio.get_running_loop()
    try:
        rows = await asyncio.wait_for(
            loop.getaddrinfo(
                host,
                443,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            ),
            timeout=5.0,
        )
    except (OSError, TimeoutError) as exc:
        raise StripeBillingProviderError(
            "customer invoice receipt DNS resolution failed"
        ) from exc
    addresses = {str(row[4][0]) for row in rows if row[4]}
    if not addresses or any(not _is_global_ip(address) for address in addresses):
        raise StripeBillingProviderError(
            "customer invoice receipt DNS resolved outside the public Internet"
        )


def _require_public_receipt_peer(response: httpx.Response) -> None:
    """Catch DNS rebinding by checking the socket peer before reading bytes."""

    stream = response.extensions.get("network_stream")
    try:
        server_address = (
            stream.get_extra_info("server_addr") if stream is not None else None
        )
    except Exception as exc:  # pragma: no cover - defensive transport boundary
        raise StripeBillingProviderError(
            "customer invoice receipt peer address is unavailable"
        ) from exc
    if (
        not isinstance(server_address, (tuple, list))
        or not server_address
        or not _is_global_ip(server_address[0])
    ):
        raise StripeBillingProviderError(
            "customer invoice receipt peer is outside the public Internet"
        )


def _is_global_ip(value: object) -> bool:
    try:
        return ipaddress.ip_address(str(value)).is_global
    except ValueError:
        return False


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _validated_meter_event_request(
    request: Mapping[str, object],
) -> dict[str, object]:
    expected_fields = {"event_name", "payload", "identifier", "timestamp"}
    if not isinstance(request, Mapping) or set(request) != expected_fields:
        raise StripeBillingProviderError("Stripe Meter Event request schema is invalid")
    event_name = request.get("event_name")
    identifier = request.get("identifier")
    timestamp = request.get("timestamp")
    payload = request.get("payload")
    if not isinstance(event_name, str) or _METER_EVENT_NAME_RE.fullmatch(event_name) is None:
        raise StripeBillingProviderError("Stripe Meter Event name is invalid")
    if not isinstance(identifier, str) or _METER_IDENTIFIER_RE.fullmatch(identifier) is None:
        raise StripeBillingProviderError("Stripe Meter Event identifier is invalid")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp <= 0:
        raise StripeBillingProviderError("Stripe Meter Event timestamp is invalid")
    if not isinstance(payload, Mapping) or set(payload) != {
        "stripe_customer_id",
        "value",
    }:
        raise StripeBillingProviderError("Stripe Meter Event payload schema is invalid")
    customer_id = payload.get("stripe_customer_id")
    value = payload.get("value")
    if not isinstance(customer_id, str) or _STRIPE_CUSTOMER_ID_RE.fullmatch(customer_id) is None:
        raise StripeBillingProviderError("Stripe Meter Event customer is invalid")
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdigit()
        or value.startswith("0")
        or int(value) <= 0
    ):
        raise StripeBillingProviderError("Stripe Meter Event value is invalid")
    return {
        "event_name": event_name,
        "payload": {
            "stripe_customer_id": customer_id,
            "value": value,
        },
        "identifier": identifier,
        "timestamp": timestamp,
    }


def build_billing_provider(settings: object) -> BillingProvider:
    provider_name = str(getattr(settings, "billing_provider", "null") or "null").lower()
    if provider_name == "null":
        return NullBillingProvider()
    if provider_name != "stripe":
        raise StripeBillingConfigurationError(
            f"unsupported NC_BILLING_PROVIDER {provider_name!r}"
        )
    reconciliation_enabled = bool(
        getattr(settings, "billing_reconciliation_enabled", False)
    )
    return StripeBillingProvider(
        secret_key=str(getattr(settings, "stripe_secret_key", "")),
        webhook_secret=str(getattr(settings, "stripe_webhook_secret", "")),
        price_by_plan={
            "professional_live": str(
                getattr(settings, "stripe_professional_price_id", "")
            ),
            "enterprise_live": str(
                getattr(settings, "stripe_enterprise_price_id", "")
            ),
        },
        livemode=bool(getattr(settings, "stripe_livemode", False)),
        usage_price_id=(
            str(getattr(settings, "stripe_usage_price_id", ""))
            if reconciliation_enabled
            else None
        ),
        success_url=str(getattr(settings, "stripe_checkout_success_url", "")),
        cancel_url=str(getattr(settings, "stripe_checkout_cancel_url", "")),
        portal_return_url=str(getattr(settings, "stripe_portal_return_url", "")),
    )
