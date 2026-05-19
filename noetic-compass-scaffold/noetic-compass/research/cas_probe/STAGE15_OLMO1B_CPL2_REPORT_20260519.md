# Stage 15 OLMo-1B CPL2 Report

**Status:** `PASS_CLEAN_STAGE15_OLMO1B_CPL2_REPLICATES`

## Probe Prediction

- Selected layer: `16`
- Selected-row Foundation accuracy: `0.9107`
- Selected-row Drive accuracy: `0.9554`

## Likelihood Results

| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |
|---|---:|---:|---:|---:|
| none | 0.1077 | 0.0000 | 0 / 112 | 1.0000 |
| gold_readable | 0.7638 | 0.6561 | 91 / 112 | 0.0000 |
| probe_readable | 0.7114 | 0.6037 | 87 / 112 | 0.0000 |
| partner_readable | -0.5934 | -0.7010 | 18 / 112 | 1.0000 |
| gold_raw | 0.1146 | 0.0069 | 60 / 112 | 0.2543 |
| probe_raw | 0.1140 | 0.0063 | 60 / 112 | 0.2543 |
| partner_raw | 0.1088 | 0.0011 | 63 / 112 | 0.1096 |

## Gate

- `probe_readable_delta_vs_none`: `0.6037`
- `probe_readable_delta_wilcoxon_p`: `0.0000`
- `probe_readable_delta_wilcoxon_statistic`: `5531.0000`
- `probe_readable_delta_wilcoxon_method`: `scipy.stats.wilcoxon(alternative='greater')`
- `probe_readable_minus_partner_readable_margin`: `1.3047`
- `probe_readable_positive_count`: `87`
- `probe_readable_positive_share`: `0.7768`
- `gold_readable_delta_vs_none`: `0.6561`
- `gold_readable_minus_partner_readable_margin`: `1.3572`
- `probe_raw_delta_vs_none`: `0.0063`
- `gold_raw_delta_vs_none`: `0.0069`

## Implication

The eta-to-epsilon readable-prefix bridge transfers to OLMo-1B under the pre-registered CPL2 gate. This supports a cross-architecture CAS Harness conditioning claim, not hidden-state steering or raw CAS-symbol understanding.
