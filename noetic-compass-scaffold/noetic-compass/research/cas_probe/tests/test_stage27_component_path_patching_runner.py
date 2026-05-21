from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27_component_path_patching.py"


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


def test_head_targets_rejects_non_head_components() -> None:
    stage27 = _load_module("stage27_runner_targets")

    targets = stage27._head_targets([stage27.Component("head", 5, 3), stage27.Component("head", 1, 6)])
    assert targets == {5: {3}, 1: {6}}

    try:
        stage27._head_targets([stage27.Component("mlp", 5, None)])
    except ValueError as exc:
        assert "attention-head" in str(exc)
    else:
        raise AssertionError("expected non-head component to be rejected")


def test_matched_head_components_preserve_layer_and_avoid_selected() -> None:
    stage27 = _load_module("stage27_runner_matched")
    selected = ["L5H3", "L5H5", "L1H6"]

    matched = stage27._matched_head_components(selected, np.random.default_rng(42))

    assert len(matched) == len(selected)
    assert all(name not in selected for name in matched)
    assert [stage27._component_from_name(name).layer for name in matched] == [5, 5, 1]
    assert all(stage27._component_from_name(name).kind == "head" for name in matched)


def test_class_restoration_summary_orders_by_lost_accuracy() -> None:
    stage27 = _load_module("stage27_runner_class_restore")
    y = np.array([0, 0, 1, 1])
    baseline = np.array([0, 0, 1, 1])
    ablated = np.array([1, 1, 1, 0])
    patched = np.array([0, 0, 1, 1])

    result = stage27._class_restoration_summary(y, baseline, ablated, patched)

    assert result["top_restored_classes"][0]["foundation"] == "F1T"
    assert result["top_restored_classes"][0]["lost"] == 1.0
    assert result["top_restored_classes"][0]["recovery_fraction"] == 1.0
    assert result["n_top_lost_with_positive_restoration"] == 2


def test_status_boundaries() -> None:
    stage27 = _load_module("stage27_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "stage26_contract": {"formal_gate_valid": True},
        "path_patching": {"targeted_drop": 0.6, "recovery_fraction": 0.9},
        "matched_patch_control": {"empirical_p_random_ge_actual": 0.01},
        "sanity_controls": {"baseline_repeat_disagreement_rate": 0.0},
        "class_restoration": {"n_top_lost_with_positive_restoration": 3},
        "gates": {
            "min_targeted_drop": 0.25,
            "min_recovery_fraction": 0.5,
            "max_control_p": 0.05,
            "max_repeat_disagreement_rate": 0.0,
        },
    }

    assert stage27._status_from_gates(report) == "PASS_BOUNDED_COMPONENT_PATH_PATCHING"
    report["path_patching"]["recovery_fraction"] = 0.1
    assert stage27._status_from_gates(report) == "NULL_COMPONENT_PATH_PATCHING_NOT_ESTABLISHED"
    report["path_patching"]["recovery_fraction"] = 0.9
    report["matched_patch_control"]["empirical_p_random_ge_actual"] = 0.5
    assert stage27._status_from_gates(report) == "GREY_COMPONENT_PATH_PATCHING_PARTIAL"
