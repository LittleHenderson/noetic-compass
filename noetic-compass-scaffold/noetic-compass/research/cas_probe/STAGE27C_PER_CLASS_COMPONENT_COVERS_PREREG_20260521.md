# Stage 27C Per-Class Component Covers Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 26/27A localized and path-patched a global six-head Foundation cover, while Stage 27B showed only partial aggregate token contrast. Stage 27C tests whether hard-partner distinctions live in class-local subcovers inside the validated head family.

## Formal Anchor

Coverage-family framing: the six selected heads form a local cover for the Foundation readout. Stage 27C asks whether smaller class-indexed subcovers refine that cover for specific Foundation hard-partner distinctions.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `model_revision` | `50f5173d932e8e61f858120bcb800b97af589f46` |
| `fixture` | `stage7_foundation_pilot_20260517.jsonl` |
| `stage7_activations` | `stage7_foundation_pilot_activations_20260517.npz` |
| `stage7_activation_sha256` | `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f` |
| `stage26_report` | `stage26_component_attribution_20260521.json` |
| `stage26_status` | `PASS_BOUNDED_COMPONENT_ATTRIBUTION` |
| `stage27a_report` | `stage27_component_path_patching_20260521.json` |
| `stage27a_status` | `PASS_BOUNDED_COMPONENT_PATH_PATCHING` |
| `stage27b_report` | `stage27b_component_guided_contrast_sonar_20260521.json` |
| `stage27b_status` | `GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL` |
| `locked_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}` |
| `global_selected_components` | `('L5H3', 'L5H5', 'L5H0', 'L5H10', 'L1H6', 'L5H6')` |
| `per_class_cover_size` | `3` |
| `learn_rows_per_class` | `4` |
| `eval_rows_per_class` | `4` |

## Method

- Commit this pre-registration before any Stage 27C GPU result is generated.
- Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.
- Verify Stage 26 and Stage 27A are PASS with the same selected six-head component family; Stage 27B is used only as the grey baseline.
- Build a balanced cover-learning subset from Stage 7 train rows and a disjoint balanced evaluation subset from Stage 7 test rows.
- For each cover-learning row, globally ablate the selected six heads, then patch each selected head individually.
- Score each individual head by target-vs-hard-partner Foundation probe-logit margin lift over the globally ablated state.
- For each Foundation class, define a three-head class-local cover as the top three selected heads by mean lift on learn rows for that class.
- On held-out evaluation rows, compare class-local covers against a same-size global-prefix cover and same-size random subsets of the selected six-head family.
- Report full six-head global cover as a ceiling, not as the same-size primary control.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 7 activation artifact hash matches the locked manifest. |
| `component_path_contract` | `pass_floor` | Stage 26 and Stage 27A source reports are PASS and selected components match the top-six attention-head family. |
| `learn_eval_separation` | `pass_floor` | Class-cover learning rows come only from train split; scoring rows come only from test split. |
| `same_size_global_control` | `primary` | Per-class covers beat the same-size global-prefix cover on mean target-vs-hard-partner probe-logit margin. |
| `paired_global_sign_test` | `primary` | Per-class covers beat the same-size global-prefix cover on at least 60% of eval rows with sign-test p<0.05. |
| `matched_random_subset_control` | `primary` | Per-class covers beat per-row random-subset mean margin on at least 60% of eval rows with sign-test p<0.05. |
| `positive_margin_floor` | `supporting` | At least 55% of eval rows have positive target-vs-hard-partner margin under the per-class cover. |
| `full_global_ceiling` | `diagnostic` | Report per-class cover margin as a fraction of the full six-head global cover margin; this is diagnostic, not required for PASS. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS
- `grey_status`: GREY_PER_CLASS_COMPONENT_COVERS_PARTIAL
- `null_status`: NULL_PER_CLASS_COMPONENT_COVERS_NOT_ESTABLISHED
- `claim_if_pass`: Within the Stage 26/27A validated Pythia-160M attention-head family, class-local Foundation covers improve held-out hard-partner readout margins over same-size global and random subset controls.
- `claim_if_null`: The global Stage 26/27A component path remains valid, but decomposing it into three-head per-class covers did not improve held-out hard-partner readout margins under the preregistered controls.
- `scope_boundary`: Stage 27C is bounded to Pythia-160M Stage 7 Foundation probe-logit margins inside the already validated six-head component family. It does not test Noetic/40-Element covers, token sonar, exact neurons, or generation control.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal CAS compiler behavior, Noetic/40-Element component causality, free-form generation control, or cross-model component generality from Stage 27C.

## Execution Order

- commit_preregistration_before_gpu_run
- verify_stage26_and_stage27a_component_contracts
- learn_per_class_covers_on_train_split_only
- evaluate_hard_partner_margins_on_test_split_only
- record_bounded_result

## Validation

- valid
