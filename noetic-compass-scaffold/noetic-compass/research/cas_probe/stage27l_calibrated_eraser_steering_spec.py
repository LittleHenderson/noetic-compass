"""Stage 27L calibrated eraser steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27LGate:
    name: str
    kind: str
    criterion: str


def stage27l_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_prefix_report": "stage7_cas_prefix_likelihood_20260517.json",
        "stage27j_report": "stage27j_output_side_component_attribution_20260521.json",
        "stage27k_report": "stage27k_output_side_component_steering_20260521.json",
        "stage7_prefix_status": "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD",
        "stage27j_status": "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION",
        "stage27k_status": "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL",
        "calibration_rows": "Stage 27J learn split",
        "evaluation_rows": "Stage 27J held-out eval split",
        "eraser_scale_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
        "calibration_modes": ["global", "drive_calibrated"],
        "intervention_positions": "continuation_prediction_positions_only",
        "random_control_policy": "same calibrated gain(s) applied to matched random eraser covers",
    }


def stage27l_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27L GPU result is generated.",
        "Verify Stage 7 readable-prefix PASS, Stage 27J output-side attribution PASS, and Stage 27K grey steering source contracts.",
        "Load the Stage 27J eraser cover; do not relearn the cover in Stage 27L.",
        "Recreate the Stage 27J learn/eval split deterministically.",
        "On learn rows, choose one global eraser scale from the fixed scale grid by maximum mean margin increment.",
        "On learn rows, choose one eraser scale per Foundation drive from the same fixed grid by maximum mean margin increment within that drive.",
        "Evaluate global-calibrated and drive-calibrated eraser suppression on held-out rows only.",
        "Compare held-out increments against matched random eraser covers using the same calibrated global or per-drive gains.",
    )


def stage27l_gates() -> tuple[Stage27LGate, ...]:
    return (
        Stage27LGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 7 readable-prefix PASS, Stage 27J PASS, and Stage 27K GREY source contracts are verified.",
        ),
        Stage27LGate(
            name="learn_eval_split",
            kind="pass_floor",
            criterion="Gain calibration uses only Stage 27J learn rows, and evaluation uses only Stage 27J held-out rows.",
        ),
        Stage27LGate(
            name="global_calibrated_eval",
            kind="primary",
            criterion="Global calibrated eraser suppression beats matched random eraser suppression on at least 60% of held-out rows with sign-test p<0.05.",
        ),
        Stage27LGate(
            name="drive_calibrated_eval",
            kind="primary",
            criterion="Drive-calibrated eraser suppression beats matched random eraser suppression on at least 60% of held-out rows with sign-test p<0.05.",
        ),
        Stage27LGate(
            name="positive_effect_floor",
            kind="primary",
            criterion="Passing calibrated mode must have positive mean increment and positive increment share at least 55%.",
        ),
    )


def stage27l_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_CALIBRATED_ERASER_STEERING",
        "strong_status": "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING",
        "grey_status": "GREY_CALIBRATED_ERASER_STEERING_PARTIAL",
        "null_status": "NULL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M, Stage 27J eraser covers can be calibrated on held-out-disjoint learn rows "
            "to shift readable-prefix semantic likelihood margins on held-out rows beyond matched random eraser covers."
        ),
        "claim_if_null": (
            "Stage 27K's directional mean lift remains a calibration hint, but fixed-grid global/drive eraser calibration "
            "did not establish held-out row-consistent steering beyond matched random controls."
        ),
        "scope_boundary": (
            "Stage 27L is bounded calibrated eraser-cover intervention over Pythia-160M CPL2 likelihood margins. "
            "It is not weight editing, not complete circuit discovery, not model-wide control, not cross-model control, "
            "and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, "
            "cross-model steering, or raw CAS-symbol understanding from Stage 27L."
        ),
    }


def stage27l_payload() -> dict[str, Any]:
    payload = {
        "stage": "27L",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27K showed that fixed eraser suppression is the strongest output-side steering channel, but the combined "
            "fixed intervention did not pass row-consistency gates. Stage 27L calibrates the eraser gain on the Stage 27J learn "
            "split, then evaluates global and drive-calibrated eraser suppression on held-out rows against matched random covers."
        ),
        "formal_anchor": (
            "Learn-disjoint gain calibration over an already attributed output-side eraser cover, with held-out matched-random "
            "component-cover controls at continuation prediction positions."
        ),
        "required_inputs": stage27l_required_inputs(),
        "method": stage27l_method(),
        "gates": [asdict(gate) for gate in stage27l_gates()],
        "claim_boundary": stage27l_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_source_contracts",
            "calibrate_global_and_drive_scales_on_learn_rows",
            "evaluate_held_out_calibrated_eraser_steering_against_matched_random_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27l_payload(payload)
    return payload


def validate_stage27l_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27L starts as GPU-recommended preregistration.")
    if inputs.get("stage27j_status") != "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION":
        errors.setdefault("required_inputs", []).append("Stage 27L must inherit the Stage 27J bounded PASS.")
    if inputs.get("stage27k_status") != "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL":
        errors.setdefault("required_inputs", []).append("Stage 27L must inherit the Stage 27K GREY.")
    if inputs.get("calibration_rows") != "Stage 27J learn split":
        errors.setdefault("required_inputs", []).append("Stage 27L must calibrate on Stage 27J learn rows.")
    if inputs.get("evaluation_rows") != "Stage 27J held-out eval split":
        errors.setdefault("required_inputs", []).append("Stage 27L must evaluate on Stage 27J held-out rows.")
    scale_grid = inputs.get("eraser_scale_grid", [])
    if not scale_grid or min(float(x) for x in scale_grid) < 0.0 or max(float(x) for x in scale_grid) > 1.0:
        errors.setdefault("required_inputs", []).append("Eraser scale grid must be within [0, 1].")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27L must localize to continuation prediction positions.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("global_calibrated_eval", "drive_calibrated_eval", "positive_effect_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("complete circuits", "durable weight edits", "open-ended generation control", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors

