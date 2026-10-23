# Preregistration — checkpoint selection for the mouth (authorised 2026-10-23)

Status: **authorised by the owner and frozen before any selection result exists.** Companion approval:
`OWNER_APPROVAL_CHECKPOINT_SELECTION_20261023.json`. The frozen c60 result and its protocol are untouched.

## 1. The question

Does choosing a checkpoint by held-out validation score, then reporting on a sealed exam, beat always taking the final
checkpoint? The E1 diagnostic suggested yes for one seed; this decides it across three seeds and on data never used for
selection.

## 2. Splits (fixed before the run)

| Split | Rows | Role |
|---|---|---|
| `mouth_dev.jsonl` | 2,097 | **selection only** — the checkpoint with the lowest mean token NLL here is "SELECTED" |
| `mouth_exam.jsonl` | 1,517 | **sealed report** — never read for selection |

Leakage guard: the exam is opened exactly once per checkpoint, after selection is fixed. If the seal is broken, the
experiment is void.

## 3. Runs

Three seeds, model A4 (9,585,823 parameters), frozen training (6,000 steps, batch 256 split into micro-batches of 64
with gradient accumulation, cosine to 0, same data and mix), order seed **3855894630296892324** for all three — the
order the c60 runs used (read from the c60 `WEIGHTS_MANIFEST.json` files).

Checkpoints saved at steps 1,000, 2,000, 3,000, 4,000, 5,000 and 6,000.

Note, on the record: the earlier E1 run used order seed `1423595301575908809` (from the older c59 run). It remains a
valid diagnostic and is kept, but it is **superseded for this experiment**; seed 1 is rerun with the correct order.

## 4. Arms compared (per seed)

| Arm | Checkpoint | Chosen using |
|---|---|---|
| FINAL | step 6,000 | the frozen rule (baseline) |
| EARLY | step 1,000 | fixed a priori |
| SELECTED | best mean dev NLL among the six | `mouth_dev` only |
| ORACLE | best mean exam NLL among the six | reported as an upper bound only, never as a result |

## 5. Metric and decision rule

Metric: mean token NLL on the exam, teacher-forced, PAD masked, identical script for every checkpoint.

**Preregistered decision:** the experiment counts as "selection helps" if, on the exam, `SELECTED` beats `FINAL` by at
least **0.05 NLL** in at least **2 of 3 seeds**. Anything less is recorded as no gain, including a tie or a reversal.
Secondary, reported but not decisive: the share of exam rows where the selected checkpoint is worse than final, and the
per-seed spread.

## 6. Cost and status

- Compute: the laptop RTX 4070, **0 USD**. Each seed is one 6,000-step run (~45–90 minutes, resumable every 250 steps
  after the machine's power resets).
- Claim status: **diagnostic, not claim-bearing** under the standing AWS rule. A positive result stays `PROPOSED` until
  it is replicated on AWS within a separately authorised cap.
- Nothing here changes the c60 result, its exam or its word (`MOUTH_NO_GAIN`).

## 7. What would make this experiment void

- The exam being read before selection is fixed.
- A run that did not reach 6,000 steps (a partial run can be a diagnostic but not an arm).
- Selecting a checkpoint on anything other than mean dev NLL.
- Reporting the best seed alone.

## 8. Owner record

> I authorise a checkpoint-selection experiment.

Given 2026-10-23 in the DSH session; recorded by the operator because the owner writes nothing. New money authorised:
0.00 USD.
