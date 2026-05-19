# Stage 19A Formula Verification Stack Report

**Status:** `PASS_STRONG_AUDIT_CLEAN`

## Headline

- Baseline focus-token layer-12 accuracy: `0.9540`
- Ensemble-only accuracy: `0.9550`
- Ensemble-only coverage: `0.9569`
- Stack accepted accuracy: `0.9978`
- Stack coverage: `0.8760`
- Stack silent error rate: `0.0022`
- Stack suppressed rate: `0.1240`
- Accepted examples: `3679/4200`
- Suppressed examples: `521/4200`
- Silent accepted errors: `8/3679`

## Deterministic Rerun Audit

This rerun was executed after the Stage 19 gates, runner, and first report were
committed and pushed through commit `05ac687`.

The rerun reproduced the first-run metrics exactly:

| Metric | First run | Rerun |
|---|---:|---:|
| Baseline `focus_token` layer-12 accuracy | `0.954047619047619` | `0.954047619047619` |
| Ensemble-only accuracy | `0.954963921373476` | `0.954963921373476` |
| Ensemble-only coverage | `0.956904761904762` | `0.956904761904762` |
| Ensemble accepted | `4019` | `4019` |
| Stack accepted | `3679` | `3679` |
| Stack suppressed | `521` | `521` |
| Stack coverage | `0.875952380952381` | `0.875952380952381` |
| Stack accepted accuracy | `0.997825496058712` | `0.997825496058712` |
| Stack silent error rate | `0.002174503941288` | `0.002174503941288` |
| Stack suppressed rate | `0.124047619047619` | `0.124047619047619` |

Verdict:

> The Stage 19A pre-commit caveat is resolved. The clean standing status is
> `PASS_STRONG_AUDIT_CLEAN`.

## Acceptance Counts

| Tier | Count | Accuracy |
|---|---:|---:|
| `high` | 3678 | `0.9978` |
| `medium` | 1 | `1.0000` |

## Suppression Reasons

| Reason | Count |
|---|---:|
| `ensemble_all_disagree` | 181 |
| `final_token_conflicted` | 15 |
| `final_token_conflicted+focus_token_conflicted` | 69 |
| `final_token_conflicted+focus_token_conflicted+mean_over_seq_len_conflicted` | 134 |
| `final_token_conflicted+mean_over_seq_len_conflicted` | 35 |
| `focus_token_conflicted` | 14 |
| `focus_token_conflicted+mean_over_seq_len_conflicted` | 46 |
| `mean_over_seq_len_conflicted` | 18 |
| `trace_unstable` | 9 |

## Boundary

This is a product-realistic verification-stack run. Gold labels are used only for scoring, not for acceptance. The stack does not use oracle `stable_correct` or `stable_wrong` labels at runtime.
