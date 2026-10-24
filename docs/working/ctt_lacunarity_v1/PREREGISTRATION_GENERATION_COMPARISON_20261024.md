# Preregistration — generation-level comparison, step 1,000 vs step 6,000 (2026-10-24)

Status: **frozen before any reply is generated.** Companion to the checkpoint-selection result
(`CHECKPOINT_SELECTION_RESULT_20261024.md`). This is a separate, predeclared experiment. It does not change the frozen
c60 protocol, the exam, or any existing reading.

## 1. The question

The prediction-level result says step 1,000 beats step 6,000 on held-out next-token loss in three of three seeds.
Prediction loss is not reply quality. This experiment asks: **do the step-1,000 models write better replies than the
step-6,000 models, under the mouth's own frozen rules?**

## 2. Models and inputs

| Item | Value |
|---|---|
| Seeds | A4-s1, A4-s2, A4-s3 |
| Checkpoints per seed | `step_01000.pt` and `final.pt` (6,000) — 6 models |
| Inputs | `mouth_exam.jsonl`, 1,517 items, identical for every model |
| Decoding | the frozen mouth path: `mouth_task.sample.sample_locked`, top-p 0.9, per-item seed `sample.seed_of(input_text, situation, turn)`, whole-word lock, `max_len` as frozen |
| Instruction | none beyond the frozen situation and tone fields carried by each item |

Because the per-item seed depends only on the item, the two checkpoints see the same seed for the same input.

## 3. Primary metric (deterministic, no rater, no money)

For every generated reply, the frozen mouth rules are applied in order, and **every attempted item is counted**:

1. **guard pass** — `mouth_task.check` plus the lock re-check; a failure is recorded as a failure, never dropped.
2. **round-trip pass** — for replies that state a fact, the ear reads the reply back and must recover the same
   thing, value, month and old value.
3. **fact exactness** — every number and name in the reply must come from the input; an invented fact is a failure.

Primary composite, per model: `guard_pass_rate × roundtrip_pass_rate × fact_exact_rate`, with each rate computed
over all 1,517 items (failures included; a non-fact reply counts as a pass for round-trip, as the frozen reader does).

## 4. Decision rule

Step 1,000 counts as better at generation if, in **at least 2 of 3 seeds**:

- its composite is at least **0.02** higher than the final checkpoint's, **and**
- no component (guard, round-trip, fact) is worse by more than **0.01**.

Anything else is recorded as **no generation gain**, including a tie. A seed where the final checkpoint is better is
reported as such.

## 5. Secondary, optional, and separately authorised

AI raters (sounds-human, tone) on a random sample of 200 replies per model, shuffled with a fixed seed so raters
cannot tell which checkpoint produced a reply. **These are not part of the decision rule and cost money; they run
only if the owner authorises a rater budget.** If run, they are reported beside the primary result, never instead of
it.

## 6. Failure accounting

- Guard rejections, round-trip failures, invented facts and empty replies are all counted in the denominators.
- No item is excluded for being bad.
- The number of items attempted per model is reported; it must be 1,517 for every model.

## 7. What would justify changing the protocol

A protocol change (early stopping at 1,000) would be proposed only if the generation result agrees with the
prediction result: step 1,000 better on both, in at least 2 of 3 seeds. If prediction improves but generation does
not, or they disagree across seeds, the protocol stays as it is and the result is recorded as a negative.

Even a positive result establishes an advantage **for this configuration only** — model A4, this data, this mix,
these six seeds' order — not a universal stopping rule.

## 8. Status and cost

- Compute: local RTX 4070, **0 USD**. Generation is neural work, so the result is **diagnostic, not claim-bearing**
  until it is replicated on AWS.
- No rater budget is assumed. Nothing in this experiment touches the c60 result or its word (`MOUTH_NO_GAIN`).

## 9. Owner record

The owner's instruction of 2026-10-23 ("proceed with the generation-level comparison") is recorded in
`OWNER_APPROVAL_CHECKPOINT_SELECTION_20261023.json`; the rater leg remains unauthorised.
