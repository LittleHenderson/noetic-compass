from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage28a_noetic_involution_sonar.py"


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


def test_noetic_index_maps_ten_to_zero_label_position() -> None:
    stage28a = _load_module("stage28a_runner_index")

    assert stage28a._noetic_index({"element_noetic_tks": 1}) == 0
    assert stage28a._noetic_index({"element_noetic_tks": 10}) == 9


def test_non_involution_pairs_exclude_formal_involutions() -> None:
    stage28a = _load_module("stage28a_runner_pairs")

    pairs = set(stage28a._non_involution_pairs())

    assert (1, 2) not in pairs
    assert (4, 5) not in pairs
    assert (7, 8) not in pairs
    assert (0, 1) in pairs


def test_opposition_metrics_reward_lower_involution_cosines() -> None:
    stage28a = _load_module("stage28a_runner_metrics")
    scores = np.zeros((20, 10), dtype=np.float64)
    for idx in range(10):
        scores[idx, idx] = 1.0
    # Make involution pairs explicitly opposed in token space.
    for left, right in ((1, 2), (4, 5), (7, 8)):
        scores[10 + left, left] = 2.0
        scores[10 + left, right] = -2.0

    metrics = stage28a._opposition_metrics(scores)

    assert metrics["non_involution_minus_involution_cosine"] > 0
    assert metrics["involution_pairs_below_median"] >= 2


def test_status_boundaries() -> None:
    stage28a = _load_module("stage28a_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "probe": {"test_acc": 0.8},
        "top_token_readability": {"readable_rate": 1.0},
        "opposition_metrics": {
            "non_involution_minus_involution_cosine": 0.2,
            "involution_pairs_below_median": 3,
        },
        "random_control_summary": {
            "non_involution_minus_involution_cosine": {"empirical_p_random_ge_actual": 0.01}
        },
        "gates": {
            "min_probe_test_acc": 0.5,
            "min_readable_rate": 0.5,
            "max_control_p": 0.05,
            "min_pairs_below_median": 2,
        },
    }

    assert stage28a._status_from_gates(report) == "PASS_BOUNDED_NOETIC_INVOLUTION_SONAR"
    report["random_control_summary"]["non_involution_minus_involution_cosine"]["empirical_p_random_ge_actual"] = 0.5
    assert stage28a._status_from_gates(report) == "GREY_NOETIC_INVOLUTION_SONAR_PARTIAL"
    report["opposition_metrics"]["non_involution_minus_involution_cosine"] = -0.1
    report["opposition_metrics"]["involution_pairs_below_median"] = 0
    assert stage28a._status_from_gates(report) == "NULL_NOETIC_INVOLUTION_SONAR_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage28a._status_from_gates(report) == "STAGE28A_NOETIC_INVOLUTION_SONAR_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"


def test_artifact_contract_accepts_replacement_contract() -> None:
    stage28a = _load_module("stage28a_runner_contract")
    manifest = ROOT / "__stage28a_contract_manifest_test.json"
    try:
        manifest.write_text('{"replacement_artifact_contract": {"output_sha256": "abc"}}', encoding="utf-8")

        contract = stage28a._artifact_contract("abc", manifest)
    finally:
        if manifest.exists():
            manifest.unlink()

    assert contract["status"] == "LOCKED_ARTIFACT_MATCH"
    assert contract["contract_source"] == "replacement_artifact_contract.output_sha256"
