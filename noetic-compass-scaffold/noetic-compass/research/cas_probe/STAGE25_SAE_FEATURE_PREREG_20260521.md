# Stage 25 SAE Feature Localization Pre-Registration

**Status:** `AUTHORIZED_GPU_SAE_PREREGISTERED`

## Motivation

Stage 24A/24B static sonar detected broad token geometry but failed hard local contrasts. This suggests polysemantic readout directions and motivates SAE feature decomposition.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `fixture` | `stage7_foundation_pilot_20260517.jsonl` |
| `activations` | `stage7_foundation_pilot_activations_20260517.npz` |
| `activation_layer` | `6` |
| `activation_readout` | `focus_token` |
| `probe_labels` | `28` |
| `probe_task` | `Foundation interaction F1T..F7E` |

## Training Config

| Field | Value |
|---|---|
| `sae_family` | `residual_stream_relu_sae` |
| `input_dim` | `768` |
| `feature_multiplier` | `8` |
| `n_features` | `6144` |
| `optimizer` | `AdamW` |
| `learning_rate` | `0.001` |
| `batch_size` | `1024` |
| `max_steps` | `5000` |
| `l1_coefficient` | `0.001` |
| `dead_feature_threshold` | `1e-06` |
| `random_seed` | `25025` |
| `expected_gpu_budget_usd` | `200-500` |

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `reconstruction_quality` | `pass_floor` | heldout_explained_variance >= 0.80 and heldout_mse finite |
| `sparsity_noncollapse` | `pass_floor` | mean_active_features_per_row between 5 and 250 and dead_feature_rate < 0.80 |
| `cas_alignment` | `primary` | top SAE decoder features align to Stage 7 Foundation probe directions above matched random decoder-vector controls, empirical p < 0.05 |
| `feature_specificity` | `primary` | CAS-aligned features show heldout class-selective activation; top-class mean activation exceeds random feature controls, empirical p < 0.05 |
| `causal_feature_drop` | `causal` | removing top CAS-aligned SAE feature contributions degrades Stage 7 Foundation probe accuracy more than matched random feature removals |

## Claim Boundary

- PASS status: `PASS_BOUNDED_SAE_FEATURE_READOUT`
- GREY status: `GREY_SAE_FEATURE_READOUT_UNDERPOWERED_OR_TEXT_EXPLAINED`
- NULL status: `NULL_SAE_FEATURE_READOUT_NOT_ESTABLISHED`
- Claim if PASS: In this first pilot, SAE-derived features provide a bounded, inspectable feature basis from which CAS Foundation signals are recoverable above pre-registered baselines on the tested model, layer, fixture, and held-out split.
- Claim if PASS with ablation: If targeted SAE-feature removal clears the causal gate, CAS Harness may also claim readout-level causal relevance of the selected feature set under controls.
- Claim if NULL: The Stage 7 Foundation readout remains real, but this SAE configuration did not recover sparse CAS-aligned features beyond controls.
- Claim if GREY: SAE-derived features show suggestive structure, but the result is underpowered, text-explained, unstable across controls, or not reliably above baseline.
- Forbidden claims: Do not claim exact causal neurons, true CAS neurons, model thoughts, a complete neuron-by-neuron causal map, generated-language steering, raw CAS-symbol understanding, an internal CAS compiler, solved black-box interpretability, or generalization to arbitrary models/tasks/frontier scale.

## Execution Order

- `commit_preregistration_before_gpu_run`
- `run_stage25_sae_training`
- `rank_features_by_cas_alignment`
- `evaluate_feature_specificity`
- `evaluate_feature_removal_against_random_controls`
- `record_report_and_checkpoint_manifest`

## Validation

- valid
