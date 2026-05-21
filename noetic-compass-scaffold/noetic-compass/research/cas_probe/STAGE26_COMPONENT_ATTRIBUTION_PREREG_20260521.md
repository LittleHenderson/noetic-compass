# Stage 26 Component Attribution Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Motivation

Stage 24B and Stage 25 constrained within-layer decomposition. Stage 26 tests whether the distributed CAS readout localizes across attention heads and MLP blocks.

## Formal Anchor

ACBE Axiom 4.2 / joint-surjectivity framing: multiple component morphisms may jointly cover the residual-stream target even when no sparse within-layer feature is individually causal.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `model_revision` | `50f5173d932e8e61f858120bcb800b97af589f46` |
| `fixture` | `stage7_foundation_pilot_20260517.jsonl` |
| `stage7_activations` | `stage7_foundation_pilot_activations_20260517.npz` |
| `stage7_activation_sha256` | `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f` |
| `locked_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}` |
| `probe_task` | `Foundation interaction F1T..F7E` |
| `n_foundation_classes` | `28` |

## Component Scope

```json
{
  "attention_heads": {
    "heads_per_layer": 12,
    "hook_target": "per-head attention output before residual addition",
    "layers": [
      0,
      1,
      2,
      3,
      4,
      5
    ],
    "total_heads": 72
  },
  "mlp_blocks": {
    "hook_target": "MLP block output before residual addition",
    "layers": [
      0,
      1,
      2,
      3,
      4,
      5
    ],
    "neuron_level": "deferred; Stage 26 block-level only unless a follow-up is preregistered",
    "total_blocks": 6
  },
  "readout_position": "focus_token",
  "target_probe_layer": 6
}
```

## Method

- Fit/recover the Stage 7 Foundation probe on locked layer-6 focus-token activations.
- Run Pythia-160M on the locked Stage 7 fixture with hooks for layers 0..5.
- For each attention head and MLP block, capture its focus-token contribution before residual addition.
- Rank components by projection of their contribution onto the Stage 7 Foundation probe subspace.
- Ablate top-ranked components during a fresh forward pass and re-score the locked Foundation probe at layer 6.
- Compare targeted ablations against same-count random component ablations and same-layer random controls.
- Report per-class disruption and whether the effect is specific or global activation damage.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `capture_contract` | `pass_floor` | all 72 heads and 6 MLP blocks emit finite focus-token contribution tensors on the locked fixture |
| `alignment_enrichment` | `primary` | top-ranked components have higher Foundation-subspace projection than matched random components, empirical p < 0.05 |
| `targeted_ablation_drop` | `causal` | ablating top-ranked components drops Stage 7 Foundation probe accuracy more than same-count random component ablations, empirical p < 0.05 |
| `class_specificity` | `causal` | top-component ablation disruption is concentrated in the predicted/claimed Foundation classes rather than uniform global damage |
| `sanity_controls` | `pass_floor` | random same-layer ablations and no-op hooks preserve probe accuracy within the preregistered slack |

## Claim Boundary

- PASS status: `PASS_BOUNDED_COMPONENT_ATTRIBUTION`
- GREY status: `GREY_COMPONENT_ATTRIBUTION_UNDERPOWERED_OR_DIFFUSE`
- NULL status: `NULL_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED`
- Claim if PASS: CAS Harness localizes bounded Stage 7 Foundation readout signal to specific attention-head or MLP-block components with alignment and ablation evidence.
- Claim if NULL: The Stage 7 Foundation readout remains real, but this head/MLP-block attribution run did not localize the signal to separable transformer components beyond controls.
- Forbidden claims: Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal CAS compiler behavior, free-form generation control, or cross-model component generality from Stage 26.

## Execution Order

- `commit_preregistration_before_gpu_run`
- `implement_or_verify_component_hooks`
- `run_capture_and_alignment_ranking`
- `run_targeted_and_random_component_ablations`
- `record_report_and_artifact_manifest`

## Validation

- valid
