# 04 — Queue / Resume

**Workstream:** 04 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the durable job queue + idempotent leasing + checkpoint/resume that turns the
in-process fleet executor into something that survives a worker (or orchestrator) dying mid-run.

> Scope boundary up front: this workstream owns **job delivery durability and resumability** — the
> queue, the lease, the checkpoint cursor, the dead-letter + retry policy. It does **not** own
> *placement/autoscaling/backpressure* (that is **03**, which sits on top of this queue) and it does
> **not** own *where partial-result bytes physically land* (that is **02**'s `ArtifactStore`; 04
> stores only a content-addressed **reference** to the blob, never the bytes). When in doubt: 03
> decides *which* worker and *how many*; 04 guarantees the job is *delivered at-least-once, leased
> exactly to one worker at a time, and resumable from its last checkpoint*.

---

## 1. Current state — what the executor actually does today

The fleet executor (`api/services/cas_harness_fleet_executor.py`) already implements a **correct
lease/receipt/merge state machine** — but entirely **in one process's memory**. The leasing
discipline is real and honest; the *durability* is the gap.

### 1.1 The "queue" is three process-global dicts

```python
_WORKERS: dict[str, FleetWorkerRecord] = {}        # cas_harness_fleet_executor.py:159
_FLEET_RUNS: dict[str, FleetRunRecord] = {}         # :160
_FRAGMENT_REFS: set[str] = set()                    # :161
```

There is **no broker, no WAL, no persistence**. `reset_fleet_executor_for_tests()` (`:164-172`)
just `.clear()`s them. A process restart (per project memory, *"pod can disappear"*) loses every
lease, every job state, and every dedup set — the run is unrecoverable and must restart from zero.
Jobs are not even a queue data structure: they live as a `list[FleetJobRecord]` inside each
`FleetRunRecord.jobs` (`:124`), scanned linearly.

### 1.2 Jobs are *materialized at prepare time*, not enqueued on demand

`prepare_fleet_for_audit(audit_id)` (`:240-276`) reads the dispatched audit's
`worker_evidence` and eagerly builds **one `FleetJobRecord` per planned worker assignment**
(`:252-265`), each pre-bound to a specific `assigned_worker_id` (`:75`). The job id is deterministic
— `_job_id_for(audit_id, worker_id, shard_id)` = `fleet-job-<sha256[:16]>` (`:631-633`). So:

- Jobs are **statically partitioned to a named worker** (`probe-worker-001` …). There is no work-
  stealing: a job assigned to `probe-worker-007` can only ever be leased by `probe-worker-007`
  (`lease_next_job` filters `job.assigned_worker_id == worker_id` — `:312`). This is the seam where
  **03** (placement/autoscaling) and 04 (durable delivery) currently collide — see §6.
- The full job set is sized by `recommended_worker_count` from the planner
  (`cas_harness_scale_planner.py:349-375`, capped at `MAX_WORKER_FANOUT = 512`, `:60`). A 300B run
  materializes 300 job records at once (contract test
  `test_300b_fleet_run_requires_all_300_worker_receipts_before_merge_completes`).

### 1.3 Leasing — token-based, single-holder, time-boxed (this part is good)

`lease_next_job(audit_id, worker_id, lease_seconds=900)` (`:292-324`):

- refuses unless the worker is registered and `status == "active"` (`:303-308`);
- calls `_expire_stale_leases(run)` (`:562-569`) first — any `leased` job whose
  `lease_expires_at < now` flips back to `expired` and is re-leasable;
- finds the first job for this worker in `{"queued", "expired"}` (`:311-312`) — **so an expired
  lease is already retryable today, by the same worker**;
- mints a content-derived lease token `_lease_token_for(job, now)` = `sha256({audit, job, worker,
  leased_at})` (`:636-643`), stores both the token and `lease_token_hash` (`:316-317`), sets
  `lease_expires_at = now + lease_seconds` (`:318`).

`submit_job_receipt(...)` (`:327-409`) is the ack: it requires `job.status == "leased"` (`:354`),
**both** `lease_token` and `lease_token_hash` to match (`:356-359`) — a stale/forged token is
rejected — validates the content-addressed fragment ref against a recomputed hash and rejects a
**replayed** ref already in `_FRAGMENT_REFS` (`_validate_fragment_ref` `:683-711`), then clears the
lease token (`:391-392`) and moves the job to `completed`/`failed`. This is **idempotent-leaning
ack with replay protection** — but only within the live process's `_FRAGMENT_REFS` set.

### 1.4 Lease expiry is the *only* failure recovery — and it's pull-driven

Two paths expire a lease: `_expire_stale_leases(run)` (lazy, on the next `lease_next_job`/
`get_fleet_run` → `_refresh_run_gate`) and `_expire_worker_leases(worker_id)` (eager, when a worker
goes stale via `heartbeat_worker`/`mark_stale_workers` — `:572-584`, `:598-610`). Both just set
`job.status = "expired"`. There is **no timer/reaper thread**: if nothing calls into the module,
an abandoned lease sits `leased` forever. Contract tests
`test_stale_worker_cannot_submit_receipt_with_unexpired_lease` and
`test_stale_then_heartbeat_cannot_submit_old_lease` pin this token-invalidation behavior.

### 1.5 What is simply absent today

| Capability | Today | Evidence |
|---|---|---|
| Durable queue (survives restart) | **absent** — in-mem dicts | `:159-161` |
| Checkpoint / resume of a *partial* job | **absent** — a job is atomic; a worker that did 90% of a layer-shard and died re-does 100% | no cursor field on `FleetJobRecord` `:71-115` |
| Dead-letter queue | **absent** — a `failed` job blocks the gate (`blocked_failed_worker` `:459-461`) and waits for human/rerun; nothing routes it to a DLQ | `_refresh_run_gate` `:449-473` |
| Retry policy / backoff | **absent** — `expired` is *immediately* re-leasable, no attempt counter, no backoff, no max-attempts cap | `lease_next_job` `:311-312` |
| Attempt accounting | **absent** — no `attempt`/`delivery_count` field anywhere | `FleetJobRecord` `:71-89` |
| Visibility-timeout reaper | **absent** — expiry is lazy/pull-driven, not a background sweep | §1.4 |
| Cross-process leasing | **absent** — `_WORKERS`/`_FLEET_RUNS` are not shared across orchestrator replicas | `:159-160` |

**Honest summary:** the executor is a faithful *single-process simulation* of a durable queue. The
lease semantics (single holder, token-validated, time-boxed, replay-protected ack) are exactly the
semantics a real broker must preserve — so the migration is "back the same state machine with a
durable broker + a checkpoint cursor," not "rewrite the contract."

---

## 2. Gap to production

The delta from §1 to a durable, idempotent, resumable queue:

1. **Durable, out-of-process queue.** Job state, lease state, and the dedup set must live in a
   store that survives orchestrator/worker restart and is shared across orchestrator replicas
   (so 03 can run more than one scheduler). Today they are three module globals.
2. **Idempotent leasing across processes.** `lease_next_job` must become an atomic compare-and-set
   in the broker (claim ⇒ set visibility deadline) so two orchestrator replicas can't hand the same
   job to two workers. The token discipline (`:316-317`, `:356-359`) is the right primitive; it just
   needs to be enforced by the broker's atomic claim, not a Python dict mutation.
3. **Visibility-timeout reaper.** Lease expiry must be driven by a background sweep (or the broker's
   native visibility timeout), not only by the next incidental call (§1.4), so an abandoned lease is
   reliably reclaimed within a bounded time even if no worker polls.
4. **Checkpoint / resume.** A long shard job (a 300B layer-range probe) must persist a **cursor +
   partial-result reference** periodically, so a re-lease after a crash resumes from the cursor
   instead of recomputing the whole shard. This needs (a) a `Checkpoint` record in the durable
   store and (b) a `partial_result_ref` pointing at a **02** `ArtifactStore` blob.
5. **Dead-letter policy.** A job that exhausts `max_attempts` (or hits a non-retryable error class)
   must move to a **dead-letter queue** with its full failure history, *instead of* either silently
   retrying forever or permanently wedging the run's verifier gate. The DLQ is the honest
   "we tried N times and stopped" surface — it must still drive the gate to `blocked_failed_worker`,
   never to ACCEPT.
6. **Retry policy with backoff + attempt cap.** `expired`/`failed`-retryable jobs need an `attempt`
   counter, an exponential-backoff `not_before` timestamp (so a re-lease isn't instantaneous), and a
   `max_attempts` ceiling after which the job dead-letters.
7. **Exactly-once-effect merge.** With at-least-once delivery (the only honest guarantee over an
   unreliable fleet), the **merge** must be idempotent under duplicate receipts. The content-
   addressed fragment ref + `_FRAGMENT_REFS` replay check (`:710-711`) is already the right idea;
   it must be **durable** (a persisted dedup index, not an in-mem `set`) so a duplicate receipt
   delivered after a restart is still rejected.

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

### Phase A — `DurableQueue` / `Lease` / `Checkpoint` Protocols + in-memory stub
Define the seams of §5 and ship a clearly-labeled **in-memory stub** (`InMemoryQueueStub`) that
re-implements the executor's lease/ack/expire semantics behind the Protocol — *explicitly labeled
non-durable*. No real infra. (Delivered with this doc:
`api/services/production/queue_resume.py`.)
- **Validate:** enqueue → lease (one holder) → second lease of same job is refused while leased →
  extend_lease pushes the deadline → nack with backoff makes the job invisible until `not_before` →
  ack is idempotent (second ack of the same lease is a no-op, not an error) → expiry after the
  visibility deadline makes the job re-leasable with `attempt` incremented → max-attempts dead-
  letters. (`tests/test_production_queue_resume.py`.)
- **Kill:** if the Protocol cannot express the executor's existing token-validated single-holder
  lease (`:316-317`, `:356-359`) without leaking broker specifics, redesign the seam before any
  backend work.

### Phase B — Idempotency + checkpoint semantics lock
Freeze the idempotency contract: (a) `lease` returns a `Lease` carrying `(lease_id, deadline,
attempt)`; (b) `ack(lease_id, receipt)` is keyed by a durable **idempotency key** = the content-
addressed fragment ref (`build_evidence_fragment_ref` `:652-680`), so a duplicate ack is detected
and dropped; (c) `checkpoint(run_id, shard_id, cursor, partial_result_ref)` is **monotonic** —
a checkpoint with a cursor at or behind the stored one is rejected (no rewind). Implement these in
the stub.
- **Validate:** replaying a previously-acked fragment ref is rejected exactly as the live
  `_validate_fragment_ref` rejects an already-present ref (`:710-711`); a resumed job reads back the
  last checkpoint cursor; an out-of-order/stale checkpoint is refused.
- **Kill:** if the idempotency key cannot be made stable across a worker restart (i.e. the worker
  cannot recompute the *same* fragment ref for the *same* work after resuming from a checkpoint),
  at-least-once + idempotent-merge is unachievable — fall back to documenting at-least-once **with a
  human-reviewed dedup** at merge and do not claim exactly-once-effect.

### Phase C — Real durable broker backend
Implement a `DurableQueue` over a real broker (see §7 open question — recommend a transactional
store the orchestrator already needs: **Postgres `SELECT … FOR UPDATE SKIP LOCKED`** for the claim,
or **SQS/Redis-Streams** if the fleet is already on that infra). The claim is the broker's atomic
compare-and-set; the visibility timeout is the broker's native one (SQS) or a `leased_until` column
+ reaper (Postgres). Persist the dedup index and the checkpoint table.
- **Validate:** kill the orchestrator process mid-run and restart → all leases, job states, dedup
  set, and checkpoints survive; two orchestrator replicas leasing concurrently never double-deliver
  a job (claim is atomic); an abandoned lease is reclaimed by the reaper within the visibility
  timeout without any worker polling; a duplicate receipt after restart is still rejected by the
  durable dedup index.
- **Kill:** if the chosen broker cannot give an atomic single-claim + visibility timeout (i.e.
  it can double-deliver *under contention*, not just on timeout), it cannot back idempotent leasing —
  switch brokers before wiring the executor to it. (At-least-once-on-timeout is fine and expected;
  double-claim-under-contention is the disqualifier.)

### Phase D — Checkpoint/resume wired into the worker loop + DLQ operations
Make the live shard worker call `checkpoint(...)` every N layers / T seconds, writing
`partial_result_ref` to the **02** `ArtifactStore`; on re-lease, the worker reads the last
checkpoint and resumes. Wire the dead-letter queue into `_refresh_run_gate` so a dead-lettered job
drives `blocked_failed_worker` (`:459-461`) with the full attempt history, and expose a
`list_dead_letters(run_id)` + a `requeue_dead_letter(job_id)` operator action.
- **Validate:** a worker killed at 60% of a 160-layer shard resumes from its last checkpoint and the
  re-leased attempt completes the *remaining* layers (not all 160); a job that fails `max_attempts`
  times lands in the DLQ, the verifier gate goes `blocked_failed_worker` (never ACCEPT), and an
  operator can requeue it; `bytes`/attempt counts reconcile.
- **Kill:** if resumed partial results cannot be proven to compose into the **same** evidence
  fragment as a single-shot run (i.e. checkpoint+resume changes the merged readout), disable resume
  and fall back to full-shard retry — correctness of the harvested signal outranks resume savings.

> Sequencing: A and B are pure-Python (no infra), land together. C is the first phase needing a real
> broker + credentials. D needs C **and** 02's `ArtifactStore` (for `partial_result_ref`). 03's
> scheduler attaches at the seams A defines, so 03 is not blocked on C/D landing.

---

## 4. Honesty constraints (non-negotiable)

- **A stub queue must never claim durability.** Per `production/__init__.py:9-12`, the in-memory
  `InMemoryQueueStub` MUST NOT emit any `*_VERIFIED` / `*_METERED` / `*_WORM_COMMITTED` status, and
  specifically MUST NOT report a job/checkpoint as `durably_committed` / `replicated` / `persisted`.
  It may honestly report `accepted_in_memory` and `delivery_guarantee="none_process_local"`. The
  flip to `durably_committed=True` is only honest from the **real broker backend** (Phase C) after
  the write is actually fsynced/replicated.
- **Declared vs delivered is the queue's version of declared vs verified.** `enqueue` returning an
  id is a *declaration* that a job was accepted. Only a `DurableQueue` whose backend has actually
  persisted the record may report it durable. The API tier may *declare* a run is queued; only the
  fleet-adjacent durable broker may assert the job is durably enqueued — consistent with the gate-
  series split (`00_index.md:24-34`).
- **At-least-once is the honest delivery guarantee; say so.** Over an unreliable fleet, exactly-once
  *delivery* is not achievable. The honest claim is **at-least-once delivery + idempotent merge =
  exactly-once *effect***. A stub or doc must never advertise "exactly-once delivery." If the
  idempotency key can't be made durable (Phase B kill), the system must downgrade its claim to
  "at-least-once with human-reviewed dedup," not silently keep the stronger label.
- **A dead-letter is not an ACCEPT and not a silent drop.** A dead-lettered job must drive the
  verifier gate to `blocked_failed_worker` (`:459-461`) with its failure history attached — never
  let exhausted retries quietly disappear and let the gate read "ready." Honesty: "we tried N times,
  stopped, and the run cannot support ACCEPT" is the only truthful terminal state for a job that
  never produced a receipt. (Mirrors `merge_distributed_audit`'s refusal to ACCEPT on failed/missing
  evidence — `cas_harness_distributed_audits.py:434-467`.)
- **Replay protection must be durable, or the dedup claim is a lie.** The live `_FRAGMENT_REFS`
  replay check (`:710-711`) is correct but in-memory; a duplicate receipt after a restart would slip
  through. A production queue that claims idempotent ack MUST persist the dedup index. A stub may
  only claim *process-local* replay protection.
- **A checkpoint cursor must never let a run look more complete than it is.** `partial_result_ref`
  points at *partial* bytes; a checkpoint is not a receipt. Resume must re-emit the canonical,
  content-addressed fragment ref for the *whole* shard before the job counts as `completed`
  (`submit_job_receipt` still gates the fragment-ref hash — `:360-382`). The checkpoint accelerates
  recovery; it never substitutes for the receipt.

---

## 5. Interfaces / seams

Concrete `typing.Protocol` / `dataclass` shapes (the shippable scaffold is
`api/services/production/queue_resume.py`). Method shapes mirror the executor's existing
lease/receipt so a real broker is a drop-in for `_FLEET_RUNS`-backed leasing.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Literal, Sequence

JobStatus = Literal["queued", "leased", "completed", "failed", "dead_letter"]
DeliveryGuarantee = Literal["none_process_local", "at_least_once"]  # never "exactly_once"


@dataclass(frozen=True)
class QueueJob:
    job_id: str                  # == _job_id_for(audit, worker, shard): fleet_executor.py:631
    run_id: str                  # the distributed audit_id
    shard_id: str
    assigned_worker_id: str | None  # None once 03 enables work-stealing; today: pinned
    payload_ref: str             # pointer to the assignment (layer range, methods, expected outputs)
    not_before: str | None = None   # backoff gate: not leasable until this ISO-8601 instant
    attempt: int = 0             # delivery/attempt count (absent in today's FleetJobRecord)
    max_attempts: int = 5
    status: JobStatus = "queued"


@dataclass(frozen=True)
class Lease:
    lease_id: str                # opaque; maps to today's lease_token (fleet_executor.py:316)
    job_id: str
    worker_id: str
    deadline: str                # ISO-8601 visibility deadline (today: lease_expires_at :318)
    attempt: int                 # which delivery attempt this lease represents


@dataclass(frozen=True)
class Checkpoint:
    run_id: str
    shard_id: str
    cursor: int                  # monotonic progress marker, e.g. last completed layer index
    partial_result_ref: str | None  # 02 ArtifactStore key (sha256:<digest>) for partial bytes; None if cursor-only
    created_at: str
    schema_version: str = "cas_harness_checkpoint.v1"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_backoff_seconds: float = 2.0     # exponential: base * 2**(attempt-1)
    max_backoff_seconds: float = 900.0
    jitter_seconds: float = 0.0           # +/- jitter to de-synchronize fleet retries

    def next_not_before(self, *, attempt: int, now_iso: str) -> str: ...
        # Compute the backoff gate for the next attempt; pure function over (attempt, now).


@dataclass(frozen=True)
class DeadLetterPolicy:
    # Non-retryable error classes go straight to DLQ regardless of attempt count.
    non_retryable_error_substrings: Sequence[str] = field(
        default_factory=lambda: ("model_id does not match", "does not support assigned methods")
    )  # mirrors FleetExecutorStateError messages that a retry can never fix (fleet_executor.py:553-559)

    def should_dead_letter(self, *, attempt: int, max_attempts: int, error_message: str | None) -> bool: ...


@dataclass(frozen=True)
class DeadLetterRecord:
    job_id: str
    run_id: str
    shard_id: str
    final_attempt: int
    error_history: tuple[str, ...]   # every attempt's error, in order — the "show your work" trail
    dead_lettered_at: str


class DurableQueue(Protocol):
    # Delivery guarantee a backend actually provides. A stub MUST return
    # "none_process_local"; only a real durable broker may return "at_least_once".
    @property
    def delivery_guarantee(self) -> DeliveryGuarantee: ...

    def enqueue(self, job: QueueJob) -> str: ...
        # Idempotent on job_id (re-enqueue of an existing id is a no-op, returns the id).
        # Returns the job_id. Does NOT assert durability unless the backend is real.

    def lease(self, *, run_id: str, worker_id: str, lease_seconds: int = 900) -> Lease | None:
        ...
        # Atomic single-claim: pick the oldest leasable job (queued|expired, not_before<=now,
        # attempt<max_attempts, matching worker if pinned), set its visibility deadline, increment
        # attempt, return a Lease. None if nothing leasable. Mirrors lease_next_job (:292-324) but
        # the claim is atomic in the backend so two callers never double-lease.

    def ack(self, *, lease_id: str, idempotency_key: str) -> bool: ...
        # Complete the leased job. idempotency_key == the content-addressed fragment ref
        # (build_evidence_fragment_ref :652-680). Returns True on first ack, False if this key was
        # already acked (durable replay protection — durable analog of _FRAGMENT_REFS :710-711).
        # A second ack of the same lease/key is a NO-OP, never an error (idempotent).

    def nack(self, *, lease_id: str, error_message: str, retry: RetryPolicy,
             dlq: DeadLetterPolicy) -> JobStatus: ...
        # Negative ack. Applies dlq.should_dead_letter; if so -> "dead_letter" with error history;
        # else releases the lease, sets attempt+1's not_before via retry.next_not_before, status
        # back to "queued". Returns the resulting status.

    def extend_lease(self, *, lease_id: str, lease_seconds: int = 900) -> Lease | None: ...
        # Heartbeat-driven visibility extension for a long shard still making progress. None if the
        # lease already expired/was reclaimed (worker must re-lease and resume from checkpoint).

    def reap_expired(self, *, now_iso: str | None = None) -> Sequence[str]: ...
        # Background sweep: any lease past its deadline -> released (status "queued", attempt kept).
        # Returns reclaimed job_ids. This is the active reaper the in-memory executor lacks (§1.4).

    def checkpoint(self, ckpt: Checkpoint) -> bool: ...
        # Monotonic: reject (return False) a checkpoint whose cursor <= the stored cursor for
        # (run_id, shard_id). No rewind. True if accepted/advanced.

    def latest_checkpoint(self, *, run_id: str, shard_id: str) -> Checkpoint | None: ...
        # Resume point read by a re-leased worker. None if no checkpoint yet (start from scratch).

    def list_dead_letters(self, *, run_id: str) -> Sequence[DeadLetterRecord]: ...

    def requeue_dead_letter(self, *, job_id: str) -> bool: ...
        # Operator action: reset attempt, status -> "queued". The only path out of the DLQ.
```

**Seam to the live executor.** Today `lease_next_job`/`submit_job_receipt` mutate `_FLEET_RUNS`
directly. Under this seam, the executor's `FleetJobRecord` becomes a **projection** of a `QueueJob`:
`lease_next_job` delegates to `DurableQueue.lease`, `submit_job_receipt` delegates to
`DurableQueue.ack` with `idempotency_key = build_evidence_fragment_ref(...)`, and the lazy expiry in
`_expire_stale_leases` is replaced by `reap_expired`. The merge gate (`_refresh_run_gate` `:449-473`)
reads queue/DLQ state instead of the in-mem job list. The lease *token* discipline is preserved —
`Lease.lease_id` is the durable analog of `lease_token`/`lease_token_hash` (`:316-317`).

**Seam to checkpoints/partial bytes (02).** `Checkpoint.partial_result_ref` is an **02**
`ArtifactStore` key (`sha256:<digest>` — see `02_large_artifact_object_storage.md` §5). 04 stores
only the *reference* in its checkpoint table; the partial-activation bytes live in 02. Clean
split: 02 = durable self-verifying bytes; 04 = "this run/shard reached cursor C and its partial
output is that blob."

---

## 6. Cross-references

- **03 (fleet execution at scale)** *sits on top of 04.* 03 owns placement/autoscaling/backpressure;
  it calls `DurableQueue.lease`/`ack`/`nack`/`extend_lease`/`reap_expired` and never touches a broker
  directly. **The key collision to resolve with 03:** today jobs are *pinned* to a named
  `assigned_worker_id` at prepare time (`cas_harness_fleet_executor.py:75,312`). For 03 to autoscale
  and work-steal, `QueueJob.assigned_worker_id` must be allowed to be `None` (any compatible worker
  claims it) — but then the model/method-compatibility check that `lease_next_job` does via
  `_assert_worker_can_run_job` (`:549-559`) must move *into* the `lease` claim predicate so an
  unpinned job is only handed to a worker that can actually run it. That is the single most important
  04↔03 interface decision (§7).
- **02 (large artifact object storage)** *holds 04's checkpoint/partial-result blobs.*
  `Checkpoint.partial_result_ref` is an 02 `ArtifactStore` key; 04 persists the reference, 02
  persists the bytes (self-verifying via integrity-on-read). 04 never stores tensor bytes itself.
- **05 (observability)** *surfaces 04's health signals.* The metrics 05 must emit from this queue:
  **queue depth** (per run + global, leasable vs total), **lease-expiry / reclaim rate**
  (`reap_expired` count over time — a rising rate signals dying workers), **retry counts &
  attempt-distribution** per job, **dead-letter count** per run, **checkpoint lag** (cursor vs total
  shard size), and **time-in-queue** before first lease. A `dead_letter` count > 0 must be an
  alert-worthy SLO breach because it means the run cannot ACCEPT.
- **01 (worker-side verification)** *produces the idempotency key 04 dedups on.* The content-
  addressed fragment ref (`build_evidence_fragment_ref` `:652-680`) that 01's verified capture emits
  IS `ack(idempotency_key=...)`. One hash, computed once, is both 01's evidence identity and 04's
  dedup key — no double-hashing.
- **08 (billing/accounts)** *meters retries 04 exposes.* Re-leased attempts consume real
  accelerator-hours; the `attempt` counter and DLQ history are the signal 08 needs so a customer is
  billed for genuine compute, and so runaway-retry cost is visible. (A backoff/`max_attempts` cap is
  also a cost guardrail.)
- **09 (compliance)** governs DLQ retention: a `DeadLetterRecord.error_history` may contain
  customer-model-identifying detail, so its retention/redaction falls under 09's policy.

---

## 7. Open questions

1. **Exactly-once-effect vs at-least-once + idempotent merge — confirm the honest claim.**
   Recommendation: commit publicly to **at-least-once delivery + idempotent merge (= exactly-once
   effect)**, never "exactly-once delivery." This hinges on the idempotency key
   (`build_evidence_fragment_ref`) being **durable and recomputable after a resume** (Phase B). The
   decision a human must ratify: *is exactly-once-effect via the content-addressed fragment ref the
   contract, or do we accept at-least-once with a human dedup at merge?* This is the workstream's
   load-bearing decision (see §4).
2. **Queue technology choice.** Candidates: (a) **Postgres `FOR UPDATE SKIP LOCKED`** — no new infra
   if the orchestrator already needs a DB, transactional with the audit records, easy reaper via a
   `leased_until` column; (b) **AWS SQS** — native visibility timeout + DLQ + at-least-once, but
   opaque ordering and a separate dedup store still needed; (c) **Redis Streams / consumer groups** —
   fast, `XAUTOCLAIM` for reclaim, but persistence/HA needs care. Recommend **Postgres** for the
   first durable backend (fewest moving parts, transactional with the merge), revisit SQS at fleet
   scale. **Decision needed before Phase C.**
3. **Pinned-shard vs work-stealing (the 03 boundary).** Resolving this changes `QueueJob`: keep
   jobs pinned (simplest, matches today, but no autoscaling/rebalancing) or make
   `assigned_worker_id` nullable and move compatibility into the lease predicate (enables 03 but
   complicates the claim). Must be decided jointly with 03 before Phase C.
4. **Checkpoint granularity & cost.** How often does a shard worker checkpoint — every N layers,
   every T seconds, or on a memory-pressure signal? Too frequent = 02 write amplification (each
   `partial_result_ref` is a real blob); too sparse = large redo on resume. Interacts with 02 cost
   and 08 metering. Needs a default + a knob.
5. **Reaper ownership & cadence.** Is `reap_expired` a dedicated orchestrator background task, a
   broker-native visibility timeout (SQS), or piggybacked on each `lease` call (today's lazy model,
   but made unconditional)? Affects the worst-case reclaim latency 05 must SLO.
6. **Resume correctness proof.** Can a checkpoint+resume shard be *proven* to produce the same
   content-addressed evidence fragment as a single-shot run (Phase D kill gate)? If layer-range
   probing is order-sensitive in a way that resume perturbs, resume must be disabled for that method
   and only full-shard retry used — correctness of the harvested CAS signal outranks resume savings.
7. **Multi-orchestrator leasing.** When 03 runs >1 scheduler replica, the atomic-claim guarantee
   (no double-lease under contention) must hold across replicas. Postgres `SKIP LOCKED` gives this
   for free; an in-process stub cannot (single process only) — so the stub must *document* that it
   provides single-process leasing only, never cross-replica safety.
