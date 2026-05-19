# Stage 14 Pythia-2.8B CPL2 Report

**Status:** `PASS_CLEAN_STAGE14_PYTHIA28B_CPL2_REPLICATES`

## Probe Prediction

- Selected layer: `14`
- Selected-row Foundation accuracy: `0.8571`
- Selected-row Drive accuracy: `0.9464`

## Likelihood Results

| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |
|---|---:|---:|---:|---:|
| none | 0.0671 | 0.0000 | 0 / 112 | 1.0000 |
| gold_readable | 0.7327 | 0.6656 | 98 / 112 | 0.0000 |
| probe_readable | 0.6503 | 0.5832 | 92 / 112 | 0.0000 |
| partner_readable | -0.6860 | -0.7531 | 7 / 112 | 1.0000 |
| gold_raw | 0.0711 | 0.0040 | 53 / 112 | 0.7457 |
| probe_raw | 0.0698 | 0.0027 | 53 / 112 | 0.7457 |
| partner_raw | 0.0641 | -0.0030 | 55 / 112 | 0.6115 |

## Gate

- `probe_readable_delta_vs_none`: `0.5832`
- `probe_readable_delta_wilcoxon_p`: `0.0000`
- `probe_readable_delta_wilcoxon_statistic`: `5851.0000`
- `probe_readable_delta_wilcoxon_method`: `scipy.stats.wilcoxon(alternative='greater')`
- `probe_readable_minus_partner_readable_margin`: `1.3363`
- `probe_readable_positive_count`: `92`
- `probe_readable_positive_share`: `0.8214`
- `gold_readable_delta_vs_none`: `0.6656`
- `gold_readable_minus_partner_readable_margin`: `1.4187`
- `probe_raw_delta_vs_none`: `0.0027`
- `gold_raw_delta_vs_none`: `0.0040`

## Implication

The eta-to-epsilon readable-prefix bridge transfers to Pythia-2.8B under the pre-registered CPL2 gate. This supports a larger-scale within-Pythia CAS Harness conditioning claim, not hidden-state steering or raw CAS-symbol understanding.
