# Stage 27G MLP-Neuron Cover Steering

**Status:** `PASS_BOUNDED_MLP_NEURON_COVER_STEERING`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 27F source status: `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`
- Stage 27F formal gate: `True`

## Evaluation

- Eval rows: `112` (4 per class)
- Amplification scale: `2.0`
- Polarity flip scale: `-1.0`
- Clean mean margin: `6.371307`
- Target-amplified mean margin: `19.088273`
- Target-flipped mean margin: `-18.773726`
- Partner-amplified mean margin: `1.417746`
- Target amplification mean delta: `12.716967`
- Random target amplification mean delta: `-0.078081`
- Target flip mean reduction: `25.145033`
- Random target flip mean reduction: `-0.135299`

## Paired Controls

- Target amplification > random: `112 / 112` (share `1.0000`, p `1.92593e-34`, mean delta `12.795047`)
- Target polarity flip > random: `112 / 112` (share `1.0000`, p `1.92593e-34`, mean delta `25.280332`)
- Partner amplification diagnostic > random: `112 / 112` (share `1.0000`, p `1.92593e-34`, mean delta `4.982333`)

## Flip Diagnostics

- Target polarity flip margin below zero share: `1.0000`
- Partner amplification margin below zero share: `0.2589`

## Pair-Kind Breakdown

| Pair kind | n | Amp delta mean | Amp > random share | Flip reduction mean | Flip > random share |
|---|---:|---:|---:|---:|---:|
| `same_drive_diff_register` | 112 | 12.716967 | 1.0000 | 25.145033 | 1.0000 |

## Boundary

Stage 27G is bounded to readout-level intervention on Stage 27F Pythia-160M MLP intermediate-neuron covers. It tests amplification and polarity-flip steering of the trained Stage 7 Foundation readout. It is not free-form generation control, not weight editing, not complete circuit discovery, not model-wide control, not cross-model steering, and not raw CAS-symbol understanding.
