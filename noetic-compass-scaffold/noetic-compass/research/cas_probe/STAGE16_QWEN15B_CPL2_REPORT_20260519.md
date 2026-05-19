# Stage 16 Qwen2.5-1.5B CPL2 Report

**Status:** `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`

## Probe Prediction

- Selected layer: `11`
- Selected-row Foundation accuracy: `0.8036`
- Selected-row Drive accuracy: `0.9107`

## Likelihood Results

| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |
|---|---:|---:|---:|---:|
| none | 0.0158 | 0.0000 | 0 / 112 | 1.0000 |
| gold_readable | 0.9524 | 0.9366 | 89 / 112 | 0.0000 |
| probe_readable | 0.8118 | 0.7960 | 83 / 112 | 0.0000 |
| partner_readable | -0.8134 | -0.8293 | 31 / 112 | 1.0000 |
| gold_raw | 0.0196 | 0.0037 | 65 / 112 | 0.0539 |
| probe_raw | 0.0156 | -0.0002 | 66 / 112 | 0.0361 |
| partner_raw | 0.0076 | -0.0082 | 56 / 112 | 0.5376 |

## Gate

- `probe_readable_delta_vs_none`: `0.7960`
- `probe_readable_delta_wilcoxon_p`: `0.0000`
- `probe_readable_delta_wilcoxon_statistic`: `5535.0000`
- `probe_readable_delta_wilcoxon_method`: `scipy.stats.wilcoxon(alternative='greater')`
- `probe_readable_minus_partner_readable_margin`: `1.6253`
- `probe_readable_positive_count`: `83`
- `probe_readable_positive_share`: `0.7411`
- `gold_readable_delta_vs_none`: `0.9366`
- `gold_readable_minus_partner_readable_margin`: `1.7659`
- `probe_raw_delta_vs_none`: `-0.0002`
- `gold_raw_delta_vs_none`: `0.0037`

## Implication

The eta-to-epsilon readable-prefix bridge transfers to Qwen2.5-1.5B under the pre-registered CPL2 gate. This supports a cross-architecture CAS Harness conditioning claim, not hidden-state steering or raw CAS-symbol understanding.
