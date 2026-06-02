# 08 — Billing / Accounts

**Workstream:** 08 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** accounts, real accelerator-hour metering (the honest source of `COST_METERED`), usage → invoicing, quotas.

> Scope boundary up front: the API tier **declares/acknowledges an estimate**; it never meters.
> `COST_METERED` is a **promise the fleet must keep** by measuring real accelerator-seconds
> consumed. This workstream turns that promise into real metering, accounts, invoices, and quotas.
> The one-line rule for this whole document: **an estimate is not a meter, and only a meter may
> bill.** A stub meter that has measured nothing MUST NEVER emit `COST_METERED`.

---

## 1. Current state (what already exists)

The Harness has a **cost-acknowledgment gate** and a **resource estimator**. It has **no account,
no meter, no invoice, and no quota**. It is essential to be precise about how little of "cost"
actually exists today, because the gap is wider than it looks.

### 1.1 There is an acknowledgment, and it is honest about being uncosted

`api/services/cas_harness_cost_acknowledgment.py` is gate 4. Its honest tri-state
(`CostAcknowledgmentStatus`, `:48-52`) is the contract this workstream inherits:

- `COST_METERED` — "the fleet metered real accelerator-hours of actual consumption. Fleet-side
  only; **never produced at the API tier**" (`:30-33` docstring; the `Literal` member `:49`).
- `COST_ACKNOWLEDGED` — the caller accepted an uncosted commitment. "Enough to *create* a run,
  never on its own a customer ACCEPT" (`:33-35`).
- `COST_NOT_ACKNOWLEDGED` — a frontier run without acknowledgment → `ValueError` → HTTP 422
  (`validate_frontier_cost_acknowledgment`, `:177-197`).

The receipt is `CostExposureSummary` (`:55-96`). Its `cost_metered` field is **hardcoded `False`**
at construction (`summarize_cost_exposure`, `:166`), with the field comment stating real cost "can
only be known by running the fleet and metering accelerator-hours, which the workers do, not this
tier" (`:66-69`). **That hardcoded `False` is the exact promise this workstream exists to make
true** — and the only place in the codebase entitled to flip it is a real meter reading
fleet-measured GPU-seconds.

### 1.2 There is a resource *magnitude*, but it is NOT even an accelerator-hour estimate

The only quantities the cost gate surfaces are pulled from the scale planner — it "invents none"
(`_magnitudes`, `:113-128`):

- `ScalePlan.recommended_worker_count` (`cas_harness_scale_planner.py:189`) — an instantaneous
  worker *count*, not worker-*hours*.
- `MemoryEstimate.estimated_total_runtime_gb` (`cas_harness_scale_planner.py:173`) — a memory
  footprint in GB, not a duration and not GPU-seconds.
- From gate 3, the declared fleet: `declared_accelerator_count` / `declared_accelerator_memory_gb`
  / `effective_accelerator_count` (`cas_harness_compute_feasibility.py`).

Read the cost gate's own docstring (`cas_harness_cost_acknowledgment.py:7-14`):

> "**nothing** in the system models wall-clock duration, throughput (tokens/sec), or dollars — there
> is no rate, no price book, no duration estimator anywhere in the planner. So this gate **refuses
> to quote a price**."

This is the crucial honest fact for workstream 08: **today there is not even an accelerator-hour
*estimate*.** There is a worker count (how *wide*) and a memory footprint (how *big*), but no
duration (how *long*), so `accelerator_hours = workers × hours` cannot be computed at all. The
system has a *fleet-size* estimate, not a *consumption* estimate, and certainly not a meter. Any
billing work must therefore build the estimate AND the meter — and keep them rigorously distinct.

### 1.3 The run record the meter will attach to

`api/services/cas_harness_distributed_audits.py` holds `DistributedAuditRecord` (`:108-155`),
keyed by `audit_id` (`_audit_id_for`, `:481-491`) in a process-global dict `_DISTRIBUTED_AUDITS`
(`:158`). It already carries `cost: CostExposureSummary | None` (`:127`, `:264-266`). This is the
join key every `MeterReading` and `InvoiceLine` will reference: **a meter reading is *about* a run,
and an invoice line walks back to the run + the consumption events that produced it.** There is no
tenant/account field on the record today (see §2) and the dict is not durable (vanishes on restart;
per project memory, "pod can disappear").

### 1.4 Consumption-adjacent signals that exist but do NOT measure GPU-seconds

Two peer scaffolds emit facts close to consumption but **neither is an accelerator-hour meter**:

- **02 (storage):** `InMemoryArtifactStore.bytes_stored_for_audit(audit_id)`
  (`api/services/production/artifact_store.py:335-341`) — a real *bytes-stored* number. This is a
  **storage**-cost signal (a second billable dimension), not compute.
- **03 (fleet):** `PlacementDecision` / `HeartbeatState` (`api/services/production/fleet_scale.py`)
  — placement bindings and heartbeat liveness. A heartbeat says a worker is *alive*, not how many
  GPU-seconds it *burned*. These are the **timing spine** a meter can integrate over, but they are
  declared/observed facts, explicitly **not** `*_METERED` (that module's docstring, `:21-31`).

**Net:** the honest starting point is an *acknowledged estimate of fleet size* with `cost_metered`
nailed to `False`, plus storage-bytes and liveness telemetry — and **zero** measured
accelerator-seconds.

---

## 2. Gap to production

The delta from "acknowledged estimate" to "accounts + real accelerator-hour metering +
usage→invoice + quotas":

1. **No account model.** There is no `Account`, no `tenant_id` on the run record, nothing tying a
   run to a billable entity. Billing needs an account a run belongs to, with a lifecycle
   (`active` / `suspended` / `closed`). (Tenancy is **06**; the account is the *billing* projection
   of a tenant — see §6.)
2. **No accelerator-hour meter (the core gap).** Nothing measures GPU-seconds. Production needs a
   metering pipeline that reads **actual** per-worker accelerator busy-time from the fleet/cloud and
   records `MeterReading`s sourced from real consumption — the only thing that may license
   `COST_METERED`.
3. **No estimate-of-consumption either.** Even the *pre-run* estimate is only fleet size, not
   accelerator-hours (no duration model). Production needs a `accelerator_seconds` **estimate**
   (clearly labeled `source="planner_estimate"`) so there is something to reconcile actuals against
   — and a reconciliation gate that proves measured ≈ estimated within a tolerance on known runs.
4. **No usage aggregation.** No rollup of readings per run / per account / per billing period. Need
   a `UsageMeter` that records readings and aggregates them into billable quantities.
5. **No rating / price book.** No `$/accelerator-second`, no `$/GB-month` for stored artifacts, no
   currency. Need a versioned price book (so an invoice line records *which* rate produced it).
6. **No invoice.** No `InvoiceLine`, no `Invoice`, no evidence linkage. Need invoices whose every
   line walks back to a run + the measured readings that produced it.
7. **No quotas.** No spend cap, no concurrency cap, no GPU-hour budget. Note the cost gate
   explicitly "does **not** bill, meter, or **cap**" (`cas_harness_cost_acknowledgment.py:20-23`):
   the *cap* is squarely this workstream. Need a `QuotaLedger` checked at admission.
8. **No payment provider.** No charge, no settlement, no external money movement. Need a
   `PaymentProvider` seam, clearly external, that the in-memory stub never pretends to be.
9. **No durability.** Accounts, readings, and invoices are financial records of record — they cannot
   live in a process dict. Real persistence + an append-only audit trail (interacts with **09**
   retention, §6).

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

> Sequencing note: Phases A–B are pure-Python seams with no infra and can land immediately. Phase C
> is the first phase that needs a **real consumption source** (fleet/cloud GPU-second telemetry) and
> is the gate that earns the right to flip `COST_METERED`. D–F layer on C. The seams in A are what
> 06/09 and the real backends attach to, so they are not blocked on C.

### Phase A — Account model + billing Protocols/ABCs + in-memory stubs
Define the seam (`Account`, `MeterReading`, `UsageMeter`, `InvoiceLine`, `Invoice`, `QuotaLedger`,
`PaymentProvider` of §5) and ship a clearly-labeled in-memory stub meter that **records readings but
NEVER emits `COST_METERED`** and a stub `PaymentProvider` that **never moves money**. No real infra.
(Delivered with this doc: `api/services/production/billing.py`.)
- **Validate:** an `Account` round-trips through create/suspend/close; a `MeterReading` with
  `source="planner_estimate"` is stored but the meter's metered-status query returns
  `COST_NOT_METERED`; a reading with `source="fleet_measured"` is required before the meter will even
  *consider* metered; the stub `PaymentProvider.charge` raises `NotImplementedError`/returns a
  clearly-fake result and never claims a real settlement. (`tests/test_production_billing.py`.)
- **Kill:** if the `MeterReading.source` discriminator cannot cleanly separate estimate-sourced from
  measurement-sourced readings such that no estimate can ever reach an invoice, redesign the seam
  before any pipeline work — that separation *is* the product.

### Phase B — Accelerator-second **estimator** (labeled estimate, never metered)
Add a pre-run `accelerator_seconds` estimate. Because the planner has no duration model
(§1.2), this requires introducing an explicit, honestly-labeled duration assumption (e.g. a
per-scale-tier nominal runtime, or a caller-declared expected duration) and computing
`estimated_accelerator_seconds = effective_accelerator_count × estimated_duration_seconds`. Emitted
as a `MeterReading(source="planner_estimate")` — it populates a *quote*, never an invoice.
- **Validate:** the estimate is produced from named inputs (worker/accelerator count × a declared or
  tiered duration); it is tagged `source="planner_estimate"`; an attempt to bill it is refused by the
  invoice builder (§4); the estimate and any later measured reading for the same run are both
  retained and clearly distinguishable.
- **Kill:** if the only honest duration input is "caller-declared" and callers won't declare one,
  ship the estimator as **optional** and let billing depend solely on measured readings — do **not**
  invent a throughput/duration model to manufacture an estimate (that is the precise dishonesty the
  cost gate refuses, `cas_harness_cost_acknowledgment.py:11-14`).

### Phase C — Real accelerator-hour meter + **reconciliation gate** (this flips `COST_METERED`)
Implement a metering pipeline that reads **actual** GPU busy-seconds per worker from the real
consumption source (RunPod/cloud accounting API, NVML/DCGM exporter scraped via 05, or cloud billing
export — see §7) and records `MeterReading(source="fleet_measured", accelerator_seconds=<real>)`
against the run. Only a `fleet_measured` reading sets the run's metered status to `COST_METERED`.
- **Validate (the load-bearing gate):** on a **known run** (e.g. the reproduced Pythia-160M lane, or
  a deliberately fixed synthetic fleet), the **measured** accelerator-seconds reconcile to the Phase-B
  **estimate within ±X%** (propose **±15%** as the initial tolerance; tighten with data). The
  reconciliation is recorded as evidence on the run. `COST_METERED` is emitted **only** for runs with
  a `fleet_measured` reading; a run with only a `planner_estimate` reading reports `COST_NOT_METERED`.
- **Kill:** if measured GPU-seconds cannot be obtained at all for the target cloud (no per-job
  accounting, no exporter access), `COST_METERED` **stays false** and billing is blocked for that
  cloud — ship the estimator-only quote and say so loudly. **A meter we cannot trust is worse than no
  meter:** never synthesize a "measurement" from the estimate to make the status flip.

### Phase D — Usage aggregation + versioned price book + invoice builder
Aggregate `fleet_measured` readings per run and per billing period into billable quantities; apply a
**versioned** price book (`$/accelerator-second` for compute; `$/GB-month` for stored bytes from 02);
build `Invoice` objects whose every `InvoiceLine` carries `evidence_ref` back to the run + the
specific readings. The invoice builder **rejects** any line whose backing reading is not
`fleet_measured` (§4).
- **Validate:** an invoice for a known run sums only `fleet_measured` quantities; every line's
  `evidence_ref` resolves to the run id and the reading ids that produced its `quantity`; re-running
  the builder on the same readings is idempotent (same invoice total); a line built from an estimate
  reading is refused with a clear error.
- **Kill:** if a line cannot be traced to its readings (evidence ref does not resolve), the invoice is
  not shippable — "show your work, or don't ship it." Block invoicing until the join is solid.

### Phase E — Quotas (spend cap, concurrency cap, GPU-hour budget) at admission
Add `QuotaLedger` checked at run **admission** (interacts with 03 backpressure and the API admit
gate): reserve estimated accelerator-seconds against the account's budget before a run is created;
commit/refund the reservation against the **measured** reading when the run completes. A run that
would exceed a hard cap is refused (HTTP 429/402-style) at create time.
- **Validate:** a run that would exceed the account's remaining GPU-hour budget (by **estimate**) is
  refused at admission; on completion the **measured** usage adjusts the ledger (over- or
  under-estimate reconciled); concurrency cap blocks the N+1 concurrent run.
- **Kill:** if reservation-by-estimate then commit-by-measurement produces ledger drift that cannot
  be reconciled (e.g. estimate wildly off and no measured reading arrives), fall back to
  post-paid-only (meter → bill, no pre-reservation) until the estimator is trustworthy. Never block a
  legitimate run on an *estimate* the system itself labels unreliable without a manual override path.

### Phase F — Payment provider integration (clearly external) + durable records
Wire a real `PaymentProvider` (Stripe-class) behind the seam; persist accounts/readings/invoices in
a durable store with an append-only financial audit trail (09). The stub remains the test double.
- **Validate:** a charge for a shippable invoice succeeds against the provider sandbox; the
  settlement reference is recorded on the invoice; the financial audit trail is append-only and
  reconciles to the invoices.
- **Kill:** if the provider cannot be reconciled to internal invoices (settlement amount ≠ invoiced
  amount), do not auto-charge; require manual finance review. Money movement is never "best effort."

---

## 4. Honesty constraints (non-negotiable)

These are the invariants. Each maps to a check the stub/test enforces or a documented backend flip.

- **Estimate ≠ meter — the founding distinction.** A `MeterReading` carries a `source`. Only
  `source="fleet_measured"` (real GPU-seconds the fleet/cloud measured) is a *measurement*;
  `source="planner_estimate"` is a *projection*. They share a dataclass **only** so the difference is
  explicit and inescapable, never to blur them. The estimator (Phase B) and the meter (Phase C) are
  different code paths with different sources.
- **Only measured consumption flips `COST_METERED`.** The run's metered status is `COST_METERED`
  **iff** it has at least one `fleet_measured` reading. A run with only estimate readings reports
  `COST_NOT_METERED`. This is the runtime form of `cas_harness_cost_acknowledgment.py:66-69` /
  `:166` (the hardcoded `False`): the API tier acknowledges; only the fleet meters. **Nothing at the
  API tier may set `COST_METERED`.**
- **An invoice may bill metered usage only.** `InvoiceLine` quantities come **exclusively** from
  `fleet_measured` readings (compute) and real `bytes_stored` from 02 (storage). The invoice builder
  **refuses** to bill an estimate. You cannot invoice a quote. (Phase D validate/kill.)
- **The stub meter never claims `COST_METERED`.** Per `production/__init__.py:9-12`, a stub is a
  stub. `InMemoryUsageMeter` records readings (including, in tests, fake "measured" ones a test
  explicitly constructs) but its *production* honesty rule is enforced structurally: the shippable
  in-memory meter exposes **no** path that asserts `COST_METERED` from estimate data, and the default
  stub refuses to mint a metered status it did not measure. The test asserts this refusal.
- **Show your work — every line walks back.** `InvoiceLine.evidence_ref` resolves to the run id and
  the reading ids whose `accelerator_seconds` sum to the line `quantity`. An unresolvable evidence
  ref makes the invoice unshippable. Traceability is the billing spine, exactly as it is the project
  spine.
- **Declared vs verified, at the billing tier.** Acknowledging cost (gate 4) is a *declaration* the
  caller will pay an uncosted amount. A `fleet_measured` reading is the *verified* statement of what
  was actually consumed. Billing acts on the verified statement, never the declaration.
- **Quotas cap by estimate, settle by measurement.** A pre-run quota reservation may use the
  *estimate* (it is all that exists pre-run), but the ledger is **trued up against the measured
  reading** on completion. The estimate gates admission; only the measurement bills.
- **No fabricated production.** Where real infra is required — a GPU-second telemetry source and a
  payment provider — the interface is defined, a labeled stub ships for tests, and this document
  states exactly what flips the status: a metering pipeline reading actual GPU-seconds (flips
  `COST_METERED`) and a payment provider clearing money (flips an invoice to `paid`).

---

## 5. Interfaces / seams

Concrete `typing.Protocol` / `ABC` / `dataclass` signatures. The shippable scaffold is
`api/services/production/billing.py`; the in-memory stubs there emit declared/recorded facts only.

```python
from typing import Protocol, runtime_checkable, Literal
from dataclasses import dataclass, field

# --- status vocabularies (mirror the gate-4 tri-state) ----------------------
# Runtime metered-status of a run, derived from its readings. COST_METERED is
# emitted ONLY when a fleet_measured reading exists (honesty constraint §4).
RunMeteredStatus = Literal["COST_METERED", "COST_NOT_METERED"]

AccountStatus = Literal["active", "suspended", "closed"]
InvoiceStatus = Literal["draft", "issued", "paid", "void"]

# THE load-bearing discriminator: where a reading's number came from.
#   "fleet_measured"  -> real GPU-seconds the fleet/cloud measured -> may bill, may meter.
#   "planner_estimate"-> a projection -> may quote, NEVER bills, NEVER meters.
MeterSource = Literal["fleet_measured", "planner_estimate"]

UsageUnit = Literal["accelerator_second", "gb_month", "audit_run"]


@dataclass(frozen=True)
class Account:
    """The billable entity a run belongs to. The billing projection of a 06 tenant."""
    id: str
    tenant_id: str            # 06 partition key; the account bills what the tenant consumes
    status: AccountStatus = "active"
    created_at: str = ""
    # price-book + currency the account is rated under (versioned; an invoice records which)
    price_book_version: str = "cas_harness_price_book.v0_unpriced"
    currency: str = "USD"


@dataclass(frozen=True)
class MeterReading:
    """One measurement (or, when source=planner_estimate, one projection) of consumption.

    accelerator_seconds is the real GPU busy-time when source=='fleet_measured'. The
    `source` field is the entire honesty mechanism: a reading sourced from the planner
    estimate can NEVER license COST_METERED or reach an invoice line.
    """
    run_id: str               # joins to DistributedAuditRecord.audit_id
    accelerator_seconds: float
    source: MeterSource       # fleet_measured == real; planner_estimate == projection
    measured_at: str
    reading_id: str = ""      # stable id an InvoiceLine.evidence_ref points back to
    worker_id: str | None = None   # which probe worker burned the time (03 spine)
    tenant_id: str | None = None
    unit: UsageUnit = "accelerator_second"

    @property
    def is_measurement(self) -> bool:
        """Only a fleet_measured reading is a real measurement; an estimate is not."""
        return self.source == "fleet_measured"


@runtime_checkable
class UsageMeter(Protocol):
    """Records consumption readings and aggregates them into billable quantities.

    A real meter's record() is fed by the metering pipeline reading actual GPU-seconds
    (Phase C). The stub records whatever it is handed but refuses to *claim* metered
    from estimate data.
    """
    def record(self, reading: MeterReading) -> MeterReading: ...
    def readings_for_run(self, run_id: str) -> list[MeterReading]: ...
    def aggregate_measured_seconds(self, run_id: str) -> float:
        """Sum accelerator_seconds across ONLY fleet_measured readings for the run."""
        ...
    def metered_status(self, run_id: str) -> RunMeteredStatus:
        """COST_METERED iff >=1 fleet_measured reading exists; else COST_NOT_METERED.
        A stub MUST NOT return COST_METERED without a real measured reading."""
        ...


@dataclass(frozen=True)
class InvoiceLine:
    """One billable line. quantity is summed from MEASURED readings only (§4)."""
    run_id: str
    quantity: float
    unit: UsageUnit
    evidence_ref: str         # resolves to run_id + the reading_ids producing `quantity`
    unit_price: float | None = None     # from the versioned price book; None == unpriced (v0)
    amount: float | None = None         # quantity * unit_price; None until priced
    description: str = ""


@dataclass(frozen=True)
class Invoice:
    """A period/account invoice. Every line walks back to measured consumption."""
    id: str
    account_id: str
    period_start: str
    period_end: str
    lines: tuple[InvoiceLine, ...]
    status: InvoiceStatus = "draft"
    currency: str = "USD"
    price_book_version: str = "cas_harness_price_book.v0_unpriced"
    total_amount: float | None = None    # None while unpriced/draft
    settlement_ref: str | None = None    # set only by a real PaymentProvider (Phase F)


@runtime_checkable
class QuotaLedger(Protocol):
    """Caps an account's consumption. Reserve by estimate at admission; settle by
    measurement on completion (§4). The cap the cost gate explicitly does NOT do."""
    def reserve(self, account_id: str, *, run_id: str,
                estimated_accelerator_seconds: float) -> "QuotaDecision": ...
    def settle(self, account_id: str, *, run_id: str,
               measured_accelerator_seconds: float) -> "QuotaDecision": ...
    def remaining_budget_seconds(self, account_id: str) -> float | None: ...


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    account_id: str
    run_id: str
    reason: str
    remaining_after_seconds: float | None = None


@runtime_checkable
class PaymentProvider(Protocol):
    """CLEARLY EXTERNAL. Real money movement (Stripe-class). The stub NEVER charges;
    it raises / returns a labeled fake and never claims a real settlement. Only a real
    provider flips an Invoice to `paid` with a genuine settlement_ref (Phase F)."""
    def charge(self, *, account_id: str, invoice_id: str, amount: float,
               currency: str) -> "PaymentResult": ...


@dataclass(frozen=True)
class PaymentResult:
    succeeded: bool
    settlement_ref: str | None
    is_real: bool             # stub returns False; only a real provider returns True
    notes: str = ""
```

**How a `MeterReading` licenses `COST_METERED` (the central seam).** A run's metered status is
**derived**, never set directly:

```
DistributedAuditRecord (run_id)                      [cas_harness_distributed_audits.py:108]
  └── cost: CostExposureSummary(cost_metered=False)  [hardcoded False, :166 — the promise]
        ▲
        │ flips to COST_METERED ONLY when:
        │
UsageMeter.metered_status(run_id) == "COST_METERED"
        ▲
        │ true iff:
        │
∃ MeterReading(run_id, source="fleet_measured", accelerator_seconds>0)
        ▲
        │ produced by:
        │
Metering pipeline reading ACTUAL GPU-seconds from the fleet/cloud (Phase C, §7)
   — NOT from ScalePlan.recommended_worker_count / estimated_total_runtime_gb (those are the estimate)
```

The estimator path (`source="planner_estimate"`) feeds **quotes and quota reservations only** and is
structurally barred from `metered_status` and from `InvoiceLine`. That bar is the workstream.

---

## 6. Cross-references

- **05 (observability)** — *the consumption telemetry source.* 05's metrics/timing events
  (per-stage, per-worker) are a primary candidate carrier for the GPU-second signal a `MeterReading`
  records. The metering pipeline (Phase C) consumes 05's per-worker busy-time / GPU-utilization
  counters; 05 also receives this workstream's per-reading and per-invoice counters for dashboards.
  Distinction preserved: 05 *observes* timing; 08 *meters* it into billable accelerator-seconds.
- **03 (fleet execution at scale)** — *emits the real consumption signal.* `HeartbeatState`
  (`production/fleet_scale.py`) gives the liveness/timing spine, and a real worker is where GPU-seconds
  are actually burned. The meter integrates worker busy-time over the placement (`PlacementDecision`)
  lifecycle; 03's `WorkerSlot.gpu_type` tells the price book which rate applies. 03 emits *observed*
  facts (alive, placed); 08 turns measured busy-time into `fleet_measured` readings.
- **06 (tenant isolation)** — *partitions/bills per tenant.* `Account.tenant_id` is the billing
  projection of a 06 tenant: 06 owns isolation/keys/partitioning; 08 owns the money. The `tenant_id`
  on `MeterReading`/`Account` is the same partition key 02 (`ArtifactDescriptor.tenant_id`) and 03
  (`WorkerSlot.tenant_id`) carry. Per-tenant quotas (`QuotaLedger`) are 06's quota requirement made
  financial.
- **02 (large artifact object storage)** — *the storage-cost dimension.* `bytes_stored_for_audit` /
  Phase-D `bytes_stored` per audit/tenant (`production/artifact_store.py:335-341`) is the second
  billable unit (`gb_month`). 02's doc already names 08 as the consumer of `size_bytes`
  (`02_large_artifact_object_storage.md` §6); dedup (02 §4) directly changes the metered storage
  number, so the storage line's `evidence_ref` must resolve to 02's descriptor catalog.
- **09 (compliance / records retention)** — *financial-audit retention.* Accounts, readings, and
  invoices are financial records of record: 09 governs how long they are retained, residency, and the
  append-only audit trail. The reservation/settlement ledger (Phase E) and the invoice→reading
  evidence chain (Phase D) are exactly the audit trail 09 must preserve; a 09 redaction request can
  never delete a reading an issued invoice still references.

---

## 7. Open questions (genuinely unresolved)

1. **How are GPU-seconds *authoritatively* measured on RunPod / cloud? (the single most important
   decision — it is what `COST_METERED` *means*.)** Candidates, none yet validated:
   - **Cloud per-pod accounting API** (RunPod billing/usage API) — authoritative for *what the cloud
     charges*, but granularity and per-audit attribution are unclear (a pod may serve >1 run).
   - **NVML/DCGM exporter** scraped via 05 — fine-grained per-GPU busy-time, but it measures the
     *device*, and mapping device-seconds → a specific `run_id`/`shard_id` needs the 03 placement map.
   - **Cloud billing export** (delayed, file-based) — authoritative dollars, but T+1 latency breaks
     real-time quotas.
   Likely answer: **wall-clock GPU-lease-seconds per worker** (lease start→stop from 03's placement +
   heartbeat lifecycle) as the authoritative billable unit, cross-checked against the cloud accounting
   API, with NVML utilization as a *diagnostic* (not the bill). **Decision needed before Phase C** —
   it defines what a `fleet_measured` reading actually contains.
2. **Prepaid vs postpaid.** Prepaid (reserve budget, meter down, refuse at zero — strongest cap, best
   honesty fit because no run exceeds an *acknowledged* prepaid balance) vs postpaid (meter, invoice
   in arrears — friendlier, but needs credit risk + the quota ledger to enforce a soft cap). The cost
   gate's "uncosted, caller-owned, uncapped" frontier framing
   (`cas_harness_cost_acknowledgment.py:99-110`) leans toward **prepaid for frontier** runs and
   postpaid for the validated small lanes — but this is a product/commercial call, not yet made.
3. **Payment provider choice.** Stripe (default, broad, good metered-billing primitives) vs a
   cloud-marketplace billing integration (AWS/GCP Marketplace, if the Harness is sold there) vs
   invoice-only/manual for early enterprise deals. Affects the `PaymentProvider` adapter and whether
   metered usage is reported to a third party's metering API.
4. **Billing granularity for the duration estimate.** Phase B needs *some* honest duration input.
   Per-scale-tier nominal runtime (engineered guess) vs caller-declared expected duration vs
   "estimate disabled, postpaid-only" (§3 Phase B kill). Which is acceptable to the honesty bar
   without inventing a throughput model?
5. **Reconciliation tolerance.** §3 Phase C proposes **±15%** measured-vs-estimate as the
   validate/kill gate. Is that the right initial number, on which known run (Pythia-160M lane vs a
   fixed synthetic fleet), and does breaching it block billing or just flag the estimate as
   untrustworthy (downgrade to postpaid)?
6. **Idempotency / double-billing boundary.** Retried/resumed runs (04) and deduped storage (02) can
   produce duplicate consumption signals. What is the dedup key for a `MeterReading` (`run_id` +
   `worker_id` + lease window?) so a re-leased shard is not billed twice? Needs settling with 04's
   idempotent leasing before Phase D.
