"""Stage 27F targeted MLP-neuron cover pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_SELECTED_STAGE27_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


@dataclass(frozen=True)
class Stage27FGate:
    name: str
    kind: str
    criterion: str


def stage27f_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage27c_report": "stage27c_per_class_component_covers_20260521.json",
        "stage27c_status": "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS",
        "stage27e_report": "stage27e_single_dim_coordinate_covers_20260521.json",
        "stage27e_status": "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "global_selected_components": _SELECTED_STAGE27_COMPONENTS,
        "candidate_layers": "per-class layers from Stage 27E coordinate covers",
        "mlp_intermediate_dim": 3072,
        "neuron_cover_size": 32,
        "learn_rows_per_class": 4,
        "eval_rows_per_class": 4,
    }


def stage27f_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27F GPU result is generated.",
        "Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.",
        "Verify Stage 27C and Stage 27E are PASS with the locked artifact and selected six-head family.",
        "Use Stage 27E per-class single-coordinate covers only to choose candidate MLP layers for each Foundation class.",
        "Capture activated MLP intermediate neurons at the focus token for those candidate layers on train rows.",
        "Rank every candidate MLP neuron by first-order target-vs-hard-partner margin contribution: activation_j times the output-projection alignment with the probe margin direction.",
        "For each Foundation class, define a 32-neuron cover as the top ranked candidate neurons learned only on train rows.",
        "On held-out test rows, ablate the per-class neuron cover from the clean forward pass and measure target-vs-hard-partner margin drop.",
        "Compare targeted drops against same-size random neuron covers with the same per-layer count as the targeted cover.",
        "Patch-back of the targeted cover is a sanity/recovery check; the primary discovery gate is targeted ablation drop above matched random ablations.",
    )


def stage27f_gates() -> tuple[Stage27FGate, ...]:
    return (
        Stage27FGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest.",
        ),
        Stage27FGate(
            name="stage27c_contract",
            kind="pass_floor",
            criterion="Stage 27C source report is PASS and exposes per-class attention-head covers.",
        ),
        Stage27FGate(
            name="stage27e_contract",
            kind="pass_floor",
            criterion="Stage 27E source report is PASS and exposes single-coordinate covers for per-class candidate-layer targeting.",
        ),
        Stage27FGate(
            name="learn_eval_separation",
            kind="pass_floor",
            criterion="Neuron-cover learning rows come only from train split; scoring rows come only from test split.",
        ),
        Stage27FGate(
            name="matched_random_neuron_control",
            kind="primary",
            criterion="Per-class neuron-cover ablation drop beats per-row random same-size/same-layer neuron-cover mean drop on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27FGate(
            name="positive_drop_floor",
            kind="primary",
            criterion="At least 55% of eval rows have positive target-vs-hard-partner margin drop under targeted neuron-cover ablation.",
        ),
        Stage27FGate(
            name="mean_drop_floor",
            kind="primary",
            criterion="Mean targeted neuron-cover drop is positive and greater than mean matched-random neuron-cover drop.",
        ),
        Stage27FGate(
            name="patchback_sanity",
            kind="sanity",
            criterion="Patch-back after targeted ablation restores the clean margin within numerical tolerance on average.",
        ),
    )


def stage27f_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS",
        "grey_status": "GREY_TARGETED_MLP_NEURON_COVERS_PARTIAL",
        "null_status": "NULL_TARGETED_MLP_NEURON_COVERS_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within MLP layers targeted by Stage 27E attention-coordinate covers, sparse MLP intermediate-neuron covers "
            "causally support class-specific Foundation hard-partner readout margins above matched same-layer random "
            "neuron controls."
        ),
        "claim_if_null": (
            "Stage 27C/27D/27E attention-coordinate localization remains valid, but this targeted MLP-neuron cover "
            "method did not establish held-out causal margin drops above matched random neuron controls."
        ),
        "scope_boundary": (
            "Stage 27F is bounded to Pythia-160M MLP intermediate neurons in layers selected from Stage 27E coordinate "
            "covers, scored against the trained Stage 7 Foundation readout. It is not a complete circuit, not all "
            "neurons in the model, not token sonar, not Noetic/40-Element coverage, not raw CAS-symbol understanding, "
            "and not generation control."
        ),
        "forbidden_claims": (
            "Do not claim complete circuits, model-wide exact causal explanation, raw CAS-symbol understanding, an "
            "internal CAS compiler, Noetic/40-Element component causality, free-form generation control, or cross-model "
            "component generality from Stage 27F."
        ),
    }


def stage27f_payload() -> dict[str, Any]:
    payload = {
        "stage": "27F",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27E localized class-specific Foundation readout evidence to single attention-head coordinates. "
            "Stage 27F tests whether nearby MLP intermediate neurons in the same targeted layers causally support the "
            "same hard-partner margins."
        ),
        "formal_anchor": (
            "Targeted local-cover refinement: Stage 27E supplies per-class coordinate covers that select candidate "
            "layers; Stage 27F asks whether sparse MLP-neuron covers inside those layers form causal supports for the "
            "same readout margins."
        ),
        "required_inputs": stage27f_required_inputs(),
        "method": stage27f_method(),
        "gates": [asdict(gate) for gate in stage27f_gates()],
        "claim_boundary": stage27f_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_stage27c_and_stage27e_contracts",
            "learn_per_class_neuron_covers_on_train_split_only",
            "evaluate_targeted_ablation_drops_on_test_split_only",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27f_payload(payload)
    return payload


def validate_stage27f_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27F starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if tuple(inputs.get("global_selected_components", ())) != _SELECTED_STAGE27_COMPONENTS:
        errors.setdefault("required_inputs", []).append("selected components must match the Stage 26/27A top-six family.")
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27F must target the Stage 7 layer-6 Foundation readout.")
    if int(inputs.get("neuron_cover_size", 0)) <= 0 or int(inputs.get("neuron_cover_size", 0)) >= int(inputs.get("mlp_intermediate_dim", 0)):
        errors.setdefault("required_inputs", []).append("neuron cover must be a sparse strict subcover of an MLP layer.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("matched_random_neuron_control", "positive_drop_floor", "mean_drop_floor", "learn_eval_separation"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("complete circuits", "free-form generation control", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
