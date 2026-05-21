# Stage 27A Component Path-Patching Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Motivation

Stage 26 established bounded component-level necessity. Stage 27A tests sufficiency by patching the selected clean component path back into an ablated forward pass.

## Formal Anchor

Noetic coverage / jointly-surjective-family framing: the selected attention-head family is tested as a local covering family for the Stage 7 Foundation readout, not as exact neurons.

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
| `locked_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}` |
| `selected_components` | `('L5H3', 'L5H5', 'L5H0', 'L5H10', 'L1H6', 'L5H6')` |

## Component Scope

```json
{
  "mlp_blocks": "not primary in Stage 27A because Stage 26 selected family is all attention heads",
  "patching_unit": "full-sequence selected-head slice, not only focus-token slice",
  "primary_components": {
    "components": [
      "L5H3",
      "L5H5",
      "L5H0",
      "L5H10",
      "L1H6",
      "L5H6"
    ],
    "hook_target": "input slices to GPT-NeoX attention.dense before output projection",
    "kind": "attention_head",
    "selection_source": "Stage 26 matched-control PASS top-six component family"
  },
  "readout_position": "focus_token",
  "target_probe_layer": 6
}
```

## Method

- Recover the Stage 7 Foundation probe on locked layer-6 focus-token activations.
- Load the Stage 26 selected attention-head family from the committed Stage 26 result.
- On held-out Stage 7 test rows, run baseline forwards and score the locked Foundation probe.
- Run targeted ablation by zeroing the selected head slices before attention.dense.
- Run patch restoration by caching clean selected head slices and inserting them into the ablated forward.
- Run matched random patch controls by ablating the selected heads while patching same-kind/layer non-selected heads.
- Report lost accuracy, recovered accuracy, recovery fraction, matched-control empirical p-values, and per-class restoration.

## Gates

| Gate | Kind | Criterion |
|---|---|---|
| `artifact_contract` | `pass_floor` | Stage 7 activation artifact hash matches the locked manifest and Stage 26 report is PASS |
| `ablation_replicates_stage26` | `causal` | selected-component ablation drops Foundation probe accuracy by at least 0.25 on the evaluated rows |
| `patch_restoration` | `causal_sufficiency` | patching clean selected-component slices restores at least 50% of the targeted-ablation lost accuracy |
| `matched_patch_control` | `causal_control` | selected-component patch restoration exceeds matched random patch restoration, empirical p < 0.05 |
| `class_restoration` | `diagnostic` | restoration is visible in the top disrupted Foundation classes and is not merely a no-op scoring artifact |
| `sanity_controls` | `pass_floor` | no-op and baseline repeat predictions match within the preregistered slack |

## Claim Boundary

- PASS status: `PASS_BOUNDED_COMPONENT_PATH_PATCHING`
- GREY status: `GREY_COMPONENT_PATH_PATCHING_PARTIAL`
- NULL status: `NULL_COMPONENT_PATH_PATCHING_NOT_ESTABLISHED`
- Claim if PASS: CAS Harness identifies a bounded Pythia-160M attention-head path for the Stage 7 Foundation readout with ablation necessity and patch-restoration sufficiency evidence.
- Claim if NULL: Stage 26 component ablation remains valid, but Stage 27A did not establish that the selected component family is sufficient to restore the readout under patching controls.
- Forbidden claims: Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal CAS compiler behavior, free-form generation control, or cross-model component generality from Stage 27A.

## Execution Order

- `commit_preregistration_before_gpu_run`
- `verify_stage26_selected_family`
- `run_baseline_targeted_ablation_and_patch_restoration`
- `run_matched_random_patch_controls`
- `record_report_and_artifact_manifest`

## Validation

- valid
