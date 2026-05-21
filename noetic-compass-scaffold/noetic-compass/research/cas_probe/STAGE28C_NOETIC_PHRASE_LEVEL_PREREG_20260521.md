# Stage 28C Noetic Phrase-Level Realization Pre-Registration

**Status:** `PREREGISTERED_LOCAL_FORWARD_PASS`

## Motivation

Stage 28B tested only the first token of each colloquial phrase and returned a bounded null. Stage 28C tests the explicit measurement critique: colloquialisms are phrase-level cognitive acts, so phrase-mean or phrase-last activations may carry the intended Noetic more faithfully than the first token.

## Formal Anchor

Noetic colloquialisms are treated as natural-language realizations. This stage changes the measurement position from a token-local readout to a phrase-level readout while preserving the same Stage 9 artifact and the same Stage 28B phrase fixture.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `model_revision` | `50f5173d932e8e61f858120bcb800b97af589f46` |
| `stage28b_fixture` | `reuse exact Stage 28B 40-row colloquialism fixture` |
| `n_colloquialism_rows` | `40` |
| `stage9_fixture` | `stage9_elements_pilot_20260517.jsonl` |
| `stage9_activations` | `stage9_elements_pilot_activations_20260517.npz` |
| `activation_contract` | `stage24b_40_element_cpu_recap_prereg_20260521.json` |
| `locked_layer` | `5` |
| `baseline_readout` | `{'runtime_name': 'phrase_first', 'stage9_key': 'X_focus', 'stage9_name': 'focus_token', 'definition': 'first tokenizer state overlapping the quoted colloquial phrase span'}` |
| `primary_phrase_level_readouts` | `({'runtime_name': 'phrase_mean', 'stage9_key': 'X_mean', 'stage9_name': 'mean_over_seq_len', 'definition': 'mean of all tokenizer states overlapping the quoted colloquial phrase span'}, {'runtime_name': 'phrase_last', 'stage9_key': 'X_final', 'stage9_name': 'final_token', 'definition': 'last tokenizer state overlapping the quoted colloquial phrase span'})` |
| `task` | `10-way Noetic realization readout from full-phrase natural-language colloquialisms` |
| `involution_pairs` | `(('^2', '^3'), ('^5', '^6'), ('^8', '^9'))` |

## Method

- Commit this pre-registration before any Stage 28C result artifact is generated.
- Reuse the exact 40-row Stage 28B colloquialism fixture; do not edit phrases after seeing results.
- Fit three collapsed Stage 9 Noetic probes at layer 5: X_focus, X_mean, and X_final.
- Run Pythia-160M forward on each carrier sentence and capture all layer-5 token states overlapping the quoted phrase span.
- Score phrase_first with the X_focus probe only as the Stage 28B baseline replication.
- Score phrase_mean with the X_mean probe and phrase_last with the X_final probe as the two preregistered phrase-level candidates.
- Apply a two-candidate correction by requiring exact-binomial p<0.025 for a PASS on either phrase-level candidate.
- Report per-Noetic rows and target-vs-involution-partner margins for each readout.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B. |
| `candidate_probe_floor` | `pass_floor` | A phrase-level candidate is eligible only if its matching Stage 9 Noetic probe has test accuracy at least 0.50. |
| `corrected_exact_accuracy` | `primary` | At least one eligible phrase-level candidate has exact Noetic accuracy at least 0.45 and exact-binomial p<0.025 against 10-way chance. |
| `target_probability_lift` | `primary` | The same passing candidate has mean target probability at least 0.15, i.e. +0.05 over 10-way chance. |
| `top2_accuracy` | `supporting` | The same passing candidate has top-2 Noetic accuracy at least 0.65. |
| `involution_partner_margin` | `supporting` | For rows whose Noetic has a formal involution partner, the same passing candidate beats partner probability on at least 0.60 of rows. |
| `baseline_improvement` | `diagnostic` | Report the delta from Stage 28B phrase_first exact accuracy; this is diagnostic, not required for PASS. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_NOETIC_PHRASE_LEVEL_REALIZATION
- `grey_status`: GREY_NOETIC_PHRASE_LEVEL_REALIZATION_PARTIAL
- `null_status`: NULL_NOETIC_PHRASE_LEVEL_REALIZATION_NOT_ESTABLISHED
- `claim_if_pass`: A preregistered phrase-level readout, using the matching Stage 9 readout probe, reads canonical Noetic colloquialisms above the corrected gates on Pythia-160M.
- `claim_if_null`: Stage 28B's first-token null is not rescued by the preregistered phrase-mean or phrase-last readouts under the matching Stage 9 Noetic probes.
- `scope_boundary`: Stage 28C tests phrase-level readout positions for single Noetic colloquialisms on Pythia-160M. It does not test Noetic clusters, retrained colloquialism probes, full TKS formulas, component-localized covers, exact neurons, or open-ended generation control.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, Noetic clusters, retrained colloquialism classifiers, 40-Element hard-partner resolution, raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28C.

## Execution Order

- commit_preregistration_before_result_run
- fit_collapsed_noetic_probes_for_focus_mean_final_from_stage9_artifact
- run_pythia_forward_on_locked_stage28b_colloquialism_fixture
- score_phrase_mean_and_phrase_last_hidden_states_with_matching_noetic_probes
- record_bounded_result

## Validation

- valid
