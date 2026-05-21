# Stage 27P-A Qwen Hook-Adapter Preflight Pre-Registration

**Status:** `PREREGISTERED_GPU_REQUIRED`

## Motivation

Stage 27O closed Pythia cross-scale steering with drive-local output-side eraser covers. Stage 27P moves to Qwen, but Qwen uses different module paths than Pythia. Stage 27P-A validates the hook adapter before any cross-architecture steering claim is attempted.

## Required Inputs

- `model`: `Qwen/Qwen2.5-1.5B`
- `model_revision`: `8faed761d45a263340a0528343f099c05c9a4323`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage16_cpl2_report`: `STAGE16_QWEN15B_CPL2_REPORT_20260519.json`
- `stage16_manifest`: `stage16_qwen15b_activations_manifest_20260519.json`
- `stage27o_report`: `stage27o_drive_local_cross_scale_eraser_steering_20260521.json`
- `stage16_cpl2_status`: `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`
- `stage27o_status`: `PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING`
- `candidate_layers`: `[24, 25, 26, 27]`
- `probe_layer_reference`: `11`
- `intervention_positions`: `continuation_prediction_positions_only`
- `preflight_components`: `['L27H0', 'L27MLP']`

## Method

1. Commit this pre-registration, adapter, runner, and tests before any Qwen hook result is generated.
2. Verify Stage 16 Qwen CPL2 PASS and Stage 27O Pythia-1B drive-local steering PASS source contracts.
3. Load Qwen/Qwen2.5-1.5B at revision 8faed761d45a263340a0528343f099c05c9a4323.
4. Inspect candidate late layers 24-27 and verify attention output projection and MLP module paths.
5. Run one actual CPL2-style prompt/continuation row with no hook, one attention-head scale hook, and one MLP scale hook.
6. Confirm hooks are continuation-prediction-position localized: positions before the first prediction position remain unchanged.
7. Confirm each hook changes logits at prediction positions and yields finite continuation log-probabilities.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 16 Qwen CPL2 PASS, Stage 16 manifest revision match, and Stage 27O PASS source contracts are verified. |
| `model_revision` | `pass_floor` | Loaded Qwen model revision matches 8faed761d45a263340a0528343f099c05c9a4323. |
| `adapter_paths` | `primary` | Every candidate layer exposes attention output projection self_attn.o_proj and MLP module mlp. |
| `attention_hook_effect` | `primary` | A scaled attention-head hook changes logits at prediction positions while leaving earlier positions unchanged. |
| `mlp_hook_effect` | `primary` | A scaled MLP hook changes logits at prediction positions while leaving earlier positions unchanged. |

## Claim Boundary

Stage 27P-A is only a hook-adapter preflight. It proves Qwen component hooks can be applied at the intended positions with finite effects; it does not prove Qwen steering, component attribution, or circuit control.

## Forbidden Claims

Do not claim Qwen steering, cross-architecture control, complete circuits, durable weight edits, open-ended generation control, or raw CAS-symbol understanding from Stage 27P-A.

## Validation

`{}`
