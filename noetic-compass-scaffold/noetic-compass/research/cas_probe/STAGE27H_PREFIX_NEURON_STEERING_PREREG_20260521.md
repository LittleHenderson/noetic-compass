# Stage 27H Prefix-Plus-Neuron Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 7 proved readable-prefix likelihood conditioning. Stage 27G proved MLP-neuron cover readout steering. Stage 27H tests whether the two routes combine at the semantic likelihood level.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_prefix_report`: `stage7_cas_prefix_likelihood_20260517.json`
- `stage27f_report`: `stage27f_targeted_mlp_neuron_covers_20260521.json`
- `stage27g_report`: `stage27g_mlp_neuron_cover_steering_20260521.json`
- `stage7_prefix_status`: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- `stage27f_status`: `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`
- `stage27g_status`: `PASS_BOUNDED_MLP_NEURON_COVER_STEERING`
- `amplification_scale`: `2.0`
- `polarity_flip_scale`: `-1.0`
- `per_drive`: `16`

## Method

1. Commit this pre-registration and runner before any Stage 27H GPU result is generated.
2. Reuse the Stage 7 CAS-prefix likelihood row selection and readable plain-prefix wording.
3. Verify Stage 27F and Stage 27G source reports are PASS and expose the class-specific MLP-neuron covers.
4. Score correct-drive versus hard-partner-drive continuation likelihood under no prefix and readable prefix.
5. During likelihood scoring, amplify the target class's Stage 27F neuron cover and compare prefix-plus-amplification against prefix-only.
6. Compare the prefix-plus-amplification increment against same-size/same-layer random neuron-cover amplification controls.
7. Polarity-flip the target cover under the same readable prefix and compare the margin reduction against random polarity-flip controls.
8. Report neuron-only amplification and partner-cover amplification as diagnostics, not primary PASS gates.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 7 readable-prefix, Stage 27F, and Stage 27G source reports have the preregistered PASS statuses. |
| `prefix_floor` | `pass_floor` | Readable prefix-only margin delta versus no-prefix is positive and at least +0.10 on average. |
| `prefix_plus_target_amplification` | `primary` | Prefix-plus-target-cover amplification beats random-cover amplification increments on at least 60% of rows with sign-test p<0.05. |
| `prefix_plus_target_flip` | `primary` | Prefix-plus-target-cover polarity flip reduces margin more than random-cover polarity flips on at least 60% of rows with sign-test p<0.05. |
| `bidirectional_effect_share` | `primary` | Both amplification increments and polarity-flip reductions are positive on at least 55% of rows. |

## Claim Boundary

Stage 27H is output-distribution likelihood steering, not free-form visible-text control, not weight editing, not model-wide control, not a complete circuit, and not cross-model evidence.

## Forbidden Claims

Do not claim open-ended generation control, exact circuit completion, model-wide control, weight editing, cross-model steering, or raw CAS-symbol understanding from Stage 27H.

## Validation

`{}`
