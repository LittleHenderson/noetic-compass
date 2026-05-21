from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27m_robust_calibrated_eraser_steering.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_load_stage27l_contract_checks_pass_status() -> None:
    stage27m = _load_module("stage27m_runner_contract")
    path = ROOT / ".tmp_stage27m_stage27l_contract.json"
    try:
        path.write_text(
            json.dumps({"status": "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"}),
            encoding="utf-8",
        )
        contract = stage27m._load_stage27l_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"


def test_status_boundaries() -> None:
    stage27m = _load_module("stage27m_runner_status")
    report = {
        "source_contracts": {
            "stage7_prefix": {"formal_gate_valid": True},
            "stage27j": {"formal_gate_valid": True},
            "stage27l": {"formal_gate_valid": True},
        },
        "split_contract": {
            "learn_eval_disjoint": True,
            "eval_rows": 245,
            "eval_rows_per_drive": 35,
        },
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "global": {
                "increment": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_increment": {"mean": 0.1},
                "vs_random": {"win_share": 0.7, "sign_test_p": 0.01},
            },
            "drive_calibrated": {
                "increment": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_increment": {"mean": 0.1},
                "vs_random": {"win_share": 0.8, "sign_test_p": 0.001},
            },
        },
    }

    assert stage27m._status_from_gates(report) == "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["drive_calibrated"]["vs_random"]["win_share"] = 0.4
    assert stage27m._status_from_gates(report) == "PASS_BOUNDED_ROBUST_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["global"]["vs_random"]["win_share"] = 0.56
    assert stage27m._status_from_gates(report) == "GREY_ROBUST_CALIBRATED_ERASER_STEERING_PARTIAL"
    report["evaluation"]["global"]["vs_random"]["win_share"] = 0.4
    report["evaluation"]["global"]["increment"]["mean"] = -1.0
    report["evaluation"]["drive_calibrated"]["increment"]["mean"] = -1.0
    assert stage27m._status_from_gates(report) == "NULL_ROBUST_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"
    report["source_contracts"]["stage27l"]["formal_gate_valid"] = False
    assert (
        stage27m._status_from_gates(report)
        == "STAGE27M_ROBUST_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )


def test_status_rejects_small_eval_split() -> None:
    stage27m = _load_module("stage27m_runner_split")
    report = {
        "source_contracts": {"stage7_prefix": {"formal_gate_valid": True}},
        "split_contract": {
            "learn_eval_disjoint": True,
            "eval_rows": 112,
            "eval_rows_per_drive": 16,
        },
        "evaluation": {},
        "gates": {},
    }

    assert stage27m._status_from_gates(report) == "NULL_ROBUST_CALIBRATED_ERASER_STEERING_SPLIT_INVALID"

