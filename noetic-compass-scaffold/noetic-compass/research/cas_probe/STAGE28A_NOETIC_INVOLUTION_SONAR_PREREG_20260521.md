# Stage 28A Noetic Involution Sonar Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Motivation

Foundation hard-partner token sonar failed because same-drive/different-register classes share vocabulary. Stage 28A tests the sharper hypothesis: Noetic involution pairs are formal opposites and should therefore be more separable/opposed in static token-signature space.

## Formal Anchor

TKS/Noetic involution structure: ^2<->^3, ^5<->^6, and ^8<->^9 are treated as typed opposition pairs. The sonar asks whether Pythia's output embedding geometry reflects that opposition.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `model_revision` | `50f5173d932e8e61f858120bcb800b97af589f46` |
| `fixture` | `stage9_elements_pilot_20260517.jsonl` |
| `stage9_activations` | `stage9_elements_pilot_activations_20260517.npz` |
| `activation_contract` | `stage24b_40_element_cpu_recap_prereg_20260521.json` |
| `locked_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 5}` |
| `task` | `10-way Noetic readout collapsed from the Stage 9 original-TKS 40 Element fixture` |
| `involution_pairs` | `(('^2', '^3'), ('^5', '^6'), ('^8', '^9'))` |

## Method

- Collapse the Stage 9 40-Element labels into 10 Noetic labels (^1..^9,^0).
- Fit the locked focus-token layer-5 Noetic probe on the existing Stage 9 activation artifact.
- Project the 10 Noetic probe directions through Pythia-160M output embeddings.
- Center and normalize each Noetic token-signature vector.
- Measure whether involution pairs (^2/^3, ^5/^6, ^8/^9) have lower cosine similarity / higher opposition than non-involution Noetic pairs.
- Compare the involution-opposition margin against random-direction controls.
- Report top positive and negative readable tokens for each Noetic class for audit, but do not use human interpretation as the pass gate.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B. |
| `probe_floor` | `pass_floor` | Noetic probe test accuracy is at least 0.50 on the 10-way collapsed Noetic task. |
| `readable_signature_floor` | `data_quality` | Readable top-token rate is at least 0.50. |
| `involution_opposition_margin` | `sonar_contrast` | non-involution mean cosine minus involution mean cosine is positive. |
| `random_direction_control` | `control` | Involution-opposition margin exceeds random-direction controls with empirical p < 0.05. |
| `pair_rank_floor` | `diagnostic` | At least 2 of 3 involution pairs fall below the global pairwise median cosine similarity. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_NOETIC_INVOLUTION_SONAR
- `grey_status`: GREY_NOETIC_INVOLUTION_SONAR_PARTIAL
- `null_status`: NULL_NOETIC_INVOLUTION_SONAR_NOT_ESTABLISHED
- `claim_if_pass`: Pythia-160M's Stage 9 Noetic readout directions show token-level opposition for the formal Noetic involution pairs, exceeding random-direction controls.
- `claim_if_null`: The Stage 9 Noetic readout may remain valid, but static output-embedding sonar did not establish token-level involution opposition under the preregistered controls.
- `scope_boundary`: Stage 28A tests Noetic classes collapsed from the 40-Element fixture. It does not test Noetic clusters, component-localized Noetic covers, or dynamic generation.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, 40-Element hard-partner resolution, Noetic clusters, raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28A.

## Execution Order

- commit_preregistration_before_result_run
- fit_collapsed_noetic_probe_from_stage9_artifact
- project_noetic_directions_to_token_space
- measure_involution_opposition_against_non_involution_and_random_controls
- record_bounded_result

## Validation

- valid
