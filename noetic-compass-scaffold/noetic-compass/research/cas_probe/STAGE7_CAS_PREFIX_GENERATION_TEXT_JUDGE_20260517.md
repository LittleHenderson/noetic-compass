# Stage 7.CPL4 Generated-Text Quality Judge

**Status:** `PROBE_PREFIX_GENERATED_TEXT_CLASSIFIER_SHIFT_NOT_CLEAN`

## Read

A text-only judge trained on the original Stage 7 fixture is applied to generated CPL3 continuations. The judge never trains on generated text. This tests whether the probe-readable prefix creates a visible text shift beyond the simple keyword heuristic.

## Judge Reliability

- Drive judge: `tfidf_char_3_5` test acc `0.6679`, macro-F1 `0.6546`.
- Foundation judge: `tfidf_char_3_5` test acc `0.4966`, macro-F1 `0.4801`.

## Drive Judgment

| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None | Positive Delta | Sign p |
|---|---:|---:|---:|---:|---:|---:|
| none | 0.304 | 0.393 | -0.0116 | 0.0000 | 0 / 56 | 1.0000 |
| gold_readable | 0.357 | 0.357 | 0.0283 | 0.0398 | 28 / 56 | 0.5531 |
| probe_readable | 0.339 | 0.357 | 0.0141 | 0.0256 | 27 / 56 | 0.6556 |
| partner_readable | 0.339 | 0.411 | 0.0244 | 0.0360 | 27 / 56 | 0.6556 |
| probe_raw | 0.286 | 0.357 | -0.0160 | -0.0044 | 21 / 56 | 0.9780 |

## Foundation Judgment

| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None | Positive Delta | Sign p |
|---|---:|---:|---:|---:|---:|---:|
| none | 0.071 | 0.125 | -0.0042 | 0.0000 | 0 / 56 | 1.0000 |
| gold_readable | 0.161 | 0.179 | 0.0184 | 0.0227 | 26 / 56 | 0.7478 |
| probe_readable | 0.161 | 0.179 | 0.0160 | 0.0202 | 25 / 56 | 0.8252 |
| partner_readable | 0.161 | 0.179 | 0.0206 | 0.0249 | 28 / 56 | 0.5531 |
| probe_raw | 0.107 | 0.107 | -0.0022 | 0.0021 | 24 / 56 | 0.8856 |

## Key Comparisons

- `drive_probe_readable_delta_vs_none`: 0.0256
- `drive_probe_readable_margin_minus_partner_readable`: -0.0103
- `drive_probe_target_pred_minus_partner_target_pred`: 0.0000
- `foundation_probe_readable_delta_vs_none`: 0.0202
- `foundation_probe_readable_margin_minus_partner_readable`: -0.0047
- `foundation_probe_target_pred_minus_partner_target_pred`: 0.0000

## Implication

The independent text judge does not cleanly close the visible-generation tier. CPL2 likelihood remains the load-bearing eta-to-epsilon result; generated text should stay marked as exploratory.
