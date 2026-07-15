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

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Protocol

from api.services.billing_meter_dispatch import (
    MeterEventProviderContract,
    MeterEventProviderReceipt,
)


STRIPE_SDK_VERSION = "15.2.1"
STRIPE_API_VERSION = "2026-06-24.dahlia"
_STRIPE_PRICE_ID_RE = re.compile(r"^price_[A-Za-z0-9_]{1,249}$")
_STRIPE_CUSTOMER_ID_RE = re.compile(r"^cus_[A-Za-z0-9_]{1,251}$")
_METER_EVENT_NAME_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_METER_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_MAX_METER_EVENT_RESPONSE_BYTES = 1_000_000


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
    ) -> None:
        required = {
            "NC_STRIPE_SECRET_KEY": secret_key,
            "NC_STRIPE_WEBHOOK_SECRET": webhook_secret,
            "NC_STRIPE_PROFESSIONAL_PRICE_ID": price_by_plan.get(
                "professional_live", ""
            ),
            "NC_STRIPE_ENTERPRISE_PRICE_ID": price_by_plan.get(
                "enterprise_live", ""
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
        professional_price = str(price_by_plan.get("professional_live", ""))
        enterprise_price = str(price_by_plan.get("enterprise_live", ""))
        if professional_price == enterprise_price:
            raise StripeBillingConfigurationError(
                "Stripe professional and enterprise price ids must be distinct"
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
            if usage_price_id in {professional_price, enterprise_price}:
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
        self._price_by_plan = dict(price_by_plan)
        self._usage_price_id = usage_price_id
        self._success_url = success_url
        self._cancel_url = cancel_url
        self._portal_return_url = portal_return_url

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
        idempotency_key: str,
    ) -> CheckoutSessionResult:
        price_id = self._price_by_plan.get(plan_id)
        if not price_id:
            raise StripeBillingProviderError(f"no Stripe price configured for {plan_id}")
        metadata = {
            "cas_tenant_id": tenant_id,
            "cas_account_id": account_id,
            "cas_plan_id": plan_id,
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
