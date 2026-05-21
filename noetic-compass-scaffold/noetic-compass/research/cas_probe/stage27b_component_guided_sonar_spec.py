"""Stage 27B component-guided contrast-sonar pre-registration.

Stage 24A/24B showed that static unembedding sonar can see broad CAS token
families but blurs hard-local contrasts. Stage 26/27A then localized and
path-patched a bounded Stage 7 Foundation attention-head family. Stage 27B
tests whether measuring token signatures through that validated component path
recovers hard-partner contrast signal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_SELECTED_STAGE27_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


@dataclass(frozen=True)
class Stage27BGate:
    name: str
    kind: str
    criterion: str


def stage27b_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage26_report": "stage26_component_attribution_20260521.json",
        "stage26_status": "PASS_BOUNDED_COMPONENT_ATTRIBUTION",
        "stage27a_report": "stage27_component_path_patching_20260521.json",
        "stage27a_status": "PASS_BOUNDED_COMPONENT_PATH_PATCHING",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "selected_components": _SELECTED_STAGE27_COMPONENTS,
    }


def stage27b_method() -> tuple[str, ...]:
    return (
        "Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.",
        "Project Foundation probe directions through Pythia-160M output embeddings to define readable target and hard-partner token sets.",
        "On held-out Stage 7 rows, run baseline, selected-head ablation, and selected-head patch-restoration forwards.",
        "Compute the component-path token-logit delta as patched_hidden - ablated_hidden at the locked readout position.",
        "For each target/hard-partner row, score mean(delta logits on target token set) minus mean(delta logits on hard-partner token set).",
        "Compare the selected-component path against same-layer/same-kind matched patch controls.",
        "Report overall and pair-family breakdowns for same-drive/different-register and different-drive/same-register hard partners.",
    )


def stage27b_gates() -> tuple[Stage27BGate, ...]:
    return (
        Stage27BGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest.",
        ),
        Stage27BGate(
            name="component_path_contract",
            kind="pass_floor",
            criterion="Stage 26 and Stage 27A source reports are PASS and selected components match the top-six family.",
        ),
        Stage27BGate(
            name="readable_signature_floor",
            kind="data_quality",
            criterion="Readable token-signature rate is at least 50%.",
        ),
        Stage27BGate(
            name="hard_partner_margin",
            kind="contrast",
            criterion="Mean selected component-path target-minus-hard-partner token margin is positive.",
        ),
        Stage27BGate(
            name="positive_share",
            kind="contrast",
            criterion="At least 55% of evaluated rows have positive target-minus-hard-partner token margin.",
        ),
        Stage27BGate(
            name="matched_component_control",
            kind="causal_control",
            criterion="Selected component-path margin exceeds matched patch-control margins with empirical p < 0.05.",
        ),
    )


def stage27b_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_COMPONENT_GUIDED_CONTRAST_SONAR",
        "grey_status": "GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL",
        "null_status": "NULL_COMPONENT_GUIDED_CONTRAST_SONAR_NOT_ESTABLISHED",
        "claim_if_pass": (
            "For Pythia-160M Stage 7 Foundation classes, hard-partner token signatures become "
            "more discriminative when measured through the causally validated component path than "
            "through static unembedding alone."
        ),
        "claim_if_null": (
            "Stage 26/27A component-path evidence remains valid, but the component path did not "
            "recover hard-partner token contrast under the preregistered sonar metric."
        ),
        "scope_boundary": (
            "Stage 27B is Foundation-first because the selected head path was validated on the "
            "Stage 7 Foundation readout. Original TKS 40-Element sonar remains a follow-on until "
            "a 40-Element component path is separately localized and path-patched."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal "
            "CAS compiler behavior, 40-Element component causality, free-form generation control, "
            "or cross-model component generality from Stage 27B."
        ),
    }


def stage27b_payload() -> dict[str, Any]:
    payload = {
        "stage": "27B",
        "status": "PREREGISTERED_NO_GPU",
        "motivation": (
            "Static sonar sees broad CAS token geometry but fails hard-local contrast. Stage 27B "
            "tests the solution suggested by Stage 26/27A: measure token signatures through the "
            "component path that causally carries the Foundation readout."
        ),
        "formal_anchor": (
            "Coverage-family framing: the selected attention-head family is treated as a local "
            "covering family for the Stage 7 Foundation readout. The sonar is measured on the "
            "component-path delta, not on an unlocalized residual-stream direction."
        ),
        "required_inputs": stage27b_required_inputs(),
        "method": stage27b_method(),
        "gates": [asdict(gate) for gate in stage27b_gates()],
        "claim_boundary": stage27b_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_gpu_run",
            "verify_stage26_and_stage27a_component_contracts",
            "derive_static_readable_token_sets_for_target_and_hard_partner_classes",
            "run_selected_component_path_delta_and_matched_patch_controls",
            "record_hard_partner_margins_and_claim_boundary",
        ],
    }
    payload["validation"] = validate_stage27b_payload(payload)
    return payload


def validate_stage27b_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_NO_GPU":
        errors.setdefault("status", []).append("Stage 27B starts as no-GPU preregistration.")
    inputs = payload.get("required_inputs", {})
    if tuple(inputs.get("selected_components", ())) != _SELECTED_STAGE27_COMPONENTS:
        errors.setdefault("required_inputs", []).append("selected components must match the Stage 26/27A top-six family.")
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27B must target the Stage 7 layer-6 Foundation readout.")
    gates = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("hard_partner_margin", "matched_component_control", "positive_share"):
        if required not in gates:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    boundary = payload.get("claim_boundary", {})
    if "40-Element" not in boundary.get("scope_boundary", ""):
        errors.setdefault("claim_boundary", []).append("scope boundary must reserve 40-Element component claims.")
    forbidden = boundary.get("forbidden_claims", "")
    if "exact neurons" not in forbidden or "free-form generation control" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound exact-neuron and generation claims.")
    return errors
