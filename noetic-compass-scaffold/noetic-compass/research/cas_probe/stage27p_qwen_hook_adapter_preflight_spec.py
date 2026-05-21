"""Stage 27P-A Qwen hook-adapter preflight pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27PAGate:
    name: str
    kind: str
    criterion: str


def stage27pa_required_inputs() -> dict[str, Any]:
    return {
        "model": "Qwen/Qwen2.5-1.5B",
        "model_revision": "8faed761d45a263340a0528343f099c05c9a4323",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage16_cpl2_report": "STAGE16_QWEN15B_CPL2_REPORT_20260519.json",
        "stage16_manifest": "stage16_qwen15b_activations_manifest_20260519.json",
        "stage27o_report": "stage27o_drive_local_cross_scale_eraser_steering_20260521.json",
        "stage16_cpl2_status": "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES",
        "stage27o_status": "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING",
        "candidate_layers": [24, 25, 26, 27],
        "probe_layer_reference": 11,
        "intervention_positions": "continuation_prediction_positions_only",
        "preflight_components": ["L27H0", "L27MLP"],
    }


def stage27pa_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration, adapter, runner, and tests before any Qwen hook result is generated.",
        "Verify Stage 16 Qwen CPL2 PASS and Stage 27O Pythia-1B drive-local steering PASS source contracts.",
        "Load Qwen/Qwen2.5-1.5B at revision 8faed761d45a263340a0528343f099c05c9a4323.",
        "Inspect candidate late layers 24-27 and verify attention output projection and MLP module paths.",
        "Run one actual CPL2-style prompt/continuation row with no hook, one attention-head scale hook, and one MLP scale hook.",
        "Confirm hooks are continuation-prediction-position localized: positions before the first prediction position remain unchanged.",
        "Confirm each hook changes logits at prediction positions and yields finite continuation log-probabilities.",
    )


def stage27pa_gates() -> tuple[Stage27PAGate, ...]:
    return (
        Stage27PAGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 16 Qwen CPL2 PASS, Stage 16 manifest revision match, and Stage 27O PASS source contracts are verified.",
        ),
        Stage27PAGate(
            name="model_revision",
            kind="pass_floor",
            criterion="Loaded Qwen model revision matches 8faed761d45a263340a0528343f099c05c9a4323.",
        ),
        Stage27PAGate(
            name="adapter_paths",
            kind="primary",
            criterion="Every candidate layer exposes attention output projection self_attn.o_proj and MLP module mlp.",
        ),
        Stage27PAGate(
            name="attention_hook_effect",
            kind="primary",
            criterion="A scaled attention-head hook changes logits at prediction positions while leaving earlier positions unchanged.",
        ),
        Stage27PAGate(
            name="mlp_hook_effect",
            kind="primary",
            criterion="A scaled MLP hook changes logits at prediction positions while leaving earlier positions unchanged.",
        ),
    )


def stage27pa_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT",
        "null_status": "NULL_QWEN_HOOK_ADAPTER_PREFLIGHT_NOT_READY",
        "claim_if_pass": (
            "CAS Harness has a validated Qwen2.5-1.5B component-hook adapter for continuation-position attention-head "
            "and MLP interventions, unblocking Stage 27P drive-local Qwen eraser-cover steering."
        ),
        "scope_boundary": (
            "Stage 27P-A is only a hook-adapter preflight. It proves Qwen component hooks can be applied at the intended "
            "positions with finite effects; it does not prove Qwen steering, component attribution, or circuit control."
        ),
        "forbidden_claims": (
            "Do not claim Qwen steering, cross-architecture control, complete circuits, durable weight edits, open-ended "
            "generation control, or raw CAS-symbol understanding from Stage 27P-A."
        ),
    }


def stage27pa_payload() -> dict[str, Any]:
    payload = {
        "stage": "27P-A",
        "status": "PREREGISTERED_GPU_REQUIRED",
        "motivation": (
            "Stage 27O closed Pythia cross-scale steering with drive-local output-side eraser covers. Stage 27P moves to "
            "Qwen, but Qwen uses different module paths than Pythia. Stage 27P-A validates the hook adapter before any "
            "cross-architecture steering claim is attempted."
        ),
        "required_inputs": stage27pa_required_inputs(),
        "method": stage27pa_method(),
        "gates": [asdict(gate) for gate in stage27pa_gates()],
        "claim_boundary": stage27pa_claim_boundary(),
        "execution_order": [
            "commit_preregistration_adapter_runner_and_tests",
            "verify_stage16_and_stage27o_contracts",
            "load_pinned_qwen_model",
            "inspect_adapter_paths",
            "run_attention_and_mlp_position_localized_hook_smoke",
            "record_preflight_result",
        ],
    }
    payload["validation"] = validate_stage27pa_payload(payload)
    return payload


def validate_stage27pa_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    inputs = payload.get("required_inputs", {})
    if payload.get("status") != "PREREGISTERED_GPU_REQUIRED":
        errors.setdefault("status", []).append("Stage 27P-A starts as GPU-required preregistration.")
    if inputs.get("stage16_cpl2_status") != "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES":
        errors.setdefault("required_inputs", []).append("Stage 27P-A must inherit the Stage 16 Qwen CPL2 PASS.")
    if inputs.get("stage27o_status") != "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING":
        errors.setdefault("required_inputs", []).append("Stage 27P-A must inherit the Stage 27O Pythia-1B PASS.")
    if inputs.get("intervention_positions") != "continuation_prediction_positions_only":
        errors.setdefault("required_inputs", []).append("Stage 27P-A must localize to continuation prediction positions.")
    if inputs.get("candidate_layers") != [24, 25, 26, 27]:
        errors.setdefault("required_inputs", []).append("Stage 27P-A candidate layers are locked to 24-27.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("adapter_paths", "attention_hook_effect", "mlp_hook_effect"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("Qwen steering", "cross-architecture control", "complete circuits", "durable weight edits"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
