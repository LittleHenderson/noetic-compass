# Stage 27D Within-Head Slice Covers Pre-Registration

**Status:** `PREREGISTERED_GPU_RECOMMENDED`

## Motivation

Stage 27C found that hard-partner fineness lives in class-local attention-head covers. Stage 27D asks whether those class-local covers can be narrowed further to contiguous within-head vector slices without claiming literal neurons.

## Formal Anchor

Refined local-cover framing: Stage 26/27A gives a global head cover, Stage 27C gives class-indexed subcovers, and Stage 27D tests whether each class-indexed cover admits a smaller within-head subcover.

## Required Inputs

- `model`: `EleutherAI/pythia-160m`
- `model_revision`: `50f5173d932e8e61f858120bcb800b97af589f46`
- `fixture`: `stage7_foundation_pilot_20260517.jsonl`
- `stage7_activations`: `stage7_foundation_pilot_activations_20260517.npz`
- `stage7_activation_sha256`: `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`
- `stage27c_report`: `stage27c_per_class_component_covers_20260521.json`
- `stage27c_status`: `PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS`
- `locked_readout`: `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}`
- `global_selected_components`: `('L5H3', 'L5H5', 'L5H0', 'L5H10', 'L1H6', 'L5H6')`
- `source_cover_size`: `3`
- `slices_per_head`: `8`
- `slice_cover_size`: `8`
- `learn_rows_per_class`: `4`
- `eval_rows_per_class`: `4`

## Method

1. Commit this pre-registration and runner before any Stage 27D GPU result is generated.
2. Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.
3. Verify Stage 27C is PASS and was built from a locked Stage 7 artifact plus the Stage 26/27A six-head family.
4. Use Stage 27C per-class three-head covers as the candidate head set for each Foundation class.
5. Split each candidate head's 64-dimensional pre-output-projection slice into eight contiguous 8-dimensional slices.
6. Build a balanced slice-learning subset from Stage 7 train rows and a disjoint balanced evaluation subset from Stage 7 test rows.
7. For each learning row, globally ablate the six selected heads, then patch each candidate slice individually.
8. Score each candidate slice by target-vs-hard-partner Foundation probe-logit margin lift over the globally ablated state.
9. For each Foundation class, define an eight-slice class-local cover as the top slices by mean lift on learn rows for that class.
10. On held-out evaluation rows, compare class-local slice covers against same-size random slice covers sampled from the same class candidate heads.
11. Report the full Stage 27C class-head cover as the ceiling for each row; it is diagnostic, not the primary control.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 7 activation artifact hash matches the locked manifest. |
| `stage27c_contract` | `pass_floor` | Stage 27C source report is PASS, uses the locked artifact, and exposes per-class covers over the selected six-head family. |
| `learn_eval_separation` | `pass_floor` | Slice-cover learning rows come only from train split; scoring rows come only from test split. |
| `matched_random_slice_control` | `primary` | Per-class slice covers beat per-row random same-size slice-cover mean margin on at least 60% of eval rows with sign-test p<0.05. |
| `positive_margin_floor` | `primary` | At least 55% of eval rows have positive target-vs-hard-partner margin under the per-class slice cover. |
| `head_cover_gain_fraction` | `supporting` | Mean slice-cover gain is at least 25% of the mean Stage 27C class-head-cover gain. |
| `head_cover_ceiling` | `diagnostic` | Report slice-cover margin as a fraction of the full Stage 27C class-head cover margin; this is diagnostic, not required for PASS. |

## Claim Boundary

- `pass_status`: PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS
- `grey_status`: GREY_WITHIN_HEAD_SLICE_COVERS_PARTIAL
- `null_status`: NULL_WITHIN_HEAD_SLICE_COVERS_NOT_ESTABLISHED
- `claim_if_pass`: Within the Stage 27C per-class Pythia-160M attention-head covers, smaller contiguous within-head slices recover held-out hard-partner readout margins above matched random slice controls.
- `claim_if_null`: Stage 27C class-local head covers remain valid, but this contiguous within-head slice decomposition did not recover held-out hard-partner readout margins under the preregistered controls.
- `scope_boundary`: Stage 27D is bounded to contiguous slices of the pre-output-projection attention-head vectors inside the Pythia-160M Stage 27C Foundation covers. It is not exact neuron discovery, an MLP-neuron claim, a complete circuit, token sonar, Noetic/40-Element coverage, raw CAS-symbol understanding, or generation control.
- `forbidden_claims`: Do not claim exact neurons, complete circuits, MLP-neuron localization, raw CAS-symbol understanding, an internal CAS compiler, Noetic/40-Element component causality, free-form generation control, or cross-model component generality from Stage 27D.

## Validation

- No validation errors.
