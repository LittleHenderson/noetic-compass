# Stage 19B Cross-Architecture Foundation Verification Stack Report

**Status:** `NULL`

## Headline

| Model | Status | Best single | Stack accepted acc | Coverage | Silent error | Suppressed |
|---|---|---:|---:|---:|---:|---:|
| OLMo-1B | `DIAGNOSTIC_ONLY` | `0.9060` | `0.9816` | `0.7173` | `0.0184` | `0.2827` |
| Qwen2.5-1.5B | `DIAGNOSTIC_ONLY` | `0.8537` | `0.9949` | `0.7457` | `0.0051` | `0.2543` |

## Per-Model Details

### OLMo-1B (`olmo1b`)

- Source stage: `Stage 15`
- Activation file: `stage15_olmo1b_activations_20260519.npz`
- Best single Foundation accuracy: `0.9060`
- Ensemble-only accuracy / coverage: `0.8975` / `0.9039`
- Factor-consistent accuracy / coverage: `0.9422` / `0.8240`
- Stack accepted accuracy / coverage: `0.9816` / `0.7173`
- Stack accepted Drive accuracy: `0.9935`
- Stack accepted Register accuracy: `0.9881`

Selected layers:

| Task | Readout | Layer | Selection | Val acc | Test acc |
|---|---|---:|---|---:|---:|
| `foundation` | `focus_token` | `16` | `validation_selected_layer` | `0.9911` | `0.9060` |
| `foundation` | `final_token` | `16` | `validation_selected_layer` | `0.9033` | `0.7347` |
| `foundation` | `mean_over_seq_len` | `10` | `validation_selected_layer` | `0.7827` | `0.6582` |
| `drive` | `focus_token` | `16` | `foundation_selected_layer` | `0.9866` | `0.9600` |
| `drive` | `final_token` | `16` | `foundation_selected_layer` | `0.9315` | `0.8652` |
| `drive` | `mean_over_seq_len` | `10` | `foundation_selected_layer` | `0.8006` | `0.7292` |
| `register` | `focus_token` | `16` | `foundation_selected_layer` | `1.0000` | `0.9247` |
| `register` | `final_token` | `16` | `foundation_selected_layer` | `0.9955` | `0.8771` |
| `register` | `mean_over_seq_len` | `10` | `foundation_selected_layer` | `0.9985` | `0.9294` |

Suppression reasons:

| Reason | Count |
|---|---:|
| `drive_ensemble_all_disagree` | 28 |
| `factor_conflicted` | 143 |
| `final_token_conflicted` | 13 |
| `final_token_conflicted+focus_token_conflicted` | 7 |
| `final_token_conflicted+focus_token_conflicted+mean_over_seq_len_conflicted` | 5 |
| `final_token_conflicted+focus_token_uncertain+mean_over_seq_len_conflicted` | 1 |
| `final_token_conflicted+mean_over_seq_len_conflicted` | 11 |
| `final_token_uncertain` | 1 |
| `focus_token_conflicted` | 59 |
| `focus_token_conflicted+mean_over_seq_len_conflicted` | 15 |
| `focus_token_uncertain` | 4 |
| `focus_token_uncertain+mean_over_seq_len_conflicted` | 8 |
| `foundation_ensemble_all_disagree` | 226 |
| `mean_over_seq_len_conflicted` | 51 |
| `register_ensemble_all_disagree` | 17 |
| `trace_unstable` | 76 |

### Qwen2.5-1.5B (`qwen15b`)

- Source stage: `Stage 16`
- Activation file: `stage16_qwen15b_activations_20260519.npz`
- Best single Foundation accuracy: `0.8537`
- Ensemble-only accuracy / coverage: `0.9281` / `0.8988`
- Factor-consistent accuracy / coverage: `0.9661` / `0.8274`
- Stack accepted accuracy / coverage: `0.9949` / `0.7457`
- Stack accepted Drive accuracy: `0.9983`
- Stack accepted Register accuracy: `0.9966`

Selected layers:

| Task | Readout | Layer | Selection | Val acc | Test acc |
|---|---|---:|---|---:|---:|
| `foundation` | `focus_token` | `11` | `validation_selected_layer` | `0.9985` | `0.8202` |
| `foundation` | `final_token` | `21` | `validation_selected_layer` | `0.9747` | `0.8537` |
| `foundation` | `mean_over_seq_len` | `20` | `validation_selected_layer` | `0.8170` | `0.6526` |
| `drive` | `focus_token` | `11` | `foundation_selected_layer` | `1.0000` | `0.9209` |
| `drive` | `final_token` | `21` | `foundation_selected_layer` | `0.9881` | `0.9626` |
| `drive` | `mean_over_seq_len` | `20` | `foundation_selected_layer` | `0.8140` | `0.7066` |
| `register` | `focus_token` | `11` | `foundation_selected_layer` | `0.9955` | `0.8597` |
| `register` | `final_token` | `21` | `foundation_selected_layer` | `0.9955` | `0.8992` |
| `register` | `mean_over_seq_len` | `20` | `foundation_selected_layer` | `0.9955` | `0.9035` |

Suppression reasons:

| Reason | Count |
|---|---:|
| `drive_ensemble_all_disagree` | 22 |
| `factor_conflicted` | 115 |
| `final_token_conflicted` | 6 |
| `final_token_conflicted+focus_token_conflicted` | 23 |
| `final_token_conflicted+focus_token_conflicted+mean_over_seq_len_conflicted` | 50 |
| `final_token_conflicted+mean_over_seq_len_conflicted` | 16 |
| `final_token_uncertain+focus_token_conflicted+mean_over_seq_len_conflicted` | 2 |
| `focus_token_conflicted` | 28 |
| `focus_token_conflicted+mean_over_seq_len_conflicted` | 41 |
| `focus_token_uncertain+mean_over_seq_len_conflicted` | 1 |
| `foundation_ensemble_all_disagree` | 238 |
| `mean_over_seq_len_conflicted` | 18 |
| `register_ensemble_all_disagree` | 31 |
| `trace_unstable` | 7 |

## Boundary

This is a runtime-safe verifier run. Gold labels are used only for scoring, not for acceptance. Register is used as an internal consistency signal, not as a fresh beyond-text claim.
