from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage28c_noetic_phrase_level_realization.py"


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


def test_phrase_vectors_from_layer_returns_first_last_and_mean() -> None:
    stage28c = _load_module("stage28c_runner_vectors")
    layer = np.asarray(
        [
            [0.0, 0.0],
            [1.0, 3.0],
            [5.0, 7.0],
            [9.0, 11.0],
        ],
        dtype=np.float64,
    )

    vectors = stage28c._phrase_vectors_from_layer(layer, [1, 2, 3])

    np.testing.assert_allclose(vectors["phrase_first"], [1.0, 3.0])
    np.testing.assert_allclose(vectors["phrase_last"], [9.0, 11.0])
    np.testing.assert_allclose(vectors["phrase_mean"], [5.0, 7.0])


def test_candidate_pass_requires_probe_floor_and_all_metrics() -> None:
    stage28c = _load_module("stage28c_runner_candidate")
    gates = {
        "min_probe_test_acc": 0.5,
        "min_exact_accuracy": 0.45,
        "max_exact_binomial_p": 0.025,
        "min_mean_target_probability": 0.15,
        "min_top2_accuracy": 0.65,
        "min_involution_partner_positive_share": 0.60,
    }
    metrics = {
        "exact_accuracy": 0.5,
        "exact_binomial_p_vs_chance": 0.01,
        "mean_target_probability": 0.2,
        "top2_accuracy": 0.7,
        "involution_partner_positive_share": 0.7,
    }

    assert stage28c._candidate_pass(metrics, {"test_acc": 0.8}, gates)
    assert not stage28c._candidate_pass(metrics, {"test_acc": 0.4}, gates)
    metrics["exact_binomial_p_vs_chance"] = 0.03
    assert not stage28c._candidate_pass(metrics, {"test_acc": 0.8}, gates)


def test_status_boundaries() -> None:
    stage28c = _load_module("stage28c_runner_status")
    base_metrics = {
        "exact_accuracy": 0.125,
        "mean_target_probability": 0.12,
        "top2_accuracy": 0.15,
    }
    candidate_metrics = {
        "exact_accuracy": 0.5,
        "mean_target_probability": 0.2,
        "top2_accuracy": 0.7,
    }
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "gates": {"min_mean_target_probability": 0.15, "min_top2_accuracy": 0.65},
        "readout_results": {
            "phrase_first": {
                "is_phrase_level_candidate": False,
                "eligible_probe_floor": True,
                "passes_all_primary_gates": False,
                "metrics": base_metrics,
            },
            "phrase_mean": {
                "is_phrase_level_candidate": True,
                "eligible_probe_floor": True,
                "passes_all_primary_gates": True,
                "metrics": candidate_metrics,
            },
        },
    }

    assert stage28c._status_from_gates(report) == "PASS_BOUNDED_NOETIC_PHRASE_LEVEL_REALIZATION"
    report["readout_results"]["phrase_mean"]["passes_all_primary_gates"] = False
    assert stage28c._status_from_gates(report) == "GREY_NOETIC_PHRASE_LEVEL_REALIZATION_PARTIAL"
    report["readout_results"]["phrase_mean"]["metrics"]["exact_accuracy"] = 0.1
    report["readout_results"]["phrase_mean"]["metrics"]["mean_target_probability"] = 0.1
    report["readout_results"]["phrase_mean"]["metrics"]["top2_accuracy"] = 0.1
    assert stage28c._status_from_gates(report) == "NULL_NOETIC_PHRASE_LEVEL_REALIZATION_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage28c._status_from_gates(report) == "STAGE28C_NOETIC_PHRASE_LEVEL_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"


def test_status_rejects_no_eligible_phrase_level_candidate() -> None:
    stage28c = _load_module("stage28c_runner_probe_floor")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "gates": {"min_mean_target_probability": 0.15, "min_top2_accuracy": 0.65},
        "readout_results": {
            "phrase_first": {
                "is_phrase_level_candidate": False,
                "eligible_probe_floor": True,
                "passes_all_primary_gates": False,
                "metrics": {"exact_accuracy": 0.1, "mean_target_probability": 0.1, "top2_accuracy": 0.1},
            },
            "phrase_mean": {
                "is_phrase_level_candidate": True,
                "eligible_probe_floor": False,
                "passes_all_primary_gates": False,
                "metrics": {"exact_accuracy": 0.5, "mean_target_probability": 0.2, "top2_accuracy": 0.7},
            },
        },
    }

    assert stage28c._status_from_gates(report) == "NULL_NOETIC_PHRASE_LEVEL_REALIZATION_PROBE_FLOOR_NOT_MET"
