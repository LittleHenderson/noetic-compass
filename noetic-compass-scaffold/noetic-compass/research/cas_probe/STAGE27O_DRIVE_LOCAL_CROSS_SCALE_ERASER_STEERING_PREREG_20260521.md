# Stage 27O Drive-Local Cross-Scale Eraser Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_REQUIRED`

## Motivation

Stage 27N showed positive mean Pythia-1B eraser steering but failed row-consistency against matched random controls. Stage 27O tests the most direct fix: learn and calibrate separate output-side eraser covers per Foundation drive.

## Required Inputs

- `model`: `EleutherAI/pythia-1b`
- `model_revision`: `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage8_cpl2_report`: `STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json`
- `stage8_manifest`: `stage8_pythia1b_activations_manifest_20260517.json`
- `stage27n_report`: `stage27n_cross_scale_calibrated_eraser_steering_20260521.json`
- `stage8_cpl2_status`: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`
- `stage27n_status`: `GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL`
- `stage27n_failure_mode`: `positive mean lift but insufficient row-consistency against random controls`
- `candidate_layers`: `[12, 13, 14, 15]`
- `candidate_heads`: `read from model.config.num_attention_heads`
- `cover_size_per_drive`: `6`
- `per_drive`: `16`
- `learn_rows_per_drive`: `8`
- `eval_rows_per_drive`: `8`
- `held_out_eval_rows`: `56`
- `selection_seed`: `27041`
- `eraser_scale_grid`: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- `n_random_covers_per_drive`: `8`
- `intervention_positions`: `continuation_prediction_positions_only`
- `random_control_policy`: `each drive-local eraser cover compared against matched random covers for the same drive and same selected scale`

## Method

1. Commit this pre-registration, runner, and tests before any Stage 27O GPU result is generated.
2. Verify Stage 8 Pythia-1B CPL2 PASS and Stage 27N GREY source contracts.
3. Use the same Stage 27N Pythia-1B selection seed and learn/eval split to isolate cover granularity as the changed variable.
4. Enumerate the same Pythia-1B output-side candidate components over layers 12-15.
5. For each Foundation drive, learn a separate eraser cover on that drive's 8 learn rows only.
6. For each Foundation drive, choose one eraser scale from the fixed grid by maximum mean margin increment on that drive's learn rows.
7. Evaluate each drive-local cover only on held-out rows from its matching drive.
8. Compare held-out increments against matched random covers sampled separately for each drive-local cover.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 8 Pythia-1B CPL2 PASS and Stage 27N GREY-positive source contracts are verified. |
| `model_revision` | `pass_floor` | The loaded Pythia-1B causal LM revision matches f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2. |
| `drive_local_cover_contract` | `pass_floor` | All seven Foundation drives produce exactly six learned eraser components from learn rows only. |
| `controlled_split` | `pass_floor` | Evaluation uses the Stage 27N split: exactly 56 held-out rows, 8 held-out rows per drive, and no learn/eval overlap. |
| `drive_local_eval` | `primary` | Drive-local calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05. |
| `positive_effect_floor` | `primary` | Passing drive-local mode must have positive mean increment and positive increment share at least 55%. |

## Claim Boundary

Stage 27O is bounded cross-scale evidence for drive-local calibrated output-side eraser-cover intervention over Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not complete circuit discovery, not model-wide control, and not visible free-form generation control.

## Forbidden Claims

Do not claim cross-architecture steering, complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, raw CAS-symbol understanding, or universal Pythia-1B control from Stage 27O.

## Validation

`{}`
