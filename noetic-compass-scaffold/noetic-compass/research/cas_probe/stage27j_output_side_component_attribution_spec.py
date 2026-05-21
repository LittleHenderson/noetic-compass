"""Stage 27J output-side component attribution pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27JGate:
    name: str
    kind: str
    criterion: str


def stage27j_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_prefix_report": "stage7_cas_prefix_likelihood_20260517.json",
        "stage27i_report": "stage27i_prediction_position_steering_20260521.json",
        "stage7_prefix_status": "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD",
        "stage27i_status": "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED",
        "candidate_layers": [8, 9, 10, 11],
        "candidate_components": "12 attention heads plus 1 MLP block per candidate layer",
        "intervention_positions": "continuation_prediction_positions_only",
        "per_drive": 16,
        "learn_rows_per_drive": 8,
        "eval_rows_per_drive": 8,
        "cover_size": 6,
        "random_control_policy": "same layer/kind when available; singleton MLP blocks fall back to same-kind different-layer controls",
    }


def stage27j_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27J GPU result is generated.",
        "Reuse the Stage 7 CAS-prefix likelihood row selection and readable plain-prefix wording.",
        "Verify the Stage 7 readable-prefix source PASS and Stage 27I prediction-position NULL source contract.",
        "Split the selected rows by drive into learn and held-out eval halves.",
        "On learn rows, ablate each late-layer output-side component at continuation prediction positions and score prefix-likelihood margin change.",
        "Rank carrier components by positive margin drop when ablated; rank eraser components by margin lift when ablated.",
        "On held-out eval rows, ablate the learned carrier cover and eraser cover separately.",
        "Compare held-out carrier drop and eraser lift against same-size matched random output-side component covers: layer/kind matched where available, with explicit same-kind fallback for singleton MLP blocks.",
    )


def stage27j_gates() -> tuple[Stage27JGate, ...]:
    return (
        Stage27JGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 7 readable-prefix source PASS and Stage 27I source NULL are both verified.",
        ),
        Stage27JGate(
            name="learn_eval_split",
            kind="pass_floor",
            criterion="Learn and eval rows are disjoint and balanced by drive.",
        ),
        Stage27JGate(
            name="carrier_cover_eval",
            kind="primary",
            criterion="Held-out carrier-cover ablation drop beats matched random cover drop on at least 60% of rows with sign-test p<0.05; random controls are layer/kind matched where available and explicitly same-kind for singleton MLP blocks.",
        ),
        Stage27JGate(
            name="eraser_cover_eval",
            kind="primary",
            criterion="Held-out eraser-cover ablation lift beats matched random cover lift on at least 60% of rows with sign-test p<0.05; random controls are layer/kind matched where available and explicitly same-kind for singleton MLP blocks.",
        ),
        Stage27JGate(
            name="attribution_floor",
            kind="primary",
            criterion="At least one of carrier_cover_eval or eraser_cover_eval passes; both passing is stronger.",
        ),
    )


def stage27j_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_ATTRIBUTION",
        "strong_status": "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION",
        "grey_status": "GREY_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_PARTIAL",
        "null_status": "NULL_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M, late-layer output-side attention/MLP components can be identified whose ablation "
            "changes readable-prefix semantic continuation likelihood on held-out rows beyond matched random component covers."
        ),
        "claim_if_null": (
            "The Stage 27I output-path fade remains the best explanation; this late-layer component attribution pass "
            "did not isolate held-out output-side carrier or eraser covers beyond matched random controls."
        ),
        "scope_boundary": (
            "Stage 27J is late-layer output-side component attribution over Pythia-160M likelihood margins. It is not "
            "complete circuit discovery, not model-wide control, not weight editing, and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim complete circuits, exact model-wide causal explanation, open-ended generation control, "
            "weight editing, cross-model control, or raw CAS-symbol understanding from Stage 27J."
        ),
    }


def stage27j_payload() -> dict[str, Any]:
    payload = {
        "stage": "27J",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27I localized the layer-5 neuron-cover intervention to continuation prediction positions but still "
            "found a likelihood null, while the survival trace showed the readout signal fading by layer 12. Stage 27J "
            "therefore searches the output side directly for late components that carry or erase the readable-prefix likelihood margin."
        ),
        "formal_anchor": (
            "Output-path component attribution: ablate late attention-head and MLP-block contributions at the exact positions "
            "whose logits score the continuation objective, then validate selected covers on held-out rows."
        ),
        "required_inputs": stage27j_required_inputs(),
        "method": stage27j_method(),
        "gates": [asdict(gate) for gate in stage27j_gates()],
        "claim_boundary": stage27j_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_source_contracts",
            "learn_output_side_carrier_and_eraser_components",
            "evaluate_covers_on_held_out_rows_against_matched_random_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27j_payload(payload)
    return payload


def validate_stage27j_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27J starts as GPU-recommended preregistration.")
    if inputs.get("stage27i_status") != "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED":
        errors.setdefault("required_inputs", []).append("Stage 27J must explicitly inherit the Stage 27I NULL.")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27J must localize to continuation prediction positions.")
    if int(inputs.get("learn_rows_per_drive", 0)) + int(inputs.get("eval_rows_per_drive", 0)) != int(inputs.get("per_drive", -1)):
        errors.setdefault("required_inputs", []).append("learn+eval rows per drive must equal per_drive.")
    if int(inputs.get("cover_size", 0)) <= 0:
        errors.setdefault("required_inputs", []).append("cover size must be positive.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("carrier_cover_eval", "eraser_cover_eval", "attribution_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("complete circuits", "open-ended generation control", "weight editing", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
