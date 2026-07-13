"""Durable tenant subscription and entitlement records for CAS Harness.

This module is the account-facing complement to ``production/billing.py``.  The
older module deliberately models honest metering/invoice seams and remains
import-isolated; this module owns the durable *right to use a product feature*.

The security boundary is intentionally simple:

* every subscription is stored under its tenant in the shared ``StateStore``;
* the browser never chooses an effective plan or quota;
* a Stripe plan is accepted only from a signature-verified webhook event whose
  price id maps to a server-configured plan;
* comped beta access is a distinct, expiring ``manual_comped`` source and can
  never be represented as paid;
* missing, stale, canceled, past-due, incomplete, or unknown state resolves to
  the free/reference plan and cannot start a live audit;
* webhook receipts are hash-bound, durable, retryable, and ordered so an old
  event cannot roll a tenant back over a newer provider event.

The feature is dark unless ``NC_BILLING_ENTITLEMENTS_ENABLED=true``.  A
``StateStore`` implementation is only as durable as its backend; hosted account
mode already requires PostgreSQL, while acknowledged SQLite remains a
single-host development posture.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import Any, Literal, Mapping

from api.services.production.state_substrate.interface import (
    Lease,
    LeaseHeld,
    LedgerRecord,
    StateStore,
    VersionConflict,
)


BILLING_ENTITLEMENT_SCHEMA_VERSION = "cas_harness_billing_entitlement.v1"
SUBSCRIPTION_KIND = "billing_subscription"
SUBSCRIPTION_RECORD_ID = "current"
CUSTOMER_INDEX_KIND = "billing_customer_index"
SUBSCRIPTION_INDEX_KIND = "billing_subscription_index"
WEBHOOK_EVENT_KIND = "billing_webhook_event"
CHECKOUT_INTENT_KIND = "billing_checkout_intent"
CHECKOUT_INTENT_RECORD_ID = "current"
BILLING_PLATFORM_TENANT = "_cas_billing_platform"
MAX_WRITE_RETRIES = 12
CHECKOUT_INTENT_TTL = timedelta(hours=24)

SubscriptionSource = Literal["none", "manual_comped", "stripe_verified"]
SubscriptionStatus = Literal[
    "none",
    "trialing",
    "active",
    "past_due",
    "incomplete",
    "incomplete_expired",
    "unpaid",
    "paused",
    "canceled",
]


class BillingEntitlementError(RuntimeError):
    """A billing transition is malformed, contradictory, or cannot be trusted."""


class BillingEventConflict(BillingEntitlementError):
    """A provider identity/event was already bound to contradictory data."""


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    plan_id: str
    display_name: str
    monthly_audit_limit: int
    live_audit: bool
    distributed_audit: bool
    reserved_gpu: bool
    paid: bool
    checkout_available: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "display_name": self.display_name,
            "monthly_audit_limit": self.monthly_audit_limit,
            "live_audit": self.live_audit,
            "distributed_audit": self.distributed_audit,
            "reserved_gpu": self.reserved_gpu,
            "paid": self.paid,
            "checkout_available": self.checkout_available,
        }


PLAN_CATALOG: dict[str, PlanDefinition] = {
    "free_reference": PlanDefinition(
        plan_id="free_reference",
        display_name="Free reference",
        monthly_audit_limit=0,
        live_audit=False,
        distributed_audit=False,
        reserved_gpu=False,
        paid=False,
        checkout_available=False,
    ),
    "beta_comped": PlanDefinition(
        plan_id="beta_comped",
        display_name="Comped beta",
        monthly_audit_limit=25,
        live_audit=True,
        distributed_audit=False,
        reserved_gpu=False,
        paid=False,
        checkout_available=False,
    ),
    "professional_live": PlanDefinition(
        plan_id="professional_live",
        display_name="Professional live",
        monthly_audit_limit=100,
        live_audit=True,
        distributed_audit=False,
        reserved_gpu=False,
        paid=True,
        checkout_available=True,
    ),
    "enterprise_live": PlanDefinition(
        plan_id="enterprise_live",
        display_name="Enterprise live audit",
        monthly_audit_limit=1000,
        live_audit=True,
        # Tenant-bound fleet service credentials are a separate release gate.
        # The plan never claims that unimplemented capability is available.
        distributed_audit=False,
        reserved_gpu=False,
        paid=True,
        # Contact-sales only until reserved compute and fleet deployment proof exist.
        checkout_available=False,
    ),
}


def get_plan(plan_id: str) -> PlanDefinition:
    try:
        return PLAN_CATALOG[plan_id]
    except KeyError as exc:
        raise BillingEntitlementError(f"unknown billing plan {plan_id!r}") from exc


@dataclass(frozen=True, slots=True)
class SubscriptionRecord:
    tenant_id: str
    plan_id: str
    status: SubscriptionStatus
    source: SubscriptionSource
    billing_account_id: str | None = None
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False
    provider_event_id: str | None = None
    provider_event_created: int = 0
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise BillingEntitlementError("subscription tenant_id is required")
        get_plan(self.plan_id)
        if self.source == "none":
            if self.plan_id != "free_reference" or self.status != "none":
                raise BillingEntitlementError(
                    "source=none may represent only the free reference plan"
                )
            if self.external_customer_id or self.external_subscription_id:
                raise BillingEntitlementError(
                    "source=none cannot claim provider identities"
                )
        elif self.source == "manual_comped":
            if self.plan_id != "beta_comped" or self.status != "active":
                raise BillingEntitlementError(
                    "manual comped subscriptions may grant only active beta_comped"
                )
            if not self.billing_account_id or not self.current_period_end:
                raise BillingEntitlementError(
                    "manual comped subscriptions require account and expiry"
                )
            if self.external_customer_id or self.external_subscription_id:
                raise BillingEntitlementError(
                    "manual comped subscriptions cannot claim provider identities"
                )
        elif self.source == "stripe_verified":
            if not get_plan(self.plan_id).paid:
                raise BillingEntitlementError(
                    "Stripe subscriptions may map only to paid plans"
                )
            if not (
                self.external_customer_id
                and self.external_subscription_id
                and self.provider_event_id
            ):
                raise BillingEntitlementError(
                    "Stripe subscriptions require customer, subscription, and event ids"
                )
            if self.status in {"active", "trialing"} and not self.current_period_end:
                raise BillingEntitlementError(
                    "active Stripe subscriptions require a current period end"
                )
            if self.provider_event_created < 0:
                raise BillingEntitlementError(
                    "Stripe provider event timestamp cannot be negative"
                )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
            "tenant_id": self.tenant_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "source": self.source,
            "billing_account_id": self.billing_account_id,
            "external_customer_id": self.external_customer_id,
            "external_subscription_id": self.external_subscription_id,
            "current_period_start": self.current_period_start,
            "current_period_end": self.current_period_end,
            "cancel_at_period_end": self.cancel_at_period_end,
            "provider_event_id": self.provider_event_id,
            "provider_event_created": self.provider_event_created,
            "updated_at": self.updated_at or _now_iso(),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "SubscriptionRecord":
        if payload.get("schema_version") != BILLING_ENTITLEMENT_SCHEMA_VERSION:
            raise BillingEntitlementError("subscription schema version is invalid")
        raw_status = str(payload.get("status") or "")
        if raw_status not in {
            "none",
            "trialing",
            "active",
            "past_due",
            "incomplete",
            "incomplete_expired",
            "unpaid",
            "paused",
            "canceled",
        }:
            raise BillingEntitlementError("stored subscription status is invalid")
        raw_source = str(payload.get("source") or "")
        if raw_source not in {"none", "manual_comped", "stripe_verified"}:
            raise BillingEntitlementError("stored subscription source is invalid")
        return cls(
            tenant_id=_required_text(payload.get("tenant_id"), "subscription.tenant_id"),
            plan_id=_required_text(payload.get("plan_id"), "subscription.plan_id"),
            status=raw_status,  # type: ignore[arg-type]
            source=raw_source,  # type: ignore[arg-type]
            billing_account_id=_optional_text(payload.get("billing_account_id")),
            external_customer_id=_optional_text(payload.get("external_customer_id")),
            external_subscription_id=_optional_text(
                payload.get("external_subscription_id")
            ),
            current_period_start=_optional_text(payload.get("current_period_start")),
            current_period_end=_optional_text(payload.get("current_period_end")),
            cancel_at_period_end=bool(payload.get("cancel_at_period_end", False)),
            provider_event_id=_optional_text(payload.get("provider_event_id")),
            provider_event_created=_nonnegative_int(
                payload.get("provider_event_created", 0),
                "subscription.provider_event_created",
            ),
            updated_at=str(payload.get("updated_at") or _now_iso()),
        )


@dataclass(frozen=True, slots=True)
class EntitlementDecision:
    tenant_id: str
    plan: PlanDefinition
    subscription_status: SubscriptionStatus
    subscription_source: SubscriptionSource
    active: bool
    reason: str
    current_period_end: str | None = None
    cancel_at_period_end: bool = False
    external_customer_present: bool = False

    @property
    def can_run_live_audit(self) -> bool:
        return self.active and self.plan.live_audit

    def to_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan.to_dict(),
            "subscription_status": self.subscription_status,
            "subscription_source": self.subscription_source,
            "active": self.active,
            "can_run_live_audit": self.can_run_live_audit,
            "reason": self.reason,
            "current_period_end": self.current_period_end,
            "cancel_at_period_end": self.cancel_at_period_end,
            "external_customer_present": self.external_customer_present,
        }


class BillingEntitlementStore:
    """Versioned billing state over the app's shared tenant ``StateStore``."""

    def __init__(self, store: StateStore) -> None:
        self._store = store

    def get_subscription(self, tenant_id: str) -> SubscriptionRecord | None:
        record = self._store.get(
            tenant_id, SUBSCRIPTION_KIND, SUBSCRIPTION_RECORD_ID
        )
        if record is None:
            return None
        subscription = SubscriptionRecord.from_payload(record.payload)
        if subscription.tenant_id != tenant_id:
            raise BillingEventConflict("subscription payload tenant does not match its key")
        return subscription

    def resolve_entitlement(
        self, tenant_id: str, *, now: datetime | None = None
    ) -> EntitlementDecision:
        subscription = self.get_subscription(tenant_id)
        free = PLAN_CATALOG["free_reference"]
        if subscription is None:
            return EntitlementDecision(
                tenant_id=tenant_id,
                plan=free,
                subscription_status="none",
                subscription_source="none",
                active=True,
                reason="no active subscription; reference/demo access only",
            )

        clock = now or datetime.now(UTC)
        active_status = subscription.status in {"active", "trialing"}
        # Every grant is time-bounded. Missing or malformed provider periods
        # must never turn into perpetual access.
        period_live = False
        if subscription.current_period_end:
            try:
                period_live = _parse_datetime(subscription.current_period_end) > clock
            except ValueError:
                period_live = False
        active = active_status and period_live
        if not active:
            reason = (
                "subscription period expired"
                if active_status and not period_live
                else f"subscription status {subscription.status!r} does not grant live access"
            )
            return EntitlementDecision(
                tenant_id=tenant_id,
                plan=free,
                subscription_status=subscription.status,
                subscription_source=subscription.source,
                active=False,
                reason=reason,
                current_period_end=subscription.current_period_end,
                cancel_at_period_end=subscription.cancel_at_period_end,
                external_customer_present=bool(subscription.external_customer_id),
            )

        return EntitlementDecision(
            tenant_id=tenant_id,
            plan=get_plan(subscription.plan_id),
            subscription_status=subscription.status,
            subscription_source=subscription.source,
            active=True,
            reason="active server-derived subscription entitlement",
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            external_customer_present=bool(subscription.external_customer_id),
        )

    def grant_manual_comped(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
        expires_at: str,
        source: str = "billing.manual_comped",
    ) -> SubscriptionRecord:
        expiry = _parse_datetime(expires_at)
        if expiry <= datetime.now(UTC):
            raise BillingEntitlementError("manual comped expiry must be in the future")
        subscription = SubscriptionRecord(
            tenant_id=tenant_id,
            plan_id="beta_comped",
            status="active",
            source="manual_comped",
            billing_account_id=billing_account_id,
            current_period_start=_now_iso(),
            current_period_end=expiry.isoformat(),
            updated_at=_now_iso(),
        )
        return self._put_subscription(
            subscription,
            source=source,
            reject_stripe_managed=True,
        )

    def begin_checkout_intent(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
        plan_id: str,
        request_id: str,
        now: datetime | None = None,
    ) -> tuple[dict[str, object], bool]:
        """Reserve the tenant's one live Checkout intent.

        A stable request id may retry the same Stripe idempotency key. A different
        request id is refused for 24 hours so browser retries or abuse cannot mint
        an unbounded set of simultaneously payable Checkout sessions.
        """
        plan = get_plan(plan_id)
        if not plan.paid or not plan.checkout_available:
            raise BillingEntitlementError("plan is not available through Checkout")
        clock = now or datetime.now(UTC)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                tenant_id, CHECKOUT_INTENT_KIND, CHECKOUT_INTENT_RECORD_ID
            )
            if existing is not None:
                current = dict(existing.payload)
                if str(current.get("tenant_id")) != tenant_id:
                    raise BillingEventConflict("Checkout intent tenant mismatch")
                try:
                    created_at = _parse_datetime(str(current["created_at"]))
                except (KeyError, ValueError) as exc:
                    raise BillingEntitlementError(
                        "Checkout intent timestamp is invalid"
                    ) from exc
                same_request = (
                    str(current.get("request_id")) == request_id
                    and str(current.get("plan_id")) == plan.plan_id
                    and str(current.get("billing_account_id"))
                    == billing_account_id
                )
                if clock - created_at < CHECKOUT_INTENT_TTL:
                    if same_request:
                        return current, False
                    raise BillingEventConflict(
                        "a recent Checkout intent already exists for this tenant"
                    )

            payload: dict[str, object] = {
                "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
                "tenant_id": tenant_id,
                "billing_account_id": billing_account_id,
                "plan_id": plan.plan_id,
                "request_id": request_id,
                "state": "creating",
                "created_at": clock.isoformat(),
                "updated_at": clock.isoformat(),
            }
            record = (
                existing.with_payload(payload)
                if existing is not None
                else LedgerRecord.new(
                    tenant_id=tenant_id,
                    kind=CHECKOUT_INTENT_KIND,
                    record_id=CHECKOUT_INTENT_RECORD_ID,
                    payload=payload,
                    source="billing.checkout_intent",
                    trace_id=request_id,
                )
            )
            try:
                self._store.put(
                    record,
                    expected_version=existing.version if existing is not None else 0,
                )
                return payload, True
            except VersionConflict:
                continue
        raise BillingEntitlementError("Checkout intent contention exceeded")

    def finish_checkout_intent(
        self,
        *,
        tenant_id: str,
        request_id: str,
        checkout_session_id: str,
        url: str,
    ) -> dict[str, object]:
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                tenant_id, CHECKOUT_INTENT_KIND, CHECKOUT_INTENT_RECORD_ID
            )
            if existing is None or str(existing.payload.get("request_id")) != request_id:
                raise BillingEventConflict("Checkout intent changed before completion")
            payload = dict(existing.payload)
            payload.update(
                {
                    "state": "completed",
                    "checkout_session_id": checkout_session_id,
                    "url": url,
                    "updated_at": _now_iso(),
                }
            )
            try:
                self._store.put(
                    existing.with_payload(payload),
                    expected_version=existing.version,
                )
                return payload
            except VersionConflict:
                continue
        raise BillingEntitlementError("Checkout intent completion contention exceeded")

    def acquire_subscription_refresh_lock(
        self, *, external_subscription_id: str, event_id: str
    ) -> Lease:
        try:
            return self._store.acquire_lease(
                BILLING_PLATFORM_TENANT,
                _subscription_refresh_resource_id(external_subscription_id),
                holder=event_id,
                ttl_seconds=300,
            )
        except LeaseHeld as exc:
            raise BillingEntitlementError(
                "another subscription refresh is in progress"
            ) from exc

    def release_subscription_refresh_lock(self, lease: Lease) -> None:
        self._store.release_lease(lease.token)

    def apply_stripe_subscription(
        self,
        *,
        tenant_id: str,
        plan_id: str | None,
        status: str,
        external_customer_id: str,
        external_subscription_id: str,
        event_id: str,
        event_created: int,
        current_period_start: str | None,
        current_period_end: str | None,
        cancel_at_period_end: bool,
        resource_refreshed: bool = False,
        refresh_lock_token: str | None = None,
    ) -> tuple[SubscriptionRecord, bool]:
        """Apply one signature-verified provider event; return (record, changed)."""
        if not event_id.strip() or event_created < 0:
            raise BillingEntitlementError("provider event identity is invalid")
        if not external_customer_id or not external_subscription_id:
            raise BillingEntitlementError("provider customer/subscription ids are required")
        normalized_status = _subscription_status(status)
        if resource_refreshed and not refresh_lock_token:
            raise BillingEntitlementError(
                "latest-resource subscription updates require a refresh lock"
            )

        self.bind_customer(
            external_customer_id=external_customer_id, tenant_id=tenant_id
        )
        self.bind_subscription(
            external_subscription_id=external_subscription_id,
            external_customer_id=external_customer_id,
            tenant_id=tenant_id,
        )
        for _ in range(MAX_WRITE_RETRIES):
            if resource_refreshed:
                lease = self._store.get_lease(
                    BILLING_PLATFORM_TENANT,
                    _subscription_refresh_resource_id(external_subscription_id),
                )
                if lease is None or lease.token != refresh_lock_token:
                    raise BillingEntitlementError(
                        "subscription refresh lock expired before persistence"
                    )
            stored = self._store.get(
                tenant_id, SUBSCRIPTION_KIND, SUBSCRIPTION_RECORD_ID
            )
            existing = (
                SubscriptionRecord.from_payload(stored.payload)
                if stored is not None
                else None
            )
            effective_plan_id = plan_id
            if effective_plan_id is None:
                if normalized_status in {"active", "trialing"}:
                    raise BillingEntitlementError(
                        "active provider subscription price is not mapped to a plan"
                    )
                if existing is None or existing.source != "stripe_verified":
                    raise BillingEntitlementError(
                        "provider event has no mapped plan and no existing Stripe subscription"
                    )
                effective_plan_id = existing.plan_id
            plan = get_plan(effective_plan_id)
            if not plan.paid:
                raise BillingEntitlementError(
                    "provider event mapped to a non-paid plan"
                )

            if existing and existing.provider_event_id and not resource_refreshed:
                if event_created < existing.provider_event_created:
                    return existing, False
                if event_created == existing.provider_event_created:
                    if event_id == existing.provider_event_id:
                        return existing, False
                    raise BillingEventConflict(
                        "provider events share a timestamp with no trustworthy order"
                    )
            if (
                existing
                and existing.source == "stripe_verified"
                and existing.external_subscription_id
                and existing.external_subscription_id != external_subscription_id
                and existing.status not in {"canceled", "incomplete_expired"}
            ):
                raise BillingEventConflict(
                    "tenant already has a different live Stripe subscription"
                )

            subscription = SubscriptionRecord(
                tenant_id=tenant_id,
                plan_id=plan.plan_id,
                status=normalized_status,
                source="stripe_verified",
                billing_account_id=(
                    existing.billing_account_id if existing else None
                ),
                external_customer_id=external_customer_id,
                external_subscription_id=external_subscription_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                cancel_at_period_end=cancel_at_period_end,
                provider_event_id=event_id,
                provider_event_created=event_created,
                updated_at=_now_iso(),
            )
            record = (
                stored.with_payload(subscription.to_payload())
                if stored is not None
                else LedgerRecord.new(
                    tenant_id=tenant_id,
                    kind=SUBSCRIPTION_KIND,
                    record_id=SUBSCRIPTION_RECORD_ID,
                    payload=subscription.to_payload(),
                    source="billing.stripe_webhook",
                    trace_id=event_id,
                )
            )
            try:
                self._store.put(
                    record,
                    expected_version=stored.version if stored is not None else 0,
                )
                return subscription, True
            except VersionConflict:
                # Re-read and re-evaluate provider ordering and conflicts. A blind
                # retry here could let an older webhook overwrite a newer event.
                continue
        raise BillingEntitlementError("subscription update contention exceeded")

    def bind_customer(self, *, external_customer_id: str, tenant_id: str) -> None:
        record_id = _customer_index_id(external_customer_id)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, CUSTOMER_INDEX_KIND, record_id
            )
            if existing is not None:
                if (
                    str(existing.payload.get("external_customer_id"))
                    != external_customer_id
                    or str(existing.payload.get("tenant_id")) != tenant_id
                ):
                    raise BillingEventConflict(
                        "Stripe customer id is already bound to another tenant"
                    )
                return
            record = LedgerRecord.new(
                tenant_id=BILLING_PLATFORM_TENANT,
                kind=CUSTOMER_INDEX_KIND,
                record_id=record_id,
                payload={
                    "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
                    "external_customer_id": external_customer_id,
                    "tenant_id": tenant_id,
                },
                source="billing.customer_index",
                trace_id=record_id,
            )
            try:
                self._store.put(record, expected_version=0)
                return
            except VersionConflict:
                continue
        raise BillingEntitlementError("billing customer binding contention exceeded")

    def bind_subscription(
        self,
        *,
        external_subscription_id: str,
        external_customer_id: str,
        tenant_id: str,
    ) -> None:
        record_id = _subscription_index_id(external_subscription_id)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, SUBSCRIPTION_INDEX_KIND, record_id
            )
            if existing is not None:
                if (
                    str(existing.payload.get("external_subscription_id"))
                    != external_subscription_id
                    or str(existing.payload.get("external_customer_id"))
                    != external_customer_id
                    or str(existing.payload.get("tenant_id")) != tenant_id
                ):
                    raise BillingEventConflict(
                        "Stripe subscription id is already bound to another identity"
                    )
                return
            record = LedgerRecord.new(
                tenant_id=BILLING_PLATFORM_TENANT,
                kind=SUBSCRIPTION_INDEX_KIND,
                record_id=record_id,
                payload={
                    "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
                    "external_subscription_id": external_subscription_id,
                    "external_customer_id": external_customer_id,
                    "tenant_id": tenant_id,
                },
                source="billing.subscription_index",
                trace_id=record_id,
            )
            try:
                self._store.put(record, expected_version=0)
                return
            except VersionConflict:
                continue
        raise BillingEntitlementError("billing subscription binding contention exceeded")

    def tenant_for_customer(self, external_customer_id: str) -> str | None:
        record = self._store.get(
            BILLING_PLATFORM_TENANT,
            CUSTOMER_INDEX_KIND,
            _customer_index_id(external_customer_id),
        )
        if record is None:
            return None
        if str(record.payload.get("external_customer_id")) != external_customer_id:
            raise BillingEventConflict("billing customer index digest collision")
        return _optional_text(record.payload.get("tenant_id"))

    def begin_webhook_event(
        self, *, event_id: str, event_type: str, raw_payload: bytes
    ) -> tuple[LedgerRecord, bool]:
        digest = hashlib.sha256(raw_payload).hexdigest()
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
            )
            if existing is not None:
                if str(existing.payload.get("payload_sha256")) != digest:
                    raise BillingEventConflict(
                        "provider event id was replayed with different bytes"
                    )
                return existing, False
            record = LedgerRecord.new(
                tenant_id=BILLING_PLATFORM_TENANT,
                kind=WEBHOOK_EVENT_KIND,
                record_id=event_id,
                payload={
                    "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
                    "event_id": event_id,
                    "event_type": event_type,
                    "payload_sha256": digest,
                    "state": "received",
                    "received_at": _now_iso(),
                },
                source="billing.stripe_webhook",
                trace_id=event_id,
            )
            try:
                stored = self._store.put(record, expected_version=0)
                return stored, True
            except VersionConflict:
                continue
        raise BillingEntitlementError("webhook receipt contention exceeded")

    def finish_webhook_event(
        self,
        *,
        event_id: str,
        state: Literal["applied", "ignored", "unresolved"],
        tenant_id: str | None,
        detail: str,
    ) -> None:
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
            )
            if existing is None:
                raise BillingEntitlementError("webhook receipt disappeared")
            payload = dict(existing.payload)
            if payload.get("state") == "applied" and state != "applied":
                return
            payload.update(
                {
                    "state": state,
                    "tenant_id": (
                        tenant_id
                        if tenant_id is not None
                        else payload.get("tenant_id")
                    ),
                    "detail": detail,
                    "finished_at": _now_iso(),
                }
            )
            try:
                self._store.put(
                    existing.with_payload(payload), expected_version=existing.version
                )
                return
            except VersionConflict:
                continue
        raise BillingEntitlementError("webhook receipt update contention exceeded")

    def record_webhook_refresh(
        self,
        *,
        event_id: str,
        external_subscription_id: str,
        refreshed_object: Mapping[str, Any],
        provider_request_id: str | None,
    ) -> None:
        digest = hashlib.sha256(canonical_event_bytes(refreshed_object)).hexdigest()
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
            )
            if existing is None:
                raise BillingEntitlementError("webhook receipt disappeared")
            payload = dict(existing.payload)
            attempts = list(payload.get("provider_refreshes") or [])
            attempts.append(
                {
                    "external_subscription_id": external_subscription_id,
                    "refreshed_object_sha256": digest,
                    "provider_request_id": provider_request_id,
                    "retrieved_at": _now_iso(),
                }
            )
            payload["provider_refreshes"] = attempts[-20:]
            try:
                self._store.put(
                    existing.with_payload(payload),
                    expected_version=existing.version,
                )
                return
            except VersionConflict:
                continue
        raise BillingEntitlementError("webhook refresh receipt contention exceeded")

    def _put_subscription(
        self,
        subscription: SubscriptionRecord,
        *,
        source: str,
        reject_stripe_managed: bool = False,
    ) -> SubscriptionRecord:
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                subscription.tenant_id,
                SUBSCRIPTION_KIND,
                SUBSCRIPTION_RECORD_ID,
            )
            if existing is None:
                record = LedgerRecord.new(
                    tenant_id=subscription.tenant_id,
                    kind=SUBSCRIPTION_KIND,
                    record_id=SUBSCRIPTION_RECORD_ID,
                    payload=subscription.to_payload(),
                    source=source,
                    trace_id=subscription.provider_event_id,
                )
                expected_version = 0
            else:
                current = SubscriptionRecord.from_payload(existing.payload)
                if (
                    reject_stripe_managed
                    and current.source == "stripe_verified"
                ):
                    raise BillingEventConflict(
                        "a Stripe-managed subscription cannot be replaced by a comped grant"
                    )
                record = existing.with_payload(subscription.to_payload())
                expected_version = existing.version
            try:
                self._store.put(record, expected_version=expected_version)
                return subscription
            except VersionConflict:
                continue
        raise BillingEntitlementError("subscription update contention exceeded")


def process_stripe_event(
    store: BillingEntitlementStore,
    *,
    event: Mapping[str, Any],
    raw_payload: bytes,
    price_to_plan: Mapping[str, str],
    resource_refreshed: bool = False,
    refresh_lock_token: str | None = None,
) -> dict[str, object]:
    """Durably apply a signature-verified Stripe event.

    The caller MUST verify the signature before constructing ``event``.  This
    function intentionally accepts plain mappings so tests do not need the SDK.
    """
    event_id = _required_text(event.get("id"), "event.id")
    event_type = _required_text(event.get("type"), "event.type")
    try:
        event_created = int(event.get("created", 0))
    except (TypeError, ValueError) as exc:
        raise BillingEntitlementError("provider event created timestamp is invalid") from exc
    receipt, created = store.begin_webhook_event(
        event_id=event_id, event_type=event_type, raw_payload=raw_payload
    )
    if not created and receipt.payload.get("state") == "applied":
        return {"event_id": event_id, "applied": False, "duplicate": True}

    data = event.get("data")
    obj = data.get("object") if isinstance(data, Mapping) else None
    if not isinstance(obj, Mapping):
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail="event data.object is missing",
        )
        raise BillingEntitlementError("provider event data.object is missing")

    if event_type == "checkout.session.completed":
        tenant_id = _metadata_tenant(obj)
        customer_id = _optional_text(obj.get("customer"))
        if not tenant_id or not customer_id:
            message = (
                "checkout metadata tenant_id is missing"
                if not tenant_id
                else "checkout.customer is required"
            )
            store.finish_webhook_event(
                event_id=event_id,
                state="unresolved",
                tenant_id=tenant_id,
                detail=message,
            )
            raise BillingEntitlementError(message)
        try:
            store.bind_customer(
                external_customer_id=customer_id, tenant_id=tenant_id
            )
        except BillingEntitlementError as exc:
            store.finish_webhook_event(
                event_id=event_id,
                state="unresolved",
                tenant_id=tenant_id,
                detail=str(exc),
            )
            raise
        store.finish_webhook_event(
            event_id=event_id,
            state="applied",
            tenant_id=tenant_id,
            detail="checkout customer binding recorded; entitlement awaits subscription event",
        )
        return {"event_id": event_id, "applied": True, "tenant_id": tenant_id}

    supported = {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
    }
    if event_type not in supported:
        store.finish_webhook_event(
            event_id=event_id,
            state="ignored",
            tenant_id=None,
            detail="event type does not affect CAS Harness entitlements",
        )
        return {"event_id": event_id, "applied": False, "ignored": True}

    customer_id = _optional_text(obj.get("customer"))
    subscription_id = _optional_text(obj.get("id"))
    if not customer_id or not subscription_id:
        message = (
            "subscription.customer is required"
            if not customer_id
            else "subscription.id is required"
        )
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail=message,
        )
        raise BillingEntitlementError(message)
    metadata_tenant = _metadata_tenant(obj)
    indexed_tenant = store.tenant_for_customer(customer_id)
    if metadata_tenant and indexed_tenant and metadata_tenant != indexed_tenant:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail="subscription metadata contradicts the customer tenant binding",
        )
        raise BillingEventConflict(
            "subscription metadata contradicts the customer tenant binding"
        )
    tenant_id = metadata_tenant or indexed_tenant
    if not tenant_id:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail="subscription could not be mapped to a tenant",
        )
        raise BillingEntitlementError(
            "subscription metadata/customer index could not resolve tenant"
        )

    status = "canceled" if event_type == "customer.subscription.deleted" else str(
        obj.get("status") or "none"
    )
    if not resource_refreshed or not refresh_lock_token:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=tenant_id,
            detail="subscription event was not refreshed under the provider lock",
        )
        raise BillingEntitlementError(
            "subscription events require a locked refresh of current provider state"
        )
    price_ids = _subscription_price_ids(obj)
    mapped_plan_items = [
        (price_id, price_to_plan[price_id])
        for price_id in price_ids
        if price_id in price_to_plan
    ]
    selected_price_id = mapped_plan_items[0][0] if len(mapped_plan_items) == 1 else None
    plan_id = mapped_plan_items[0][1] if len(mapped_plan_items) == 1 else None
    try:
        current_start, current_end = _subscription_period(
            obj, selected_price_id=selected_price_id
        )
        if status in {"active", "trialing"} and plan_id is None:
            try:
                store.apply_stripe_subscription(
                    tenant_id=tenant_id,
                    plan_id=None,
                    status="none",
                    external_customer_id=customer_id,
                    external_subscription_id=subscription_id,
                    event_id=event_id,
                    event_created=event_created,
                    current_period_start=current_start,
                    current_period_end=current_end,
                    cancel_at_period_end=bool(
                        obj.get("cancel_at_period_end", False)
                    ),
                    resource_refreshed=True,
                    refresh_lock_token=refresh_lock_token,
                )
            except BillingEntitlementError:
                # A new unknown-price subscription has no previous paid grant to
                # revoke. An existing one is rewritten to status=none above.
                pass
            reason = (
                "active provider subscription has multiple CAS plan prices"
                if len(mapped_plan_items) > 1
                else "active provider subscription price is not mapped to a plan"
            )
            raise BillingEntitlementError(reason)
        subscription, changed = store.apply_stripe_subscription(
            tenant_id=tenant_id,
            plan_id=plan_id,
            status=status,
            external_customer_id=customer_id,
            external_subscription_id=subscription_id,
            event_id=event_id,
            event_created=event_created,
            current_period_start=current_start,
            current_period_end=current_end,
            cancel_at_period_end=bool(obj.get("cancel_at_period_end", False)),
            resource_refreshed=True,
            refresh_lock_token=refresh_lock_token,
        )
    except (BillingEntitlementError, ValueError) as exc:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=tenant_id,
            detail=str(exc),
        )
        if isinstance(exc, BillingEntitlementError):
            raise
        raise BillingEntitlementError("subscription period is invalid") from exc
    store.finish_webhook_event(
        event_id=event_id,
        state="applied",
        tenant_id=tenant_id,
        detail="subscription updated" if changed else "stale/duplicate event ignored",
    )
    return {
        "event_id": event_id,
        "applied": changed,
        "tenant_id": tenant_id,
        "plan_id": subscription.plan_id,
        "status": subscription.status,
    }


def _subscription_status(value: object) -> SubscriptionStatus:
    normalized = str(value or "none").strip().lower()
    if normalized == "deleted":
        normalized = "canceled"
    allowed = {
        "none",
        "trialing",
        "active",
        "past_due",
        "incomplete",
        "incomplete_expired",
        "unpaid",
        "paused",
        "canceled",
    }
    return normalized if normalized in allowed else "none"  # type: ignore[return-value]


def _metadata_tenant(obj: Mapping[str, object]) -> str | None:
    metadata = obj.get("metadata")
    if isinstance(metadata, Mapping):
        return _optional_text(metadata.get("cas_tenant_id") or metadata.get("tenant_id"))
    return None


def _subscription_price_ids(obj: Mapping[str, object]) -> tuple[str, ...]:
    items = obj.get("items")
    rows = items.get("data") if isinstance(items, Mapping) else None
    if not isinstance(rows, list):
        return ()
    price_ids: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        price_id = _subscription_item_price_id(row)
        if price_id:
            price_ids.append(price_id)
    return tuple(price_ids)


def _subscription_item_price_id(row: Mapping[str, object]) -> str | None:
    price = row.get("price")
    return (
        _optional_text(price.get("id"))
        if isinstance(price, Mapping)
        else _optional_text(price)
    )


def _subscription_period(
    obj: Mapping[str, object], *, selected_price_id: str | None
) -> tuple[str | None, str | None]:
    start = obj.get("current_period_start")
    end = obj.get("current_period_end")
    if start is None or end is None:
        items = obj.get("items")
        rows = items.get("data") if isinstance(items, Mapping) else None
        if isinstance(rows, list):
            candidates = [row for row in rows if isinstance(row, Mapping)]
            if selected_price_id is not None:
                candidates = [
                    row
                    for row in candidates
                    if _subscription_item_price_id(row) == selected_price_id
                ]
            for row in candidates:
                row_start = row.get("current_period_start")
                row_end = row.get("current_period_end")
                if row_start is not None and row_end is not None:
                    start = start if start is not None else row_start
                    end = end if end is not None else row_end
                    break
    return _unix_or_iso(start), _unix_or_iso(end)


def _unix_or_iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=UTC).isoformat()
    text = str(value).strip()
    if not text:
        return None
    return _parse_datetime(text).isoformat()


def _customer_index_id(external_customer_id: str) -> str:
    return "cus-" + hashlib.sha256(external_customer_id.encode("utf-8")).hexdigest()


def _subscription_index_id(external_subscription_id: str) -> str:
    return "sub-" + hashlib.sha256(
        external_subscription_id.encode("utf-8")
    ).hexdigest()


def _subscription_refresh_resource_id(external_subscription_id: str) -> str:
    digest = hashlib.sha256(external_subscription_id.encode("utf-8")).hexdigest()
    return "billing-subscription-refresh-" + digest


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_text(value: object, field: str) -> str:
    text = _optional_text(value)
    if not text:
        raise BillingEntitlementError(f"{field} is required")
    return text


def _nonnegative_int(value: object, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BillingEntitlementError(f"{field} is invalid") from exc
    if parsed < 0:
        raise BillingEntitlementError(f"{field} cannot be negative")
    return parsed


def canonical_event_bytes(event: Mapping[str, Any]) -> bytes:
    """Stable bytes for tests or non-SDK event replay receipts."""
    return json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
