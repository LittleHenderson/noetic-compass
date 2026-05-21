# Stage 27P-A Qwen Hook-Adapter Preflight

**Status:** `PASS_QWEN_HOOK_ADAPTER_PREFLIGHT`

## Contracts

- Stage 16 CPL2 source: `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`
- Stage 16 manifest model revision: `8faed761d45a263340a0528343f099c05c9a4323`
- Stage 27O source: `PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING`
- Loaded model revision: `8faed761d45a263340a0528343f099c05c9a4323`

## Adapter

- Candidate layers: `[24, 25, 26, 27]`
- Candidate components: `52`
- Attention path: `self_attn.o_proj`
- MLP path: `mlp`

## Hook Effects

- Attention component: `L27H0` scale `0.0`
- Attention prediction-position max delta: `1.15625`
- Attention pre-prediction max delta: `0`
- MLP component: `L27MLP` scale `0.0`
- MLP prediction-position max delta: `15.0625`
- MLP pre-prediction max delta: `0`

## Boundary

Stage 27P-A is only a hook-adapter preflight. It proves Qwen component hooks can be applied at the intended positions with finite effects; it does not prove Qwen steering, component attribution, or circuit control.
