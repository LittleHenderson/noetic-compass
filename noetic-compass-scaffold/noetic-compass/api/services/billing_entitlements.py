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

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import Any, Literal, Mapping
from uuid import uuid4

from api.services.production.state_substrate.interface import (
    Lease,
    LeaseHeld,
    LedgerRecord,
    StateStore,
    VersionConflict,
)


BILLING_ENTITLEMENT_SCHEMA_VERSION = "cas_harness_billing_entitlement.v2"
SUBSCRIPTION_KIND = "billing_subscription"
SUBSCRIPTION_RECORD_ID = "current"
CUSTOMER_INDEX_KIND = "billing_customer_index"
SUBSCRIPTION_INDEX_KIND = "billing_subscription_index"
WEBHOOK_EVENT_KIND = "billing_webhook_event"
CHECKOUT_INTENT_KIND = "billing_checkout_intent"
CHECKOUT_INTENT_RECORD_ID = "current"
CHECKOUT_SESSION_INDEX_KIND = "billing_checkout_session_index"
CHECKOUT_COMPLETION_INDEX_KIND = "billing_checkout_completion_index"
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
    "pending_provider_revalidation",
    "quarantined",
]

_SUBSCRIPTION_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "tenant_id",
        "plan_id",
        "status",
        "source",
        "billing_account_id",
        "external_customer_id",
        "external_subscription_id",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
        "provider_event_id",
        "provider_event_created",
        "checkout_request_id",
        "checkout_session_id",
        "checkout_event_id",
        "checkout_event_payload_sha256",
        "checkout_lineage_sha256",
        "provider_event_payload_sha256",
        "provider_refresh_facts_sha256",
        "provider_refreshed_object_sha256",
        "provider_refresh_fence",
        "provider_livemode",
        "quarantine_reason",
        "updated_at",
    }
)
_COMPLETED_CHECKOUT_INTENT_KEYS = frozenset(
    {
        "schema_version",
        "tenant_id",
        "billing_account_id",
        "plan_id",
        "request_id",
        "state",
        "created_at",
        "updated_at",
        "checkout_session_id",
        "url",
    }
)
_WEBHOOK_RECEIPT_BASE_KEYS = frozenset(
    {
        "schema_version",
        "event_id",
        "event_type",
        "event_created",
        "payload_sha256",
        "signature_verified",
        "signature_verified_at",
        "livemode",
        "state",
        "received_at",
    }
)
_WEBHOOK_RECEIPT_ALLOWED_KEYS = _WEBHOOK_RECEIPT_BASE_KEYS | {
    "provider_refreshes",
    "tenant_id",
    "detail",
    "finished_at",
    "applied_subscription_facts_sha256",
    "external_subscription_id",
    "subscription_refresh_resource_id",
    "subscription_refresh_fence",
    "subscription_refresh_lock_token_sha256",
}
_WEBHOOK_TERMINAL_KEYS = frozenset({"tenant_id", "detail", "finished_at"})
_WEBHOOK_SUBSCRIPTION_ATTEMPT_KEYS = frozenset(
    {
        "external_subscription_id",
        "subscription_refresh_resource_id",
        "subscription_refresh_fence",
        "subscription_refresh_lock_token_sha256",
    }
)
_WEBHOOK_REFRESH_KEYS = frozenset(
    {
        "external_subscription_id",
        "refreshed_object_sha256",
        "provider_request_id",
        "refresh_resource_id",
        "refresh_lock_token_sha256",
        "refresh_fence",
        "retrieved_at",
        "refresh_facts_sha256",
    }
)
_SUBSCRIPTION_WEBHOOK_TYPES = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
    }
)


class BillingEntitlementError(RuntimeError):
    """A billing transition is malformed, contradictory, or cannot be trusted."""


class BillingEventConflict(BillingEntitlementError):
    """A provider identity/event was already bound to contradictory data."""


@dataclass(frozen=True, slots=True)
class StripeSubscriptionProvenance:
    """Immutable digests needed to re-prove one paid subscription grant."""

    checkout_request_id: str
    checkout_session_id: str
    checkout_event_id: str
    checkout_event_payload_sha256: str
    checkout_lineage_sha256: str
    provider_event_id: str
    provider_event_payload_sha256: str
    provider_refresh_facts_sha256: str
    provider_refreshed_object_sha256: str
    provider_refresh_fence: int
    checkout_receipt_facts_sha256: str | None = None
    provider_receipt_facts_sha256: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "checkout_request_id",
            "checkout_session_id",
            "checkout_event_id",
            "provider_event_id",
        ):
            value = getattr(self, field_name)
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
            ):
                raise BillingEntitlementError(
                    f"subscription provenance {field_name} is invalid"
                )
        if (
            not isinstance(self.provider_refresh_fence, int)
            or isinstance(self.provider_refresh_fence, bool)
            or self.provider_refresh_fence < 0
        ):
            raise BillingEntitlementError(
                "subscription provenance provider_refresh_fence is invalid"
            )
        for field_name in (
            "checkout_event_payload_sha256",
            "checkout_lineage_sha256",
            "provider_event_payload_sha256",
            "provider_refresh_facts_sha256",
            "provider_refreshed_object_sha256",
        ):
            value = getattr(self, field_name)
            if not _is_sha256(value):
                raise BillingEntitlementError(
                    f"subscription provenance {field_name} is invalid"
                )
        for field_name in (
            "checkout_receipt_facts_sha256",
            "provider_receipt_facts_sha256",
        ):
            value = getattr(self, field_name)
            if value is not None and not _is_sha256(value):
                raise BillingEntitlementError(
                    f"subscription provenance {field_name} is invalid"
                )

    def to_payload(self) -> dict[str, str | int | None]:
        return {
            "checkout_request_id": self.checkout_request_id,
            "checkout_session_id": self.checkout_session_id,
            "checkout_event_id": self.checkout_event_id,
            "checkout_event_payload_sha256": self.checkout_event_payload_sha256,
            "checkout_lineage_sha256": self.checkout_lineage_sha256,
            "provider_event_id": self.provider_event_id,
            "provider_event_payload_sha256": self.provider_event_payload_sha256,
            "provider_refresh_facts_sha256": self.provider_refresh_facts_sha256,
            "provider_refreshed_object_sha256": (
                self.provider_refreshed_object_sha256
            ),
            "provider_refresh_fence": self.provider_refresh_fence,
            "checkout_receipt_facts_sha256": self.checkout_receipt_facts_sha256,
            "provider_receipt_facts_sha256": self.provider_receipt_facts_sha256,
        }

    def to_subscription_payload(self) -> dict[str, str | int]:
        payload = self.to_payload()
        payload.pop("provider_event_id")
        payload.pop("checkout_receipt_facts_sha256")
        payload.pop("provider_receipt_facts_sha256")
        return {
            key: value if key == "provider_refresh_fence" else str(value)
            for key, value in payload.items()
        }


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
    checkout_request_id: str | None = None
    checkout_session_id: str | None = None
    checkout_event_id: str | None = None
    checkout_event_payload_sha256: str | None = None
    checkout_lineage_sha256: str | None = None
    provider_event_payload_sha256: str | None = None
    provider_refresh_facts_sha256: str | None = None
    provider_refreshed_object_sha256: str | None = None
    provider_refresh_fence: int = 0
    provider_livemode: bool | None = None
    quarantine_reason: str | None = None
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
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
            if (
                not self.billing_account_id
                or not self.current_period_start
                or not self.current_period_end
            ):
                raise BillingEntitlementError(
                    "manual comped subscriptions require account and exact period"
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
                self.billing_account_id
                and self.external_customer_id
                and self.external_subscription_id
                and self.provider_event_id
            ):
                raise BillingEntitlementError(
                    "Stripe subscriptions require billing account, customer, "
                    "subscription, and event ids"
                )
            if self.status in {"active", "trialing"}:
                if not self.current_period_start or not self.current_period_end:
                    raise BillingEntitlementError(
                        "active Stripe subscriptions require an exact current period"
                    )
                StripeSubscriptionProvenance(
                    checkout_request_id=_required_text(
                        self.checkout_request_id,
                        "subscription.checkout_request_id",
                    ),
                    checkout_session_id=_required_text(
                        self.checkout_session_id,
                        "subscription.checkout_session_id",
                    ),
                    checkout_event_id=_required_text(
                        self.checkout_event_id, "subscription.checkout_event_id"
                    ),
                    checkout_event_payload_sha256=_required_text(
                        self.checkout_event_payload_sha256,
                        "subscription.checkout_event_payload_sha256",
                    ),
                    checkout_lineage_sha256=_required_text(
                        self.checkout_lineage_sha256,
                        "subscription.checkout_lineage_sha256",
                    ),
                    provider_event_id=_required_text(
                        self.provider_event_id,
                        "subscription.provider_event_id",
                    ),
                    provider_event_payload_sha256=_required_text(
                        self.provider_event_payload_sha256,
                        "subscription.provider_event_payload_sha256",
                    ),
                    provider_refresh_facts_sha256=_required_text(
                        self.provider_refresh_facts_sha256,
                        "subscription.provider_refresh_facts_sha256",
                    ),
                    provider_refreshed_object_sha256=_required_text(
                        self.provider_refreshed_object_sha256,
                        "subscription.provider_refreshed_object_sha256",
                    ),
                    provider_refresh_fence=self.provider_refresh_fence,
                )
            if self.provider_event_created < 0:
                raise BillingEntitlementError(
                    "Stripe provider event timestamp cannot be negative"
                )
            if not isinstance(self.provider_livemode, bool):
                raise BillingEntitlementError(
                    "Stripe subscriptions require an exact provider livemode fact"
                )
            if (
                not isinstance(self.provider_refresh_fence, int)
                or isinstance(self.provider_refresh_fence, bool)
                or self.provider_refresh_fence < 0
            ):
                raise BillingEntitlementError(
                    "Stripe provider refresh fence is invalid"
                )
        if self.current_period_start is not None or self.current_period_end is not None:
            if not self.current_period_start or not self.current_period_end:
                raise BillingEntitlementError(
                    "subscription period start and end must both be present"
                )
            try:
                start = _parse_datetime(self.current_period_start)
                end = _parse_datetime(self.current_period_end)
            except (TypeError, ValueError) as exc:
                raise BillingEntitlementError(
                    "subscription period timestamps must be timezone-aware"
                ) from exc
            if start >= end:
                raise BillingEntitlementError(
                    "subscription period start must precede its end"
                )
        if not isinstance(self.cancel_at_period_end, bool):
            raise BillingEntitlementError(
                "subscription cancel_at_period_end must be boolean"
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
            "checkout_request_id": self.checkout_request_id,
            "checkout_session_id": self.checkout_session_id,
            "checkout_event_id": self.checkout_event_id,
            "checkout_event_payload_sha256": self.checkout_event_payload_sha256,
            "checkout_lineage_sha256": self.checkout_lineage_sha256,
            "provider_event_payload_sha256": self.provider_event_payload_sha256,
            "provider_refresh_facts_sha256": self.provider_refresh_facts_sha256,
            "provider_refreshed_object_sha256": (
                self.provider_refreshed_object_sha256
            ),
            "provider_refresh_fence": self.provider_refresh_fence,
            "provider_livemode": self.provider_livemode,
            "quarantine_reason": self.quarantine_reason,
            "updated_at": self.updated_at or _now_iso(),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "SubscriptionRecord":
        if (
            set(payload) != _SUBSCRIPTION_PAYLOAD_KEYS
            or payload.get("schema_version") != BILLING_ENTITLEMENT_SCHEMA_VERSION
        ):
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
            "pending_provider_revalidation",
            "quarantined",
        }:
            raise BillingEntitlementError("stored subscription status is invalid")
        raw_source = str(payload.get("source") or "")
        if raw_source not in {"none", "manual_comped", "stripe_verified"}:
            raise BillingEntitlementError("stored subscription source is invalid")
        subscription = cls(
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
            cancel_at_period_end=_strict_bool(
                payload.get("cancel_at_period_end", False),
                "subscription.cancel_at_period_end",
            ),
            provider_event_id=_optional_text(payload.get("provider_event_id")),
            provider_event_created=_nonnegative_int(
                payload.get("provider_event_created", 0),
                "subscription.provider_event_created",
            ),
            checkout_request_id=_optional_text(payload.get("checkout_request_id")),
            checkout_session_id=_optional_text(payload.get("checkout_session_id")),
            checkout_event_id=_optional_text(payload.get("checkout_event_id")),
            checkout_event_payload_sha256=_optional_text(
                payload.get("checkout_event_payload_sha256")
            ),
            checkout_lineage_sha256=_optional_text(
                payload.get("checkout_lineage_sha256")
            ),
            provider_event_payload_sha256=_optional_text(
                payload.get("provider_event_payload_sha256")
            ),
            provider_refresh_facts_sha256=_optional_text(
                payload.get("provider_refresh_facts_sha256")
            ),
            provider_refreshed_object_sha256=_optional_text(
                payload.get("provider_refreshed_object_sha256")
            ),
            provider_refresh_fence=_nonnegative_int(
                payload.get("provider_refresh_fence"),
                "subscription.provider_refresh_fence",
            ),
            provider_livemode=(
                _strict_bool(
                    payload.get("provider_livemode"),
                    "subscription.provider_livemode",
                )
                if raw_source == "stripe_verified"
                else None
            ),
            quarantine_reason=_optional_text(payload.get("quarantine_reason")),
            updated_at=_required_text(
                payload.get("updated_at"), "subscription.updated_at"
            ),
        )
        try:
            _parse_datetime(subscription.updated_at)
        except (TypeError, ValueError) as exc:
            raise BillingEntitlementError(
                "subscription updated_at is invalid"
            ) from exc
        if _canonical_sha256(payload) != _canonical_sha256(
            subscription.to_payload()
        ):
            raise BillingEntitlementError(
                "stored subscription facts are not exact"
            )
        return subscription


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

    @property
    def can_run_distributed_audit(self) -> bool:
        return self.active and self.plan.distributed_audit

    def to_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan.to_dict(),
            "subscription_status": self.subscription_status,
            "subscription_source": self.subscription_source,
            "active": self.active,
            "can_run_live_audit": self.can_run_live_audit,
            "can_run_distributed_audit": self.can_run_distributed_audit,
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
        free = PLAN_CATALOG["free_reference"]
        try:
            subscription = self.get_subscription(tenant_id)
        except (BillingEntitlementError, ValueError, TypeError):
            return EntitlementDecision(
                tenant_id=tenant_id,
                plan=free,
                subscription_status="none",
                subscription_source="none",
                active=False,
                reason="stored subscription is malformed; live access denied",
            )
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
        period_live = subscription_period_is_live(subscription, now=clock)
        provenance_live = subscription.source != "stripe_verified"
        if active_status and subscription.source == "stripe_verified":
            try:
                self.assert_subscription_provenance(subscription)
                provenance_live = True
            except (BillingEntitlementError, ValueError, TypeError):
                provenance_live = False
        active = (
            subscription_is_live(subscription, now=clock) and provenance_live
        )
        if not active:
            reason = (
                "subscription provenance is absent or invalid"
                if active_status and period_live and not provenance_live
                else "subscription period is absent, malformed, future, or expired"
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
            record = LedgerRecord.new(
                tenant_id=tenant_id,
                kind=CHECKOUT_INTENT_KIND,
                record_id=CHECKOUT_INTENT_RECORD_ID,
                payload=payload,
                source="billing.checkout_intent",
                trace_id=request_id,
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
        session_id = _required_text(
            checkout_session_id, "checkout_session_id"
        )
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                tenant_id, CHECKOUT_INTENT_KIND, CHECKOUT_INTENT_RECORD_ID
            )
            if existing is None or str(existing.payload.get("request_id")) != request_id:
                raise BillingEventConflict("Checkout intent changed before completion")
            payload = dict(existing.payload)
            if payload.get("state") == "completed":
                if (
                    payload.get("checkout_session_id") != session_id
                    or payload.get("url") != url
                ):
                    raise BillingEventConflict(
                        "Checkout intent completion contradicts its durable session"
                    )
                self._bind_checkout_session(payload)
                return payload
            payload.update(
                {
                    "state": "completed",
                    "checkout_session_id": session_id,
                    "url": url,
                    "updated_at": _now_iso(),
                }
            )
            # Persist the immutable reverse index first. The tenant intent must
            # still be marked completed before a webhook may consume it, so a
            # crash between these writes remains fail-closed and retryable.
            self._bind_checkout_session(payload)
            try:
                self._store.put(
                    existing.with_payload(payload),
                    expected_version=existing.version,
                )
                return payload
            except VersionConflict:
                continue
        raise BillingEntitlementError("Checkout intent completion contention exceeded")

    def require_checkout_lineage(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
        plan_id: str,
        request_id: str,
        checkout_session_id: str | None = None,
    ) -> Mapping[str, object]:
        """Revalidate one server-created Checkout session and its exact owner.

        Stripe metadata is useful only as a lookup claim. The durable tenant
        intent and immutable session index must independently agree before any
        provider customer or subscription can become authoritative.
        """

        expected = {
            "tenant_id": _required_text(tenant_id, "checkout.tenant_id"),
            "billing_account_id": _required_text(
                billing_account_id, "checkout.billing_account_id"
            ),
            "plan_id": _required_text(plan_id, "checkout.plan_id"),
            "request_id": _required_text(request_id, "checkout.request_id"),
        }
        intent = self._store.get(
            expected["tenant_id"], CHECKOUT_INTENT_KIND, CHECKOUT_INTENT_RECORD_ID
        )
        if intent is None:
            raise BillingEntitlementError(
                "Stripe metadata has no durable Checkout intent"
            )
        if (
            intent.tenant_id != expected["tenant_id"]
            or intent.kind != CHECKOUT_INTENT_KIND
            or intent.record_id != CHECKOUT_INTENT_RECORD_ID
            or intent.parent_ids
            or intent.source != "billing.checkout_intent"
        ):
            raise BillingEntitlementError(
                "durable Checkout intent envelope is invalid"
            )
        if intent.trace_id != expected["request_id"]:
            raise BillingEventConflict(
                "Stripe metadata contradicts the durable Checkout intent"
            )
        payload = dict(intent.payload)
        if payload.get("state") != "completed":
            raise BillingEntitlementError(
                "Stripe Checkout intent is not durably completed"
            )
        if (
            set(payload) != _COMPLETED_CHECKOUT_INTENT_KEYS
            or payload.get("schema_version") != BILLING_ENTITLEMENT_SCHEMA_VERSION
        ):
            raise BillingEntitlementError("Checkout intent schema is invalid")
        if any(payload.get(field) != value for field, value in expected.items()):
            raise BillingEventConflict(
                "Stripe metadata contradicts the durable Checkout intent"
            )
        try:
            created_at = _parse_datetime(
                _required_text(payload.get("created_at"), "checkout.created_at")
            )
            updated_at = _parse_datetime(
                _required_text(payload.get("updated_at"), "checkout.updated_at")
            )
        except (TypeError, ValueError) as exc:
            raise BillingEntitlementError(
                "durable Checkout intent timestamps are invalid"
            ) from exc
        if updated_at < created_at:
            raise BillingEntitlementError(
                "durable Checkout intent timestamps are contradictory"
            )
        _required_text(payload.get("url"), "checkout.url")
        durable_session_id = _required_text(
            payload.get("checkout_session_id"), "checkout.checkout_session_id"
        )
        if (
            checkout_session_id is not None
            and _required_text(
                checkout_session_id, "checkout.checkout_session_id"
            )
            != durable_session_id
        ):
            raise BillingEventConflict(
                "Stripe Checkout session contradicts the durable Checkout intent"
            )
        index = self._store.get(
            BILLING_PLATFORM_TENANT,
            CHECKOUT_SESSION_INDEX_KIND,
            _checkout_session_index_id(durable_session_id),
        )
        expected_index = {
            "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
            "checkout_session_id": durable_session_id,
            "checkout_intent_facts_sha256": _canonical_sha256(payload),
            **expected,
        }
        if (
            index is None
            or index.version != 1
            or index.tenant_id != BILLING_PLATFORM_TENANT
            or index.kind != CHECKOUT_SESSION_INDEX_KIND
            or index.record_id != _checkout_session_index_id(durable_session_id)
            or index.parent_ids
            or index.source != "billing.checkout_session_index"
            or index.trace_id != expected["request_id"]
            or dict(index.payload) != expected_index
        ):
            raise BillingEntitlementError(
                "durable Checkout session lineage is absent or invalid"
            )
        return expected_index

    def bind_signed_checkout_completion(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
        plan_id: str,
        request_id: str,
        checkout_session_id: str,
        external_customer_id: str,
        external_subscription_id: str,
        checkout_event_id: str,
        checkout_event_payload_sha256: str,
        checkout_livemode: bool,
    ) -> Mapping[str, object]:
        """Bind one signed Checkout completion to its provider subscription."""

        lineage = dict(
            self.require_checkout_lineage(
                tenant_id=tenant_id,
                billing_account_id=billing_account_id,
                plan_id=plan_id,
                request_id=request_id,
                checkout_session_id=checkout_session_id,
            )
        )
        customer_id = _strict_provider_text(
            external_customer_id, "checkout.customer"
        )
        subscription_id = _strict_provider_text(
            external_subscription_id, "checkout.subscription"
        )
        signed_receipt = self.require_verified_webhook_event(
            event_id=_strict_provider_text(checkout_event_id, "checkout.event_id"),
            event_type="checkout.session.completed",
            payload_sha256=_required_text(
                checkout_event_payload_sha256,
                "checkout.event_payload_sha256",
            ),
            livemode=checkout_livemode,
        )
        if signed_receipt.get("state") not in {"received", "applied"}:
            raise BillingEntitlementError(
                "signed Checkout completion receipt is not consumable"
            )
        # Establish the provider indexes before exposing the completed binding.
        # Every step is immutable/idempotent, so a crash remains retryable.
        self.bind_customer(external_customer_id=customer_id, tenant_id=tenant_id)
        self.bind_subscription(
            external_subscription_id=subscription_id,
            external_customer_id=customer_id,
            tenant_id=tenant_id,
        )
        payload: dict[str, object] = {
            **lineage,
            "external_customer_id": customer_id,
            "external_subscription_id": subscription_id,
            "checkout_event_id": checkout_event_id,
            "checkout_event_payload_sha256": checkout_event_payload_sha256,
            "checkout_livemode": checkout_livemode,
        }
        record_id = _checkout_subscription_index_id(subscription_id)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT,
                CHECKOUT_COMPLETION_INDEX_KIND,
                record_id,
            )
            if existing is not None:
                if not _checkout_completion_record_matches(
                    existing, record_id=record_id, payload=payload
                ):
                    raise BillingEventConflict(
                        "Stripe subscription is already bound to a different Checkout"
                    )
                return payload
            record = LedgerRecord.new(
                tenant_id=BILLING_PLATFORM_TENANT,
                kind=CHECKOUT_COMPLETION_INDEX_KIND,
                record_id=record_id,
                payload=payload,
                source="billing.checkout_completion_index",
                trace_id=request_id,
            )
            try:
                self._store.put(record, expected_version=0)
                return payload
            except VersionConflict:
                continue
        raise BillingEntitlementError(
            "Checkout completion lineage contention exceeded"
        )

    def require_checkout_subscription_lineage(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
        plan_id: str,
        request_id: str,
        external_customer_id: str,
        external_subscription_id: str,
    ) -> Mapping[str, object]:
        """Revalidate subscription identity from the signed Checkout completion."""

        lineage = dict(
            self.require_checkout_lineage(
                tenant_id=tenant_id,
                billing_account_id=billing_account_id,
                plan_id=plan_id,
                request_id=request_id,
            )
        )
        customer_id = _required_text(
            external_customer_id, "subscription.customer"
        )
        subscription_id = _required_text(
            external_subscription_id, "subscription.id"
        )
        payload: dict[str, object] = {
            **lineage,
            "external_customer_id": customer_id,
            "external_subscription_id": subscription_id,
        }
        record_id = _checkout_subscription_index_id(subscription_id)
        record = self._store.get(
            BILLING_PLATFORM_TENANT,
            CHECKOUT_COMPLETION_INDEX_KIND,
            record_id,
        )
        if record is not None:
            payload.update(
                {
                    "checkout_event_id": record.payload.get("checkout_event_id"),
                    "checkout_event_payload_sha256": record.payload.get(
                        "checkout_event_payload_sha256"
                    ),
                    "checkout_livemode": record.payload.get(
                        "checkout_livemode"
                    ),
                }
            )
        if not _checkout_completion_record_matches(
            record, record_id=record_id, payload=payload
        ):
            raise BillingEntitlementError(
                "signed Checkout completion lineage is absent or invalid"
            )
        checkout_event_id = _required_text(
            payload.get("checkout_event_id"), "checkout.event_id"
        )
        checkout_event_payload_sha256 = _required_text(
            payload.get("checkout_event_payload_sha256"),
            "checkout.event_payload_sha256",
        )
        checkout_livemode = _strict_bool(
            payload.get("checkout_livemode"), "checkout.livemode"
        )
        self.require_verified_webhook_event(
            event_id=checkout_event_id,
            event_type="checkout.session.completed",
            payload_sha256=checkout_event_payload_sha256,
            livemode=checkout_livemode,
            state="applied",
            tenant_id=tenant_id,
        )
        self.require_customer_binding(
            external_customer_id=customer_id,
            tenant_id=tenant_id,
        )
        self.require_subscription_binding(
            external_subscription_id=subscription_id,
            external_customer_id=customer_id,
            tenant_id=tenant_id,
        )
        return payload

    def build_subscription_provenance(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
        plan_id: str,
        request_id: str,
        external_customer_id: str,
        external_subscription_id: str,
        provider_event_id: str,
        provider_event_payload_sha256: str,
        refresh_lock_token: str,
        provider_refresh_facts_sha256: str,
    ) -> StripeSubscriptionProvenance:
        """Revalidate every durable precursor before constructing grant facts."""

        lineage = self.require_checkout_subscription_lineage(
            tenant_id=tenant_id,
            billing_account_id=billing_account_id,
            plan_id=plan_id,
            request_id=request_id,
            external_customer_id=external_customer_id,
            external_subscription_id=external_subscription_id,
        )
        provider_receipt = self.require_verified_webhook_event(
            event_id=provider_event_id,
            payload_sha256=provider_event_payload_sha256,
        )
        if provider_receipt.get("state") not in {"received", "unresolved"}:
            raise BillingEntitlementError(
                "subscription provider receipt is not consumable"
            )
        if provider_receipt.get("event_type") not in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.paused",
            "customer.subscription.resumed",
        }:
            raise BillingEntitlementError(
                "subscription provider receipt type is invalid"
            )
        refresh = self.require_webhook_refresh(
            event_id=provider_event_id,
            external_subscription_id=external_subscription_id,
            refresh_lock_token=refresh_lock_token,
            refresh_facts_sha256=provider_refresh_facts_sha256,
        )
        return StripeSubscriptionProvenance(
            checkout_request_id=_required_text(
                lineage.get("request_id"), "checkout.request_id"
            ),
            checkout_session_id=_required_text(
                lineage.get("checkout_session_id"), "checkout.session_id"
            ),
            checkout_event_id=_required_text(
                lineage.get("checkout_event_id"), "checkout.event_id"
            ),
            checkout_event_payload_sha256=_required_text(
                lineage.get("checkout_event_payload_sha256"),
                "checkout.event_payload_sha256",
            ),
            checkout_lineage_sha256=_canonical_sha256(lineage),
            provider_event_id=_required_text(
                provider_event_id, "subscription.provider_event_id"
            ),
            provider_event_payload_sha256=provider_event_payload_sha256,
            provider_refresh_facts_sha256=provider_refresh_facts_sha256,
            provider_refreshed_object_sha256=_required_sha256(
                refresh.get("refreshed_object_sha256"),
                "refresh.refreshed_object_sha256",
            ),
            provider_refresh_fence=_nonnegative_int(
                refresh.get("refresh_fence"), "refresh.refresh_fence"
            ),
        )

    def assert_subscription_provenance(
        self, subscription: SubscriptionRecord
    ) -> StripeSubscriptionProvenance:
        """Re-read exact immutable lineage and applied receipts on every serve."""

        if subscription.source != "stripe_verified":
            raise BillingEntitlementError(
                "subscription is not a Stripe-verified provider grant"
            )
        provenance = StripeSubscriptionProvenance(
            checkout_request_id=_required_text(
                subscription.checkout_request_id,
                "subscription.checkout_request_id",
            ),
            checkout_session_id=_required_text(
                subscription.checkout_session_id,
                "subscription.checkout_session_id",
            ),
            checkout_event_id=_required_text(
                subscription.checkout_event_id, "subscription.checkout_event_id"
            ),
            checkout_event_payload_sha256=_required_text(
                subscription.checkout_event_payload_sha256,
                "subscription.checkout_event_payload_sha256",
            ),
            checkout_lineage_sha256=_required_text(
                subscription.checkout_lineage_sha256,
                "subscription.checkout_lineage_sha256",
            ),
            provider_event_id=_required_text(
                subscription.provider_event_id,
                "subscription.provider_event_id",
            ),
            provider_event_payload_sha256=_required_text(
                subscription.provider_event_payload_sha256,
                "subscription.provider_event_payload_sha256",
            ),
            provider_refresh_facts_sha256=_required_text(
                subscription.provider_refresh_facts_sha256,
                "subscription.provider_refresh_facts_sha256",
            ),
            provider_refreshed_object_sha256=_required_text(
                subscription.provider_refreshed_object_sha256,
                "subscription.provider_refreshed_object_sha256",
            ),
            provider_refresh_fence=subscription.provider_refresh_fence,
        )
        subscription_id = _required_text(
            subscription.external_subscription_id,
            "subscription.external_subscription_id",
        )
        completion = self._store.get(
            BILLING_PLATFORM_TENANT,
            CHECKOUT_COMPLETION_INDEX_KIND,
            _checkout_subscription_index_id(subscription_id),
        )
        if completion is None or not isinstance(completion.payload, Mapping):
            raise BillingEntitlementError(
                "signed Checkout completion lineage is absent or invalid"
            )
        completion_payload = dict(completion.payload)
        lineage = self.require_checkout_subscription_lineage(
            tenant_id=subscription.tenant_id,
            billing_account_id=_required_text(
                subscription.billing_account_id, "subscription.billing_account_id"
            ),
            plan_id=subscription.plan_id,
            request_id=provenance.checkout_request_id,
            external_customer_id=_required_text(
                subscription.external_customer_id,
                "subscription.external_customer_id",
            ),
            external_subscription_id=subscription_id,
        )
        if (
            _canonical_sha256(lineage) != provenance.checkout_lineage_sha256
            or lineage.get("request_id") != provenance.checkout_request_id
            or lineage.get("checkout_session_id")
            != provenance.checkout_session_id
            or lineage.get("checkout_event_id") != provenance.checkout_event_id
            or lineage.get("checkout_event_payload_sha256")
            != provenance.checkout_event_payload_sha256
            or _strict_bool(
                lineage.get("checkout_livemode"), "checkout.livemode"
            )
            is not subscription.provider_livemode
        ):
            raise BillingEntitlementError(
                "subscription Checkout lineage digest is stale or invalid"
            )
        checkout_receipt = self.require_verified_webhook_event(
            event_id=provenance.checkout_event_id,
            event_type="checkout.session.completed",
            payload_sha256=provenance.checkout_event_payload_sha256,
            livemode=_strict_bool(
                lineage.get("checkout_livemode"), "checkout.livemode"
            ),
            state="applied",
            tenant_id=subscription.tenant_id,
        )
        receipt = self.require_verified_webhook_event(
            event_id=provenance.provider_event_id,
            payload_sha256=provenance.provider_event_payload_sha256,
            livemode=_strict_bool(
                subscription.provider_livemode,
                "subscription.provider_livemode",
            ),
            state="applied",
            tenant_id=subscription.tenant_id,
        )
        if checkout_receipt.get("livemode") is not receipt.get("livemode"):
            raise BillingEntitlementError(
                "Checkout and subscription livemode facts are contradictory"
            )
        if receipt.get("event_type") not in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.paused",
            "customer.subscription.resumed",
        }:
            raise BillingEntitlementError(
                "subscription provider receipt type is invalid"
            )
        refresh = _require_stored_refresh_facts(
            receipt,
            external_subscription_id=subscription_id,
            refresh_facts_sha256=provenance.provider_refresh_facts_sha256,
        )
        if (
            refresh.get("refreshed_object_sha256")
            != provenance.provider_refreshed_object_sha256
            or refresh.get("refresh_fence")
            != provenance.provider_refresh_fence
            or receipt.get("external_subscription_id") != subscription_id
            or receipt.get("subscription_refresh_resource_id")
            != refresh.get("refresh_resource_id")
            or receipt.get("subscription_refresh_fence")
            != refresh.get("refresh_fence")
            or receipt.get("subscription_refresh_lock_token_sha256")
            != refresh.get("refresh_lock_token_sha256")
        ):
            raise BillingEntitlementError(
                "subscription provider snapshot digest is stale or invalid"
            )
        if receipt.get("applied_subscription_facts_sha256") != (
            subscription_authority_facts_sha256(subscription)
        ):
            raise BillingEntitlementError(
                "applied provider receipt contradicts the current subscription"
            )
        return replace(
            provenance,
            checkout_receipt_facts_sha256=_canonical_sha256(checkout_receipt),
            provider_receipt_facts_sha256=_canonical_sha256(receipt),
        )

    def assert_applied_subscription_replay_consistent(
        self, *, external_subscription_id: str, event_id: str
    ) -> SubscriptionRecord:
        """Guard a 200 duplicate ACK against receipt/row crash splits.

        A later fully proven provider event may legitimately supersede the
        replayed event. If the current row still claims the replayed event,
        however, its complete applied receipt and authority digest must match.
        Missing indexes/rows and pending or quarantined rows are never blindly
        acknowledged as successful duplicates.
        """

        subscription_id = _strict_provider_text(
            external_subscription_id, "subscription.id"
        )
        replay_event_id = _strict_provider_text(event_id, "event.id")
        index = self._store.get(
            BILLING_PLATFORM_TENANT,
            SUBSCRIPTION_INDEX_KIND,
            _subscription_index_id(subscription_id),
        )
        if index is None:
            raise BillingEventConflict(
                "applied subscription receipt has no durable subscription binding"
            )
        tenant_id = _required_text(
            index.payload.get("tenant_id"), "index.tenant_id"
        )
        customer_id = _required_text(
            index.payload.get("external_customer_id"),
            "index.external_customer_id",
        )
        try:
            self.require_subscription_binding(
                external_subscription_id=subscription_id,
                external_customer_id=customer_id,
                tenant_id=tenant_id,
            )
            subscription = self.get_subscription(tenant_id)
        except BillingEntitlementError as exc:
            raise BillingEventConflict(
                "applied subscription receipt binding is absent or invalid"
            ) from exc
        if (
            subscription is None
            or subscription.source != "stripe_verified"
            or subscription.status
            in {"pending_provider_revalidation", "quarantined"}
        ):
            raise BillingEventConflict(
                "applied subscription receipt contradicts current subscription state"
            )
        if (
            subscription.external_subscription_id == subscription_id
            and subscription.external_customer_id != customer_id
        ):
            raise BillingEventConflict(
                "applied subscription receipt contradicts current subscription identity"
            )
        try:
            self.assert_subscription_provenance(subscription)
        except BillingEntitlementError as exc:
            message = (
                "applied subscription receipt contradicts its current row"
                if subscription.provider_event_id == replay_event_id
                else "applied subscription replay is not superseded by proven current state"
            )
            raise BillingEventConflict(message) from exc
        return subscription

    def _bind_checkout_session(self, intent: Mapping[str, object]) -> None:
        if (
            set(intent) != _COMPLETED_CHECKOUT_INTENT_KEYS
            or intent.get("schema_version") != BILLING_ENTITLEMENT_SCHEMA_VERSION
            or intent.get("state") != "completed"
        ):
            raise BillingEntitlementError(
                "completed Checkout intent facts are invalid"
            )
        created_at = _parse_datetime(
            _required_text(intent.get("created_at"), "checkout.created_at")
        )
        updated_at = _parse_datetime(
            _required_text(intent.get("updated_at"), "checkout.updated_at")
        )
        if updated_at < created_at:
            raise BillingEntitlementError(
                "completed Checkout intent timestamps are contradictory"
            )
        _required_text(intent.get("url"), "checkout.url")
        session_id = _required_text(
            intent.get("checkout_session_id"), "checkout.checkout_session_id"
        )
        request_id = _required_text(
            intent.get("request_id"), "checkout.request_id"
        )
        payload: dict[str, object] = {
            "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
            "checkout_session_id": session_id,
            "tenant_id": _required_text(
                intent.get("tenant_id"), "checkout.tenant_id"
            ),
            "billing_account_id": _required_text(
                intent.get("billing_account_id"), "checkout.billing_account_id"
            ),
            "plan_id": _required_text(intent.get("plan_id"), "checkout.plan_id"),
            "request_id": request_id,
            "checkout_intent_facts_sha256": _canonical_sha256(intent),
        }
        record_id = _checkout_session_index_id(session_id)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, CHECKOUT_SESSION_INDEX_KIND, record_id
            )
            if existing is not None:
                if (
                    existing.version != 1
                    or existing.source != "billing.checkout_session_index"
                    or existing.trace_id != request_id
                    or dict(existing.payload) != payload
                ):
                    raise BillingEventConflict(
                        "Stripe Checkout session is already bound to different lineage"
                    )
                return
            record = LedgerRecord.new(
                tenant_id=BILLING_PLATFORM_TENANT,
                kind=CHECKOUT_SESSION_INDEX_KIND,
                record_id=record_id,
                payload=payload,
                source="billing.checkout_session_index",
                trace_id=request_id,
            )
            try:
                self._store.put(record, expected_version=0)
                return
            except VersionConflict:
                continue
        raise BillingEntitlementError(
            "Checkout session lineage contention exceeded"
        )

    def acquire_subscription_refresh_lock(
        self, *, external_subscription_id: str, event_id: str
    ) -> Lease:
        try:
            return self._store.acquire_lease(
                BILLING_PLATFORM_TENANT,
                _subscription_refresh_resource_id(external_subscription_id),
                # Stripe can deliver the same event concurrently.  The event id
                # identifies the durable receipt, not one delivery attempt.  A
                # per-attempt holder keeps a duplicate delivery from using the
                # StateStore's same-holder re-acquire path to steal the live
                # attempt's token (and, on Postgres, advance its fence).
                holder=f"{event_id}:attempt:{uuid4().hex}",
                ttl_seconds=300,
            )
        except LeaseHeld as exc:
            raise BillingEntitlementError(
                "another subscription refresh is in progress"
            ) from exc

    def release_subscription_refresh_lock(self, lease: Lease) -> None:
        self._store.release_lease(lease.token)

    def claim_subscription_webhook_attempt(
        self,
        *,
        event_id: str,
        external_subscription_id: str,
        refresh_lock_token: str,
    ) -> LedgerRecord | None:
        """Fence one shared receipt to the current unique delivery attempt.

        A same-event retry performs this CAS before changing the subscription
        row to pending. Therefore a stalled older finisher either commits its
        receipt first (and this method observes ``applied``) or loses its receipt
        CAS to this newer claim and is rejected on retry.
        """

        normalized_event_id = _strict_provider_text(event_id, "event.id")
        subscription_id = _strict_provider_text(
            external_subscription_id, "subscription.id"
        )
        resource_id = _subscription_refresh_resource_id(subscription_id)
        lease = self._store.get_lease(BILLING_PLATFORM_TENANT, resource_id)
        if lease is None or lease.token != refresh_lock_token:
            raise BillingEntitlementError(
                "subscription refresh lock expired before receipt claim"
            )
        token_sha256 = hashlib.sha256(
            refresh_lock_token.encode("utf-8")
        ).hexdigest()
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT,
                WEBHOOK_EVENT_KIND,
                normalized_event_id,
            )
            if existing is None:
                return None
            payload = dict(existing.payload)
            if (
                existing.tenant_id != BILLING_PLATFORM_TENANT
                or existing.kind != WEBHOOK_EVENT_KIND
                or existing.record_id != normalized_event_id
                or existing.parent_ids
                or existing.source != "billing.stripe_webhook"
                or existing.trace_id != normalized_event_id
                or payload.get("event_id") != normalized_event_id
                or payload.get("event_type") not in _SUBSCRIPTION_WEBHOOK_TYPES
                or payload.get("signature_verified") is not True
            ):
                raise BillingEventConflict(
                    "subscription webhook receipt claim is cross-wired"
                )
            _validate_webhook_receipt_payload(payload)
            state = payload.get("state")
            if state == "applied":
                return existing
            if state not in {"received", "unresolved"}:
                raise BillingEventConflict(
                    "terminal subscription receipt cannot be claimed"
                )
            claimed_subscription_id = payload.get("external_subscription_id")
            claimed_resource_id = payload.get(
                "subscription_refresh_resource_id"
            )
            claimed_fence = payload.get("subscription_refresh_fence")
            claimed_token_sha256 = payload.get(
                "subscription_refresh_lock_token_sha256"
            )
            if claimed_subscription_id is not None:
                if (
                    claimed_subscription_id != subscription_id
                    or claimed_resource_id != resource_id
                    or not isinstance(claimed_fence, int)
                    or isinstance(claimed_fence, bool)
                    or claimed_fence < 0
                    or not _is_sha256(claimed_token_sha256)
                ):
                    raise BillingEventConflict(
                        "subscription webhook receipt claim is invalid"
                    )
                if (
                    claimed_fence > lease.fence
                    or (
                        claimed_fence == lease.fence
                        and lease.fence > 0
                        and claimed_token_sha256 != token_sha256
                    )
                ):
                    raise BillingEventConflict(
                        "stale subscription delivery cannot reclaim receipt"
                    )
                if (
                    claimed_fence == lease.fence
                    and claimed_token_sha256 == token_sha256
                ):
                    return existing
            payload.update(
                {
                    "external_subscription_id": subscription_id,
                    "subscription_refresh_resource_id": resource_id,
                    "subscription_refresh_fence": lease.fence,
                    "subscription_refresh_lock_token_sha256": token_sha256,
                }
            )
            current_lease = self._store.get_lease(
                BILLING_PLATFORM_TENANT, resource_id
            )
            if (
                current_lease is None
                or current_lease.token != refresh_lock_token
                or current_lease.fence != lease.fence
            ):
                raise BillingEntitlementError(
                    "subscription refresh lock expired before receipt claim persistence"
                )
            try:
                return self._store.put(
                    existing.with_payload(payload),
                    expected_version=existing.version,
                )
            except VersionConflict:
                continue
        raise BillingEntitlementError(
            "subscription webhook receipt claim contention exceeded"
        )

    def _require_subscription_webhook_attempt_claim(
        self,
        payload: Mapping[str, object],
        *,
        external_subscription_id: str,
        refresh_lock_token: str,
    ) -> Lease:
        subscription_id = _strict_provider_text(
            external_subscription_id, "subscription.id"
        )
        resource_id = _subscription_refresh_resource_id(subscription_id)
        lease = self._store.get_lease(BILLING_PLATFORM_TENANT, resource_id)
        token_sha256 = hashlib.sha256(
            refresh_lock_token.encode("utf-8")
        ).hexdigest()
        if (
            lease is None
            or lease.token != refresh_lock_token
            or payload.get("external_subscription_id") != subscription_id
            or payload.get("subscription_refresh_resource_id") != resource_id
            or payload.get("subscription_refresh_fence") != lease.fence
            or payload.get("subscription_refresh_lock_token_sha256")
            != token_sha256
        ):
            raise BillingEntitlementError(
                "subscription webhook receipt is claimed by another delivery"
            )
        return lease

    def apply_stripe_subscription(
        self,
        *,
        tenant_id: str,
        billing_account_id: str,
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
        provenance: StripeSubscriptionProvenance | None = None,
        refreshed_object: Mapping[str, Any] | None = None,
        price_to_plan: Mapping[str, str] | None = None,
        event_type: str | None = None,
    ) -> tuple[SubscriptionRecord, bool]:
        """Apply one signature-verified provider event; return (record, changed)."""
        if (
            not isinstance(event_id, str)
            or not event_id.strip()
            or not isinstance(event_created, int)
            or isinstance(event_created, bool)
            or event_created < 0
        ):
            raise BillingEntitlementError("provider event identity is invalid")
        if not external_customer_id or not external_subscription_id:
            raise BillingEntitlementError("provider customer/subscription ids are required")
        normalized_billing_account_id = _required_text(
            billing_account_id, "billing_account_id"
        )
        normalized_status = _subscription_status(status)
        if (
            not resource_refreshed
            or not refresh_lock_token
            or not isinstance(provenance, StripeSubscriptionProvenance)
        ):
            raise BillingEntitlementError(
                "subscription updates require verified Checkout and locked-refresh provenance"
            )
        if provenance.provider_event_id != event_id:
            raise BillingEventConflict(
                "subscription provenance event identity is cross-wired"
            )
        if (
            not isinstance(refreshed_object, Mapping)
            or not isinstance(price_to_plan, Mapping)
            or event_type not in {
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
                "customer.subscription.paused",
                "customer.subscription.resumed",
            }
        ):
            raise BillingEntitlementError(
                "subscription updates require the exact refreshed provider object"
            )
        if not isinstance(cancel_at_period_end, bool):
            raise BillingEntitlementError(
                "provider cancel_at_period_end must be boolean"
            )
        provider_receipt = self.require_verified_webhook_event(
            event_id=event_id,
            payload_sha256=provenance.provider_event_payload_sha256,
        )
        if provider_receipt.get("state") not in {"received", "unresolved"}:
            raise BillingEntitlementError(
                "subscription receipt is not open for application"
            )
        receipt_event_type = _required_text(
            provider_receipt.get("event_type"), "webhook.event_type"
        )
        receipt_livemode = _strict_bool(
            provider_receipt.get("livemode"), "webhook.livemode"
        )
        receipt_event_created = _nonnegative_int(
            provider_receipt.get("event_created"), "webhook.event_created"
        )
        if (
            event_type != receipt_event_type
            or event_created != receipt_event_created
        ):
            raise BillingEventConflict(
                "subscription application event identity contradicts its signed receipt"
            )
        refresh = self.require_webhook_refresh(
            event_id=event_id,
            external_subscription_id=external_subscription_id,
            refresh_lock_token=refresh_lock_token,
            refresh_facts_sha256=provenance.provider_refresh_facts_sha256,
        )
        if (
            refresh.get("refreshed_object_sha256")
            != provenance.provider_refreshed_object_sha256
            or refresh.get("refresh_fence")
            != provenance.provider_refresh_fence
            or _canonical_sha256(refreshed_object)
            != provenance.provider_refreshed_object_sha256
        ):
            raise BillingEventConflict(
                "subscription application contradicts the locked provider snapshot"
            )

        snapshot_subscription_id = _provider_reference_id(
            refreshed_object.get("id"), "subscription.id"
        )
        snapshot_customer_id = _provider_reference_id(
            refreshed_object.get("customer"), "subscription.customer"
        )
        snapshot_livemode = _strict_bool(
            refreshed_object.get("livemode"), "subscription.livemode"
        )
        (
            snapshot_tenant_id,
            snapshot_billing_account_id,
            snapshot_checkout_plan_id,
            snapshot_checkout_request_id,
        ) = _checkout_lineage_metadata(refreshed_object)
        price_ids = _subscription_price_ids(refreshed_object)
        mapped_plan_items = [
            (price_id, price_to_plan[price_id])
            for price_id in price_ids
            if price_id in price_to_plan
        ]
        if len(mapped_plan_items) != 1:
            raise BillingEntitlementError(
                "provider snapshot must contain exactly one configured CAS plan price"
            )
        selected_price_id, snapshot_plan_id = mapped_plan_items[0]
        snapshot_status = (
            "canceled"
            if receipt_event_type == "customer.subscription.deleted"
            else _subscription_status(refreshed_object.get("status"))
        )
        snapshot_period_start, snapshot_period_end = _subscription_period(
            refreshed_object, selected_price_id=selected_price_id
        )
        snapshot_cancel_at_period_end = _strict_bool(
            refreshed_object.get("cancel_at_period_end", False),
            "subscription.cancel_at_period_end",
        )
        if (
            snapshot_subscription_id != external_subscription_id
            or snapshot_customer_id != external_customer_id
            or snapshot_livemode is not receipt_livemode
            or snapshot_tenant_id != tenant_id
            or snapshot_billing_account_id != normalized_billing_account_id
            or snapshot_checkout_request_id != provenance.checkout_request_id
            or snapshot_checkout_plan_id != snapshot_plan_id
            or plan_id != snapshot_plan_id
            or normalized_status != snapshot_status
            or current_period_start != snapshot_period_start
            or current_period_end != snapshot_period_end
            or cancel_at_period_end != snapshot_cancel_at_period_end
        ):
            raise BillingEventConflict(
                "subscription application facts contradict the locked provider snapshot"
            )
        # From this point onward every persisted provider fact is the value
        # re-derived above from the exact digest-bound locked snapshot.
        tenant_id = snapshot_tenant_id
        normalized_billing_account_id = snapshot_billing_account_id
        external_customer_id = snapshot_customer_id
        external_subscription_id = snapshot_subscription_id
        normalized_status = snapshot_status
        current_period_start = snapshot_period_start
        current_period_end = snapshot_period_end
        cancel_at_period_end = snapshot_cancel_at_period_end
        lineage = self.require_checkout_subscription_lineage(
            tenant_id=tenant_id,
            billing_account_id=normalized_billing_account_id,
            plan_id=snapshot_checkout_plan_id,
            request_id=snapshot_checkout_request_id,
            external_customer_id=snapshot_customer_id,
            external_subscription_id=snapshot_subscription_id,
        )
        if (
            _canonical_sha256(lineage) != provenance.checkout_lineage_sha256
            or lineage.get("checkout_session_id")
            != provenance.checkout_session_id
            or lineage.get("checkout_event_id") != provenance.checkout_event_id
            or lineage.get("checkout_event_payload_sha256")
            != provenance.checkout_event_payload_sha256
            or _strict_bool(
                lineage.get("checkout_livemode"), "checkout.livemode"
            )
            is not snapshot_livemode
        ):
            raise BillingEventConflict(
                "subscription application contradicts its signed Checkout lineage"
            )

        current = self.get_subscription(tenant_id)
        if (
            current is not None
            and current.billing_account_id != normalized_billing_account_id
        ):
            raise BillingEventConflict(
                "Stripe billing account contradicts the tenant subscription binding"
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
            if existing is not None and (
                existing.provider_refresh_fence
                > provenance.provider_refresh_fence
                or (
                    provenance.provider_refresh_fence > 0
                    and existing.provider_refresh_fence
                    == provenance.provider_refresh_fence
                    and existing.provider_event_id != event_id
                )
            ):
                raise BillingEventConflict(
                    "stale subscription refresh fence cannot overwrite current state"
                )
            if (
                existing is not None
                and existing.billing_account_id != normalized_billing_account_id
            ):
                raise BillingEventConflict(
                    "Stripe billing account contradicts the tenant subscription binding"
                )
            effective_plan_id = snapshot_plan_id
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
                billing_account_id=normalized_billing_account_id,
                external_customer_id=external_customer_id,
                external_subscription_id=external_subscription_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                cancel_at_period_end=cancel_at_period_end,
                provider_event_id=event_id,
                provider_event_created=event_created,
                **provenance.to_subscription_payload(),
                provider_livemode=snapshot_livemode,
                quarantine_reason=None,
                updated_at=_now_iso(),
            )
            if normalized_status in {"active", "trialing"} and not (
                subscription_period_is_live(subscription)
            ):
                raise BillingEntitlementError(
                    "active provider subscription period is not currently live"
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
            current_lease = self._store.get_lease(
                BILLING_PLATFORM_TENANT,
                _subscription_refresh_resource_id(external_subscription_id),
            )
            if (
                current_lease is None
                or current_lease.token != refresh_lock_token
                or current_lease.fence != provenance.provider_refresh_fence
            ):
                raise BillingEntitlementError(
                    "subscription refresh lock expired before persistence"
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

    def mark_subscription_pending_revalidation(
        self,
        *,
        external_subscription_id: str,
        event_id: str,
        event_created: int,
        raw_payload: bytes,
        provider_event_payload_sha256: str,
        refresh_lock_token: str,
    ) -> SubscriptionRecord | None:
        """Deny an existing bound grant until the signed event is refreshed."""

        subscription_id = _strict_provider_text(
            external_subscription_id, "subscription.id"
        )
        signed_event = _strict_event_from_raw_payload(raw_payload)
        signed_event_id = _strict_provider_text(
            signed_event.get("id"), "event.id"
        )
        signed_event_type = _strict_provider_text(
            signed_event.get("type"), "event.type"
        )
        signed_event_created = _nonnegative_int(
            signed_event.get("created"), "event.created"
        )
        signed_livemode = _strict_bool(
            signed_event.get("livemode"), "event.livemode"
        )
        signed_data = signed_event.get("data")
        signed_obj = (
            signed_data.get("object") if isinstance(signed_data, Mapping) else None
        )
        if (
            signed_event_type not in _SUBSCRIPTION_WEBHOOK_TYPES
            or not isinstance(signed_obj, Mapping)
            or _provider_reference_id(
                signed_obj.get("id"), "signed subscription.id"
            )
            != subscription_id
            or signed_event_id != event_id
            or signed_event_created != event_created
            or hashlib.sha256(raw_payload).hexdigest()
            != provider_event_payload_sha256
        ):
            raise BillingEventConflict(
                "pending provider revalidation identity is cross-wired"
            )
        resource_id = _subscription_refresh_resource_id(subscription_id)
        lease = self._store.get_lease(BILLING_PLATFORM_TENANT, resource_id)
        if lease is None or lease.token != refresh_lock_token:
            raise BillingEntitlementError(
                "subscription refresh lock expired before pending barrier"
            )
        existing_receipt = self._store.get(
            BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
        )
        if existing_receipt is not None:
            receipt_payload = self.require_verified_webhook_event(
                event_id=event_id,
                payload_sha256=provider_event_payload_sha256,
            )
            if receipt_payload.get("state") not in {"received", "unresolved"}:
                raise BillingEventConflict(
                    "terminal subscription receipt cannot write a pending barrier"
                )
            self._require_subscription_webhook_attempt_claim(
                receipt_payload,
                external_subscription_id=subscription_id,
                refresh_lock_token=refresh_lock_token,
            )
        index_id = _subscription_index_id(subscription_id)
        index = self._store.get(
            BILLING_PLATFORM_TENANT, SUBSCRIPTION_INDEX_KIND, index_id
        )
        if index is None:
            return None
        tenant_id = _strict_provider_text(
            index.payload.get("tenant_id"), "index.tenant_id"
        )
        customer_id = _strict_provider_text(
            index.payload.get("external_customer_id"),
            "index.external_customer_id",
        )
        self.require_subscription_binding(
            external_subscription_id=subscription_id,
            external_customer_id=customer_id,
            tenant_id=tenant_id,
        )
        reason = "awaiting exact locked provider revalidation"
        for _ in range(MAX_WRITE_RETRIES):
            stored = self._store.get(
                tenant_id, SUBSCRIPTION_KIND, SUBSCRIPTION_RECORD_ID
            )
            if stored is None:
                return None
            current = SubscriptionRecord.from_payload(stored.payload)
            if (
                current.tenant_id != tenant_id
                or current.source != "stripe_verified"
                or current.external_subscription_id != subscription_id
                or current.external_customer_id != customer_id
            ):
                return None
            if (
                current.provider_refresh_fence > lease.fence
                or (
                    lease.fence > 0
                    and current.provider_refresh_fence == lease.fence
                    and current.provider_event_id != event_id
                )
            ):
                raise BillingEventConflict(
                    "stale pending-revalidation fence cannot overwrite current state"
                )
            if (
                current.status == "pending_provider_revalidation"
                and current.provider_event_id == event_id
                and current.provider_event_created == event_created
                and current.provider_event_payload_sha256
                == provider_event_payload_sha256
                and current.provider_livemode is signed_livemode
                and current.provider_refresh_fence == lease.fence
            ):
                return current
            pending = replace(
                current,
                status="pending_provider_revalidation",
                provider_event_id=event_id,
                provider_event_created=event_created,
                provider_event_payload_sha256=provider_event_payload_sha256,
                provider_refresh_facts_sha256=None,
                provider_refreshed_object_sha256=None,
                provider_refresh_fence=lease.fence,
                provider_livemode=signed_livemode,
                quarantine_reason=reason,
                updated_at=_now_iso(),
            )
            current_lease = self._store.get_lease(
                BILLING_PLATFORM_TENANT, resource_id
            )
            if (
                current_lease is None
                or current_lease.token != refresh_lock_token
                or current_lease.fence != lease.fence
            ):
                raise BillingEntitlementError(
                    "subscription refresh lock expired before pending persistence"
                )
            try:
                self._store.put(
                    stored.with_payload(pending.to_payload()),
                    expected_version=stored.version,
                )
                return pending
            except VersionConflict:
                continue
        raise BillingEntitlementError(
            "subscription pending-revalidation contention exceeded"
        )

    def quarantine_refreshed_subscription(
        self,
        *,
        external_subscription_id: str,
        event_id: str,
        event_created: int,
        detail: str,
        refresh_lock_token: str,
        provider_event_payload_sha256: str,
        provider_refresh_facts_sha256: str,
    ) -> SubscriptionRecord | None:
        """Revoke only the subscription already bound to a locked provider id.

        No tenant, account, customer, or plan claim from the refreshed object is
        trusted here. The immutable subscription index selects the sole row that
        may be quarantined, which keeps drift handling cross-tenant safe.
        """

        subscription_id = _required_text(
            external_subscription_id, "subscription.id"
        )
        if (
            not isinstance(event_created, int)
            or isinstance(event_created, bool)
            or event_created < 0
        ):
            raise BillingEntitlementError(
                "quarantine provider event timestamp is invalid"
            )
        event_payload_sha256 = _required_sha256(
            provider_event_payload_sha256,
            "quarantine.provider_event_payload_sha256",
        )
        refresh_facts_sha256 = _required_sha256(
            provider_refresh_facts_sha256,
            "quarantine.provider_refresh_facts_sha256",
        )
        resource_id = _subscription_refresh_resource_id(subscription_id)
        lease = self._store.get_lease(BILLING_PLATFORM_TENANT, resource_id)
        if lease is None or lease.token != refresh_lock_token:
            raise BillingEntitlementError(
                "subscription refresh lock expired before quarantine"
            )
        self.require_verified_webhook_event(
            event_id=event_id,
            payload_sha256=event_payload_sha256,
        )
        refresh = self.require_webhook_refresh(
            event_id=event_id,
            external_subscription_id=subscription_id,
            refresh_lock_token=refresh_lock_token,
            refresh_facts_sha256=refresh_facts_sha256,
        )
        refreshed_object_sha256 = _required_sha256(
            refresh.get("refreshed_object_sha256"),
            "quarantine.refreshed_object_sha256",
        )
        index_id = _subscription_index_id(subscription_id)
        index = self._store.get(
            BILLING_PLATFORM_TENANT, SUBSCRIPTION_INDEX_KIND, index_id
        )
        if index is None:
            return None
        expected_index_payload = {
            "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
            "external_subscription_id": subscription_id,
            "external_customer_id": index.payload.get("external_customer_id"),
            "tenant_id": index.payload.get("tenant_id"),
        }
        if (
            index.version != 1
            or index.tenant_id != BILLING_PLATFORM_TENANT
            or index.kind != SUBSCRIPTION_INDEX_KIND
            or index.record_id != index_id
            or index.parent_ids
            or index.source != "billing.subscription_index"
            or index.trace_id != index_id
            or dict(index.payload) != expected_index_payload
        ):
            raise BillingEventConflict(
                "bound subscription index is invalid; live access remains denied"
            )
        tenant_id = _required_text(index.payload.get("tenant_id"), "index.tenant_id")
        customer_id = _required_text(
            index.payload.get("external_customer_id"), "index.external_customer_id"
        )
        safe_detail = _required_text(detail, "quarantine.detail")[:500]
        for _ in range(MAX_WRITE_RETRIES):
            stored = self._store.get(
                tenant_id, SUBSCRIPTION_KIND, SUBSCRIPTION_RECORD_ID
            )
            if stored is None:
                return None
            current = SubscriptionRecord.from_payload(stored.payload)
            if (
                current.tenant_id != tenant_id
                or current.source != "stripe_verified"
                or current.external_subscription_id != subscription_id
                or current.external_customer_id != customer_id
            ):
                return None
            if (
                current.provider_refresh_fence > lease.fence
                or (
                    lease.fence > 0
                    and current.provider_refresh_fence == lease.fence
                    and current.provider_event_id != event_id
                )
            ):
                raise BillingEventConflict(
                    "stale quarantine fence cannot overwrite current state"
                )
            if (
                current.status == "quarantined"
                and current.provider_event_id == event_id
                and current.provider_event_created == event_created
                and current.provider_event_payload_sha256
                == event_payload_sha256
                and current.provider_refresh_facts_sha256
                == refresh_facts_sha256
                and current.provider_refreshed_object_sha256
                == refreshed_object_sha256
                and current.provider_refresh_fence == lease.fence
                and current.quarantine_reason == safe_detail
            ):
                return current
            quarantined = replace(
                current,
                status="quarantined",
                provider_event_id=event_id,
                provider_event_created=event_created,
                provider_event_payload_sha256=event_payload_sha256,
                provider_refresh_facts_sha256=refresh_facts_sha256,
                provider_refreshed_object_sha256=refreshed_object_sha256,
                provider_refresh_fence=lease.fence,
                quarantine_reason=safe_detail,
                updated_at=_now_iso(),
            )
            current_lease = self._store.get_lease(
                BILLING_PLATFORM_TENANT, resource_id
            )
            if (
                current_lease is None
                or current_lease.token != refresh_lock_token
                or current_lease.fence != lease.fence
            ):
                raise BillingEntitlementError(
                    "subscription refresh lock expired before quarantine persistence"
                )
            try:
                self._store.put(
                    stored.with_payload(quarantined.to_payload()),
                    expected_version=stored.version,
                )
                return quarantined
            except VersionConflict:
                continue
        raise BillingEntitlementError("subscription quarantine contention exceeded")

    def bind_customer(self, *, external_customer_id: str, tenant_id: str) -> None:
        record_id = _customer_index_id(external_customer_id)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, CUSTOMER_INDEX_KIND, record_id
            )
            if existing is not None:
                self.require_customer_binding(
                    external_customer_id=external_customer_id,
                    tenant_id=tenant_id,
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
                self.require_subscription_binding(
                    external_subscription_id=external_subscription_id,
                    external_customer_id=external_customer_id,
                    tenant_id=tenant_id,
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

    def require_customer_binding(
        self, *, external_customer_id: str, tenant_id: str
    ) -> Mapping[str, object]:
        customer_id = _required_text(external_customer_id, "customer.id")
        expected_tenant = _required_text(tenant_id, "customer.tenant_id")
        record_id = _customer_index_id(customer_id)
        record = self._store.get(
            BILLING_PLATFORM_TENANT, CUSTOMER_INDEX_KIND, record_id
        )
        payload = {
            "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
            "external_customer_id": customer_id,
            "tenant_id": expected_tenant,
        }
        if (
            record is None
            or record.version != 1
            or record.tenant_id != BILLING_PLATFORM_TENANT
            or record.kind != CUSTOMER_INDEX_KIND
            or record.record_id != record_id
            or record.parent_ids
            or record.source != "billing.customer_index"
            or record.trace_id != record_id
            or dict(record.payload) != payload
        ):
            raise BillingEventConflict(
                "Stripe customer id is not bound to the exact tenant identity"
            )
        return payload

    def require_subscription_binding(
        self,
        *,
        external_subscription_id: str,
        external_customer_id: str,
        tenant_id: str,
    ) -> Mapping[str, object]:
        subscription_id = _required_text(
            external_subscription_id, "subscription.id"
        )
        customer_id = _required_text(
            external_customer_id, "subscription.customer"
        )
        expected_tenant = _required_text(tenant_id, "subscription.tenant_id")
        record_id = _subscription_index_id(subscription_id)
        record = self._store.get(
            BILLING_PLATFORM_TENANT, SUBSCRIPTION_INDEX_KIND, record_id
        )
        payload = {
            "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
            "external_subscription_id": subscription_id,
            "external_customer_id": customer_id,
            "tenant_id": expected_tenant,
        }
        if (
            record is None
            or record.version != 1
            or record.tenant_id != BILLING_PLATFORM_TENANT
            or record.kind != SUBSCRIPTION_INDEX_KIND
            or record.record_id != record_id
            or record.parent_ids
            or record.source != "billing.subscription_index"
            or record.trace_id != record_id
            or dict(record.payload) != payload
        ):
            raise BillingEventConflict(
                "Stripe subscription id is not bound to the exact customer/tenant identity"
            )
        return payload

    def tenant_for_customer(self, external_customer_id: str) -> str | None:
        record = self._store.get(
            BILLING_PLATFORM_TENANT,
            CUSTOMER_INDEX_KIND,
            _customer_index_id(external_customer_id),
        )
        if record is None:
            return None
        tenant_id = _required_text(
            record.payload.get("tenant_id"), "customer_index.tenant_id"
        )
        self.require_customer_binding(
            external_customer_id=external_customer_id,
            tenant_id=tenant_id,
        )
        return tenant_id

    def preflight_webhook_event(
        self,
        *,
        event_id: str,
        event_type: str,
        event_created: int,
        raw_payload: bytes,
        livemode: bool,
    ) -> LedgerRecord | None:
        """Read-only replay/conflict check before a deny-first subscription barrier."""

        event_id = _strict_provider_text(event_id, "webhook.event_id")
        event_type = _strict_provider_text(event_type, "webhook.event_type")
        event_created = _nonnegative_int(event_created, "webhook.event_created")
        if not isinstance(livemode, bool):
            raise BillingEntitlementError("webhook livemode fact must be boolean")
        digest = hashlib.sha256(raw_payload).hexdigest()
        record = self._store.get(
            BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
        )
        if record is None:
            return None
        payload = dict(record.payload)
        if (
            record.tenant_id != BILLING_PLATFORM_TENANT
            or record.kind != WEBHOOK_EVENT_KIND
            or record.record_id != event_id
            or record.parent_ids
            or record.source != "billing.stripe_webhook"
            or record.trace_id != event_id
            or payload.get("schema_version")
            != BILLING_ENTITLEMENT_SCHEMA_VERSION
            or payload.get("event_id") != event_id
            or payload.get("event_type") != event_type
            or payload.get("event_created") != event_created
            or payload.get("payload_sha256") != digest
            or payload.get("livemode") is not livemode
        ):
            raise BillingEventConflict(
                "provider event id was replayed with contradictory facts"
            )
        _validate_webhook_receipt_payload(payload)
        return record

    def begin_webhook_event(
        self,
        *,
        event_id: str,
        event_type: str,
        event_created: int,
        raw_payload: bytes,
        livemode: bool,
        signature_verified: bool = False,
    ) -> tuple[LedgerRecord, bool]:
        """Record exact event bytes and an explicit post-verification route fact.

        ``signature_verified`` may be true only after the provider adapter has
        successfully constructed the event from the exact raw bytes. Direct
        callers default to unverified and therefore cannot publish entitlement.
        """
        event_id = _strict_provider_text(event_id, "webhook.event_id")
        event_type = _strict_provider_text(event_type, "webhook.event_type")
        if not isinstance(signature_verified, bool):
            raise BillingEntitlementError("webhook signature fact must be boolean")
        if not isinstance(livemode, bool):
            raise BillingEntitlementError("webhook livemode fact must be boolean")
        normalized_event_created = _nonnegative_int(
            event_created, "webhook.event_created"
        )
        digest = hashlib.sha256(raw_payload).hexdigest()
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
            )
            if existing is not None:
                if (
                    existing.tenant_id != BILLING_PLATFORM_TENANT
                    or existing.kind != WEBHOOK_EVENT_KIND
                    or existing.record_id != event_id
                    or existing.parent_ids
                    or existing.source != "billing.stripe_webhook"
                    or existing.trace_id != event_id
                    or existing.payload.get("schema_version")
                    != BILLING_ENTITLEMENT_SCHEMA_VERSION
                    or existing.payload.get("event_id") != event_id
                    or existing.payload.get("event_type") != event_type
                    or existing.payload.get("event_created")
                    != normalized_event_created
                    or existing.payload.get("payload_sha256") != digest
                    or existing.payload.get("livemode") is not livemode
                ):
                    raise BillingEventConflict(
                        "provider event id was replayed with contradictory facts"
                    )
                if signature_verified and existing.payload.get(
                    "signature_verified"
                ) is not True:
                    payload = dict(existing.payload)
                    payload.update(
                        {
                            "signature_verified": True,
                            "signature_verified_at": _now_iso(),
                        }
                    )
                    try:
                        upgraded = self._store.put(
                            existing.with_payload(payload),
                            expected_version=existing.version,
                        )
                        return upgraded, False
                    except VersionConflict:
                        continue
                return existing, False
            record = LedgerRecord.new(
                tenant_id=BILLING_PLATFORM_TENANT,
                kind=WEBHOOK_EVENT_KIND,
                record_id=event_id,
                payload={
                    "schema_version": BILLING_ENTITLEMENT_SCHEMA_VERSION,
                    "event_id": event_id,
                    "event_type": event_type,
                    "event_created": normalized_event_created,
                    "payload_sha256": digest,
                    "livemode": livemode,
                    "signature_verified": signature_verified,
                    "signature_verified_at": (
                        _now_iso() if signature_verified else None
                    ),
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

    def _assert_subscription_webhook_finalization_guard(
        self,
        payload: Mapping[str, object],
        *,
        event_id: str,
        external_subscription_id: str,
        refresh_lock_token: str,
        refresh_fence: int,
        applied_subscription_facts_sha256: str,
    ) -> None:
        lease = self._require_subscription_webhook_attempt_claim(
            payload,
            external_subscription_id=external_subscription_id,
            refresh_lock_token=refresh_lock_token,
        )
        if (
            not isinstance(refresh_fence, int)
            or isinstance(refresh_fence, bool)
            or refresh_fence < 0
            or lease.fence != refresh_fence
        ):
            raise BillingEventConflict(
                "subscription receipt finalization fence is stale"
            )
        subscription_id = _strict_provider_text(
            external_subscription_id, "subscription.id"
        )
        index = self._store.get(
            BILLING_PLATFORM_TENANT,
            SUBSCRIPTION_INDEX_KIND,
            _subscription_index_id(subscription_id),
        )
        if index is None:
            raise BillingEventConflict(
                "subscription receipt finalization binding is absent"
            )
        tenant_id = _required_text(
            index.payload.get("tenant_id"), "index.tenant_id"
        )
        customer_id = _required_text(
            index.payload.get("external_customer_id"),
            "index.external_customer_id",
        )
        self.require_subscription_binding(
            external_subscription_id=subscription_id,
            external_customer_id=customer_id,
            tenant_id=tenant_id,
        )
        subscription = self.get_subscription(tenant_id)
        if (
            subscription is None
            or subscription.source != "stripe_verified"
            or subscription.external_subscription_id != subscription_id
            or subscription.external_customer_id != customer_id
            or subscription.provider_event_id != event_id
            or subscription.provider_refresh_fence != refresh_fence
            or subscription.status
            in {"pending_provider_revalidation", "quarantined"}
            or subscription_authority_facts_sha256(subscription)
            != applied_subscription_facts_sha256
        ):
            raise BillingEventConflict(
                "subscription receipt finalization contradicts current row"
            )

    def finish_webhook_event(
        self,
        *,
        event_id: str,
        state: Literal["applied", "ignored", "unresolved"],
        tenant_id: str | None,
        detail: str,
        applied_subscription_facts_sha256: str | None = None,
        external_subscription_id: str | None = None,
        refresh_lock_token: str | None = None,
        refresh_fence: int | None = None,
    ) -> None:
        if (
            applied_subscription_facts_sha256 is not None
            and not _is_sha256(applied_subscription_facts_sha256)
        ):
            raise BillingEntitlementError(
                "applied subscription facts digest is invalid"
            )
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
            )
            if existing is None:
                raise BillingEntitlementError("webhook receipt disappeared")
            payload = dict(existing.payload)
            _validate_webhook_receipt_payload(payload)
            current_state = payload.get("state")
            if current_state in {"applied", "ignored"}:
                if current_state == state:
                    return
                raise BillingEventConflict(
                    "terminal webhook receipt cannot change state"
                )
            guarded_subscription_apply = (
                state == "applied"
                and payload.get("event_type") in _SUBSCRIPTION_WEBHOOK_TYPES
            )
            if guarded_subscription_apply:
                if (
                    applied_subscription_facts_sha256 is None
                    or external_subscription_id is None
                    or refresh_lock_token is None
                    or refresh_fence is None
                ):
                    raise BillingEntitlementError(
                        "subscription receipt finalization requires its exact attempt claim"
                    )
                self._assert_subscription_webhook_finalization_guard(
                    payload,
                    event_id=event_id,
                    external_subscription_id=external_subscription_id,
                    refresh_lock_token=refresh_lock_token,
                    refresh_fence=refresh_fence,
                    applied_subscription_facts_sha256=(
                        applied_subscription_facts_sha256
                    ),
                )
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
            if applied_subscription_facts_sha256 is not None:
                payload["applied_subscription_facts_sha256"] = (
                    applied_subscription_facts_sha256
                )
            if guarded_subscription_apply:
                # The receipt-side attempt claim is the transactional fence:
                # takeover CASes this same record first, so either this put wins
                # or its expected version fails and the retry observes/rejects
                # the newer token/fence. Recheck the row/lease immediately before
                # the receipt CAS as defense in depth.
                self._assert_subscription_webhook_finalization_guard(
                    payload,
                    event_id=event_id,
                    external_subscription_id=str(external_subscription_id),
                    refresh_lock_token=str(refresh_lock_token),
                    refresh_fence=int(refresh_fence),
                    applied_subscription_facts_sha256=str(
                        applied_subscription_facts_sha256
                    ),
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
        refresh_lock_token: str,
    ) -> str:
        resource_id = _subscription_refresh_resource_id(external_subscription_id)
        lease = self._store.get_lease(BILLING_PLATFORM_TENANT, resource_id)
        if lease is None or lease.token != refresh_lock_token:
            raise BillingEntitlementError(
                "subscription refresh lock expired before receipt persistence"
            )
        claimed_receipt = self.claim_subscription_webhook_attempt(
            event_id=event_id,
            external_subscription_id=external_subscription_id,
            refresh_lock_token=refresh_lock_token,
        )
        if claimed_receipt is None:
            raise BillingEntitlementError("webhook receipt disappeared")
        if claimed_receipt.payload.get("state") == "applied":
            raise BillingEntitlementError(
                "terminal provider receipt cannot accept another refresh"
            )
        digest = _canonical_sha256(refreshed_object)
        refresh_facts: dict[str, object] = {
            "external_subscription_id": external_subscription_id,
            "refreshed_object_sha256": digest,
            "provider_request_id": provider_request_id,
            "refresh_resource_id": resource_id,
            "refresh_lock_token_sha256": hashlib.sha256(
                refresh_lock_token.encode("utf-8")
            ).hexdigest(),
            "refresh_fence": lease.fence,
            "retrieved_at": _now_iso(),
        }
        refresh_facts_sha256 = _canonical_sha256(refresh_facts)
        refresh_entry = {
            **refresh_facts,
            "refresh_facts_sha256": refresh_facts_sha256,
        }
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
            )
            if existing is None:
                raise BillingEntitlementError("webhook receipt disappeared")
            payload = dict(existing.payload)
            attempts = list(payload.get("provider_refreshes") or [])
            _validate_webhook_receipt_payload(payload)
            if payload.get("signature_verified") is not True:
                raise BillingEntitlementError(
                    "provider refresh receipt is not signature verified"
                )
            if payload.get("state") not in {"received", "unresolved"}:
                raise BillingEntitlementError(
                    "terminal provider receipt cannot accept another refresh"
                )
            claimed_lease = self._require_subscription_webhook_attempt_claim(
                payload,
                external_subscription_id=external_subscription_id,
                refresh_lock_token=refresh_lock_token,
            )
            attempts.append(refresh_entry)
            payload["provider_refreshes"] = attempts[-20:]
            current_lease = self._store.get_lease(
                BILLING_PLATFORM_TENANT, resource_id
            )
            if (
                current_lease is None
                or current_lease.token != refresh_lock_token
                or current_lease.fence != claimed_lease.fence
            ):
                raise BillingEntitlementError(
                    "subscription refresh lock expired before receipt persistence"
                )
            try:
                self._store.put(
                    existing.with_payload(payload),
                    expected_version=existing.version,
                )
                return refresh_facts_sha256
            except VersionConflict:
                continue
        raise BillingEntitlementError("webhook refresh receipt contention exceeded")

    def require_verified_webhook_event(
        self,
        *,
        event_id: str,
        event_type: str | None = None,
        payload_sha256: str | None = None,
        livemode: bool | None = None,
        state: str | None = None,
        tenant_id: str | None = None,
    ) -> Mapping[str, object]:
        record = self._store.get(
            BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id
        )
        payload = dict(record.payload) if record is not None else {}
        if (
            record is None
            or record.tenant_id != BILLING_PLATFORM_TENANT
            or record.kind != WEBHOOK_EVENT_KIND
            or record.record_id != event_id
            or record.parent_ids
            or record.source != "billing.stripe_webhook"
            or record.trace_id != event_id
            or payload.get("schema_version")
            != BILLING_ENTITLEMENT_SCHEMA_VERSION
            or payload.get("event_id") != event_id
            or payload.get("signature_verified") is not True
            or not isinstance(payload.get("livemode"), bool)
            or not _is_sha256(payload.get("payload_sha256"))
            or set(payload) - _WEBHOOK_RECEIPT_ALLOWED_KEYS
            or not _WEBHOOK_RECEIPT_BASE_KEYS.issubset(payload)
            or (event_type is not None and payload.get("event_type") != event_type)
            or (
                payload_sha256 is not None
                and payload.get("payload_sha256") != payload_sha256
            )
            or (livemode is not None and payload.get("livemode") is not livemode)
            or (state is not None and payload.get("state") != state)
            or (tenant_id is not None and payload.get("tenant_id") != tenant_id)
        ):
            raise BillingEntitlementError(
                "signature-verified webhook receipt is absent or invalid"
            )
        _validate_webhook_receipt_payload(payload)
        _parse_datetime(
            _required_text(
                payload.get("signature_verified_at"),
                "webhook.signature_verified_at",
            )
        )
        return payload

    def require_webhook_refresh(
        self,
        *,
        event_id: str,
        external_subscription_id: str,
        refresh_lock_token: str,
        refresh_facts_sha256: str,
    ) -> Mapping[str, object]:
        payload = self.require_verified_webhook_event(event_id=event_id)
        if not _is_sha256(refresh_facts_sha256):
            raise BillingEntitlementError("provider refresh facts digest is invalid")
        resource_id = _subscription_refresh_resource_id(external_subscription_id)
        lease = self._store.get_lease(BILLING_PLATFORM_TENANT, resource_id)
        if lease is None or lease.token != refresh_lock_token:
            raise BillingEntitlementError("subscription refresh lock is not current")
        attempts = payload.get("provider_refreshes")
        if not isinstance(attempts, list):
            raise BillingEntitlementError("locked provider refresh receipt is absent")
        for candidate in reversed(attempts):
            if not isinstance(candidate, Mapping):
                continue
            facts = {
                key: candidate.get(key)
                for key in (
                    "external_subscription_id",
                    "refreshed_object_sha256",
                    "provider_request_id",
                    "refresh_resource_id",
                    "refresh_lock_token_sha256",
                    "refresh_fence",
                    "retrieved_at",
                )
            }
            if (
                candidate.get("refresh_facts_sha256") == refresh_facts_sha256
                and _canonical_sha256(facts) == refresh_facts_sha256
                and facts["external_subscription_id"] == external_subscription_id
                and facts["refresh_resource_id"] == resource_id
                and facts["refresh_lock_token_sha256"]
                == hashlib.sha256(refresh_lock_token.encode("utf-8")).hexdigest()
                and facts["refresh_fence"] == lease.fence
                and _is_sha256(facts["refreshed_object_sha256"])
            ):
                _parse_datetime(_required_text(facts["retrieved_at"], "refresh.retrieved_at"))
                return candidate
        raise BillingEntitlementError("locked provider refresh receipt is invalid")

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
    refresh_facts_sha256: str | None = None,
    locked_subscription_id: str | None = None,
    signature_verified: bool = False,
) -> dict[str, object]:
    """Durably apply one explicitly signature-verified Stripe route event."""
    signed_event = _strict_event_from_raw_payload(raw_payload)
    event_id = _strict_provider_text(signed_event.get("id"), "event.id")
    event_type = _strict_provider_text(signed_event.get("type"), "event.type")
    event_created = _nonnegative_int(
        signed_event.get("created"), "provider event created timestamp"
    )
    event_livemode = _strict_bool(
        signed_event.get("livemode"), "event.livemode"
    )
    signed_subscription_id: str | None = None
    if event_type in _SUBSCRIPTION_WEBHOOK_TYPES:
        signed_data = signed_event.get("data")
        signed_obj = (
            signed_data.get("object") if isinstance(signed_data, Mapping) else None
        )
        processed_data = event.get("data")
        processed_obj = (
            processed_data.get("object")
            if isinstance(processed_data, Mapping)
            else None
        )
        if not isinstance(signed_obj, Mapping) or not isinstance(
            processed_obj, Mapping
        ):
            raise BillingEntitlementError(
                "provider subscription event object is missing"
            )
        signed_subscription_id = _provider_reference_id(
            signed_obj.get("id"), "signed subscription.id"
        )
        expected_event = dict(signed_event)
        expected_data = dict(signed_data)
        expected_data["object"] = dict(processed_obj)
        expected_event["data"] = expected_data
        if _canonical_sha256(expected_event) != _canonical_sha256(event):
            raise BillingEventConflict(
                "processed provider event is not the exact locked-object substitution"
            )
    elif _canonical_sha256(signed_event) != _canonical_sha256(event):
        raise BillingEventConflict(
            "constructed provider event contradicts the exact signed payload"
        )
    event_payload_sha256 = hashlib.sha256(raw_payload).hexdigest()
    receipt, created = store.begin_webhook_event(
        event_id=event_id,
        event_type=event_type,
        event_created=event_created,
        raw_payload=raw_payload,
        livemode=event_livemode,
        signature_verified=signature_verified,
    )
    if not created and receipt.payload.get("state") == "applied":
        return {"event_id": event_id, "applied": False, "duplicate": True}
    try:
        store.require_verified_webhook_event(
            event_id=event_id,
            event_type=event_type,
            payload_sha256=event_payload_sha256,
        )
    except BillingEntitlementError as exc:
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail=str(exc),
        )
        raise

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
        tenant_id: str | None = None
        try:
            (
                tenant_id,
                billing_account_id,
                checkout_plan_id,
                checkout_request_id,
            ) = _checkout_lineage_metadata(obj)
            checkout_session_id = _strict_provider_text(
                obj.get("id"), "checkout.id"
            )
            if obj.get("mode") != "subscription":
                raise BillingEntitlementError(
                    "Stripe Checkout completion is not subscription mode"
                )
            checkout_livemode = _strict_bool(
                obj.get("livemode"), "checkout.livemode"
            )
            if checkout_livemode is not event_livemode:
                raise BillingEventConflict(
                    "Stripe Checkout object contradicts its event livemode"
                )
            if obj.get("client_reference_id") != tenant_id:
                raise BillingEventConflict(
                    "Stripe Checkout client reference contradicts its tenant"
                )
            customer_id = _provider_reference_id(
                obj.get("customer"), "checkout.customer"
            )
            subscription_id = _provider_reference_id(
                obj.get("subscription"), "checkout.subscription"
            )
            store.bind_signed_checkout_completion(
                tenant_id=tenant_id,
                billing_account_id=billing_account_id,
                plan_id=checkout_plan_id,
                request_id=checkout_request_id,
                checkout_session_id=checkout_session_id,
                external_customer_id=customer_id,
                external_subscription_id=subscription_id,
                checkout_event_id=event_id,
                checkout_event_payload_sha256=event_payload_sha256,
                checkout_livemode=checkout_livemode,
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
    object_subscription_id = _optional_provider_reference_id(obj.get("id"))
    bound_subscription_id = _optional_provider_reference_id(locked_subscription_id)
    subscription_id = bound_subscription_id or object_subscription_id
    tenant_id: str | None = None
    if (
        not resource_refreshed
        or not refresh_lock_token
        or not refresh_facts_sha256
        or not subscription_id
    ):
        message = (
            "subscription events require an exact locked refresh receipt of current provider state"
        )
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=None,
            detail=message,
        )
        raise BillingEntitlementError(message)
    try:
        if (
            object_subscription_id != subscription_id
            or signed_subscription_id != subscription_id
        ):
            raise BillingEventConflict(
                "signed/refreshed subscription identity contradicts the locked provider id"
            )
        refresh = store.require_webhook_refresh(
            event_id=event_id,
            external_subscription_id=subscription_id,
            refresh_lock_token=refresh_lock_token,
            refresh_facts_sha256=refresh_facts_sha256,
        )
        if refresh.get("refreshed_object_sha256") != _canonical_sha256(obj):
            raise BillingEventConflict(
                "processed subscription object contradicts the locked provider snapshot"
            )
        customer_id = _provider_reference_id(
            obj.get("customer"), "subscription.customer"
        )
        (
            metadata_tenant,
            billing_account_id,
            checkout_plan_id,
            checkout_request_id,
        ) = _checkout_lineage_metadata(obj)
        indexed_tenant = store.tenant_for_customer(customer_id)
        if indexed_tenant is not None and metadata_tenant != indexed_tenant:
            raise BillingEventConflict(
                "subscription metadata contradicts the customer tenant binding"
            )
        tenant_id = metadata_tenant
        store.require_checkout_subscription_lineage(
            tenant_id=tenant_id,
            billing_account_id=billing_account_id,
            plan_id=checkout_plan_id,
            request_id=checkout_request_id,
            external_customer_id=customer_id,
            external_subscription_id=subscription_id,
        )
        price_ids = _subscription_price_ids(obj)
        mapped_plan_items = [
            (price_id, price_to_plan[price_id])
            for price_id in price_ids
            if price_id in price_to_plan
        ]
        selected_price_id = (
            mapped_plan_items[0][0] if len(mapped_plan_items) == 1 else None
        )
        plan_id = mapped_plan_items[0][1] if len(mapped_plan_items) == 1 else None
        if plan_id is not None and plan_id != checkout_plan_id:
            raise BillingEventConflict(
                "Stripe subscription price contradicts the Checkout plan binding"
            )
        status = (
            "canceled"
            if event_type == "customer.subscription.deleted"
            else _subscription_status(obj.get("status"))
        )
        if status in {"active", "trialing"} and plan_id is None:
            reason = (
                "active provider subscription has multiple CAS plan prices"
                if len(mapped_plan_items) > 1
                else "active provider subscription price is not mapped to a plan"
            )
            raise BillingEntitlementError(reason)
        current_start, current_end = _subscription_period(
            obj, selected_price_id=selected_price_id
        )
        cancel_at_period_end = _strict_bool(
            obj.get("cancel_at_period_end", False),
            "subscription.cancel_at_period_end",
        )
        provenance = store.build_subscription_provenance(
            tenant_id=tenant_id,
            billing_account_id=billing_account_id,
            plan_id=checkout_plan_id,
            request_id=checkout_request_id,
            external_customer_id=customer_id,
            external_subscription_id=subscription_id,
            provider_event_id=event_id,
            provider_event_payload_sha256=event_payload_sha256,
            refresh_lock_token=refresh_lock_token,
            provider_refresh_facts_sha256=refresh_facts_sha256,
        )
        subscription, changed = store.apply_stripe_subscription(
            tenant_id=tenant_id,
            billing_account_id=billing_account_id,
            plan_id=plan_id,
            status=status,
            external_customer_id=customer_id,
            external_subscription_id=subscription_id,
            event_id=event_id,
            event_created=event_created,
            current_period_start=current_start,
            current_period_end=current_end,
            cancel_at_period_end=cancel_at_period_end,
            resource_refreshed=True,
            refresh_lock_token=refresh_lock_token,
            provenance=provenance,
            refreshed_object=obj,
            price_to_plan=price_to_plan,
            event_type=event_type,
        )
    except (BillingEntitlementError, ValueError, TypeError) as exc:
        message = (
            str(exc)
            if isinstance(exc, BillingEntitlementError)
            else "subscription period is invalid"
        )
        quarantined = store.quarantine_refreshed_subscription(
            external_subscription_id=subscription_id,
            event_id=event_id,
            event_created=event_created,
            detail=message,
            refresh_lock_token=refresh_lock_token,
            provider_event_payload_sha256=event_payload_sha256,
            provider_refresh_facts_sha256=refresh_facts_sha256,
        )
        if quarantined is not None:
            tenant_id = quarantined.tenant_id
        store.finish_webhook_event(
            event_id=event_id,
            state="unresolved",
            tenant_id=tenant_id,
            detail=message,
        )
        if isinstance(exc, BillingEntitlementError):
            raise
        raise BillingEntitlementError(message) from exc
    store.finish_webhook_event(
        event_id=event_id,
        state="applied",
        tenant_id=tenant_id,
        detail="subscription updated" if changed else "stale/duplicate event ignored",
        applied_subscription_facts_sha256=subscription_authority_facts_sha256(
            subscription
        ),
        external_subscription_id=subscription_id,
        refresh_lock_token=refresh_lock_token,
        refresh_fence=subscription.provider_refresh_fence,
    )
    return {
        "event_id": event_id,
        "applied": changed,
        "tenant_id": tenant_id,
        "plan_id": subscription.plan_id,
        "status": subscription.status,
    }


def _subscription_status(value: object) -> SubscriptionStatus:
    allowed = {
        "trialing",
        "active",
        "past_due",
        "incomplete",
        "incomplete_expired",
        "unpaid",
        "paused",
        "canceled",
    }
    if not isinstance(value, str) or value not in allowed:
        raise BillingEntitlementError(
            "provider subscription status is invalid"
        )
    return value  # type: ignore[return-value]


def _checkout_lineage_metadata(
    obj: Mapping[str, object],
) -> tuple[str, str, str, str]:
    metadata = obj.get("metadata")
    if not isinstance(metadata, Mapping):
        raise BillingEntitlementError("Stripe Checkout lineage metadata is missing")
    return (
        _strict_provider_text(
            metadata.get("cas_tenant_id"), "metadata.cas_tenant_id"
        ),
        _strict_provider_text(
            metadata.get("cas_account_id"), "metadata.cas_account_id"
        ),
        _strict_provider_text(
            metadata.get("cas_plan_id"), "metadata.cas_plan_id"
        ),
        _strict_provider_text(
            metadata.get("cas_checkout_request_id"),
            "metadata.cas_checkout_request_id",
        ),
    )


def _optional_provider_reference_id(value: object) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("id")
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text == value and text else None


def _strict_provider_text(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise BillingEntitlementError(f"{field} is invalid")
    return value


def _provider_reference_id(value: object, field: str) -> str:
    reference = _optional_provider_reference_id(value)
    if reference is None:
        raise BillingEntitlementError(f"{field} is required")
    return reference


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
    value = price.get("id") if isinstance(price, Mapping) else price
    if value is None:
        return None
    return _strict_provider_text(value, "subscription.price.id")


def _subscription_period(
    obj: Mapping[str, object], *, selected_price_id: str | None
) -> tuple[str | None, str | None]:
    top_start = obj.get("current_period_start")
    top_end = obj.get("current_period_end")
    if (top_start is None) != (top_end is None):
        raise BillingEntitlementError(
            "subscription top-level period is partial"
        )
    top_period = (
        (_unix_or_iso(top_start), _unix_or_iso(top_end))
        if top_start is not None and top_end is not None
        else None
    )

    item_periods: list[tuple[str | None, str | None]] = []
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
            if row_start is None and row_end is None:
                continue
            if (row_start is None) != (row_end is None):
                raise BillingEntitlementError(
                    "subscription item period is partial"
                )
            item_periods.append(
                (_unix_or_iso(row_start), _unix_or_iso(row_end))
            )
    if len(set(item_periods)) > 1:
        raise BillingEntitlementError(
            "subscription item periods are contradictory"
        )
    item_period = item_periods[0] if item_periods else None
    if top_period is not None and item_period is not None and top_period != item_period:
        raise BillingEntitlementError(
            "subscription top-level and item periods are contradictory"
        )
    return top_period or item_period or (None, None)


def _unix_or_iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=UTC).isoformat()
        except (OverflowError, OSError, ValueError) as exc:
            raise BillingEntitlementError(
                "subscription period timestamp is outside the supported range"
            ) from exc
    if not isinstance(value, str):
        raise BillingEntitlementError(
            "subscription period timestamp must be an integer or aware ISO time"
        )
    text = value.strip()
    if not text:
        return None
    return _parse_datetime(text).isoformat()


def _customer_index_id(external_customer_id: str) -> str:
    return "cus-" + hashlib.sha256(external_customer_id.encode("utf-8")).hexdigest()


def _subscription_index_id(external_subscription_id: str) -> str:
    return "sub-" + hashlib.sha256(
        external_subscription_id.encode("utf-8")
    ).hexdigest()


def _checkout_session_index_id(checkout_session_id: str) -> str:
    return "checkout-" + hashlib.sha256(
        checkout_session_id.encode("utf-8")
    ).hexdigest()


def _checkout_subscription_index_id(external_subscription_id: str) -> str:
    return "checkout-subscription-" + hashlib.sha256(
        external_subscription_id.encode("utf-8")
    ).hexdigest()


def _checkout_completion_record_matches(
    record: LedgerRecord | None,
    *,
    record_id: str,
    payload: Mapping[str, object],
) -> bool:
    return bool(
        record is not None
        and record.version == 1
        and record.tenant_id == BILLING_PLATFORM_TENANT
        and record.kind == CHECKOUT_COMPLETION_INDEX_KIND
        and record.record_id == record_id
        and not record.parent_ids
        and record.source == "billing.checkout_completion_index"
        and record.trace_id == payload.get("request_id")
        and dict(record.payload) == dict(payload)
    )


def _subscription_refresh_resource_id(external_subscription_id: str) -> str:
    digest = hashlib.sha256(external_subscription_id.encode("utf-8")).hexdigest()
    return "billing-subscription-refresh-" + digest


def _parse_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("timestamp must be a non-empty exact string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def subscription_period_is_live(
    subscription: SubscriptionRecord, *, now: datetime | None = None
) -> bool:
    """Return true only for one coherent aware half-open current period."""

    clock = now or datetime.now(UTC)
    if clock.tzinfo is None or clock.utcoffset() is None:
        return False
    if not subscription.current_period_start or not subscription.current_period_end:
        return False
    try:
        start = _parse_datetime(subscription.current_period_start)
        end = _parse_datetime(subscription.current_period_end)
    except (TypeError, ValueError):
        return False
    clock = clock.astimezone(UTC)
    return start < end and start <= clock < end


def subscription_status_period_is_current(
    subscription: SubscriptionRecord, *, now: datetime | None = None
) -> bool:
    """Apply the shared status and aware half-open-period invariant."""

    return (
        subscription.status in {"active", "trialing"}
        and subscription_period_is_live(subscription, now=now)
    )


def subscription_is_live(
    subscription: SubscriptionRecord, *, now: datetime | None = None
) -> bool:
    """Authorize customer live access only for production-mode provider state."""

    return subscription_status_period_is_current(
        subscription, now=now
    ) and (
        subscription.source != "stripe_verified"
        or subscription.provider_livemode is True
    )


def subscription_authority_facts_sha256(
    subscription: SubscriptionRecord,
) -> str:
    """Digest all mutable authority facts except presentation/update metadata."""

    return _canonical_sha256(
        {
            "tenant_id": subscription.tenant_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "source": subscription.source,
            "billing_account_id": subscription.billing_account_id,
            "external_customer_id": subscription.external_customer_id,
            "external_subscription_id": subscription.external_subscription_id,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "provider_event_id": subscription.provider_event_id,
            "provider_event_created": subscription.provider_event_created,
            "checkout_request_id": subscription.checkout_request_id,
            "checkout_session_id": subscription.checkout_session_id,
            "checkout_event_id": subscription.checkout_event_id,
            "checkout_event_payload_sha256": (
                subscription.checkout_event_payload_sha256
            ),
            "checkout_lineage_sha256": subscription.checkout_lineage_sha256,
            "provider_event_payload_sha256": (
                subscription.provider_event_payload_sha256
            ),
            "provider_refresh_facts_sha256": (
                subscription.provider_refresh_facts_sha256
            ),
            "provider_refreshed_object_sha256": (
                subscription.provider_refreshed_object_sha256
            ),
            "provider_refresh_fence": subscription.provider_refresh_fence,
            "provider_livemode": subscription.provider_livemode,
            "quarantine_reason": subscription.quarantine_reason,
        }
    )


def _require_stored_refresh_facts(
    receipt: Mapping[str, object],
    *,
    external_subscription_id: str,
    refresh_facts_sha256: str,
) -> Mapping[str, object]:
    attempts = receipt.get("provider_refreshes")
    if not isinstance(attempts, list):
        raise BillingEntitlementError("provider refresh provenance is absent")
    for candidate in reversed(attempts):
        if not isinstance(candidate, Mapping):
            continue
        facts = {
            key: candidate.get(key)
            for key in (
                "external_subscription_id",
                "refreshed_object_sha256",
                "provider_request_id",
                "refresh_resource_id",
                "refresh_lock_token_sha256",
                "refresh_fence",
                "retrieved_at",
            )
        }
        if (
            candidate.get("refresh_facts_sha256") == refresh_facts_sha256
            and _canonical_sha256(facts) == refresh_facts_sha256
            and facts["external_subscription_id"] == external_subscription_id
            and facts["refresh_resource_id"]
            == _subscription_refresh_resource_id(external_subscription_id)
            and _is_sha256(facts["refreshed_object_sha256"])
            and _is_sha256(facts["refresh_lock_token_sha256"])
            and isinstance(facts["refresh_fence"], int)
            and not isinstance(facts["refresh_fence"], bool)
            and int(facts["refresh_fence"]) >= 0
        ):
            _parse_datetime(_required_text(facts["retrieved_at"], "refresh.retrieved_at"))
            return candidate
    raise BillingEntitlementError("provider refresh provenance is invalid")


def _validate_webhook_receipt_payload(payload: Mapping[str, object]) -> None:
    keys = set(payload)
    if (
        not _WEBHOOK_RECEIPT_BASE_KEYS.issubset(keys)
        or keys - _WEBHOOK_RECEIPT_ALLOWED_KEYS
    ):
        raise BillingEntitlementError("webhook receipt schema is invalid")
    state = _required_text(payload.get("state"), "webhook.state")
    if state not in {"received", "applied", "ignored", "unresolved"}:
        raise BillingEntitlementError("webhook receipt state is invalid")
    _parse_datetime(
        _required_text(payload.get("received_at"), "webhook.received_at")
    )
    event_type = _required_text(payload.get("event_type"), "webhook.event_type")
    _nonnegative_int(payload.get("event_created"), "webhook.event_created")
    terminal = state in {"applied", "ignored", "unresolved"}
    if terminal:
        if not _WEBHOOK_TERMINAL_KEYS.issubset(keys):
            raise BillingEntitlementError(
                "terminal webhook receipt facts are incomplete"
            )
        _required_text(payload.get("detail"), "webhook.detail")
        _parse_datetime(
            _required_text(payload.get("finished_at"), "webhook.finished_at")
        )
        tenant_id = payload.get("tenant_id")
        if tenant_id is not None:
            _required_text(tenant_id, "webhook.tenant_id")
    elif keys & _WEBHOOK_TERMINAL_KEYS:
        raise BillingEntitlementError(
            "nonterminal webhook receipt has terminal facts"
        )

    has_refreshes = "provider_refreshes" in keys
    has_applied_facts = "applied_subscription_facts_sha256" in keys
    attempt_keys = keys & _WEBHOOK_SUBSCRIPTION_ATTEMPT_KEYS
    if attempt_keys:
        if (
            attempt_keys != _WEBHOOK_SUBSCRIPTION_ATTEMPT_KEYS
            or event_type not in _SUBSCRIPTION_WEBHOOK_TYPES
        ):
            raise BillingEntitlementError(
                "subscription webhook attempt claim is incomplete"
            )
        subscription_id = _strict_provider_text(
            payload.get("external_subscription_id"),
            "webhook.external_subscription_id",
        )
        if (
            payload.get("subscription_refresh_resource_id")
            != _subscription_refresh_resource_id(subscription_id)
            or not _is_sha256(
                payload.get("subscription_refresh_lock_token_sha256")
            )
            or not isinstance(payload.get("subscription_refresh_fence"), int)
            or isinstance(payload.get("subscription_refresh_fence"), bool)
            or int(payload.get("subscription_refresh_fence")) < 0
        ):
            raise BillingEntitlementError(
                "subscription webhook attempt claim is invalid"
            )
    if has_refreshes:
        attempts = payload.get("provider_refreshes")
        if (
            event_type not in _SUBSCRIPTION_WEBHOOK_TYPES
            or not isinstance(attempts, list)
            or not attempts
            or any(
                not isinstance(candidate, Mapping)
                or set(candidate) != _WEBHOOK_REFRESH_KEYS
                for candidate in attempts
            )
        ):
            raise BillingEntitlementError(
                "provider refresh receipt schema is invalid"
            )
    if has_applied_facts and not _is_sha256(
        payload.get("applied_subscription_facts_sha256")
    ):
        raise BillingEntitlementError(
            "applied subscription facts digest is invalid"
        )
    if state == "applied" and event_type in _SUBSCRIPTION_WEBHOOK_TYPES:
        if (
            not has_refreshes
            or not has_applied_facts
            or attempt_keys != _WEBHOOK_SUBSCRIPTION_ATTEMPT_KEYS
        ):
            raise BillingEntitlementError(
                "applied subscription receipt facts are incomplete"
            )
    elif has_applied_facts:
        raise BillingEntitlementError(
            "non-subscription receipt has applied subscription facts"
        )
    if event_type == "checkout.session.completed" and has_refreshes:
        raise BillingEntitlementError(
            "Checkout receipt cannot contain subscription refresh facts"
        )


def _canonical_sha256(value: Mapping[str, object]) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise BillingEntitlementError("billing facts are not strict canonical JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _required_sha256(value: object, field: str) -> str:
    if not _is_sha256(value):
        raise BillingEntitlementError(f"{field} is invalid")
    return str(value)


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
    if isinstance(value, bool):
        raise BillingEntitlementError(f"{field} is invalid")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BillingEntitlementError(f"{field} is invalid") from exc
    if parsed < 0:
        raise BillingEntitlementError(f"{field} cannot be negative")
    return parsed


def _strict_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise BillingEntitlementError(f"{field} must be boolean")
    return value


def canonical_event_bytes(event: Mapping[str, Any]) -> bytes:
    """Stable bytes for tests or non-SDK event replay receipts."""
    return json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_constructed_stripe_event(
    event: Mapping[str, Any], raw_payload: bytes
) -> Mapping[str, object]:
    """Require the provider adapter's event to be the exact signed JSON value."""

    signed_event = _strict_event_from_raw_payload(raw_payload)
    if _canonical_sha256(signed_event) != _canonical_sha256(event):
        raise BillingEventConflict(
            "constructed provider event contradicts the exact signed payload"
        )
    return signed_event


def _strict_event_from_raw_payload(raw_payload: bytes) -> Mapping[str, object]:
    try:
        parsed = json.loads(
            raw_payload.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_strict_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise BillingEntitlementError(
            "signed provider payload is not strict JSON"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise BillingEntitlementError(
            "signed provider payload must contain one event object"
        )
    return parsed


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant {value}")


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result
