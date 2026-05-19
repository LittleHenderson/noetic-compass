# Stage 19A Formula Verification Stack Report

**Status:** `PASS_STRONG_WITH_PRECOMMIT_CAVEAT`

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

## Procedural Caveat

The Stage 19 gates and runner were written before the pod run, but they were
not committed before execution. Treat this as a strong internal result with a
pre-commit audit caveat. External-facing use should wait for Codex/Claude audit
or a deterministic rerun after the gates and script are committed.

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
