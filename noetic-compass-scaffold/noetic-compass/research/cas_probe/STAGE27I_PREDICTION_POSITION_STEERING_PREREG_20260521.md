# Stage 27I Prediction-Position Neuron Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27H showed that broad MLP-neuron cover hooks do not add likelihood control over the readable prefix. Stage 27I localizes the same covers to the exact hidden positions whose logits score the continuation tokens, and traces whether that layer-5 signal survives to output-side depths.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_prefix_report`: `stage7_cas_prefix_likelihood_20260517.json`
- `stage7_activations`: `stage7_foundation_pilot_activations_20260517.npz`
- `stage7_activation_sha256`: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- `stage27f_report`: `stage27f_targeted_mlp_neuron_covers_20260521.json`
- `stage27g_report`: `stage27g_mlp_neuron_cover_steering_20260521.json`
- `stage27h_report`: `stage27h_prefix_neuron_steering_20260521.json`
- `stage7_prefix_status`: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- `stage27f_status`: `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`
- `stage27g_status`: `PASS_BOUNDED_MLP_NEURON_COVER_STEERING`
- `stage27h_status`: `NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED`
- `intervention_positions`: `continuation_prediction_positions_only`
- `downstream_trace_layers`: `[6, 7, 8, 9, 10, 11, 12]`
- `amplification_scale`: `2.0`
- `polarity_flip_scale`: `-1.0`
- `per_drive`: `16`

## Method

1. Commit this pre-registration and runner before any Stage 27I GPU result is generated.
2. Reuse the Stage 7 CAS-prefix likelihood row selection and readable plain-prefix wording.
3. Verify Stage 7 prefix, Stage 7 activation artifact, Stage 27F, Stage 27G, and Stage 27H source contracts, including Stage 27H's preregistered NULL.
4. Score correct-drive versus hard-partner-drive continuation likelihood under no prefix and readable prefix.
5. Apply Stage 27F neuron-cover amplification only at hidden positions whose logits score continuation tokens.
6. Compare prefix-plus-position-localized amplification against prefix-only and same-size/same-layer random localized controls.
7. Apply target-cover polarity flip at the same prediction positions and compare the reduction against random localized flips.
8. Trace the target-cover amplification effect through layers 6-12 at the same prediction positions using layer-specific Stage 7 Foundation readouts.
9. Report whether position-localized intervention changes the Stage 27H broad-hook null and where the layer-5 signal survives or fades.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 7 readable-prefix, Stage 7 activation artifact, Stage 27F, Stage 27G, and Stage 27H source reports have the preregistered statuses. |
| `prefix_floor` | `pass_floor` | Readable prefix-only margin delta versus no-prefix is positive and at least +0.10 on average. |
| `position_localized_amplification` | `primary` | Prediction-position target-cover amplification beats random-cover amplification increments on at least 60% of rows with sign-test p<0.05. |
| `position_localized_flip` | `primary` | Prediction-position target-cover polarity flip reduces margin more than random-cover polarity flips on at least 60% of rows with sign-test p<0.05. |
| `bidirectional_effect_share` | `primary` | Both localized amplification increments and localized polarity-flip reductions are positive on at least 55% of rows. |
| `downstream_survival_trace` | `diagnostic` | Report layer 6-12 readout-margin deltas after localized target-cover amplification; not required for PASS. |

## Claim Boundary

Stage 27I is prediction-position-localized likelihood steering, not free-form visible-text control, not weight editing, not model-wide control, not a complete circuit, and not cross-model evidence.

## Forbidden Claims

Do not claim open-ended generation control, exact circuit completion, model-wide control, weight editing, cross-model steering, or raw CAS-symbol understanding from Stage 27I.

## Validation

`{}`
