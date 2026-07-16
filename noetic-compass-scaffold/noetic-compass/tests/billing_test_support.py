"""Test-only builders for the full durable Stripe subscription lineage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib

from api.services.billing_entitlements import (
    BillingEntitlementStore,
    SubscriptionRecord,
    canonical_event_bytes,
    process_stripe_event,
)


def install_verified_stripe_subscription(
    entitlements: BillingEntitlementStore,
    *,
    tenant_id: str = "tenant-a",
    billing_account_id: str = "acct-a",
    customer_id: str = "cus_CustomerA",
    subscription_id: str = "sub_SubscriptionA",
    plan_id: str = "professional_live",
    price_id: str = "price_ProfessionalLive",
    status: str = "active",
    livemode: bool = True,
    event_id: str | None = None,
    event_created: int | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    checkout_now: datetime | None = None,
) -> tuple[SubscriptionRecord, dict[str, object]]:
    """Install a subscription only through the production receipt/refresh path."""

    clock = datetime.now(UTC).replace(microsecond=0)
    start = period_start or (clock - timedelta(days=1))
    end = period_end or (clock + timedelta(days=30))
    lineage_digest = hashlib.sha256(
        "\x00".join(
            (
                tenant_id,
                billing_account_id,
                customer_id,
                subscription_id,
                plan_id,
            )
        ).encode("utf-8")
    ).hexdigest()[:24]
    request_id = f"request_test_{lineage_digest}"
    session_id = f"cs_test_{lineage_digest}"
    checkout_event_id = f"evt_checkout_test_{lineage_digest}"
    provider_event_id = event_id or f"evt_subscription_test_{lineage_digest}"
    metadata = {
        "cas_tenant_id": tenant_id,
        "cas_account_id": billing_account_id,
        "cas_plan_id": plan_id,
        "cas_checkout_request_id": request_id,
    }

    entitlements.begin_checkout_intent(
        tenant_id=tenant_id,
        billing_account_id=billing_account_id,
        plan_id=plan_id,
        request_id=request_id,
        now=checkout_now,
    )
    entitlements.finish_checkout_intent(
        tenant_id=tenant_id,
        request_id=request_id,
        checkout_session_id=session_id,
        url=f"https://checkout.stripe.test/{session_id}",
    )
    checkout_event: dict[str, object] = {
        "id": checkout_event_id,
        "type": "checkout.session.completed",
        "created": 1,
        "livemode": livemode,
        "data": {
            "object": {
                "id": session_id,
                "customer": customer_id,
                "subscription": subscription_id,
                "mode": "subscription",
                "livemode": livemode,
                "client_reference_id": tenant_id,
                "metadata": metadata,
            }
        },
    }
    process_stripe_event(
        entitlements,
        event=checkout_event,
        raw_payload=canonical_event_bytes(checkout_event),
        price_to_plan={price_id: plan_id},
        signature_verified=True,
    )

    subscription_object: dict[str, object] = {
        "id": subscription_id,
        "customer": customer_id,
        "livemode": livemode,
        "status": status,
        "metadata": metadata,
        "items": {
            "data": [
                {
                    "price": {"id": price_id},
                    "current_period_start": start.isoformat(),
                    "current_period_end": end.isoformat(),
                }
            ]
        },
        "cancel_at_period_end": False,
    }
    subscription_event: dict[str, object] = {
        "id": provider_event_id,
        "type": "customer.subscription.updated",
        "livemode": livemode,
        "created": (
            int(clock.timestamp()) if event_created is None else event_created
        ),
        "data": {"object": subscription_object},
    }
    raw_payload = canonical_event_bytes(subscription_event)
    entitlements.begin_webhook_event(
        event_id=provider_event_id,
        event_type="customer.subscription.updated",
        event_created=int(subscription_event["created"]),
        raw_payload=raw_payload,
        livemode=livemode,
        signature_verified=True,
    )
    lease = entitlements.acquire_subscription_refresh_lock(
        external_subscription_id=subscription_id,
        event_id=provider_event_id,
    )
    try:
        refresh_facts_sha256 = entitlements.record_webhook_refresh(
            event_id=provider_event_id,
            external_subscription_id=subscription_id,
            refreshed_object=subscription_object,
            provider_request_id=f"req_{provider_event_id}",
            refresh_lock_token=lease.token,
        )
        result = process_stripe_event(
            entitlements,
            event=subscription_event,
            raw_payload=raw_payload,
            price_to_plan={price_id: plan_id},
            resource_refreshed=True,
            refresh_lock_token=lease.token,
            refresh_facts_sha256=refresh_facts_sha256,
            locked_subscription_id=subscription_id,
            signature_verified=True,
        )
    finally:
        entitlements.release_subscription_refresh_lock(lease)
    subscription = entitlements.get_subscription(tenant_id)
    assert subscription is not None
    return subscription, result
