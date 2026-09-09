# Graph-first ^6 — CONFIRMATION run 001 — authorization request (PACKAGE BUILT; NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** This is the experiment you asked for:
*"Freeze this successful candidate and confirm the result, rather than
redesign it."* Nothing has been reserved, registered, or launched.

## What this is

The same frozen candidate — same module, same representation, same option
path, same `operation:^6`-only learning scope, same allowance (lr `0.003`,
64 optimizer steps, 600 s) — repeated for **three predeclared seeds**
`(20260910, 20260911, 20260912)` on **newly generated examples**, so the
sealed panel is no longer the panel you already examined.

## The panel correction is now enforced by construction

Your correction stands: run 005's 12 sealed ids were identical to attempt
010's panel — held out from that run's training, but not new to the
development process. This experiment fixes that with numbers, not promises:

* Evidence file `CONFIRMATION_PANEL_CHECK_001.json`
  (sha256 `926bd47177e9b7876449748e040ee131be58749d31b92d61aff4bc5939adc25a`,
  5,140 bytes), produced by `tools/graph_training_confirmation_panel_check.py`
  with `neural_work: false` and `gpu_used: false`.
* Examined panel: **12** ids, read from the preserved run-005 result.
* New panels: **11** ids (seed 20260910), **11** ids (20260911), **13** ids
  (20260912). Sealed-id overlap with the examined panel: **0, 0, 0**.
  Familiar-id overlap with the examined panel: **0, 0, 0**.
* Dataset seed `20260909` (the examined one) is excluded by construction.

## Declared, not hidden: panel sizes differ

The frozen lesson generator produces a seed-dependent sealed panel size
(12 examined; 11, 11, 13 for the new seeds). The registered bar is absolute
(**≥ 6 correct**). Two readings are computed and reported for every seed:

* **Primary (registered):** sealed correct ≥ 6 → decides the verdict.
* **Secondary (reported only):** sealed correct ≥ `max(6, ceil(attempted/2))`
  — 6 of 11, 7 of 13 — the conservative comparable reading.

**Decision item 2 for you:** which reading is authoritative for the
replication claim. Default if you do not say: the registered absolute rule
(≥ 6), with the normalized reading reported alongside. Either way, one run
produces both numbers; no second run is needed.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `08abdf29d0eaf91b7ed48950735d3320ee5ab3d3` |
| archive_sha256 | `59a2432fbf082006974be3aa82130372449c679b0ffdb155273d2e03ca38d798` |
| archive_bytes | 372060 |
| manifest_sha256 | `7c1484f7ec1a5f5b7c651d095510cd69ffa3505408e92a452f4a27c0c84b0d94` |
| member_count | 32 |
| package | `training_mode_001/confirmation_package_001/` |
| launch request | `training_mode_001/confirmation_launch_001/launch_request.json` (sha256 `c34c5de90645c5c6a4c24f256817422431429774f44d55bdda82bd8be519ecc3`, `launch_authorized: false`) |
| proposed job | `cas-meta2-confirmation-20260909233000-08abdf29` |
| launcher | `aws/graph_training_confirmation_launch.py` at commit `08abdf29` |
| preregistration | `CONFIRMATION_RUN_001.md` |

The packaged worker was byte-checked against `render_worker()` and contains
exactly: per seed → stage 1 gate → 64 bounded updates → sealed evaluation →
deterministic verdict. No parameter scope is touched by the worker; no
learning-rate or step change appears anywhere in it.

## The one-job request

ONE job, one arm (`cas`), three predeclared seeds inside it, one new `$4.00`
reservation created exactly once, no refund, no automatic retry, verified
cleanup, original errors preserved. Ledger today: revision 45, `$230.00`
reserved / `$170.00` unreserved; after this job's reservation: revision 46,
`$234.00` / `$166.00`.

Verdict rule (deterministic, `competence.confirmation_outcome`):
**REPLICATED** iff ≥ 2 of 3 seeds meet the fit criterion AND ≥ 2 of 3 reach
the registered transfer bar; otherwise **NOT_REPLICATED**, with every
per-seed number reported.

## What I need from you

1. **GO / NO-GO** for this single job (one new owner-signed record + one new
   `$4.00` reservation).
2. **Which transfer reading is authoritative** (registered absolute ≥ 6 —
   default — or the conservative panel-normalized reading).

On GO I will mint the owner record binding these exact identities, register,
and execute — nothing before. No reservation and no AWS call exists today.
