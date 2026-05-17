# Stage 8 Pythia-1B CPL2 Report

**Status:** `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`

## Probe Prediction

- Selected layer: `8`
- Selected-row Foundation accuracy: `0.7321`
- Selected-row Drive accuracy: `0.9464`

## Likelihood Results

| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |
|---|---:|---:|---:|---:|
| none | 0.0554 | 0.0000 | 0 / 112 | 1.0000 |
| gold_readable | 0.6354 | 0.5800 | 95 / 112 | 0.0000 |
| probe_readable | 0.6096 | 0.5542 | 90 / 112 | 0.0000 |
| partner_readable | -0.6364 | -0.6918 | 15 / 112 | 1.0000 |
| gold_raw | 0.0321 | -0.0233 | 48 / 112 | 0.9461 |
| probe_raw | 0.0327 | -0.0227 | 50 / 112 | 0.8904 |
| partner_raw | 0.0335 | -0.0219 | 50 / 112 | 0.8904 |

## Gate

- `probe_readable_delta_vs_none`: `0.5542`
- `probe_readable_delta_wilcoxon_p`: `0.0000`
- `probe_readable_delta_wilcoxon_statistic`: `5757.0000`
- `probe_readable_delta_wilcoxon_method`: `scipy.stats.wilcoxon(alternative='greater')`
- `probe_readable_minus_partner_readable_margin`: `1.2460`
- `probe_readable_positive_count`: `90`
- `probe_readable_positive_share`: `0.8036`
- `gold_readable_delta_vs_none`: `0.5800`
- `gold_readable_minus_partner_readable_margin`: `1.2718`
- `probe_raw_delta_vs_none`: `-0.0227`
- `gold_raw_delta_vs_none`: `-0.0233`

## Implication

The eta-to-epsilon readable-prefix bridge transfers from Pythia-160M to Pythia-1B under the pre-registered CPL2 gate. This supports a cross-scale CAS Harness conditioning claim, not hidden-state steering or raw CAS-symbol understanding.
