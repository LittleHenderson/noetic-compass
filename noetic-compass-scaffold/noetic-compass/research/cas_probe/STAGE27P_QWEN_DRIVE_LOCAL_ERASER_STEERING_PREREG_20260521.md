# Stage 27P Qwen Drive-Local Eraser Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_REQUIRED`

## Motivation

Stage 27O showed that drive-local output-side eraser covers solve Pythia-1B cross-scale steering. Stage 27P tests the same drive-local method on Qwen2.5-1.5B after Stage 27P-A validated the Qwen hook adapter.

## Required Inputs

- `model`: `Qwen/Qwen2.5-1.5B`
- `model_revision`: `8faed761d45a263340a0528343f099c05c9a4323`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage16_cpl2_report`: `STAGE16_QWEN15B_CPL2_REPORT_20260519.json`
- `stage16_manifest`: `stage16_qwen15b_activations_manifest_20260519.json`
- `stage27o_report`: `stage27o_drive_local_cross_scale_eraser_steering_20260521.json`
- `stage27pa_report`: `stage27p_qwen_hook_adapter_preflight_20260521.json`
- `stage16_cpl2_status`: `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`
- `stage27o_status`: `PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING`
- `stage27pa_status`: `PASS_QWEN_HOOK_ADAPTER_PREFLIGHT`
- `candidate_layers`: `[24, 25, 26, 27]`
- `cover_size_per_drive`: `6`
- `per_drive`: `16`
- `learn_rows_per_drive`: `8`
- `eval_rows_per_drive`: `8`
- `held_out_eval_rows`: `56`
- `selection_seed`: `27043`
- `eraser_scale_grid`: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- `n_random_covers_per_drive`: `8`
- `intervention_positions`: `continuation_prediction_positions_only`
- `random_control_policy`: `each Qwen drive-local eraser cover compared against matched random covers for the same drive and same selected scale`

## Method

1. Commit this pre-registration, runner, and tests before any Stage 27P GPU result is generated.
2. Verify Stage 16 Qwen CPL2 PASS, Stage 27O Pythia drive-local PASS, and Stage 27P-A Qwen hook-adapter PASS source contracts.
3. Load Qwen/Qwen2.5-1.5B at revision 8faed761d45a263340a0528343f099c05c9a4323.
4. Select 16 CPL2-eligible hard-partner rows per Foundation drive from the Stage 7 fixture using seed 27043.
5. Split the selected rows into 8 learn rows and 8 held-out eval rows per drive.
6. Enumerate Qwen output-side candidate components over layers 24-27: every attention head plus one MLP block per layer.
7. For each Foundation drive, learn a separate Qwen eraser cover on that drive's 8 learn rows only.
8. For each Foundation drive, choose one eraser scale from the fixed grid by maximum mean margin increment on that drive's learn rows.
9. Evaluate each drive-local cover only on held-out rows from its matching drive.
10. Compare held-out increments against matched random covers sampled separately for each drive-local cover.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 16 Qwen CPL2 PASS, Stage 27O Pythia-1B PASS, and Stage 27P-A Qwen adapter PASS source contracts are verified. |
| `model_revision` | `pass_floor` | Loaded Qwen model revision matches 8faed761d45a263340a0528343f099c05c9a4323. |
| `drive_local_cover_contract` | `pass_floor` | All seven Foundation drives produce exactly six learned Qwen eraser components from learn rows only. |
| `controlled_split` | `pass_floor` | Evaluation uses exactly 56 held-out rows, 8 held-out rows per drive, and no learn/eval overlap. |
| `qwen_drive_local_eval` | `primary` | Qwen drive-local calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05. |
| `positive_effect_floor` | `primary` | Passing Qwen drive-local mode must have positive mean increment and positive increment share at least 55%. |

## Claim Boundary

Stage 27P is bounded cross-architecture evidence for Qwen drive-local calibrated output-side eraser-cover intervention over CPL2 likelihood margins. It is not universal architecture evidence, not weight editing, not complete circuit discovery, not model-wide control, and not visible free-form generation control.

## Forbidden Claims

Do not claim universal cross-architecture steering, complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, or raw CAS-symbol understanding from Stage 27P.

## Validation

`{}`
