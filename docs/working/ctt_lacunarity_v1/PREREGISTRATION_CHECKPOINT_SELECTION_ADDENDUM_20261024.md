# Addendum to the checkpoint-selection preregistration (2026-10-24)

Status: **written before any selection or report result on the replacement split was computed.** It records an
instrument problem and fixes a replacement. The original preregistration stays on file, unedited.

## 1. The instrument problem

The preregistration named `mouth_exam.jsonl` (1,517 rows) as the sealed report split. That file **has no gold reply
text**. Its fields are: `fact_id, form, id, input_key, input_text, profession, reading, situation, split, style,
tone, world_index`. There is no `target`.

Consequence: the metric the experiment uses — teacher-forced mean token NLL — **cannot be computed** on that split.
The attempt failed for all 18 checkpoints with `KeyError: 'target'`. The c60 mouth exam scored *generated replies*
against a guard and AI raters, not teacher-forced likelihood; that machinery is not what this experiment needs.

The failure is recorded, not hidden. The exam split is unusable for this experiment.

## 2. The replacement split (fixed now)

Without new training, the only gold-reply data with per-row scores already computed is `mouth_dev.jsonl` (2,097 rows;
`score_*.json` carry per-row means for all 18 checkpoints). It is split deterministically by row position:

| Split | Rows | Role |
|---|---|---|
| **even indices** (0, 2, 4, …) | 1,049 | selection only |
| **odd indices** (1, 3, 5, …) | 1,048 | report only |

The split is by position in the frozen file, fixed before any aggregate on either half was computed. Selection and
report never share a row.

## 3. What weakens, honestly

- The report set is now a held-out **half of the same dev distribution**, not a sealed exam drawn from a different
  frame. It guards against fitting the selection to noise, but not against a dev-vs-real distribution shift.
- Two halves are not independent of each other in the way a sealed exam would be.
- The result therefore stays **diagnostic, not claim-bearing**, exactly as the original status said.

## 4. Decision rule (unchanged)

`SELECTED` (best even-half NLL among the six checkpoints) must beat `FINAL` on the odd half by at least **0.05 NLL**
in at least **2 of 3 seeds**. Anything less is recorded as no gain. `EARLY` (step 1,000 fixed) and `ORACLE` (best odd
half, upper bound only) are reported alongside; neither counts toward the decision.

## 5. Cost

No new compute. The per-row scores already exist; this addendum costs nothing.
