# 13 — Phase-4 Dict Deletion PLAN (analysis only — deletes nothing)

> **THIS PLAN DELETES NOTHING.** It is analysis. Deletion of the four process-global dicts is **HELD**
> until the full rollout sequence (workstream 12) is deployed *and proven* in a real durable deployment:
> the mirror enabled, **zero divergence earned on real traffic**, read-authority flipped **and soaked**,
> the multi-host Postgres backend **verified against a live server**, and a **tested rollback path** in
> place. Phase 4 is the one **irreversible** step in the entire migration — it removes the hot
> write-through cache that makes every prior step instantly rollback-able — so it does not begin on the
> strength of this document. This plan **maps the work**; it does not authorize it.

**Workstream:** 13 (the Phase-4 half of workstream 10) · **Status:** PLAN ONLY — no code touched, no dict
removed · **Date:** Jun 2, 2026
**Owner seam:** the eventual, gated removal of `_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`,
`_FRAGMENT_REFS` once the durable `StateStore` ledger is the sole, proven source of truth.

> Read [`10_state_substrate_migration.md`](./10_state_substrate_migration.md) §3 Phase 4 and
> [`12_operational_rollout_runbook.md`](./12_operational_rollout_runbook.md) first. Doc 10 names Phase 4 as
> the final migration phase; doc 12 is the gated turn-on that must *complete and soak* before Phase 4 is
> even considered. This doc is the detailed deletion map that sits behind doc 12's step 5.

---

## (a) The four dicts and EVERY site that touches each

The control-plane state lives in four process-global containers across two service modules. Below, every
read / write / rehydrate / reset site, cited by file + symbol. (Line numbers are as of Jun 2, 2026 and
will drift; the symbols are the durable anchors.)

### A.1 `_DISTRIBUTED_AUDITS: dict[str, DistributedAuditRecord]`
`api/services/cas_harness_distributed_audits.py:181`

| Site (symbol) | Kind | What it does |
|---|---|---|
| `create_distributed_audit` → `_DISTRIBUTED_AUDITS[audit_id] = record` (`:486`) | **write** | mints + stores the audit, then `_mirror_audit` dual-writes the ledger |
| `_mirror_audit` (`:213-?`, writes dict + `mirror_put`) | **write/mirror** | dual-write helper; gated on `_STATE_MIRROR is not None` |
| `_shadow_audit` (`:225-226`, `shadow_compare`) | **shadow-read** | compares dict payload against ledger on single reads |
| `get_distributed_audit` (`:490-499`) | **read** | **gated**: `read_from_ledger` → `read_payload`; else dict + shadow-compare |
| `list_distributed_audits` (`:502-511`) | **read** | **gated**: `read_from_ledger` → `read_all_payloads`; else dict + `shadow_compare_all` |
| status transitions (`dispatch_distributed_audit` `:514+`, `mark_worker_running`, `merge_distributed_audit`, `record_worker_evidence`) | **read-modify-write** | all route their read through `get_distributed_audit` and re-mirror on mutate |
| `rehydrate_from_ledger` (`:312-333`) | **rehydrate** | rebuilds the dict from the ledger on startup; `clear()` + `update()` |
| `reset_distributed_audits_for_tests` (`:230-231`, `_DISTRIBUTED_AUDITS.clear()`) | **test reset** | clears the dict between tests |
| `set_state_mirror` (`:195-198`) | **install** | sets/clears `_STATE_MIRROR` (shared with the fleet service via the bootstrap) |

### A.2 `_WORKERS: dict[str, FleetWorkerRecord]`
`api/services/cas_harness_fleet_executor.py:159`

| Site (symbol) | Kind | What it does |
|---|---|---|
| `register_worker` → `_WORKERS[worker_id] = record` (`:446+`) | **write** | registers a worker, refuses duplicate id, dual-writes via `_mirror_worker` |
| `heartbeat_worker` (`:483-491`) | **read-modify-write** | mutates `last_heartbeat_at` / `status` in place, re-mirrors |
| `list_workers` (`:494-507`) | **read** | **gated**: `read_from_ledger` → `read_all_payloads` + re-derive staleness; else dict + `shadow_compare_all` |
| `mark_stale_workers` (`:510-520`) | **read-modify-write** | ages workers via `_mark_stale_worker_if_expired` over the dict's values |
| `_mark_stale_worker_if_expired` (`:?`) | **derive** | recomputes `status` from `(last_heartbeat_at, now)` — a **view**, not stored state |
| `rehydrate_from_ledger` (`:396-443`) | **rehydrate** | rebuilds `_WORKERS` first (order is load-bearing — the gate reads it) |
| `reset_fleet_executor_for_tests` (`:301-304`, `_WORKERS.clear()`) | **test reset** | clears the dict |

### A.3 `_FLEET_RUNS: dict[str, FleetRunRecord]`
`api/services/cas_harness_fleet_executor.py:160`

| Site (symbol) | Kind | What it does |
|---|---|---|
| `prepare_fleet_for_audit` → `_FLEET_RUNS[audit_id] = record` (`:557`) | **write** | builds the run + jobs, `_refresh_run_gate`, then `_mirror_run` |
| `lease_next_job` / `submit_job_receipt` | **read-modify-write** | mint/verify lease tokens in-line on `run.jobs`, re-mirror the run |
| `_expire_stale_leases` / `_expire_worker_leases` | **read-modify-write (indirect)** | reclaim leases by nulling token fields; re-mirror the affected run |
| `_refresh_run_gate` (`:?`) | **derive** | recomputes `verifier_gate_status` / readiness / aggregates from jobs + `_WORKERS` + clock — a **view**, run in **both** read modes |
| `get_fleet_run` (`:562-579`) | **read** | **gated**: `read_from_ledger` → `read_payload` + `_refresh_run_gate`; else dict + `_refresh_run_gate` + `_shadow_run` |
| `list_fleet_runs` (`:582-596`) | **read** | **gated**: `read_from_ledger` → `read_all_payloads` + `_refresh_run_gate`; else dict + `_refresh_run_gate` + `shadow_compare_all` |
| `merge_fleet_evidence` | **read-modify-write** | reads the run, refuses to merge until every receipt is in, lands only `ready_for_verifier` |
| `_mirror_run` (`:?`, dict write + `mirror_put`) / `_shadow_run` (`:295-298`) | **write/shadow** | dual-write and shadow-compare helpers |
| `rehydrate_from_ledger` (`:396-443`) | **rehydrate** | rebuilds `_FLEET_RUNS` after workers, then re-derives every run's gate |
| `reset_fleet_executor_for_tests` (`:301-304`, `_FLEET_RUNS.clear()`) | **test reset** | clears the dict |

### A.4 `_FRAGMENT_REFS: set[str]` — the dedup guard (special case)
`api/services/cas_harness_fleet_executor.py:161`

| Site (symbol) | Kind | What it does |
|---|---|---|
| `submit_job_receipt` → `_FRAGMENT_REFS.add(...)` (`:703`) | **write** | records a submitted fragment, then `_mirror_fragment` dual-writes |
| `_mirror_fragment` (`:286-292`, `.add()` + `mirror_put`) | **write/mirror** | dual-write helper; gated on `_STATE_MIRROR is not None` |
| **`_validate_fragment_ref` → `if fragment_ref in _FRAGMENT_REFS` (`:1027`)** | **read — NOT gated on `read_from_ledger`** | the replay guard reads the **in-RAM set unconditionally**, in *every* posture |
| `rehydrate_from_ledger` (`:427,433-434`) | **rehydrate** | rebuilds the set from `fragment_ref` rows on startup |
| `reset_fleet_executor_for_tests` (`:304`, `_FRAGMENT_REFS.clear()`) | **test reset** | clears the set |

> **The `_FRAGMENT_REFS` asymmetry is the single most important finding in this plan.** Unlike the other
> three dicts — whose `get_*` / `list_*` reads are *gated* on `read_from_ledger` and therefore stop
> consulting the dict once read-authority flips — the fragment **replay guard** at
> `_validate_fragment_ref` (`fleet_executor.py:1027`) reads `_FRAGMENT_REFS` with **no `read_from_ledger`
> gate at all.** It is kept correct under read-authority only because the dual-write *and* rehydrate keep
> the in-RAM set current. **So `_FRAGMENT_REFS` is a LIVE read even in `enabled_ledger_read_authoritative`
> posture** — it does not become read-redundant the way the other three do. This is the dict whose
> deletion requires actual code change *before* it is safe (re-point the guard at the ledger), not merely
> the read-authority flip.

---

## (b) What becomes DEAD vs what is STILL NEEDED once the ledger is read-authoritative

Read-authority (`read_from_ledger == True`) changes what the *gated* read sites consult. It does **not**
make everything dict-shaped dead. Classify carefully:

### B.1 DEAD once read-authoritative AND Phase 4 lands (safe to delete)
- **The dict *containers themselves* as a read source for the three gated kinds.** Under
  `read_from_ledger`, `get_distributed_audit` / `list_distributed_audits` / `list_workers` /
  `get_fleet_run` / `list_fleet_runs` all reconstruct from the ledger and **never read the dict**
  (`distributed_audits.py:495-497,503-505`; `fleet_executor.py:498-501,568-574,583-588`). The dict-branch
  of each of those reads is dead under read-authority.
- **The shadow-compare scaffolding** — `_shadow_audit` / `_shadow_run` and the `shadow_compare` /
  `shadow_compare_all` calls on the read path (`distributed_audits.py:225-226,507-510`;
  `fleet_executor.py:295-298,503-506,592-595`). Shadow-compare exists to *earn the cutover evidence*; once
  the ledger is authoritative and soaked, comparing it against a cache it write-throughs to is redundant.
- **The `reset_*_for_tests` helpers** (`distributed_audits.py:230-231`; `fleet_executor.py:301-304`) —
  once tests reset state by pointing at a fresh `InMemoryStateStore` instead of clearing a module global
  (doc 10 §3 Phase 4).

### B.2 STILL NEEDED after the read flip (must NOT be deleted as "dict code")
- **`_refresh_run_gate` — derived view, recomputed in BOTH modes.** The verifier gate / readiness /
  aggregates are *not* stored in the ledger payload (doc 10 §3 Phase 0 refinement table); they are
  re-derived on every read from jobs + workers + clock. `get_fleet_run` / `list_fleet_runs` call
  `_refresh_run_gate` **after** reconstructing from the ledger (`fleet_executor.py:572-574,586-588`), and
  `rehydrate_from_ledger` re-derives it after workers load (`:436-437`). **This is the ACCEPT-gating logic
  the honesty spine depends on; the read flip moves authority for *stored state*, not for the gate.** It
  survives Phase 4 untouched.
- **Worker staleness derivation** (`_mark_stale_worker_if_expired`, and the cutoff re-derivation in
  `list_workers` / `rehydrate`, `fleet_executor.py:498-501,415-419`). `status` is a pure function of
  `(last_heartbeat_at, now)` and is **never stored** (doc 10 §3 Phase 0 refinement). Recomputed in both
  modes; survives Phase 4.
- **The `_FRAGMENT_REFS` replay-guard READ (`_validate_fragment_ref:1027`).** As established in (a), this
  is ungated and live in every posture. It cannot be deleted with the set unless the guard is first
  re-pointed at a ledger existence check (`store.get(tenant, "fragment_ref", ref) is not None`, or a
  `put_if_absent` per doc 10 §5's proposal). **Deleting the set without re-pointing the guard removes the
  replay protection entirely** — a correctness failure, not just a loss.
- **`rehydrate_from_ledger` (both services).** As long as the dicts exist as the hot write-through cache
  (which they do through step 4 and any Phase-4 transition), rehydrate is what repopulates them on restart.
  It is only removable in lockstep with the dicts themselves — and only after the read path no longer
  depends on a warm cache (see (e)).
- **The dual-write / write-through itself** (`_mirror_audit` / `_mirror_worker` / `_mirror_run` /
  `_mirror_fragment`). Under read-authority this is what keeps the dicts current for **instant rollback**
  (doc 12 step 4). It is *not* dead while rollback-to-dict is the safety net; it becomes dead only when
  Phase 4 deliberately gives up that net (see (e)).
- **`set_state_mirror` and the `_STATE_MIRROR` install seam.** The bootstrap installs/uninstalls the mirror
  through these; they are the lifecycle, not dict code.

---

## (c) Preconditions — ALL must hold before ANY deletion is safe

Deletion may begin only when **every** one of these is true (this is the directive's "only after all the
above" gate, made concrete):

1. **Enable deployed.** `NC_STATE_LEDGER_ENABLED=true` is live in the real durable deployment, install
   succeeded (fail-loud, no silent degrade), posture log-line `ENABLED, …` confirmed (doc 12 step 1).
2. **Zero-divergence earned on REAL traffic.** `divergences_found == 0` over a large, representative
   `reads_compared` across all four kinds and the full lifecycle, including the clock-triggered staleness /
   lease-expiry paths (doc 12 step 2). Not a clean start — earned soak evidence.
3. **Read-authority flipped AND soaked.** `NC_STATE_LEDGER_READ_AUTHORITY=true`, posture
   `enabled_ledger_read_authoritative`, run for a **stated soak period** (define it up front — e.g. ≥ N
   days of representative traffic) with divergences pinned at zero the entire time (doc 12 step 4).
4. **Live multi-host Postgres verified.** The `NC_TEST_POSTGRES_URL` conformance + close/reopen-durability
   + fencing suite green against a **real** server (not skipped, not SQLite, not in-memory), and — for a
   multi-host deployment — the two-replica cooperation smoke passed (doc 12 step 3;
   `11_multi_host_state.md` §0). A single instance earns "survives restart"; "survives host loss" needs
   synchronous replication + failover routing (`11_multi_host_state.md` §6) — claim only what the config
   earns.
5. **A tested rollback path that does NOT depend on the dicts.** Before deletion, there must be a proven
   way to recover read-authority trouble **without** falling back to the in-RAM cache — because Phase 4
   removes that cache. See (e): this is the precondition most likely to be missing.
6. **The `_FRAGMENT_REFS` replay guard re-pointed at the ledger (and tested).** Because the guard
   (`fleet_executor.py:1027`) is ungated, the dedup set cannot be deleted until the guard reads the ledger
   instead, with a test proving a replayed fragment is still rejected from durable state.

> If any single precondition is not met, Phase 4 does not start. A partially-met set is not a
> "mostly-safe" deletion; it is an unsafe one.

---

## (d) Safe deletion ORDER, and how each step would be tested

Delete in dependency order — least-coupled scaffolding first, the load-bearing cache last — so the suite
stays green at every step and any miss is caught before the irreversible removal. **Each step is its own
commit with its own green suite; never batch.**

1. **Remove the read-path shadow-compare scaffolding** (`_shadow_audit`, `_shadow_run`, and the
   `shadow_compare` / `shadow_compare_all` calls inside the gated reads). *Test:* full distributed/fleet
   suites green; the read sites now have only the ledger branch + the (still-present) dict branch.
   *Rollback:* trivial — re-add the calls (still pre-deletion of the dicts).
2. **Re-point the `_FRAGMENT_REFS` replay guard at the ledger** (`_validate_fragment_ref` reads
   `store.get(tenant, "fragment_ref", ref) is not None`, or adopt `put_if_absent` per doc 10 §5). *Test:* a
   replay test that submits a duplicate fragment and asserts rejection **with the in-RAM set already
   cleared** — proving the guard now enforces dedup from durable state alone. This is the precondition-6
   work; it must land and soak before step 5 below.
3. **Collapse the gated reads to ledger-only** (remove the `if _STATE_MIRROR … read_from_ledger` branch and
   the dict-read fallback from `get_distributed_audit` / `list_distributed_audits` / `list_workers` /
   `get_fleet_run` / `list_fleet_runs`), keeping `_refresh_run_gate` and the staleness derivation intact.
   *Test:* suites green against a backend (tests inject a fresh `InMemoryStateStore`); a read with no dict
   populated still returns correct, gate-derived records.
4. **Remove the write-through-to-dict from the dual-write helpers** (`_mirror_*` stop `.add()`-ing /
   assigning the dict, keep `mirror_put`). *Test:* mutate → read round-trips entirely through the store;
   restart-survival test still passes via rehydrate-into-ledger-backed reads. **Note: this is the step that
   gives up instant dict-rollback — do not take it until (e)'s replacement is in place.**
5. **Delete the dicts, `rehydrate_from_ledger`, and the `reset_*_for_tests` helpers.** Tests reset by
   pointing at a fresh `InMemoryStateStore` (doc 10 §3 Phase 4). *Test (the doc-10 gate):* full suite green
   with the dicts **physically deleted**; a repo grep for `_DISTRIBUTED_AUDITS` / `_WORKERS` /
   `_FLEET_RUNS` / `_FRAGMENT_REFS` returns **only** docs + changelog (doc 10 §3 Phase 4 validate). Any
   lingering reference = a call site missed in steps 1-4; restore and finish that site first (doc 10 Phase
   4 kill).

> Steps 1-3 are reversible by ordinary revert and touch no durability guarantee. Steps 4-5 are the
> irreversible core and must each soak before the next.

---

## (e) The IRREVERSIBILITY risk — what is lost, and what must replace it first

**Deleting the dicts removes the instant-rollback hot cache. This is the defining risk of Phase 4 and the
reason it is held.**

Through doc 12 steps 1-4, the dicts are a **write-through cache kept byte-current by the dual-write**
(`migration.py` docstring §"reversible"; doc 10 implementation-status note). That is precisely what makes
read-authority **reversible**: `disable_ledger_reads()` (`migration.py:312-315`) — or unsetting the flag
and restarting — returns reads to the dicts **instantly and losslessly**, because the cache never went
stale. Rollback from a bad cutover is, today, a single switch.

**Phase 4 deliberately destroys that affordance.** Once the dicts are gone:

- **There is no warm in-RAM fallback.** A read that the ledger cannot serve (backend unreachable, a latent
  reconstruction bug, a bad migration of a payload shape) can no longer be answered by a current dict — it
  **fails the request** (authoritative reads propagate `StateStoreError` by design,
  `migration.py:317-338`). That is *honest*, but it converts "instant flip back to the cache" into "the
  read is down until the backend is fixed."
- **Rollback stops being a switch and becomes a restore.** Recovering now means fixing the durable backend
  (or failing over to a replica), not toggling `read_from_ledger`. The mean-time-to-recover for a
  read-authority fault goes from seconds to however long backend recovery takes.
- **The replay guard loses its in-RAM source** unless precondition 6 / step (d).2 already re-pointed it at
  the ledger. Deleting `_FRAGMENT_REFS` without that re-point removes dedup protection outright.

**What must replace the cache before deletion is safe:**

1. **A verified, host-loss-survivable durable backend** — live multi-host Postgres with synchronous
   commit + synchronous replication + failover routing (precondition 4; `11_multi_host_state.md` §3.4,
   §6). The cache was the thing covering "the backend blinked"; remove the cache only when the backend's
   own HA covers it.
2. **A tested non-dict rollback / recovery runbook** (precondition 5) — explicit, exercised steps for a
   read-authority fault that rely on backend failover and (if needed) restore-from-backup, **not** on the
   in-RAM cache. Proven before deletion, not improvised after.
3. **The replay guard already on the ledger** (precondition 6 / step (d).2), soaked, so deleting the set
   removes nothing load-bearing.
4. **The fencing-token protection live end-to-end** for any resource a stalled multi-host holder could
   double-write (`11_multi_host_state.md` §5.2) — once the dict-cache no longer provides a single-process
   backstop, the multi-host correctness story rests entirely on the store + fencing.

> **The honest one-liner:** the dicts are cheap insurance with an instant payout. Phase 4 cancels the
> policy. Do not cancel it until the durable backend's own HA, a tested non-dict recovery path, the
> ledger-backed replay guard, and end-to-end fencing have *demonstrably* taken over the risks the cache was
> silently absorbing. Until then, this plan stays a plan.

---

## Cross-references

- **[`10_state_substrate_migration.md`](./10_state_substrate_migration.md)** §3 Phase 4 — the deletion
  phase this doc details; §3 Phase 0 refinement — why gate / staleness are derived views (not stored),
  which is why they survive deletion; §5 — the `put_if_absent` proposal relevant to re-pointing the
  fragment guard.
- **[`12_operational_rollout_runbook.md`](./12_operational_rollout_runbook.md)** — the gated turn-on whose
  completion + soak is the precondition set (c) for this plan; step 5 points here.
- **[`11_multi_host_state.md`](./11_multi_host_state.md)** §0, §3.4, §5.2, §6 — the live-server
  verification (precondition 4), the durability/HA config that must replace the cache (e), and the fencing
  the post-cache correctness story rests on.
- **`api/services/cas_harness_distributed_audits.py`** — `_DISTRIBUTED_AUDITS` and its read/write/rehydrate
  sites (A.1).
- **`api/services/cas_harness_fleet_executor.py`** — `_WORKERS` / `_FLEET_RUNS` / `_FRAGMENT_REFS`, the
  ungated replay guard at `_validate_fragment_ref`, `_refresh_run_gate`, and both rehydrate paths (A.2-A.4).
- **`api/services/production/state_substrate/migration.py`** — `read_from_ledger` /
  `enable_ledger_reads` / `disable_ledger_reads`, the write-through that makes rollback lossless, and the
  fail-loud authoritative reads that define the post-deletion failure mode.
