# 10 — State Substrate Migration

**Workstream:** 10 of 11 · **Status:** Phases 0–2 implemented behind the `LedgerMirror` seam (dual-write + shadow-read, **zero divergence** proven on `InMemoryStateStore`); single-host durability **and rehydrate-on-startup** proven on `SqliteStateStore`; Phase 3 read-authority flip **mechanism built dark** — reversible, fail-closed, proven by clearing the dicts and still serving from the ledger; its operational enable in a durable deployment, the multi-host smoke, and Phase 4 still gated on workstream 11 · **Date:** Jun 1, 2026
**Owner seam:** the cutover that moves run/worker/fleet/fragment state out of process-global Python
dicts and onto the durable, tenant-scoped, version-checked `StateStore` ledger.

> Scope boundary up front: this workstream owns *where state lives* — it relocates the four global
> dicts onto `api/services/production/state_substrate/`'s `StateStore`. It does **not** own *who may
> mint a verified status*: that boundary is the honesty spine the gate series already enforces, and
> the migration must carry it across unchanged. A status (`*_VERIFIED` / `*_METERED` /
> `*_WORM_COMMITTED`) is produced *where the real thing happened*; moving the bytes from RAM to a
> ledger does not move that authority. The substrate package itself says so: it is "real, tested
> infrastructure" but "**not yet wired in**" (`api/services/production/state_substrate/__init__.py:40-44`).
> The concrete durable backends this consumes — SQLite (single-host) and Postgres/Redis (multi-host) —
> are workstream **11**; this doc targets the *interface*, so a backend swap is a config change, not a
> re-migration.

---

## 1. Current state — what the code ACTUALLY does today

Four process-global containers hold the entire control-plane state of a distributed CAS Harness audit.
Each is correct for a single Python process that never restarts and serves one customer; each is fatal
for a public product for the same three reasons (restart, multi-host, multi-tenant), spelled out in §2.

### 1.1 `_DISTRIBUTED_AUDITS` — the audit control ledger

`api/services/cas_harness_distributed_audits.py`:

- **`_DISTRIBUTED_AUDITS: dict[str, DistributedAuditRecord] = {}`** (`cas_harness_distributed_audits.py:158`)
  is the process-global audit ledger. It is keyed by **`audit_id` ONLY** — there is no tenant
  dimension in the key. Each value is a `DistributedAuditRecord` carrying the run's plan, the 8 honesty
  receipts (access / provenance / architecture / probe / compute / cost / data_capture), lifecycle
  status (`PLANNED → DISPATCHED → RUNNING → MERGE_PENDING → COMPLETE|FAILED`), and the per-assignment
  `WorkerEvidenceRecord` list.
- `create_distributed_audit` mints the id with `_audit_id_for(plan)` (`:285`) and writes the record
  with `_DISTRIBUTED_AUDITS[audit_id] = record` (`:315`).
- `_audit_id_for` (`:481-491`) builds the id from `model_id / parameter_count_b / num_layers /
  worker_count / precision / run_nonce`, sha256-digests it, and returns `cas-dist-<digest[:16]>`. The
  `run_nonce = uuid4().hex` (`:488`) makes the id unique per call — but **only within this process's
  RAM**; nothing persists it, so a restart cannot rediscover an in-flight id.
- Reads are `get_distributed_audit(audit_id)` (`:319-320`) and `list_distributed_audits()`
  (`:323-324`) — both straight dict access, both tenant-blind.
- The merge gate is honest and stays honest: `merge_distributed_audit` only ever lands
  `FLAG_FOR_HUMAN_REVIEW`, never `ACCEPT` (`:469-477`) — "Final ACCEPT/SUPPRESS still requires the
  verifier decision layer."

### 1.2 `_WORKERS` — the fleet worker registry

`api/services/cas_harness_fleet_executor.py`:

- **`_WORKERS: dict[str, FleetWorkerRecord] = {}`** (`cas_harness_fleet_executor.py:159`), keyed by
  `worker_id`. A `FleetWorkerRecord` (`:45-55`) holds `model_id / worker_url / gpu_type / capacity /
  supported_methods / registered_at / last_heartbeat_at / status`.
- `register_worker` writes `_WORKERS[record.worker_id] = record` (`:208`) and refuses a duplicate id
  (`:193-195`). `heartbeat_worker` (`:212-220`) mutates `last_heartbeat_at` in place. Liveness is one
  cutoff, `DEFAULT_MAX_HEARTBEAT_AGE_SECONDS = 120` (`:38`), evaluated lazily in
  `_mark_stale_worker_if_expired` (`:598-610`). No worker on another host can reach this dict.

### 1.3 `_FLEET_RUNS` — the fleet run + lease state

- **`_FLEET_RUNS: dict[str, FleetRunRecord] = {}`** (`cas_harness_fleet_executor.py:160`), keyed by
  `audit_id`. A `FleetRunRecord` (`:118-127`) owns the run's `jobs: list[FleetJobRecord]`,
  `verifier_gate_status`, and `merged_packet_trace_id`. Each `FleetJobRecord` (`:71-90`) carries the
  **lease state in-line**: `lease_token`, `lease_token_hash`, `lease_expires_at`, plus the produced
  fragment ref.
- `prepare_fleet_for_audit` writes `_FLEET_RUNS[audit_id] = record` (`:274`). The lease/ack/merge flow
  reads and mutates the run dict directly:
  - `lease_next_job` (`:292-324`) linear-scans `run.jobs`, and on the first leasable job mints
    `job.lease_token = _lease_token_for(job, now)` (`:316`) and `job.lease_token_hash =
    _hash_token(job.lease_token)` (`:317`), with a wall-clock `lease_expires_at` (`:318`).
  - `submit_job_receipt` (`:327-…`) verifies BOTH `job.lease_token != lease_token` (`:356`) and
    `job.lease_token_hash != _hash_token(lease_token)` (`:358`) before accepting the receipt — the
    single-holder proof.
  - `_expire_stale_leases` (`:562-569`) and `_expire_worker_leases` (`:572-584`) reclaim a lease by
    nulling the token fields in place. Placement is pinned: a job runs only on the worker whose id
    equals `job.assigned_worker_id` (`_assert_worker_can_run_job` `:549-559`).
  - The merge gate `merge_fleet_evidence` (`:412-446`) refuses to merge until every assigned job has a
    receipt and even a clean merge reaches only `ready_for_verifier` — "fleet executor does not
    fabricate ACCEPT" (`:441-444`).

### 1.4 `_FRAGMENT_REFS` — the content-addressed dedup set

- **`_FRAGMENT_REFS: set[str] = set()`** (`cas_harness_fleet_executor.py:161`). Not a record store — a
  *dedup guard*. `build_evidence_fragment_ref` (`:652-680`) produces a content-addressed ref
  `cas-fragment://<audit>/<job>/<worker>/<shard>/sha256:<digest>` (`:680`) where the digest covers the
  canonical fragment payload. On receipt, `submit_job_receipt` adds the ref with
  `_FRAGMENT_REFS.add(job.evidence_packet_fragment_ref)` (`:395`); `_validate_fragment_ref` rejects a
  replay with `if fragment_ref in _FRAGMENT_REFS` (`:710-711`). The set is the only memory that a
  given fragment was already submitted.

### 1.5 The missing tenant dimension

None of the four containers is keyed by tenant, and there is **no honest source of a tenant id** to key
on even if they were. The JWT attaches only `request.state.user = payload.get("sub", …)` (`auth.py:78`)
and `request.state.api_key = payload.get("api_key", "default")` (`auth.py:79`); `create_token` mints
exactly `{"sub", "api_key", "exp"}` (`auth.py:91`) — **no tenant claim**. Rate limiting is per-`api_key`
too (`rate_limit.py:87`, `:90`, `:101-103`), not per-tenant. This is the gap workstream **06** closes;
this migration must build the *seam* tenant-scoped while honestly admitting there is no real tenant yet.

### 1.6 Honest one-line summary

> Today the Harness keeps its entire distributed-audit control plane — audit ledger, worker registry,
> run+lease state, and the fragment dedup set — in **four process-global dicts/sets in one Python
> process**, keyed by `audit_id`/`worker_id` with **no tenant dimension** and **no durability**. It is
> correct for a single-pod run; it cannot survive a restart, be shared across hosts, or hold two
> tenants apart.

---

## 2. Gap to production

The delta between §1 and "a durable, multi-host, multi-tenant control plane." Each consequence ties to a
concrete failure, not an abstraction.

1. **No durability — restart loses in-flight audits.** The dicts live in RAM
   (`cas_harness_distributed_audits.py:158`, `cas_harness_fleet_executor.py:159-161`). A pod restart —
   and per project memory, *"pod can disappear"* — erases every `DistributedAuditRecord`, every
   `FleetRunRecord`, every leased `lease_token`, and the entire `_FRAGMENT_REFS` set. A run that was
   `MERGE_PENDING` with 400 of 512 receipts in is simply gone; the workers that already burned
   accelerator-hours have nowhere to return their receipts. Worse, the lost `_FRAGMENT_REFS` set means
   that even if workers re-submitted, the **replay guard** (`:710-711`) is empty, so duplicate
   fragments would be silently accepted — a correctness failure, not just a loss.
2. **No host-sharing — a second API host can't see the first's workers.** `register_worker` writes to
   *this* process's `_WORKERS` (`:208`). A worker that registered against host A is invisible to host
   B's `_WORKERS.get(worker_id)` in `lease_next_job` (`:303`), which raises "Worker must register
   before leasing jobs" (`:305`). Two API replicas behind a load balancer cannot cooperate on one run:
   whichever host did `prepare_fleet_for_audit` owns the only copy of `_FLEET_RUNS[audit_id]` (`:274`),
   and the other host's `merge_fleet_evidence` returns `None` (`:413-415`) because the run isn't in its
   dict. There is no scheduler horizon beyond one process.
3. **No tenant partition — tenant A's `audit_id` can collide with tenant B's.** Keys are tenant-blind
   (`_DISTRIBUTED_AUDITS[audit_id]`, `_FLEET_RUNS[audit_id]`, `_WORKERS[worker_id]`). The `run_nonce` in
   `_audit_id_for` (`:488`) makes *accidental* collision unlikely, but nothing *enforces* isolation: a
   caller who learns or guesses another tenant's `audit_id` reads their record straight out of
   `get_distributed_audit` (`:319-320`) with no tenant check, and a `worker_id` reused across tenants
   overwrites — `register_worker` refuses the *second* registration (`:193-195`), letting tenant B deny
   tenant A a worker slot by squatting the id. There is no boundary because there is no tenant key, and
   no tenant key because there is no tenant claim (`auth.py:91`).
4. **Concurrency is last-writer-wins.** In-place mutation of dict values (`heartbeat_worker` `:218-219`,
   the lease mint at `:315-319`, the gate flip in `_refresh_run_gate` `:449-471`) has no version guard.
   The moment two schedulers touch one `FleetRunRecord`, the later write clobbers the earlier with no
   signal — exactly the race the substrate's optimistic concurrency exists to refuse
   (`interface.py:95-111`).

---

## 3. Migration plan (strangler-fig, each phase with a kill/validate gate)

The cutover touches the request-handling path, so it lands as a **strangler fig**: the new ledger grows
*alongside* the dicts, takes over reads only after writes are proven to agree, and the dicts are removed
only after the ledger is sole source of truth and survives a restart. No phase is a flag-day rewrite.

The four globals share one mapping onto the ledger. Define it once (Phase 0), then advance every global
through the same four gates (Phases 1–4) so divergence is caught per-global, not all at once.

### Phase 0 — `kind` taxonomy + record-id scheme (no behaviour change)

Introduce a `Kind` string per global and a `record_id` scheme that **reuses the existing identifiers**,
so a ledger row is addressable by the same id the code already holds.

| Global (file:line) | `kind` | `record_id` | Source of id |
|---|---|---|---|
| `_DISTRIBUTED_AUDITS` (`distributed_audits.py:158`) | `"distributed_audit"` | the existing `audit_id` | `_audit_id_for(plan)` (`:481-491`) — already `cas-dist-<digest[:16]>`; reuse verbatim, do **not** call `new_record_id` |
| `_WORKERS` (`fleet_executor.py:159`) | `"worker"` | the existing `worker_id` | `register_worker(worker_id=…)` (`:175`) |
| `_FLEET_RUNS` (`fleet_executor.py:160`) | `"fleet_run"` | the existing `audit_id` (1:1 with its audit) | `prepare_fleet_for_audit(audit_id)` (`:240`) |
| `_FRAGMENT_REFS` (`fleet_executor.py:161`) | `"fragment_ref"` | the fragment ref string itself | `build_evidence_fragment_ref(...)` (`:652-680`) — the `cas-fragment://…/sha256:<digest>` ref *is* its own content-addressed id |

Note that `distributed_audit` and `fleet_run` legitimately share the same `record_id` (the `audit_id`):
that is exactly why the ledger keys on the **(tenant, kind, record_id)** triple
(`memory_store.py:55-57`) — two kinds may reuse one id without collision. The `_audit_id_for` digest is
preserved as-is so existing traceability (the id appears in `plan_id`, `evidence_packet_trace_id`,
fragment refs) is unbroken.

- **Validate:** a pure unit test maps each existing record into a `LedgerRecord.new(...)` and back, with
  zero id churn — every `audit_id`/`worker_id`/fragment-ref round-trips byte-identical. The `payload` is
  the record's **durable intrinsic projection**: for `distributed_audit` that is exactly its `to_dict()`
  (a pure own-data view); for `worker` and `fleet_run` it is a payload *narrower* than `to_dict()` (see
  the refinement immediately below), because their renders fold in clock/foreign-derived view fields that
  must not be stored.
- **Kill:** if any record's intrinsic state cannot serialise into a `Mapping[str, object]` payload without
  loss (e.g. a non-JSON-able field), fix the record shape before any dual-write — a lossy payload would
  make the ledger a downgrade.

**Phase 0 refinement (as implemented) — the ledger stores durable STATE, never the rendered VIEW.** The
Phase-0 payload is *not always* `to_dict()`. A record's `to_dict()` is a *render*: it can fold in state
derived from the clock or from sibling records, recomputed fresh on every read. Persisting that render
would store a stale lie — and, worse, would manufacture **false divergences**, because the same record
re-rendered a few milliseconds later (after a worker ages, or `now` advances) no longer matches the bytes
the ledger holds, even though nothing the record *owns* has changed. So the mirror stores each record's
*intrinsic projection* — the fields the record actually owns — and excludes every recomputed view:

| `kind` | Stored payload (intrinsic state) | Deliberately excluded (recomputed view) | Implemented as |
|---|---|---|---|
| `distributed_audit` | its full `to_dict()` — already a pure own-data projection (plan, the 8 receipts, status, `worker_evidence`, computed counts) | *(nothing — no clock/foreign state in the render)* | mirrored as-is |
| `worker` | `worker_id / model_id / worker_url / gpu_type / capacity / supported_methods / registered_at / last_heartbeat_at` | **`status`** — a pure function of `(last_heartbeat_at, now)`; a worker aging `active→stale` changes *only* this view | `_worker_ledger_payload` |
| `fleet_run` | `audit_id / status / merged_packet_trace_id / created_at / updated_at / jobs[…]` (each job's intrinsic fields, lease token redacted) | **`verifier_gate_status` / `merge_reason` / `readiness` / `stale_workers` / aggregates** — all recomputed from jobs+workers+clock by `_refresh_run_gate` on every read | `_run_ledger_payload` |
| `fragment_ref` | `{audit_id, job_id, worker_id, shard_id}` provenance of the content-addressed ref | *(none)* | `_mirror_fragment` |

This is exactly the projection a Phase-3 reload would have to recompute: a durable backend persists the
intrinsic state and re-derives `status` / gate / readiness from the clock and siblings at read time, just
as `to_dict()` does now. The exclusion is proven *behaviourally*, not by assertion:
`test_worker_going_stale_is_not_a_divergence` ages every worker into `stale` (re-mirroring the durable
`last_heartbeat_at` so only the derived view is free to move) and asserts the shadow ledger still shows
**zero divergence** — the view flipped, the stored state did not.

### Phase 1 — dual-write (write BOTH dict and ledger; reads still from the dict)

Every mutation that currently writes a dict *also* writes the ledger. Reads stay on the dict, so a ledger
bug cannot affect serving. Precise per-global mapping:

- **`_DISTRIBUTED_AUDITS`** — at the write site `_DISTRIBUTED_AUDITS[audit_id] = record` (`:315`), also
  `store.put(LedgerRecord.new(tenant_id=TENANT, kind="distributed_audit", record_id=audit_id,
  payload=record.to_dict(), source="cas_harness_distributed_audits.create_distributed_audit",
  trace_id=audit_id), expected_version=0)`. Subsequent status transitions (`dispatch_distributed_audit`
  `:327-341`, `mark_worker_running` `:344-…`, `merge_distributed_audit` `:469-477`) become a
  read-modify-`put` carrying the version the store last returned.
- **`_WORKERS`** — at `_WORKERS[record.worker_id] = record` (`:208`),
  `store.put(LedgerRecord.new(kind="worker", record_id=worker_id, payload=record.to_dict(), …),
  expected_version=0)`. Heartbeat (`:218-219`) becomes `get` → `with_payload` → `put(expected_version=v)`.
- **`_FLEET_RUNS`** — at `_FLEET_RUNS[audit_id] = record` (`:274`), `put(kind="fleet_run",
  record_id=audit_id, payload=record.to_dict(), parent_ids=(audit_id,)[for the distributed_audit],
  expected_version=0)`. Every gate refresh (`_refresh_run_gate` `:449-471`) and lease transition writes
  the new version back.
- **`_FRAGMENT_REFS`** — the dedup set maps onto the ledger as a presence check. At
  `_FRAGMENT_REFS.add(fragment_ref)` (`:395`), also `put(kind="fragment_ref", record_id=fragment_ref,
  payload={"audit_id":…, "job_id":…, "worker_id":…, "shard_id":…}, source="…submit_job_receipt",
  expected_version=0)`. The replay guard `if fragment_ref in _FRAGMENT_REFS` (`:710-711`) gains a shadow
  `store.get(TENANT, "fragment_ref", fragment_ref) is not None` for comparison (still authoritative on
  the set in Phase 1). A `VersionConflict` on the `expected_version=0` put *is itself* the replay
  signal — two submissions of the same content-addressed ref race to create row version 1, and the
  loser learns the fragment already exists.

  **Lease flow → `acquire_lease`.** The in-line `lease_token`/`lease_token_hash` (`:316-317`) maps onto
  the substrate's lease primitive. In dual-write, alongside minting the in-line token, also
  `lease = store.acquire_lease(TENANT, resource_id=job.job_id, holder=worker_id, ttl_seconds=lease_seconds)`.
  The substrate's opaque `lease.token` (`interface.py:226-240`) is the durable analogue of
  `_lease_token_for` (`:636-643`); `_hash_token` (`:646-649`) stays as the *receipt* proof the worker
  echoes back (`submit_job_receipt` `:356-358`) — the store proves single-holder, the hash proves the
  echoing worker is the holder. Reclaim (`_expire_stale_leases` `:562-569`, `_expire_worker_leases`
  `:572-584`) maps to `release_lease(token)`; TTL expiry maps to `Lease.is_expired` (`interface.py:242-250`)
  rather than the wall-clock `lease_expires_at` compare.
- **Validate (gate):** a shadow-compare harness reads the same record from *both* the dict and the
  ledger after every mutation and asserts equality, over **N ≥ the full distributed-audit test suite +
  a multi-shard soak run**. Gate passes when dict and ledger payloads agree for N consecutive runs with
  zero mismatches.
- **Kill:** if any payload diverges (a field the dict mutates in place but the ledger missed, or a
  version the code failed to thread), stop and fix the write path — never advance reads onto a ledger
  that disagrees with the dict.

### Phase 2 — shadow-read (reads from ledger; dict kept as fallback + compared)

Flip reads to the ledger; keep the dict populated (still dual-writing) as a fallback and a live oracle.

- `get_distributed_audit` (`:319-320`) → `require_tenant(store.get(TENANT, "distributed_audit",
  audit_id), TENANT)`; on a `None` from the store, fall back to the dict **and log the divergence**.
- `list_distributed_audits` (`:323-324`) → `store.list(TENANT, "distributed_audit")`.
- `get_fleet_run` (`:279-283`) / `list_fleet_runs` (`:286-289`) → `store.get` / `store.list` with
  `kind="fleet_run"`; `list_workers` (`:223-224`) → `store.list(TENANT, "worker")`.
- The fragment replay guard (`:710-711`) reads the ledger first; the in-RAM set is the fallback.
- **Validate (gate):** **zero divergence** between ledger-read and dict-fallback over a defined soak
  window (e.g. 24h of CI + staging traffic, or M soak runs). Any fallback hit is a logged defect that
  must reach zero before cutover.
- **Kill:** if divergences persist (ledger read disagrees with the dict oracle), the write path is still
  wrong — return to Phase 1; do not remove the dict.

### Phase 3 — cutover (ledger is source of truth; dict removed from the hot path)

The ledger is authoritative. The dict is no longer read and no longer written on the serving path; it
remains only as dead scaffolding to be deleted in Phase 4.

- **Validate (gate):** **restart-survival** — kill the API process mid-run (a `MERGE_PENDING` audit with
  partial receipts), restart, and confirm the audit, its fleet run, leases (or honest expiry), and the
  `_FRAGMENT_REFS` dedup set are all recovered from the ledger with **zero lost or double-counted
  receipts** (cross-check the merged fragment set is exactly complete, no dupes — the same proof
  workstream 03 Phase D requires). **All three slices now have a built, tested mechanism.** (i) *Storage
  survival*: `test_mirrored_ledger_survives_a_single_host_restart` drives the real flow through
  `SqliteStateStore`, drops the in-RAM dicts, reopens the file, and recovers the full record set from the
  ledger — the *bytes* survive a single-host restart. (ii) *Rehydrate-on-startup*: `rehydrate_from_ledger`
  on both live services reads those surviving rows back into `_DISTRIBUTED_AUDITS` / `_WORKERS` /
  `_FLEET_RUNS` / `_FRAGMENT_REFS`, and the three `test_rehydrate_*` tests prove a restarted process then
  *serves the same records* — byte-identical audit render, byte-identical durable run projection (and a
  re-derived gate that lands where it was), re-derived worker staleness — with **zero lost or
  double-counted** fragment refs, and with the two honest restart consequences made explicit (an in-flight
  lease drops `leased`→`expired` and is then immediately re-leasable; the non-durable fragment-payload
  digest drops while the content-addressed ref survives). (iii) *The flip itself* is now **built and tested,
  shipped dark**: `enable_ledger_reads()` moves read-authority onto the ledger so the public `get_*` /
  `list_*` reconstruct each record's stored state from the durable rows instead of the dicts — proven by
  clearing the dicts and still serving byte-identical state — and it is **reversible**
  (`disable_ledger_reads()` returns to the dicts, which the dual-write keeps current as a write-through
  cache for instant rollback) and **fail-closed** (the `_STATE_MIRROR is not None and read_from_ledger`
  guard means production, which installs no mirror, can never engage it). What the cutover still owes is
  therefore not the mechanism but the **operational enable** — turning it on in a real durable deployment is
  the separate human-gated step the directive pins behind "only after that passes" — plus a **multi-host
  smoke**: two API replicas against one shared (SQLite-single-host first, then Postgres) backend cooperate
  on one run, host A prepares, host B merges. That last half is impossible on `InMemoryStateStore` and needs
  the durable multi-host backend from workstream 11.
- **Kill:** if a resumed run ever double-counts or loses a receipt, the durable-state model is unsafe —
  revert to the dicts (which are honest for single-host) and do not ship the cutover.

### Phase 4 — delete the globals

Remove `_DISTRIBUTED_AUDITS` (`:158`), `_WORKERS`/`_FLEET_RUNS`/`_FRAGMENT_REFS` (`:159-161`), their
`reset_*_for_tests` helpers (`distributed_audits.py:161-162`, `fleet_executor.py:164-172`), and the
shadow-compare scaffolding. Tests reset state by pointing at a fresh `InMemoryStateStore` instead of
clearing a module global.

- **Validate:** full suite green with the dicts physically deleted; a grep for `_DISTRIBUTED_AUDITS` /
  `_WORKERS` / `_FLEET_RUNS` / `_FRAGMENT_REFS` returns only this doc and the changelog.
- **Kill:** any lingering reference means a call site was missed in Phases 1–3 — restore the global and
  finish the migration of that site first.

> Sequencing: Phase 0 is pure-Python and free. Phases 1–2 run against `InMemoryStateStore` (no infra) —
> they prove *behaviour*, not durability. Phase 3 is the first phase that **requires** a durable backend
> (workstream 11's SQLite, then Postgres/Redis) because restart-survival and multi-host are exactly the
> claims `InMemoryStateStore` cannot make (`__init__.py:30-34`). The dicts stay until Phase 3's restart
> proof passes — removing them earlier would trade an honest single-host store for a ledger not yet
> proven durable.

> **Implementation status (Jun 1, 2026).** Phases 0–2 are built and green against `InMemoryStateStore`,
> behind a single dual-write / shadow-read seam, `LedgerMirror`
> (`api/services/production/state_substrate/migration.py`):
> - **Dark by default.** Each live service holds a module-global `_STATE_MIRROR: LedgerMirror | None`,
>   installed only via `set_state_mirror(...)`. Production and every pre-existing test run with it `None`,
>   so the wiring is a **no-op with zero behaviour change** — proven by `test_mirror_is_dark_when_uninstalled`
>   and by the full distributed/fleet suites passing unchanged with the mirror uninstalled.
> - **Non-authoritative.** `mirror_put` never raises into the caller: a backend `StateStoreError` is
>   swallowed and *recorded as a divergence* (a record we failed to mirror IS a place the ledger and the
>   dict disagree); `VersionConflict` retries, then exhaustion is itself a divergence. The dict stays the
>   sole source of truth throughout Phases 1–2.
> - **Dual-write** fires one `_mirror_*(record)` at every creation/mutation site — helpers return the
>   *same* object so callers' in-place mutation is preserved — including the *indirect*, clock-triggered
>   paths `_expire_stale_leases` / `_expire_worker_leases`, which mutate run state outside a run's own
>   mutators and so re-mirror the affected run. **Shadow-read** sits at every `get_*` / `list_*` via
>   `shadow_compare` / `shadow_compare_all`.
> - **One unified ledger, partitioned by `kind`.** Both services share a single `StateStore` under one
>   `INTERIM_TENANT = "default"`; `distributed_audit` and `fleet_run` reuse one `audit_id`, kept distinct
>   by the `(tenant, kind, record_id)` triple.
> - **Not yet wired: the substrate lease primitive.** Phase 1/2 mirror the in-line lease state *inside*
>   the `fleet_run` payload (token redacted); the durable single-holder `acquire_lease` / `release_lease`
>   mapping (§3 Phase 1, §5) stays on the in-process token and is deferred to Phase 3, where cross-host
>   racing is what makes the substrate lease load-bearing.
> - **The Phase-2 gate is met (on `InMemoryStateStore`).** `tests/test_state_substrate_live_migration.py`
>   drives both live services through their real service-layer flow (create→dispatch→register→prepare→
>   lease→submit→merge, plus clock-triggered lease-expiry) and asserts `LedgerMirror.assert_no_divergence()`
>   — **zero divergence**. This proves the *wiring*, not durability.
> - **Single-host restart-survival is now demonstrated (on `SqliteStateStore`).** The same live flow,
>   driven through the durable SQLite backend, then a simulated restart — detach the mirror, **close the DB
>   file, and erase the in-RAM dicts** (the only thing a process restart loses) — and reopen a fresh store
>   on the same file: the audit, its fleet run (every job), every worker, and every fragment ref are **all
>   recovered from the ledger**, while the dicts come back empty
>   (`test_mirrored_ledger_survives_a_single_host_restart`). The real mirrored payloads also serialise and
>   round-trip through SQLite (a stricter check than the in-memory store's). This is the durability
>   *evidence* Phase 3's single-host half needs, on the one backend whose own tests earn "durable on a
>   single host" — it is **not** the cutover (the dicts are still authoritative on the serving path) and
>   **not** multi-host (that is workstream 11).
> - **Rehydrate-on-startup is now implemented and proven (the read inverse of the dual-write).**
>   `rehydrate_from_ledger(store)` on both live services rebuilds the four in-RAM containers from the
>   durable ledger. The distributed-audit service reconstructs each `DistributedAuditRecord` — plan via
>   `ScalePlan.from_dict`, the *mutated* `worker_evidence` rows via `WorkerEvidenceRecord.from_dict`, and
>   the 7 immutable, only-rendered summaries as faithful `to_dict()` re-servers (a stored dict re-served
>   byte-identically, which is both more faithful and less code than field-by-field reconstruction). The
>   fleet service rebuilds workers, runs, and the fragment-ref dedup set, then re-derives each run's gate
>   via `_refresh_run_gate` **after** workers are back (the order is load-bearing — the gate reads
>   `_WORKERS`). Unlike the non-authoritative mirror it **fails loud**: a `StateStoreError` propagates
>   (a half-restored service must not look authoritative) and it builds into fresh containers swapped in
>   only once every row rebuilds, so a malformed row cannot leave a service half-populated. Two honest
>   restart consequences are baked in and tested: a `leased` job rehydrates `expired` (the lease token is
>   a secret capability never written to the ledger) yet is immediately re-leasable, and the
>   fragment-payload `sha256` rehydrates null (the raw payload lives in the WORM store, not the run
>   ledger) while its durable content-addressed ref survives. Proven by the three `test_rehydrate_*` tests
>   in `tests/test_state_substrate_live_migration.py`, which snapshot what the services serve, simulate a
>   restart (close the SQLite file + erase the dicts), rehydrate from a freshly reopened store, **close it
>   before asserting** (proving rehydrate is a full copy into RAM, not a lazy handle), and assert the
>   served records match. This is the cutover **prerequisite** the directive names, **not** the cutover:
>   the dicts remain authoritative on the serving path until the separately gated read-authority flip.
> - **The read-authority flip itself is now built and proven, shipped dark (Phase 3's third slice).**
>   `LedgerMirror` carries a `read_from_ledger` switch (default `False`); `enable_ledger_reads()` /
>   `disable_ledger_reads()` toggle it. While off, every `get_*` / `list_*` serves the dict and
>   shadow-compares (Phase 2). While on, they reconstruct each record's *stored* state from the ledger via
>   `read_payload` / `read_all_payloads` (the same `_*_from_ledger_payload` reconstructions rehydrate uses),
>   re-deriving the excluded *views* on read — worker staleness from the heartbeat, and the run's verifier
>   gate via `_refresh_run_gate` against the worker cache, which is a derived view in **both** modes, so the
>   flip moves authority for *stored state*, not the ACCEPT-gating logic. Three properties make it safe to
>   ship dark: (a) **fail-closed** — the read sites gate on `_STATE_MIRROR is not None and
>   _STATE_MIRROR.read_from_ledger`, so production (no mirror) is structurally pinned to the dicts and
>   cannot enable the ledger by accident; (b) **reversible** — the dual-write now also writes the dict back
>   (a write-through cache), so under ledger-reads a mutate-then-mirror keeps the dict current and
>   `disable_ledger_reads()` is an instant, lossless rollback; (c) **authoritative reads fail loud** —
>   `read_payload` / `read_all_payloads` propagate `StateStoreError` (when the ledger IS the truth, an
>   unreachable ledger must fail the request, not fabricate an answer — the opposite of the swallow-and-record
>   shadow path). Proven by the three new cutover tests in `tests/test_state_substrate_live_migration.py`:
>   clearing each backing dict and still serving byte-identical state from the ledger; the switch reversible
>   and dark by default (an installed-but-disabled mirror still serves the dict, not the ledger); and the
>   write-through keeping the dict current so rollback loses nothing. This is the **mechanism**, dark by
>   default — the operational enable in a durable deployment, and Phase 4 (deleting the dicts), remain
>   separate human-gated steps; multi-host durability is still workstream 11.

---

## 4. Honesty constraints (non-negotiable)

**Moving state does NOT move who may mint a verified status.** This is the single most important
invariant. The migration relocates *where bytes live*; it must not relocate the declared-vs-verified
authority. Concretely:

- The merge gate keeps its semantics exactly. `merge_fleet_evidence` still refuses to merge until every
  receipt is in and still lands only `ready_for_verifier` — "fleet executor does not fabricate ACCEPT"
  (`cas_harness_fleet_executor.py:441-444`) — whether the `FleetRunRecord` it reads came from a dict or
  from `store.get`. `merge_distributed_audit` still returns only `FLAG_FOR_HUMAN_REVIEW`
  (`cas_harness_distributed_audits.py:469-477`). The storage layer is *underneath* the gate; it cannot
  reach up and change the verdict.
- The content-addressed fragment ref keeps its meaning. `build_evidence_fragment_ref` (`:652-680`)
  still hashes the same canonical payload to the same `sha256:<digest>` ref; the ledger stores that ref
  as a `record_id`, it does not *re-derive* or *bless* it. The dedup guarantee moves from "is it in the
  set" (`:710-711`) to "does a `fragment_ref` row exist / did the `expected_version=0` put conflict" —
  **identical semantics, different storage**. The substrate never computes a fragment ref; only the
  worker-fed builder does.
- The substrate is explicitly *behavioural, not durable-by-default* — "Do not read 'implements
  StateStore' as 'durable'" (`interface.py:33-37`). A deployment may claim exactly the durability its
  chosen backend's tests earn (`__init__.py:36-38`). The migration must not let "we moved to the ledger"
  be read as "we are now durable"; durability arrives only with the workstream-11 backend whose tests
  prove close/reopen survival.

**The tenant-claim gap — the KNOWN interim (read this twice).** There is **no honest source of a
`tenant_id` today**: the JWT carries `sub` + `api_key` only and `create_token` mints no tenant claim
(`auth.py:91`); rate limits are per-`api_key` (`rate_limit.py:87`). Until workstream **06** adds a real
tenant claim, this migration threads a **single literal `tenant_id = "default"`** into every `store.put`
/ `store.get` / `store.list` / `acquire_lease` call. This is a deliberate, documented interim — **not
real multi-tenancy**. Using `"default"` everywhere means today's deployment is *single-tenant*, exactly
as honest as the current tenant-blind dicts, **no more**. What it buys is that the **seam is
tenant-scoped from day one**: every call site already passes a `tenant_id` argument, so when 06 lands a
real claim the change is a **one-line source edit** (`"default"` → `request.state.tenant_id`), not a
re-architecture of every read and write. Claiming the product is multi-tenant on the strength of this
migration alone would be the precise dishonesty (`__init__.py:36-38`) this program exists to refuse:
the `tenant_id` parameter being *present* is a seam, not a *boundary* — the boundary is real only once a
verified claim populates it. This caveat must appear in any status that touches tenancy until 06 closes
it.

**Optimistic concurrency is a correctness guard, not an optimisation.** Where two API hosts could race
on one `fleet_run` (Phase 3+), `expected_version` MUST be threaded through every `put` (`interface.py:297`),
and a `VersionConflict` (`interface.py:95-111`) MUST trigger re-read-re-decide, never a blind retry —
the honest response to "the state changed underneath me" is to re-decide on fresh state, because the
lease/gate decision was based on stale data.

---

## 5. Interfaces / seams

The `StateStore` Protocol methods each call site binds to (`interface.py:297-330`):

| Current call (file:line) | `StateStore` method |
|---|---|
| `_DISTRIBUTED_AUDITS[audit_id] = record` (`distributed_audits.py:315`) | `put(record, expected_version=0)` then RMW `put(expected_version=v)` |
| `get_distributed_audit(audit_id)` (`:319`) | `get(tenant_id, "distributed_audit", audit_id)` |
| `list_distributed_audits()` (`:323`) | `list(tenant_id, "distributed_audit")` |
| `_WORKERS[worker_id] = record` (`fleet_executor.py:208`) | `put(... kind="worker" ...)` |
| `heartbeat_worker` mutation (`:218-219`) | `get` → `with_payload` → `put(expected_version=v)` |
| `list_workers()` (`:223`) | `list(tenant_id, "worker")` |
| `_FLEET_RUNS[audit_id] = record` (`:274`) | `put(... kind="fleet_run" ...)` |
| `get_fleet_run` / `list_fleet_runs` (`:279`, `:286`) | `get` / `list` `kind="fleet_run"` |
| lease mint `_lease_token_for` (`:316`, `:636-643`) | `acquire_lease(tenant_id, job.job_id, holder=worker_id, ttl_seconds=…)` |
| lease reclaim (`_expire_stale_leases` `:562`, `_expire_worker_leases` `:572`) | `release_lease(token)` |
| lease TTL compare (`lease_expires_at` `:318`, `:565`) | `Lease.is_expired(now=…)` (`interface.py:242`) / `renew_lease` |
| `_FRAGMENT_REFS.add(ref)` (`:395`) | `put(... kind="fragment_ref", record_id=ref ..., expected_version=0)` |
| `if ref in _FRAGMENT_REFS` (`:710`) | `get(tenant_id, "fragment_ref", ref) is not None` |

**Lease-token ↔ `acquire_lease` mapping, precisely.** The executor today carries two values per leased
job: a `lease_token` the worker echoes back as proof of holding the lease, and a `lease_token_hash` it
verifies against (`:356-358`). The substrate's `acquire_lease` returns one opaque `token`
(`interface.py:226-240`) that *is* the single-holder claim — only its holder can `renew_lease` /
`release_lease`. The clean mapping: the substrate `token` replaces `_lease_token_for` as the durable
who-holds-it record; the existing `_hash_token` echo-proof (`:646-649`) is retained at the receipt
boundary so the worker still proves it is the holder without the API tier handing the raw token around.
`LeaseHeld` (`interface.py:124-134`) is the cross-host analogue of "this job is already leased"; today
that case simply doesn't arise because there is one process.

**Possible missing helper (PROPOSAL ONLY — do not implement).** The fragment-ref dedup wants an
**atomic "create-if-absent"** that returns "already existed" without an exception in the hot path. Today
this can be expressed as `put(expected_version=0)` and catching `VersionConflict` — which works, but
makes the *normal* replay path an exception. A thin `put_if_absent(record) -> bool` (True = created,
False = already present) on the `StateStore` Protocol would map the `_FRAGMENT_REFS` guard (`:710-711`)
more directly and keep replay off the exception path. This is a *proposed* addition to
`interface.py`/`memory_store.py`/`conformance.py`; it is **not required** for the migration (the
`VersionConflict` route is sufficient) and must not be built as part of this workstream — flagged here
for the substrate owners to weigh.

---

## 6. Cross-references

This migration is the foundation the rest of the program's stateful workstreams sit on. It produces no
customer-visible feature itself; it makes the others *possible*.

- **03 (fleet execution at scale) — unblocked.** 03 §7 names its biggest open question as "Where does
  shared run/worker/lease state live?" and its Phase D explicitly needs
  `_WORKERS`/`_FLEET_RUNS`/`_DISTRIBUTED_AUDITS` to "become durable and fleet-visible"
  (`03_fleet_execution_at_scale.md:351-354`, `:157-169`). This workstream *is* that answer: once the
  ledger is the source of truth (Phase 3), a replacement orchestrator resumes a run from durable state,
  and a scheduler on host B sees host A's workers via `store.list(tenant, "worker")`.
- **04 (queue / resume) — shares the substrate.** 04's durable job queue and this control-plane ledger
  are the same durability story from two angles; the `acquire_lease` primitive here is the idempotent
  leasing 04 relies on, and the restart-survival proof (Phase 3) is 04's checkpoint/resume in
  microcosm. They consume the same workstream-11 backend.
- **05 (observability) — gains a durable record to observe.** Every `LedgerRecord` carries the
  traceability envelope `parent_ids` / `source` / `trace_id` (`interface.py:171-174`); 05's run
  dashboards and traceability surfaces read a persistent ledger instead of a volatile dict, so a run's
  history survives the process that created it.
- **06 (tenant isolation) — lands on the prepared seam.** This is the reciprocal dependency: 06 supplies
  the real `tenant_id` claim the JWT lacks today (`auth.py:91`), and this migration supplies the
  tenant-scoped storage seam 06 partitions on (`interface.py:19-22`). The `"default"` interim (§4) is
  the explicit handoff point — 06 flips it from a literal to a real claim.
- **08 (billing / accounts) — meters off durable consumption.** Which worker ran which shard for how
  long is the `COST_METERED` input; once the fleet run + lease timestamps are durable, a metering pass
  can read them after the fact rather than racing the process that holds them in RAM.
- **09 (compliance) — audits a durable trail.** Consent → capture → WORM retention needs an audit trail
  that outlives the request; the ledger's versioned, timestamped, tenant-scoped records are that trail.
- **Consumes:** the `state_substrate` package (`StateStore` + `InMemoryStateStore` reference +
  `run_state_store_contract`, `__init__.py:49-92`) now, and the forthcoming **SQLite** (durable
  single-host) and **Postgres/Redis** (multi-host) backends from **workstream 11** at Phase 3 — the same
  interface, a backend whose tests earn the durability claim (`__init__.py:30-34`).

---

## 7. Open questions

1. **Retention of completed-audit records vs unbounded growth.** The dicts are implicitly bounded by
   process lifetime — a restart "garbage-collects" everything. A durable ledger does not: every
   `distributed_audit` / `fleet_run` accumulates forever unless a retention policy prunes
   `COMPLETE`/`FAILED` runs. What is the TTL, and does pruning conflict with **09**'s retention/audit-
   trail requirements (a completed audit may be exactly what compliance must keep)? Decision needed
   before Phase 3 makes growth real.
2. **Do fragment refs belong in the ledger at all, or only their content-addresses?** `_FRAGMENT_REFS`
   is a *set of strings*, not rich records. Storing each as a `fragment_ref` `LedgerRecord` (§3) is the
   clean mapping, but a 512-shard run mints up to 512 such rows per audit. Alternative: keep only the
   content-address (the `sha256:<digest>` from `build_evidence_fragment_ref` `:680`) in a compact
   per-run index. Trade-off: full rows give traceability (which job/worker produced the fragment); a
   bare digest set is leaner but loses provenance. Leaning toward full rows, since object traceability
   is load-bearing in this codebase — but flagged.
3. **Lease TTL tuning vs the existing heartbeat staleness cutoff.** Two timeouts will coexist: the
   substrate lease `ttl_seconds` (`interface.py:309-317`) and the executor's
   `DEFAULT_MAX_HEARTBEAT_AGE_SECONDS = 120` (`fleet_executor.py:38`) / job `lease_seconds = 900`
   (`:296`). They must not fight — a lease that outlives worker staleness lets a dead worker hold a job;
   a lease shorter than the heartbeat window thrashes. What is the right relationship (lease TTL ≈ a
   small multiple of the heartbeat cutoff?), and is it tuned per workstream 03's suspect→lost model?
4. **Where does the `StateStore` instance live, and who owns its lifecycle?** The migration assumes a
   process-wide store handle the call sites reach. Is it a module singleton, a FastAPI dependency, or
   app-state? `close()` (`interface.py:329`) is idempotent, but the choice affects testability (Phase 4
   wants tests to inject a fresh `InMemoryStateStore`) and the multi-host backend's connection pooling.
5. **When does the `"default"` tenant interim actually end?** Strictly a 06 dependency, but worth a hard
   gate: no status that asserts or implies multi-tenancy may ship while `"default"` is threaded
   everywhere (§4). Who owns confirming the literal is gone — a grep gate in CI, or a 06 acceptance
   criterion?
