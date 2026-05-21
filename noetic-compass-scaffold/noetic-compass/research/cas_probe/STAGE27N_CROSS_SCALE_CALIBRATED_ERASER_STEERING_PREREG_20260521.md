# Stage 27N Cross-Scale Calibrated Eraser Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_REQUIRED`

## Motivation

Stage 27M established robust calibrated output-side eraser steering on Pythia-160M. Stage 27N tests whether the method transfers across scale to Pythia-1B with model-specific output-side covers and the same held-out calibration discipline.

## Required Inputs

- `model`: `EleutherAI/pythia-1b`
- `model_revision`: `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `fixture_rows`: `4368`
- `fixture_rows_per_drive`: `624`
- `stage8_cpl2_report`: `STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json`
- `stage8_manifest`: `stage8_pythia1b_activations_manifest_20260517.json`
- `stage27m_report`: `stage27m_robust_calibrated_eraser_steering_20260521.json`
- `stage8_cpl2_status`: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`
- `stage27m_status`: `PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING`
- `candidate_layers`: `[12, 13, 14, 15]`
- `candidate_heads`: `read from model.config.num_attention_heads`
- `cover_size`: `6`
- `per_drive`: `16`
- `learn_rows_per_drive`: `8`
- `eval_rows_per_drive`: `8`
- `held_out_eval_rows`: `56`
- `selection_seed`: `27041`
- `eraser_scale_grid`: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- `n_random_covers`: `8`
- `calibration_modes`: `['global', 'drive_calibrated']`
- `intervention_positions`: `continuation_prediction_positions_only`
- `random_control_policy`: `same calibrated gain(s) applied to matched random Pythia-1B eraser covers`

## Method

1. Commit this pre-registration, runner, and tests before any Stage 27N GPU result is generated.
2. Verify Stage 8 Pythia-1B CPL2 PASS and Stage 27M Pythia-160M robust calibrated-steering PASS source contracts.
3. Load EleutherAI/pythia-1b at revision f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2, or mark the result diagnostic-only if the loaded revision does not match.
4. Select 16 CPL2-eligible hard-partner rows per Foundation drive from the Stage 7 fixture using seed 27041.
5. Split the selected rows into 8 learn rows and 8 held-out eval rows per drive.
6. Enumerate Pythia-1B output-side candidate components over layers 12-15: every attention head plus one MLP block per layer.
7. Learn model-specific carrier and eraser covers on the learn rows only; do not reuse Pythia-160M component identities.
8. Choose one global eraser scale and one per-drive eraser scale from the fixed grid by maximum learn-row mean margin increment.
9. Evaluate global-calibrated and drive-calibrated eraser suppression on the 56 held-out rows only.
10. Compare held-out increments against matched random Pythia-1B eraser covers using the same calibrated global or per-drive gains.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 8 Pythia-1B CPL2 PASS and Stage 27M Pythia-160M robust calibrated-steering PASS source contracts are verified. |
| `model_revision` | `pass_floor` | The loaded Pythia-1B causal LM revision matches f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2. |
| `cross_scale_split` | `pass_floor` | Evaluation uses exactly 56 held-out rows, with 8 held-out rows per drive and no overlap with calibration rows. |
| `global_cross_scale_eval` | `primary` | Global calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05. |
| `drive_cross_scale_eval` | `primary` | Drive-calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05. |
| `positive_effect_floor` | `primary` | Passing cross-scale mode must have positive mean increment and positive increment share at least 55%. |

## Claim Boundary

Stage 27N is bounded cross-scale evidence for calibrated output-side eraser-cover intervention over Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not complete circuit discovery, not model-wide control, and not visible free-form generation control.

## Forbidden Claims

Do not claim cross-architecture steering, complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, or raw CAS-symbol understanding from Stage 27N.

## Validation

`{}`
