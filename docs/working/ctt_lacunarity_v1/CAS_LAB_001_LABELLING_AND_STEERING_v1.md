# CAS-LAB-001 — Structural labelling and bounded cell steering, v1 (2026-10-24)

Status: **first build + first probe.** Diagnostic, local GPU, weights frozen. Not claim-bearing. This starts from the
owner's direction: read the books and the Harness record, then build for labelling RPM and recipes and for
steering/influencing/controlling the cells.

## 1. What the books and the Harness record actually say

| Source | What it supplies | What it does not supply |
|---|---|---|
| CAS PCBA Engineer (feedback, gain, CMB) | the control picture: compare intended and actual behaviour, adjust a bounded next state; addressed memory cells with read/write paths | a numeric update rule for neural parameters |
| Thinking in Cognitive Architecture (fractal learning) | diagnose the missing capability, prescribe a targeted exercise; simplex-based learning exists | a mapping from a failed task to a parameter |
| Reality Engineering (RPM) | find the lowest critical unsatisfied prerequisite, test a targeted intervention, record the outcome | a universal repair rule |
| Harness spec sheet (`docs/CAS_HARNESS_SPEC_SHEET.md`) | read (probes on hidden states), prove cause (knock-outs against matched random controls), correct (ε-prefix conditioning), record (evidence packets) | CAS-specificity is `GREY`; **no `ACCEPT` stands anywhere**; surface-text steering "was not yet closed" |

The consistent message: reading is evidenced, steering is the open bridge, and every causal claim needs a matched
random control.

## 2. What was built

### 2.1 Labeller (`lacunarity_e1/cas_label.py`, schema `cas-label-v1`)

For each row it writes: the cells (`^n^D`), the Noetics, the operators, a recipe entry, and an RPM entry.

- **Recipe:** one ingredient per declared cell at requirement `1.0`, marked `coefficient_source: "design_value"`
  because the RPU Recipe's own coefficients are design values, not measurements. `Y_T` and `limiting` are `null` with a
  reason, because no state vector `x_i` is supplied for a row. The labeller never invents a coefficient.
- **RPM:** a chain is written only when the source text really contains `stageA0/stageD/stageW/stageP` names. Every
  other row is `not_applicable` with a reason. It never guesses a prerequisite.

Result: `data/labels_notation.jsonl` (600 rows, all with cells, 0 unpaired), and `data/labels_rpm_sample.jsonl`
(100 RPM-chain rows, all with a chain **and** cells parsed from the source). Example chain: `["A0","D5","W5","P5"]`.

### 2.2 Bounded steering (`lacunarity_e1/cell_steer.py`)

Inference only; weights are frozen. For a cell `c`:

1. Encode each held-out row; mean-pool the encoder memory over real tokens into one vector per row.
2. Build the direction `v_c` = mean(memory of rows with `c`) − mean(memory of rows without `c`), unit-normalised.
3. Add `α · ‖h‖ · v_c` to the memory of confirmation rows and re-score teacher-forced error.
4. **Control:** the same added magnitude along a random unit vector, seeded from `sha256(c)` so the run is
   reproducible.
5. **Leakage guard:** the direction is built from the discovery half of the cell's rows and scored on the other half.

## 3. First probe — 30 cells, A4-s1 step 1,000, 600 held-out rows

At `α = 1.0`, counting a cell only when the change exceeds 0.01 and beats the random control:

| Outcome | Cells | Examples (baseline → steered, random) |
|---|---|---|
| **Helps and beats random** | **8** | `^2^C` 1.4084 → −0.3800 (random +0.1741); `^8^O` 1.5745 → −0.1745 (random +0.5806); `^8^P` 1.7080 → −0.2271 (random +0.0092); `^3^P` 2.2758 → −0.2019 (random +0.0985); `^2^O`, `^1^C`, `^1^O`, `^7^O` smaller |
| **Hurts and is worse than random** | **14** | `^0^E` 1.6948 → +0.7000 (random −0.0597); `^5^O` 1.9343 → +0.4177 (random −0.0702); `^0^C`, `^3^C`, `^4^E`, `^4^O`, `^5^C`, `^5^P`, `^6^C`, `^6^E`, `^6^P`, `^7^P`, `^2^E`, `^3^E` |
| Neither | 8 | mixed or below the 0.01 bar |

**Reading, stated plainly:** a direction built from the model's own memory is causally load-bearing for some cells —
it lowers held-out error by up to 0.38 on `^2^C` while the matched random direction raises it — but the effect is
**not uniform**: on 14 of 30 cells the same procedure makes error worse than doing nothing, and worse than random.

That is exactly why the steering question is not "does steering work" but "which cells can be steered, and can that be
known before intervening".

## 4. Limits, stated now

- Confirmation sets are 12–33 rows per cell, so a single cell's number is noisy. No intervals yet.
- One model, one seed, one checkpoint (A4-s1 step 1,000), one data source (`notation_new100`).
- The direction is a mean difference, not a fitted probe; a better estimator may move the boundary.
- Teacher-forced error is not the generation composite. A cell that improves NLL may not write better replies.
- Nothing here tests weight updates; this is inference-time influence only.

## 5. The confirmation protocol (next, predeclared before running)

1. **Selection on discovery only:** choose cells whose discovery-half gain is positive and beats random. Freeze the
   list before confirmation.
2. **Confirmation:** score those cells on the untouched half; report per-cell deltas with bootstrap intervals over
   rows, per seed.
3. **Success bar:** the selected set must improve on confirmation in at least 2 of 3 seeds, and must not be worse than
   the random control in any seed.
4. **Generation guard:** run the 300-item generation composite for the best single cell and for the selected set; a
   fall of more than 0.02 fails the run regardless of the NLL gain.
5. Only then consider a recipe/RPM-guided version, where the choice of cell comes from the structural label rather
   than from the discovery gain.

## 6. Artifacts

- `lacunarity_e1/cas_label.py`, `cell_steer.py`.
- `lacunarity_e1/data/labels_notation.jsonl` (600), `data/labels_rpm_sample.jsonl` (100).
- `cs_aws/steer_results.jsonl` (30 cells × 3 alphas, steered and random).
