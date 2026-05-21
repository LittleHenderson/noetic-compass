# Stage 27M Robust Calibrated Eraser Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27L established calibrated eraser-cover likelihood steering on 56 held-out rows. Stage 27M tests whether that capability survives a larger 245-row held-out robustness split using the same cover, same fixed scale grid, and matched random eraser-cover controls.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `fixture_rows`: `4368`
- `fixture_rows_per_drive`: `624`
- `stage7_prefix_report`: `stage7_cas_prefix_likelihood_20260517.json`
- `stage27j_report`: `stage27j_output_side_component_attribution_20260521.json`
- `stage27l_report`: `stage27l_calibrated_eraser_steering_20260521.json`
- `stage7_prefix_status`: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- `stage27j_status`: `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`
- `stage27l_status`: `PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING`
- `per_drive`: `70`
- `learn_rows_per_drive`: `35`
- `eval_rows_per_drive`: `35`
- `held_out_eval_rows`: `245`
- `selection_seed`: `27040`
- `eraser_scale_grid`: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- `calibration_modes`: `['global', 'drive_calibrated']`
- `intervention_positions`: `continuation_prediction_positions_only`
- `random_control_policy`: `same calibrated gain(s) applied to matched random eraser covers`

## Method

1. Commit this pre-registration and runner before any Stage 27M GPU result is generated.
2. Verify Stage 7 readable-prefix PASS, Stage 27J output-side attribution PASS, and Stage 27L calibrated-steering PASS source contracts.
3. Use the Stage 27J eraser cover; do not relearn the cover in Stage 27M.
4. Select 70 rows per Foundation drive from the Stage 7 CPL2-eligible test fixture using seed 27040.
5. Split the selected rows into 35 learn rows and 35 held-out eval rows per drive.
6. On learn rows, choose one global eraser scale from the fixed scale grid by maximum mean margin increment.
7. On learn rows, choose one eraser scale per Foundation drive from the same fixed grid by maximum mean margin increment within that drive.
8. Evaluate global-calibrated and drive-calibrated eraser suppression on the 245 held-out rows only.
9. Compare held-out increments against matched random eraser covers using the same calibrated global or per-drive gains.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 7 readable-prefix PASS, Stage 27J PASS, and Stage 27L PASS source contracts are verified. |
| `robust_split` | `pass_floor` | Evaluation uses exactly 245 held-out rows, with 35 held-out rows per drive and no overlap with calibration rows. |
| `global_robust_eval` | `primary` | Global calibrated eraser suppression beats matched random eraser suppression on at least 60% of 245 held-out rows with sign-test p<0.05. |
| `drive_robust_eval` | `primary` | Drive-calibrated eraser suppression beats matched random eraser suppression on at least 60% of 245 held-out rows with sign-test p<0.05. |
| `positive_effect_floor` | `primary` | Passing robust mode must have positive mean increment and positive increment share at least 55%. |

## Claim Boundary

Stage 27M is bounded larger-sample robustness evidence for calibrated eraser-cover intervention over Pythia-160M CPL2 likelihood margins. It is not weight editing, not complete circuit discovery, not model-wide control, not cross-model control, and not visible free-form generation control.

## Forbidden Claims

Do not claim complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, cross-model steering, or raw CAS-symbol understanding from Stage 27M.

## Validation

`{}`
