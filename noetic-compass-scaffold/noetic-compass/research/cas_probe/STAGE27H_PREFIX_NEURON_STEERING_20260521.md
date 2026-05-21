# Stage 27H Prefix-Plus-Neuron Steering

**Status:** `NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED`

## Contracts

- Stage 7 prefix source: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- Stage 27F source: `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`
- Stage 27G source: `PASS_BOUNDED_MLP_NEURON_COVER_STEERING`

## Evaluation

- Cases: `112` (16 per drive)
- Amplification scale: `2.0`
- Polarity flip scale: `-1.0`
- No-prefix mean margin: `0.040478`
- Prefix-only mean margin: `0.524425`
- Prefix + target amplification mean margin: `0.491874`
- Prefix + target flip mean margin: `0.550014`
- Prefix delta vs none: `0.483947`
- Prefix + target amplification increment: `-0.032551`
- Random amplification increment: `-0.022499`
- Prefix + target flip reduction: `-0.025589`
- Random flip reduction: `-0.004372`
- Neuron-only amplification delta vs none: `-0.013920`
- Prefix amplification minus neuron-only amplification: `0.465315`

## Paired Controls

- Prefix + target amplification > random: `52 / 112` (share `0.4643`, p `0.802403`, mean delta `-0.010052`)
- Prefix + target flip > random: `55 / 112` (share `0.4911`, p `0.611518`, mean delta `-0.021217`)
- Prefix + target flip margin below zero share: `0.3036`

## Boundary

Stage 27H is bounded to semantic continuation likelihood on Pythia-160M using readable-prefix conditioning plus Stage 27F/27G MLP-neuron cover interventions. It is output-distribution evidence, not free-form visible-text control, not weight editing, not complete circuit discovery, not model-wide control, and not cross-model evidence.
