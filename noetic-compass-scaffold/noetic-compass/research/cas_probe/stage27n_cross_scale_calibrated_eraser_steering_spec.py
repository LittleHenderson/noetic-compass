"""Stage 27N cross-scale calibrated eraser steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27NGate:
    name: str
    kind: str
    criterion: str


def stage27n_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-1b",
        "model_revision": "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "fixture_rows": 4368,
        "fixture_rows_per_drive": 624,
        "stage8_cpl2_report": "STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json",
        "stage8_manifest": "stage8_pythia1b_activations_manifest_20260517.json",
        "stage27m_report": "stage27m_robust_calibrated_eraser_steering_20260521.json",
        "stage8_cpl2_status": "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES",
        "stage27m_status": "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING",
        "candidate_layers": [12, 13, 14, 15],
        "candidate_heads": "read from model.config.num_attention_heads",
        "cover_size": 6,
        "per_drive": 16,
        "learn_rows_per_drive": 8,
        "eval_rows_per_drive": 8,
        "held_out_eval_rows": 56,
        "selection_seed": 27041,
        "eraser_scale_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
        "n_random_covers": 8,
        "calibration_modes": ["global", "drive_calibrated"],
        "intervention_positions": "continuation_prediction_positions_only",
        "random_control_policy": "same calibrated gain(s) applied to matched random Pythia-1B eraser covers",
    }


def stage27n_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration, runner, and tests before any Stage 27N GPU result is generated.",
        "Verify Stage 8 Pythia-1B CPL2 PASS and Stage 27M Pythia-160M robust calibrated-steering PASS source contracts.",
        "Load EleutherAI/pythia-1b at revision f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2, or mark the result diagnostic-only if the loaded revision does not match.",
        "Select 16 CPL2-eligible hard-partner rows per Foundation drive from the Stage 7 fixture using seed 27041.",
        "Split the selected rows into 8 learn rows and 8 held-out eval rows per drive.",
        "Enumerate Pythia-1B output-side candidate components over layers 12-15: every attention head plus one MLP block per layer.",
        "Learn model-specific carrier and eraser covers on the learn rows only; do not reuse Pythia-160M component identities.",
        "Choose one global eraser scale and one per-drive eraser scale from the fixed grid by maximum learn-row mean margin increment.",
        "Evaluate global-calibrated and drive-calibrated eraser suppression on the 56 held-out rows only.",
        "Compare held-out increments against matched random Pythia-1B eraser covers using the same calibrated global or per-drive gains.",
    )


def stage27n_gates() -> tuple[Stage27NGate, ...]:
    return (
        Stage27NGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 8 Pythia-1B CPL2 PASS and Stage 27M Pythia-160M robust calibrated-steering PASS source contracts are verified.",
        ),
        Stage27NGate(
            name="model_revision",
            kind="pass_floor",
            criterion="The loaded Pythia-1B causal LM revision matches f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2.",
        ),
        Stage27NGate(
            name="cross_scale_split",
            kind="pass_floor",
            criterion="Evaluation uses exactly 56 held-out rows, with 8 held-out rows per drive and no overlap with calibration rows.",
        ),
        Stage27NGate(
            name="global_cross_scale_eval",
            kind="primary",
            criterion="Global calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05.",
        ),
        Stage27NGate(
            name="drive_cross_scale_eval",
            kind="primary",
            criterion="Drive-calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05.",
        ),
        Stage27NGate(
            name="positive_effect_floor",
            kind="primary",
            criterion="Passing cross-scale mode must have positive mean increment and positive increment share at least 55%.",
        ),
    )


def stage27n_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_CROSS_SCALE_CALIBRATED_ERASER_STEERING",
        "strong_status": "PASS_BOUNDED_CROSS_SCALE_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING",
        "grey_status": "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL",
        "null_status": "NULL_CROSS_SCALE_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Calibrated output-side eraser-cover intervention transfers from Pythia-160M methodology to Pythia-1B when "
            "Pythia-1B learns its own output-side eraser cover and calibrated gains."
        ),
        "claim_if_null": (
            "Stage 27M remains robust Pythia-160M evidence, but the calibrated eraser intervention did not establish "
            "cross-scale transfer to Pythia-1B under the Stage 27N gates."
        ),
        "scope_boundary": (
            "Stage 27N is bounded cross-scale evidence for calibrated output-side eraser-cover intervention over "
            "Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not complete "
            "circuit discovery, not model-wide control, and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim cross-architecture steering, complete circuits, exact model-wide causal explanation, durable "
            "weight edits, open-ended generation control, or raw CAS-symbol understanding from Stage 27N."
        ),
    }


def stage27n_payload() -> dict[str, Any]:
    payload = {
        "stage": "27N",
        "status": "PREREGISTERED_GPU_REQUIRED",
        "motivation": (
            "Stage 27M established robust calibrated output-side eraser steering on Pythia-160M. Stage 27N tests whether "
            "the method transfers across scale to Pythia-1B with model-specific output-side covers and the same held-out "
            "calibration discipline."
        ),
        "formal_anchor": (
            "Cross-scale replication of the calibrated output-side eraser-cover intervention, preserving the Stage 27L/M "
            "learn/eval split and matched-random-control discipline while relearning the component cover for Pythia-1B."
        ),
        "required_inputs": stage27n_required_inputs(),
        "method": stage27n_method(),
        "gates": [asdict(gate) for gate in stage27n_gates()],
        "claim_boundary": stage27n_claim_boundary(),
        "execution_order": [
            "commit_preregistration_runner_and_tests_before_gpu_result",
            "verify_source_contracts_and_loaded_revision",
            "select_balanced_cross_scale_split",
            "learn_pythia1b_output_side_eraser_cover_on_learn_rows",
            "calibrate_global_and_drive_scales_on_learn_rows",
            "evaluate_56_held_out_rows_against_matched_random_controls",
            "record_bounded_cross_scale_result",
        ],
    }
    payload["validation"] = validate_stage27n_payload(payload)
    return payload


def validate_stage27n_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_REQUIRED":
        errors.setdefault("status", []).append("Stage 27N starts as GPU-required preregistration.")
    if inputs.get("stage8_cpl2_status") != "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES":
        errors.setdefault("required_inputs", []).append("Stage 27N must inherit the Stage 8 Pythia-1B CPL2 PASS.")
    if inputs.get("stage27m_status") != "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING":
        errors.setdefault("required_inputs", []).append("Stage 27N must inherit the Stage 27M robust Pythia-160M PASS.")
    if int(inputs.get("learn_rows_per_drive", 0)) + int(inputs.get("eval_rows_per_drive", 0)) != int(inputs.get("per_drive", -1)):
        errors.setdefault("required_inputs", []).append("learn+eval rows per drive must equal per_drive.")
    if int(inputs.get("held_out_eval_rows", 0)) != 56:
        errors.setdefault("required_inputs", []).append("held-out eval rows must be exactly 56 for the first cross-scale gate.")
    if int(inputs.get("cover_size", 0)) <= 0:
        errors.setdefault("required_inputs", []).append("cover_size must be positive.")
    scale_grid = inputs.get("eraser_scale_grid", [])
    if not scale_grid or min(float(x) for x in scale_grid) < 0.0 or max(float(x) for x in scale_grid) > 1.0:
        errors.setdefault("required_inputs", []).append("Eraser scale grid must be within [0, 1].")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27N must localize to continuation prediction positions.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("model_revision", "global_cross_scale_eval", "drive_cross_scale_eval", "positive_effect_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("cross-architecture", "complete circuits", "durable weight edits", "open-ended generation control"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
