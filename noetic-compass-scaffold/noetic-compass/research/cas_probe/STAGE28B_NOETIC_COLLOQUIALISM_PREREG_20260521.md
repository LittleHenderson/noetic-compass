# Stage 28B Noetic Colloquialism Realization Pre-Registration

**Status:** `PREREGISTERED_LOCAL_FORWARD_PASS`

## Motivation

Static output-embedding sonar failed to resolve most hard local Noetic contrasts. Stage 28B tests a different route: feed the model natural-language colloquialisms that realize Noetic operators and read the resulting hidden states with the existing Stage 9 Noetic probe.

## Formal Anchor

η→ε bridge framing: colloquialisms are readable realization language (ε-side) rather than raw CAS symbols or static W_U projections. The probe tests whether the realized phrase re-enters the hidden-state Noetic readout (η-side).

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `model_revision` | `50f5173d932e8e61f858120bcb800b97af589f46` |
| `fixture_source` | `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarification 6 plus balanced source-compatible variants` |
| `n_colloquialism_rows` | `40` |
| `stage9_fixture` | `stage9_elements_pilot_20260517.jsonl` |
| `stage9_activations` | `stage9_elements_pilot_activations_20260517.npz` |
| `activation_contract` | `stage24b_40_element_cpu_recap_prereg_20260521.json` |
| `locked_probe_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 5}` |
| `runtime_readout` | `{'name': 'phrase_first_token', 'layer': 5, 'definition': 'first tokenizer token overlapping the quoted colloquial phrase span'}` |
| `task` | `10-way Noetic realization readout from natural-language colloquial phrases` |
| `involution_pairs` | `(('^2', '^3'), ('^5', '^6'), ('^8', '^9'))` |

## Locked Colloquialism Fixture

| Noetic | Name | Phrase |
|---|---|---|
| `^1` | Mind | paying attention |
| `^1` | Mind | making up my mind |
| `^1` | Mind | using my head |
| `^1` | Mind | becoming aware |
| `^2` | Positive | drawn to it like a moth to a flame |
| `^2` | Positive | speaks to me |
| `^2` | Positive | can't resist it |
| `^2` | Positive | pulled toward it |
| `^3` | Negative | can't stomach it |
| `^3` | Negative | rubs me the wrong way |
| `^3` | Negative | wouldn't touch it with a ten-foot pole |
| `^3` | Negative | pushed away from it |
| `^4` | Vibration | hit me hard |
| `^4` | Vibration | struck a chord |
| `^4` | Vibration | resonated with me |
| `^4` | Vibration | made an impression |
| `^5` | Female | we are the sum of our experiences |
| `^5` | Female | it's who I am |
| `^5` | Female | part of what makes me me |
| `^5` | Female | shaped by what came before |
| `^6` | Male | unpacking an idea |
| `^6` | Male | breaking it down |
| `^6` | Male | looking at what's underneath |
| `^6` | Male | pulling apart the argument |
| `^7` | Rhythm | practice makes perfect |
| `^7` | Rhythm | you are what you repeatedly do |
| `^7` | Rhythm | getting into a groove |
| `^7` | Rhythm | muscle memory |
| `^8` | Above/Cause | that reminds me |
| `^8` | Above/Cause | one thing leads to another |
| `^8` | Above/Cause | triggered a memory |
| `^8` | Above/Cause | made me think of something else |
| `^9` | Below/Effect | it just popped into my head |
| `^9` | Below/Effect | out of nowhere I thought of it |
| `^9` | Below/Effect | the thought came to me |
| `^9` | Below/Effect | it just clicked |
| `^0` | Idea | it's all in your head |
| `^0` | Idea | a thought on my mind |
| `^0` | Idea | something on my mind |
| `^0` | Idea | the idea itself |

## Method

- Commit this pre-registration before any Stage 28B result artifact is generated.
- Collapse the Stage 9 40-Element labels into the same 10 Noetic labels used in Stage 28A.
- Fit the locked focus-token layer-5 Noetic probe on the existing Stage 9 activation artifact.
- Construct a balanced 40-row colloquialism fixture: four natural-language phrases per Noetic class.
- Run Pythia-160M forward on each carrier sentence and capture the layer-5 hidden state at the first token overlapping the phrase span.
- Score each captured state with the locked Noetic probe.
- Evaluate exact accuracy, top-2 accuracy, mean target probability lift over chance, and target-vs-involution-partner margins.
- Report per-Noetic rows and failures for audit. Human readability of phrases is not a scoring gate because the fixture is locked natural language.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B. |
| `probe_floor` | `pass_floor` | Noetic probe test accuracy is at least 0.50 on the 10-way collapsed Stage 9 task. |
| `realization_exact_accuracy` | `primary` | Colloquial phrase exact Noetic accuracy is at least 0.45 and exact-binomial p<0.05 against 10-way chance. |
| `target_probability_lift` | `primary` | Mean target probability is at least 0.15, i.e. +0.05 over 10-way chance. |
| `top2_accuracy` | `supporting` | Top-2 Noetic accuracy is at least 0.65. |
| `involution_partner_margin` | `supporting` | For rows whose Noetic has a formal involution partner, target probability beats partner probability on at least 0.60 of rows. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_NOETIC_COLLOQUIALISM_REALIZATION
- `grey_status`: GREY_NOETIC_COLLOQUIALISM_REALIZATION_PARTIAL
- `null_status`: NULL_NOETIC_COLLOQUIALISM_REALIZATION_NOT_ESTABLISHED
- `claim_if_pass`: Pythia-160M's hidden states for canonical natural-language Noetic colloquialisms are readable by the Stage 9 Noetic probe above the preregistered gates, supporting the η→ε realization route for Noetic language.
- `claim_if_null`: Noetic readouts may remain valid on the Stage 9 fixture, but this colloquialism realization fixture did not establish that canonical Noetic phrases produce the matching hidden-state readout under the locked probe.
- `scope_boundary`: Stage 28B tests single Noetic colloquial phrases on Pythia-160M. It does not test Noetic clusters, full TKS formulas, component-localized covers, exact neurons, or open-ended generation control.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, Noetic clusters, 40-Element hard-partner resolution, raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28B.

## Execution Order

- commit_preregistration_before_result_run
- fit_collapsed_noetic_probe_from_stage9_artifact
- run_pythia_forward_on_locked_colloquialism_fixture
- score_phrase_hidden_states_with_noetic_probe
- record_bounded_result

## Validation

- valid
