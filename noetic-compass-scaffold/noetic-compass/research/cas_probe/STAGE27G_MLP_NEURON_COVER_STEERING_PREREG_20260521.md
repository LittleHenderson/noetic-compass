# Stage 27G MLP-Neuron Cover Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27F established sparse MLP-neuron covers that causally support class-specific Foundation margins. Stage 27G tests whether those same covers can steer the readout when amplified.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_activations`: `stage7_foundation_pilot_activations_20260517.npz`
- `stage7_activation_sha256`: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- `stage27f_report`: `stage27f_targeted_mlp_neuron_covers_20260521.json`
- `stage27f_status`: `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`
- `locked_readout`: `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}`
- `amplification_scale`: `2.0`
- `polarity_flip_scale`: `-1.0`
- `eval_rows_per_class`: `4`

## Method

1. Commit this pre-registration and runner before any Stage 27G GPU result is generated.
2. Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.
3. Verify Stage 27F is PASS, uses the locked artifact, and exposes per-class MLP-neuron covers.
4. On held-out Stage 7 test rows, read the target Foundation and hard-partner Foundation for each row.
5. Amplify the target class's Stage 27F neuron cover by the preregistered scale and measure target-vs-partner margin increase.
6. Polarity-flip the same target class neuron cover by the preregistered negative scale and measure target-vs-partner margin decrease or sign flip.
7. Compare both directional effects against same-size/same-layer random neuron-cover controls using the same intervention scale.
8. Amplify the hard-partner class's cover as a countersteering diagnostic, but do not use it as the primary PASS gate because the partner cover may be inactive on target-class prompts.
9. Report actual margin-flip share for polarity flip and partner amplification as diagnostics; signed readout-margin steering is the primary gate.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 7 activation artifact hash matches the locked manifest. |
| `stage27f_contract` | `pass_floor` | Stage 27F source report is PASS and exposes per-class MLP-neuron covers. |
| `target_amplification_control` | `primary` | Target-cover amplification beats random target-layer amplification on at least 60% of eval rows with sign-test p<0.05. |
| `target_polarity_flip_control` | `primary` | Target-cover polarity flip reduces target-vs-partner margin more than random target-layer polarity flips on at least 60% of eval rows with sign-test p<0.05. |
| `bidirectional_positive_share` | `primary` | Both target-amplification margin increases and target-flip margin reductions are positive on at least 55% of eval rows. |
| `flip_share` | `diagnostic` | Report the share of rows where target polarity flip and partner amplification push target-vs-partner margin below zero; not required for PASS. |

## Claim Boundary

Stage 27G is readout-level steering evidence over Stage 27F MLP-neuron covers. It is not free-form generation control, not weight editing, not a complete circuit, not model-wide control, and not a claim that raw CAS symbols are understood.

## Forbidden Claims

Do not claim free-form generation control, model-wide control, complete circuits, weight editing, internal CAS compiler behavior, cross-model steering, or raw CAS-symbol understanding from Stage 27G.

## Validation

`{}`
