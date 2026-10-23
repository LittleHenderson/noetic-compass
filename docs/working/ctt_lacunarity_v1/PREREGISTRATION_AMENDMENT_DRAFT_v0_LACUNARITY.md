# Preregistration amendment draft v0 — lacunarity instrumentation and two bounded arms (CTT)

Status: **DRAFT. NOT APPROVED. NOTHING RUN.** This file is a proposal for the owner's signature. Until a signed
copy exists beside it, no code changes and no GPU job may follow from it. Companion: `LACUNARITY_CTT_DESIGN_v1.md`.

Base preregistration: `Documents/Codex/2026-10-19/cas_token_transformer/PREREGISTRATION_CTT.md` (sha256 recorded
there). This amendment adds measurement and two optional arms; it changes no existing gate, threshold, exam, data,
vocabulary, decoder lock or reading rule.

---

## 1. What is being added

| Step | What | Behaviour change | Cost |
|---|---|---|---|
| E1 | Error-field lacunarity logging (`lacunarity.jsonl`) on an ordinary A4 run | none (logging only) | 0 USD |
| E2 | Global multiplier arm, `λ=1`, `g=2` | LR path changes; nothing else | ≈ 0.6 USD |
| E3 | Per-block damping arm, `λ=0.5`, `g=1.5` | per-block LR changes | ≈ 0.6 USD |

E2 is a **null control**: its preregistered expectation is "no exam gain". E1 gates E2 and E3.

## 2. Frozen before code

- Boxes: `{4, 16, 64}` tokens for the error field; `{2}` for the block field (7 blocks).
- Normalisation: `L̃ = clip((L − 1)/(L_ref − 1), 0, 1)`, `L_ref` = median `L(16)` at epoch 7 from E1, rounded to
  four decimals and written into the amendment's signed copy before E2 starts.
- Slow EMA half-life: 500 steps. Ramp-in: over the existing 1000 warmup steps.
- Bounds: `g = 2.0` (E2), `g = 1.5` (E3). Signs: `λ = +1.0` (E2), `λ = +0.5` (E3) with the prior that high-lacunarity
  blocks are damped.
- Seeds: the three frozen A4 seeds (`A4-s1`, `A4-s2`, `A4-s3`). No seed shopping.
- Data, vocabulary, exam, reader, locks: unchanged, byte-identical to c45.
- Checkpoint scored: `final`. Early stopping: none. Same 12 epochs, batch 256, AdamW `lr=5e-4`, `wd=0.01`,
  `clip=1.0`, `dropout=0.1`, fp32.

## 3. Predictions (falsifiable, written before any run)

E1:
- P1. `L_loss(16) ≤ 1.05` by epoch 3 on an A4-shaped run.
- P2. `L_loss(16)` within 0.02 of 1.0 by epoch 7.
- If P1 and P2 both hold, E2/E3 are **not launched**: the dynamic field is uniform and the step-size idea has
  nothing to act on. This is the expected result.

E2 (only if E1 keeps the field live):
- P3. Primary exam right count within 105–107 (the c45 A4 spread).
- P4. Training loss ≤ 1e-4 and validation at epoch 11 within ±0.001 of 0.00815.
- Expected word: `NO_GAIN`.

E3 (only after E2 reports):
- P5. Either validation loss ≥ 5% lower at the same step budget, or primary exam exact +≥ 3 licensed sentences over
  the A4 median of 106, with `H-CWFW ≤ 2` still true.
- Expected word: `NO_GAIN` (prior), `GAIN` if P5 holds.

## 4. Decision rules

- Every reading comes from the frozen reader `ctt_score/merge_ctt.py`, exactly as in c45. The runner's exit code is
  never the verdict.
- A word requires every hard gate. `H-CWFW` cap stays 2 and must not exceed the retrieval rival's count.
- Reporting is per seed; the best seed is never reported alone. A single seed above the band is noise, not a gain.
- A failed gate is a failure, never "pass with caveats".
- Any E2/E3 outcome is recorded as a negative result if it fails; the file is never deleted.

## 5. Budget

- Measured basis: the whole c45 run (6 models, 3 × A4) cost **1.40 USD** of an 8.00 USD cap; 7.79 USD remained
  before it (`RUN_RESULT_CTT1_C45.md`).
- E2 and E3 are 3 seeds each at A4 shapes and epochs: **≈ 0.6 USD per arm**, ≈ 1.2 USD for both.
- Cap for this amendment: **2.00 USD**, one attempt per arm plus one plumbing retry, no extension without a new
  owner line.
- Compute: AWS GPU only (A10G class or smaller), `GPU_REQUIRED` fails closed; no CPU fallback. Job record must name
  instance, wall clock, cost and cleanup, per the standing owner order.

## 6. Instrument rules (unchanged, restated so they bind here)

- The translator's write-audit stays as fixed by amendment A-CTT-2. The new artefact `lacunarity.jsonl` is written
  inside the run's own output folder only.
- Every new file's sha256 is recorded in `WEIGHTS_MANIFEST.json` or a sibling manifest.
- Test counts are recorded; the 14 estimator tests in `test_lacunarity.py` run on the host before training.
- `progress.jsonl` schema is not modified. Existing readers must keep working unmodified.

## 7. What would make us abandon this line

- E1 shows the field uniform early (expected) → abandon the optimiser use; keep the instrumentation.
- E2/E3 produce no change beyond the seed spread → record the null, do not extend to more seeds.
- Any arm fails a safety gate → the arm is a failure regardless of its score.
- Any result depends on a box size chosen after the fact → the result is void.

## 8. Owner approval (to be signed; blank until then)

```
I approve this amendment as written, including the 2.00 USD cap.

signature: ______________________     date: ____________
```

No signature, no run. This draft licenses nothing by itself.
