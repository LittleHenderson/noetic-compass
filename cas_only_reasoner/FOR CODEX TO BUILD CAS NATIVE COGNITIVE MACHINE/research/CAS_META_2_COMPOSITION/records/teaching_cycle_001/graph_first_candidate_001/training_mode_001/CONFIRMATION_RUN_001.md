# Confirmation run 001 — preregistration (frozen candidate, predeclared seeds)

Status: **PREPARED — NOT LAUNCHED.** No reservation, no owner authorization
record, and no AWS call exists for this experiment. This document is the
executable design the paid job would follow.

Owner directive this answers: *"Freeze this successful candidate and confirm
the result, rather than redesign it"* — a small predeclared set of independent
seeds, evaluated on **newly generated examples excluding the previously
examined panel**. No additional launch is authorized by that recommendation.

## 1. What stays frozen (no redesign)

| Element | Frozen value | Source |
| --- | --- | --- |
| Candidate | graph-first teaching candidate 001, `cas` framing only | run 005 |
| Plasticity group | `operation:^6` only; every other parameter frozen | `trainer.scope_parameters` |
| Representation | line-wise unit-normalized Hadamard encoder, `d_model=64` | `real_framework.build_encoder` |
| Option path | per-occurrence removal of tokens shared by all three options; zero-vector for empty content | `GraphLearner._content_ids` |
| Allowance per seed | `learning_rate=0.003`, `max_optimizer_steps=64`, `max_wall_seconds=600.0` | `trainer.TrainingBudget` |
| Stage-1 gate | same-token rewire input difference > 10× reorder baseline; finite losses with nonzero gradients | `competence.stage1_passes` |
| Fit criterion | `mean(after_loss) < mean(before_loss) − 0.02` | `competence.FIT_MARGIN` |
| Registered transfer bar | sealed combined correct ≥ 6 (of the 12-item panel it was registered on) | `competence.TRANSFER_THRESHOLD` |
| Verdict rule | REPLICATED iff ≥ 2 of 3 seeds meet fit AND ≥ 2 of 3 reach the transfer bar | `competence.confirmation_outcome` |

Nothing in this experiment changes the module, the representation, the option
path, the learning scope, or the allowance. The only new variables are the
predeclared seeds themselves.

## 2. Predeclared seeds (declared before the run)

`CONFIRM_SEEDS = (20260910, 20260911, 20260912)` — three independent seeds.
Each seed sets (a) the generated lesson dataset, (b) the encoder projection,
and (c) the module initialization, exactly as run 005's single seed did.

The previously examined dataset seed `20260909` is **excluded by
construction** and is not in the list.

## 3. Newly generated panels exclude the previously examined panel

Deterministic, non-neural evidence: `tools/graph_training_confirmation_panel_check.py`.

* Evidence file: `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/CONFIRMATION_PANEL_CHECK_001.json`
* sha256 `926bd47177e9b7876449748e040ee131be58749d31b92d61aff4bc5939adc25a`, 5,140 bytes
* Examined panel: **12** sealed ids, read from the preserved run-005 result
  `receipt_cas-meta2-competence-20260909210625-0a10f14d/competence_result.json`
* `neural_work: false`, `gpu_used: false` — pure-Python dataset construction only.

| Seed | Sealed ids | Per op (LIST / FIND / REACHED) | Familiar ids | Sealed overlap with examined panel | Familiar overlap with examined panel |
| --- | --- | --- | --- | --- | --- |
| 20260910 | 11 | 4 / 3 / 4 | 30 | 0 | 0 |
| 20260911 | 11 | 4 / 3 / 4 | 30 | 0 | 0 |
| 20260912 | 13 | 4 / 4 / 5 | 31 | 0 | 0 |

`all_sealed_panels_disjoint_from_examined_panel: true`,
`no_familiar_overlap_with_examined_panel: true`.

## 4. Panel size is seed-dependent — declared, not hidden

The frozen lesson generator produces a seed-dependent number of sealed
whole-part records: the examined panel had 12, and the three predeclared seeds
produce 11, 11 and 13. The registered bar is absolute (≥ 6). Two readings are
therefore computed and reported for every seed:

* **Primary (registered)**: sealed correct ≥ 6. This decides `outcome`.
* **Secondary (reported only)**: sealed correct ≥ `max(6, ceil(attempted/2))`,
  i.e. at least half of *that seed's* panel, never below 6 — 6 for an 11-item
  panel, 7 for a 13-item panel. Reported as `panel_normalized_met` and
  `outcome_panel_normalized`.

Open owner decision (does **not** change the job): whether the replication
claim should use the primary registered rule (default if the owner does not
answer before launch) or the conservative normalized reading. Both are
computable from the same recorded numbers; no second run is needed either way.

## 5. The job (one job, one run, no restarts)

One EC2 `g7.2xlarge` (RTX PRO 4500), one `$4.00` reservation, zero automatic
retries. Inside the single worker, for each predeclared seed, in order:

1. **Stage 1** — relationship-preservation gate (same-token rewiring vs
   connection-list reordering, module input difference) and forward/backward
   sanity. A gate failure stops that seed's run with the measured numbers
   (`STAGE1_CHECK_FAILED`); the remaining seeds still run.
2. **Stage 2** — 64 bounded optimizer steps on the familiar examples with the
   learning curve recorded every 8 steps and the digest containment report.
3. **Stage 3** — only if the fit criterion is met: sealed evaluation on that
   seed's **newly generated** validation/test whole-part records, predictions
   recorded before answers are consulted, plus the familiar-example accuracy.

Verdict: `competence.confirmation_outcome` over the three per-seed results.
Per-seed wall ceiling 600 s, per-seed 64 optimizer steps, job ceiling 1,800
worker seconds / 3,600 instance seconds.

## 6. What this experiment does NOT claim

* No composition claim, no specialist claim, no two-framing comparison
  (still postponed).
* No claim about the frozen sealed splits of the original attempt-010 panel.
* A `REPLICATED` verdict means: the same frozen candidate, on newly generated
  examples from three independent predeclared seeds, again met the fit
  criterion and the transfer bar for at least two of three seeds. Nothing more.

## 7. Cost and authority

* One new owner-signed authorization record + one new `$4.00` reservation
  (ledger revision 45 → 46; `$234.00` reserved / `$166.00` unreserved against
  the `$400.00` cap).
* The paid path requires: a hash-bound launch request, the owner authority
  record naming the exact job, source sha, archive sha256, manifest sha256,
  the frozen budget, **and** the predeclared seeds; plan output stays inert.
* No launch happens until the owner says GO.
