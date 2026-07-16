from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib

import pytest

from api.services.billing_entitlements import (
    BILLING_PLATFORM_TENANT,
    SUBSCRIPTION_KIND,
    SUBSCRIPTION_RECORD_ID,
    WEBHOOK_EVENT_KIND,
    BillingEntitlementError,
    BillingEntitlementStore,
    BillingEventConflict,
    PLAN_CATALOG,
    SubscriptionRecord,
    canonical_event_bytes,
    process_stripe_event,
    subscription_authority_facts_sha256,
    subscription_is_live,
)
from api.services.production.state_substrate import (
    InMemoryStateStore,
    LedgerRecord,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


def _future(days: int = 30) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _event(
    event_id: str,
    *,
    created: int = 100,
    tenant_id: str = "tenant-a",
    account_id: str = "acct-a",
    customer_id: str = "cus_a",
    subscription_id: str = "sub_a",
    status: str = "active",
    price_id: str = "price_pro",
    checkout_request_id: str = "request_0123456789",
    livemode: bool = True,
) -> dict[str, object]:
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "created": created,
        "livemode": livemode,
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "livemode": livemode,
                "status": status,
                "metadata": {
                    "cas_tenant_id": tenant_id,
                    "cas_account_id": account_id,
                    "cas_plan_id": "professional_live",
                    "cas_checkout_request_id": checkout_request_id,
                },
                "items": {
                    "data": [
                        {
                            "price": {"id": price_id},
                            "current_period_start": 1_700_000_000,
                            "current_period_end": 4_000_000_000,
                        }
                    ]
                },
                "cancel_at_period_end": False,
            }
        },
    }


def _checkout_completion_event(
    event_id: str,
    *,
    tenant_id: str = "tenant-a",
    account_id: str = "acct-a",
    customer_id: str = "cus_a",
    subscription_id: str = "sub_a",
    plan_id: str = "professional_live",
    checkout_request_id: str = "request_0123456789",
    checkout_session_id: str | None = None,
    livemode: bool = True,
) -> dict[str, object]:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "created": 99,
        "livemode": livemode,
        "data": {
            "object": {
                "id": checkout_session_id or f"cs_{checkout_request_id}",
                "customer": customer_id,
                "subscription": subscription_id,
                "mode": "subscription",
                "livemode": livemode,
                "client_reference_id": tenant_id,
                "metadata": {
                    "cas_tenant_id": tenant_id,
                    "cas_account_id": account_id,
                    "cas_plan_id": plan_id,
                    "cas_checkout_request_id": checkout_request_id,
                },
            }
        },
    }


def _apply(
    store: BillingEntitlementStore,
    *,
    event_id: str = "evt_1",
    created: int = 100,
    tenant_id: str = "tenant-a",
    billing_account_id: str = "acct-a",
    customer_id: str = "cus_a",
    subscription_id: str = "sub_a",
    plan_id: str | None = "professional_live",
    status: str = "active",
    livemode: bool = True,
) -> tuple[SubscriptionRecord, bool]:
    event = _event(
        event_id,
        created=created,
        tenant_id=tenant_id,
        account_id=billing_account_id,
        customer_id=customer_id,
        subscription_id=subscription_id,
        status=status,
        price_id="price_pro" if plan_id is not None else "price_unknown",
        checkout_request_id=f"request_{tenant_id}_{subscription_id}",
        livemode=livemode,
    )
    result = _process(
        store,
        event=event,
        raw_payload=canonical_event_bytes(event),
        price_to_plan=(
            {"price_pro": plan_id} if plan_id is not None else {}
        ),
    )
    subscription = store.get_subscription(tenant_id)
    assert subscription is not None
    return subscription, bool(result["applied"])


def _process(
    store: BillingEntitlementStore,
    *,
    event: dict[str, object],
    raw_payload: bytes,
    price_to_plan: dict[str, str],
    ensure_checkout_lineage: bool = True,
) -> dict[str, object]:
    obj = event["data"]["object"]  # type: ignore[index]
    metadata = obj.get("metadata")  # type: ignore[union-attr]
    if ensure_checkout_lineage and isinstance(metadata, dict):
        tenant_id = str(metadata.get("cas_tenant_id") or "")
        account_id = str(metadata.get("cas_account_id") or "")
        plan_id = str(metadata.get("cas_plan_id") or "")
        request_id = str(metadata.get("cas_checkout_request_id") or "")
        if all((tenant_id, account_id, plan_id, request_id)):
            store.begin_checkout_intent(
                tenant_id=tenant_id,
                billing_account_id=account_id,
                plan_id=plan_id,
                request_id=request_id,
            )
            store.finish_checkout_intent(
                tenant_id=tenant_id,
                request_id=request_id,
                checkout_session_id=f"cs_{request_id}",
                url=f"https://checkout.stripe.test/{request_id}",
            )
            completion = _checkout_completion_event(
                f"evt_checkout_{tenant_id}_{obj.get('id')}",
                tenant_id=tenant_id,
                account_id=account_id,
                customer_id=str(obj.get("customer") or ""),
                subscription_id=str(obj.get("id") or ""),
                plan_id=plan_id,
                checkout_request_id=request_id,
                checkout_session_id=f"cs_{request_id}",
                livemode=bool(event.get("livemode")),
            )
            process_stripe_event(
                store,
                event=completion,
                raw_payload=canonical_event_bytes(completion),
                price_to_plan=price_to_plan,
                signature_verified=True,
            )
    subscription_id = str(obj["id"])  # type: ignore[index]
    receipt, created = store.begin_webhook_event(
        event_id=str(event["id"]),
        event_type=str(event["type"]),
        event_created=int(event["created"]),
        raw_payload=raw_payload,
        livemode=bool(event.get("livemode")),
        signature_verified=True,
    )
    if not created and receipt.payload.get("state") == "applied":
        return process_stripe_event(
            store,
            event=event,
            raw_payload=raw_payload,
            price_to_plan=price_to_plan,
            signature_verified=True,
        )
    lease = store.acquire_subscription_refresh_lock(
        external_subscription_id=subscription_id,
        event_id=str(event["id"]),
    )
    try:
        refresh_facts_sha256 = store.record_webhook_refresh(
            event_id=str(event["id"]),
            external_subscription_id=subscription_id,
            refreshed_object=obj,  # type: ignore[arg-type]
            provider_request_id=f"req_{event['id']}",
            refresh_lock_token=lease.token,
        )
        return process_stripe_event(
            store,
            event=event,
            raw_payload=raw_payload,
            price_to_plan=price_to_plan,
            resource_refreshed=True,
            refresh_lock_token=lease.token,
            refresh_facts_sha256=refresh_facts_sha256,
            locked_subscription_id=subscription_id,
            signature_verified=True,
        )
    finally:
        store.release_subscription_refresh_lock(lease)


def test_plan_catalog_does_not_claim_unreleased_capabilities() -> None:
    assert PLAN_CATALOG["free_reference"].monthly_audit_limit == 0
    assert PLAN_CATALOG["beta_comped"].paid is False
    assert PLAN_CATALOG["beta_comped"].checkout_available is False
    assert PLAN_CATALOG["professional_live"].paid is True
    assert PLAN_CATALOG["enterprise_live"].distributed_audit is False
    assert PLAN_CATALOG["enterprise_live"].reserved_gpu is False
    assert PLAN_CATALOG["enterprise_live"].checkout_available is False


def test_missing_subscription_is_free_reference_without_live_access() -> None:
    decision = BillingEntitlementStore(InMemoryStateStore()).resolve_entitlement(
        "tenant-a"
    )
    assert decision.plan.plan_id == "free_reference"
    assert decision.active is True
    assert decision.can_run_live_audit is False
    assert decision.subscription_source == "none"


def test_manual_comped_grant_is_expiring_and_never_paid() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    record = store.grant_manual_comped(
        tenant_id="tenant-a",
        billing_account_id="acct-owner",
        expires_at=_future(2),
    )
    active = store.resolve_entitlement("tenant-a")
    expired = store.resolve_entitlement(
        "tenant-a", now=datetime.now(UTC) + timedelta(days=3)
    )
    assert record.source == "manual_comped"
    assert active.plan.plan_id == "beta_comped"
    assert active.plan.paid is False
    assert active.can_run_live_audit is True
    assert expired.plan.plan_id == "free_reference"
    assert expired.can_run_live_audit is False


def test_manual_grant_cannot_overwrite_active_verified_stripe() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store)
    with pytest.raises(BillingEventConflict):
        store.grant_manual_comped(
            tenant_id="tenant-a",
            billing_account_id="acct-owner",
            expires_at=_future(),
        )
    subscription = store.get_subscription("tenant-a")
    assert subscription is not None
    assert subscription.source == "stripe_verified"


def test_stripe_status_and_expiry_fail_closed() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store, event_id="evt_active", created=1)
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True
    _apply(store, event_id="evt_past_due", created=2, status="past_due")
    decision = store.resolve_entitlement("tenant-a")
    assert decision.subscription_status == "past_due"
    assert decision.plan.plan_id == "free_reference"
    assert decision.can_run_live_audit is False


def test_shared_status_and_aware_half_open_period_invariant() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    subscription, _ = _apply(store)
    now = datetime.now(UTC).replace(microsecond=0)

    at_start = replace(
        subscription,
        current_period_start=now.isoformat(),
        current_period_end=(now + timedelta(seconds=1)).isoformat(),
    )
    assert subscription_is_live(at_start, now=now) is True

    at_end = replace(
        subscription,
        current_period_start=(now - timedelta(seconds=1)).isoformat(),
        current_period_end=now.isoformat(),
    )
    assert subscription_is_live(at_end, now=now) is False

    future = replace(
        subscription,
        current_period_start=(now + timedelta(seconds=1)).isoformat(),
        current_period_end=(now + timedelta(seconds=2)).isoformat(),
    )
    assert subscription_is_live(future, now=now) is False
    assert subscription_is_live(replace(subscription, status="past_due"), now=now) is False
    with pytest.raises(BillingEntitlementError, match="timezone-aware"):
        replace(
            subscription,
            current_period_start=now.replace(tzinfo=None).isoformat(),
        )


def test_direct_subscription_apply_without_durable_lineage_is_refused() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    now = datetime.now(UTC)
    with pytest.raises(BillingEntitlementError, match="provenance"):
        store.apply_stripe_subscription(
            tenant_id="tenant-a",
            billing_account_id="acct-a",
            plan_id="professional_live",
            status="active",
            external_customer_id="cus_a",
            external_subscription_id="sub_a",
            event_id="evt_direct",
            event_created=1,
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=30)).isoformat(),
            cancel_at_period_end=False,
        )
    assert store.get_subscription("tenant-a") is None


def test_locked_current_snapshot_supersedes_delivery_timestamp_order() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store, event_id="evt_new", created=200, status="canceled")
    record, changed = _apply(
        store, event_id="evt_old", created=100, status="active"
    )
    assert changed is True
    assert record.provider_event_id == "evt_old"
    assert record.status == "active"


def test_same_second_events_use_locked_current_resource_not_event_id_order() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store, event_id="evt_z", created=100, status="active")
    record, changed = _apply(
        store, event_id="evt_a", created=100, status="canceled"
    )
    assert changed is True
    assert record.status == "canceled"
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False


def test_active_stripe_without_period_end_is_structurally_invalid() -> None:
    with pytest.raises(BillingEntitlementError, match="exact current period"):
        SubscriptionRecord(
            tenant_id="tenant-a",
            plan_id="professional_live",
            status="active",
            source="stripe_verified",
            billing_account_id="acct-a",
            external_customer_id="cus_a",
            external_subscription_id="sub_a",
            provider_event_id="evt_a",
            provider_event_created=1,
        )


def test_persisted_subscription_schema_and_key_tenant_are_verified() -> None:
    backend = InMemoryStateStore()
    valid = SubscriptionRecord(
        tenant_id="tenant-b",
        plan_id="professional_live",
        status="active",
        source="stripe_verified",
        billing_account_id="acct-a",
        external_customer_id="cus_a",
        external_subscription_id="sub_a",
        current_period_start=datetime.now(UTC).isoformat(),
        current_period_end=_future(),
        provider_event_id="evt_a",
        provider_event_created=1,
        checkout_request_id="request_a",
        checkout_session_id="cs_a",
        checkout_event_id="evt_checkout",
        checkout_event_payload_sha256="a" * 64,
        checkout_lineage_sha256="b" * 64,
        provider_event_payload_sha256="c" * 64,
            provider_refresh_facts_sha256="d" * 64,
            provider_refreshed_object_sha256="e" * 64,
            provider_livemode=True,
        )
    backend.put(
        LedgerRecord.new(
            tenant_id="tenant-a",
            kind=SUBSCRIPTION_KIND,
            record_id=SUBSCRIPTION_RECORD_ID,
            payload=valid.to_payload(),
        ),
        expected_version=0,
    )
    with pytest.raises(BillingEventConflict, match="tenant"):
        BillingEntitlementStore(backend).get_subscription("tenant-a")


class _WriteConflictStore(InMemoryStateStore):
    """Inject a newer provider record immediately before the first old write."""

    def __init__(self) -> None:
        super().__init__()
        self.armed = True

    def put(self, record: LedgerRecord, *, expected_version: int) -> LedgerRecord:
        if (
            self.armed
            and record.kind == SUBSCRIPTION_KIND
            and record.record_id == SUBSCRIPTION_RECORD_ID
        ):
            self.armed = False
            payload = dict(record.payload)
            payload.update(
                {
                    "status": "canceled",
                    "provider_event_id": "evt_newer",
                    "provider_event_created": 999,
                }
            )
            newer = LedgerRecord.new(
                tenant_id=record.tenant_id,
                kind=record.kind,
                record_id=record.record_id,
                payload=payload,
                source="test.concurrent_newer_event",
                trace_id="evt_newer",
            )
            super().put(newer, expected_version=0)
        return super().put(record, expected_version=expected_version)


def test_write_conflict_rechecks_locked_current_snapshot_on_retry() -> None:
    store = BillingEntitlementStore(_WriteConflictStore())
    record, changed = _apply(store, event_id="evt_old", created=1)
    assert changed is True
    assert record.provider_event_id == "evt_old"
    assert record.status == "active"


def test_customer_id_is_bound_to_exactly_one_tenant() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store, tenant_id="tenant-a", customer_id="cus_shared")
    with pytest.raises(BillingEventConflict):
        _apply(
            store,
            event_id="evt_other",
            tenant_id="tenant-b",
            customer_id="cus_shared",
            subscription_id="sub_b",
        )
    assert store.get_subscription("tenant-b") is None


def test_subscription_id_cannot_be_rebound_to_another_customer_or_tenant() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store, tenant_id="tenant-a", customer_id="cus_a", subscription_id="sub_shared")
    with pytest.raises(BillingEventConflict, match="subscription id"):
        _apply(
            store,
            event_id="evt_rebind",
            created=2,
            tenant_id="tenant-b",
            customer_id="cus_b",
            subscription_id="sub_shared",
        )
    assert store.get_subscription("tenant-b") is None


def test_unknown_active_price_revokes_old_grant_and_stays_unresolved() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    first = _event("evt_known", created=100)
    _process(
        store,
        event=first,
        raw_payload=canonical_event_bytes(first),
        price_to_plan={"price_pro": "professional_live"},
    )
    unknown = _event("evt_unknown", created=101, price_id="price_unknown")
    raw = canonical_event_bytes(unknown)
    with pytest.raises(BillingEntitlementError, match="not mapped"):
        _process(store, event=unknown, raw_payload=raw, price_to_plan={})
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False
    receipt = store._store.get(  # noqa: SLF001 - receipt attribution assertion
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_unknown"
    )
    assert receipt is not None
    assert receipt.payload["tenant_id"] == "tenant-a"
    repaired = _process(
        store,
        event=unknown,
        raw_payload=raw,
        price_to_plan={"price_unknown": "professional_live"},
    )
    assert repaired["applied"] is True
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True


def test_plan_price_can_follow_an_unmapped_add_on_but_two_plans_fail_closed() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    event = _event("evt_addon_first")
    rows = event["data"]["object"]["items"]["data"]  # type: ignore[index]
    rows.insert(0, {"price": {"id": "price_addon"}})
    result = _process(
        store,
        event=event,
        raw_payload=canonical_event_bytes(event),
        price_to_plan={"price_pro": "professional_live"},
    )
    assert result["plan_id"] == "professional_live"

    ambiguous = _event("evt_two_plans", created=101)
    ambiguous_rows = ambiguous["data"]["object"]["items"]["data"]  # type: ignore[index]
    ambiguous_rows.append({"price": {"id": "price_ent"}})
    with pytest.raises(BillingEntitlementError, match="multiple CAS plan prices"):
        _process(
            store,
            event=ambiguous,
            raw_payload=canonical_event_bytes(ambiguous),
            price_to_plan={
                "price_pro": "professional_live",
                "price_ent": "enterprise_live",
            },
        )
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False


def test_checkout_intent_is_single_tenant_durable_and_idempotent() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    first, created = store.begin_checkout_intent(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
    )
    assert created is True
    same, created_again = store.begin_checkout_intent(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
    )
    assert created_again is False
    assert same["request_id"] == first["request_id"]
    with pytest.raises(BillingEventConflict, match="already exists"):
        store.begin_checkout_intent(
            tenant_id="tenant-a",
            billing_account_id="acct-a",
            plan_id="professional_live",
            request_id="different_0123456789",
        )
    completed = store.finish_checkout_intent(
        tenant_id="tenant-a",
        request_id="request_0123456789",
        checkout_session_id="cs_server",
        url="https://checkout.stripe.com/c/pay/cs_server",
    )
    assert completed["state"] == "completed"


def test_first_time_checkout_completion_creates_account_bound_stripe_subscription() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    store.begin_checkout_intent(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
    )
    store.finish_checkout_intent(
        tenant_id="tenant-a",
        request_id="request_0123456789",
        checkout_session_id="cs_request_0123456789",
        url="https://checkout.stripe.test/request_0123456789",
    )
    completion = _checkout_completion_event("evt_checkout_complete")
    completed = process_stripe_event(
        store,
        event=completion,
        raw_payload=canonical_event_bytes(completion),
        price_to_plan={"price_pro": "professional_live"},
        signature_verified=True,
    )
    assert completed == {
        "event_id": "evt_checkout_complete",
        "applied": True,
        "tenant_id": "tenant-a",
    }

    subscription_event = _event("evt_first_subscription")
    applied = _process(
        store,
        event=subscription_event,
        raw_payload=canonical_event_bytes(subscription_event),
        price_to_plan={"price_pro": "professional_live"},
        ensure_checkout_lineage=False,
    )
    subscription = store.get_subscription("tenant-a")
    assert applied["applied"] is True
    assert subscription is not None
    assert subscription.source == "stripe_verified"
    assert subscription.billing_account_id == "acct-a"
    assert subscription.external_customer_id == "cus_a"


def test_subscription_before_checkout_completion_fails_retryably_then_applies() -> None:
    backend = InMemoryStateStore()
    store = BillingEntitlementStore(backend)
    store.begin_checkout_intent(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
    )
    event = _event("evt_out_of_order")
    raw = canonical_event_bytes(event)
    with pytest.raises(BillingEntitlementError, match="not durably completed"):
        _process(
            store,
            event=event,
            raw_payload=raw,
            price_to_plan={"price_pro": "professional_live"},
            ensure_checkout_lineage=False,
        )
    receipt = backend.get(
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_out_of_order"
    )
    assert receipt is not None and receipt.payload["state"] == "unresolved"

    store.finish_checkout_intent(
        tenant_id="tenant-a",
        request_id="request_0123456789",
        checkout_session_id="cs_request_0123456789",
        url="https://checkout.stripe.test/request_0123456789",
    )
    completion = _checkout_completion_event("evt_checkout_after_subscription")
    process_stripe_event(
        store,
        event=completion,
        raw_payload=canonical_event_bytes(completion),
        price_to_plan={"price_pro": "professional_live"},
        signature_verified=True,
    )
    retried = _process(
        store,
        event=event,
        raw_payload=raw,
        price_to_plan={"price_pro": "professional_live"},
        ensure_checkout_lineage=False,
    )
    assert retried["applied"] is True
    assert store.get_subscription("tenant-a").billing_account_id == "acct-a"  # type: ignore[union-attr]


def test_stripe_subscription_without_billing_account_is_structurally_invalid() -> None:
    with pytest.raises(BillingEntitlementError, match="billing account"):
        SubscriptionRecord(
            tenant_id="tenant-a",
            plan_id="professional_live",
            status="canceled",
            source="stripe_verified",
            external_customer_id="cus_a",
            external_subscription_id="sub_a",
            provider_event_id="evt_a",
            provider_event_created=1,
        )


def test_checkout_session_and_subscription_metadata_cross_wires_fail_closed() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    store.begin_checkout_intent(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
    )
    store.finish_checkout_intent(
        tenant_id="tenant-a",
        request_id="request_0123456789",
        checkout_session_id="cs_request_0123456789",
        url="https://checkout.stripe.test/request_0123456789",
    )

    wrong_session = _checkout_completion_event(
        "evt_wrong_session", checkout_session_id="cs_cross_wired"
    )
    with pytest.raises(BillingEventConflict, match="session contradicts"):
        process_stripe_event(
            store,
            event=wrong_session,
            raw_payload=canonical_event_bytes(wrong_session),
            price_to_plan={"price_pro": "professional_live"},
            signature_verified=True,
        )
    assert store.tenant_for_customer("cus_a") is None

    valid_completion = _checkout_completion_event("evt_valid_completion")
    process_stripe_event(
        store,
        event=valid_completion,
        raw_payload=canonical_event_bytes(valid_completion),
        price_to_plan={"price_pro": "professional_live"},
        signature_verified=True,
    )
    wrong_subscription = _event(
        "evt_cross_wire_subscription", subscription_id="sub_cross_wired"
    )
    with pytest.raises(BillingEntitlementError, match="signed Checkout completion"):
        _process(
            store,
            event=wrong_subscription,
            raw_payload=canonical_event_bytes(wrong_subscription),
            price_to_plan={"price_pro": "professional_live"},
            ensure_checkout_lineage=False,
        )

    for field, value in (
        ("cas_account_id", "acct-cross-wired"),
        ("cas_plan_id", "enterprise_live"),
        ("cas_checkout_request_id", "request_cross_wired"),
    ):
        event = _event(f"evt_cross_wire_{field}")
        event["data"]["object"]["metadata"][field] = value  # type: ignore[index]
        with pytest.raises(BillingEventConflict, match="durable Checkout intent"):
            _process(
                store,
                event=event,
                raw_payload=canonical_event_bytes(event),
                price_to_plan={"price_pro": "professional_live"},
                ensure_checkout_lineage=False,
            )
    assert store.get_subscription("tenant-a") is None


def test_webhook_receipt_is_hash_bound_and_duplicate_safe() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    event = _event("evt_replay")
    raw = canonical_event_bytes(event)
    first = _process(
        store, event=event, raw_payload=raw, price_to_plan={"price_pro": "professional_live"}
    )
    second = _process(
        store, event=event, raw_payload=raw, price_to_plan={"price_pro": "professional_live"}
    )
    assert first["applied"] is True
    assert second == {"event_id": "evt_replay", "applied": False, "duplicate": True}
    assert store.get_subscription("tenant-a").billing_account_id == "acct-a"  # type: ignore[union-attr]
    with pytest.raises(BillingEventConflict):
        _process(
            store,
            event=event,
            raw_payload=raw + b" ",
            price_to_plan={"price_pro": "professional_live"},
        )


def test_subscription_apply_before_terminal_receipt_crash_denies_until_exact_replay(
    monkeypatch,
) -> None:
    """A row write without its terminal receipt is never a usable grant."""

    backend = InMemoryStateStore()
    store = BillingEntitlementStore(backend)
    seeded, _ = _apply(store, event_id="evt_finish_crash_seed", created=1)
    event = _event(
        "evt_finish_crash",
        created=2,
        checkout_request_id=str(seeded.checkout_request_id),
    )
    raw = canonical_event_bytes(event)
    real_finish = store.finish_webhook_event
    armed = True

    def fail_first_terminal_finish(**kwargs):
        nonlocal armed
        if (
            armed
            and kwargs.get("event_id") == "evt_finish_crash"
            and kwargs.get("state") == "applied"
        ):
            armed = False
            raise RuntimeError("injected crash after subscription persistence")
        return real_finish(**kwargs)

    monkeypatch.setattr(store, "finish_webhook_event", fail_first_terminal_finish)
    with pytest.raises(RuntimeError, match="after subscription persistence"):
        _process(
            store,
            event=event,
            raw_payload=raw,
            price_to_plan={"price_pro": "professional_live"},
            ensure_checkout_lineage=False,
        )

    interim = store.get_subscription("tenant-a")
    assert interim is not None
    assert interim.provider_event_id == "evt_finish_crash"
    receipt = backend.get(
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_finish_crash"
    )
    assert receipt is not None and receipt.payload["state"] == "received"
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False

    monkeypatch.setattr(store, "finish_webhook_event", real_finish)
    replay = _process(
        store,
        event=event,
        raw_payload=raw,
        price_to_plan={"price_pro": "professional_live"},
        ensure_checkout_lineage=False,
    )
    assert replay["applied"] is True
    final = store.get_subscription("tenant-a")
    assert final is not None and final.provider_event_id == "evt_finish_crash"
    assert len(backend.list("tenant-a", SUBSCRIPTION_KIND)) == 1
    terminal = backend.get(
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_finish_crash"
    )
    assert terminal is not None and terminal.payload["state"] == "applied"
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True


@pytest.mark.parametrize("claim_field", ("fence", "token_sha256"))
def test_active_entitlement_rejects_tampered_terminal_attempt_claim(
    claim_field: str,
) -> None:
    backend = InMemoryStateStore()
    store = BillingEntitlementStore(backend)
    subscription, _ = _apply(
        store, event_id=f"evt_claim_tamper_{claim_field}", created=1
    )
    receipt = backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        str(subscription.provider_event_id),
    )
    assert receipt is not None
    payload = dict(receipt.payload)
    if claim_field == "fence":
        payload["subscription_refresh_fence"] = (
            int(payload["subscription_refresh_fence"]) + 1
        )
    else:
        payload["subscription_refresh_lock_token_sha256"] = "0" * 64
    backend.put(receipt.with_payload(payload), expected_version=receipt.version)

    with pytest.raises(BillingEntitlementError, match="snapshot digest"):
        store.assert_subscription_provenance(subscription)
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False


def test_unresolved_signed_event_leaves_durable_retry_receipt() -> None:
    backend = InMemoryStateStore()
    store = BillingEntitlementStore(backend)
    event = _event("evt_unresolved", tenant_id="")
    event["data"]["object"]["metadata"] = {}  # type: ignore[index]
    raw = canonical_event_bytes(event)
    with pytest.raises(BillingEntitlementError):
        _process(
            store,
            event=event,
            raw_payload=raw,
            price_to_plan={"price_pro": "professional_live"},
        )
    receipt = backend.get(
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_unresolved"
    )
    assert receipt is not None
    assert receipt.payload["state"] == "unresolved"


def test_contradictory_locked_snapshot_quarantines_then_exact_repair_recovers() -> None:
    backend = InMemoryStateStore()
    store = BillingEntitlementStore(backend)
    active, _ = _apply(store, event_id="evt_active_before_drift")
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True

    drift = _event(
        "evt_locked_drift",
        created=2,
        account_id="acct-cross-wired",
        checkout_request_id=str(active.checkout_request_id),
    )
    with pytest.raises(BillingEventConflict, match="Checkout intent"):
        _process(
            store,
            event=drift,
            raw_payload=canonical_event_bytes(drift),
            price_to_plan={"price_pro": "professional_live"},
            ensure_checkout_lineage=False,
        )

    quarantined = store.get_subscription("tenant-a")
    assert quarantined is not None
    assert quarantined.status == "quarantined"
    assert quarantined.quarantine_reason
    assert quarantined.provider_event_id == "evt_locked_drift"
    assert quarantined.provider_refreshed_object_sha256
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False
    receipt = backend.get(
        BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, "evt_locked_drift"
    )
    assert receipt is not None and receipt.payload["state"] == "unresolved"

    recovered, changed = _apply(store, event_id="evt_exact_repair", created=3)
    assert changed is True
    assert recovered.status == "active"
    assert recovered.quarantine_reason is None
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True


def test_processed_object_must_be_the_exact_locked_snapshot() -> None:
    backend = InMemoryStateStore()
    store = BillingEntitlementStore(backend)
    active, _ = _apply(store, event_id="evt_snapshot_identity_seed")
    event = _event(
        "evt_snapshot_identity_drift",
        created=2,
        status="past_due",
        checkout_request_id=str(active.checkout_request_id),
    )
    current = _event(
        "unused_current_snapshot_envelope",
        created=2,
        status="active",
        checkout_request_id=str(active.checkout_request_id),
    )
    event_object = event["data"]["object"]  # type: ignore[index]
    current_object = current["data"]["object"]  # type: ignore[index]
    raw = canonical_event_bytes(event)
    store.begin_webhook_event(
        event_id="evt_snapshot_identity_drift",
        event_type="customer.subscription.updated",
        event_created=2,
        raw_payload=raw,
        livemode=True,
        signature_verified=True,
    )
    lease = store.acquire_subscription_refresh_lock(
        external_subscription_id="sub_a",
        event_id="evt_snapshot_identity_drift",
    )
    try:
        refresh_facts_sha256 = store.record_webhook_refresh(
            event_id="evt_snapshot_identity_drift",
            external_subscription_id="sub_a",
            refreshed_object=current_object,  # type: ignore[arg-type]
            provider_request_id="req_snapshot_identity_drift",
            refresh_lock_token=lease.token,
        )
        with pytest.raises(BillingEventConflict, match="locked provider snapshot"):
            process_stripe_event(
                store,
                event={**event, "data": {"object": event_object}},
                raw_payload=raw,
                price_to_plan={"price_pro": "professional_live"},
                resource_refreshed=True,
                refresh_lock_token=lease.token,
                refresh_facts_sha256=refresh_facts_sha256,
                locked_subscription_id="sub_a",
                signature_verified=True,
            )
    finally:
        store.release_subscription_refresh_lock(lease)

    quarantined = store.get_subscription("tenant-a")
    assert quarantined is not None
    assert quarantined.status == "quarantined"
    assert "locked provider snapshot" in str(quarantined.quarantine_reason)
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False


def _stage_locked_refresh(
    store: BillingEntitlementStore,
    event: dict[str, object],
):
    """Open the exact receipt/refresh/provenance chain without applying it."""

    raw_payload = canonical_event_bytes(event)
    obj = event["data"]["object"]  # type: ignore[index]
    metadata = obj["metadata"]  # type: ignore[index]
    store.begin_webhook_event(
        event_id=str(event["id"]),
        event_type=str(event["type"]),
        event_created=int(event["created"]),
        raw_payload=raw_payload,
        livemode=bool(event["livemode"]),
        signature_verified=True,
    )
    lease = store.acquire_subscription_refresh_lock(
        external_subscription_id=str(obj["id"]),  # type: ignore[index]
        event_id=str(event["id"]),
    )
    refresh_facts_sha256 = store.record_webhook_refresh(
        event_id=str(event["id"]),
        external_subscription_id=str(obj["id"]),  # type: ignore[index]
        refreshed_object=obj,  # type: ignore[arg-type]
        provider_request_id=f"req_{event['id']}",
        refresh_lock_token=lease.token,
    )
    provenance = store.build_subscription_provenance(
        tenant_id=str(metadata["cas_tenant_id"]),  # type: ignore[index]
        billing_account_id=str(metadata["cas_account_id"]),  # type: ignore[index]
        plan_id=str(metadata["cas_plan_id"]),  # type: ignore[index]
        request_id=str(metadata["cas_checkout_request_id"]),  # type: ignore[index]
        external_customer_id=str(obj["customer"]),  # type: ignore[index]
        external_subscription_id=str(obj["id"]),  # type: ignore[index]
        provider_event_id=str(event["id"]),
        provider_event_payload_sha256=hashlib.sha256(raw_payload).hexdigest(),
        refresh_lock_token=lease.token,
        provider_refresh_facts_sha256=refresh_facts_sha256,
    )
    return raw_payload, obj, lease, provenance


class _ZeroFenceMemoryStore(InMemoryStateStore):
    """Reference-backend fence=0 model with stale-token visibility injection."""

    def force_visible_lease(self, lease) -> None:
        key = (lease.tenant_id, lease.resource_id)
        with self._lock:  # noqa: SLF001 - deterministic stale-holder injection
            current = self._leases.get(key)  # noqa: SLF001
            if current is not None:
                self._token_index.pop(current.token, None)  # noqa: SLF001
            self._leases[key] = lease  # noqa: SLF001
            self._token_index[lease.token] = key  # noqa: SLF001


class _FencedMemoryStore(_ZeroFenceMemoryStore):
    """Test backend that mints fences and can expose a stalled old holder."""

    def __init__(self) -> None:
        super().__init__()
        self._next_test_fence = 0

    def _make_lease(
        self,
        tenant_id,
        resource_id,
        holder,
        stamp,
        ttl_seconds,
        *,
        token=None,
    ):
        lease = super()._make_lease(
            tenant_id,
            resource_id,
            holder,
            stamp,
            ttl_seconds,
            token=token,
        )
        if token is not None:
            current = self._leases.get((tenant_id, resource_id))  # noqa: SLF001
            fence = current.fence if current is not None else self._next_test_fence
        else:
            self._next_test_fence += 1
            fence = self._next_test_fence
        return replace(lease, fence=fence)

    def force_visible_lease(self, lease) -> None:
        """Model a partition that reports a stalled holder as current."""

        key = (lease.tenant_id, lease.resource_id)
        with self._lock:  # noqa: SLF001 - deterministic stale-holder injection
            current = self._leases.get(key)  # noqa: SLF001
            if current is not None:
                self._token_index.pop(current.token, None)  # noqa: SLF001
            self._leases[key] = lease  # noqa: SLF001
            self._token_index[lease.token] = key  # noqa: SLF001


def test_persisted_refresh_fence_rejects_stalled_lower_fence_overwrite() -> None:
    """A stale holder cannot restore active over a higher-fence cancellation."""

    backend = _FencedMemoryStore()
    store = BillingEntitlementStore(backend)
    seeded, _ = _apply(store, event_id="evt_fence_seed", created=1)
    stale_event = _event(
        "evt_fence_stale_active",
        created=2,
        status="active",
        checkout_request_id=str(seeded.checkout_request_id),
    )
    _, stale_object, stale_lease, stale_provenance = _stage_locked_refresh(
        store, stale_event
    )
    assert stale_provenance.provider_refresh_fence > 0
    store.release_subscription_refresh_lock(stale_lease)

    canceled, changed = _apply(
        store,
        event_id="evt_fence_current_canceled",
        created=3,
        status="canceled",
    )
    assert changed is True
    assert canceled.status == "canceled"
    assert (
        canceled.provider_refresh_fence
        > stale_provenance.provider_refresh_fence
    )

    # Model stalled host A waking after host B persisted the higher-fence row.
    # Even if A's partition reports its old token as current, the row's durable
    # high-water mark must reject the write.
    backend.force_visible_lease(stale_lease)
    with pytest.raises(BillingEventConflict, match="stale subscription refresh fence"):
        store.apply_stripe_subscription(
            tenant_id="tenant-a",
            billing_account_id="acct-a",
            plan_id="professional_live",
            status="active",
            external_customer_id="cus_a",
            external_subscription_id="sub_a",
            event_id="evt_fence_stale_active",
            event_created=2,
            current_period_start=datetime.fromtimestamp(
                1_700_000_000, tz=UTC
            ).isoformat(),
            current_period_end=datetime.fromtimestamp(
                4_000_000_000, tz=UTC
            ).isoformat(),
            cancel_at_period_end=False,
            resource_refreshed=True,
            refresh_lock_token=stale_lease.token,
            provenance=stale_provenance,
            refreshed_object=stale_object,  # type: ignore[arg-type]
            price_to_plan={"price_pro": "professional_live"},
            event_type="customer.subscription.updated",
        )
    final = store.get_subscription("tenant-a")
    assert final is not None
    assert final.status == "canceled"
    assert final.provider_event_id == "evt_fence_current_canceled"


@pytest.mark.parametrize(
    "backend_type",
    (_FencedMemoryStore, _ZeroFenceMemoryStore),
    ids=("monotonic-fence", "zero-fence-token-cas"),
)
def test_receipt_attempt_claim_fences_stale_finish_and_retry_converges(
    backend_type,
) -> None:
    """A stale f1 finisher cannot terminalize after same-event f2 takeover."""

    backend = backend_type()
    store = BillingEntitlementStore(backend)
    seeded, _ = _apply(store, event_id="evt_receipt_fence_seed", created=1)
    event = _event(
        "evt_receipt_fence_shared",
        created=2,
        status="active",
        checkout_request_id=str(seeded.checkout_request_id),
    )
    raw, obj, stale_lease, stale_provenance = _stage_locked_refresh(store, event)
    stale_row, changed = store.apply_stripe_subscription(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        status="active",
        external_customer_id="cus_a",
        external_subscription_id="sub_a",
        event_id="evt_receipt_fence_shared",
        event_created=2,
        current_period_start=datetime.fromtimestamp(
            1_700_000_000, tz=UTC
        ).isoformat(),
        current_period_end=datetime.fromtimestamp(
            4_000_000_000, tz=UTC
        ).isoformat(),
        cancel_at_period_end=False,
        resource_refreshed=True,
        refresh_lock_token=stale_lease.token,
        provenance=stale_provenance,
        refreshed_object=obj,  # type: ignore[arg-type]
        price_to_plan={"price_pro": "professional_live"},
        event_type="customer.subscription.updated",
    )
    assert changed is True
    stale_authority = subscription_authority_facts_sha256(stale_row)
    receipt = backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        "evt_receipt_fence_shared",
    )
    assert receipt is not None and receipt.payload["state"] == "received"
    assert (
        receipt.payload["subscription_refresh_fence"]
        == stale_lease.fence
    )

    # A stalls before terminalizing; its lease expires and exact retry B takes
    # a higher fence, claims the shared receipt by CAS, then installs pending.
    store.release_subscription_refresh_lock(stale_lease)
    retry_lease = store.acquire_subscription_refresh_lock(
        external_subscription_id="sub_a",
        event_id="evt_receipt_fence_shared",
    )
    if stale_lease.fence > 0:
        assert retry_lease.fence > stale_lease.fence
    else:
        assert retry_lease.fence == stale_lease.fence == 0
        assert retry_lease.token != stale_lease.token
    claimed = store.claim_subscription_webhook_attempt(
        event_id="evt_receipt_fence_shared",
        external_subscription_id="sub_a",
        refresh_lock_token=retry_lease.token,
    )
    assert claimed is not None
    assert claimed.payload["subscription_refresh_fence"] == retry_lease.fence
    pending = store.mark_subscription_pending_revalidation(
        external_subscription_id="sub_a",
        event_id="evt_receipt_fence_shared",
        event_created=2,
        raw_payload=raw,
        provider_event_payload_sha256=hashlib.sha256(raw).hexdigest(),
        refresh_lock_token=retry_lease.token,
    )
    assert pending is not None
    assert pending.status == "pending_provider_revalidation"
    assert pending.provider_refresh_fence == retry_lease.fence

    # Even if A wakes in a partition that reports its old token as current, the
    # receipt-side CAS claim is f2 and rejects A's late terminalization.
    backend.force_visible_lease(stale_lease)
    with pytest.raises(
        BillingEntitlementError, match="claimed by another delivery"
    ):
        store.finish_webhook_event(
            event_id="evt_receipt_fence_shared",
            state="applied",
            tenant_id="tenant-a",
            detail="stale attempt must not terminalize",
            applied_subscription_facts_sha256=stale_authority,
            external_subscription_id="sub_a",
            refresh_lock_token=stale_lease.token,
            refresh_fence=stale_lease.fence,
        )
    still_open = backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        "evt_receipt_fence_shared",
    )
    assert still_open is not None and still_open.payload["state"] == "received"

    backend.force_visible_lease(retry_lease)
    retry_refresh = store.record_webhook_refresh(
        event_id="evt_receipt_fence_shared",
        external_subscription_id="sub_a",
        refreshed_object=obj,  # type: ignore[arg-type]
        provider_request_id="req_receipt_fence_retry",
        refresh_lock_token=retry_lease.token,
    )
    recovered = process_stripe_event(
        store,
        event=event,
        raw_payload=raw,
        price_to_plan={"price_pro": "professional_live"},
        resource_refreshed=True,
        refresh_lock_token=retry_lease.token,
        refresh_facts_sha256=retry_refresh,
        locked_subscription_id="sub_a",
        signature_verified=True,
    )
    assert recovered["applied"] is True
    final = store.get_subscription("tenant-a")
    assert final is not None and final.status == "active"
    assert final.provider_refresh_fence == retry_lease.fence
    terminal = backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        "evt_receipt_fence_shared",
    )
    assert terminal is not None and terminal.payload["state"] == "applied"
    assert (
        terminal.payload["subscription_refresh_fence"]
        == final.provider_refresh_fence
    )
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True


def test_cross_tenant_drift_quarantines_only_the_bound_subscription() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    active, _ = _apply(store, event_id="evt_cross_tenant_seed")
    drift = _event(
        "evt_cross_tenant_drift",
        created=2,
        tenant_id="tenant-b",
        account_id="acct-b",
        customer_id="cus_b",
        subscription_id="sub_a",
        checkout_request_id=str(active.checkout_request_id),
    )
    with pytest.raises(BillingEntitlementError):
        _process(
            store,
            event=drift,
            raw_payload=canonical_event_bytes(drift),
            price_to_plan={"price_pro": "professional_live"},
            ensure_checkout_lineage=False,
        )
    assert store.get_subscription("tenant-a").status == "quarantined"  # type: ignore[union-attr]
    assert store.get_subscription("tenant-b") is None


def test_concurrent_refresh_lock_refuses_second_writer_without_revoking_access() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    active, _ = _apply(store, event_id="evt_lock_seed")
    held = store.acquire_subscription_refresh_lock(
        external_subscription_id="sub_a", event_id="evt_lock_holder"
    )
    contender = _event(
        "evt_lock_contender",
        created=2,
        checkout_request_id=str(active.checkout_request_id),
    )
    try:
        # The durable event id is shared by concurrent Stripe deliveries, so
        # each call must still use a distinct lease holder and lose this race.
        with pytest.raises(BillingEntitlementError, match="another subscription refresh"):
            store.acquire_subscription_refresh_lock(
                external_subscription_id="sub_a",
                event_id="evt_lock_holder",
            )
        with pytest.raises(BillingEntitlementError, match="another subscription refresh"):
            _process(
                store,
                event=contender,
                raw_payload=canonical_event_bytes(contender),
                price_to_plan={"price_pro": "professional_live"},
                ensure_checkout_lineage=False,
            )
    finally:
        store.release_subscription_refresh_lock(held)
    assert store.get_subscription("tenant-a").status == "active"  # type: ignore[union-attr]
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is True


def test_pending_barrier_before_receipt_survives_sqlite_restart_and_exact_retry(
    tmp_path,
) -> None:
    """Crash after the deny barrier but before receipt creation stays fail-closed."""

    path = tmp_path / "billing-pending-barrier.db"
    first_backend = SqliteStateStore(path)
    first = BillingEntitlementStore(first_backend)
    seeded, _ = _apply(first, event_id="evt_barrier_seed", created=1)
    event = _event(
        "evt_barrier_before_receipt",
        created=2,
        status="canceled",
        checkout_request_id=str(seeded.checkout_request_id),
    )
    raw = canonical_event_bytes(event)
    lease = first.acquire_subscription_refresh_lock(
        external_subscription_id="sub_a",
        event_id="evt_barrier_before_receipt",
    )
    pending = first.mark_subscription_pending_revalidation(
        external_subscription_id="sub_a",
        event_id="evt_barrier_before_receipt",
        event_created=2,
        raw_payload=raw,
        provider_event_payload_sha256=hashlib.sha256(raw).hexdigest(),
        refresh_lock_token=lease.token,
    )
    assert pending is not None
    assert pending.status == "pending_provider_revalidation"
    assert first_backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        "evt_barrier_before_receipt",
    ) is None
    first_backend.close()  # injected process death before begin_webhook_event

    second_backend = SqliteStateStore(path)
    second = BillingEntitlementStore(second_backend)
    restored = second.get_subscription("tenant-a")
    assert restored is not None
    assert restored.status == "pending_provider_revalidation"
    assert second.resolve_entitlement("tenant-a").can_run_live_audit is False
    assert second_backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        "evt_barrier_before_receipt",
    ) is None

    # A real crashed holder becomes reclaimable at TTL expiry. Releasing its
    # known test token models that handoff without a five-minute wall-clock wait.
    second_backend.release_lease(lease.token)
    replay = _process(
        second,
        event=event,
        raw_payload=raw,
        price_to_plan={"price_pro": "professional_live"},
        ensure_checkout_lineage=False,
    )
    assert replay["applied"] is True
    final = second.get_subscription("tenant-a")
    assert final is not None and final.status == "canceled"
    assert len(second_backend.list("tenant-a", SUBSCRIPTION_KIND)) == 1
    receipt = second_backend.get(
        BILLING_PLATFORM_TENANT,
        WEBHOOK_EVENT_KIND,
        "evt_barrier_before_receipt",
    )
    assert receipt is not None and receipt.payload["state"] == "applied"
    assert second.resolve_entitlement("tenant-a").can_run_live_audit is False
    second_backend.close()


def test_sqlite_subscription_and_receipt_survive_restart(tmp_path) -> None:
    path = tmp_path / "billing.db"
    first_backend = SqliteStateStore(path)
    first = BillingEntitlementStore(first_backend)
    event = _event("evt_restart")
    raw = canonical_event_bytes(event)
    _process(
        first, event=event, raw_payload=raw, price_to_plan={"price_pro": "professional_live"}
    )
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second = BillingEntitlementStore(second_backend)
    second.require_checkout_lineage(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
        checkout_session_id="cs_request_0123456789",
    )
    second.require_checkout_subscription_lineage(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        plan_id="professional_live",
        request_id="request_0123456789",
        external_customer_id="cus_a",
        external_subscription_id="sub_a",
    )
    assert second.resolve_entitlement("tenant-a").can_run_live_audit is True
    assert second.get_subscription("tenant-a").billing_account_id == "acct-a"  # type: ignore[union-attr]
    duplicate = _process(
        second, event=event, raw_payload=raw, price_to_plan={"price_pro": "professional_live"}
    )
    assert duplicate["duplicate"] is True
    second_backend.close()
