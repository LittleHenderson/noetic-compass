# Stage 27L Calibrated Eraser Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27K showed that fixed eraser suppression is the strongest output-side steering channel, but the combined fixed intervention did not pass row-consistency gates. Stage 27L calibrates the eraser gain on the Stage 27J learn split, then evaluates global and drive-calibrated eraser suppression on held-out rows against matched random covers.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_prefix_report`: `stage7_cas_prefix_likelihood_20260517.json`
- `stage27j_report`: `stage27j_output_side_component_attribution_20260521.json`
- `stage27k_report`: `stage27k_output_side_component_steering_20260521.json`
- `stage7_prefix_status`: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- `stage27j_status`: `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`
- `stage27k_status`: `GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL`
- `calibration_rows`: `Stage 27J learn split`
- `evaluation_rows`: `Stage 27J held-out eval split`
- `eraser_scale_grid`: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- `calibration_modes`: `['global', 'drive_calibrated']`
- `intervention_positions`: `continuation_prediction_positions_only`
- `random_control_policy`: `same calibrated gain(s) applied to matched random eraser covers`

## Method

1. Commit this pre-registration and runner before any Stage 27L GPU result is generated.
2. Verify Stage 7 readable-prefix PASS, Stage 27J output-side attribution PASS, and Stage 27K grey steering source contracts.
3. Load the Stage 27J eraser cover; do not relearn the cover in Stage 27L.
4. Recreate the Stage 27J learn/eval split deterministically.
5. On learn rows, choose one global eraser scale from the fixed scale grid by maximum mean margin increment.
6. On learn rows, choose one eraser scale per Foundation drive from the same fixed grid by maximum mean margin increment within that drive.
7. Evaluate global-calibrated and drive-calibrated eraser suppression on held-out rows only.
8. Compare held-out increments against matched random eraser covers using the same calibrated global or per-drive gains.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 7 readable-prefix PASS, Stage 27J PASS, and Stage 27K GREY source contracts are verified. |
| `learn_eval_split` | `pass_floor` | Gain calibration uses only Stage 27J learn rows, and evaluation uses only Stage 27J held-out rows. |
| `global_calibrated_eval` | `primary` | Global calibrated eraser suppression beats matched random eraser suppression on at least 60% of held-out rows with sign-test p<0.05. |
| `drive_calibrated_eval` | `primary` | Drive-calibrated eraser suppression beats matched random eraser suppression on at least 60% of held-out rows with sign-test p<0.05. |
| `positive_effect_floor` | `primary` | Passing calibrated mode must have positive mean increment and positive increment share at least 55%. |

## Claim Boundary

Stage 27L is bounded calibrated eraser-cover intervention over Pythia-160M CPL2 likelihood margins. It is not weight editing, not complete circuit discovery, not model-wide control, not cross-model control, and not visible free-form generation control.

## Forbidden Claims

Do not claim complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, cross-model steering, or raw CAS-symbol understanding from Stage 27L.

## Validation

`{}`
