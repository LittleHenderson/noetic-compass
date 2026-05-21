from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27l_calibrated_eraser_steering.py"


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


def test_parse_scale_grid_bounds_values() -> None:
    stage27l = _load_module("stage27l_runner_grid")

    assert stage27l._parse_scale_grid("0,0.25,1.0") == [0.0, 0.25, 1.0]

    try:
        stage27l._parse_scale_grid("-0.1,0.5")
    except ValueError as exc:
        assert "within [0, 1]" in str(exc)
    else:
        raise AssertionError("expected bad scale grid to fail")


def test_choose_best_scale_prefers_mean_then_positive_share_then_less_severe() -> None:
    stage27l = _load_module("stage27l_runner_choose")
    calibration = [
        {"scale": 0.0, "increment": {"mean": 1.0, "positive_share": 0.5}},
        {"scale": 0.25, "increment": {"mean": 1.0, "positive_share": 0.6}},
        {"scale": 0.5, "increment": {"mean": 0.9, "positive_share": 1.0}},
    ]

    assert stage27l._choose_best_scale(calibration)["scale"] == 0.25


def test_load_stage27k_contract_checks_grey_status() -> None:
    stage27l = _load_module("stage27l_runner_contract")
    path = ROOT / ".tmp_stage27l_stage27k_contract.json"
    try:
        path.write_text(json.dumps({"status": "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL"}), encoding="utf-8")
        contract = stage27l._load_stage27k_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL"


def test_evaluate_mode_applies_drive_scales_and_random_controls(monkeypatch) -> None:
    stage27l = _load_module("stage27l_runner_eval")
    rows = [
        {"sample_id": "r1", "foundation_label": "F1T", "foundation_drive": 1},
        {"sample_id": "r2", "foundation_label": "F2T", "foundation_drive": 2},
    ]

    def fake_margin(row, _model, _tokenizer, _device, *, component_scales=None):
        base = float(row["foundation_drive"])
        if component_scales is None:
            return base
        scale = float(component_scales[0][1])
        return base + (1.0 - scale)

    monkeypatch.setattr(stage27l, "_margin_for_row", fake_margin)
    monkeypatch.setattr(stage27l, "_names_to_components", lambda names: names)

    result = stage27l._evaluate_mode(
        rows,
        object(),
        object(),
        object(),
        eraser_cover=["L1MLP"],
        random_eraser_covers=[["L2MLP"]],
        drive_scales={"1": 0.0, "2": 0.5},
    )

    assert result["row_reports"][0]["scale"] == 0.0
    assert result["row_reports"][1]["scale"] == 0.5
    assert result["increment"]["mean"] == 0.75


def test_status_boundaries() -> None:
    stage27l = _load_module("stage27l_runner_status")
    report = {
        "source_contracts": {
            "stage7_prefix": {"formal_gate_valid": True},
            "stage27j": {"formal_gate_valid": True},
            "stage27k": {"formal_gate_valid": True},
        },
        "split_contract": {"learn_eval_disjoint": True},
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

    assert stage27l._status_from_gates(report) == "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["drive_calibrated"]["vs_random"]["win_share"] = 0.4
    assert stage27l._status_from_gates(report) == "PASS_BOUNDED_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["global"]["vs_random"]["win_share"] = 0.56
    assert stage27l._status_from_gates(report) == "GREY_CALIBRATED_ERASER_STEERING_PARTIAL"
    report["evaluation"]["global"]["vs_random"]["win_share"] = 0.4
    report["evaluation"]["global"]["increment"]["mean"] = -1.0
    report["evaluation"]["drive_calibrated"]["increment"]["mean"] = -1.0
    assert stage27l._status_from_gates(report) == "NULL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"
    report["source_contracts"]["stage27k"]["formal_gate_valid"] = False
    assert (
        stage27l._status_from_gates(report)
        == "STAGE27L_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )

