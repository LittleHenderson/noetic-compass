# Stage 27I Prediction-Position Neuron Steering

**Status:** `NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 7 prefix source: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- Stage 27F source: `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`
- Stage 27G source: `PASS_BOUNDED_MLP_NEURON_COVER_STEERING`
- Stage 27H source: `NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED`

## Evaluation

- Cases: `112` (16 per drive)
- Intervention positions: `continuation_prediction_positions_only`
- Amplification scale: `2.0`
- Polarity flip scale: `-1.0`
- No-prefix mean margin: `0.040478`
- Prefix-only mean margin: `0.524425`
- Prefix + localized target amplification mean margin: `0.500579`
- Prefix + localized target flip mean margin: `0.522995`
- Prefix delta vs none: `0.483947`
- Localized amplification increment: `-0.023846`
- Random localized amplification increment: `-0.007575`
- Localized flip reduction: `0.001430`
- Random localized flip reduction: `0.015879`

## Paired Controls

- Localized amplification > random: `46 / 112` (share `0.4107`, p `0.976632`, mean delta `-0.016270`)
- Localized flip > random: `47 / 112` (share `0.4196`, p `0.963937`, mean delta `-0.014449`)
- Localized target flip margin below zero share: `0.2946`

## Downstream Survival Trace

| Layer | Clean readout margin | Amplified readout margin | Delta | Positive share |
|---:|---:|---:|---:|---:|
| 6 | 0.615643 | 0.998051 | 0.382408 | 0.7232 |
| 7 | 0.944192 | 1.179461 | 0.235269 | 0.5714 |
| 8 | 1.464518 | 1.782099 | 0.317582 | 0.6161 |
| 9 | 1.344921 | 1.436480 | 0.091559 | 0.5446 |
| 10 | 1.698680 | 1.760214 | 0.061534 | 0.5714 |
| 11 | 2.688922 | 2.700930 | 0.012009 | 0.4911 |
| 12 | 1.703521 | 1.693835 | -0.009687 | 0.4732 |

## Boundary

Stage 27I is bounded to semantic continuation likelihood on Pythia-160M using readable-prefix conditioning plus Stage 27F MLP-neuron cover interventions localized to continuation prediction positions. It is output-distribution evidence, not free-form visible-text control, not weight editing, not complete circuit discovery, not model-wide control, and not cross-model evidence.
