# GRAPH6_CONFIRMATION_001 — authorization request (PACKAGE BUILT; NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** One combined job, one package, one total
budget. Nothing has been reserved, registered, or launched.

## What this job is

Preserve competence run 005 as the successful baseline and measure, in ONE job:
three **independently initialized** candidate learners (not three rounds on one
checkpoint), 64 updates each = **192 updates**, each measured on the SAME
pre-registered **fresh 90-case panel** before and after training, with answers
sealed until the predictions are recorded, plus the preserved-baseline row.
Reused as-is: encoder, tokenizer fitting set, module, teaching records, teaching
order, optimizer settings, existing checks. No architecture change, no framing
comparison.

## The fresh panel (already built and audited, no GPU used)

Evidence: `GRAPH6_FRESH_PANEL_001.json`
(sha256 `c7876508fd3853556569134191a126f19113d02aac6f59c51b9556b7c46cc15a`,
`neural_work: false`, `gpu_used: false`).

| Item | Value |
| --- | --- |
| Families / cases | **30 families, 90 cases** (one question per operation: 30 / 30 / 30) |
| Reach coverage | 10 `direct`, 10 `via`, 10 `absent` |
| Pattern coverage | 30 distinct family patterns; 56 distinct case patterns of 90 |
| Content digest | `d1076de3ae310562e97552c4f854fab10661bed78f9d4108187ea2f549ae8209` |
| Excluded | the 42 whole-part records of the previously examined dataset (seed `20260909`, all splits) |
| Overlap | **0** exact ids and **0** label-invariant signatures — renamed duplicates are rejected, not just identical records |
| Isolation | the panel never enters tokenizer fitting, training, checkpoint selection or any experiment change |

## Pre-registered rule (declared before execution — your approval fixes it)

* Fit (unchanged): `mean(after_loss) < mean(before_loss) − 0.02`.
* Fresh transfer, per candidate — passes iff all three:
  1. paired margin ≥ **+0.10** (9 of 90 cases) **and** family-clustered 95 % bootstrap lower bound **> 0**;
  2. absolute fresh accuracy ≥ **0.50** (45/90), chance is 1/3;
  3. no operation regresses and ≥ 2 operations gain ≥ +0.10.
* Uncertainty: family-clustered percentile bootstrap (10,000 resamples, seed
  `20260921`, 30 clusters × 3 cases) **plus** exact McNemar on discordant cases.
* Verdict: `FRESH_TRANSFER_CONFIRMED` iff **≥ 2 of 3** candidates pass; every
  candidate is reported either way.
* The old **6/12** threshold is **not** reused.

## One measured problem you must know about: the run-005 checkpoint does not exist

Run 005 saved only the parameter **digest**
`cb008721b92144b4e0ef52e86c2c449415935110747aca18ff23229c05240e50`. The weights
were never written to evidence, and the wheel builds the module's `nn.Linear`
layers with **no seed** (`cas_cjt/neural.py` lines 174–188), so those exact
weights cannot be reproduced. Your table row *"Preserved successful checkpoint —
fresh evaluation only"* therefore cannot be filled from the original weights.

**Decision item 1 — pick one:**
* **A (default, no extra cost):** report the row `UNAVAILABLE` with that reason;
  the trained-vs-untrained comparison is unaffected (each candidate is measured
  before and after training on the new panel).
* **B:** add a declared reproduction candidate (same frozen configuration,
  recorded init seed) and check its trained digest against `cb008721…`; it is
  reported `BASELINE_REPRODUCED` only on an exact match. Cost: +64 updates,
  +600 s, +$2.52 ceiling.

**Decision item 2:** confirm the pre-registered fresh-transfer rule above as
written, or state a different margin/level before the run.

## Exact package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `e485b07c3fbdc1fd3231bfdc9638635119660e5a` |
| archive_sha256 | `b3d7d1be6c811f856ceb859db461752e6f90135d5e7e4240eecb06e98e0f8c50` |
| archive_bytes | 385418 |
| manifest_sha256 | `b30c4260d6502715496f1ffb1497422fae4b031315480e892b1dd91806d6a538` |
| member_count | 34 |
| package | `training_mode_001/graph6_confirmation_package_001/` |
| launch request | `training_mode_001/graph6_confirmation_launch_001/launch_request.json` (sha256 `b8f75ffe3cbf6ae785c7bf144bd652674d4503797106583b50336453cd4b0c29`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6conf-20260910013000-e485b07c` |
| launcher | `aws/graph_training_graph6_confirmation_launch.py` at commit `e485b07c` |
| preregistration | `GRAPH6_CONFIRMATION_001.md` |

The packaged worker was byte-checked against `render_worker()`; the manifest
carries `launch_enabled: false`, `learner_seeds [20260913, 20260914, 20260915]`,
`panel_seed 20260920`, `baseline_mode none`, `total_optimizer_steps 192`.
193 graph tests pass.

## Total budget (one authorization)

| Item | Value |
| --- | --- |
| Candidates | 3 (seeds `20260913`, `20260914`, `20260915`; encoder seed `20260909` fixed and shared) |
| Optimizer updates | 64 per candidate → **192 total** |
| Wall ceiling | 600 s per candidate → 1,800 s worker, 5,400 s instance (1.5 h) |
| GPU | 1 × `g7.2xlarge` (RTX PRO 4500); no T4 fallback |
| Reservation | one new **`$6.00`** (1.5 h × `$2.52` + `$1.48` ancillary, rounded up) |
| Ledger after | revision 45 → 46: `$236.00` reserved / `$164.00` unreserved (cap `$400.00`) |
| Retries | zero; original errors preserved; verified cleanup on every exit |
| Controls | encoder identity shared across candidates; initial checkpoint identities pairwise distinct; containment limited to `operation:^6`; all candidates reported |

## What I need from you

1. **GO / NO-GO** for this single job (one owner-signed record + one new `$6.00`
   reservation).
2. **Baseline row:** A (report `UNAVAILABLE`, default) or B (add the declared
   reproduction candidate).
3. **Confirm the pre-registered fresh-transfer rule** as written, or state a
   different margin/level now.

On GO I mint the owner record binding these exact identities, register, and
execute — nothing before. After confirmation, the two follow-on tracks stay
separate and separately authorized: (1) the focused curriculum for
"direct / through another part / not connected", (2) the first learned child
call inside CASformer.
