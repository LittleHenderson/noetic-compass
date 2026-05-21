"""Stage 27O drive-local cross-scale eraser steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27OGate:
    name: str
    kind: str
    criterion: str


def stage27o_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-1b",
        "model_revision": "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage8_cpl2_report": "STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json",
        "stage8_manifest": "stage8_pythia1b_activations_manifest_20260517.json",
        "stage27n_report": "stage27n_cross_scale_calibrated_eraser_steering_20260521.json",
        "stage8_cpl2_status": "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES",
        "stage27n_status": "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL",
        "stage27n_failure_mode": "positive mean lift but insufficient row-consistency against random controls",
        "candidate_layers": [12, 13, 14, 15],
        "candidate_heads": "read from model.config.num_attention_heads",
        "cover_size_per_drive": 6,
        "per_drive": 16,
        "learn_rows_per_drive": 8,
        "eval_rows_per_drive": 8,
        "held_out_eval_rows": 56,
        "selection_seed": 27041,
        "eraser_scale_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
        "n_random_covers_per_drive": 8,
        "intervention_positions": "continuation_prediction_positions_only",
        "random_control_policy": "each drive-local eraser cover compared against matched random covers for the same drive and same selected scale",
    }


def stage27o_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration, runner, and tests before any Stage 27O GPU result is generated.",
        "Verify Stage 8 Pythia-1B CPL2 PASS and Stage 27N GREY source contracts.",
        "Use the same Stage 27N Pythia-1B selection seed and learn/eval split to isolate cover granularity as the changed variable.",
        "Enumerate the same Pythia-1B output-side candidate components over layers 12-15.",
        "For each Foundation drive, learn a separate eraser cover on that drive's 8 learn rows only.",
        "For each Foundation drive, choose one eraser scale from the fixed grid by maximum mean margin increment on that drive's learn rows.",
        "Evaluate each drive-local cover only on held-out rows from its matching drive.",
        "Compare held-out increments against matched random covers sampled separately for each drive-local cover.",
    )


def stage27o_gates() -> tuple[Stage27OGate, ...]:
    return (
        Stage27OGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 8 Pythia-1B CPL2 PASS and Stage 27N GREY-positive source contracts are verified.",
        ),
        Stage27OGate(
            name="model_revision",
            kind="pass_floor",
            criterion="The loaded Pythia-1B causal LM revision matches f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2.",
        ),
        Stage27OGate(
            name="drive_local_cover_contract",
            kind="pass_floor",
            criterion="All seven Foundation drives produce exactly six learned eraser components from learn rows only.",
        ),
        Stage27OGate(
            name="controlled_split",
            kind="pass_floor",
            criterion="Evaluation uses the Stage 27N split: exactly 56 held-out rows, 8 held-out rows per drive, and no learn/eval overlap.",
        ),
        Stage27OGate(
            name="drive_local_eval",
            kind="primary",
            criterion="Drive-local calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05.",
        ),
        Stage27OGate(
            name="positive_effect_floor",
            kind="primary",
            criterion="Passing drive-local mode must have positive mean increment and positive increment share at least 55%.",
        ),
    )


def stage27o_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING",
        "grey_status": "GREY_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_PARTIAL",
        "null_status": "NULL_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "The Stage 27N cross-scale row-consistency failure is improved by drive-local Pythia-1B output-side eraser covers, "
            "supporting drive-specific cover granularity as the correct cross-scale control surface."
        ),
        "claim_if_null": (
            "Drive-local Pythia-1B eraser covers did not resolve Stage 27N's row-consistency failure; next cross-scale work "
            "should move to class-local covers, larger splits, or patch-style interventions."
        ),
        "scope_boundary": (
            "Stage 27O is bounded cross-scale evidence for drive-local calibrated output-side eraser-cover intervention over "
            "Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not complete "
            "circuit discovery, not model-wide control, and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim cross-architecture steering, complete circuits, exact model-wide causal explanation, durable "
            "weight edits, open-ended generation control, raw CAS-symbol understanding, or universal Pythia-1B control from Stage 27O."
        ),
    }


def stage27o_payload() -> dict[str, Any]:
    payload = {
        "stage": "27O",
        "status": "PREREGISTERED_GPU_REQUIRED",
        "motivation": (
            "Stage 27N showed positive mean Pythia-1B eraser steering but failed row-consistency against matched random controls. "
            "Stage 27O tests the most direct fix: learn and calibrate separate output-side eraser covers per Foundation drive."
        ),
        "formal_anchor": (
            "Drive-local refinement of the Stage 27N cross-scale calibrated eraser protocol, preserving the same split and "
            "candidate component universe while changing only cover granularity."
        ),
        "required_inputs": stage27o_required_inputs(),
        "method": stage27o_method(),
        "gates": [asdict(gate) for gate in stage27o_gates()],
        "claim_boundary": stage27o_claim_boundary(),
        "execution_order": [
            "commit_preregistration_runner_and_tests_before_gpu_result",
            "verify_source_contracts_and_loaded_revision",
            "reuse_stage27n_balanced_split",
            "learn_drive_local_pythia1b_eraser_covers_on_learn_rows",
            "calibrate_one_scale_per_drive_on_learn_rows",
            "evaluate_56_held_out_rows_against_drive_matched_random_controls",
            "record_bounded_drive_local_cross_scale_result",
        ],
    }
    payload["validation"] = validate_stage27o_payload(payload)
    return payload


def validate_stage27o_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_REQUIRED":
        errors.setdefault("status", []).append("Stage 27O starts as GPU-required preregistration.")
    if inputs.get("stage8_cpl2_status") != "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES":
        errors.setdefault("required_inputs", []).append("Stage 27O must inherit the Stage 8 Pythia-1B CPL2 PASS.")
    if inputs.get("stage27n_status") != "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL":
        errors.setdefault("required_inputs", []).append("Stage 27O must explicitly inherit Stage 27N's GREY result.")
    if int(inputs.get("learn_rows_per_drive", 0)) + int(inputs.get("eval_rows_per_drive", 0)) != int(inputs.get("per_drive", -1)):
        errors.setdefault("required_inputs", []).append("learn+eval rows per drive must equal per_drive.")
    if int(inputs.get("held_out_eval_rows", 0)) != 56:
        errors.setdefault("required_inputs", []).append("held-out eval rows must stay at 56 to isolate the Stage 27N split.")
    if int(inputs.get("cover_size_per_drive", 0)) <= 0:
        errors.setdefault("required_inputs", []).append("cover_size_per_drive must be positive.")
    scale_grid = inputs.get("eraser_scale_grid", [])
    if not scale_grid or min(float(x) for x in scale_grid) < 0.0 or max(float(x) for x in scale_grid) > 1.0:
        errors.setdefault("required_inputs", []).append("Eraser scale grid must be within [0, 1].")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27O must localize to continuation prediction positions.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("drive_local_cover_contract", "drive_local_eval", "positive_effect_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("cross-architecture", "complete circuits", "durable weight edits", "open-ended generation control", "universal"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
