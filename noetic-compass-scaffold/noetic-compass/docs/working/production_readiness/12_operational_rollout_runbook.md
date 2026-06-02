# 12 — Operational Rollout Runbook (durable state ledger)

**Workstream:** 12 (operational counterpart to 10) · **Status:** runbook for the human-gated turn-on of the durable state ledger in a real deployment — the mechanism (workstream 10) and the multi-host backend (workstream 11) are built; this doc is the **procedure** for enabling them safely · **Date:** Jun 2, 2026
**Owner seam:** the deliberate, reversible operator act of moving the public CAS Harness off its four process-global dicts and onto the durable `StateStore` ledger — *one gated step at a time*, never a flag-day.

> Scope boundary up front: this runbook does **not** re-explain the migration design (that is
> [`10_state_substrate_migration.md`](./10_state_substrate_migration.md)) nor the multi-host backend
> (that is [`11_multi_host_state.md`](./11_multi_host_state.md)). It owns exactly one thing: *the order
> an operator turns the two flags on, what evidence must be earned at each gate before advancing, and
> how to roll back at every gate.* It carries one invariant from the rest of the program unchanged —
> **declared-vs-verified is sacred.** This runbook is built around the gap between "the flag is on" and
> "the flag is on **and** the evidence has been earned." Setting a flag is a *declaration*; the
> divergence evidence is the *verification*. Never advance on a declaration.

---

## 0. The non-negotiable order, and why it is an order

There are two flags, and they are deliberately separate (`api/config.py:26-28`,
`api/state_ledger_bootstrap.py:26-44`):

- **`NC_STATE_LEDGER_ENABLED`** installs the durable ledger mirror into **both** live services
  (`cas_harness_distributed_audits`, `cas_harness_fleet_executor`), rehydrates the four dicts from the
  durable file on startup, and turns on **dual-write + shadow-compare** — but **the dicts still serve
  every read.**
- **`NC_STATE_LEDGER_READ_AUTHORITY`** is the *separate* flip that moves **read authority** onto the
  ledger (`LedgerMirror.enable_ledger_reads()`, `migration.py:299-310`). It is meaningful **only** when
  the first flag is also set.

Both default `False` (`config.py:26-28`), so an unconfigured deployment is fully **dark**: no mirror is
installed, the ledger is never written or read, and behaviour is byte-for-byte the current dict-served
product. The cutover is *structurally* impossible to enable by accident, because every live read site
gates on `_STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger`
(`cas_harness_distributed_audits.py:495,503`; `cas_harness_fleet_executor.py:498,568,583`) — a service
with no mirror can never satisfy the first half.

The five steps below are an **order, not a menu.** Each gate exists because the next step makes a
*stronger* claim about the world, and that claim is only honest if the prior step earned its evidence.
The spine:

| Step | Action | Posture after | What it claims | Gate to advance |
|---|---|---|---|---|
| **1** | Set `NC_STATE_LEDGER_ENABLED=true`, restart | enabled, dual-write+shadow, **dict-authoritative** | "the ledger is mirroring the dicts" | install clean + rehydrate accounted |
| **2** | Watch live zero-divergence accumulate | *(unchanged — still step-1 posture)* | "the ledger and dicts **agree on real traffic**" | zero divergence over a real-traffic soak |
| **3** | Run live Postgres tests (`NC_TEST_POSTGRES_URL`) | *(unchanged)* | "the multi-host backend keeps the contract on a **real server**" | live contract + durability tests green |
| **4** | Set `NC_STATE_LEDGER_READ_AUTHORITY=true`, restart | enabled, **ledger read-authoritative** | "the ledger **is** the read truth" | **1 AND 2 AND 3 all passed** |
| **5** | *(separate doc)* consider Phase 4: delete the dicts | — | "the dicts are dead scaffolding" | see [`13_phase4_dict_deletion_plan.md`](./13_phase4_dict_deletion_plan.md) |

> **The one sentence to remember:** read-authority (step 4) is gated on **1 + 2 + 3 all passing**, and it
> is **reversible** — the dual-write keeps the dicts a hot write-through cache, so `disable_ledger_reads()`
> (or unsetting the flag and restarting) is an instant, lossless rollback. Phase 4 (step 5) is the **only**
> step that is *not* reversible, which is why it lives in its own gated plan.

---

## Step 1 — Enable the mirror (dual-write + shadow-compare; dicts still serve)

**Action.** Set the environment variable on **both** API hosts / replicas and restart them:

```
NC_STATE_LEDGER_ENABLED=true
# leave NC_STATE_LEDGER_READ_AUTHORITY unset (defaults false)
# NC_STATE_LEDGER_PATH defaults to state_ledger.db; point it at the durable backend / path for this deployment
```

On startup the lifespan calls `install_state_ledger(settings)` (`api/main.py:84`), which — because the
first flag is set and the second is not — builds a `SqliteStateStore` on `state_ledger_path`, wraps it in
one `LedgerMirror`, installs that mirror into **both** services, and rehydrates the four dicts from the
durable file (`state_ledger_bootstrap.py:88-150`). It does **not** call `enable_ledger_reads()` (the
second flag is off), so reads still come from the dicts. The handle is stashed on `app.state.state_ledger`
(`main.py:85`).

**Expected posture log-line (success).** The lifespan logs exactly (`main.py:91`):

```
state ledger: ENABLED, dual-write+shadow, dict-authoritative
```

If you instead see `state ledger: dark (dict-authoritative)` (`main.py:87`), the flag did not reach the
process — the env var is not set in the runtime the server actually booted with. Fix the environment; do
not proceed.

**Expected observability readout.** The ledger status readout / divergence evidence surface should report
posture **`enabled_shadow_dict_authoritative`** and a divergence tally that is *present and counting*
(`reads_compared` climbing as traffic flows, `divergences_found` ideally `0`). The startup handle also
carries honest rehydrate counts — `audit_count` and `fleet_counts`
(`state_ledger_bootstrap.py:82-85,144-150`) — i.e. how many records the durable file restored into the
dicts on boot. On a brand-new ledger file these are `0`; on a restart of an already-enabled deployment
they should match what the process was serving before it went down.

**GO criteria (all must hold to advance to step 2):**

1. The process started — **install fails loud, it does not degrade silently.** If the ledger path is
   unwritable, the store errors, or rehydrate fails, `install_state_ledger` lets the error propagate and
   **startup fails** (`state_ledger_bootstrap.py:46-56,102-107`). A running process with the success
   log-line above is itself the first piece of evidence: the mirror installed on both services and
   rehydrate completed.
2. The posture log-line reads `ENABLED, dual-write+shadow, dict-authoritative` (not `dark`, not
   `READ-AUTHORITATIVE`).
3. The status readout shows posture `enabled_shadow_dict_authoritative`.
4. Rehydrate counts are accounted for (zero on a fresh file; matching prior served state on a restart).

**NO-GO / abort signals:**

- **Startup crashed.** This is the *designed* honest outcome of a bad ledger path or backend — not a bug
  to work around. Read the propagated error, fix the cause (path permissions, backend reachability), and
  retry. Do **not** try to "force" the ledger on; a half-installed mirror is impossible by construction
  (the partial-install unwind clears both services before re-raising,
  `state_ledger_bootstrap.py:131-142`), but a crashed start means durability is genuinely not yet on.
- **Posture log-line says `READ-AUTHORITATIVE` at step 1.** Then the second flag is *also* set in this
  environment — you have skipped straight to step 4 without earning steps 2-3. **Abort and roll back**
  (below); unset `NC_STATE_LEDGER_READ_AUTHORITY` and restart back to step-1 posture.

**Rollback at this gate.** Unset `NC_STATE_LEDGER_ENABLED` and restart. On shutdown the lifespan calls
`teardown_state_ledger(handle)` (`main.py:96`), which uninstalls the mirror from both services and closes
the store (`state_ledger_bootstrap.py:153-174`); on the next boot, with the flag unset,
`install_state_ledger` returns `None` and the deployment is **fully dark** again — dicts authoritative,
ledger untouched, behaviour byte-for-byte as before. This rollback loses nothing the dicts didn't already
hold (the dicts were the read authority the whole time).

---

## Step 2 — Earn zero-divergence evidence on REAL traffic (do not advance on a clean start alone)

**This is the gate that the whole program turns on, and it is not an action you *do* — it is evidence you
*wait for*.** Step 1 made the ledger *mirror* the dicts. Step 2 proves they *agree under real production
traffic*. A clean startup (step 1) proves the wiring; it does **not** prove the two views of the world
stay identical as audits are created, dispatched, leased, submitted, merged, and as workers heartbeat and
go stale. Only real traffic exercises the mutation paths — including the indirect, clock-triggered ones
(`_expire_stale_leases`, `_expire_worker_leases`) that mutate run state outside a run's own mutators.

**Action.** None to the flags. Let the deployment run in step-1 posture and **watch the divergence tally**
on the ledger status readout. Drive real customer / staging traffic through it for a deliberate soak
window (define one up front — e.g. a fixed number of full distributed-audit lifecycles **plus** a
multi-shard soak run, or a wall-clock window such as 24h of representative traffic; mirror the soak
standard in `10_state_substrate_migration.md` §3 Phase 2).

**Expected observability readout (the gate).** Posture stays `enabled_shadow_dict_authoritative`. The
divergence tally shows `reads_compared` climbing with traffic and **`divergences_found` pinned at `0`**
across the entire soak window. Every `get_*` / `list_*` on both services shadow-compares the dict it
served against the ledger (`cas_harness_distributed_audits.py:498-510`,
`cas_harness_fleet_executor.py:494-507,562-596`), so a climbing `reads_compared` with zero divergences is
the live, accumulating proof.

> ### What zero-divergence evidence actually looks like
>
> A divergence is one recorded disagreement between a live dict and the shadow ledger
> (`migration.py:107-126`). "Zero divergence" is **not** "I didn't see an error" — it is a *positive,
> counted* claim with a denominator. Concretely, the evidence you are earning is:
>
> - **A non-trivial `reads_compared` denominator.** Zero divergences over *zero reads* is no evidence at
>   all. The tally must show that real reads happened — ideally across all four record kinds (audits,
>   workers, runs, fragment refs) and across the full lifecycle (`PLANNED → DISPATCHED → RUNNING →
>   MERGE_PENDING → COMPLETE`), not just idle health checks.
> - **`divergences_found == 0` the whole time.** The mirror records six kinds of disagreement, each a
>   short stable tag you would see if it fired: `write_failed` / `write_conflict_exhausted` (a mutation
>   the ledger could not persist), `missing_in_ledger` (the dict has a record the ledger never got),
>   `payload_mismatch` (a field the dict mutated in place but the ledger missed, or a field that did not
>   survive serialization), `read_failed` (the backend read errored), and `extra_in_ledger` (a ghost row
>   the ledger holds but the dict does not) — see `migration.py:206-282`. Any one of these is a defect in
>   the write path, **not** a reason to advance.
> - **Coverage of the clock-triggered paths.** Worker staleness is a *derived view*, recomputed from the
>   heartbeat on every read, and a worker aging `active → stale` must produce **zero** divergence (the
>   stored `last_heartbeat_at` did not change, only the rendered `status`). The soak must run long enough
>   for workers to actually go stale and leases to actually expire, so that the indirect re-mirror paths
>   are exercised under real timing.
>
> **The honest distinction this gate enforces:** "`NC_STATE_LEDGER_ENABLED=true`" is a *declaration* that
> durability is on. "`divergences_found == 0` over `reads_compared = <large N>` of real traffic, across
> all kinds and the full lifecycle" is the *verification* that the ledger can be trusted to answer. Step 4
> is licensed by the **second** statement, never the first.

**GO criteria (all must hold to advance to step 3):**

1. `divergences_found == 0` for the entire defined soak window.
2. `reads_compared` is large and representative (real lifecycle traffic across all four kinds, not idle
   pings).
3. The window covered the clock-triggered paths (workers went stale, leases expired) with still-zero
   divergence.

**NO-GO / abort signals:**

- **Any non-zero `divergences_found`.** Stop. A divergence means the dict and the ledger disagree, which
  means the ledger is **not yet** a safe read authority. Read the divergence reason tag, find the write
  site that diverged (a mutator that changed a dict but did not mirror it, or a payload that did not
  round-trip), fix it, and **restart the soak window from zero** — a partially-clean window is not
  evidence. Do **not** advance to step 4.
- **A flat or trivial `reads_compared`.** No real reads happened — you have not earned evidence, you have
  only confirmed the process is up. Generate representative traffic before this gate counts.

**Rollback at this gate.** Same as step 1 — unset `NC_STATE_LEDGER_ENABLED` and restart back to dark. No
read authority has moved, so there is nothing to undo beyond uninstalling the mirror. The dicts have been
authoritative throughout.

---

## Step 3 — Verify the multi-host backend against a REAL server (`NC_TEST_POSTGRES_URL`)

**Why before step 4, not after.** Step 4 makes the ledger the read authority. If this deployment is (or
will be) multi-host, the read authority is a **shared Postgres**, and per
[`11_multi_host_state.md`](./11_multi_host_state.md) the Postgres backend's live conformance,
close/reopen-durability, and fence-mint tests **skip unless `NC_TEST_POSTGRES_URL` is set, and have not
been run against a real Postgres** — so "`PostgresStateStore` passes the contract" is, until you run them,
a *declared* claim, not a *verified* one (`11_multi_host_state.md` §0 implementation-status note). Moving
read authority onto a backend whose contract conformance is only declared would be exactly the
declared-vs-verified violation this program refuses.

**Action.** Point the test suite at a real Postgres server and run the live state-substrate tests
(do **not** run this against production data — use a dedicated test database):

```
NC_TEST_POSTGRES_URL=postgresql://…   # a real, reachable Postgres for this deployment's backend
pytest tests/test_state_substrate_postgres.py
# plus the live migration suite that proves the seam end-to-end on the durable backend:
pytest tests/test_state_substrate_live_migration.py
```

**Expected readout (the gate).** The previously-skip-guarded tests now **run and pass**: the
`run_state_store_contract` conformance suite (record round-trip + version 0→1 promotion, fail-closed
tenant scoping, optimistic concurrency / first-writer-wins, version-checked delete, the full lease
lifecycle), the **close/reopen durability** check, and the **fencing-token mint** all green against the
live server (`11_multi_host_state.md` §1.1, §3, §5.2). For a genuinely multi-host claim, also exercise the
two-replica smoke (`10_state_substrate_migration.md` §3 Phase 3: host A prepares a run, host B merges it
against the one shared backend).

**GO criteria (all must hold to advance to step 4):**

1. `NC_TEST_POSTGRES_URL` pointed at a **real** server (not the in-memory fallback, not SQLite) — the tests
   actually ran rather than skipped.
2. The full conformance + durability + fencing suite is green against that server.
3. If multi-host is in scope: the two-replica cooperation smoke passed (one shared backend, host A
   prepares, host B merges).

**NO-GO / abort signals:**

- **Tests skipped** (env var unset or unreachable server). A skipped test earns nothing — the multi-host
  claim is still only declared. Treat a skip as a NO-GO.
- **Any contract / durability / fencing failure.** The backend does not yet keep the guarantees the read
  authority depends on. Fix the backend or its configuration (`synchronous_commit`,
  `synchronous_standby_names`, failover routing per `11_multi_host_state.md` §3.4) before advancing.
- **Reminder:** a single Postgres instance that passes these tests earns *"survives restart,"* **not**
  *"survives host loss"* — the stronger claim needs synchronous replication + failover routing
  (`11_multi_host_state.md` §6). Do not round the claim up; size step-4 expectations to what the config
  actually earned.

**Rollback at this gate.** Nothing to roll back — this step touches only the test database, never the
running deployment. A failure here simply means you stay at step-1/2 posture (mirror on, dicts
authoritative) until the backend is fixed.

---

## Step 4 — Flip read authority onto the ledger (gated on 1 + 2 + 3; REVERSIBLE)

> **Do not run this step unless steps 1, 2, and 3 have *all* passed:** the mirror installed clean
> (step 1), zero-divergence was earned over real traffic (step 2), and the multi-host backend was verified
> against a real server (step 3). This is the directive's "only after that passes" gate. Setting the flag
> without the earned evidence is the precise declared-vs-verified dishonesty this runbook exists to refuse.

**Action.** With `NC_STATE_LEDGER_ENABLED` still set, additionally set the **separate** flag on both hosts
and restart:

```
NC_STATE_LEDGER_ENABLED=true            # still set from step 1
NC_STATE_LEDGER_READ_AUTHORITY=true     # the Phase-3 read flip — separate, deliberate, reversible
```

On startup `install_state_ledger` now *also* calls `mirror.enable_ledger_reads()`
(`state_ledger_bootstrap.py:128-130`; `migration.py:299-310`), flipping `read_from_ledger` to `True`. From
this point the live `get_*` / `list_*` reconstruct each record's **stored state** from the durable rows
via `read_payload` / `read_all_payloads` instead of the dicts
(`cas_harness_distributed_audits.py:495-497,503-505`;
`cas_harness_fleet_executor.py:498-501,568-574,583-588`). Two things are deliberately **not** moved by the
flip, because they are *derived views* recomputed on read in **both** modes: worker **staleness**
(re-derived from the heartbeat against the same cutoff, `fleet_executor.py:498-501`) and the run's
**verifier gate** (`_refresh_run_gate` is called after reconstruction, `fleet_executor.py:572-574,586-588`).
**The flip moves authority for stored state, not the ACCEPT-gating logic** — the merge gate's honesty spine
is untouched.

**Expected posture log-line (success).** The lifespan logs exactly (`main.py:89`):

```
state ledger: ENABLED, LEDGER READ-AUTHORITATIVE
```

**Expected observability readout.** Posture flips to **`enabled_ledger_read_authoritative`**. The
divergence tally should **stay at zero** — because the dual-write is now also a **write-through cache**
(every mutation still writes the dict back as well as the ledger), the dict remains byte-current with the
ledger, so any continued shadow accounting still agrees.

**GO criteria (cutover is healthy):**

1. Posture log-line reads `ENABLED, LEDGER READ-AUTHORITATIVE`; status readout shows
   `enabled_ledger_read_authoritative`.
2. Reads are being served (audits, runs, workers list correctly) with `divergences_found` still `0`.
3. Authoritative reads are **failing loud on backend trouble, not fabricating** — `read_payload` /
   `read_all_payloads` propagate `StateStoreError` (`migration.py:317-338`); a healthy backend means no
   such errors, but the *posture* is now "an unreachable ledger fails the request" rather than "the dict
   silently answers." That is the correct, honest posture for a read-authoritative ledger.

**NO-GO / abort signals:**

- **Divergences appear after the flip,** reads error, or records come back wrong / empty. The ledger is not
  faithfully serving. **Roll back immediately** (below) — this is instant and lossless.
- **Posture log-line still says `dual-write+shadow, dict-authoritative`** after setting the second flag:
  the read-authority flag did not reach the process (or `NC_STATE_LEDGER_ENABLED` was dropped, which makes
  the second flag meaningless). Fix the environment; the ledger is still dict-authoritative, so there is no
  urgency, only a non-advance.

**Rollback at this gate (instant, lossless — this is the whole point of two flags).** Two equivalent paths,
both safe because the dual-write kept the dicts a current write-through cache the entire time:

1. **In-process / immediate:** call `disable_ledger_reads()` (`migration.py:312-315`) to flip
   `read_from_ledger` back to `False`. Reads instantly return to the dicts, which are byte-current. (Wire
   this to whatever operational lever the deployment exposes; the method is the lever.)
2. **Via config / restart:** unset `NC_STATE_LEDGER_READ_AUTHORITY` (keep `NC_STATE_LEDGER_ENABLED` set)
   and restart. The next boot installs the mirror **without** the read flip — back to step-1/2 posture
   (dual-write + shadow, dict-authoritative). Or unset **both** flags to return fully dark.

Because rollback is instant and loses nothing, read-authority is a *safe* place to sit and soak. **Sitting
in `enabled_ledger_read_authoritative` for a deliberate period, watching divergences stay at zero, is
itself the evidence Phase 4 needs** — see step 5.

---

## Step 5 — Only then: consider Phase 4 (deleting the dicts)

Phase 4 — physically removing `_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS` and their
rehydrate/reset scaffolding — is the **one irreversible step**, because deleting the dicts removes the
write-through hot cache that makes steps 1-4 instantly rollback-able. It is therefore **out of scope for
this runbook** and gated behind its own analysis: see
[`13_phase4_dict_deletion_plan.md`](./13_phase4_dict_deletion_plan.md). That plan deletes nothing; it maps
the work and states the preconditions (enable deployed; zero-divergence earned; read-authority flipped and
**soaked**; live multi-host Postgres verified; a tested rollback path) that must **all** hold before any
deletion is safe.

> **Declared-vs-verified, one last time.** Reaching `enabled_ledger_read_authoritative` is a *declaration*
> that the ledger is the truth. Soaking there with zero divergence over real traffic for a stated period is
> the *verification*. Phase 4 is licensed only by the verification — and even then, only after the
> instant-rollback affordance it removes has an equally-safe replacement (see doc 13 §(e)).

---

## Quick reference — flags, postures, log-lines, rollbacks

| Posture | Flags | Posture log-line (`api/main.py`) | Status readout | Reads served from | Rollback |
|---|---|---|---|---|---|
| **Dark** (default) | both unset | `state ledger: dark (dict-authoritative)` (`:87`) | `dark` | dicts | n/a (already safe) |
| **Step 1-3** | `ENABLED=true` only | `state ledger: ENABLED, dual-write+shadow, dict-authoritative` (`:91`) | `enabled_shadow_dict_authoritative` | **dicts** (ledger shadow-compared) | unset `ENABLED`, restart → dark |
| **Step 4** | `ENABLED=true` **and** `READ_AUTHORITY=true` | `state ledger: ENABLED, LEDGER READ-AUTHORITATIVE` (`:89`) | `enabled_ledger_read_authoritative` | **ledger** (dicts kept current via write-through) | `disable_ledger_reads()` **or** unset `READ_AUTHORITY`, restart → step-1 posture (instant, lossless) |

---

## Cross-references

- **[`10_state_substrate_migration.md`](./10_state_substrate_migration.md)** — the migration design and the
  Phase 0-4 model this runbook operationalizes. Phase 2's zero-divergence proof obligation is this
  runbook's step 2; Phase 3's read-authority flip is step 4; Phase 4 is step 5 / doc 13.
- **[`11_multi_host_state.md`](./11_multi_host_state.md)** — the multi-host backend whose live tests are
  this runbook's step 3, and the §6 truthful-claims table that bounds what step 4 may claim (restart vs
  host-loss survival; acquire vs act / fencing).
- **`api/state_ledger_bootstrap.py`** — `install_state_ledger` / `teardown_state_ledger` /
  `StateLedgerHandle`: the fail-loud install, the partial-install unwind, and the two-flag logic this
  runbook drives.
- **`api/main.py:79-97`** — the lifespan wiring: where the handle is installed, stashed on
  `app.state.state_ledger`, torn down, and where each posture log-line is emitted.
- **`api/services/production/state_substrate/migration.py`** — `LedgerMirror`: `enable_ledger_reads()` /
  `disable_ledger_reads()` (the reversible read switch), `read_from_ledger`, the shadow-compare and
  divergence accounting whose tally this runbook reads at every gate.
- **The ledger status readout / divergence evidence surface** — the pure observability function
  `ledger_status(handle)` in `api/services/production/state_substrate/observability.py`, exposed read-only at
  **`GET /api/state-ledger/status`** (`api/routes/state_ledger_status.py`, wired in `api/main.py`). It reports
  posture `{dark | enabled_shadow_dict_authoritative | enabled_ledger_read_authoritative}`, the rehydrate
  counts `audit_count` / `fleet_counts`, and the live divergence tally
  `{reads_compared, divergences_found, last_divergence}` read from `LedgerMirror.tally()`
  (`migration.py`). This is the concrete surface every gate above means by "the status readout": it is
  dark-safe (returns exactly `{"posture": "dark"}` when no mirror is installed — it never fabricates a
  "0 divergences" that no shadow-compare earned), read-only, and changes nothing it observes.
