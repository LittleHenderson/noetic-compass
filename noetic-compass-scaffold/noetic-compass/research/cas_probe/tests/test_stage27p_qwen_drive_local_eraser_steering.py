from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27p_qwen_drive_local_eraser_steering.py"
SPEC = ROOT / "stage27p_qwen_drive_local_eraser_steering_spec.py"


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


def test_stage27p_payload_validates_cleanly() -> None:
    spec = _load_module(SPEC, "stage27p_spec_payload")

    payload = spec.stage27p_payload()

    assert payload["status"] == "PREREGISTERED_GPU_REQUIRED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27pa_status"] == "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT"


def test_status_contract_accepts_expected_status() -> None:
    runner = _load_module(RUNNER, "stage27p_runner_contract")
    path = ROOT / ".tmp_stage27p_status_contract.json"
    try:
        path.write_text(json.dumps({"status": "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT"}), encoding="utf-8")
        contract = runner._load_status_contract(path, "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT")
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT"


def test_drive_local_cover_contract_requires_all_drives() -> None:
    runner = _load_module(RUNNER, "stage27p_runner_cover_contract")
    covers = {str(drive): [f"L24H{i}" for i in range(6)] for drive in range(1, 8)}

    good = runner._drive_local_cover_contract(covers, 6)
    covers["3"] = ["L24H0"]
    bad = runner._drive_local_cover_contract(covers, 6)

    assert good["formal_gate_valid"] is True
    assert bad["formal_gate_valid"] is False


def test_status_boundaries() -> None:
    runner = _load_module(RUNNER, "stage27p_runner_status")
    report = {
        "source_contracts": {
            "stage16_cpl2": {"formal_gate_valid": True},
            "stage16_manifest": {"formal_gate_valid": True},
            "stage27o": {"formal_gate_valid": True},
            "stage27pa": {"formal_gate_valid": True},
        },
        "loaded_model_contract": {"formal_gate_valid": True},
        "drive_local_cover_contract": {"formal_gate_valid": True},
        "split_contract": {
            "learn_eval_disjoint": True,
            "eval_rows": 56,
            "eval_rows_per_drive": 8,
        },
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "drive_local": {
                "increment": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_increment": {"mean": 0.1},
                "vs_random": {"win_share": 0.7, "sign_test_p": 0.01},
            },
        },
    }

    assert runner._status_from_gates(report) == "PASS_BOUNDED_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["drive_local"]["vs_random"]["win_share"] = 0.56
    assert runner._status_from_gates(report) == "GREY_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_PARTIAL"
    report["evaluation"]["drive_local"]["vs_random"]["win_share"] = 0.4
    report["evaluation"]["drive_local"]["increment"]["mean"] = -1.0
    assert runner._status_from_gates(report) == "NULL_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"
    report["loaded_model_contract"]["formal_gate_valid"] = False
    assert runner._status_from_gates(report) == "STAGE27P_QWEN_DRIVE_LOCAL_ERASER_STEERING_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
