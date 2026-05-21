from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage25_sae_feature_pilot.py"


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


def test_standardize_train_uses_train_only_statistics() -> None:
    stage25 = _load_module("stage25_runner_standardize")
    X = np.array([[1.0, 2.0], [3.0, 6.0], [100.0, 200.0]])
    Z, mean, std = stage25._standardize_train(X, np.array([0, 1]))

    assert np.allclose(mean, [2.0, 4.0])
    assert np.allclose(std, [1.0, 2.0])
    assert np.allclose(Z[0], [-1.0, -1.0])
    assert np.allclose(Z[1], [1.0, 1.0])


def test_feature_alignment_selects_matching_probe_direction() -> None:
    stage25 = _load_module("stage25_runner_alignment")
    decoder_features = np.eye(3)
    probe_directions = np.eye(3)

    alignment = stage25._feature_alignment(decoder_features, probe_directions)

    assert alignment["best_class_idx"].tolist() == [0, 1, 2]
    assert np.allclose(alignment["best_abs_alignment"], [1.0, 1.0, 1.0])


def test_specificity_detects_class_selective_feature() -> None:
    stage25 = _load_module("stage25_runner_specificity")
    y = np.array([0, 0, 1, 1])
    acts = np.zeros((4, 2), dtype=np.float64)
    acts[:, 0] = [10.0, 8.0, 0.1, 0.2]
    acts[:, 1] = [0.0, 0.1, 3.0, 4.0]

    result = stage25._feature_specificity(acts, y, np.array([0, 1, 2, 3]), [0])

    assert result["features"][0]["top_foundation"] == "F1T"
    assert result["features"][0]["top_minus_other"] > 0


def test_status_reports_pass_when_all_gates_clear() -> None:
    stage25 = _load_module("stage25_runner_status_pass")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "reconstruction": {"heldout_explained_variance": 0.9},
        "sparsity": {"mean_active_features_per_row": 20, "dead_feature_rate": 0.1},
        "cas_alignment": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
        "feature_specificity": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
        "causal_feature_drop": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
    }

    assert stage25._status_from_gates(report) == "PASS_BOUNDED_SAE_FEATURE_READOUT"


def test_status_reports_diagnostic_only_for_artifact_mismatch() -> None:
    stage25 = _load_module("stage25_runner_status_mismatch")
    report = {
        "artifact_contract": {"formal_gate_valid": False},
        "reconstruction": {"heldout_explained_variance": 1.0},
        "sparsity": {"mean_active_features_per_row": 20, "dead_feature_rate": 0.0},
        "cas_alignment": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
        "feature_specificity": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
        "causal_feature_drop": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
    }

    assert stage25._status_from_gates(report) == "STAGE25_SAE_FEATURE_READOUT_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
