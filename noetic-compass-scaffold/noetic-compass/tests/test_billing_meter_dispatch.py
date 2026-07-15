from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib

import pytest

from api.services.billing_entitlements import BillingEntitlementStore
from api.services.billing_meter_dispatch import (
    MeterEventProviderContract,
    MeterEventProviderReceipt,
    StripeMeterEventDispatcher,
)
from api.services.billing_reconciliation import (
    BillingReconciliationConflict,
    BillingReconciliationError,
    BillingReconciliationStore,
    FleetUsageMeasurement,
)
from api.services.production.state_substrate import InMemoryStateStore


class _Provider:
    def __init__(
        self,
        *,
        fail: bool = False,
        gate: asyncio.Event | None = None,
        usage_price_id: str = "price_UsageMilliseconds",
        livemode: bool = False,
    ):
        self.fail = fail
        self.gate = gate
        self.usage_price_id = usage_price_id
        self.livemode = livemode
        self.calls: list[dict[str, object]] = []
        self.started = asyncio.Event()

    @property
    def meter_event_contract(self) -> MeterEventProviderContract:
        return MeterEventProviderContract(
            usage_price_id=self.usage_price_id,
            livemode=self.livemode,
        )

    async def submit_meter_event(self, *, request):
        self.calls.append(dict(request))
        self.started.set()
        if self.gate is not None:
            await self.gate.wait()
        if self.fail:
            raise TimeoutError("simulated ambiguous network timeout")
        response = {
            "object": "billing.meter_event",
            "created": max(
                int(datetime.now(UTC).timestamp()), int(request["timestamp"])
            ),
            "event_name": request["event_name"],
            "identifier": request["identifier"],
            "livemode": self.livemode,
            "payload": request["payload"],
            "timestamp": request["timestamp"],
        }
        return MeterEventProviderReceipt(
            response=response,
            provider_request_id="req_MeterDispatch",
            response_sha256=hashlib.sha256(b"provider-response").hexdigest(),
        )


def _service(
    *,
    tenants=("tenant-a",),
    backend: InMemoryStateStore | None = None,
    seed_entitlements: bool = True,
    usage_price_id: str = "price_UsageMilliseconds",
    meter_event_name: str = "cas.accelerator_milliseconds",
    meter_event_version: str = "cas_meter.v1",
    currency: str = "usd",
    livemode: bool = False,
):
    backend = backend if backend is not None else InMemoryStateStore()
    entitlements = BillingEntitlementStore(backend)
    now = datetime.now(UTC)
    if seed_entitlements:
        for suffix, tenant in enumerate(tenants):
            account = f"acct-{suffix}"
            entitlements.grant_manual_comped(
                tenant_id=tenant,
                billing_account_id=account,
                expires_at=(now + timedelta(days=30)).isoformat(),
            )
            entitlements.apply_stripe_subscription(
                tenant_id=tenant,
                plan_id="professional_live",
                status="active",
                external_customer_id=f"cus_Customer{suffix}",
                external_subscription_id=f"sub_Subscription{suffix}",
                event_id=f"evt_Subscription{suffix}",
                event_created=suffix + 1,
                current_period_start=(now - timedelta(days=1)).isoformat(),
                current_period_end=(now + timedelta(days=30)).isoformat(),
                cancel_at_period_end=False,
            )
    return BillingReconciliationStore(
        backend,
        entitlements,
        provider_reference_hash_key="provider-reference-key-0123456789-ABCDE",
        usage_price_id=usage_price_id,
        meter_event_name=meter_event_name,
        meter_event_version=meter_event_version,
        currency=currency,
        livemode=livemode,
        customer_receipt_allowed_hosts=("receipts.stripe.test",),
    )


def _record(service, *, tenant="tenant-a", suffix=0):
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=5)
    return service.record_fleet_measurement(
        FleetUsageMeasurement(
            tenant_id=tenant,
            billing_account_id=f"acct-{suffix}",
            run_id=f"run-{suffix}",
            worker_id=f"worker-{suffix}",
            worker_provider_id="runpod-test",
            model_id="EleutherAI/pythia-160m",
            accelerator_milliseconds=1000,
            accelerator_count=1,
            measurement_started_at=now.isoformat(),
            measurement_ended_at=(now + timedelta(seconds=2)).isoformat(),
            receipt_sha256=hashlib.sha256(
                f"receipt-{tenant}-{suffix}".encode()
            ).hexdigest(),
            receipt_schema_version="cas_harness_live_worker_measurement_receipt.v1",
            receipt_size_bytes=1024,
            receipt_issuer="atlas-live-worker",
        )
    )[0]


@pytest.mark.asyncio
async def test_dispatch_reserves_before_one_provider_attempt_and_acknowledges() -> None:
    service = _service()
    usage = _record(service)
    provider = _Provider()
    dispatcher = StripeMeterEventDispatcher(
        reconciliation=service,
        provider=provider,
    )

    result = await dispatcher.run_once()

    assert result.candidates == 1
    assert result.submitted == 1
    assert result.quarantined == 0
    assert len(provider.calls) == 1
    assert provider.calls[0] == usage.meter_event_request()
    assert provider.calls[0]["identifier"] == usage.meter_event_identifier
    stored = service.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "submitted"
    assert stored.attempt_count == 1


@pytest.mark.asyncio
async def test_concurrent_dispatchers_grant_exactly_one_provider_call() -> None:
    service = _service()
    usage = _record(service)
    release = asyncio.Event()
    first_provider = _Provider(gate=release)
    second_provider = _Provider()
    first = StripeMeterEventDispatcher(
        reconciliation=service, provider=first_provider
    )
    second = StripeMeterEventDispatcher(
        reconciliation=service, provider=second_provider
    )

    first_task = asyncio.create_task(first.run_once())
    await first_provider.started.wait()
    second_result = await second.run_once()
    release.set()
    first_result = await first_task

    assert len(first_provider.calls) + len(second_provider.calls) == 1
    assert first_result.submitted == 1
    assert second_result.submitted == 0
    assert second_result.skipped in {0, 1}
    assert service.get_usage("tenant-a", usage.usage_id).outbox_state == "submitted"


@pytest.mark.asyncio
async def test_timeout_is_quarantined_and_never_replayed_after_restart() -> None:
    service = _service()
    usage = _record(service)
    failing = _Provider(fail=True)
    first = StripeMeterEventDispatcher(reconciliation=service, provider=failing)

    result = await first.run_once()
    assert result.quarantined == 1
    assert len(failing.calls) == 1
    stored = service.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "delivery_uncertain"

    restarted_provider = _Provider()
    restarted = StripeMeterEventDispatcher(
        reconciliation=service, provider=restarted_provider
    )
    restarted_result = await restarted.run_once()
    assert restarted_result.candidates == 0
    assert restarted_provider.calls == []
    assert service.get_usage("tenant-a", usage.usage_id).outbox_state == "delivery_uncertain"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changed_field", "changed_value"),
    (
        ("livemode", True),
        ("meter_event_name", "cas.accelerator_seconds"),
        ("meter_event_version", "cas_meter.v2"),
        ("usage_price_id", "price_UsageMillisecondsV2"),
        ("currency", "eur"),
    ),
)
async def test_restart_contract_drift_refuses_pending_row_before_reservation(
    monkeypatch, changed_field: str, changed_value: object
) -> None:
    backend = InMemoryStateStore()
    original = _service(backend=backend)
    usage = _record(original)
    active_contract: dict[str, object] = {
        "usage_price_id": "price_UsageMilliseconds",
        "meter_event_name": "cas.accelerator_milliseconds",
        "meter_event_version": "cas_meter.v1",
        "currency": "usd",
        "livemode": False,
    }
    active_contract[changed_field] = changed_value
    restarted = _service(
        backend=backend,
        seed_entitlements=False,
        **active_contract,
    )
    provider = _Provider(
        usage_price_id=str(active_contract["usage_price_id"]),
        livemode=bool(active_contract["livemode"]),
    )
    reservation_calls = 0
    reserve = restarted.reserve_usage_delivery

    def tracked_reserve(**kwargs):
        nonlocal reservation_calls
        reservation_calls += 1
        return reserve(**kwargs)

    monkeypatch.setattr(restarted, "reserve_usage_delivery", tracked_reserve)
    dispatcher = StripeMeterEventDispatcher(
        reconciliation=restarted,
        provider=provider,
    )

    with pytest.raises(BillingReconciliationConflict, match=changed_field):
        await dispatcher.run_once()

    assert reservation_calls == 0
    assert provider.calls == []
    stored = restarted.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "pending"
    assert stored.attempt_count == 0

    # The durable service repeats the contract check inside its reservation
    # lock, so bypassing the dispatcher cannot create send authority either.
    monkeypatch.setattr(restarted, "reserve_usage_delivery", reserve)
    with pytest.raises(BillingReconciliationConflict, match=changed_field):
        restarted.reserve_usage_delivery(
            tenant_id="tenant-a",
            usage_id=usage.usage_id,
        )
    stored = restarted.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "pending"
    assert stored.attempt_count == 0


@pytest.mark.parametrize(
    "provider",
    (
        _Provider(livemode=True),
        _Provider(usage_price_id="price_UsageMillisecondsV2"),
    ),
)
def test_dispatcher_refuses_store_provider_contract_mismatch_before_scan(
    provider: _Provider,
) -> None:
    service = _service()
    usage = _record(service)

    with pytest.raises(BillingReconciliationConflict, match="provider contract"):
        StripeMeterEventDispatcher(
            reconciliation=service,
            provider=provider,
        )

    assert provider.calls == []
    stored = service.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "pending"
    assert stored.attempt_count == 0


@pytest.mark.asyncio
async def test_cancellation_after_reservation_stays_non_replayable() -> None:
    service = _service()
    usage = _record(service)
    release = asyncio.Event()
    provider = _Provider(gate=release)
    dispatcher = StripeMeterEventDispatcher(
        reconciliation=service, provider=provider
    )

    task = asyncio.create_task(dispatcher.run_once())
    await provider.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    stored = service.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "delivery_uncertain"
    restarted_provider = _Provider()
    await StripeMeterEventDispatcher(
        reconciliation=service, provider=restarted_provider
    ).run_once()
    assert restarted_provider.calls == []


@pytest.mark.asyncio
async def test_acknowledgement_write_failure_underbills_without_resend(monkeypatch) -> None:
    service = _service()
    usage = _record(service)
    provider = _Provider()
    original = service.mark_usage_submitted
    monkeypatch.setattr(
        service,
        "mark_usage_submitted",
        lambda **_kwargs: (_ for _ in ()).throw(
            BillingReconciliationError("simulated durable acknowledgement outage")
        ),
    )
    result = await StripeMeterEventDispatcher(
        reconciliation=service, provider=provider
    ).run_once()
    monkeypatch.setattr(service, "mark_usage_submitted", original)

    assert result.quarantined == 1
    assert len(provider.calls) == 1
    assert service.get_usage("tenant-a", usage.usage_id).outbox_state == "delivery_uncertain"
    replacement = _Provider()
    await StripeMeterEventDispatcher(
        reconciliation=service, provider=replacement
    ).run_once()
    assert replacement.calls == []


@pytest.mark.asyncio
async def test_preflight_retries_are_bounded_and_happen_before_provider(monkeypatch) -> None:
    service = _service()
    _record(service)
    provider = _Provider()
    original = service.pending_usage_global
    attempts = 0

    def flaky(*, limit):
        nonlocal attempts
        attempts += 1
        assert provider.calls == []
        if attempts < 3:
            raise BillingReconciliationError("temporary preflight read outage")
        return original(limit=limit)

    monkeypatch.setattr(service, "pending_usage_global", flaky)
    dispatcher = StripeMeterEventDispatcher(
        reconciliation=service,
        provider=provider,
        preflight_retries=3,
        preflight_backoff_seconds=0,
    )
    result = await dispatcher.run_once()

    assert attempts == 3
    assert result.submitted == 1
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_exhausted_preflight_never_reserves_or_calls_provider(monkeypatch) -> None:
    service = _service()
    usage = _record(service)
    provider = _Provider()
    attempts = 0

    def unavailable(*, limit):
        nonlocal attempts
        attempts += 1
        raise BillingReconciliationError(f"read outage {limit}")

    monkeypatch.setattr(service, "pending_usage_global", unavailable)
    dispatcher = StripeMeterEventDispatcher(
        reconciliation=service,
        provider=provider,
        preflight_retries=3,
        preflight_backoff_seconds=0,
    )
    with pytest.raises(BillingReconciliationError, match="read outage"):
        await dispatcher.run_once()

    assert attempts == 3
    assert provider.calls == []
    stored = service.get_usage("tenant-a", usage.usage_id)
    assert stored is not None and stored.outbox_state == "pending"
    assert stored.attempt_count == 0


def test_global_candidate_scan_is_tenant_safe_and_bounded() -> None:
    service = _service(tenants=("tenant-a", "tenant-b"))
    first = _record(service, tenant="tenant-a", suffix=0)
    second = _record(service, tenant="tenant-b", suffix=1)

    candidates = service.pending_usage_global(limit=2)
    assert {(row.tenant_id, row.usage_id) for row in candidates} == {
        ("tenant-a", first.usage_id),
        ("tenant-b", second.usage_id),
    }
    assert service.pending_usage_global(limit=1) in {(first,), (second,)}
