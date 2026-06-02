# 03 — Fleet Execution at Scale

**Workstream:** 03 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the scheduler / autoscaler / placement / backpressure / liveness / recovery layer
that runs audit work across a worker fleet beyond the current 512-worker fan-out cap.

> Scope boundary up front: this workstream owns *deciding where work runs and keeping the fleet
> alive*. It does **not** own the durable job queue itself — that is **workstream 04**, which
> *underpins* 03 (a real scheduler reads/writes a durable queue rather than the in-process deque this
> doc stubs). When in doubt: 04 guarantees a job is not lost; 03 decides which worker runs it, when,
> and what happens when that worker dies. The clean seam between them is in §5 and §6.

---

## 1. Current state — what the code ACTUALLY does today

The Harness already runs a **real, honest, single-orchestrator** distributed audit. The pieces are
trustworthy at their current scope; what is missing is everything that turns one in-process
orchestrator into a *fleet*.

### 1.1 Shard math + the hard fan-out cap

`api/services/cas_harness_scale_planner.py` turns a declared model size into a layer/shard plan:

- **`MAX_WORKER_FANOUT = 512`** (`cas_harness_scale_planner.py:60`) is a hard clamp.
  `_recommended_worker_count` returns `min(MAX_WORKER_FANOUT, max(layer_floor, size_floor,
  memory_floor, minimum_worker_count or 1))` (`:372-375`), and `_validate_request` refuses any
  `minimum_worker_count > MAX_WORKER_FANOUT` outright (`:313-316`). **512 is the ceiling this entire
  workstream exists to lift.**
- `_assign_layers` (`:397-460`) produces `WorkerAssignment`s (`:152-165`) either as contiguous layer
  ranges (worker_count ≤ num_layers) or as per-layer tensor shards (worker_count > num_layers). This
  is the shard placement *plan* — but it is static: worker N always gets `probe-worker-{N}`, a label,
  not a real host bound to real capacity.
- `USABLE_MEMORY_FRACTION = 0.62` (`:52`) is the only capacity model, and it is a *planning
  constant*, not a reading of any real accelerator.

### 1.2 The in-process executor (lease / dispatch / merge)

`api/services/cas_harness_fleet_executor.py` is the execution layer:

- **Fleet state is three process-global dicts**: `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS`
  (`cas_harness_fleet_executor.py:159-161`). They live in one Python process, vanish on restart, and
  do not span hosts. This is the single biggest "not a fleet" fact.
- **Workers self-register and heartbeat** in memory: `register_worker` (`:175-209`),
  `heartbeat_worker` (`:212-220`), with staleness from a single cutoff
  `DEFAULT_MAX_HEARTBEAT_AGE_SECONDS = 120` (`:38`) in `_mark_stale_worker_if_expired`
  (`:598-610`). There is no cross-process heartbeat transport — a worker on another host cannot
  reach this dict.
- **Leasing is a linear scan with an in-memory token**: `lease_next_job` (`:292-324`) walks
  `run.jobs`, finds the first `queued|expired` job for that worker, mints a sha256 `lease_token`
  (`_lease_token_for` `:636-643`), and sets a wall-clock `lease_expires_at`. Lease expiry is
  evaluated lazily on the next call (`_expire_stale_leases` `:562-569`) — there is no timer, no
  background reaper.
- **There is no scheduler.** Placement = "the worker whose id equals the assignment's worker_id may
  lease that assignment's job" (`_assert_worker_can_run_job` `:549-559` checks model_id + supported
  methods). Work does not flow to *available* capacity; it waits for the *specifically named* worker
  to show up. If `probe-worker-417` never registers, its shard never runs and the gate sits at
  `waiting_for_workers` forever (`_refresh_run_gate` `:456-458`).
- **The merge gate is honest and evidence-bound** (this part is production-quality): `merge_fleet_evidence`
  (`:412-446`) refuses to merge until every assigned job has a receipt, and even a clean merge only
  reaches `ready_for_verifier` — `"fleet executor does not fabricate ACCEPT"` (`:441-444`). The
  underlying `merge_distributed_audit` likewise only ever returns `FLAG_FOR_HUMAN_REVIEW`, never
  `ACCEPT` (`cas_harness_distributed_audits.py:469-477`).

### 1.3 The control-plane choke point

`api/services/cas_harness_distributed_audits.py::create_distributed_audit` (`:165-316`) is the single
entry point. It runs the 8 honesty gates, then materializes one `WorkerEvidenceRecord` per planned
assignment (`:287-297`) and stores the run in the process-global `_DISTRIBUTED_AUDITS` dict (`:158`).
Lifecycle: `PLANNED → DISPATCHED → RUNNING → MERGE_PENDING → COMPLETE|FAILED`
(`DistributedAuditStatus` `:59-66`). Every status here is **declared**; the worker tier verifies.

### 1.4 Honest one-line summary

> Today the Harness runs **one orchestrator process** that fans out to **≤512 named, self-registering,
> same-process worker records**, leases jobs by linear scan, tracks liveness with one heartbeat cutoff
> in a dict, and has **no scheduler, no autoscaler, no backpressure, no cross-host liveness, and no
> recovery** of a run whose orchestrator died. It is correct for a single-pod 20B/300B run on a hand-
> registered fleet; it is not a multi-host service.

---

## 2. Gap to production

The delta between §1 and "a real fleet at scale":

1. **The 512 cap itself.** A 1T–4T frontier plan (`scale_validation_status` returns
   `EXPERIMENTAL_NOT_VALIDATED` above 300B — `cas_harness_scale_planner.py:86-98`) can need far more
   than 512 shards, but `_validate_request` refuses `minimum_worker_count > 512` and the count is
   clamped regardless. Lifting the cap is not a one-line change: it requires a scheduler that places
   *more shards than named slots* by reusing capacity over time, plus hierarchical fan-out
   (orchestrator → sub-orchestrators → workers) so one process is not scanning a 5,000-element
   `run.jobs` list on every lease.
2. **No scheduler / no placement engine.** Work is pinned to pre-named worker ids, not flowed to
   whatever capacity is free. Production needs a scheduler that bin-packs shards onto heterogeneous
   workers by (memory fit, method support, model match, tenant) and re-packs as capacity changes.
3. **No autoscaler.** `USABLE_MEMORY_FRACTION`/`MAX_WORKER_FANOUT` are static planning numbers.
   Nothing watches a queue and asks a cloud provider for more workers, or drains idle ones. The
   worker count is decided once at plan time and never adjusts to real demand.
4. **In-memory, single-process state.** `_WORKERS`/`_FLEET_RUNS`/`_DISTRIBUTED_AUDITS` are dicts in
   one process. A fleet spanning hosts needs shared, durable run/worker state (this is where **04**'s
   durable queue and a shared store come in). Per project memory — *"pod can disappear"* — a lost
   orchestrator currently loses the entire run's coordination state.
5. **No backpressure.** `create_distributed_audit` always accepts (modulo the honesty gates). There
   is no admit/throttle/shed decision when the fleet is already saturated, so a burst of audits
   over-commits the fleet and every run thrashes.
6. **Liveness is single-cutoff and in-process.** One 120 s staleness line, evaluated lazily, in a
   dict no other host can read. Production needs a real heartbeat transport, a two-stage
   suspect→lost model (so a brief network blip does not trigger a reclaim), and a background evaluator.
7. **No recovery.** When a worker goes stale, `_expire_worker_leases` (`:572-584`) just flips its
   leased jobs back to `expired` and the gate reverts to `waiting_for_workers` — it waits for *that
   same named worker* to come back. There is no re-placement onto a *different* healthy worker, and
   no recovery at all if the **orchestrator** dies mid-run.

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

### Phase A — Seams + in-memory stubs (no infra)
Define the six seams (`FleetScheduler`, `FleetAutoscaler`, `FleetBackpressure`,
`FleetLivenessMonitor`, `FleetRecoveryCoordinator`, plus the value objects of §5) and ship clearly-
labeled in-memory stubs. No real infra, no new behavior wired into the live executor. *(Delivered
with this doc: `api/services/production/fleet_scale.py` + `tests/test_production_fleet_scale.py`.)*
- **Validate:** scheduler bin-packs compatible shards and marks the rest `FLEET_PLACEMENT_INFEASIBLE`;
  autoscaler recommendation clamps to the 512 cap; backpressure crosses ADMIT→THROTTLE→SHED at its
  watermarks; liveness progresses live→suspect→lost on heartbeat age; recovery re-enqueues a lost
  worker's shards **idempotently**; and a `PlacementDecision` **refuses** to be constructed as
  `FLEET_PLACEMENT_VERIFIED`. (All covered in `test_production_fleet_scale.py`.)
- **Kill:** if the Protocols cannot express the executor's existing
  register/heartbeat/lease/merge shape without leaking in-process-dict assumptions, redesign the seam
  before any backend work.

### Phase B — Real scheduler over a durable queue (04 dependency)
Replace the linear lease-scan with a scheduler that pulls shards from **04**'s durable queue and
places them on workers discovered from a shared registry. Keep fan-out at 512 for this phase — prove
the *placement* model before lifting the cap. Wire it behind the existing `lease_next_job` surface so
the merge gate is unchanged.
- **Validate:** with 512 workers and >512 shards queued, every shard eventually runs as capacity
  frees up (placement reuses a worker across shards), and the merge gate still requires every shard's
  receipt before `ready_for_verifier`. Killing one worker mid-run re-places its in-flight shard onto a
  *different* healthy worker and the run still completes — observed end-to-end, not asserted.
- **Kill:** if placement cannot recover a single lost worker's shard without a full run restart, the
  recovery model is wrong — stop and fix recovery (Phase D) before lifting the cap.

### Phase C — Autoscaling + backpressure against a real provider
Wire `FleetAutoscaler` to a real worker provider (RunPod/k8s/cloud GPU pool) and `FleetBackpressure`
to the admit path at `create_distributed_audit`. Autoscaler recommendations remain *recommendations*
until the provider confirms a worker is up and registered (declared→verified at the infra seam).
- **Validate:** a burst of queued shards drives a real scale-up to (but never past) the configured
  ceiling; idle workers drain; and when the fleet is saturated, new `create_distributed_audit` calls
  receive a `THROTTLE`/`SHED` signal **instead of** over-committing — verified by watching real
  worker count track demand and admitted-run latency stay bounded.
- **Kill:** if scaling oscillates (thrash: up/down/up within one control interval) or a `SHED` ever
  silently drops an *already-admitted* run, disable autoscale, pin to a fixed pool, and ship Phase B
  only.

### Phase D — Cap lift + orchestrator recovery (hierarchical fan-out)
Lift `MAX_WORKER_FANOUT` past 512 via hierarchical fan-out (orchestrator → sub-orchestrators →
workers) and make the **orchestrator** itself recoverable: run/worker/lease state lives in the shared
durable store (04 + a shared registry), so a replacement orchestrator resumes a run whose previous
coordinator died.
- **Validate:** a >512-shard (frontier-lane) run schedules and completes across multiple sub-
  orchestrators; killing the top orchestrator mid-run and starting a replacement resumes from the
  durable state with **zero** lost or double-counted receipts (cross-check the merged Evidence Packet
  fragment set is exactly complete, no dupes). Only then change the `512` constant and the
  `_validate_request` ceiling.
- **Kill:** if resumed runs ever double-count a receipt or lose one (merged fragment set wrong), the
  durable-state model is unsafe — revert to the 512 single-orchestrator ceiling, which is honest, and
  do not ship the lift.

> Sequencing: A is pure-Python (shipped here). B is the first phase needing 04's durable queue. C is
> the first needing a real cloud provider. D needs both plus shared orchestrator state. The cap stays
> **512** until Phase D's recovery proof passes — lifting it earlier would let the system schedule a
> fleet it cannot honestly recover.

---

## 4. Honesty constraints (non-negotiable)

**Statuses at stake** (this workstream introduces these; only the *declared* rungs may be emitted at
the orchestrator/API tier):

| Status | May be emitted by | Becomes true (verified) when |
|---|---|---|
| `FLEET_PLACEMENT_DECLARED` | scheduler (this tier) | — (declaration that a shard was *bound* to a worker) |
| `FLEET_PLACEMENT_VERIFIED` | **worker tier only** | the worker confirms the assigned shard's resident set actually loaded (ties to 01's `ACTIVATION_CAPTURE_VERIFIED`) |
| `FLEET_PLACEMENT_INFEASIBLE` | scheduler (this tier) | — (no capacity slot can hold the shard) |
| liveness `live`/`suspect`/`lost` | liveness monitor (this tier) | — (observed from heartbeat age; an *observation*, never a verdict) |
| admission `ADMIT`/`THROTTLE`/`SHED` | backpressure (this tier) | — (advisory load signal; never an audit verdict) |
| scaling `SCALE_UP`/`DOWN`/`HOLD` | autoscaler (this tier) | provider confirms workers provisioned (declared→verified at the infra seam) |

**What the real backend must exist before any flip to verified:**
- `FLEET_PLACEMENT_VERIFIED` requires a **real worker** that loaded the shard and can attest it — i.e.
  it depends on **01 (worker-side verification)** producing a real resident-set/activation
  attestation. The orchestrator may never self-certify placement; it only knows it *sent* the
  assignment.
- A scaling action only becomes a real *provisioning* fact when the **cloud provider** confirms a
  worker is up and registered. The autoscaler recommendation is honest as a recommendation; it must
  not be reported as "we have N workers" until the provider + registry confirm N.

**What the stub must never claim:**
- The in-memory stubs (`api/services/production/fleet_scale.py`) **must never** emit
  `FLEET_PLACEMENT_VERIFIED`. `PlacementDecision.__post_init__` raises `FleetScaleStateError` if you
  try — a test cannot launder a verified status through it.
- No stub here emits an audit `ACCEPT`/`SUPPRESS` or any `*_VERIFIED`/`*_METERED`/`*_WORM_COMMITTED`
  status (the `production/__init__.py:9-12` rule). The fleet layer **schedules** the work that
  *produces* evidence; the verdict stays with the verifier decision layer, exactly as
  `merge_fleet_evidence` already refuses to fabricate ACCEPT
  (`cas_harness_fleet_executor.py:441-444`).
- The autoscaler stub computes a target worker count but **must not** imply hardware exists. It is a
  number, clamped to the cap — not a fleet.

**Declared-vs-verified at the fleet tier (the sacred line):** the orchestrator/API tier *declares*
placements, *observes* liveness, *advises* admission, and *recommends* scale. Only the worker tier
*verifies* a shard ran, and only a real provider *confirms* capacity. Every object above carries its
origin so a placement walks back to (which scheduler pass, which queue item, which plan assignment) —
the traceability spine.

---

## 5. Interfaces / seams

Concrete `typing.Protocol` / `ABC` / `dataclass` signatures the team builds against. The shippable
scaffold is `api/services/production/fleet_scale.py`; the contract test is
`tests/test_production_fleet_scale.py`. Field names line up with the existing
`WorkerAssignment` (`cas_harness_scale_planner.py:152`), `FleetWorkerRecord`/`FleetJobRecord`
(`cas_harness_fleet_executor.py:45,71`) so a real backend can be fed directly from a plan.

```python
# Status vocabularies — declared-only at this tier (the VERIFIED rung is worker-side).
FleetPlacementStatus = Literal[
    "FLEET_PLACEMENT_DECLARED", "FLEET_PLACEMENT_VERIFIED", "FLEET_PLACEMENT_INFEASIBLE",
]
FleetLivenessStatus  = Literal["live", "suspect", "lost"]
FleetAdmissionSignal = Literal["ADMIT", "THROTTLE", "SHED"]
FleetScalingAction   = Literal["SCALE_UP", "SCALE_DOWN", "HOLD"]

@dataclass(frozen=True)
class WorkerSlot:          # a unit of fleet capacity the scheduler can place onto
    worker_id: str; model_id: str; gpu_type: str
    usable_memory_gb: float; free_capacity: int
    supported_methods: tuple[str, ...]
    tenant_id: str | None = None          # 06 partition key

@dataclass(frozen=True)
class ShardDemand:         # one shard awaiting placement (fed from WorkerAssignment)
    audit_id: str; shard_id: str; layer_start: int; layer_end: int
    required_methods: tuple[str, ...]; estimated_memory_gb: float
    tenant_id: str | None = None; priority: int = 0

@dataclass(frozen=True)
class PlacementDecision:   # __post_init__ RAISES if status == FLEET_PLACEMENT_VERIFIED
    audit_id: str; shard_id: str; worker_id: str
    status: FleetPlacementStatus; reason: str; decided_at: str

@dataclass(frozen=True)
class ScalingRecommendation:
    action: FleetScalingAction; current_workers: int; target_workers: int
    pending_shards: int; reason: str; fanout_cap: int   # clamped to MAX_WORKER_FANOUT

@dataclass(frozen=True)
class BackpressureReading:
    queue_depth: int; inflight: int; capacity: int
    signal: FleetAdmissionSignal; reason: str

@dataclass
class HeartbeatState:
    worker_id: str; last_heartbeat_at: str; liveness: FleetLivenessStatus

@runtime_checkable
class FleetScheduler(Protocol):
    def offer_capacity(self, slot: WorkerSlot) -> None: ...
    def submit_shard(self, shard: ShardDemand) -> None: ...
    def schedule_once(self) -> list[PlacementDecision]: ...   # DECLARED|INFEASIBLE only
    def pending_count(self) -> int: ...

@runtime_checkable
class FleetAutoscaler(Protocol):
    def recommend(self, *, pending_shards: int, current_workers: int) -> ScalingRecommendation: ...

@runtime_checkable
class FleetBackpressure(Protocol):
    def observe(self, *, queue_depth: int, inflight: int) -> BackpressureReading: ...

@runtime_checkable
class FleetLivenessMonitor(Protocol):
    def heartbeat(self, worker_id: str) -> HeartbeatState: ...
    def evaluate(self, *, now: datetime | None = None) -> list[HeartbeatState]: ...
    def lost_workers(self) -> list[str]: ...

class FleetRecoveryCoordinator(ABC):       # ABC: a real coordinator carries durable state
    @abstractmethod
    def reclaim(self, *, lost_worker_id: str) -> list[ShardDemand]: ...
        # MUST be idempotent: reclaiming the same lost worker twice yields its shards ONCE.
```

**Seam to the existing executor.** A real `FleetScheduler` sits *in front of* `lease_next_job`
(`cas_harness_fleet_executor.py:292`): instead of a worker scanning `run.jobs` for its named
assignment, the scheduler hands the worker the next shard placed on it. `submit_shard` is fed from
`plan.worker_assignments`; `offer_capacity` is fed from `register_worker`/`heartbeat_worker`. The
merge gate (`merge_fleet_evidence`) and the fragment-ref integrity check
(`build_evidence_fragment_ref` `:652-680`) are unchanged — the scheduler only changes *who runs
what, when*, not what counts as evidence.

**Seam to liveness.** `FleetLivenessMonitor` generalizes `_mark_stale_worker_if_expired`
(`:598-610`) from one in-process cutoff to a cross-process two-stage (suspect→lost) model. The stub's
`suspect_after_seconds` default equals the executor's `DEFAULT_MAX_HEARTBEAT_AGE_SECONDS = 120` so the
two agree (asserted in the test).

---

## 6. Cross-references

- **04 (queue / resume) — underpins 03.** This is the load-bearing dependency. A real `FleetScheduler`
  pulls from 04's durable, idempotently-leased queue rather than the in-process deque the stub uses;
  04's checkpoint/resume is what makes Phase D's orchestrator recovery possible. The executor's
  current lease/expiry (`lease_next_job` `:292`, `_expire_stale_leases` `:562`) is the *in-memory*
  precedent 04 makes durable. **03 decides placement; 04 guarantees no job is lost.**
- **05 (observability) — consumes 03's signals.** Every object in §5 is a telemetry source: placement
  decisions, `BackpressureReading` (queue_depth/inflight/load), `HeartbeatState` liveness transitions,
  and `ScalingRecommendation`s are exactly the per-stage timing, queue-depth, and liveness metrics 05
  surfaces on the run dashboard and SLOs. 03 emits; 05 records and alerts.
- **06 (tenant isolation) — schedules per tenant.** The `tenant_id` field on `WorkerSlot`/`ShardDemand`
  is the scheduler's partition key (the stub already enforces it: a tenant-scoped shard only lands on a
  same-tenant or unpartitioned slot). Noisy-neighbor isolation is a scheduling concern — per-tenant
  capacity reservations and fair-share live here, on top of 06's data partitioning.
- **08 (billing / accounts) — consumes 03's consumption signal.** The fleet is where accelerator-hours
  are actually spent: which worker ran which shard for how long is the raw `COST_METERED` input. The
  scheduler's placement record + the liveness monitor's run/leave timestamps are 08's metering source.
  Honesty parity: 03 *declares* "this worker was placed on this shard"; only real elapsed worker time
  (worker tier) is *metered*.
- **01 (worker-side verification) — flips 03's placement to verified.** `FLEET_PLACEMENT_VERIFIED` is
  not an orchestrator status; it is produced when 01's real activation capture confirms the assigned
  shard actually loaded and ran. 03 can only declare the binding.
- **02 / 07 (storage / WORM).** The scheduler decides *where* the run happens; the artifacts it
  produces land in 02 and are retained by 07. 03 does not touch storage directly, but a recovery
  re-placement (Phase D) must not orphan partially-written artifacts — coordinate the reclaim with
  02's content-addressed dedup so a re-run shard's bytes collapse to the same key.

---

## 7. Open questions

1. **How high does the cap actually go, and via what topology?** Lifting `MAX_WORKER_FANOUT` past 512
   forces a choice: flat fan-out from one orchestrator (simplest, but one process scans/coordinates
   thousands of jobs) vs. hierarchical (orchestrator → sub-orchestrators → workers, more moving parts
   but each coordinates a bounded slice). A 4T frontier plan at the planner's `_estimated_layers`
   ceiling of 320 layers (`cas_harness_scale_planner.py:331-346`) could shard into thousands of
   tensor slices. **Decision needed before Phase D** — it determines whether recovery is one-level or
   recursive.
2. **Where does shared run/worker/lease state live?** Phase D needs `_WORKERS`/`_FLEET_RUNS`/
   `_DISTRIBUTED_AUDITS` to become durable and fleet-visible. Is that 04's queue store extended, a
   separate shared registry (etcd/Consul/DB), or a control-plane DB? This is the biggest infra
   commitment and it couples 03 tightly to 04.
3. **Recovery granularity: shard, run, or orchestrator?** Re-placing a single lost worker's shard
   (Phase B) is cheap. Resuming a whole run after the orchestrator dies (Phase D) is much harder and
   needs durable state. Is per-shard recovery enough for the 300B engineered lane, with full
   orchestrator recovery reserved for the frontier lane? Affects how much of Phase D is actually
   required for the validated product.
4. **Backpressure policy: where is the watermark, and who owns SHED?** The stub uses a load ratio over
   capacity. In production, does `SHED` reject at the API admit gate (`create_distributed_audit`
   returns 429/503) or queue-with-deadline in 04? And what is the watermark — fleet memory headroom,
   queue depth, or a tenant fair-share budget (06)? Interacts with 08 (a rejected run is not billed).
5. **Suspect→lost thresholds vs. real network reality.** The stub defaults suspect at 120 s, lost at
   240 s. Real values depend on heartbeat transport jitter and the cost of a wrongful reclaim
   (re-running a shard that was actually fine = wasted accelerator-hours = real money via 08). Needs
   tuning against observed heartbeat distributions once 05 is emitting them.
6. **Does autoscaling respect the compute-feasibility gate?** `cas_harness_compute_feasibility.py`
   refuses a run whose declared envelope cannot hold the model under the 512 cap. If autoscaling makes
   the *effective* fleet larger than declared at create time, the feasibility math (computed once at
   `create_distributed_audit`) is stale. Must autoscale re-validate feasibility, or is the declared
   envelope a hard contract the autoscaler may never exceed? Leaning: declared envelope is the hard
   ceiling; autoscale only fills *up to* it, never past.
```
