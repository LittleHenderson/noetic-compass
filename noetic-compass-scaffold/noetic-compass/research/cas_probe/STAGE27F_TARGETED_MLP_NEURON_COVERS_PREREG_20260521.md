# Stage 27F Targeted MLP-Neuron Covers Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27E localized class-specific Foundation readout evidence to single attention-head coordinates. Stage 27F tests whether nearby MLP intermediate neurons in the same targeted layers causally support the same hard-partner margins.

## Formal Anchor

Targeted local-cover refinement: Stage 27E supplies per-class coordinate covers that select candidate layers; Stage 27F asks whether sparse MLP-neuron covers inside those layers form causal supports for the same readout margins.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_activations`: `stage7_foundation_pilot_activations_20260517.npz`
- `stage7_activation_sha256`: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- `stage27c_report`: `stage27c_per_class_component_covers_20260521.json`
- `stage27c_status`: `PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS`
- `stage27e_report`: `stage27e_single_dim_coordinate_covers_20260521.json`
- `stage27e_status`: `PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS`
- `locked_readout`: `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}`
- `global_selected_components`: `('L5H3', 'L5H5', 'L5H0', 'L5H10', 'L1H6', 'L5H6')`
- `candidate_layers`: `per-class layers from Stage 27E coordinate covers`
- `mlp_intermediate_dim`: `3072`
- `neuron_cover_size`: `32`
- `learn_rows_per_class`: `4`
- `eval_rows_per_class`: `4`

## Method

1. Commit this pre-registration and runner before any Stage 27F GPU result is generated.
2. Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.
3. Verify Stage 27C and Stage 27E are PASS with the locked artifact and selected six-head family.
4. Use Stage 27E per-class single-coordinate covers only to choose candidate MLP layers for each Foundation class.
5. Capture activated MLP intermediate neurons at the focus token for those candidate layers on train rows.
6. Rank every candidate MLP neuron by first-order target-vs-hard-partner margin contribution: activation_j times the output-projection alignment with the probe margin direction.
7. For each Foundation class, define a 32-neuron cover as the top ranked candidate neurons learned only on train rows.
8. On held-out test rows, ablate the per-class neuron cover from the clean forward pass and measure target-vs-hard-partner margin drop.
9. Compare targeted drops against same-size random neuron covers with the same per-layer count as the targeted cover.
10. Patch-back of the targeted cover is a sanity/recovery check; the primary discovery gate is targeted ablation drop above matched random ablations.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 7 activation artifact hash matches the locked manifest. |
| `stage27c_contract` | `pass_floor` | Stage 27C source report is PASS and exposes per-class attention-head covers. |
| `stage27e_contract` | `pass_floor` | Stage 27E source report is PASS and exposes single-coordinate covers for per-class candidate-layer targeting. |
| `learn_eval_separation` | `pass_floor` | Neuron-cover learning rows come only from train split; scoring rows come only from test split. |
| `matched_random_neuron_control` | `primary` | Per-class neuron-cover ablation drop beats per-row random same-size/same-layer neuron-cover mean drop on at least 60% of eval rows with sign-test p<0.05. |
| `positive_drop_floor` | `primary` | At least 55% of eval rows have positive target-vs-hard-partner margin drop under targeted neuron-cover ablation. |
| `mean_drop_floor` | `primary` | Mean targeted neuron-cover drop is positive and greater than mean matched-random neuron-cover drop. |
| `patchback_sanity` | `sanity` | Patch-back after targeted ablation restores the clean margin within numerical tolerance on average. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS
- `grey_status`: GREY_TARGETED_MLP_NEURON_COVERS_PARTIAL
- `null_status`: NULL_TARGETED_MLP_NEURON_COVERS_NOT_ESTABLISHED
- `claim_if_pass`: Within MLP layers targeted by Stage 27E attention-coordinate covers, sparse MLP intermediate-neuron covers causally support class-specific Foundation hard-partner readout margins above matched same-layer random neuron controls.
- `claim_if_null`: Stage 27C/27D/27E attention-coordinate localization remains valid, but this targeted MLP-neuron cover method did not establish held-out causal margin drops above matched random neuron controls.
- `scope_boundary`: Stage 27F is bounded to Pythia-160M MLP intermediate neurons in layers selected from Stage 27E coordinate covers, scored against the trained Stage 7 Foundation readout. It is not a complete circuit, not all neurons in the model, not token sonar, not Noetic/40-Element coverage, not raw CAS-symbol understanding, and not generation control.
- `forbidden_claims`: Do not claim complete circuits, model-wide exact causal explanation, raw CAS-symbol understanding, an internal CAS compiler, Noetic/40-Element component causality, free-form generation control, or cross-model component generality from Stage 27F.

## Validation

- No validation errors.
