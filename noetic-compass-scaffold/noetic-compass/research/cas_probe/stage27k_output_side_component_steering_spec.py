"""Stage 27K output-side component steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27KGate:
    name: str
    kind: str
    criterion: str


def stage27k_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_prefix_report": "stage7_cas_prefix_likelihood_20260517.json",
        "stage27j_report": "stage27j_output_side_component_attribution_20260521.json",
        "stage7_prefix_status": "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD",
        "stage27j_status": "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION",
        "intervention_rows": "Stage 27J held-out eval split only",
        "carrier_scale": 2.0,
        "eraser_scale": 0.0,
        "carrier_flip_scale": -1.0,
        "intervention_positions": "continuation_prediction_positions_only",
        "random_control_policy": "same layer/kind when available; singleton MLP blocks fall back to same-kind different-layer controls",
    }


def stage27k_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27K GPU result is generated.",
        "Verify the Stage 7 readable-prefix source PASS and Stage 27J output-side attribution PASS source contract.",
        "Recreate the Stage 27J learn/eval split deterministically and evaluate only the held-out eval rows.",
        "Load the Stage 27J carrier and eraser covers; do not relearn covers in Stage 27K.",
        "Score readable-prefix CPL2 margins with no intervention.",
        "Score carrier amplification, eraser suppression, and combined carrier-amplification-plus-eraser-suppression at continuation prediction positions.",
        "Score matched random combined interventions with the same cover sizes and component matching policy.",
        "Use carrier polarity flip as a destructive-control diagnostic.",
    )


def stage27k_gates() -> tuple[Stage27KGate, ...]:
    return (
        Stage27KGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 7 readable-prefix source PASS and Stage 27J output-side attribution PASS are both verified.",
        ),
        Stage27KGate(
            name="held_out_split",
            kind="pass_floor",
            criterion="Evaluation uses the recreated Stage 27J held-out rows only.",
        ),
        Stage27KGate(
            name="combined_steering_eval",
            kind="primary",
            criterion=(
                "Combined carrier amplification plus eraser suppression increases held-out readable-prefix likelihood margin "
                "more than matched random combined interventions on at least 60% of rows with sign-test p<0.05."
            ),
        ),
        Stage27KGate(
            name="positive_effect_floor",
            kind="primary",
            criterion="Combined intervention has positive mean margin increment and positive increment share at least 55%.",
        ),
        Stage27KGate(
            name="carrier_polarity_control",
            kind="secondary",
            criterion="Carrier polarity flip reduces held-out margin more than matched random carrier flip on at least 60% of rows with sign-test p<0.05.",
        ),
    )


def stage27k_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_STEERING",
        "strong_status": "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_STEERING_WITH_POLARITY_CONTROL",
        "grey_status": "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL",
        "null_status": "NULL_OUTPUT_SIDE_COMPONENT_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M, Stage 27J late-layer carrier and eraser covers can be used as an output-side "
            "intervention surface that shifts readable-prefix semantic likelihood margins on held-out rows beyond matched random controls."
        ),
        "claim_if_null": (
            "Stage 27J remains attribution evidence only; direct carrier/eraser scaling did not establish held-out "
            "likelihood steering beyond matched random controls."
        ),
        "scope_boundary": (
            "Stage 27K is bounded late-layer intervention steering over Pythia-160M CPL2 likelihood margins. It is not "
            "weight editing, not complete circuit discovery, not model-wide control, not cross-model control, and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, "
            "cross-model steering, or raw CAS-symbol understanding from Stage 27K."
        ),
    }


def stage27k_payload() -> dict[str, Any]:
    payload = {
        "stage": "27K",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27J found late output-side carrier and eraser components for readable-prefix likelihood margins. "
            "Stage 27K tests whether those attributed covers are usable as a direct intervention surface: amplify carriers, "
            "suppress erasers, and compare the held-out margin lift against matched random interventions."
        ),
        "formal_anchor": (
            "Output-side component intervention: scale the late component contributions that Stage 27J identified at the exact "
            "prediction positions used by the CPL2 continuation objective."
        ),
        "required_inputs": stage27k_required_inputs(),
        "method": stage27k_method(),
        "gates": [asdict(gate) for gate in stage27k_gates()],
        "claim_boundary": stage27k_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_source_contracts",
            "load_stage27j_covers_without_relearning",
            "evaluate_held_out_output_side_scaling_against_matched_random_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27k_payload(payload)
    return payload


def validate_stage27k_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27K starts as GPU-recommended preregistration.")
    if inputs.get("stage27j_status") != "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION":
        errors.setdefault("required_inputs", []).append("Stage 27K must inherit the Stage 27J bounded PASS.")
    if inputs.get("intervention_rows") != "Stage 27J held-out eval split only":
        errors.setdefault("required_inputs", []).append("Stage 27K must use held-out Stage 27J eval rows.")
    if float(inputs.get("carrier_scale", 0.0)) <= 1.0:
        errors.setdefault("required_inputs", []).append("carrier_scale must amplify above 1.")
    if float(inputs.get("eraser_scale", 1.0)) != 0.0:
        errors.setdefault("required_inputs", []).append("eraser_scale must suppress to zero.")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27K must localize to continuation prediction positions.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("combined_steering_eval", "positive_effect_floor", "carrier_polarity_control"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("complete circuits", "durable weight edits", "open-ended generation control", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors

