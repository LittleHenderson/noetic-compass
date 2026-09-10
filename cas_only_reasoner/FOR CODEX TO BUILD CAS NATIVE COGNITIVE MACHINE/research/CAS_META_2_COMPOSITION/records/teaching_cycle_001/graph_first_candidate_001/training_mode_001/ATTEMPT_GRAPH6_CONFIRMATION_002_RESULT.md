# GRAPH6_CONFIRMATION_001 — attempt 002 RESULT

**Registered outcome (deterministic rule, no prose judgement): `FRESH_TRANSFER_NOT_CONFIRMED` — 0 of 3 candidates passed the pre-registered fresh-transfer rule.**

The familiar-example learning replicated in all three independently initialized
learners (fit criterion met 3/3), but the improvement did not reach the
pre-registered bar on the fresh 90-case panel.

## Execution facts

| Item | Value |
| --- | --- |
| job | `cas-meta2-graph6conf-20260910023000-a387d882` |
| launcher status | `AWS_GRAPH6_CONFIRMATION_FINISHED` |
| result sha256 | `8a313f3d39a42443a2d00bcb4f4f00a3d71de8763f59098e057e4fc4951105f4` |
| elapsed | 574.9 s |
| instance | `i-0c5c7705128fd938e` → `CONFIRMED_TERMINATED` |
| cleanup | `complete: true`, failures `[]`, bucket deleted, results deleted |
| independent hygiene check | 0 active `cas_meta_job`-tagged instances, 0 graph6 buckets, 0 leftover security groups |
| reservation | `$6.00`, `RESERVED_NO_AUTOMATIC_REFUND`, AWS-side record `RECORDED`; ledger 46 → 47 (`$242.00` reserved / `$158.00` unreserved) |
| budget consumed | 192 / 192 declared optimizer updates (64 per candidate), 3 / 3 candidates reported |

## Controls (all held)

| Control | Observed |
| --- | --- |
| encoder identity shared across candidates | **true** — one projection, `116f3677d343db7cd9becbb0b293c4419d5f455b9e1044e33dbd6738ed1468cb` |
| initial checkpoints distinct | **true** — `9c34c98f…`, `61b0f180…`, `da4f55f7…` |
| containment limited to `operation:^6` | **true** for all three — changed only `left.weight`, `merge.weight`, `right.weight`; no forbidden change |
| teaching dataset frozen | seed `20260909` for all candidates (the attempt-001 bug is fixed and guarded) |
| answers sealed before predictions | **true** |
| all scheduled candidates reported | **true** — none dropped |

## The results table (exact numbers)

| Candidate | Practice before → after | Fresh before → after | Δ (paired) | 95 % CI (family-clustered) | McNemar p | Fit margin | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| seed 20260913 | 9/30 → 23/30 | 29/90 → 34/90 (37.78 %) | +5/90 = +5.56 % | −8.89 % … +20.00 % | 0.5327 | 0.4940 (met) | **no** |
| seed 20260914 | 4/30 → 22/30 | 27/90 → 36/90 (40.00 %) | +9/90 = +10.00 % | −5.56 % … +25.56 % | 0.2327 | 0.5148 (met) | **no** |
| seed 20260915 | 9/30 → 23/30 | 17/90 → 36/90 (40.00 %) | +19/90 = +21.11 % | +8.89 % … +32.22 % | 0.0013 | 0.5340 (met) | **no** |
| preserved run-005 checkpoint | no additional training | **UNAVAILABLE** (weights never persisted; only digest `cb008721…`) | — | — | — | — | — |

Per-operation fresh counts (before → after, of 30 each):

| Candidate | LIST_PARTS | FIND_SHARED_PART | REACHED_VIA |
| --- | --- | --- | --- |
| seed 20260913 | 5 → 6 | 16 → 14 | 8 → 14 |
| seed 20260914 | 8 → 10 | 11 → 15 | 8 → 11 |
| seed 20260915 | 5 → 7 | 3 → 15 | 9 → 14 |

Learning curves (mean per-op loss, every 8 updates):
* 20260913: `1.08842 → 0.90253 → 0.80259 → 0.73358 → 0.69473 → 0.66173 → 0.64150 → 0.58301 → 0.59440`
* 20260914: `1.16560 → 0.93109 → 0.79266 → 0.75352 → 0.74277 → 0.69828 → 0.68116 → 0.63435 → 0.65085`
* 20260915: `1.08568 → 0.86285 → 0.75540 → 0.69571 → 0.65163 → 0.61678 → 0.59603 → 0.55211 → 0.55167`

## Which pre-registered conditions failed

| Condition (per candidate) | Required | 20260913 | 20260914 | 20260915 |
| --- | --- | --- | --- | --- |
| paired margin | ≥ +10 % | 5.56 % ✗ | 10.00 % ✓ | 21.11 % ✓ |
| interval above zero | CI low > 0 | −8.89 % ✗ | −5.56 % ✗ | +8.89 % ✓ |
| absolute level | ≥ 50 % | 37.78 % ✗ | 40.00 % ✗ | 40.00 % ✗ |
| per operation | no regression, ≥ 2 gain ≥ +10 % | FIND regressed ✗ | ✓ | ✓ |

Verdict rule: `FRESH_TRANSFER_CONFIRMED` iff ≥ 2 of 3 pass → **0 passed** →
`FRESH_TRANSFER_NOT_CONFIRMED`.

## What these numbers support, and what they do not

Supported (real measurements from a completed, cleaned-up job):
* The **familiar-example learning replicates** across three independent
  initializations: fit criterion met 3/3 with margins 0.4940 / 0.5148 / 0.5340,
  and practice accuracy rose from 9/30, 4/30, 9/30 to 23/30, 22/30, 23/30.
* The **fresh-panel improvement is smaller than the registered bar**: +5.56 %,
  +10.00 %, +21.11 % paired, with only the third candidate's interval excluding
  zero, and none reaching the 50 % absolute level.
* The **weakest fresh operation is `LIST_PARTS`**: 6/30, 10/30, 7/30 after
  training, at or below the 1/3 chance level of the three-slot interface, while
  `FIND_SHARED_PART` (14/30, 15/30, 15/30) and `REACHED_VIA` (14/30, 11/30,
  14/30) sit between chance and 50 %.
* One candidate (20260915) met three of the four conditions and missed only the
  absolute level.

NOT supported (no claim licensed by this run):
* No transfer claim for the targeted ^6 module. The pre-registered confirmation
  rule returned a negative.
* No claim that the run-005 `7/12` sealed result is wrong; it remains a
  single-seed result on a 12-case panel that had already been examined. What
  this run adds is that on a **new, balanced 90-case panel** (30 per operation,
  reach 10 direct / 10 via / 10 absent, 0 id and 0 signature overlap with
  everything previously seen) **the three newly trained candidates** reached
  37.78 %–40.00 %, not 58 %.
* No composition, specialist, or two-framing claim.

## Corrections to this record (owner-directed, 2026-09-10)

Two statements in the first version of this record needed correction. Both are
recorded here rather than edited away, so the error stays visible.

1. **"The same frozen candidate" was wrong wording.** The 37.78 %–40.00 %
   scores belong to the three **newly trained candidates** (seeds `20260913`,
   `20260914`, `20260915`), not to the run-005 checkpoint. Run 005's weights were
   never persisted (only the digest `cb008721…` survived), so the original
   checkpoint's fresh performance is **UNAVAILABLE, not disproved**. Asking for
   the checkpoint to be preserved did not establish that its bytes existed.
   GRAPH6_CURRICULUM_002 therefore writes and collects real checkpoint files.
2. **"Answers sealed before predictions" states less than it looks.** The
   recorded flag proves that the prediction pass received **no answer field**
   (the sealed input strips `correct`, `encoded_correct_index` and `reference`).
   It does **not**, by itself, prove that the answers were opened only after the
   predictions were written; the record has no independent event-ordering
   evidence. The honest statement is: predictions were produced from an
   answer-free input view, and correctness was computed in a second pass over the
   already-recorded predictions. The curriculum experiment keeps the same
   mechanism and records this limit explicitly in
   `claims.answer_sealing_limit`.

## Follow-on options (none authorized by this record)

1. **Curriculum for the demonstrated weakness** — the owner's already-specified
   direction (direct / through another part / not connected, with matched
   lessons and maintenance practice on the other two operations), now aimed at
   the measured fresh weakness: `LIST_PARTS` at chance and reach labels.
2. **Diagnose familiar-vs-fresh gap** — measure whether the gap is
   representation, option-readout, or the teaching set's coverage, on the same
   frozen candidate, before changing anything.
3. **Larger allowance / more updates** — a bounded, declared increase, judged
   against this exact panel.
4. **Accept the negative and proceed to the child-call integration** with the
   specialist's current, measured capability.

Each option needs its own pre-registration, its own owner GO and its own
reservation.
