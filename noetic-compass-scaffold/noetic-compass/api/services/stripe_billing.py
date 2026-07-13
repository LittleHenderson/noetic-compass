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
from typing import Any, Mapping, Protocol


class StripeBillingConfigurationError(RuntimeError):
    pass


class StripeBillingProviderError(RuntimeError):
    pass


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


class NullBillingProvider:
    """Honest default: no checkout, portal, webhook, or money movement."""

    async def create_checkout_session(self, **_: object) -> CheckoutSessionResult:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def create_portal_session(self, **_: object) -> PortalSessionResult:
        raise StripeBillingProviderError("Stripe billing is not configured")

    def construct_webhook_event(self, **_: object) -> Mapping[str, Any]:
        raise StripeBillingProviderError("Stripe billing is not configured")

    async def retrieve_subscription(self, **_: object) -> SubscriptionSnapshot:
        raise StripeBillingProviderError("Stripe billing is not configured")


class StripeBillingProvider:
    def __init__(
        self,
        *,
        secret_key: str,
        webhook_secret: str,
        price_by_plan: Mapping[str, str],
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
        for name, url in (
            ("NC_STRIPE_CHECKOUT_SUCCESS_URL", success_url),
            ("NC_STRIPE_CHECKOUT_CANCEL_URL", cancel_url),
            ("NC_STRIPE_PORTAL_RETURN_URL", portal_return_url),
        ):
            if not url.startswith("https://"):
                raise StripeBillingConfigurationError(f"{name} must use https://")
        try:
            from stripe import StripeClient
        except ImportError as exc:  # pragma: no cover - exercised through builder tests
            raise StripeBillingConfigurationError(
                "NC_BILLING_PROVIDER=stripe requires stripe-python"
            ) from exc

        self._client = StripeClient(secret_key, max_network_retries=2)
        self._webhook_secret = webhook_secret
        self._price_by_plan = dict(price_by_plan)
        self._success_url = success_url
        self._cancel_url = cancel_url
        self._portal_return_url = portal_return_url

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
        params: dict[str, object] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
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
            plain = event.to_dict_recursive()
        except Exception as exc:
            raise StripeBillingProviderError(
                "Stripe webhook signature verification failed"
            ) from exc
        if not isinstance(plain, Mapping):
            raise StripeBillingProviderError("Stripe webhook event was malformed")
        return plain

    async def retrieve_subscription(
        self, *, external_subscription_id: str
    ) -> SubscriptionSnapshot:
        try:
            subscription = await self._client.v1.subscriptions.retrieve_async(
                external_subscription_id
            )
            plain = subscription.to_dict_recursive()
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


def build_billing_provider(settings: object) -> BillingProvider:
    provider_name = str(getattr(settings, "billing_provider", "null") or "null").lower()
    if provider_name == "null":
        return NullBillingProvider()
    if provider_name != "stripe":
        raise StripeBillingConfigurationError(
            f"unsupported NC_BILLING_PROVIDER {provider_name!r}"
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
        success_url=str(getattr(settings, "stripe_checkout_success_url", "")),
        cancel_url=str(getattr(settings, "stripe_checkout_cancel_url", "")),
        portal_return_url=str(getattr(settings, "stripe_portal_return_url", "")),
    )
