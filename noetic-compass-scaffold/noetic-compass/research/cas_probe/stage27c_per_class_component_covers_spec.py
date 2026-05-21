"""Stage 27C per-class component cover pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_SELECTED_STAGE27_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


@dataclass(frozen=True)
class Stage27CGate:
    name: str
    kind: str
    criterion: str


def stage27c_required_inputs() -> dict[str, Any]:
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
        "stage27b_report": "stage27b_component_guided_contrast_sonar_20260521.json",
        "stage27b_status": "GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "global_selected_components": _SELECTED_STAGE27_COMPONENTS,
        "per_class_cover_size": 3,
        "learn_rows_per_class": 4,
        "eval_rows_per_class": 4,
    }


def stage27c_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration before any Stage 27C GPU result is generated.",
        "Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.",
        "Verify Stage 26 and Stage 27A are PASS with the same selected six-head component family; Stage 27B is used only as the grey baseline.",
        "Build a balanced cover-learning subset from Stage 7 train rows and a disjoint balanced evaluation subset from Stage 7 test rows.",
        "For each cover-learning row, globally ablate the selected six heads, then patch each selected head individually.",
        "Score each individual head by target-vs-hard-partner Foundation probe-logit margin lift over the globally ablated state.",
        "For each Foundation class, define a three-head class-local cover as the top three selected heads by mean lift on learn rows for that class.",
        "On held-out evaluation rows, compare class-local covers against a same-size global-prefix cover and same-size random subsets of the selected six-head family.",
        "Report full six-head global cover as a ceiling, not as the same-size primary control.",
    )


def stage27c_gates() -> tuple[Stage27CGate, ...]:
    return (
        Stage27CGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest.",
        ),
        Stage27CGate(
            name="component_path_contract",
            kind="pass_floor",
            criterion="Stage 26 and Stage 27A source reports are PASS and selected components match the top-six attention-head family.",
        ),
        Stage27CGate(
            name="learn_eval_separation",
            kind="pass_floor",
            criterion="Class-cover learning rows come only from train split; scoring rows come only from test split.",
        ),
        Stage27CGate(
            name="same_size_global_control",
            kind="primary",
            criterion="Per-class covers beat the same-size global-prefix cover on mean target-vs-hard-partner probe-logit margin.",
        ),
        Stage27CGate(
            name="paired_global_sign_test",
            kind="primary",
            criterion="Per-class covers beat the same-size global-prefix cover on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27CGate(
            name="matched_random_subset_control",
            kind="primary",
            criterion="Per-class covers beat per-row random-subset mean margin on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27CGate(
            name="positive_margin_floor",
            kind="supporting",
            criterion="At least 55% of eval rows have positive target-vs-hard-partner margin under the per-class cover.",
        ),
        Stage27CGate(
            name="full_global_ceiling",
            kind="diagnostic",
            criterion="Report per-class cover margin as a fraction of the full six-head global cover margin; this is diagnostic, not required for PASS.",
        ),
    )


def stage27c_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS",
        "grey_status": "GREY_PER_CLASS_COMPONENT_COVERS_PARTIAL",
        "null_status": "NULL_PER_CLASS_COMPONENT_COVERS_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within the Stage 26/27A validated Pythia-160M attention-head family, class-local Foundation covers "
            "improve held-out hard-partner readout margins over same-size global and random subset controls."
        ),
        "claim_if_null": (
            "The global Stage 26/27A component path remains valid, but decomposing it into three-head per-class "
            "covers did not improve held-out hard-partner readout margins under the preregistered controls."
        ),
        "scope_boundary": (
            "Stage 27C is bounded to Pythia-160M Stage 7 Foundation probe-logit margins inside the already validated "
            "six-head component family. It does not test Noetic/40-Element covers, token sonar, exact neurons, or generation control."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, internal CAS compiler behavior, "
            "Noetic/40-Element component causality, free-form generation control, or cross-model component generality from Stage 27C."
        ),
    }


def stage27c_payload() -> dict[str, Any]:
    payload = {
        "stage": "27C",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 26/27A localized and path-patched a global six-head Foundation cover, while Stage 27B showed only "
            "partial aggregate token contrast. Stage 27C tests whether hard-partner distinctions live in class-local "
            "subcovers inside the validated head family."
        ),
        "formal_anchor": (
            "Coverage-family framing: the six selected heads form a local cover for the Foundation readout. Stage 27C "
            "asks whether smaller class-indexed subcovers refine that cover for specific Foundation hard-partner distinctions."
        ),
        "required_inputs": stage27c_required_inputs(),
        "method": stage27c_method(),
        "gates": [asdict(gate) for gate in stage27c_gates()],
        "claim_boundary": stage27c_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_gpu_run",
            "verify_stage26_and_stage27a_component_contracts",
            "learn_per_class_covers_on_train_split_only",
            "evaluate_hard_partner_margins_on_test_split_only",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27c_payload(payload)
    return payload


def validate_stage27c_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27C starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if tuple(inputs.get("global_selected_components", ())) != _SELECTED_STAGE27_COMPONENTS:
        errors.setdefault("required_inputs", []).append("selected components must match the Stage 26/27A top-six family.")
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27C must target the Stage 7 layer-6 Foundation readout.")
    if int(inputs.get("per_class_cover_size", 0)) >= len(_SELECTED_STAGE27_COMPONENTS):
        errors.setdefault("required_inputs", []).append("per-class cover must be a strict subcover of the selected family.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("same_size_global_control", "paired_global_sign_test", "matched_random_subset_control", "learn_eval_separation"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "exact neurons" not in forbidden or "free-form generation control" not in forbidden or "Noetic/40-Element" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound exact-neuron, generation, and non-Foundation claims.")
    return errors
