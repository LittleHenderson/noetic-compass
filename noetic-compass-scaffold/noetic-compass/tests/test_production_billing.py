"""Honesty tests for the workstream-08 billing scaffold (``api/services/production/billing.py``).

The single most important property under test: **the stub meter refuses to claim
``COST_METERED`` from anything but a real measured reading, and an invoice may bill metered
usage only.** An estimate is not a meter; a quote is not a bill. These tests would fail loudly
if the scaffold ever let a ``planner_estimate`` reading launder itself into a metered status or
an invoice line -- the exact dishonesty the cost-acknowledgment gate forbids.

Import-isolated: this exercises only the design-stage scaffold, no FastAPI app, no live services.
"""

from __future__ import annotations

import pytest

from api.services.production.billing import (
    Account,
    BillingStateError,
    InMemoryAccountStore,
    InMemoryQuotaLedger,
    InMemoryUsageMeter,
    InvoiceLine,
    MeterReading,
    StubPaymentProvider,
    build_compute_invoice_line,
    build_invoice,
)


# ---------------------------------------------------------------------------
# THE core honesty assertion: the stub meter never claims COST_METERED from an estimate.
# ---------------------------------------------------------------------------


def test_meter_with_no_readings_is_not_metered() -> None:
    meter = InMemoryUsageMeter()
    assert meter.metered_status("run-x") == "COST_NOT_METERED"
    assert meter.aggregate_measured_seconds("run-x") == 0.0


def test_estimate_only_reading_is_never_metered() -> None:
    """A planner_estimate reading populates a quote but NEVER licenses COST_METERED."""
    meter = InMemoryUsageMeter()
    meter.record(
        MeterReading(run_id="run-est", accelerator_seconds=3600.0, source="planner_estimate")
    )
    # The reading is stored...
    assert len(meter.readings_for_run("run-est")) == 1
    # ...but it is NOT a measurement, so the run is NOT metered, and it contributes 0 measured s.
    assert meter.metered_status("run-est") == "COST_NOT_METERED"
    assert meter.aggregate_measured_seconds("run-est") == 0.0


def test_assert_metered_refuses_estimate_only_run() -> None:
    """The active guard: asking the stub to *assert* metered on estimate data raises."""
    meter = InMemoryUsageMeter()
    meter.record(
        MeterReading(run_id="run-est", accelerator_seconds=10.0, source="planner_estimate")
    )
    with pytest.raises(BillingStateError, match="COST_METERED"):
        meter.assert_metered("run-est")


def test_assert_metered_refuses_run_with_no_readings() -> None:
    meter = InMemoryUsageMeter()
    with pytest.raises(BillingStateError, match="no fleet_measured reading"):
        meter.assert_metered("run-empty")


def test_only_fleet_measured_reading_flips_metered() -> None:
    """COST_METERED is licensed solely by a real measured reading."""
    meter = InMemoryUsageMeter()
    meter.record(
        MeterReading(run_id="run-m", accelerator_seconds=1800.0, source="fleet_measured")
    )
    assert meter.metered_status("run-m") == "COST_METERED"
    assert meter.aggregate_measured_seconds("run-m") == 1800.0
    # assert_metered now returns cleanly (a real measurement backs it).
    assert meter.assert_metered("run-m") == "COST_METERED"


def test_mixed_readings_aggregate_only_measured() -> None:
    """When estimate and measured readings coexist, only measured seconds are summed/billed."""
    meter = InMemoryUsageMeter()
    meter.record(
        MeterReading(run_id="run-mix", accelerator_seconds=5000.0, source="planner_estimate")
    )
    meter.record(
        MeterReading(run_id="run-mix", accelerator_seconds=1200.0, source="fleet_measured")
    )
    meter.record(
        MeterReading(run_id="run-mix", accelerator_seconds=300.0, source="fleet_measured")
    )
    # 5000 estimate excluded; 1200 + 300 measured included.
    assert meter.aggregate_measured_seconds("run-mix") == 1500.0
    assert meter.metered_status("run-mix") == "COST_METERED"


# ---------------------------------------------------------------------------
# Invoices bill MEASURED usage only.
# ---------------------------------------------------------------------------


def test_invoice_line_refuses_estimate_only_run() -> None:
    """You cannot invoice a run whose consumption was never measured."""
    meter = InMemoryUsageMeter()
    meter.record(
        MeterReading(run_id="run-est", accelerator_seconds=9999.0, source="planner_estimate")
    )
    with pytest.raises(BillingStateError, match="bill metered usage only|no fleet_measured"):
        build_compute_invoice_line(meter, run_id="run-est")


def test_invoice_line_bills_measured_quantity_with_evidence_ref() -> None:
    meter = InMemoryUsageMeter()
    r1 = meter.record(
        MeterReading(run_id="run-b", accelerator_seconds=600.0, source="fleet_measured")
    )
    r2 = meter.record(
        MeterReading(run_id="run-b", accelerator_seconds=400.0, source="fleet_measured")
    )
    line = build_compute_invoice_line(meter, run_id="run-b")
    assert isinstance(line, InvoiceLine)
    assert line.quantity == 1000.0
    assert line.unit == "accelerator_second"
    # Evidence ref walks back to the run and is content-addressed over the contributing readings.
    assert line.run_id == "run-b"
    assert line.evidence_ref.startswith("cas-billing://run/run-b/readings/sha256:")
    # Unpriced v0 price book: quantity only, no amount.
    assert line.unit_price is None
    assert line.amount is None
    # Reading ids really do back this line.
    assert {r1.reading_id, r2.reading_id}  # both recorded


def test_invoice_line_evidence_ref_is_idempotent() -> None:
    """Re-building on the same measured readings yields the same quantity + evidence ref."""
    meter = InMemoryUsageMeter()
    meter.record(MeterReading(run_id="run-i", accelerator_seconds=42.0, source="fleet_measured"))
    line_a = build_compute_invoice_line(meter, run_id="run-i")
    line_b = build_compute_invoice_line(meter, run_id="run-i")
    assert line_a.evidence_ref == line_b.evidence_ref
    assert line_a.quantity == line_b.quantity


def test_invoice_is_all_or_nothing_honest() -> None:
    """An invoice never silently drops an unmeasured run -- it refuses to build."""
    store = InMemoryAccountStore()
    account = store.create(tenant_id="tenant-1")
    meter = InMemoryUsageMeter()
    meter.record(MeterReading(run_id="run-ok", accelerator_seconds=100.0, source="fleet_measured"))
    meter.record(
        MeterReading(run_id="run-bad", accelerator_seconds=100.0, source="planner_estimate")
    )
    with pytest.raises(BillingStateError):
        build_invoice(
            meter,
            account=account,
            run_ids=["run-ok", "run-bad"],
            period_start="2026-06-01",
            period_end="2026-06-30",
        )


def test_invoice_with_priced_book_computes_amount() -> None:
    store = InMemoryAccountStore()
    account = store.create(tenant_id="tenant-1")
    meter = InMemoryUsageMeter()
    meter.record(MeterReading(run_id="run-p", accelerator_seconds=1000.0, source="fleet_measured"))
    invoice = build_invoice(
        meter,
        account=account,
        run_ids=["run-p"],
        period_start="2026-06-01",
        period_end="2026-06-30",
        unit_price=0.0005,  # $/accelerator-second (illustrative)
    )
    assert invoice.status == "draft"
    assert len(invoice.lines) == 1
    assert invoice.lines[0].amount == pytest.approx(0.5)
    assert invoice.total_amount == pytest.approx(0.5)
    assert invoice.lines[0].evidence_ref.startswith("cas-billing://run/run-p/")


# ---------------------------------------------------------------------------
# MeterReading source discipline.
# ---------------------------------------------------------------------------


def test_meter_reading_rejects_unknown_source() -> None:
    with pytest.raises(BillingStateError, match="source"):
        MeterReading(run_id="r", accelerator_seconds=1.0, source="guessed")  # type: ignore[arg-type]


def test_meter_reading_rejects_negative_seconds() -> None:
    with pytest.raises(BillingStateError):
        MeterReading(run_id="r", accelerator_seconds=-1.0, source="fleet_measured")


def test_is_measurement_flag() -> None:
    measured = MeterReading(run_id="r", accelerator_seconds=1.0, source="fleet_measured")
    estimate = MeterReading(run_id="r", accelerator_seconds=1.0, source="planner_estimate")
    assert measured.is_measurement is True
    assert estimate.is_measurement is False


# ---------------------------------------------------------------------------
# Quota ledger: reserve by estimate, settle by measurement.
# ---------------------------------------------------------------------------


def test_quota_uncapped_when_no_budget_configured() -> None:
    ledger = InMemoryQuotaLedger()
    decision = ledger.reserve("acct-1", run_id="run-1", estimated_accelerator_seconds=10_000.0)
    assert decision.allowed is True
    assert ledger.remaining_budget_seconds("acct-1") is None


def test_quota_refuses_run_exceeding_budget_by_estimate() -> None:
    ledger = InMemoryQuotaLedger()
    ledger.set_budget("acct-1", 1000.0)
    decision = ledger.reserve("acct-1", run_id="run-1", estimated_accelerator_seconds=1500.0)
    assert decision.allowed is False
    assert "exceeds remaining budget" in decision.reason


def test_quota_reserve_then_settle_trues_up_to_measurement() -> None:
    ledger = InMemoryQuotaLedger()
    ledger.set_budget("acct-1", 1000.0)
    reserved = ledger.reserve("acct-1", run_id="run-1", estimated_accelerator_seconds=800.0)
    assert reserved.allowed is True
    assert reserved.remaining_after_seconds == pytest.approx(200.0)
    # Run actually consumed less than estimated; settle trues the ledger up to the measurement.
    settled = ledger.settle("acct-1", run_id="run-1", measured_accelerator_seconds=600.0)
    assert settled.allowed is True
    assert ledger.remaining_budget_seconds("acct-1") == pytest.approx(400.0)


# ---------------------------------------------------------------------------
# Stub payment provider never moves money.
# ---------------------------------------------------------------------------


def test_stub_payment_provider_never_charges() -> None:
    provider = StubPaymentProvider()
    result = provider.charge(
        account_id="acct-1", invoice_id="inv-1", amount=100.0, currency="USD"
    )
    assert result.succeeded is False
    assert result.is_real is False
    assert result.settlement_ref is None


# ---------------------------------------------------------------------------
# Account lifecycle.
# ---------------------------------------------------------------------------


def test_account_lifecycle() -> None:
    store = InMemoryAccountStore()
    account = store.create(tenant_id="tenant-9")
    assert isinstance(account, Account)
    assert account.status == "active"
    assert account.tenant_id == "tenant-9"
    suspended = store.set_status(account.id, "suspended")
    assert suspended.status == "suspended"
    closed = store.set_status(account.id, "closed")
    assert closed.status == "closed"


def test_account_requires_tenant_id() -> None:
    store = InMemoryAccountStore()
    with pytest.raises(BillingStateError, match="tenant_id"):
        store.create(tenant_id="   ")
