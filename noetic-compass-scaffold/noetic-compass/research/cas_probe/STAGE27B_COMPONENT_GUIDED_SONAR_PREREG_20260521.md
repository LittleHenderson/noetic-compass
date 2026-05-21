# Stage 27B Component-Guided Contrast Sonar Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Motivation

Static sonar sees broad CAS token geometry but fails hard-local contrast. Stage 27B tests the solution suggested by Stage 26/27A: measure token signatures through the component path that causally carries the Foundation readout.

## Formal Anchor

Coverage-family framing: the selected attention-head family is treated as a local covering family for the Stage 7 Foundation readout. The sonar is measured on the component-path delta, not on an unlocalized residual-stream direction.

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
| `locked_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}` |
| `selected_components` | `('L5H3', 'L5H5', 'L5H0', 'L5H10', 'L1H6', 'L5H6')` |

## Method

- Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.
- Project Foundation probe directions through Pythia-160M output embeddings to define readable target and hard-partner token sets.
- On held-out Stage 7 rows, run baseline, selected-head ablation, and selected-head patch-restoration forwards.
- Compute the component-path token-logit delta as patched_hidden - ablated_hidden at the locked readout position.
- For each target/hard-partner row, score mean(delta logits on target token set) minus mean(delta logits on hard-partner token set).
- Compare the selected-component path against same-layer/same-kind matched patch controls.
- Report overall and pair-family breakdowns for same-drive/different-register and different-drive/same-register hard partners.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 7 activation artifact hash matches the locked manifest. |
| `component_path_contract` | `pass_floor` | Stage 26 and Stage 27A source reports are PASS and selected components match the top-six family. |
| `readable_signature_floor` | `data_quality` | Readable token-signature rate is at least 50%. |
| `hard_partner_margin` | `contrast` | Mean selected component-path target-minus-hard-partner token margin is positive. |
| `positive_share` | `contrast` | At least 55% of evaluated rows have positive target-minus-hard-partner token margin. |
| `matched_component_control` | `causal_control` | Selected component-path margin exceeds matched patch-control margins with empirical p < 0.05. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_COMPONENT_GUIDED_CONTRAST_SONAR
- `grey_status`: GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL
- `null_status`: NULL_COMPONENT_GUIDED_CONTRAST_SONAR_NOT_ESTABLISHED
- `claim_if_pass`: For Pythia-160M Stage 7 Foundation classes, hard-partner token signatures become more discriminative when measured through the causally validated component path than through static unembedding alone.
- `claim_if_null`: Stage 26/27A component-path evidence remains valid, but the component path did not recover hard-partner token contrast under the preregistered sonar metric.
- `scope_boundary`: Stage 27B is Foundation-first because the selected head path was validated on the Stage 7 Foundation readout. Original TKS 40-Element sonar remains a follow-on until a 40-Element component path is separately localized and path-patched.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal CAS compiler behavior, 40-Element component causality, free-form generation control, or cross-model component generality from Stage 27B.

## Execution Order

- commit_preregistration_before_gpu_run
- verify_stage26_and_stage27a_component_contracts
- derive_static_readable_token_sets_for_target_and_hard_partner_classes
- run_selected_component_path_delta_and_matched_patch_controls
- record_hard_partner_margins_and_claim_boundary

## Validation

- valid
