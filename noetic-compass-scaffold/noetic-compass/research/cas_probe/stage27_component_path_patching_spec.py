"""Stage 27A component path-patching preregistration.

Stage 26 showed that a bounded family of Pythia-160M attention heads carries a
causally load-bearing portion of the Stage 7 Foundation readout. Stage 27A
tests the next rung: whether the same component family is sufficient to restore
the readout after targeted ablation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27Gate:
    name: str
    kind: str
    criterion: str


_SELECTED_STAGE26_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


def stage27_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage26_report": "stage26_component_attribution_20260521.json",
        "stage26_status": "PASS_BOUNDED_COMPONENT_ATTRIBUTION",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "selected_components": _SELECTED_STAGE26_COMPONENTS,
    }


def stage27_component_scope() -> dict[str, Any]:
    return {
        "primary_components": {
            "kind": "attention_head",
            "components": _SELECTED_STAGE26_COMPONENTS,
            "hook_target": "input slices to GPT-NeoX attention.dense before output projection",
            "selection_source": "Stage 26 matched-control PASS top-six component family",
        },
        "patching_unit": "full-sequence selected-head slice, not only focus-token slice",
        "target_probe_layer": 6,
        "readout_position": "focus_token",
        "mlp_blocks": "not primary in Stage 27A because Stage 26 selected family is all attention heads",
    }


def stage27_method() -> tuple[str, ...]:
    return (
        "Recover the Stage 7 Foundation probe on locked layer-6 focus-token activations.",
        "Load the Stage 26 selected attention-head family from the committed Stage 26 result.",
        "On held-out Stage 7 test rows, run baseline forwards and score the locked Foundation probe.",
        "Run targeted ablation by zeroing the selected head slices before attention.dense.",
        "Run patch restoration by caching clean selected head slices and inserting them into the ablated forward.",
        "Run matched random patch controls by ablating the selected heads while patching same-kind/layer non-selected heads.",
        "Report lost accuracy, recovered accuracy, recovery fraction, matched-control empirical p-values, and per-class restoration.",
    )


def stage27_gates() -> tuple[Stage27Gate, ...]:
    return (
        Stage27Gate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest and Stage 26 report is PASS",
        ),
        Stage27Gate(
            name="ablation_replicates_stage26",
            kind="causal",
            criterion="selected-component ablation drops Foundation probe accuracy by at least 0.25 on the evaluated rows",
        ),
        Stage27Gate(
            name="patch_restoration",
            kind="causal_sufficiency",
            criterion="patching clean selected-component slices restores at least 50% of the targeted-ablation lost accuracy",
        ),
        Stage27Gate(
            name="matched_patch_control",
            kind="causal_control",
            criterion="selected-component patch restoration exceeds matched random patch restoration, empirical p < 0.05",
        ),
        Stage27Gate(
            name="class_restoration",
            kind="diagnostic",
            criterion="restoration is visible in the top disrupted Foundation classes and is not merely a no-op scoring artifact",
        ),
        Stage27Gate(
            name="sanity_controls",
            kind="pass_floor",
            criterion="no-op and baseline repeat predictions match within the preregistered slack",
        ),
    )


def stage27_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_COMPONENT_PATH_PATCHING",
        "grey_status": "GREY_COMPONENT_PATH_PATCHING_PARTIAL",
        "null_status": "NULL_COMPONENT_PATH_PATCHING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "CAS Harness identifies a bounded Pythia-160M attention-head path for the Stage 7 "
            "Foundation readout with ablation necessity and patch-restoration sufficiency evidence."
        ),
        "claim_if_null": (
            "Stage 26 component ablation remains valid, but Stage 27A did not establish that the "
            "selected component family is sufficient to restore the readout under patching controls."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal "
            "CAS compiler behavior, free-form generation control, or cross-model component generality "
            "from Stage 27A."
        ),
    }


def stage27_payload() -> dict[str, Any]:
    payload = {
        "stage": "27A",
        "status": "PREREGISTERED_NO_GPU",
        "motivation": (
            "Stage 26 established bounded component-level necessity. Stage 27A tests sufficiency by "
            "patching the selected clean component path back into an ablated forward pass."
        ),
        "formal_anchor": (
            "Noetic coverage / jointly-surjective-family framing: the selected attention-head family "
            "is tested as a local covering family for the Stage 7 Foundation readout, not as exact neurons."
        ),
        "required_inputs": stage27_required_inputs(),
        "component_scope": stage27_component_scope(),
        "method": stage27_method(),
        "gates": [asdict(gate) for gate in stage27_gates()],
        "claim_boundary": stage27_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_gpu_run",
            "verify_stage26_selected_family",
            "run_baseline_targeted_ablation_and_patch_restoration",
            "run_matched_random_patch_controls",
            "record_report_and_artifact_manifest",
        ],
    }
    payload["validation"] = validate_stage27_payload(payload)
    return payload


def validate_stage27_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_NO_GPU":
        errors.setdefault("status", []).append("Stage 27A starts as no-GPU preregistration")
    inputs = payload.get("required_inputs", {})
    selected = tuple(inputs.get("selected_components", ()))
    if selected != _SELECTED_STAGE26_COMPONENTS:
        errors.setdefault("required_inputs", []).append("selected components must match Stage 26 top-six family")
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27A must target Stage 7 layer 6")
    scope = payload.get("component_scope", {})
    if scope.get("primary_components", {}).get("kind") != "attention_head":
        errors.setdefault("component_scope", []).append("Stage 27A primary components must be attention heads")
    gates = [gate.get("name") for gate in payload.get("gates", [])]
    for required in ("patch_restoration", "matched_patch_control", "ablation_replicates_stage26"):
        if required not in gates:
            errors.setdefault("gates", []).append(f"missing {required}")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "exact neurons" not in forbidden or "free-form generation control" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound exact-neuron and generation claims")
    return errors
