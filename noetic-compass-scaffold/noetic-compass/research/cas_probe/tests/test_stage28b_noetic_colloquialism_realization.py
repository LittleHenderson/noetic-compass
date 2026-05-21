from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage28b_noetic_colloquialism_realization.py"


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


def test_fixture_rows_have_single_phrase_span_and_balanced_targets() -> None:
    stage28b = _load_module("stage28b_runner_fixture")

    rows = stage28b._fixture_rows()
    counts: dict[str, int] = {}
    for row in rows:
        phrase = row["phrase"]
        text = row["english"]
        counts[row["noetic"]] = counts.get(row["noetic"], 0) + 1
        assert text.count(phrase) == 1
        assert text[row["phrase_start"] : row["phrase_end"]] == phrase

    assert len(rows) == 40
    assert set(counts.values()) == {4}


def test_token_indices_overlapping_span_excludes_empty_offsets() -> None:
    stage28b = _load_module("stage28b_runner_offsets")

    offsets = [(0, 0), (0, 3), (4, 7), (8, 12)]

    assert stage28b._token_indices_overlapping_span(offsets, 4, 12) == [2, 3]
    assert stage28b._token_indices_overlapping_span(offsets, 12, 15) == []


def test_binomial_upper_tail_matches_exact_small_case() -> None:
    stage28b = _load_module("stage28b_runner_binom")

    # P(X>=2) for Binomial(3, 0.5) = 4/8.
    assert stage28b._binomial_upper_tail(2, 3, 0.5) == 0.5


def test_score_colloquialisms_computes_primary_metrics() -> None:
    stage28b = _load_module("stage28b_runner_score")
    fixture_rows = stage28b._fixture_rows()[:4]

    class DummyScaler:
        def transform(self, X):
            return X

    class DummyClf:
        def predict_proba(self, X):
            probs = np.full((len(X), 10), 0.01, dtype=np.float64)
            for i, row in enumerate(fixture_rows):
                probs[i, row["target_index"]] = 0.91
            probs /= probs.sum(axis=1, keepdims=True)
            return probs

    metrics = stage28b._score_colloquialisms({"scaler": DummyScaler(), "clf": DummyClf()}, np.zeros((4, 3)), fixture_rows)

    assert metrics["exact_accuracy"] == 1.0
    assert metrics["top2_accuracy"] == 1.0
    assert metrics["mean_target_probability"] > 0.9
    assert metrics["exact_binomial_p_vs_chance"] < 0.001


def test_status_boundaries() -> None:
    stage28b = _load_module("stage28b_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "probe": {"test_acc": 0.9},
        "gates": {
            "min_probe_test_acc": 0.5,
            "min_exact_accuracy": 0.45,
            "max_exact_binomial_p": 0.05,
            "min_mean_target_probability": 0.15,
            "min_top2_accuracy": 0.65,
            "min_involution_partner_positive_share": 0.60,
        },
        "colloquialism_metrics": {
            "exact_accuracy": 0.50,
            "exact_binomial_p_vs_chance": 0.01,
            "mean_target_probability": 0.20,
            "top2_accuracy": 0.70,
            "involution_partner_positive_share": 0.70,
        },
    }

    assert stage28b._status_from_gates(report) == "PASS_BOUNDED_NOETIC_COLLOQUIALISM_REALIZATION"
    report["colloquialism_metrics"]["top2_accuracy"] = 0.50
    assert stage28b._status_from_gates(report) == "GREY_NOETIC_COLLOQUIALISM_REALIZATION_PARTIAL"
    report["colloquialism_metrics"]["exact_accuracy"] = 0.10
    report["colloquialism_metrics"]["exact_binomial_p_vs_chance"] = 0.99
    report["colloquialism_metrics"]["mean_target_probability"] = 0.10
    assert stage28b._status_from_gates(report) == "NULL_NOETIC_COLLOQUIALISM_REALIZATION_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage28b._status_from_gates(report) == "STAGE28B_NOETIC_COLLOQUIALISM_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
