from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27o_drive_local_cross_scale_eraser_steering.py"


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


def test_load_stage27n_contract_accepts_grey_positive_source() -> None:
    stage27o = _load_module("stage27o_runner_stage27n_contract")
    path = ROOT / ".tmp_stage27o_stage27n_contract.json"
    try:
        path.write_text(
            json.dumps(
                {
                    "status": "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL",
                    "source_contracts": {"stage8": {"formal_gate_valid": True}},
                    "loaded_model_contract": {"formal_gate_valid": True},
                    "evaluation": {
                        "global": {"increment": {"mean": 0.1}},
                        "drive_calibrated": {"increment": {"mean": 0.2}},
                    },
                }
            ),
            encoding="utf-8",
        )
        contract = stage27o._load_stage27n_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL"


def test_drive_local_cover_contract_requires_all_drives() -> None:
    stage27o = _load_module("stage27o_runner_cover_contract")
    covers = {str(drive): [f"L12H{i}" for i in range(6)] for drive in range(1, 8)}

    good = stage27o._drive_local_cover_contract(covers, 6)
    covers["7"] = ["L12H0"]
    bad = stage27o._drive_local_cover_contract(covers, 6)

    assert good["formal_gate_valid"] is True
    assert bad["formal_gate_valid"] is False


def test_status_boundaries() -> None:
    stage27o = _load_module("stage27o_runner_status")
    report = {
        "source_contracts": {
            "stage8_cpl2": {"formal_gate_valid": True},
            "stage8_manifest": {"formal_gate_valid": True},
            "stage27n": {"formal_gate_valid": True},
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

    assert stage27o._status_from_gates(report) == "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["drive_local"]["vs_random"]["win_share"] = 0.56
    assert stage27o._status_from_gates(report) == "GREY_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_PARTIAL"
    report["evaluation"]["drive_local"]["vs_random"]["win_share"] = 0.4
    report["evaluation"]["drive_local"]["increment"]["mean"] = -1.0
    assert stage27o._status_from_gates(report) == "NULL_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"
    report["loaded_model_contract"]["formal_gate_valid"] = False
    assert (
        stage27o._status_from_gates(report)
        == "STAGE27O_DRIVE_LOCAL_CROSS_SCALE_ERASER_STEERING_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
    )
