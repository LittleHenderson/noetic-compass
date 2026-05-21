# Stage 27K Output-Side Component Steering Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27J found late output-side carrier and eraser components for readable-prefix likelihood margins. Stage 27K tests whether those attributed covers are usable as a direct intervention surface: amplify carriers, suppress erasers, and compare the held-out margin lift against matched random interventions.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_prefix_report`: `stage7_cas_prefix_likelihood_20260517.json`
- `stage27j_report`: `stage27j_output_side_component_attribution_20260521.json`
- `stage7_prefix_status`: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- `stage27j_status`: `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`
- `intervention_rows`: `Stage 27J held-out eval split only`
- `carrier_scale`: `2.0`
- `eraser_scale`: `0.0`
- `carrier_flip_scale`: `-1.0`
- `intervention_positions`: `continuation_prediction_positions_only`
- `random_control_policy`: `same layer/kind when available; singleton MLP blocks fall back to same-kind different-layer controls`

## Method

1. Commit this pre-registration and runner before any Stage 27K GPU result is generated.
2. Verify the Stage 7 readable-prefix source PASS and Stage 27J output-side attribution PASS source contract.
3. Recreate the Stage 27J learn/eval split deterministically and evaluate only the held-out eval rows.
4. Load the Stage 27J carrier and eraser covers; do not relearn covers in Stage 27K.
5. Score readable-prefix CPL2 margins with no intervention.
6. Score carrier amplification, eraser suppression, and combined carrier-amplification-plus-eraser-suppression at continuation prediction positions.
7. Score matched random combined interventions with the same cover sizes and component matching policy.
8. Use carrier polarity flip as a destructive-control diagnostic.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `source_contracts` | `pass_floor` | Stage 7 readable-prefix source PASS and Stage 27J output-side attribution PASS are both verified. |
| `held_out_split` | `pass_floor` | Evaluation uses the recreated Stage 27J held-out rows only. |
| `combined_steering_eval` | `primary` | Combined carrier amplification plus eraser suppression increases held-out readable-prefix likelihood margin more than matched random combined interventions on at least 60% of rows with sign-test p<0.05. |
| `positive_effect_floor` | `primary` | Combined intervention has positive mean margin increment and positive increment share at least 55%. |
| `carrier_polarity_control` | `secondary` | Carrier polarity flip reduces held-out margin more than matched random carrier flip on at least 60% of rows with sign-test p<0.05. |

## Claim Boundary

Stage 27K is bounded late-layer intervention steering over Pythia-160M CPL2 likelihood margins. It is not weight editing, not complete circuit discovery, not model-wide control, not cross-model control, and not visible free-form generation control.

## Forbidden Claims

Do not claim complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, cross-model steering, or raw CAS-symbol understanding from Stage 27K.

## Validation

`{}`
