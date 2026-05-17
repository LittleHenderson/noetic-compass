# Stage 7 CAS-Prefix Full Loop

**Status:** `PROBE_PREDICTED_CAS_PREFIX_CONDITIONS_PYTHIA`

## Read

This is the full harness bridge: Pythia hidden states are read by the Stage 7 Foundation probe, the predicted Foundation label is realized into readable CAS context, and Pythia's conditional likelihood is measured.

## Probe Accuracy

- Selected-row Foundation accuracy: `0.7857`
- Selected-row Drive accuracy: `0.8482`

## Results

| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |
|---|---:|---:|---:|---:|
| none | 0.0031 | 0.0000 | 0 / 112 | 1.0000 |
| gold_readable | 0.3954 | 0.3923 | 91 / 112 | 0.0000 |
| probe_readable | 0.2860 | 0.2828 | 81 / 112 | 0.0000 |
| partner_readable | -0.3969 | -0.4000 | 23 / 112 | 1.0000 |
| gold_raw | -0.0001 | -0.0032 | 53 / 112 | 0.7457 |
| probe_raw | 0.0020 | -0.0011 | 56 / 112 | 0.5376 |
| partner_raw | 0.0325 | 0.0294 | 61 / 112 | 0.1976 |

## Key Comparisons

- `probe_readable_delta_vs_none`: 0.2828
- `probe_readable_minus_partner_readable_margin`: 0.6829
- `gold_readable_delta_vs_none`: 0.3923
- `gold_readable_minus_partner_readable_margin`: 0.7923
- `probe_raw_delta_vs_none`: -0.0011
- `gold_raw_delta_vs_none`: -0.0032

## Implication

The full eta-to-epsilon loop works in this likelihood assay: Pythia's own Stage 7 readout can be realized as readable CAS context, and that context moves semantic likelihood in the intended direction. This supports CAS Harness conditioning, not hidden-neuron steering. Raw CAS-symbol prefixes remain ineffective.
