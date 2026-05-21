"""Stage 27P Qwen drive-local eraser steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27PGate:
    name: str
    kind: str
    criterion: str


def stage27p_required_inputs() -> dict[str, Any]:
    return {
        "model": "Qwen/Qwen2.5-1.5B",
        "model_revision": "8faed761d45a263340a0528343f099c05c9a4323",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage16_cpl2_report": "STAGE16_QWEN15B_CPL2_REPORT_20260519.json",
        "stage16_manifest": "stage16_qwen15b_activations_manifest_20260519.json",
        "stage27o_report": "stage27o_drive_local_cross_scale_eraser_steering_20260521.json",
        "stage27pa_report": "stage27p_qwen_hook_adapter_preflight_20260521.json",
        "stage16_cpl2_status": "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES",
        "stage27o_status": "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING",
        "stage27pa_status": "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT",
        "candidate_layers": [24, 25, 26, 27],
        "cover_size_per_drive": 6,
        "per_drive": 16,
        "learn_rows_per_drive": 8,
        "eval_rows_per_drive": 8,
        "held_out_eval_rows": 56,
        "selection_seed": 27043,
        "eraser_scale_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
        "n_random_covers_per_drive": 8,
        "intervention_positions": "continuation_prediction_positions_only",
        "random_control_policy": "each Qwen drive-local eraser cover compared against matched random covers for the same drive and same selected scale",
    }


def stage27p_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration, runner, and tests before any Stage 27P GPU result is generated.",
        "Verify Stage 16 Qwen CPL2 PASS, Stage 27O Pythia drive-local PASS, and Stage 27P-A Qwen hook-adapter PASS source contracts.",
        "Load Qwen/Qwen2.5-1.5B at revision 8faed761d45a263340a0528343f099c05c9a4323.",
        "Select 16 CPL2-eligible hard-partner rows per Foundation drive from the Stage 7 fixture using seed 27043.",
        "Split the selected rows into 8 learn rows and 8 held-out eval rows per drive.",
        "Enumerate Qwen output-side candidate components over layers 24-27: every attention head plus one MLP block per layer.",
        "For each Foundation drive, learn a separate Qwen eraser cover on that drive's 8 learn rows only.",
        "For each Foundation drive, choose one eraser scale from the fixed grid by maximum mean margin increment on that drive's learn rows.",
        "Evaluate each drive-local cover only on held-out rows from its matching drive.",
        "Compare held-out increments against matched random covers sampled separately for each drive-local cover.",
    )


def stage27p_gates() -> tuple[Stage27PGate, ...]:
    return (
        Stage27PGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 16 Qwen CPL2 PASS, Stage 27O Pythia-1B PASS, and Stage 27P-A Qwen adapter PASS source contracts are verified.",
        ),
        Stage27PGate(
            name="model_revision",
            kind="pass_floor",
            criterion="Loaded Qwen model revision matches 8faed761d45a263340a0528343f099c05c9a4323.",
        ),
        Stage27PGate(
            name="drive_local_cover_contract",
            kind="pass_floor",
            criterion="All seven Foundation drives produce exactly six learned Qwen eraser components from learn rows only.",
        ),
        Stage27PGate(
            name="controlled_split",
            kind="pass_floor",
            criterion="Evaluation uses exactly 56 held-out rows, 8 held-out rows per drive, and no learn/eval overlap.",
        ),
        Stage27PGate(
            name="qwen_drive_local_eval",
            kind="primary",
            criterion="Qwen drive-local calibrated eraser suppression beats matched random eraser suppression on at least 60% of 56 held-out rows with sign-test p<0.05.",
        ),
        Stage27PGate(
            name="positive_effect_floor",
            kind="primary",
            criterion="Passing Qwen drive-local mode must have positive mean increment and positive increment share at least 55%.",
        ),
    )


def stage27p_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING",
        "grey_status": "GREY_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_PARTIAL",
        "null_status": "NULL_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Drive-local calibrated output-side eraser-cover steering transfers from Pythia-family models to Qwen2.5-1.5B "
            "under Qwen-specific component covers and matched random controls."
        ),
        "claim_if_null": (
            "Qwen2.5-1.5B did not establish cross-architecture drive-local calibrated eraser steering under the Stage 27P gates; "
            "Stage 27O remains a Pythia-family cross-scale result."
        ),
        "scope_boundary": (
            "Stage 27P is bounded cross-architecture evidence for Qwen drive-local calibrated output-side eraser-cover intervention "
            "over CPL2 likelihood margins. It is not universal architecture evidence, not weight editing, not complete circuit "
            "discovery, not model-wide control, and not visible free-form generation control."
        ),
        "forbidden_claims": (
            "Do not claim universal cross-architecture steering, complete circuits, exact model-wide causal explanation, durable "
            "weight edits, open-ended generation control, or raw CAS-symbol understanding from Stage 27P."
        ),
    }


def stage27p_payload() -> dict[str, Any]:
    payload = {
        "stage": "27P",
        "status": "PREREGISTERED_GPU_REQUIRED",
        "motivation": (
            "Stage 27O showed that drive-local output-side eraser covers solve Pythia-1B cross-scale steering. Stage 27P tests "
            "the same drive-local method on Qwen2.5-1.5B after Stage 27P-A validated the Qwen hook adapter."
        ),
        "formal_anchor": (
            "Cross-architecture replication of the Stage 27O drive-local calibrated eraser protocol with Qwen-specific component "
            "covers, pinned model revision, held-out split, and matched random controls."
        ),
        "required_inputs": stage27p_required_inputs(),
        "method": stage27p_method(),
        "gates": [asdict(gate) for gate in stage27p_gates()],
        "claim_boundary": stage27p_claim_boundary(),
        "execution_order": [
            "commit_preregistration_runner_and_tests_before_gpu_result",
            "verify_source_contracts_and_loaded_revision",
            "select_balanced_qwen_split",
            "learn_drive_local_qwen_eraser_covers_on_learn_rows",
            "calibrate_one_scale_per_drive_on_learn_rows",
            "evaluate_56_held_out_rows_against_drive_matched_random_controls",
            "record_bounded_cross_architecture_result",
        ],
    }
    payload["validation"] = validate_stage27p_payload(payload)
    return payload


def validate_stage27p_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_REQUIRED":
        errors.setdefault("status", []).append("Stage 27P starts as GPU-required preregistration.")
    if inputs.get("stage16_cpl2_status") != "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES":
        errors.setdefault("required_inputs", []).append("Stage 27P must inherit the Stage 16 Qwen CPL2 PASS.")
    if inputs.get("stage27o_status") != "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING":
        errors.setdefault("required_inputs", []).append("Stage 27P must inherit the Stage 27O Pythia-1B PASS.")
    if inputs.get("stage27pa_status") != "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT":
        errors.setdefault("required_inputs", []).append("Stage 27P must inherit the Stage 27P-A adapter PASS.")
    if int(inputs.get("learn_rows_per_drive", 0)) + int(inputs.get("eval_rows_per_drive", 0)) != int(inputs.get("per_drive", -1)):
        errors.setdefault("required_inputs", []).append("learn+eval rows per drive must equal per_drive.")
    if int(inputs.get("held_out_eval_rows", 0)) != 56:
        errors.setdefault("required_inputs", []).append("held-out eval rows must be exactly 56 for the first Qwen steering gate.")
    if inputs.get("candidate_layers") != [24, 25, 26, 27]:
        errors.setdefault("required_inputs", []).append("Stage 27P candidate layers are locked to 24-27.")
    scale_grid = inputs.get("eraser_scale_grid", [])
    if not scale_grid or min(float(x) for x in scale_grid) < 0.0 or max(float(x) for x in scale_grid) > 1.0:
        errors.setdefault("required_inputs", []).append("Eraser scale grid must be within [0, 1].")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27P must localize to continuation prediction positions.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("drive_local_cover_contract", "qwen_drive_local_eval", "positive_effect_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("universal", "complete circuits", "durable weight edits", "open-ended generation control"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
