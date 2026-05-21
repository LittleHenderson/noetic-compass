"""Stage 27E single-coordinate attention-head cover pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_SELECTED_STAGE27_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


@dataclass(frozen=True)
class Stage27EGate:
    name: str
    kind: str
    criterion: str


def stage27e_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage27c_report": "stage27c_per_class_component_covers_20260521.json",
        "stage27c_status": "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS",
        "stage27d_report": "stage27d_within_head_slice_covers_20260521.json",
        "stage27d_status": "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "global_selected_components": _SELECTED_STAGE27_COMPONENTS,
        "source_cover_size": 3,
        "head_dim": 64,
        "slices_per_head": 64,
        "coordinate_cover_size": 8,
        "learn_rows_per_class": 4,
        "eval_rows_per_class": 4,
    }


def stage27e_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27E GPU result is generated.",
        "Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.",
        "Verify Stage 27C and Stage 27D are PASS with the locked artifact and selected six-head family.",
        "Use Stage 27C per-class three-head covers as the candidate head set for each Foundation class.",
        "Split each candidate head's 64-dimensional pre-output-projection vector into 64 single-coordinate slices.",
        "Build a balanced coordinate-learning subset from Stage 7 train rows and a disjoint balanced evaluation subset from Stage 7 test rows.",
        "For each learning row, globally ablate the six selected heads, then patch each candidate coordinate individually.",
        "Score each candidate coordinate by target-vs-hard-partner Foundation probe-logit margin lift over the globally ablated state.",
        "For each Foundation class, define an eight-coordinate class-local cover as the top coordinates by mean lift on learn rows for that class.",
        "On held-out evaluation rows, compare class-local coordinate covers against same-size random coordinate covers sampled from the same class candidate heads.",
        "Report the Stage 27C class-head cover and Stage 27D eight-dimensional slice-cover results as ceilings/context, not as primary controls.",
    )


def stage27e_gates() -> tuple[Stage27EGate, ...]:
    return (
        Stage27EGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest.",
        ),
        Stage27EGate(
            name="stage27c_contract",
            kind="pass_floor",
            criterion="Stage 27C source report is PASS, uses the locked artifact, and exposes per-class covers over the selected six-head family.",
        ),
        Stage27EGate(
            name="stage27d_contract",
            kind="pass_floor",
            criterion="Stage 27D source report is PASS and used single Stage 27C class-head covers as source context.",
        ),
        Stage27EGate(
            name="single_coordinate_resolution",
            kind="pass_floor",
            criterion="slices_per_head equals the 64-dimensional attention-head width; each candidate slice is one coordinate.",
        ),
        Stage27EGate(
            name="learn_eval_separation",
            kind="pass_floor",
            criterion="Coordinate-cover learning rows come only from train split; scoring rows come only from test split.",
        ),
        Stage27EGate(
            name="matched_random_coordinate_control",
            kind="primary",
            criterion="Per-class coordinate covers beat per-row random same-size coordinate-cover mean margin on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27EGate(
            name="positive_margin_floor",
            kind="primary",
            criterion="At least 55% of eval rows have positive target-vs-hard-partner margin under the per-class coordinate cover.",
        ),
        Stage27EGate(
            name="head_cover_gain_fraction",
            kind="supporting",
            criterion="Mean coordinate-cover gain is at least 10% of the mean Stage 27C class-head-cover gain.",
        ),
    )


def stage27e_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS",
        "grey_status": "GREY_SINGLE_DIM_COORDINATE_COVERS_PARTIAL",
        "null_status": "NULL_SINGLE_DIM_COORDINATE_COVERS_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within the Stage 27C per-class Pythia-160M attention-head covers, sparse single-coordinate sets recover "
            "held-out hard-partner readout margins above matched random coordinate controls."
        ),
        "claim_if_null": (
            "Stage 27C/27D class-local head and slice covers remain valid, but single-coordinate cover decomposition did "
            "not recover held-out hard-partner readout margins under the preregistered controls."
        ),
        "scope_boundary": (
            "Stage 27E is bounded to single coordinates of pre-output-projection attention-head vectors inside the "
            "Pythia-160M Stage 27C Foundation covers. These coordinates are not literal neurons. Stage 27E is not an "
            "MLP-neuron claim, complete circuit, token sonar, Noetic/40-Element coverage, raw CAS-symbol understanding, "
            "or generation control."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, MLP-neuron localization, raw CAS-symbol understanding, an "
            "internal CAS compiler, Noetic/40-Element component causality, free-form generation control, or cross-model "
            "component generality from Stage 27E."
        ),
    }


def stage27e_payload() -> dict[str, Any]:
    payload = {
        "stage": "27E",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27D narrowed class-specific Foundation readout evidence from per-class attention-head covers to "
            "contiguous within-head slices. Stage 27E tests the resolution limit: single head-coordinate covers."
        ),
        "formal_anchor": (
            "Refined local-cover framing: Stage 26/27A gives a global head cover, Stage 27C gives class-indexed head "
            "subcovers, Stage 27D gives within-head slice subcovers, and Stage 27E tests whether those covers admit "
            "single-coordinate subcovers."
        ),
        "required_inputs": stage27e_required_inputs(),
        "method": stage27e_method(),
        "gates": [asdict(gate) for gate in stage27e_gates()],
        "claim_boundary": stage27e_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_stage27c_and_stage27d_contracts",
            "learn_per_class_coordinate_covers_on_train_split_only",
            "evaluate_hard_partner_margins_on_test_split_only",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27e_payload(payload)
    return payload


def validate_stage27e_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27E starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if tuple(inputs.get("global_selected_components", ())) != _SELECTED_STAGE27_COMPONENTS:
        errors.setdefault("required_inputs", []).append("selected components must match the Stage 26/27A top-six family.")
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27E must target the Stage 7 layer-6 Foundation readout.")
    if int(inputs.get("slices_per_head", 0)) != int(inputs.get("head_dim", -1)):
        errors.setdefault("required_inputs", []).append("Stage 27E must use one coordinate per slice.")
    if int(inputs.get("coordinate_cover_size", 0)) >= int(inputs.get("source_cover_size", 0)) * int(inputs.get("head_dim", 0)):
        errors.setdefault("required_inputs", []).append("coordinate cover must be a strict subcover of candidate coordinates.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in (
        "matched_random_coordinate_control",
        "positive_margin_floor",
        "head_cover_gain_fraction",
        "single_coordinate_resolution",
        "learn_eval_separation",
    ):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("exact neurons", "MLP-neuron", "free-form generation control", "Noetic/40-Element"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
