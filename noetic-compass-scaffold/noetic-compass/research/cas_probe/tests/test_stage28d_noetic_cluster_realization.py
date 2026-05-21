from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage28d_noetic_cluster_realization.py"


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


def test_cluster_fixture_rows_have_spans_and_two_targets() -> None:
    stage28d = _load_module("stage28d_runner_fixture")

    rows = stage28d._cluster_fixture_rows()

    assert len(rows) == 24
    for row in rows:
        assert len(row["target_indices"]) == 2
        assert row["english"][row["phrase_start"] : row["phrase_end"]] == row["phrase"]


def test_replacement_control_pairs_use_involutions_when_available() -> None:
    stage28d = _load_module("stage28d_runner_controls")

    pairs = stage28d._replacement_control_pairs([1, 7])  # ^2 + ^8
    rendered = {tuple(stage28d._NOETIC_LABELS[idx] for idx in pair) for pair in pairs}

    assert ("^8", "^3") in rendered
    assert ("^2", "^9") in rendered


def test_row_zscore_and_pair_score() -> None:
    stage28d = _load_module("stage28d_runner_z")

    z = stage28d._row_zscore(np.asarray([1.0, 2.0, 3.0]))

    assert abs(float(z.mean())) < 1e-9
    assert abs(float(z.std()) - 1.0) < 1e-9
    assert stage28d._pair_score(np.asarray([1.0, 3.0, 5.0]), [0, 2]) == 3.0


def test_score_cluster_readout_rewards_target_pair_over_controls() -> None:
    stage28d = _load_module("stage28d_runner_score")
    rows = stage28d._cluster_fixture_rows()[:2]

    class DummyScaler:
        def transform(self, X):
            return X

    class DummyClf:
        def decision_function(self, X):
            logits = np.zeros((len(X), 10), dtype=np.float64)
            for i, row in enumerate(rows):
                for idx in row["target_indices"]:
                    logits[i, idx] = 5.0
            return logits

    metrics = stage28d._score_cluster_readout({"scaler": DummyScaler(), "clf": DummyClf()}, np.zeros((2, 3)), rows)

    assert metrics["positive_margin_count"] == 2
    assert metrics["mean_target_minus_hard_control_z"] > 0
    assert metrics["mean_target_labels_in_top4"] >= 2.0


def test_status_boundaries() -> None:
    stage28d = _load_module("stage28d_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "readout_results": {
            "phrase_mean": {
                "eligible_probe_floor": True,
                "passes_all_primary_gates": True,
                "metrics": {"mean_target_minus_hard_control_z": 0.2, "positive_margin_share": 0.8},
            }
        },
    }

    assert stage28d._status_from_gates(report) == "PASS_BOUNDED_NOETIC_CLUSTER_REALIZATION"
    report["readout_results"]["phrase_mean"]["passes_all_primary_gates"] = False
    assert stage28d._status_from_gates(report) == "GREY_NOETIC_CLUSTER_REALIZATION_PARTIAL"
    report["readout_results"]["phrase_mean"]["metrics"]["mean_target_minus_hard_control_z"] = -0.1
    assert stage28d._status_from_gates(report) == "NULL_NOETIC_CLUSTER_REALIZATION_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage28d._status_from_gates(report) == "STAGE28D_NOETIC_CLUSTER_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
