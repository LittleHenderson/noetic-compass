"""Stage 27M robust calibrated eraser steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27MGate:
    name: str
    kind: str
    criterion: str


def stage27m_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "fixture_rows": 4368,
        "fixture_rows_per_drive": 624,
        "stage7_prefix_report": "stage7_cas_prefix_likelihood_20260517.json",
        "stage27j_report": "stage27j_output_side_component_attribution_20260521.json",
        "stage27l_report": "stage27l_calibrated_eraser_steering_20260521.json",
        "stage7_prefix_status": "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD",
        "stage27j_status": "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION",
        "stage27l_status": "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING",
        "per_drive": 70,
        "learn_rows_per_drive": 35,
        "eval_rows_per_drive": 35,
        "held_out_eval_rows": 245,
        "selection_seed": 27040,
        "eraser_scale_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
        "calibration_modes": ["global", "drive_calibrated"],
        "intervention_positions": "continuation_prediction_positions_only",
        "random_control_policy": "same calibrated gain(s) applied to matched random eraser covers",
    }


def stage27m_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27M GPU result is generated.",
        "Verify Stage 7 readable-prefix PASS, Stage 27J output-side attribution PASS, and Stage 27L calibrated-steering PASS source contracts.",
        "Use the Stage 27J eraser cover; do not relearn the cover in Stage 27M.",
        "Select 70 rows per Foundation drive from the Stage 7 CPL2-eligible test fixture using seed 27040.",
        "Split the selected rows into 35 learn rows and 35 held-out eval rows per drive.",
        "On learn rows, choose one global eraser scale from the fixed scale grid by maximum mean margin increment.",
        "On learn rows, choose one eraser scale per Foundation drive from the same fixed grid by maximum mean margin increment within that drive.",
        "Evaluate global-calibrated and drive-calibrated eraser suppression on the 245 held-out rows only.",
        "Compare held-out increments against matched random eraser covers using the same calibrated global or per-drive gains.",
    )


def stage27m_gates() -> tuple[Stage27MGate, ...]:
    return (
        Stage27MGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 7 readable-prefix PASS, Stage 27J PASS, and Stage 27L PASS source contracts are verified.",
        ),
        Stage27MGate(
            name="robust_split",
            kind="pass_floor",
            criterion="Evaluation uses exactly 245 held-out rows, with 35 held-out rows per drive and no overlap with calibration rows.",
        ),
        Stage27MGate(
            name="global_robust_eval",
            kind="primary",
            criterion="Global calibrated eraser suppression beats matched random eraser suppression on at least 60% of 245 held-out rows with sign-test p<0.05.",
        ),
        Stage27MGate(
            name="drive_robust_eval",
            kind="primary",
            criterion="Drive-calibrated eraser suppression beats matched random eraser suppression on at least 60% of 245 held-out rows with sign-test p<0.05.",
        ),
        Stage27MGate(
            name="positive_effect_floor",
            kind="primary",
            criterion="Passing robust mode must have positive mean increment and positive increment share at least 55%.",
        ),
    )


def stage27m_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_ROBUST_CALIBRATED_ERASER_STEERING",
        "strong_status": "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING",
        "grey_status": "GREY_ROBUST_CALIBRATED_ERASER_STEERING_PARTIAL",
        "null_status": "NULL_ROBUST_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M, calibrated Stage 27J eraser-cover suppression generalizes from the initial 56-row held-out "
            "Stage 27L run to a larger 245-row held-out robustness split beyond matched random eraser-cover controls."
        ),
        "claim_if_null": (
            "Stage 27L remains a clean first calibrated-steering pass, but the larger Stage 27M robustness split did not "
            "establish row-consistent calibrated eraser steering beyond matched random controls."
        ),
        "scope_boundary": (
            "Stage 27M is bounded larger-sample robustness evidence for calibrated eraser-cover intervention over Pythia-160M "
            "CPL2 likelihood margins. It is not weight editing, not complete circuit discovery, not model-wide control, "
            "not cross-model control, and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim complete circuits, exact model-wide causal explanation, durable weight edits, open-ended generation control, "
            "cross-model steering, or raw CAS-symbol understanding from Stage 27M."
        ),
    }


def stage27m_payload() -> dict[str, Any]:
    payload = {
        "stage": "27M",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27L established calibrated eraser-cover likelihood steering on 56 held-out rows. Stage 27M tests whether "
            "that capability survives a larger 245-row held-out robustness split using the same cover, same fixed scale grid, "
            "and matched random eraser-cover controls."
        ),
        "formal_anchor": (
            "Larger-sample held-out robustness for the calibrated output-side eraser-cover intervention discovered by Stage 27J "
            "and first validated by Stage 27L."
        ),
        "required_inputs": stage27m_required_inputs(),
        "method": stage27m_method(),
        "gates": [asdict(gate) for gate in stage27m_gates()],
        "claim_boundary": stage27m_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_source_contracts",
            "select_larger_balanced_robustness_split",
            "calibrate_global_and_drive_scales_on_learn_rows",
            "evaluate_245_held_out_rows_against_matched_random_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27m_payload(payload)
    return payload


def validate_stage27m_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27M starts as GPU-recommended preregistration.")
    if inputs.get("stage27l_status") != "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING":
        errors.setdefault("required_inputs", []).append("Stage 27M must inherit the Stage 27L bounded PASS.")
    if int(inputs.get("learn_rows_per_drive", 0)) + int(inputs.get("eval_rows_per_drive", 0)) != int(inputs.get("per_drive", -1)):
        errors.setdefault("required_inputs", []).append("learn+eval rows per drive must equal per_drive.")
    if int(inputs.get("held_out_eval_rows", 0)) < 240:
        errors.setdefault("required_inputs", []).append("held-out eval rows must be at least 240 for robustness.")
    scale_grid = inputs.get("eraser_scale_grid", [])
    if not scale_grid or min(float(x) for x in scale_grid) < 0.0 or max(float(x) for x in scale_grid) > 1.0:
        errors.setdefault("required_inputs", []).append("Eraser scale grid must be within [0, 1].")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27M must localize to continuation prediction positions.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("global_robust_eval", "drive_robust_eval", "positive_effect_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("complete circuits", "durable weight edits", "open-ended generation control", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors

