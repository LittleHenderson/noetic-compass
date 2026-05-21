from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SONAR = ROOT / "run_stage24b_40_elements_token_sonar.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, SONAR)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _FakeTokenizer:
    def decode(self, token_ids: list[int]) -> str:
        return f"tok{token_ids[0]}"


def test_parse_element_splits_domain_and_noetic() -> None:
    sonar = _load_module("stage24b_parse")

    assert sonar._parse_element("A1") == ("A", 1)
    assert sonar._parse_element("D10") == ("D", 10)


def test_score_token_space_prefers_matching_direction() -> None:
    sonar = _load_module("stage24b_score")
    directions = np.eye(4)
    output_w = np.eye(4)

    scores = sonar._score_token_space(directions, output_w)

    assert scores.shape == (4, 4)
    assert scores.argmax(axis=0).tolist() == [0, 1, 2, 3]


def test_top_tokens_reports_positive_and_negative_tokens() -> None:
    sonar = _load_module("stage24b_top")
    scores = np.zeros((8, 40), dtype=np.float64)
    scores[7, 0] = 10.0
    scores[1, 0] = -5.0

    top = sonar._top_tokens(scores, _FakeTokenizer(), 1)

    assert top["A1"]["positive"][0]["token"] == "tok7"
    assert top["A1"]["negative"][0]["token"] == "tok1"


def test_pair_sets_include_same_domain_same_noetic_and_hard_partner() -> None:
    sonar = _load_module("stage24b_pairs")
    rows = [
        {"element_label": "A1", "hard_contrast_elements": ["A2", "D10"]},
        {"element_label": "A2", "hard_contrast_elements": ["A1"]},
    ]

    pairs = sonar._class_pair_sets(rows)

    assert (0, 1) in pairs["same_domain"]  # A1/A2
    assert (0, 10) in pairs["same_noetic"]  # A1/B1
    assert (0, 1) in pairs["hard_partner"]
    assert (0, 39) in pairs["hard_partner"]


def test_similarity_metrics_reward_structured_domain_and_noetic_signatures() -> None:
    sonar = _load_module("stage24b_metrics")
    rows = [{"element_label": "A1", "hard_contrast_elements": ["D10"]}]
    pairs = sonar._class_pair_sets(rows)
    scores = np.zeros((16, 40), dtype=np.float64)
    for class_idx, label in enumerate(sonar._LABEL_NAMES):
        domain, noetic = sonar._parse_element(label)
        scores["ABCD".index(domain), class_idx] = 2.0
        scores[4 + noetic - 1, class_idx] = 1.0

    metrics = sonar._similarity_metrics(scores, pairs)

    assert metrics["same_domain_mean_cosine"] > metrics["different_domain_noetic_mean_cosine"]
    assert metrics["same_noetic_mean_cosine"] > metrics["different_domain_noetic_mean_cosine"]


def test_status_marks_hash_mismatch_diagnostic_only() -> None:
    sonar = _load_module("stage24b_status")
    controls = {
        "same_domain_minus_hard_partner": {"empirical_p_random_ge_actual": 0.01},
        "same_noetic_minus_hard_partner": {"empirical_p_random_ge_actual": 0.01},
    }

    status = sonar._status_from_controls(
        controls,
        {"readable_rate": 1.0},
        {"formal_gate_valid": False},
    )

    assert status == "STAGE24B_40_ELEMENT_SONAR_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"


def test_artifact_contract_detects_manifest_mismatch() -> None:
    sonar = _load_module("stage24b_contract")
    manifest = ROOT / "__stage24b_contract_manifest_test.json"
    try:
        manifest.write_text('{"output_sha256": "expected"}', encoding="utf-8")
        contract = sonar._artifact_contract("actual", manifest)
    finally:
        if manifest.exists():
            manifest.unlink()

    assert contract["status"] == "LOCAL_RECAPTURE_HASH_MISMATCH"
    assert contract["formal_gate_valid"] is False


def test_artifact_contract_accepts_nested_replacement_contract() -> None:
    sonar = _load_module("stage24b_nested_contract")
    manifest = ROOT / "__stage24b_nested_contract_manifest_test.json"
    try:
        manifest.write_text(
            '{"replacement_artifact_contract": {"output_sha256": "actual"}}',
            encoding="utf-8",
        )
        contract = sonar._artifact_contract("actual", manifest)
    finally:
        if manifest.exists():
            manifest.unlink()

    assert contract["status"] == "LOCKED_ARTIFACT_MATCH"
    assert contract["formal_gate_valid"] is True
    assert contract["contract_source"] == "replacement_artifact_contract.output_sha256"


def test_missing_activation_artifact_fails_explicitly() -> None:
    sonar = _load_module("stage24b_missing")
    missing_dir = ROOT / "__stage24b_missing__"
    args = type(
        "Args",
        (),
        {
            "input": str(missing_dir / "missing.jsonl"),
            "activations": str(missing_dir / "missing.npz"),
            "activation_manifest": str(missing_dir / "missing_manifest.json"),
            "stage9_report": str(missing_dir / "missing_report.json"),
            "allow_download": False,
            "n_random": 1,
            "seed": 1,
            "top_k": 1,
        },
    )()

    try:
        sonar.build_report(args)
    except FileNotFoundError as exc:
        assert "Stage 24B requires locked Stage 9 40-Element activations" in str(exc)
    else:
        raise AssertionError("expected missing activation artifact to fail explicitly")
