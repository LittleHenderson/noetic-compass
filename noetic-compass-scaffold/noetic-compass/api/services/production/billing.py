"""Billing / accounts / accelerator-hour metering seams (workstream 08, design-stage scaffold).

Import-isolated. NOTHING here is wired into the live FastAPI app, the cost-acknowledgment
gate (``cas_harness_cost_acknowledgment``), the scale planner, or the distributed-audit
control plane. It exists so the blueprint in
``docs/working/production_readiness/08_billing_and_accounts.md`` has concrete Python seams
the team (and workstreams 02/03/05/06/09) can build against, plus clearly-labeled in-memory
stubs that let the contract be exercised in a unit test without any real infra.

What this module is about
-------------------------
The cost-acknowledgment gate (``cas_harness_cost_acknowledgment.py``) declares a tri-state in
which ``COST_METERED`` is "the fleet metered real accelerator-hours of actual consumption --
fleet-side only; never produced at the API tier", and its ``CostExposureSummary.cost_metered``
field is hardcoded ``False`` (``:166``). That hardcoded ``False`` is a PROMISE: only a real
meter, reading real GPU-seconds, may flip it. This module defines the meter, account, invoice,
and quota seams that keep the promise -- and, crucially, a stub meter that CANNOT keep it and
says so.

The founding distinction (honesty rule, blueprint §4)
-----------------------------------------------------
A ``MeterReading`` carries a ``source``:

* ``"fleet_measured"``  -- real GPU-seconds the fleet/cloud measured. May meter, may bill.
* ``"planner_estimate"`` -- a projection derived from the planner's fleet-size numbers
  (``ScalePlan.recommended_worker_count`` x a duration assumption). May quote, may reserve a
  quota -- but NEVER licenses ``COST_METERED`` and NEVER reaches an invoice line.

The two share a dataclass *only* so the difference is explicit and inescapable.

Honesty rule (inherited from ``production/__init__.py``)
-------------------------------------------------------
A stub is a stub. No backend here may emit ``COST_METERED`` (or any ``*_VERIFIED`` /
``*_WORM_COMMITTED``) from data it did not measure, and the stub ``PaymentProvider`` never moves
money. ``InMemoryUsageMeter.metered_status`` returns ``COST_METERED`` ONLY when a genuine
``fleet_measured`` reading has been recorded for the run; a meter holding only
``planner_estimate`` readings returns ``COST_NOT_METERED``. The default stub additionally refuses
to *accept* a fabricated metered claim it was not given the measured reading to support. The test
(``tests/test_production_billing.py``) asserts these refusals, so a test cannot accidentally
launder an estimate into a metered bill.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import hashlib
from typing import Literal, Protocol, runtime_checkable
from uuid import uuid4


BILLING_SCHEMA_VERSION = "cas_harness_billing.v1"
# The price book is unpriced at v0 on purpose: no $/accelerator-second has been set. An
# invoice line built under this version is quantity-only (amount stays None) -- honest about
# the fact that we can meter usage before we have agreed a rate to charge for it.
DEFAULT_PRICE_BOOK_VERSION = "cas_harness_price_book.v0_unpriced"


# ---------------------------------------------------------------------------
# Status vocabularies
# ---------------------------------------------------------------------------

# Runtime metered-status of a run, DERIVED from its readings (never set directly). Mirrors the
# gate-4 tri-state's COST_METERED member (``cas_harness_cost_acknowledgment.py:49``). Only a
# fleet_measured reading licenses COST_METERED.
RunMeteredStatus = Literal["COST_METERED", "COST_NOT_METERED"]

AccountStatus = Literal["active", "suspended", "closed"]
InvoiceStatus = Literal["draft", "issued", "paid", "void"]

# THE load-bearing discriminator: where a reading's number came from.
MeterSource = Literal["fleet_measured", "planner_estimate"]

UsageUnit = Literal["accelerator_second", "gb_month", "audit_run"]


class BillingStateError(ValueError):
    """Raised when a billing transition would make usage look more real than it is.

    The canonical case: trying to claim ``COST_METERED`` from estimate-sourced data, or trying
    to bill an estimate. Both are dishonesty-by-construction and are refused, not papered over.
    """


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Account:
    """The billable entity a run belongs to -- the billing projection of a 06 tenant.

    06 owns tenant isolation/keys/partitioning; 08 owns the money. ``tenant_id`` is the same
    partition key ``ArtifactDescriptor.tenant_id`` (02) and ``WorkerSlot.tenant_id`` (03) carry.
    """

    id: str
    tenant_id: str
    status: AccountStatus = "active"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    price_book_version: str = DEFAULT_PRICE_BOOK_VERSION
    currency: str = "USD"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "created_at": self.created_at,
            "price_book_version": self.price_book_version,
            "currency": self.currency,
        }


@dataclass(frozen=True)
class MeterReading:
    """One measurement (``fleet_measured``) or one projection (``planner_estimate``) of usage.

    ``accelerator_seconds`` is real GPU busy-time when ``source == 'fleet_measured'``. The
    ``source`` field is the entire honesty mechanism: an estimate-sourced reading can NEVER
    license ``COST_METERED`` (see ``InMemoryUsageMeter.metered_status``) and NEVER reaches an
    ``InvoiceLine`` (see ``build_invoice``).
    """

    run_id: str  # joins to DistributedAuditRecord.audit_id (cas_harness_distributed_audits.py:110)
    accelerator_seconds: float
    source: MeterSource
    measured_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    reading_id: str = field(default_factory=lambda: f"reading-{uuid4().hex[:16]}")
    worker_id: str | None = None
    tenant_id: str | None = None
    unit: UsageUnit = "accelerator_second"

    def __post_init__(self) -> None:
        if self.source not in ("fleet_measured", "planner_estimate"):
            raise BillingStateError(
                f"MeterReading.source must be 'fleet_measured' or 'planner_estimate', "
                f"got {self.source!r}"
            )
        if self.accelerator_seconds < 0:
            raise BillingStateError("accelerator_seconds must be non-negative")

    @property
    def is_measurement(self) -> bool:
        """Only a fleet_measured reading is a real measurement; an estimate is not."""
        return self.source == "fleet_measured"

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "accelerator_seconds": self.accelerator_seconds,
            "source": self.source,
            "measured_at": self.measured_at,
            "reading_id": self.reading_id,
            "worker_id": self.worker_id,
            "tenant_id": self.tenant_id,
            "unit": self.unit,
            "is_measurement": self.is_measurement,
        }


@dataclass(frozen=True)
class InvoiceLine:
    """One billable line. ``quantity`` is summed from MEASURED readings only (blueprint §4)."""

    run_id: str
    quantity: float
    unit: UsageUnit
    evidence_ref: str  # resolves to run_id + the reading_ids producing `quantity`
    unit_price: float | None = None  # from the versioned price book; None == unpriced (v0)
    amount: float | None = None  # quantity * unit_price; None until priced
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "quantity": self.quantity,
            "unit": self.unit,
            "evidence_ref": self.evidence_ref,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "description": self.description,
        }


@dataclass(frozen=True)
class Invoice:
    """A period/account invoice. Every line walks back to measured consumption (§4)."""

    id: str
    account_id: str
    period_start: str
    period_end: str
    lines: tuple[InvoiceLine, ...]
    status: InvoiceStatus = "draft"
    currency: str = "USD"
    price_book_version: str = DEFAULT_PRICE_BOOK_VERSION
    total_amount: float | None = None  # None while unpriced/draft
    settlement_ref: str | None = None  # set ONLY by a real PaymentProvider (Phase F)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "lines": [line.to_dict() for line in self.lines],
            "status": self.status,
            "currency": self.currency,
            "price_book_version": self.price_book_version,
            "total_amount": self.total_amount,
            "settlement_ref": self.settlement_ref,
        }


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    account_id: str
    run_id: str
    reason: str
    remaining_after_seconds: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "account_id": self.account_id,
            "run_id": self.run_id,
            "reason": self.reason,
            "remaining_after_seconds": self.remaining_after_seconds,
        }


@dataclass(frozen=True)
class PaymentResult:
    succeeded: bool
    settlement_ref: str | None
    is_real: bool  # stub returns False; only a real provider returns True
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "succeeded": self.succeeded,
            "settlement_ref": self.settlement_ref,
            "is_real": self.is_real,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Seams (Protocol / ABC the team builds real backends against)
# ---------------------------------------------------------------------------


@runtime_checkable
class UsageMeter(Protocol):
    """Records consumption readings and aggregates them into billable quantities.

    A real meter's ``record`` is fed by the metering pipeline reading ACTUAL GPU-seconds from
    the fleet/cloud (blueprint Phase C). ``metered_status`` returns ``COST_METERED`` ONLY when a
    fleet_measured reading exists for the run.
    """

    def record(self, reading: MeterReading) -> MeterReading: ...

    def readings_for_run(self, run_id: str) -> list[MeterReading]: ...

    def aggregate_measured_seconds(self, run_id: str) -> float:
        """Sum ``accelerator_seconds`` across ONLY fleet_measured readings for the run."""
        ...

    def metered_status(self, run_id: str) -> RunMeteredStatus:
        """``COST_METERED`` iff >=1 fleet_measured reading exists; else ``COST_NOT_METERED``."""
        ...


@runtime_checkable
class QuotaLedger(Protocol):
    """Caps an account's consumption. Reserve by ESTIMATE at admission; settle by MEASUREMENT on
    completion (blueprint §4). This is the cap the cost gate explicitly does NOT do
    (``cas_harness_cost_acknowledgment.py:20-23``)."""

    def reserve(
        self, account_id: str, *, run_id: str, estimated_accelerator_seconds: float
    ) -> QuotaDecision: ...

    def settle(
        self, account_id: str, *, run_id: str, measured_accelerator_seconds: float
    ) -> QuotaDecision: ...

    def remaining_budget_seconds(self, account_id: str) -> float | None: ...


class PaymentProvider(ABC):
    """CLEARLY EXTERNAL. Real money movement (Stripe-class).

    ABC (not Protocol) because a real provider carries external credentials + network state. The
    stub below NEVER charges; it returns a labeled fake (``is_real=False``) and never claims a
    real settlement. Only a real provider flips an ``Invoice`` to ``paid`` with a genuine
    ``settlement_ref`` (blueprint Phase F).
    """

    @abstractmethod
    def charge(
        self, *, account_id: str, invoice_id: str, amount: float, currency: str
    ) -> PaymentResult:
        ...


# ---------------------------------------------------------------------------
# In-memory stubs (clearly labeled; record/declared facts only)
# ---------------------------------------------------------------------------


class InMemoryAccountStore:
    """STUB account store. Plain-dict account lifecycle for tests/design only.

    Not durable -- accounts are financial records of record and need real persistence + a 09
    audit trail in production. This stub proves only the lifecycle contract.
    """

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def create(self, *, tenant_id: str, account_id: str | None = None) -> Account:
        if not tenant_id.strip():
            raise BillingStateError("tenant_id is required to open an account")
        acct = Account(id=account_id or f"acct-{uuid4().hex[:16]}", tenant_id=tenant_id)
        self._accounts[acct.id] = acct
        return acct

    def get(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    def set_status(self, account_id: str, status: AccountStatus) -> Account:
        acct = self._accounts.get(account_id)
        if acct is None:
            raise KeyError(account_id)
        updated = replace(acct, status=status)
        self._accounts[account_id] = updated
        return updated


class InMemoryUsageMeter:
    """STUB usage meter. Records readings in memory; honest about metered-status.

    It is honest about exactly one thing structurally: it returns ``COST_METERED`` ONLY when it
    holds a real ``fleet_measured`` reading for the run. A meter holding only
    ``planner_estimate`` readings returns ``COST_NOT_METERED`` -- because an estimate is not a
    measurement (blueprint §4). It provides NO durability; readings vanish on process exit, which
    is exactly why a real metering pipeline + store is required for production.
    """

    def __init__(self) -> None:
        self._readings: dict[str, list[MeterReading]] = {}

    def record(self, reading: MeterReading) -> MeterReading:
        if not isinstance(reading, MeterReading):
            raise BillingStateError("record() requires a MeterReading")
        self._readings.setdefault(reading.run_id, []).append(reading)
        return reading

    def readings_for_run(self, run_id: str) -> list[MeterReading]:
        return list(self._readings.get(run_id, []))

    def measured_readings_for_run(self, run_id: str) -> list[MeterReading]:
        return [r for r in self._readings.get(run_id, []) if r.is_measurement]

    def aggregate_measured_seconds(self, run_id: str) -> float:
        # Sum ONLY fleet_measured readings. Estimate readings are deliberately excluded: you
        # cannot meter (or bill) a projection.
        return sum(r.accelerator_seconds for r in self.measured_readings_for_run(run_id))

    def metered_status(self, run_id: str) -> RunMeteredStatus:
        # The single most important method in this workstream. COST_METERED is licensed ONLY by
        # the existence of a real measured reading -- never by an estimate, never by fiat.
        if self.measured_readings_for_run(run_id):
            return "COST_METERED"
        return "COST_NOT_METERED"

    def assert_metered(self, run_id: str) -> RunMeteredStatus:
        """Refuse to confirm ``COST_METERED`` unless a real measurement backs it.

        This is the active honesty guard the test exercises: a caller asking the stub to
        *assert* a run is metered gets a ``BillingStateError`` whenever the only evidence is an
        estimate (or nothing). The stub cannot be coerced into laundering an estimate.
        """
        status = self.metered_status(run_id)
        if status != "COST_METERED":
            raise BillingStateError(
                f"refusing to claim COST_METERED for run {run_id!r}: no fleet_measured reading "
                f"exists (only estimate/no readings). An estimate is not a meter -- "
                f"COST_METERED is licensed solely by real measured accelerator-seconds."
            )
        return status


class InMemoryQuotaLedger:
    """STUB quota ledger. Reserve-by-estimate, settle-by-measurement over an in-memory budget."""

    def __init__(self, *, budget_seconds: dict[str, float] | None = None) -> None:
        self._budget: dict[str, float] = dict(budget_seconds or {})
        self._reserved: dict[str, dict[str, float]] = {}  # account -> run -> reserved seconds

    def set_budget(self, account_id: str, budget_seconds: float) -> None:
        if budget_seconds < 0:
            raise BillingStateError("budget_seconds must be non-negative")
        self._budget[account_id] = budget_seconds

    def _committed(self, account_id: str) -> float:
        return sum(self._reserved.get(account_id, {}).values())

    def remaining_budget_seconds(self, account_id: str) -> float | None:
        budget = self._budget.get(account_id)
        if budget is None:
            return None  # no budget configured == uncapped (postpaid)
        return budget - self._committed(account_id)

    def reserve(
        self, account_id: str, *, run_id: str, estimated_accelerator_seconds: float
    ) -> QuotaDecision:
        if estimated_accelerator_seconds < 0:
            raise BillingStateError("estimated_accelerator_seconds must be non-negative")
        remaining = self.remaining_budget_seconds(account_id)
        if remaining is None:
            return QuotaDecision(
                allowed=True,
                account_id=account_id,
                run_id=run_id,
                reason="no budget configured (uncapped/postpaid); reservation recorded only",
                remaining_after_seconds=None,
            )
        if estimated_accelerator_seconds > remaining:
            return QuotaDecision(
                allowed=False,
                account_id=account_id,
                run_id=run_id,
                reason=(
                    f"estimated {estimated_accelerator_seconds}s exceeds remaining budget "
                    f"{remaining}s; run refused at admission"
                ),
                remaining_after_seconds=remaining,
            )
        self._reserved.setdefault(account_id, {})[run_id] = estimated_accelerator_seconds
        return QuotaDecision(
            allowed=True,
            account_id=account_id,
            run_id=run_id,
            reason="reserved estimated accelerator-seconds against budget (by ESTIMATE)",
            remaining_after_seconds=remaining - estimated_accelerator_seconds,
        )

    def settle(
        self, account_id: str, *, run_id: str, measured_accelerator_seconds: float
    ) -> QuotaDecision:
        # True up the by-estimate reservation against the real measured consumption.
        if measured_accelerator_seconds < 0:
            raise BillingStateError("measured_accelerator_seconds must be non-negative")
        self._reserved.setdefault(account_id, {})[run_id] = measured_accelerator_seconds
        return QuotaDecision(
            allowed=True,
            account_id=account_id,
            run_id=run_id,
            reason="reservation trued up to MEASURED accelerator-seconds on completion",
            remaining_after_seconds=self.remaining_budget_seconds(account_id),
        )


class StubPaymentProvider(PaymentProvider):
    """STUB payment provider. NEVER moves money. Returns a labeled fake (``is_real=False``).

    A real provider (blueprint Phase F) is the only thing that can flip an ``Invoice`` to
    ``paid`` with a genuine settlement reference. This stub exists so the billing flow can be
    unit-tested end-to-end without a payment integration -- and it advertises its own fakeness.
    """

    def charge(
        self, *, account_id: str, invoice_id: str, amount: float, currency: str
    ) -> PaymentResult:
        return PaymentResult(
            succeeded=False,
            settlement_ref=None,
            is_real=False,
            notes=(
                "STUB PaymentProvider: no money moved. A real provider (Stripe-class, Phase F) "
                "is required to charge and to flip an invoice to 'paid'."
            ),
        )


# ---------------------------------------------------------------------------
# Invoice builder (bills MEASURED usage only)
# ---------------------------------------------------------------------------


def _evidence_ref(run_id: str, reading_ids: list[str]) -> str:
    """A resolvable evidence ref: run id + a stable digest of the contributing reading ids.

    'Show your work' -- the line's quantity is the sum of exactly these readings' seconds. The
    digest lets a verifier confirm the line was built from this precise set, no more, no less.
    """
    joined = ",".join(sorted(reading_ids))
    digest = hashlib.sha256(f"{run_id}|{joined}".encode("utf-8")).hexdigest()[:16]
    return f"cas-billing://run/{run_id}/readings/sha256:{digest}"


def build_compute_invoice_line(
    meter: InMemoryUsageMeter,
    *,
    run_id: str,
    unit_price: float | None = None,
) -> InvoiceLine:
    """Build one compute ``InvoiceLine`` for a run from its MEASURED readings only.

    Refuses (``BillingStateError``) if the run has no fleet_measured reading -- you cannot
    invoice a run whose consumption was never measured. Estimate readings are excluded from the
    quantity by construction (``aggregate_measured_seconds``).
    """
    measured = meter.measured_readings_for_run(run_id)
    if not measured:
        raise BillingStateError(
            f"cannot build an invoice line for run {run_id!r}: no fleet_measured reading. "
            f"An invoice may bill metered usage only; an estimate is not billable."
        )
    quantity = sum(r.accelerator_seconds for r in measured)
    reading_ids = [r.reading_id for r in measured]
    amount = None if unit_price is None else round(quantity * unit_price, 6)
    return InvoiceLine(
        run_id=run_id,
        quantity=quantity,
        unit="accelerator_second",
        evidence_ref=_evidence_ref(run_id, reading_ids),
        unit_price=unit_price,
        amount=amount,
        description=(
            f"metered compute: {quantity} accelerator-seconds across "
            f"{len(measured)} fleet_measured reading(s)"
        ),
    )


def build_invoice(
    meter: InMemoryUsageMeter,
    *,
    account: Account,
    run_ids: list[str],
    period_start: str,
    period_end: str,
    unit_price: float | None = None,
    invoice_id: str | None = None,
) -> Invoice:
    """Assemble an ``Invoice`` whose every line is backed by MEASURED readings.

    A run in ``run_ids`` with no fleet_measured reading raises -- the invoice is all-or-nothing
    honest: it never silently drops an unmeasured run, and it never bills an estimate. Re-running
    on the same readings is idempotent (same quantities, same evidence refs).
    """
    lines = tuple(
        build_compute_invoice_line(meter, run_id=run_id, unit_price=unit_price)
        for run_id in run_ids
    )
    if unit_price is None:
        total: float | None = None  # unpriced price book v0: quantity-only, no amount
    else:
        total = round(sum(line.amount or 0.0 for line in lines), 6)
    return Invoice(
        id=invoice_id or f"inv-{uuid4().hex[:16]}",
        account_id=account.id,
        period_start=period_start,
        period_end=period_end,
        lines=lines,
        status="draft",
        currency=account.currency,
        price_book_version=account.price_book_version,
        total_amount=total,
    )
