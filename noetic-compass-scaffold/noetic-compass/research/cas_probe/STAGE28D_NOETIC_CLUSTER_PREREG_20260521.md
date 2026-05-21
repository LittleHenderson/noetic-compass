# Stage 28D Noetic Cluster Realization Pre-Registration

**Status:** `PREREGISTERED_LOCAL_FORWARD_PASS`

## Motivation

Stages 28B/C showed that single-Noetic colloquialisms do not cleanly re-enter the Stage 9 Noetic probe space. Stage 28D tests the user's cluster hypothesis directly: compound phrases may be represented as joint Noetic elevations rather than single-label readouts.

## Formal Anchor

Noetic clusters are treated as compound natural-language realizations. Because the target is multi-label, Stage 28D evaluates joint target-pair elevation over replacement controls instead of single-class exact accuracy.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `model_revision` | `50f5173d932e8e61f858120bcb800b97af589f46` |
| `cluster_fixture` | `24 compound colloquialisms: 8 two-Noetic clusters x 3 phrases` |
| `n_cluster_rows` | `24` |
| `stage9_fixture` | `stage9_elements_pilot_20260517.jsonl` |
| `stage9_activations` | `stage9_elements_pilot_activations_20260517.npz` |
| `activation_contract` | `stage24b_40_element_cpu_recap_prereg_20260521.json` |
| `locked_layer` | `5` |
| `primary_phrase_level_readouts` | `({'runtime_name': 'phrase_mean', 'stage9_key': 'X_mean', 'stage9_name': 'mean_over_seq_len', 'definition': 'mean of all tokenizer states overlapping the quoted cluster phrase span'}, {'runtime_name': 'phrase_last', 'stage9_key': 'X_final', 'stage9_name': 'final_token', 'definition': 'last tokenizer state overlapping the quoted cluster phrase span'})` |
| `task` | `multi-label Noetic cluster realization from compound natural-language colloquialisms` |

## Locked Cluster Fixture

| Cluster | Targets | Phrase |
|---|---|---|
| `attraction_cause` | `^2, ^8` | that reminds me of something I'm drawn to |
| `attraction_cause` | `^2, ^8` | one thing leads me back to what speaks to me |
| `attraction_cause` | `^2, ^8` | a memory triggered a pull toward it |
| `aversion_analysis` | `^3, ^6` | I'm breaking down why I can't stomach it |
| `aversion_analysis` | `^3, ^6` | pulling apart the argument that rubs me the wrong way |
| `aversion_analysis` | `^3, ^6` | looking underneath what pushes me away |
| `resonance_rhythm` | `^4, ^7` | it struck a chord and kept coming back |
| `resonance_rhythm` | `^4, ^7` | the feeling resonated until I got into a groove |
| `resonance_rhythm` | `^4, ^7` | it made an impression through repeated practice |
| `mind_analysis` | `^1, ^6` | paying attention while unpacking the idea |
| `mind_analysis` | `^1, ^6` | using my head to break it down |
| `mind_analysis` | `^1, ^6` | making up my mind by looking underneath |
| `identity_arising` | `^5, ^9` | out of nowhere it felt like part of who I am |
| `identity_arising` | `^5, ^9` | the thought came to me as something that makes me me |
| `identity_arising` | `^5, ^9` | it clicked as shaped by what came before |
| `attraction_resonance` | `^2, ^4` | it resonated with me and pulled me toward it |
| `attraction_resonance` | `^2, ^4` | it struck a chord because it speaks to me |
| `attraction_resonance` | `^2, ^4` | the impression made it hard to resist |
| `aversion_vibration` | `^3, ^4` | it hit me hard and rubbed me the wrong way |
| `aversion_vibration` | `^3, ^4` | the impression made me unable to stomach it |
| `aversion_vibration` | `^3, ^4` | it struck a sour chord I would not touch |
| `mind_rhythm` | `^1, ^7` | I keep paying attention until practice makes perfect |
| `mind_rhythm` | `^1, ^7` | using my head while getting into a groove |
| `mind_rhythm` | `^1, ^7` | making up my mind through repeated practice |

## Method

- Commit this pre-registration before any Stage 28D result artifact is generated.
- Use the locked 24-row compound-colloquialism cluster fixture.
- Fit collapsed Stage 9 Noetic probes at layer 5 for X_mean and X_final.
- Run Pythia-160M forward on each carrier sentence and capture all layer-5 token states overlapping the quoted phrase span.
- Score phrase_mean with the X_mean probe and phrase_last with the X_final probe.
- Use probe decision logits, standardized within each row, because clusters are multi-label and single-label softmax exact accuracy is the wrong target.
- For each row, compute the target-pair z-score and compare it against the maximum hard replacement-control pair score.
- Apply a two-candidate correction by requiring sign-test p<0.025 for a PASS on either phrase-level candidate.
- Report top labels and per-cluster margins for audit.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B. |
| `candidate_probe_floor` | `pass_floor` | A phrase-level candidate is eligible only if its matching Stage 9 Noetic probe has test accuracy at least 0.50. |
| `target_pair_margin` | `primary` | At least one eligible phrase-level candidate has mean target-pair z margin over hard replacement controls > 0. |
| `corrected_sign_test` | `primary` | The same candidate has at least 18/24 positive target-over-control rows and sign-test p<0.025. |
| `top4_target_coverage` | `supporting` | The same candidate has mean target-labels-in-top4 at least 0.90 out of 2. |
| `per_cluster_coverage` | `diagnostic` | Report positive-row share per cluster; this is diagnostic, not required for PASS. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_NOETIC_CLUSTER_REALIZATION
- `grey_status`: GREY_NOETIC_CLUSTER_REALIZATION_PARTIAL
- `null_status`: NULL_NOETIC_CLUSTER_REALIZATION_NOT_ESTABLISHED
- `claim_if_pass`: A preregistered phrase-level readout shows that compound Noetic cluster colloquialisms jointly elevate their two target Noetics over hard replacement controls on Pythia-160M.
- `claim_if_null`: Compound Noetic cluster colloquialisms do not jointly elevate their target Noetics over hard replacement controls under the preregistered phrase-level readouts.
- `scope_boundary`: Stage 28D tests multi-label two-Noetic clusters on Pythia-160M using existing Stage 9 probes. It does not train a cluster classifier, test full formulas/equations, prove exact neurons, or establish generation control.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, retrained cluster classifiers, full TKS formulas, raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28D.

## Execution Order

- commit_preregistration_before_result_run
- fit_collapsed_noetic_probes_for_mean_and_final_from_stage9_artifact
- run_pythia_forward_on_locked_cluster_fixture
- score_joint_target_pair_elevation_against_hard_controls
- record_bounded_result

## Validation

- valid
