"""Stage 27G MLP-neuron cover steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27GGate:
    name: str
    kind: str
    criterion: str


def stage27g_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage27f_report": "stage27f_targeted_mlp_neuron_covers_20260521.json",
        "stage27f_status": "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "amplification_scale": 2.0,
        "polarity_flip_scale": -1.0,
        "eval_rows_per_class": 4,
    }


def stage27g_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27G GPU result is generated.",
        "Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.",
        "Verify Stage 27F is PASS, uses the locked artifact, and exposes per-class MLP-neuron covers.",
        "On held-out Stage 7 test rows, read the target Foundation and hard-partner Foundation for each row.",
        "Amplify the target class's Stage 27F neuron cover by the preregistered scale and measure target-vs-partner margin increase.",
        "Polarity-flip the same target class neuron cover by the preregistered negative scale and measure target-vs-partner margin decrease or sign flip.",
        "Compare both directional effects against same-size/same-layer random neuron-cover controls using the same intervention scale.",
        "Amplify the hard-partner class's cover as a countersteering diagnostic, but do not use it as the primary PASS gate because the partner cover may be inactive on target-class prompts.",
        "Report actual margin-flip share for polarity flip and partner amplification as diagnostics; signed readout-margin steering is the primary gate.",
    )


def stage27g_gates() -> tuple[Stage27GGate, ...]:
    return (
        Stage27GGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest.",
        ),
        Stage27GGate(
            name="stage27f_contract",
            kind="pass_floor",
            criterion="Stage 27F source report is PASS and exposes per-class MLP-neuron covers.",
        ),
        Stage27GGate(
            name="target_amplification_control",
            kind="primary",
            criterion="Target-cover amplification beats random target-layer amplification on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27GGate(
            name="target_polarity_flip_control",
            kind="primary",
            criterion="Target-cover polarity flip reduces target-vs-partner margin more than random target-layer polarity flips on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27GGate(
            name="bidirectional_positive_share",
            kind="primary",
            criterion="Both target-amplification margin increases and target-flip margin reductions are positive on at least 55% of eval rows.",
        ),
        Stage27GGate(
            name="flip_share",
            kind="diagnostic",
            criterion="Report the share of rows where target polarity flip and partner amplification push target-vs-partner margin below zero; not required for PASS.",
        ),
    )


def stage27g_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_MLP_NEURON_COVER_STEERING",
        "grey_status": "GREY_MLP_NEURON_COVER_STEERING_PARTIAL",
        "null_status": "NULL_MLP_NEURON_COVER_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M and the trained Stage 7 Foundation readout, amplifying class-specific Stage 27F "
            "MLP-neuron covers increases target-vs-hard-partner margins, while polarity-flipping those same covers "
            "decreases those margins, both above matched random neuron-cover controls."
        ),
        "claim_if_null": (
            "Stage 27F neuron-cover causality remains valid, but direct amplification of those covers did not establish "
            "readout-level steering under the preregistered controls."
        ),
        "scope_boundary": (
            "Stage 27G is readout-level steering evidence over Stage 27F MLP-neuron covers. It is not free-form "
            "generation control, not weight editing, not a complete circuit, not model-wide control, and not a claim "
            "that raw CAS symbols are understood."
        ),
        "forbidden_claims": (
            "Do not claim free-form generation control, model-wide control, complete circuits, weight editing, internal "
            "CAS compiler behavior, cross-model steering, or raw CAS-symbol understanding from Stage 27G."
        ),
    }


def stage27g_payload() -> dict[str, Any]:
    payload = {
        "stage": "27G",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27F established sparse MLP-neuron covers that causally support class-specific Foundation margins. "
            "Stage 27G tests whether those same covers can steer the readout when amplified."
        ),
        "formal_anchor": (
            "Intervention surface refinement: Stage 27F identifies causal neuron covers; Stage 27G tests directional "
            "control by amplifying and polarity-flipping those covers, then measuring the signed readout-margin response."
        ),
        "required_inputs": stage27g_required_inputs(),
        "method": stage27g_method(),
        "gates": [asdict(gate) for gate in stage27g_gates()],
        "claim_boundary": stage27g_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_stage27f_contract",
            "amplify_target_and_partner_covers_on_test_split",
            "compare_against_same_layer_random_intervention_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27g_payload(payload)
    return payload


def validate_stage27g_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27G starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27G must target the Stage 7 layer-6 Foundation readout.")
    if float(inputs.get("amplification_scale", 0.0)) <= 1.0:
        errors.setdefault("required_inputs", []).append("amplification scale must be greater than 1.0.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    if float(inputs.get("polarity_flip_scale", 0.0)) >= 0.0:
        errors.setdefault("required_inputs", []).append("polarity flip scale must be negative.")
    for required in ("target_amplification_control", "target_polarity_flip_control", "bidirectional_positive_share"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("free-form generation control", "model-wide control", "weight editing", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
