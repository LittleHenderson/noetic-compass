from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
    customer_id: str = "cus_a",
    subscription_id: str = "sub_a",
    status: str = "active",
    price_id: str = "price_pro",
) -> dict[str, object]:
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "created": created,
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": status,
                "metadata": {"cas_tenant_id": tenant_id},
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


def _apply(
    store: BillingEntitlementStore,
    *,
    event_id: str = "evt_1",
    created: int = 100,
    tenant_id: str = "tenant-a",
    customer_id: str = "cus_a",
    subscription_id: str = "sub_a",
    plan_id: str | None = "professional_live",
    status: str = "active",
) -> tuple[SubscriptionRecord, bool]:
    return store.apply_stripe_subscription(
        tenant_id=tenant_id,
        plan_id=plan_id,
        status=status,
        external_customer_id=customer_id,
        external_subscription_id=subscription_id,
        event_id=event_id,
        event_created=created,
        current_period_start=datetime.now(UTC).isoformat(),
        current_period_end=_future(),
        cancel_at_period_end=False,
    )


def _process(
    store: BillingEntitlementStore,
    *,
    event: dict[str, object],
    raw_payload: bytes,
    price_to_plan: dict[str, str],
) -> dict[str, object]:
    obj = event["data"]["object"]  # type: ignore[index]
    subscription_id = str(obj["id"])  # type: ignore[index]
    lease = store.acquire_subscription_refresh_lock(
        external_subscription_id=subscription_id,
        event_id=str(event["id"]),
    )
    try:
        return process_stripe_event(
            store,
            event=event,
            raw_payload=raw_payload,
            price_to_plan=price_to_plan,
            resource_refreshed=True,
            refresh_lock_token=lease.token,
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


def test_out_of_order_provider_event_cannot_roll_back_newer_state() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    _apply(store, event_id="evt_new", created=200, status="canceled")
    record, changed = _apply(
        store, event_id="evt_old", created=100, status="active"
    )
    assert changed is False
    assert record.provider_event_id == "evt_new"
    assert record.status == "canceled"


def test_same_second_events_use_locked_current_resource_not_event_id_order() -> None:
    store = BillingEntitlementStore(InMemoryStateStore())
    first_lease = store.acquire_subscription_refresh_lock(
        external_subscription_id="sub_a", event_id="evt_z"
    )
    try:
        store.apply_stripe_subscription(
            tenant_id="tenant-a",
            plan_id="professional_live",
            status="active",
            external_customer_id="cus_a",
            external_subscription_id="sub_a",
            event_id="evt_z",
            event_created=100,
            current_period_start=datetime.now(UTC).isoformat(),
            current_period_end=_future(),
            cancel_at_period_end=False,
            resource_refreshed=True,
            refresh_lock_token=first_lease.token,
        )
    finally:
        store.release_subscription_refresh_lock(first_lease)
    second_lease = store.acquire_subscription_refresh_lock(
        external_subscription_id="sub_a", event_id="evt_a"
    )
    try:
        record, changed = store.apply_stripe_subscription(
            tenant_id="tenant-a",
            plan_id="professional_live",
            status="canceled",
            external_customer_id="cus_a",
            external_subscription_id="sub_a",
            event_id="evt_a",
            event_created=100,
            current_period_start=datetime.now(UTC).isoformat(),
            current_period_end=_future(),
            cancel_at_period_end=False,
            resource_refreshed=True,
            refresh_lock_token=second_lease.token,
        )
    finally:
        store.release_subscription_refresh_lock(second_lease)
    assert changed is True
    assert record.status == "canceled"
    assert store.resolve_entitlement("tenant-a").can_run_live_audit is False


def test_active_stripe_without_period_end_is_structurally_invalid() -> None:
    with pytest.raises(BillingEntitlementError, match="period end"):
        SubscriptionRecord(
            tenant_id="tenant-a",
            plan_id="professional_live",
            status="active",
            source="stripe_verified",
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
        external_customer_id="cus_a",
        external_subscription_id="sub_a",
        current_period_end=_future(),
        provider_event_id="evt_a",
        provider_event_created=1,
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


def test_write_conflict_rechecks_event_order_instead_of_blind_retry() -> None:
    store = BillingEntitlementStore(_WriteConflictStore())
    record, changed = _apply(store, event_id="evt_old", created=1)
    assert changed is False
    assert record.provider_event_id == "evt_newer"
    assert record.status == "canceled"


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
    with pytest.raises(BillingEventConflict):
        _process(
            store,
            event=event,
            raw_payload=raw + b" ",
            price_to_plan={"price_pro": "professional_live"},
        )


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
    assert second.resolve_entitlement("tenant-a").can_run_live_audit is True
    duplicate = _process(
        second, event=event, raw_payload=raw, price_to_plan={"price_pro": "professional_live"}
    )
    assert duplicate["duplicate"] is True
    second_backend.close()
