# Stage 7 CAS-Prefix Likelihood Probe

**Status:** `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`

## Read

This tests the eta-to-epsilon bridge as conditional likelihood instead of numbered-choice behavior. It asks whether CAS symbols or readable CAS realizations make the true Drive phrase more likely than the partner Drive phrase.

## Results

| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |
|---|---:|---:|---:|---:|
| none | 0.0405 | 0.0000 | 0 / 112 | 1.0000 |
| raw_correct | 0.0205 | -0.0200 | 48 / 112 | 0.9461 |
| raw_partner | 0.0386 | -0.0018 | 53 / 112 | 0.7457 |
| gloss_correct | 0.3978 | 0.3573 | 77 / 112 | 0.0000 |
| gloss_partner | -0.3337 | -0.3742 | 27 / 112 | 1.0000 |
| plain_correct | 0.5244 | 0.4839 | 90 / 112 | 0.0000 |
| plain_partner | -0.4257 | -0.4662 | 28 / 112 | 1.0000 |
| plain_random_wrong | -0.0098 | -0.0503 | 53 / 112 | 0.7457 |

## Key Comparisons

- `raw_correct_minus_raw_partner_margin`: -0.0182
- `gloss_correct_minus_gloss_partner_margin`: 0.7314
- `plain_correct_minus_plain_partner_margin`: 0.9501
- `plain_correct_delta_vs_none`: 0.4839
- `gloss_correct_delta_vs_none`: 0.3573
- `raw_correct_delta_vs_none`: -0.0200

## Implication

A readable CAS-realization prefix changes Pythia's conditional likelihood in the intended direction. That supports a harness bridge: read CAS structure, realize it as language, and condition generation. This is external prompt conditioning, not internal-neuron steering. Raw CAS-symbol prefixes do not appear meaningful to Pythia by themselves.
