"""Account-scoped billing, subscription entitlement, and Stripe webhook routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hmac
from typing import Annotated, Literal, Mapping

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from api.config import settings
from api.dependencies.authz import require_role
from api.services.billing_entitlements import (
    BillingEntitlementError,
    BillingEntitlementStore,
    BillingEventConflict,
    PLAN_CATALOG,
    get_plan,
    process_stripe_event,
)
from api.services.stripe_billing import (
    BillingProvider,
    StripeBillingProviderError,
    SubscriptionSnapshot,
)


router = APIRouter(tags=["billing"])


class PlanResponse(BaseModel):
    plan_id: str
    display_name: str
    monthly_audit_limit: int
    live_audit: bool
    distributed_audit: bool
    reserved_gpu: bool
    paid: bool
    checkout_available: bool


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]


class EntitlementResponse(BaseModel):
    tenant_id: str
    plan: PlanResponse
    subscription_status: str
    subscription_source: str
    active: bool
    can_run_live_audit: bool
    reason: str
    current_period_end: str | None
    cancel_at_period_end: bool
    external_customer_present: bool


class CheckoutRequest(BaseModel):
    plan_id: Literal["professional_live"]
    request_id: str = Field(..., min_length=16, max_length=128)

    @field_validator("request_id")
    @classmethod
    def safe_request_id(cls, value: str) -> str:
        text = value.strip()
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        if not text or any(character not in allowed for character in text):
            raise ValueError("request_id must use URL-safe identifier characters")
        return text


class CheckoutResponse(BaseModel):
    checkout_session_id: str
    url: str


class PortalResponse(BaseModel):
    url: str


class ManualCompedRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    billing_account_id: str = Field(..., min_length=1, max_length=128)
    expires_at: datetime

    @field_validator("tenant_id", "billing_account_id")
    @classmethod
    def strip_identifier(cls, value: str) -> str:
        return value.strip()


class ManualCompedResponse(BaseModel):
    tenant_id: str
    plan_id: str
    status: str
    source: str
    expires_at: str


def _billing_store(request: Request) -> BillingEntitlementStore:
    store = getattr(request.app.state, "billing_entitlement_store", None)
    if not settings.billing_entitlements_enabled or store is None:
        raise HTTPException(
            status_code=503,
            detail="Billing entitlements are not enabled on this deployment.",
        )
    return store


def _billing_provider(request: Request) -> BillingProvider:
    provider = getattr(request.app.state, "billing_provider", None)
    if provider is None or settings.billing_provider.strip().lower() != "stripe":
        raise HTTPException(status_code=503, detail="Stripe billing is not configured.")
    return provider


def _tenant_id(request: Request) -> str:
    tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Account tenant identity is required.")
    return tenant_id


async def _bounded_raw_body(request: Request, *, maximum_bytes: int) -> bytes:
    """Read signature-sensitive bytes without buffering an unbounded public body."""
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > maximum_bytes:
                raise HTTPException(
                    status_code=413, detail="Stripe webhook payload is too large."
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length.") from exc
    chunks: list[bytes] = []
    observed = 0
    async for chunk in request.stream():
        observed += len(chunk)
        if observed > maximum_bytes:
            raise HTTPException(
                status_code=413, detail="Stripe webhook payload is too large."
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _refresh_subscription_event(
    provider: BillingProvider, event: dict[str, object]
) -> tuple[dict[str, object], SubscriptionSnapshot | None]:
    """Use Stripe's current resource state so webhook delivery order is irrelevant."""
    if str(event.get("type") or "") not in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
    }:
        return event, None
    data = event.get("data")
    obj = data.get("object") if isinstance(data, Mapping) else None
    subscription_id = str(obj.get("id") or "") if isinstance(obj, Mapping) else ""
    if not subscription_id:
        raise StripeBillingProviderError(
            "Stripe subscription event is missing its subscription id"
        )
    snapshot = await provider.retrieve_subscription(
        external_subscription_id=subscription_id
    )
    latest = snapshot.payload
    if str(latest.get("id") or "") != subscription_id:
        raise StripeBillingProviderError(
            "Stripe refreshed a different subscription than requested"
        )
    refreshed = dict(event)
    refreshed_data = dict(data) if isinstance(data, Mapping) else {}
    refreshed_data["object"] = dict(latest)
    refreshed["data"] = refreshed_data
    return refreshed, snapshot


def _subscription_id_for_event(event: Mapping[str, object]) -> str | None:
    if str(event.get("type") or "") not in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
    }:
        return None
    data = event.get("data")
    obj = data.get("object") if isinstance(data, Mapping) else None
    subscription_id = str(obj.get("id") or "") if isinstance(obj, Mapping) else ""
    if not subscription_id:
        raise StripeBillingProviderError(
            "Stripe subscription event is missing its subscription id"
        )
    return subscription_id


@router.get("/billing/plans", response_model=PlanListResponse)
async def list_billing_plans(request: Request, response: Response) -> PlanListResponse:
    _billing_store(request)
    response.headers["Cache-Control"] = "no-store"
    # beta_comped is platform-issued, not customer-purchasable. It is intentionally omitted.
    plans = [
        PlanResponse.model_validate(plan.to_dict())
        for plan in PLAN_CATALOG.values()
        if plan.plan_id != "beta_comped"
    ]
    return PlanListResponse(plans=plans)


@router.get("/billing/entitlement", response_model=EntitlementResponse)
async def get_billing_entitlement(
    request: Request, response: Response
) -> EntitlementResponse:
    response.headers["Cache-Control"] = "no-store"
    decision = _billing_store(request).resolve_entitlement(_tenant_id(request))
    return EntitlementResponse.model_validate(decision.to_dict())


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_billing_checkout(
    body: CheckoutRequest,
    request: Request,
    response: Response,
    _role: str = Depends(require_role("owner", "admin")),
) -> CheckoutResponse:
    response.headers["Cache-Control"] = "no-store"
    store = _billing_store(request)
    provider = _billing_provider(request)
    tenant_id = _tenant_id(request)
    account_id = str(getattr(request.state, "account_id", "") or "")
    account_store = getattr(request.app.state, "account_store", None)
    account = account_store.get_account_by_id(account_id) if account_store else None
    if account is None or account.tenant_id != tenant_id:
        raise HTTPException(status_code=401, detail="Billing account identity is unavailable.")
    plan = get_plan(body.plan_id)
    if not plan.paid or not plan.checkout_available:
        raise HTTPException(status_code=400, detail="Plan is not available through Checkout.")
    current = store.get_subscription(tenant_id)
    if (
        current is not None
        and current.source == "stripe_verified"
        and current.status not in {"canceled", "incomplete_expired"}
    ):
        raise HTTPException(
            status_code=409,
            detail="A Stripe subscription already exists; use the billing portal.",
        )
    try:
        intent, created = store.begin_checkout_intent(
            tenant_id=tenant_id,
            billing_account_id=account_id,
            plan_id=plan.plan_id,
            request_id=body.request_id,
        )
        if not created and intent.get("state") == "completed":
            return CheckoutResponse(
                checkout_session_id=str(intent["checkout_session_id"]),
                url=str(intent["url"]),
            )
        result = await provider.create_checkout_session(
            tenant_id=tenant_id,
            account_id=account_id,
            email=account.email_or_username,
            plan_id=plan.plan_id,
            external_customer_id=(current.external_customer_id if current else None),
            idempotency_key=f"cas-checkout:{tenant_id}:{plan.plan_id}:{body.request_id}",
        )
        store.finish_checkout_intent(
            tenant_id=tenant_id,
            request_id=body.request_id,
            checkout_session_id=result.session_id,
            url=result.url,
        )
    except BillingEventConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BillingEntitlementError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StripeBillingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CheckoutResponse(
        checkout_session_id=result.session_id,
        url=result.url,
    )


@router.post("/billing/portal", response_model=PortalResponse)
async def create_billing_portal(
    request: Request,
    response: Response,
    _role: str = Depends(require_role("owner", "admin")),
) -> PortalResponse:
    response.headers["Cache-Control"] = "no-store"
    subscription = _billing_store(request).get_subscription(_tenant_id(request))
    if subscription is None or not subscription.external_customer_id:
        raise HTTPException(status_code=409, detail="No Stripe customer is linked to this tenant.")
    try:
        result = await _billing_provider(request).create_portal_session(
            external_customer_id=subscription.external_customer_id
        )
    except StripeBillingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PortalResponse(url=result.url)


@router.post("/billing/webhook/stripe")
async def stripe_billing_webhook(
    request: Request,
    response: Response,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Stripe-Signature header is required.")
    raw_payload = await _bounded_raw_body(request, maximum_bytes=2_000_000)
    store = _billing_store(request)
    provider = _billing_provider(request)
    try:
        event = provider.construct_webhook_event(
            payload=raw_payload, signature=stripe_signature
        )
    except StripeBillingProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    plain_event = dict(event)
    event_id = str(plain_event.get("id") or "").strip()
    event_type = str(plain_event.get("type") or "").strip()
    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Stripe event identity is missing.")
    try:
        receipt, created = store.begin_webhook_event(
            event_id=event_id,
            event_type=event_type,
            raw_payload=raw_payload,
        )
    except BillingEventConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not created and receipt.payload.get("state") == "applied":
        return {"event_id": event_id, "applied": False, "duplicate": True}

    lease = None
    try:
        subscription_id = _subscription_id_for_event(plain_event)
        lease = (
            store.acquire_subscription_refresh_lock(
                external_subscription_id=subscription_id,
                event_id=event_id,
            )
            if subscription_id is not None
            else None
        )
        plain_event, snapshot = await _refresh_subscription_event(
            provider, plain_event
        )
        if subscription_id is not None and snapshot is not None:
            store.record_webhook_refresh(
                event_id=event_id,
                external_subscription_id=subscription_id,
                refreshed_object=snapshot.payload,
                provider_request_id=snapshot.provider_request_id,
            )
        return process_stripe_event(
            store,
            event=plain_event,
            raw_payload=raw_payload,
            price_to_plan={
                price_id: plan_id
                for price_id, plan_id in (
                    (
                        settings.stripe_professional_price_id,
                        "professional_live",
                    ),
                    (
                        settings.stripe_enterprise_price_id,
                        "enterprise_live",
                    ),
                )
                if price_id
            },
            resource_refreshed=lease is not None,
            refresh_lock_token=lease.token if lease is not None else None,
        )
    except StripeBillingProviderError as exc:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail=str(exc),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except BillingEventConflict as exc:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail=str(exc),
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BillingEntitlementError as exc:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail=str(exc),
        )
        # Non-2xx intentionally asks Stripe to retry unresolved or temporarily contradictory
        # subscription events after operator/configuration repair.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if lease is not None:
            store.release_subscription_refresh_lock(lease)


@router.post(
    "/platform/billing/manual-comped-subscription",
    response_model=ManualCompedResponse,
)
async def grant_manual_comped_subscription(
    body: ManualCompedRequest,
    request: Request,
    response: Response,
    billing_admin_secret: Annotated[
        str | None, Header(alias="X-Billing-Admin-Secret")
    ] = None,
) -> ManualCompedResponse:
    """Platform-only expiring beta grant; never represents a payment."""
    response.headers["Cache-Control"] = "no-store"
    configured = settings.billing_admin_secret
    supplied = billing_admin_secret or ""
    if not configured:
        raise HTTPException(status_code=503, detail="Manual billing grants are unavailable.")
    if not hmac.compare_digest(
        configured.encode("utf-8"), supplied.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Billing admin credentials are invalid.")
    if body.expires_at.tzinfo is None:
        expires_at = body.expires_at.replace(tzinfo=UTC)
    else:
        expires_at = body.expires_at.astimezone(UTC)
    now = datetime.now(UTC)
    if expires_at <= now or expires_at > now + timedelta(days=366):
        raise HTTPException(
            status_code=400,
            detail="Comped beta expiry must be in the future and no more than 366 days away.",
        )
    account_store = getattr(request.app.state, "account_store", None)
    if account_store is None or not account_store.tenant_has_account(body.tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found.")
    account = account_store.get_account_by_id(body.billing_account_id)
    if account is None or account.tenant_id != body.tenant_id:
        raise HTTPException(status_code=404, detail="Billing account not found.")
    try:
        subscription = _billing_store(request).grant_manual_comped(
            tenant_id=body.tenant_id,
            billing_account_id=body.billing_account_id,
            expires_at=expires_at.isoformat(),
        )
    except BillingEntitlementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ManualCompedResponse(
        tenant_id=subscription.tenant_id,
        plan_id=subscription.plan_id,
        status=subscription.status,
        source=subscription.source,
        expires_at=subscription.current_period_end or "",
    )
