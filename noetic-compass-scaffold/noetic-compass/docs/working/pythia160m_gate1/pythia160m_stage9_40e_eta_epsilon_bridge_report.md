# Stage 9 40E Eta-To-Epsilon Bridge

**Status:** `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS`

## Readout

- Model: `EleutherAI/pythia-160m`
- Axis: `40_element_operator_x_domain`
- Readout mode: `logistic_linear_probe`
- Readout layer: `3`
- Selected element accuracy: `0.9500`
- Selected operator accuracy: `0.9750`
- Selected domain accuracy: `0.9625`
- Filter coverage: `80 / 80` (`1.0000`)
- Filter threshold: `None` on `normalized_readout_margin`

## Likelihood Conditions

| Condition | Mean margin | Mean delta vs none | Positive rows | Sign p |
|---|---:|---:|---:|---:|
| none | -0.0292 | 0.0000 | 0 / 80 | 1.000000 |
| gold_readable | 1.6878 | 1.7171 | 80 / 80 | 0.000000 |
| probe_readable | 1.5056 | 1.5348 | 76 / 80 | 0.000000 |
| partner_readable | -1.7207 | -1.6915 | 0 / 80 | 1.000000 |
| gold_raw | -0.0299 | -0.0007 | 41 / 80 | 0.455536 |
| probe_raw | -0.0299 | -0.0006 | 41 / 80 | 0.455536 |
| partner_raw | -0.0302 | -0.0010 | 40 / 80 | 0.544464 |

## Key Comparisons

- `probe_readable_delta_vs_none`: `1.534844`
- `probe_readable_minus_partner_readable_margin`: `3.226334`
- `gold_readable_delta_vs_none`: `1.717088`
- `gold_readable_minus_partner_readable_margin`: `3.408577`
- `probe_raw_delta_vs_none`: `-0.000626`
- `gold_raw_delta_vs_none`: `-0.000662`

## Bridge Gates

| Loop | Gate | Value | Required | Pass |
|---|---|---:|---:|---|
| probe_readable | delta_vs_none | 1.534844 | > 0.10 | yes |
| probe_readable | minus_partner_readable_margin | 3.226334 | > 0.10 | yes |
| probe_readable | delta_positive_sign_p | 0.000000 | <= 0.01 | yes |
| gold_readable | delta_vs_none | 1.717088 | > 0.10 | yes |
| gold_readable | minus_partner_readable_margin | 3.408577 | > 0.10 | yes |
| gold_readable | delta_positive_sign_p | 0.000000 | <= 0.01 | yes |

## Correctness Buckets

| Bucket | Rows | Probe delta vs none | Probe minus partner | Gold delta vs none |
|---|---:|---:|---:|---:|
| all | 80 | 1.5348 | 3.2263 | 1.7171 |
| element_correct | 76 | 1.6940 | 3.3515 | 1.6940 |
| operator_correct | 78 | 1.6425 | 3.2655 | 1.6660 |
| domain_correct | 77 | 1.6052 | 3.3079 | 1.7205 |
| element_wrong | 4 | -1.4896 | 0.8490 | 2.1553 |

## Implication

The 40E eta-to-epsilon loop passes this likelihood assay: the model's own hidden-state 40-Element readout can be realized as readable CAS context, and that context moves paired likelihood in the intended direction. Raw CAS-symbol prefixes remain non-load-bearing.
