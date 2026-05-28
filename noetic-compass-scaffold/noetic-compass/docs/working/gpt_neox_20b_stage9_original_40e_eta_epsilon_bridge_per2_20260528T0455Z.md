# Stage 9 40E Eta-To-Epsilon Bridge

**Status:** `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS`

## Readout

- Model: `EleutherAI/gpt-neox-20b`
- Axis: `40_element_operator_x_domain`
- Readout mode: `logistic_linear_probe`
- Readout layer: `2`
- Selected element accuracy: `0.9750`
- Selected operator accuracy: `0.9750`
- Selected domain accuracy: `1.0000`
- Filter coverage: `80 / 80` (`1.0000`)
- Filter threshold: `None` on `normalized_readout_margin`

## Likelihood Conditions

| Condition | Mean margin | Mean delta vs none | Positive rows | Sign p |
|---|---:|---:|---:|---:|
| none | 0.0082 | 0.0000 | 0 / 80 | 1.000000 |
| gold_readable | 1.5057 | 1.4975 | 80 / 80 | 0.000000 |
| probe_readable | 1.4203 | 1.4121 | 79 / 80 | 0.000000 |
| partner_readable | -1.4610 | -1.4692 | 0 / 80 | 1.000000 |
| gold_raw | 0.0217 | 0.0134 | 49 / 80 | 0.028332 |
| probe_raw | 0.0220 | 0.0138 | 50 / 80 | 0.016496 |
| partner_raw | 0.0239 | 0.0156 | 49 / 80 | 0.028332 |

## Key Comparisons

- `probe_readable_delta_vs_none`: `1.412050`
- `probe_readable_minus_partner_readable_margin`: `2.881239`
- `gold_readable_delta_vs_none`: `1.497513`
- `gold_readable_minus_partner_readable_margin`: `2.966701`
- `probe_raw_delta_vs_none`: `0.013817`
- `gold_raw_delta_vs_none`: `0.013427`

## Bridge Gates

| Loop | Gate | Value | Required | Pass |
|---|---|---:|---:|---|
| probe_readable | delta_vs_none | 1.412050 | > 0.10 | yes |
| probe_readable | minus_partner_readable_margin | 2.881239 | > 0.10 | yes |
| probe_readable | delta_positive_sign_p | 0.000000 | <= 0.01 | yes |
| gold_readable | delta_vs_none | 1.497513 | > 0.10 | yes |
| gold_readable | minus_partner_readable_margin | 2.966701 | > 0.10 | yes |
| gold_readable | delta_positive_sign_p | 0.000000 | <= 0.01 | yes |

## Correctness Buckets

| Bucket | Rows | Probe delta vs none | Probe minus partner | Gold delta vs none |
|---|---:|---:|---:|---:|
| all | 80 | 1.4121 | 2.8812 | 1.4975 |
| element_correct | 78 | 1.4913 | 2.9484 | 1.4913 |
| operator_correct | 78 | 1.4913 | 2.9484 | 1.4913 |
| domain_correct | 80 | 1.4121 | 2.8812 | 1.4975 |
| element_wrong | 2 | -1.6781 | 0.2637 | 1.7403 |

## Implication

The 40E eta-to-epsilon loop passes this likelihood assay: the model's own hidden-state 40-Element readout can be realized as readable CAS context, and that context moves paired likelihood in the intended direction. Raw CAS-symbol prefixes remain non-load-bearing.
