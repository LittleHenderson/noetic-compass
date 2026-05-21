"""Stage 27I prediction-position neuron-cover steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27IGate:
    name: str
    kind: str
    criterion: str


def stage27i_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_prefix_report": "stage7_cas_prefix_likelihood_20260517.json",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage27f_report": "stage27f_targeted_mlp_neuron_covers_20260521.json",
        "stage27g_report": "stage27g_mlp_neuron_cover_steering_20260521.json",
        "stage27h_report": "stage27h_prefix_neuron_steering_20260521.json",
        "stage7_prefix_status": "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD",
        "stage27f_status": "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS",
        "stage27g_status": "PASS_BOUNDED_MLP_NEURON_COVER_STEERING",
        "stage27h_status": "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED",
        "intervention_positions": "continuation_prediction_positions_only",
        "downstream_trace_layers": [6, 7, 8, 9, 10, 11, 12],
        "amplification_scale": 2.0,
        "polarity_flip_scale": -1.0,
        "per_drive": 16,
    }


def stage27i_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27I GPU result is generated.",
        "Reuse the Stage 7 CAS-prefix likelihood row selection and readable plain-prefix wording.",
        "Verify Stage 7 prefix, Stage 7 activation artifact, Stage 27F, Stage 27G, and Stage 27H source contracts, including Stage 27H's preregistered NULL.",
        "Score correct-drive versus hard-partner-drive continuation likelihood under no prefix and readable prefix.",
        "Apply Stage 27F neuron-cover amplification only at hidden positions whose logits score continuation tokens.",
        "Compare prefix-plus-position-localized amplification against prefix-only and same-size/same-layer random localized controls.",
        "Apply target-cover polarity flip at the same prediction positions and compare the reduction against random localized flips.",
        "Trace the target-cover amplification effect through layers 6-12 at the same prediction positions using layer-specific Stage 7 Foundation readouts.",
        "Report whether position-localized intervention changes the Stage 27H broad-hook null and where the layer-5 signal survives or fades.",
    )


def stage27i_gates() -> tuple[Stage27IGate, ...]:
    return (
        Stage27IGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 7 readable-prefix, Stage 7 activation artifact, Stage 27F, Stage 27G, and Stage 27H source reports have the preregistered statuses.",
        ),
        Stage27IGate(
            name="prefix_floor",
            kind="pass_floor",
            criterion="Readable prefix-only margin delta versus no-prefix is positive and at least +0.10 on average.",
        ),
        Stage27IGate(
            name="position_localized_amplification",
            kind="primary",
            criterion="Prediction-position target-cover amplification beats random-cover amplification increments on at least 60% of rows with sign-test p<0.05.",
        ),
        Stage27IGate(
            name="position_localized_flip",
            kind="primary",
            criterion="Prediction-position target-cover polarity flip reduces margin more than random-cover polarity flips on at least 60% of rows with sign-test p<0.05.",
        ),
        Stage27IGate(
            name="bidirectional_effect_share",
            kind="primary",
            criterion="Both localized amplification increments and localized polarity-flip reductions are positive on at least 55% of rows.",
        ),
        Stage27IGate(
            name="downstream_survival_trace",
            kind="diagnostic",
            criterion="Report layer 6-12 readout-margin deltas after localized target-cover amplification; not required for PASS.",
        ),
    )


def stage27i_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_PREDICTION_POSITION_NEURON_STEERING",
        "grey_status": "GREY_PREDICTION_POSITION_NEURON_STEERING_PARTIAL",
        "null_status": "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M, applying Stage 27F MLP-neuron cover interventions only at continuation "
            "prediction positions shifts semantic continuation likelihood beyond prefix-only and matched random "
            "localized controls."
        ),
        "claim_if_null": (
            "Stage 27G readout steering remains valid, but prediction-position-localized neuron-cover hooks still "
            "did not establish semantic continuation likelihood control."
        ),
        "scope_boundary": (
            "Stage 27I is prediction-position-localized likelihood steering, not free-form visible-text control, "
            "not weight editing, not model-wide control, not a complete circuit, and not cross-model evidence."
        ),
        "forbidden_claims": (
            "Do not claim open-ended generation control, exact circuit completion, model-wide control, weight editing, "
            "cross-model steering, or raw CAS-symbol understanding from Stage 27I."
        ),
    }


def stage27i_payload() -> dict[str, Any]:
    payload = {
        "stage": "27I",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27H showed that broad MLP-neuron cover hooks do not add likelihood control over the readable "
            "prefix. Stage 27I localizes the same covers to the exact hidden positions whose logits score the "
            "continuation tokens, and traces whether that layer-5 signal survives to output-side depths."
        ),
        "formal_anchor": (
            "Output-path localization: intervene only on the residual positions that feed the logits used by the "
            "CPL2 continuation likelihood objective."
        ),
        "required_inputs": stage27i_required_inputs(),
        "method": stage27i_method(),
        "gates": [asdict(gate) for gate in stage27i_gates()],
        "claim_boundary": stage27i_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_source_contracts_including_stage27h_null",
            "score_prediction_position_localized_neuron_interventions",
            "trace_downstream_layer6_to_layer12_survival",
            "compare_against_same_layer_random_localized_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27i_payload(payload)
    return payload


def validate_stage27i_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27I starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if inputs.get("stage27h_status") != "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED":
        errors.setdefault("required_inputs", []).append("Stage 27I must explicitly inherit the Stage 27H NULL.")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27I must use prediction-position-only intervention.")
    if float(inputs.get("amplification_scale", 0.0)) <= 1.0:
        errors.setdefault("required_inputs", []).append("amplification scale must be greater than 1.0.")
    if float(inputs.get("polarity_flip_scale", 0.0)) >= 0.0:
        errors.setdefault("required_inputs", []).append("polarity flip scale must be negative.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("position_localized_amplification", "position_localized_flip", "prefix_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("open-ended generation control", "model-wide control", "weight editing", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
