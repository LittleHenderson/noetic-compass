# Doc 14 — Operational ledger enable: live-traffic evidence (2026-06-02)

**Status:** steps 1–3 of the rollout runbook (doc 12) are **VERIFIED under real HTTP
service traffic**. Steps 4 (read-authority flip) and 5 (Phase-4 dict deletion) are **NOT
done** and were deliberately not touched here.

This is the gate that turns the durable state-ledger work from *built and tested* into
*proven under real service traffic*: the `LedgerMirror` ran **enabled** inside a real
running API, dual-writing and shadow-comparing every read against a durable
`SqliteStateStore`, while the process-global dicts **still served every read** — and it
showed **zero divergence**.

## What this proves

- `NC_STATE_LEDGER_ENABLED=true` boots the API into the honest posture
  `enabled_shadow_dict_authoritative` (mirror installed; dual-write + shadow-compare on;
  dicts still authoritative for reads). Confirmed by `GET /api/state-ledger/status` at
  boot, before any traffic.
- A full distributed-audit lifecycle runs end-to-end over real HTTP while the mirror is
  live: **create → dispatch → register workers → prepare fleet → lease → receipt →
  merge**, all `200 OK`, merge reaching `status=COMPLETE`, `gate=ready_for_verifier`.
- Across **95** real shadow-compares spanning every ledger-mirrored read site, the mirror
  found **0** divergences (`last_divergence: null`). A dual-write that failed to land in
  the ledger would have produced a missing/disagreeing ledger read on the next compare —
  i.e. a divergence — so 95 clean compares is direct evidence the dual-writes persisted to
  the durable store and matched the dicts byte-for-byte.

## What this does NOT prove (honesty boundary)

- **Not host-loss survival.** This is a single embedded `SqliteStateStore` on one host. It
  proves the mirror is correct and durable to *this* process's own close/reopen, not that
  state survives losing the host. Host-loss survival needs synchronous replication +
  failover and is out of scope here (multi-host Postgres durability was verified separately
  — see commit `c32f639`, PostgreSQL 16.4, 10/10 tests). Divergence (dict-vs-ledger) is
  backend-agnostic, so the zero-divergence result holds regardless of which `StateStore`
  backs the mirror.
- **Not read-authority.** `NC_STATE_LEDGER_READ_AUTHORITY` was held **false** the whole
  run. The dicts served every read; the ledger was shadow-only. Flipping read-authority is
  step 4 and is a separate gate.
- **Not Phase-4 deletion.** No dict was removed; the `_FRAGMENT_REFS` replay-guard re-point
  (doc 13) is untouched.

## Topology

- A real `uvicorn api.main:app` server process, bound to `127.0.0.1:8743`, booted with the
  enable flags below — the same command shape a staging deployment would use.
- A **separate** client process drove the lifecycle over real HTTP (loopback TCP, full
  middleware stack: request-id → JWT auth → rate-limit → audit-log). It minted its own
  Bearer JWT with the same `NC_JWT_SECRET` (the auth middleware verifies signature + expiry
  only) and computed each Evidence Packet fragment ref with the real service function
  `build_evidence_fragment_ref`, so the server's recompute-and-compare validation passed.

Server environment:

```
NC_STATE_LEDGER_ENABLED=true
NC_STATE_LEDGER_READ_AUTHORITY=false      # dicts stay read-authoritative (steps 1–3 only)
NC_STATE_LEDGER_PATH=<workdir>/ledger.db  # durable SqliteStateStore, fresh file
NC_JWT_SECRET=<shared staging secret>
NC_RATE_LIMIT_TIER=enterprise             # so a full lifecycle does not trip the
NC_RATE_LIMIT_RPM=1000                    # community monthly cap (50) mid-run
```

## Observed status (verbatim)

Before any traffic (`GET /api/state-ledger/status`):

```json
{"posture": "enabled_shadow_dict_authoritative", "audit_count": 0,
 "fleet_counts": {"workers": 0, "fleet_runs": 0, "fragment_refs": 0},
 "divergence_tally": {"reads_compared": 0, "divergences_found": 0, "last_divergence": null}}
```

After the full lifecycle + three rounds of read-site touches:

```json
{"posture": "enabled_shadow_dict_authoritative", "audit_count": 0,
 "fleet_counts": {"workers": 0, "fleet_runs": 0, "fragment_refs": 0},
 "divergence_tally": {"reads_compared": 95, "divergences_found": 0, "last_divergence": null}}
```

Lifecycle: `audit_id=cas-dist-94d9959aaa842115`, 2 workers, 2 fleet jobs, 2 receipts,
fleet merge `COMPLETE`.

### Reading the numbers (so 0 is not misread)

- `audit_count` and `fleet_counts` are the **boot-time rehydration snapshot** — how many
  records were loaded from the ledger *at startup*. The ledger file was fresh, so they are
  0 and stay 0. They are not live counters and are not expected to move during a run.
- The live evidence is `reads_compared` climbing 0 → **95** with `divergences_found`
  staying **0**. That is the Phase-2 watch the runbook calls for.

## Reproduction

Throwaway driver + artifacts live under `.tmp/ledger_enable/` (never committed). Launch a
real server with the env above, then run the driver against it:

```
PYTHONPATH=<repo> NC_JWT_SECRET=<same secret> \
LEDGER_DRIVER_BASE=http://127.0.0.1:8743 \
LEDGER_DRIVER_OUTDIR=<repo>/.tmp/ledger_enable \
python .tmp/ledger_enable/driver.py
```

It exits 0 only if `posture == enabled_shadow_dict_authoritative`, `reads_compared > 0`,
and `divergences_found == 0`.

## Next gates (not done here)

1. **Step 4 — read-authority.** Set `NC_STATE_LEDGER_READ_AUTHORITY=true` and re-run this
   watch; posture should become `enabled_ledger_read_authoritative` with divergence still 0.
2. **Step 5 — Phase-4 deletion.** Only after sustained zero-divergence on real traffic, and
   only after re-pointing the `_FRAGMENT_REFS` replay guard off the in-RAM set (doc 13).
