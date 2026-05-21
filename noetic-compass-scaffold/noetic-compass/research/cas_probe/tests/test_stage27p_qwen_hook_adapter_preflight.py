from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27p_qwen_hook_adapter_preflight.py"
SPEC = ROOT / "stage27p_qwen_hook_adapter_preflight_spec.py"


def _load_module(path: Path, name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage27pa_payload_validates_cleanly() -> None:
    spec = _load_module(SPEC, "stage27pa_spec_payload")

    payload = spec.stage27pa_payload()

    assert payload["status"] == "PREREGISTERED_GPU_REQUIRED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["model"] == "Qwen/Qwen2.5-1.5B"


def test_load_stage16_contract_checks_qwen_pass() -> None:
    runner = _load_module(RUNNER, "stage27pa_runner_stage16_contract")
    path = ROOT / ".tmp_stage27pa_stage16_contract.json"
    try:
        path.write_text(
            json.dumps(
                {
                    "status": "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES",
                    "model_name": "Qwen/Qwen2.5-1.5B",
                    "selected_layer_position": 11,
                    "n_cases": 112,
                    "key_comparisons": {"probe_readable_delta_vs_none": 0.79},
                }
            ),
            encoding="utf-8",
        )
        contract = runner._load_stage16_cpl2_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES"


def test_status_boundaries() -> None:
    runner = _load_module(RUNNER, "stage27pa_runner_status")
    report = {
        "source_contracts": {
            "stage16_cpl2": {"formal_gate_valid": True},
            "stage16_manifest": {"formal_gate_valid": True},
            "stage27o": {"formal_gate_valid": True},
        },
        "loaded_model_contract": {"formal_gate_valid": True},
        "adapter_contract": {"formal_gate_valid": True},
        "hook_effects": {
            "attention_head": {"finite": True, "position_localized": True, "prediction_effect": True},
            "mlp": {"finite": True, "position_localized": True, "prediction_effect": True},
        },
    }

    assert runner._status_from_gates(report) == "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT"
    report["hook_effects"]["mlp"]["prediction_effect"] = False
    assert runner._status_from_gates(report) == "NULL_QWEN_HOOK_ADAPTER_PREFLIGHT_NOT_READY"
    report["hook_effects"]["mlp"]["prediction_effect"] = True
    report["loaded_model_contract"]["formal_gate_valid"] = False
    assert runner._status_from_gates(report) == "STAGE27P_QWEN_HOOK_ADAPTER_PREFLIGHT_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
