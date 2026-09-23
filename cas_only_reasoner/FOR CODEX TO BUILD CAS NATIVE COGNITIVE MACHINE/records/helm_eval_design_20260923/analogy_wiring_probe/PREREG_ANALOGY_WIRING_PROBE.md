# Analogy wiring probe: rules fixed before any run

- **Owner of this probe:** Claude (independent checker).
- **Written:** 2026-09-23, before the probe was first executed.
- **What it asks:** "Changing the arrangement Helm is asked to compare can now affect the relevant answer
  scores." This comes from the owner's coordination note of 2026-09-23. It is a WIRING question. It is not
  a question about getting answers right. Correct answers on new examples are a later, separate test.

## What is measured

The probe checks every `analogy` record in the frozen course. The frozen course is `pointer_contract`, with
course digest `272c26e1...`. The probe reads the score row of the record's world-choice slot (`field ==
"world_id"`), one score per candidate world. A "non-focus candidate" is any candidate world other than the
record's focus world.

- **M1 (witness pair).** These are the two records Codex's judge A7 used:
  - `typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e`;
  - `typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a`.

  M1 is the maximum absolute score difference over the candidates that are non-focus in BOTH records.
- **M2 (focus-independence over all analogy records).** Take each candidate world. Collect the scores it
  receives across all analogy records in which it is a non-focus candidate. Take the spread (max - min). M2 is
  the largest spread over all candidates.
- **M3 (controlled rewiring of the focus world).** This one changes ONLY the focus world's `contains` list,
  inside the model's reading. Nothing else changes: not the node count, the node order, the declarations,
  the flags or the other worlds. The new arrangement is every other contains-shape that has the same node
  count in the bank, relabelled onto the focus world's nodes, excluding the focus's own shape. For each
  record, the probe keeps the maximum over rewirings of the maximum absolute non-focus score change. M3 is the
  per-record list of those values.
- **Also reported, NOT used by the verdict:**
  - how many rewirings change the top-1 candidate;
  - the focus candidate's own score change;
  - timings and GPU telemetry.

## Verdict rules (fixed now)

- `tau_zero = 1e-6` (logit units).
- `tau_present = 1e-4`.

| Verdict | Condition |
|---|---|
| `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` | M1 <= tau_zero AND M2 <= tau_zero AND every M3 value <= tau_zero |
| `FOCUS_TO_CANDIDATE_DEPENDENCY_PRESENT` | M1 > tau_present AND at least 90% of analogy records have M3 > tau_present |
| `MIXED` | anything else |

## Models the probe is run on

- **Before-reading (unchanged Helm 2.0-experimental).** This is source `20208c923d41c24614504d4ecc2b289ecb66eda8`.
  The `research/CAS_META_2_COMPOSITION/cas_meta2` tree at the probe's commit was verified identical to it.
  1. Three freshly built containers, framework seeds 20260917, 20260918 and 20260919.
  2. The saved `initial.pt` and `final.pt` of `receipt_20260917`, `receipt_20260918` and `receipt_20260919`,
     loaded with `strict=True`.
- **Predicted before-reading:** `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` on all nine models.
  - Why: in `GraphForward._world_scores` the candidate term is `[query-key . candidate, query-value .
    candidate, is_focus, is_target, 0, 0, candidate declaration]`.
  - For an analogy query, which names no node, nothing in that term depends on the focus world. The only
    exception is the focus candidate's own flag and its own world vector.
  - If the prediction FAILS, the prediction is wrong and is reported as wrong. It is not re-read.
- **After-reading (Codex's repair).** The same probe, unchanged, is run on the repaired container with its
  switch ON, at the same seeds. It is also run with the switch OFF, which must reproduce the before-reading
  exactly. The repair passes the wiring check only if:
  - the switch-ON reading is `FOCUS_TO_CANDIDATE_DEPENDENCY_PRESENT` on fresh containers;
  - the switch-OFF reading is identical to the before-reading.

## Limits of this job (current authorization: `docs/OWNER_RUN_AUTHORIZATION_20260922.md`)

- **Device:** the local RTX 4070 laptop GPU. Every script exits `GPU_REQUIRED` if CUDA is absent. There is
  no CPU fallback.
- **Work:** forward passes only, under `torch.no_grad()`. No optimizer. No update. No checkpoint is written.
- **Admission:** the GPU is at or below 75 C and has at least 2,048 MiB free.
- **Stops:** the run stops if the GPU reaches 80 C, or when the wall limit of 900 s per invocation is
  reached. There are no automatic retries.
- **Data:** only the frozen course's public packets (the model's own inputs) are read. The probe opens no
  sealed file, no eval split and no answer key. It needs no gold answers.
- **Cost and scope:** no cloud and no spending. Outputs are written only under this folder.
