from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json

import pytest

from api.services.billing_entitlements import BillingEntitlementStore
from api.services.billing_reconciliation import (
    BILLING_RECONCILIATION_PLATFORM_TENANT,
    PAID_INVOICE_KIND,
    USAGE_INVOICE_INDEX_KIND,
    USAGE_MEASUREMENT_INDEX_KIND,
    USAGE_OUTBOX_KIND,
    USAGE_RECEIPT_INDEX_KIND,
    BillingReconciliationConflict,
    BillingReconciliationError,
    BillingReconciliationStore,
    BillingReconciliationUnresolved,
    FleetUsageMeasurement,
    ProviderPaidInvoice,
)
from api.services.production.state_substrate import (
    InMemoryStateStore,
    StateStoreError,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


HASH_KEY = "provider-reference-key-is-dedicated-0123456789"
PRICE_ID = "price_1CasUsageAcceleratorMs"
METER_NAME = "cas.accelerator_milliseconds"
METER_VERSION = "cas_meter.v1"
RECEIPT_HOST = "receipts.stripe.test"
# Keep the provider invoice readback fresh while leaving all event and line
# ordering deterministic relative to one whole-second anchor.
START = datetime.now(UTC).replace(microsecond=0) - timedelta(days=2, minutes=3)
END = START + timedelta(hours=1)


class _CrashAfterUsageIndexesStore(InMemoryStateStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_usage_once = False

    def put(self, record, *, expected_version):
        if self.fail_usage_once and record.kind == USAGE_OUTBOX_KIND:
            self.fail_usage_once = False
            raise StateStoreError("simulated crash after usage indexes")
        return super().put(record, expected_version=expected_version)


def _install_stripe_subscription(
    entitlements: BillingEntitlementStore,
    *,
    tenant_id: str = "tenant-a",
    account_id: str = "acct-a",
    customer_id: str = "cus_CustomerA",
    subscription_id: str = "sub_SubscriptionA",
) -> None:
    entitlements.grant_manual_comped(
        tenant_id=tenant_id,
        billing_account_id=account_id,
        expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
    )
    entitlements.apply_stripe_subscription(
        tenant_id=tenant_id,
        plan_id="professional_live",
        status="active",
        external_customer_id=customer_id,
        external_subscription_id=subscription_id,
        event_id=("evt_SubscriptionA" if tenant_id == "tenant-a" else "evt_SubscriptionB"),
        event_created=1,
        current_period_start=START.isoformat(),
        current_period_end=(START + timedelta(days=31)).isoformat(),
        cancel_at_period_end=False,
    )


def _service(
    backend=None,
    *,
    tenants: tuple[tuple[str, str, str, str], ...] = (
        ("tenant-a", "acct-a", "cus_CustomerA", "sub_SubscriptionA"),
    ),
    key: str = HASH_KEY,
) -> tuple[BillingReconciliationStore, BillingEntitlementStore, object]:
    store = backend or InMemoryStateStore()
    entitlements = BillingEntitlementStore(store)
    for tenant, account, customer, subscription in tenants:
        _install_stripe_subscription(
            entitlements,
            tenant_id=tenant,
            account_id=account,
            customer_id=customer,
            subscription_id=subscription,
        )
    service = BillingReconciliationStore(
        store,
        entitlements,
        provider_reference_hash_key=key,
        usage_price_id=PRICE_ID,
        meter_event_name=METER_NAME,
        meter_event_version=METER_VERSION,
        currency="usd",
        livemode=True,
        customer_receipt_allowed_hosts=(RECEIPT_HOST,),
    )
    return service, entitlements, store


def _measurement(
    *,
    tenant_id: str = "tenant-a",
    account_id: str = "acct-a",
    run_id: str = "run-a",
    worker_id: str = "worker-a",
    quantity: int = 900_000,
    started_at: datetime = START,
    ended_at: datetime = END,
    receipt_char: str = "a",
    source: str = "fleet_measured",
) -> FleetUsageMeasurement:
    return FleetUsageMeasurement(
        tenant_id=tenant_id,
        billing_account_id=account_id,
        run_id=run_id,
        worker_id=worker_id,
        accelerator_milliseconds=quantity,
        accelerator_count=1,
        measurement_started_at=started_at.isoformat(),
        measurement_ended_at=ended_at.isoformat(),
        receipt_sha256=receipt_char * 64,
        receipt_schema_version="fleet_usage_receipt.v1",
        receipt_size_bytes=4096,
        receipt_issuer="authenticated-fleet-gateway",
        source=source,
    )


def _invoice(
    *,
    quantity: int = 900_000,
    invoice_id: str = "in_InvoiceA",
    customer_id: str = "cus_CustomerA",
    subscription_id: str = "sub_SubscriptionA",
    event_id: str = "evt_InvoicePaidA",
    event_created: int = int((START + timedelta(days=2, minutes=1)).timestamp()),
    raw_char: str = "b",
    snapshot_char: str = "c",
) -> ProviderPaidInvoice:
    return ProviderPaidInvoice(
        provider_event_id=event_id,
        provider_event_created=event_created,
        created=int(START.timestamp()),
        status_transitions_finalized_at=int((START + timedelta(days=1, hours=1)).timestamp()),
        external_invoice_id=invoice_id,
        external_customer_id=customer_id,
        external_subscription_id=subscription_id,
        provider_status="paid",
        provider_paid=True,
        currency="usd",
        amount_due_minor=12_34,
        amount_paid_minor=12_34,
        usage_price_id=PRICE_ID,
        meter_event_name=METER_NAME,
        meter_event_version=METER_VERSION,
        livemode=True,
        usage_quantity_milliseconds=quantity,
        usage_period_start=START.isoformat(),
        usage_period_end=(START + timedelta(days=1)).isoformat(),
        paid_at=(START + timedelta(days=2)).isoformat(),
        raw_event_sha256=raw_char * 64,
        provider_snapshot_sha256=snapshot_char * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=2)
        ).isoformat(),
        hosted_invoice_url=f"https://{RECEIPT_HOST}/{invoice_id}",
        invoice_pdf=f"https://{RECEIPT_HOST}/{invoice_id}.pdf",
        invoice_pdf_http_status=200,
        invoice_pdf_content_type="application/pdf",
        invoice_pdf_size_bytes=8192,
        invoice_pdf_sha256="f" * 64,
        invoice_pdf_retrieved_at=(
            START + timedelta(days=2, minutes=3)
        ).isoformat(),
        provider_request_id="req_InvoiceA",
    )


def _submit(
    service: BillingReconciliationStore,
    measurement: FleetUsageMeasurement,
    *,
    event_id: str = "MeterA",
):
    usage, _ = service.record_fleet_measurement(measurement)
    created = usage.meter_event_timestamp + 60
    return service.mark_usage_submitted(
        tenant_id=measurement.tenant_id,
        usage_id=usage.usage_id,
        response=_provider_readback(usage, created=created),
        provider_request_id=f"req_{event_id}",
        provider_response_sha256=hashlib.sha256(
            f"meter-response:{event_id}".encode("utf-8")
        ).hexdigest(),
    )


def _provider_readback(usage, *, created: int) -> dict[str, object]:
    return {
        "object": "billing.meter_event",
        "created": created,
        "event_name": usage.meter_event_name,
        "identifier": usage.meter_event_identifier,
        "livemode": usage.livemode,
        "payload": {
            "stripe_customer_id": usage.external_customer_id,
            "value": str(usage.accelerator_milliseconds),
        },
        "timestamp": usage.meter_event_timestamp,
    }


def _reseal(payload: dict[str, object], digest_field: str) -> dict[str, object]:
    result = dict(payload)
    result.pop(digest_field, None)
    encoded = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    result[digest_field] = hashlib.sha256(encoded).hexdigest()
    return result


def test_constructor_requires_dedicated_hmac_key() -> None:
    store = InMemoryStateStore()
    entitlements = BillingEntitlementStore(store)
    with pytest.raises(BillingReconciliationError, match="at least 32 bytes"):
        BillingReconciliationStore(
            store,
            entitlements,
            provider_reference_hash_key="weak",
            usage_price_id=PRICE_ID,
            meter_event_name=METER_NAME,
            meter_event_version=METER_VERSION,
            currency="usd",
            livemode=True,
            customer_receipt_allowed_hosts=(RECEIPT_HOST,),
        )

    for weak_key in (
        " " * 32,
        "\x00" * 32,
        "x" * 32,
        "abcd" * 8,
        "change-me-in-production-change-me-now",
    ):
        with pytest.raises(
            BillingReconciliationError,
            match="whitespace or control|unpredictable",
        ):
            BillingReconciliationStore(
                store,
                entitlements,
                provider_reference_hash_key=weak_key,
                usage_price_id=PRICE_ID,
                meter_event_name=METER_NAME,
                meter_event_version=METER_VERSION,
                currency="usd",
                livemode=True,
                customer_receipt_allowed_hosts=(RECEIPT_HOST,),
            )
    with pytest.raises(BillingReconciliationError, match="IP address"):
        BillingReconciliationStore(
            store,
            entitlements,
            provider_reference_hash_key=HASH_KEY,
            usage_price_id=PRICE_ID,
            meter_event_name=METER_NAME,
            meter_event_version=METER_VERSION,
            currency="usd",
            livemode=True,
            customer_receipt_allowed_hosts=("127.0.0.1",),
        )


def test_measurement_refuses_estimates_impossible_quantity_and_unbounded_receipt() -> None:
    service, _, _ = _service()
    with pytest.raises(BillingReconciliationError, match="estimates"):
        service.record_fleet_measurement(_measurement(source="planner_estimate"))
    with pytest.raises(BillingReconciliationError, match="exceed wall time"):
        service.record_fleet_measurement(_measurement(quantity=3_600_001))
    with pytest.raises(BillingReconciliationError, match="receipt_size_bytes"):
        service.record_fleet_measurement(
            replace(_measurement(), receipt_size_bytes=2_000_001)
        )


def test_measurement_binds_account_and_requires_stripe_subscription() -> None:
    service, _, _ = _service()
    with pytest.raises(BillingReconciliationConflict, match="billing account"):
        service.record_fleet_measurement(_measurement(account_id="acct-attacker"))
    with pytest.raises(BillingReconciliationError, match="Stripe-verified"):
        service.record_fleet_measurement(_measurement(tenant_id="tenant-missing"))


def test_usage_is_deterministic_idempotent_and_co_located_with_outbox() -> None:
    service, _, _ = _service()
    first, created = service.record_fleet_measurement(_measurement())
    second, created_again = service.record_fleet_measurement(_measurement())
    assert created is True
    assert created_again is False
    assert first == second
    assert first.usage_id.startswith("usage-")
    assert first.outbox_state == "pending"
    assert first.meter_event_identifier.startswith("cas_usage_")
    assert set(first.meter_event_request()) == {
        "event_name", "payload", "identifier", "timestamp"
    }
    assert first.meter_event_name == METER_NAME
    assert first.meter_event_version == METER_VERSION
    assert first.usage_price_id == PRICE_ID
    assert first.currency == "usd"
    assert first.livemode is True


def test_concurrent_exact_measurement_replay_creates_one_usage_record() -> None:
    service, _, _ = _service()
    measurement = _measurement()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _index: service.record_fleet_measurement(measurement),
                range(16),
            )
        )
    usage_ids = {record.usage_id for record, _created in results}
    assert len(usage_ids) == 1
    assert sum(1 for _record, created in results if created) == 1
    assert len(service.list_usage("tenant-a")) == 1


def test_concurrent_distinct_receipts_cannot_double_bill_one_measurement() -> None:
    service, _, _ = _service()

    def attempt(receipt_char: str):
        try:
            return service.record_fleet_measurement(
                _measurement(receipt_char=receipt_char)
            )
        except BillingReconciliationConflict as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ("a", "b")))
    successes = [result for result in results if isinstance(result, tuple)]
    conflicts = [
        result for result in results if isinstance(result, BillingReconciliationConflict)
    ]
    assert len(successes) == 1
    assert len(conflicts) == 1
    assert len(service.list_usage("tenant-a")) == 1


def test_crash_after_global_indexes_is_repaired_by_exact_retry() -> None:
    backend = _CrashAfterUsageIndexesStore()
    service, _, _ = _service(backend)
    backend.fail_usage_once = True
    with pytest.raises(StateStoreError, match="simulated crash"):
        service.record_fleet_measurement(_measurement())
    assert backend.list("tenant-a", USAGE_OUTBOX_KIND) == ()
    assert len(
        backend.list(
            BILLING_RECONCILIATION_PLATFORM_TENANT,
            USAGE_RECEIPT_INDEX_KIND,
        )
    ) == 1
    assert len(
        backend.list(
            BILLING_RECONCILIATION_PLATFORM_TENANT,
            USAGE_MEASUREMENT_INDEX_KIND,
        )
    ) == 1

    recovered, created = service.record_fleet_measurement(_measurement())
    assert created is True
    assert service.get_usage("tenant-a", recovered.usage_id) == recovered


def test_distinct_receipt_cannot_rebill_same_semantic_measurement() -> None:
    service, _, _ = _service()
    service.record_fleet_measurement(_measurement(receipt_char="a"))
    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.record_fleet_measurement(_measurement(receipt_char="b"))


def test_receipt_replay_conflict_and_cross_tenant_reuse_fail_closed() -> None:
    service, _, _ = _service(
        tenants=(
            ("tenant-a", "acct-a", "cus_a", "sub_a"),
            ("tenant-b", "acct-b", "cus_b", "sub_b"),
        )
    )
    service.record_fleet_measurement(_measurement())
    with pytest.raises(BillingReconciliationConflict, match="contradictory"):
        service.record_fleet_measurement(_measurement(quantity=800_000))
    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.record_fleet_measurement(
            _measurement(
                tenant_id="tenant-b",
                account_id="acct-b",
                run_id="run-b",
                worker_id="worker-b",
            )
        )


def test_tenant_scoped_reads_do_not_reveal_other_tenant_records() -> None:
    service, _, _ = _service(
        tenants=(
            ("tenant-a", "acct-a", "cus_a", "sub_a"),
            ("tenant-b", "acct-b", "cus_b", "sub_b"),
        )
    )
    usage, _ = service.record_fleet_measurement(_measurement())
    assert service.get_usage("tenant-b", usage.usage_id) is None
    assert service.list_usage("tenant-b") == ()
    assert (
        service.public_usage_projection(
            tenant_id="tenant-b", usage_id=usage.usage_id
        )
        is None
    )


def test_outbox_failure_and_submission_transitions_are_idempotent() -> None:
    service, _, _ = _service()
    usage, _ = service.record_fleet_measurement(_measurement())
    failed = service.record_delivery_failure(
        tenant_id="tenant-a", usage_id=usage.usage_id, failure_code="timeout"
    )
    assert failed.outbox_state == "pending"
    assert failed.attempt_count == 1
    assert failed.last_failure_code == "timeout"
    submitted = service.mark_usage_submitted(
        tenant_id="tenant-a",
        usage_id=usage.usage_id,
        response=_provider_readback(
            usage, created=usage.meter_event_timestamp + 60
        ),
        provider_request_id="req_MeterA",
        provider_response_sha256="d" * 64,
    )
    assert submitted.outbox_state == "submitted"
    assert submitted.attempt_count == 2
    replay = service.mark_usage_submitted(
        tenant_id="tenant-a",
        usage_id=usage.usage_id,
        response=_provider_readback(
            usage, created=usage.meter_event_timestamp + 60
        ),
        provider_request_id="req_MeterA",
        provider_response_sha256="d" * 64,
    )
    assert replay == submitted
    with pytest.raises(BillingReconciliationConflict, match="different provider"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            response=_provider_readback(
                usage, created=usage.meter_event_timestamp + 61
            ),
            provider_request_id="req_MeterOther",
            provider_response_sha256="e" * 64,
        )
    with pytest.raises(BillingReconciliationConflict, match="only pending"):
        service.record_delivery_failure(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            failure_code="provider_unreachable",
        )


def test_delivery_uncertain_is_durable_non_retryable_and_exactly_reconcilable() -> None:
    service, _, _ = _service()
    usage, _ = service.record_fleet_measurement(_measurement())

    uncertain = service.mark_delivery_uncertain(
        tenant_id="tenant-a",
        usage_id=usage.usage_id,
        failure_code="provider_timeout",
    )
    assert uncertain.outbox_state == "delivery_uncertain"
    assert uncertain.attempt_count == 1
    assert uncertain.last_attempt_at is not None
    assert service.pending_usage("tenant-a") == ()
    assert (
        service.mark_delivery_uncertain(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            failure_code="provider_timeout",
        )
        == uncertain
    )
    with pytest.raises(BillingReconciliationConflict, match="cannot be rewritten"):
        service.mark_delivery_uncertain(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            failure_code="network_error",
        )
    with pytest.raises(BillingReconciliationConflict, match="only pending"):
        service.record_delivery_failure(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            failure_code="provider_rejected",
        )

    created = usage.meter_event_timestamp + 60
    submitted = service.mark_usage_submitted(
        tenant_id="tenant-a",
        usage_id=usage.usage_id,
        response=_provider_readback(usage, created=created),
        provider_request_id="req_UncertainReadback",
        provider_response_sha256="9" * 64,
    )
    assert submitted.outbox_state == "submitted"
    assert submitted.attempt_count == 1
    assert submitted.last_failure_code is None
    assert submitted.submitted_at == datetime.fromtimestamp(created, tz=UTC).isoformat()
    assert submitted.last_attempt_at == submitted.submitted_at
    assert service.pending_usage("tenant-a") == ()


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda response: {**response, "id": "mtr_not_a_meter_event_field"}, "schema"),
        (lambda response: {**response, "created": str(response["created"])}, "integer"),
        (lambda response: {**response, "timestamp": str(response["timestamp"])}, "integer"),
        (
            lambda response: {
                **response,
                "payload": {**response["payload"], "value": 900_000},
            },
            "decimal string",
        ),
        (
            lambda response: {
                **response,
                "payload": {**response["payload"], "unexpected": "value"},
            },
            "payload schema",
        ),
    ],
)
def test_meter_event_response_requires_the_literal_stripe_v1_schema(
    mutator, message
) -> None:
    service, _, _ = _service()
    usage, _ = service.record_fleet_measurement(_measurement())
    response = _provider_readback(
        usage, created=usage.meter_event_timestamp + 60
    )
    with pytest.raises(BillingReconciliationError, match=message):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            response=mutator(response),
            provider_request_id="req_StripeSchema",
            provider_response_sha256="8" * 64,
        )
    current = service.get_usage("tenant-a", usage.usage_id)
    assert current is not None and current.outbox_state == "pending"


def test_delivery_failure_rejects_arbitrary_provider_data_without_leaking_it() -> None:
    service, _, _ = _service()
    usage, _ = service.record_fleet_measurement(_measurement())
    provider_secret = "req_PRIVATE_PROVIDER_ID_123"

    with pytest.raises(BillingReconciliationError, match="allowlisted"):
        service.record_delivery_failure(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            failure_code=provider_secret,
        )

    unchanged = service.get_usage("tenant-a", usage.usage_id)
    public = service.public_usage_projection(
        tenant_id="tenant-a", usage_id=usage.usage_id
    )
    assert unchanged is not None and unchanged.attempt_count == 0
    assert unchanged.last_failure_code is None
    assert public is not None and public["last_failure_code"] is None
    assert provider_secret not in json.dumps(public, sort_keys=True)


def test_public_projection_fails_closed_on_unknown_durable_failure_code() -> None:
    service, _, backend = _service()
    usage, _ = service.record_fleet_measurement(_measurement())
    existing = backend.get("tenant-a", USAGE_OUTBOX_KIND, usage.usage_id)
    assert existing is not None
    payload = dict(existing.payload)
    outbox = dict(payload["outbox"])
    outbox["last_failure_code"] = "req_PRIVATE_PROVIDER_ID_123"
    payload["outbox"] = outbox
    backend.put(
        existing.with_payload(payload), expected_version=existing.version
    )

    with pytest.raises(BillingReconciliationConflict, match="payload digest"):
        service.public_usage_projection(
            tenant_id="tenant-a", usage_id=usage.usage_id
        )


def test_resealed_unknown_fields_and_cross_index_tampering_fail_closed() -> None:
    service, _, backend = _service()
    usage, _ = service.record_fleet_measurement(_measurement())
    existing = backend.get("tenant-a", USAGE_OUTBOX_KIND, usage.usage_id)
    assert existing is not None
    payload = dict(existing.payload)
    payload["unbounded_provider_blob"] = "x" * 1000
    payload = _reseal(payload, "payload_sha256")
    backend.put(existing.with_payload(payload), expected_version=existing.version)
    with pytest.raises(BillingReconciliationConflict, match="usage payload schema"):
        service.get_usage("tenant-a", usage.usage_id)

    bounded, _, bounded_backend = _service()
    bounded_usage, _ = bounded.record_fleet_measurement(_measurement())
    bounded_record = bounded_backend.get(
        "tenant-a", USAGE_OUTBOX_KIND, bounded_usage.usage_id
    )
    assert bounded_record is not None
    bounded_payload = dict(bounded_record.payload)
    bounded_payload["receipt_issuer"] = "x" * 500_001
    bounded_payload = _reseal(bounded_payload, "payload_sha256")
    bounded_backend.put(
        bounded_record.with_payload(bounded_payload),
        expected_version=bounded_record.version,
    )
    with pytest.raises(BillingReconciliationConflict, match="safe bounds"):
        bounded.get_usage("tenant-a", bounded_usage.usage_id)

    second, _, second_backend = _service()
    second_usage, _ = second.record_fleet_measurement(_measurement())
    receipt_indexes = second_backend.list(
        BILLING_RECONCILIATION_PLATFORM_TENANT, USAGE_RECEIPT_INDEX_KIND
    )
    assert len(receipt_indexes) == 1
    receipt_index = receipt_indexes[0]
    index_payload = dict(receipt_index.payload)
    index_payload["tenant_id"] = "tenant-attacker"
    index_payload = _reseal(index_payload, "index_sha256")
    second_backend.put(
        receipt_index.with_payload(index_payload),
        expected_version=receipt_index.version,
    )
    with pytest.raises(BillingReconciliationConflict, match="contradictory facts"):
        second.get_usage("tenant-a", second_usage.usage_id)


def test_resealed_provider_response_facts_still_self_verify() -> None:
    service, _, backend = _service()
    usage = _submit(service, _measurement())
    existing = backend.get("tenant-a", USAGE_OUTBOX_KIND, usage.usage_id)
    assert existing is not None
    payload = dict(existing.payload)
    outbox = dict(payload["outbox"])
    outbox["provider_response_facts_sha256"] = "0" * 64
    payload["outbox"] = outbox
    payload = _reseal(payload, "payload_sha256")
    backend.put(existing.with_payload(payload), expected_version=existing.version)
    with pytest.raises(
        BillingReconciliationConflict,
        match="meter-event response facts digest",
    ):
        service.get_usage("tenant-a", usage.usage_id)


def test_provider_request_receipts_bind_to_one_usage() -> None:
    service, _, _ = _service()
    _submit(service, _measurement(), event_id="Shared")
    second_measurement = _measurement(
        run_id="run-b", worker_id="worker-b", receipt_char="b"
    )
    second, _ = service.record_fleet_measurement(second_measurement)
    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=second.usage_id,
            response=_provider_readback(
                second, created=second.meter_event_timestamp + 60
            ),
            provider_request_id="req_Shared",
            provider_response_sha256="b" * 64,
        )


def test_submission_time_and_provider_meter_readback_must_be_exact() -> None:
    service, _, _ = _service()
    measurement = _measurement()
    usage, _ = service.record_fleet_measurement(measurement)
    readback = _provider_readback(
        usage, created=usage.meter_event_timestamp + 60
    )
    with pytest.raises(BillingReconciliationError, match="predate"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            response={**readback, "created": usage.meter_event_timestamp - 1},
            provider_request_id="req_Time",
            provider_response_sha256="d" * 64,
        )
    with pytest.raises(BillingReconciliationConflict, match="readback"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            provider_request_id="req_Time",
            response={
                **readback,
                "timestamp": usage.meter_event_timestamp + 1,
            },
            provider_response_sha256="d" * 64,
        )
    with pytest.raises(BillingReconciliationConflict, match="readback"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            provider_request_id="req_Time",
            response={
                **readback,
                "payload": {
                    **readback["payload"],
                    "stripe_customer_id": "cus_Attacker",
                },
            },
            provider_response_sha256="d" * 64,
        )
    with pytest.raises(BillingReconciliationError, match="provider_response_sha256"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            response=readback,
            provider_request_id="req_Time",
            provider_response_sha256="not-a-digest",
        )
    with pytest.raises(BillingReconciliationConflict, match="readback"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            provider_request_id="req_Time",
            response={
                **readback,
                "payload": {**readback["payload"], "value": "899999"},
            },
            provider_response_sha256="d" * 64,
        )


def test_live_provider_acknowledgements_require_request_receipts() -> None:
    service, _, _ = _service()
    measurement = _measurement()
    usage, _ = service.record_fleet_measurement(measurement)
    with pytest.raises(BillingReconciliationError, match="request receipt"):
        service.mark_usage_submitted(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
            provider_request_id=None,
            response=_provider_readback(
                usage, created=usage.meter_event_timestamp + 60
            ),
            provider_response_sha256="d" * 64,
        )
    assert service.get_usage("tenant-a", usage.usage_id).outbox_state == "pending"

    _submit(service, measurement)
    with pytest.raises(BillingReconciliationError, match="request receipt"):
        service.reconcile_paid_invoice(
            replace(_invoice(), provider_request_id=None)
        )


def test_live_public_evidence_rejects_durable_records_without_request_receipts() -> None:
    service, _, backend = _service()
    usage = _submit(service, _measurement())
    usage_record = backend.get("tenant-a", USAGE_OUTBOX_KIND, usage.usage_id)
    usage_payload = dict(usage_record.payload)
    usage_outbox = dict(usage_payload["outbox"])
    usage_outbox["provider_request_id"] = None
    usage_payload["outbox"] = usage_outbox
    backend.put(
        usage_record.with_payload(usage_payload),
        expected_version=usage_record.version,
    )
    with pytest.raises(BillingReconciliationConflict, match="payload digest"):
        service.public_usage_projection(
            tenant_id="tenant-a", usage_id=usage.usage_id
        )

    invoice_service, _, invoice_backend = _service()
    _submit(invoice_service, _measurement())
    invoice = invoice_service.reconcile_paid_invoice(_invoice())
    invoice_record = invoice_backend.get(
        "tenant-a", PAID_INVOICE_KIND, invoice.invoice_record_id
    )
    invoice_payload = dict(invoice_record.payload)
    invoice_payload["provider_request_id"] = None
    observations = [
        dict(observation)
        for observation in invoice_payload["provider_observations"]
    ]
    observations[-1]["provider_request_id"] = None
    invoice_payload["provider_observations"] = observations
    invoice_backend.put(
        invoice_record.with_payload(invoice_payload),
        expected_version=invoice_record.version,
    )
    with pytest.raises(BillingReconciliationConflict, match="payload digest"):
        invoice_service.public_invoice_projection(
            tenant_id="tenant-a", invoice_record_id=invoice.invoice_record_id
        )


def test_pending_usage_is_bounded_and_stably_ordered() -> None:
    service, _, _ = _service()
    later, _ = service.record_fleet_measurement(
        _measurement(
            run_id="run-later",
            started_at=START + timedelta(hours=2),
            ended_at=END + timedelta(hours=2),
            receipt_char="d",
        )
    )
    earlier, _ = service.record_fleet_measurement(_measurement())
    assert [row.usage_id for row in service.pending_usage("tenant-a", limit=1)] == [
        earlier.usage_id
    ]
    assert later.usage_id != earlier.usage_id
    with pytest.raises(BillingReconciliationError, match="1..1000"):
        service.pending_usage("tenant-a", limit=0)


def test_usage_and_outbox_survive_sqlite_restart(tmp_path) -> None:
    path = tmp_path / "billing-reconciliation.db"
    first_backend = SqliteStateStore(path)
    first, _, _ = _service(first_backend)
    submitted = _submit(first, _measurement())
    first_backend.close()

    second_backend = SqliteStateStore(path)
    entitlements = BillingEntitlementStore(second_backend)
    second = BillingReconciliationStore(
        second_backend,
        entitlements,
        provider_reference_hash_key=HASH_KEY,
        usage_price_id=PRICE_ID,
        meter_event_name=METER_NAME,
        meter_event_version=METER_VERSION,
        currency="usd",
        livemode=True,
        customer_receipt_allowed_hosts=(RECEIPT_HOST,),
    )
    restored = second.get_usage("tenant-a", submitted.usage_id)
    assert restored is not None
    assert restored.outbox_state == "submitted"
    assert restored.provider_request_id == "req_MeterA"
    assert restored.meter_event_identifier == submitted.meter_event_identifier
    second_backend.close()


def test_paid_invoice_matches_only_exact_submitted_usage() -> None:
    service, _, _ = _service()
    usage = _submit(service, _measurement())
    reconciled = service.reconcile_paid_invoice(_invoice())
    assert reconciled.reconciliation_state == "matched"
    assert reconciled.provider_quantity_milliseconds == 900_000
    assert reconciled.local_quantity_milliseconds == 900_000
    assert reconciled.usage_ids == (usage.usage_id,)
    assert reconciled.reconciled_at is not None
    assert service.reconcile_paid_invoice(_invoice()) == reconciled


def test_matched_invoice_allows_fresh_exact_event_readback_without_rewrite() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    matched = service.reconcile_paid_invoice(_invoice())
    refreshed_at = (START + timedelta(days=2, minutes=4)).isoformat()
    refreshed = replace(
        _invoice(),
        provider_request_id="req_InvoiceFreshReplay",
        provider_snapshot_sha256="1" * 64,
        provider_snapshot_retrieved_at=refreshed_at,
        invoice_pdf_retrieved_at=refreshed_at,
    )

    replay = service.reconcile_paid_invoice(refreshed)
    assert replay.reconciliation_state == "matched"
    assert replay.usage_ids == matched.usage_ids
    assert replay.usage_set_sha256 == matched.usage_set_sha256
    assert replay.reconciled_at == matched.reconciled_at
    assert replay.ledger_version == matched.ledger_version + 1
    assert replay.provider_observation_count == 2
    assert replay.provider_snapshot_retrieved_at == refreshed_at


def test_provider_acceptance_must_strictly_precede_invoice_finalization() -> None:
    service, _, _ = _service()
    measurement = _measurement()
    usage, _ = service.record_fleet_measurement(measurement)
    finalized_at = _invoice().status_transitions_finalized_at
    service.mark_usage_submitted(
        tenant_id="tenant-a",
        usage_id=usage.usage_id,
        response=_provider_readback(usage, created=finalized_at),
        provider_request_id="req_AtFinalization",
        provider_response_sha256="6" * 64,
    )

    with pytest.raises(BillingReconciliationUnresolved) as unresolved:
        service.reconcile_paid_invoice(_invoice())
    assert unresolved.value.expected_quantity == 0
    assert unresolved.value.provider_quantity == 900_000


def test_usage_measurement_must_be_fully_contained_in_invoice_line_period() -> None:
    service, _, _ = _service()
    straddling = _measurement(
        started_at=START - timedelta(seconds=1),
        ended_at=END,
    )
    _submit(service, straddling)
    with pytest.raises(BillingReconciliationConflict, match="fully contained"):
        service.reconcile_paid_invoice(_invoice())


@pytest.mark.parametrize(
    "field",
    ["usage_period_start", "usage_period_end", "paid_at"],
)
def test_stripe_invoice_times_must_be_whole_second_canonical(field) -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    fractional = (START + timedelta(microseconds=1)).isoformat()
    with pytest.raises(BillingReconciliationError, match="whole-second"):
        service.reconcile_paid_invoice(
            replace(_invoice(), **{field: fractional})
        )


@pytest.mark.parametrize(
    "url",
    [
        f"https://user@{RECEIPT_HOST}/invoice.pdf",
        f"https://{RECEIPT_HOST}:443/invoice.pdf",
        f"https://{RECEIPT_HOST}/a/../invoice.pdf",
        f"https://{RECEIPT_HOST}/invoice.pdf#fragment",
        f"https://{RECEIPT_HOST.upper()}/invoice.pdf",
        f"http://{RECEIPT_HOST}/invoice.pdf",
    ],
)
def test_customer_receipt_urls_are_exact_canonical_https(url) -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    with pytest.raises(BillingReconciliationError, match="canonical|allowlist"):
        service.reconcile_paid_invoice(replace(_invoice(), invoice_pdf=url))


def test_invoice_period_uses_greatest_inner_second_with_half_open_boundaries() -> None:
    service, _, _ = _service()
    at_period_start = _measurement(
        run_id="run-period-start",
        worker_id="worker-period-start",
        quantity=111,
        started_at=START - timedelta(hours=1),
        ended_at=START,
        receipt_char="d",
    )
    at_period_end = _measurement(
        run_id="run-period-end",
        worker_id="worker-period-end",
        quantity=222,
        started_at=START + timedelta(days=1, hours=-1),
        ended_at=START + timedelta(days=1),
        receipt_char="e",
    )
    included = _submit(
        service, at_period_start, event_id="mtr_evt_period_start"
    )
    excluded = _submit(service, at_period_end, event_id="mtr_evt_period_end")

    reconciled = service.reconcile_paid_invoice(_invoice(quantity=222))
    assert reconciled.usage_ids == (excluded.usage_id,)
    assert included.usage_id not in reconciled.usage_ids
    assert reconciled.local_quantity_milliseconds == 222


def test_unresolved_invoice_is_durable_and_can_converge_after_outbox_ack() -> None:
    service, _, backend = _service()
    usage, _ = service.record_fleet_measurement(_measurement())
    with pytest.raises(BillingReconciliationUnresolved) as mismatch:
        service.reconcile_paid_invoice(_invoice())
    assert mismatch.value.expected_quantity == 0
    unresolved_rows = backend.list("tenant-a", PAID_INVOICE_KIND)
    assert len(unresolved_rows) == 1
    assert unresolved_rows[0].payload["reconciliation_state"] == "unresolved"

    service.mark_usage_submitted(
        tenant_id="tenant-a",
        usage_id=usage.usage_id,
        response=_provider_readback(
            usage, created=usage.meter_event_timestamp + 60
        ),
        provider_request_id="req_MeterA",
        provider_response_sha256="d" * 64,
    )
    matched = service.reconcile_paid_invoice(_invoice())
    assert matched.reconciliation_state == "matched"
    assert matched.ledger_version == 2


def test_unresolved_invoice_observations_converge_and_reject_stale_evidence() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    first = _invoice(quantity=800_000)
    with pytest.raises(BillingReconciliationUnresolved):
        service.reconcile_paid_invoice(first)

    reused_request = replace(
        first,
        usage_quantity_milliseconds=900_000,
        provider_snapshot_sha256="d" * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=4)
        ).isoformat(),
    )
    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.reconcile_paid_invoice(reused_request)

    stale = replace(
        first,
        provider_event_id="evt_invoice_stale",
        provider_event_created=int(
            (START + timedelta(days=2, seconds=30)).timestamp()
        ),
        provider_request_id="req_invoice_stale",
        raw_event_sha256="e" * 64,
        provider_snapshot_sha256="e" * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=5)
        ).isoformat(),
    )
    with pytest.raises(BillingReconciliationConflict, match="stale provider event"):
        service.reconcile_paid_invoice(stale)

    refreshed = replace(
        first,
        usage_quantity_milliseconds=900_000,
        provider_request_id="req_invoice_refresh",
        provider_snapshot_sha256="d" * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=4)
        ).isoformat(),
    )
    matched = service.reconcile_paid_invoice(refreshed)
    assert matched.reconciliation_state == "matched"
    assert matched.provider_observation_count == 2
    assert matched.provider_snapshot_sha256 == "d" * 64


def test_matched_invoice_cannot_downgrade_to_unresolved() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    matched = service.reconcile_paid_invoice(_invoice())
    downgrade = replace(
        _invoice(),
        usage_quantity_milliseconds=700_000,
        provider_request_id="req_invoice_downgrade",
        provider_snapshot_sha256="d" * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=4)
        ).isoformat(),
    )
    with pytest.raises(BillingReconciliationConflict, match="immutable"):
        service.reconcile_paid_invoice(downgrade)

    current = service.get_invoice("tenant-a", matched.invoice_record_id)
    assert current == matched
    assert current.reconciliation_state == "matched"
    assert current.provider_observation_count == 1


def test_matched_invoice_cannot_reserve_a_different_late_usage_set() -> None:
    service, _, backend = _service()
    first = _submit(service, _measurement())
    matched = service.reconcile_paid_invoice(_invoice())
    late_measurement = _measurement(
        run_id="run-late",
        worker_id="worker-late",
        quantity=100_000,
        started_at=END,
        ended_at=END + timedelta(hours=1),
        receipt_char="d",
    )
    late = _submit(service, late_measurement, event_id="mtr_evt_late")
    changed_set = replace(
        _invoice(),
        usage_quantity_milliseconds=1_000_000,
        provider_request_id="req_invoice_changed_set",
        provider_snapshot_sha256="d" * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=4)
        ).isoformat(),
    )
    with pytest.raises(BillingReconciliationConflict, match="immutable"):
        service.reconcile_paid_invoice(changed_set)

    with pytest.raises(BillingReconciliationConflict, match="usage-set digest"):
        service.get_invoice("tenant-a", matched.invoice_record_id)
    assert (
        backend.get(
            BILLING_RECONCILIATION_PLATFORM_TENANT,
            USAGE_INVOICE_INDEX_KIND,
            late.usage_id,
        )
        is None
    )


def test_matched_invoice_rejects_a_newer_provider_event() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    matched = service.reconcile_paid_invoice(_invoice())
    newer_event = replace(
        _invoice(),
        provider_event_id="evt_invoice_after_match",
        provider_event_created=int(
            (START + timedelta(days=2, minutes=5)).timestamp()
        ),
        provider_request_id="req_invoice_after_match",
        raw_event_sha256="1" * 64,
        provider_snapshot_sha256="2" * 64,
        provider_snapshot_retrieved_at=(
            START + timedelta(days=2, minutes=6)
        ).isoformat(),
    )
    with pytest.raises(BillingReconciliationConflict, match="immutable"):
        service.reconcile_paid_invoice(newer_event)

    current = service.get_invoice("tenant-a", matched.invoice_record_id)
    assert current == matched
    assert current.provider_event_id == "evt_InvoicePaidA"
    assert current.provider_observation_count == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("usage_price_id", "price_wrong", "usage price"),
        ("meter_event_name", "wrong.meter", "meter contract"),
        ("meter_event_version", "v2", "meter contract"),
        ("currency", "eur", "currency"),
        ("livemode", False, "livemode"),
        ("provider_paid", False, "provider-paid"),
    ],
)
def test_invoice_contract_dimensions_fail_closed(field, value, message) -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    with pytest.raises(BillingReconciliationError, match=message):
        service.reconcile_paid_invoice(replace(_invoice(), **{field: value}))


@pytest.mark.parametrize(
    ("field", "value", "kind"),
    [
        ("external_invoice_id", "cus_wrong_type", "invoice"),
        ("external_customer_id", "sub_wrong_type", "customer"),
        ("external_subscription_id", "in_wrong_type", "subscription"),
        ("provider_event_id", "req_wrong_type", "event"),
        ("provider_request_id", "evt_wrong_type", "request"),
        ("usage_price_id", "prod_wrong_type", "price"),
        ("external_invoice_id", 123, "invoice"),
    ],
)
def test_invoice_provider_identifiers_are_strictly_typed(field, value, kind) -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    with pytest.raises(BillingReconciliationError, match=f"Stripe {kind} id"):
        service.reconcile_paid_invoice(replace(_invoice(), **{field: value}))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("invoice_pdf", "", "canonical HTTPS"),
        (
            "invoice_pdf",
            "https://attacker.example/invoice.pdf",
            "allowlist",
        ),
        ("invoice_pdf_http_status", 302, "HTTP 200"),
        ("invoice_pdf_content_type", "text/html", "application/pdf"),
        ("invoice_pdf_size_bytes", 10_000_001, "exceeds"),
        ("invoice_pdf_sha256", "not-a-digest", "SHA-256"),
        (
            "invoice_pdf_retrieved_at",
            (START + timedelta(days=1)).isoformat(),
            "invoice PDF retrieval time",
        ),
    ],
)
def test_customer_receipt_proof_is_required_bounded_and_allowlisted(
    field, value, message
) -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    with pytest.raises(BillingReconciliationError, match=message):
        service.reconcile_paid_invoice(replace(_invoice(), **{field: value}))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"amount_paid_minor": 1_233}, "equal amount_due"),
        (
            {"paid_at": (START + timedelta(hours=12)).isoformat()},
            "predate the usage line period end",
        ),
        (
            {
                "provider_event_created": int(
                    (START + timedelta(days=1, hours=23)).timestamp()
                )
            },
            "event cannot predate invoice payment",
        ),
        (
            {
                "provider_snapshot_retrieved_at": (
                    START + timedelta(days=2, seconds=30)
                ).isoformat()
            },
            "snapshot retrieval time",
        ),
    ],
)
def test_paid_invoice_amount_and_time_ordering_fail_closed(changes, message) -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    with pytest.raises(BillingReconciliationError, match=message):
        service.reconcile_paid_invoice(replace(_invoice(), **changes))


def test_invoice_snapshot_and_customer_pdf_must_be_fresh_readbacks() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    older_paid_at = (START + timedelta(days=2, minutes=-9)).isoformat()
    older_event_created = int(
        (START + timedelta(days=2, minutes=-8)).timestamp()
    )
    stale_snapshot_at = (START + timedelta(days=2, minutes=-7)).isoformat()
    with pytest.raises(BillingReconciliationError, match="snapshot is not a fresh"):
        service.reconcile_paid_invoice(
            replace(
                _invoice(),
                paid_at=older_paid_at,
                provider_event_created=older_event_created,
                provider_snapshot_retrieved_at=stale_snapshot_at,
            )
        )

    with pytest.raises(BillingReconciliationError, match="PDF is not a fresh"):
        service.reconcile_paid_invoice(
            replace(
                _invoice(),
                paid_at=older_paid_at,
                provider_event_created=older_event_created,
                invoice_pdf_retrieved_at=(
                    START + timedelta(days=2, minutes=-6)
                ).isoformat(),
            )
        )


def test_zero_due_invoice_can_reconcile_when_metered_quantity_matches() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    reconciled = service.reconcile_paid_invoice(
        replace(_invoice(), amount_due_minor=0, amount_paid_minor=0)
    )
    assert reconciled.reconciliation_state == "matched"
    assert reconciled.amount_due_minor == 0
    assert reconciled.amount_paid_minor == 0


def test_invoice_customer_subscription_binding_is_not_metadata_trusted() -> None:
    service, _, _ = _service(
        tenants=(
            ("tenant-a", "acct-a", "cus_a", "sub_a"),
            ("tenant-b", "acct-b", "cus_b", "sub_b"),
        )
    )
    _submit(service, _measurement())
    with pytest.raises(BillingReconciliationConflict, match="subscription binding"):
        service.reconcile_paid_invoice(
            _invoice(customer_id="cus_a", subscription_id="sub_b")
        )
    with pytest.raises(BillingReconciliationError, match="not bound"):
        service.reconcile_paid_invoice(_invoice(customer_id="cus_unknown"))


def test_invoice_does_not_count_usage_from_another_meter_contract() -> None:
    original, entitlements, backend = _service()
    _submit(original, _measurement())
    upgraded = BillingReconciliationStore(
        backend,
        entitlements,
        provider_reference_hash_key=HASH_KEY,
        usage_price_id=PRICE_ID,
        meter_event_name=METER_NAME,
        meter_event_version="cas_meter.v2",
        currency="usd",
        livemode=True,
        customer_receipt_allowed_hosts=(RECEIPT_HOST,),
    )
    with pytest.raises(BillingReconciliationUnresolved) as mismatch:
        upgraded.reconcile_paid_invoice(
            replace(_invoice(), meter_event_version="cas_meter.v2")
        )
    assert mismatch.value.expected_quantity == 0


def test_provider_event_replay_with_different_bytes_is_rejected() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    service.reconcile_paid_invoice(_invoice())
    with pytest.raises(BillingReconciliationConflict, match="contradictory"):
        service.reconcile_paid_invoice(_invoice(raw_char="e"))


def test_provider_event_and_request_receipts_cannot_cross_tenants_or_subjects() -> None:
    service, _, _ = _service(
        tenants=(
            ("tenant-a", "acct-a", "cus_a", "sub_a"),
            ("tenant-b", "acct-b", "cus_b", "sub_b"),
        )
    )
    measurement_a = _measurement()
    measurement_b = _measurement(
        tenant_id="tenant-b",
        account_id="acct-b",
        run_id="run-b",
        worker_id="worker-b",
        receipt_char="b",
    )
    _submit(service, measurement_a, event_id="mtr_evt_tenant_a")
    usage_b, _ = service.record_fleet_measurement(measurement_b)

    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.mark_usage_submitted(
            tenant_id="tenant-b",
            usage_id=usage_b.usage_id,
            response=_provider_readback(
                usage_b, created=usage_b.meter_event_timestamp + 60
            ),
            provider_request_id="req_mtr_evt_tenant_a",
            provider_response_sha256="7" * 64,
        )
    _submit(service, measurement_b, event_id="mtr_evt_tenant_b")

    service.reconcile_paid_invoice(
        _invoice(
            invoice_id="in_tenant_a",
            customer_id="cus_a",
            subscription_id="sub_a",
            event_id="evt_invoice_tenant_a",
        )
    )
    tenant_b_invoice = _invoice(
        invoice_id="in_tenant_b",
        customer_id="cus_b",
        subscription_id="sub_b",
        event_id="evt_invoice_tenant_a",
        snapshot_char="3",
    )
    tenant_b_invoice = replace(
        tenant_b_invoice,
        provider_request_id="req_invoice_tenant_b_unique",
    )
    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.reconcile_paid_invoice(tenant_b_invoice)

    request_replay = replace(
        tenant_b_invoice,
        provider_event_id="evt_invoice_tenant_b_unique",
        provider_request_id="req_InvoiceA",
        raw_event_sha256="4" * 64,
    )
    with pytest.raises(BillingReconciliationConflict, match="already bound"):
        service.reconcile_paid_invoice(request_replay)


def test_submitted_usage_cannot_be_reconciled_to_two_invoices() -> None:
    service, _, _ = _service()
    _submit(service, _measurement())
    service.reconcile_paid_invoice(_invoice())
    with pytest.raises(BillingReconciliationConflict, match="another paid invoice"):
        service.reconcile_paid_invoice(
            replace(
                _invoice(
                    invoice_id="in_b",
                    event_id="evt_invoice_b",
                    raw_char="d",
                    snapshot_char="e",
                ),
                provider_request_id="req_invoice_b",
            )
        )


def test_public_projections_hmac_every_provider_identifier() -> None:
    service, _, _ = _service()
    usage = _submit(service, _measurement())
    invoice = service.reconcile_paid_invoice(_invoice())
    usage_public = service.public_usage_projection(
        tenant_id="tenant-a", usage_id=usage.usage_id
    )
    invoice_public = service.public_invoice_projection(
        tenant_id="tenant-a", invoice_record_id=invoice.invoice_record_id
    )
    assert usage_public is not None
    assert invoice_public is not None
    encoded = json.dumps([usage_public, invoice_public], sort_keys=True)
    for raw_provider_id in (
        "cus_CustomerA",
        "sub_SubscriptionA",
        "req_MeterA",
        "in_InvoiceA",
        "evt_InvoicePaidA",
        "req_InvoiceA",
        f"https://{RECEIPT_HOST}/in_InvoiceA",
        f"https://{RECEIPT_HOST}/in_InvoiceA.pdf",
        PRICE_ID,
    ):
        assert raw_provider_id not in encoded
    refs = [
        value
        for projection in (usage_public, invoice_public)
        for key, value in projection.items()
        if key.endswith("_ref") and value is not None
    ]
    assert refs
    assert all(str(value).startswith("hmac-sha256:") for value in refs)
    assert "cus_CustomerA" not in repr(usage)
    assert "sub_SubscriptionA" not in repr(usage)
    assert "req_MeterA" not in repr(usage)
    assert "in_InvoiceA" not in repr(invoice)
    assert "evt_InvoicePaidA" not in repr(invoice)
    assert f"https://{RECEIPT_HOST}/in_InvoiceA.pdf" not in repr(invoice)
    assert str(invoice_public["invoice_pdf_ref"]).startswith(
        "hmac-sha256:"
    )


def test_hmac_provider_refs_are_deployment_keyed() -> None:
    first, _, _ = _service(key=HASH_KEY)
    second, _, _ = _service(key="another-dedicated-provider-reference-key-012345")
    first_usage = _submit(first, _measurement())
    second_usage = _submit(second, _measurement())
    first_public = first.public_usage_projection(
        tenant_id="tenant-a", usage_id=first_usage.usage_id
    )
    second_public = second.public_usage_projection(
        tenant_id="tenant-a", usage_id=second_usage.usage_id
    )
    assert first_public is not None and second_public is not None
    assert first_public["customer_ref"] != second_public["customer_ref"]
