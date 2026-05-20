from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SONAR = ROOT / "run_stage24a_token_level_cas_sonar.py"


def _load_module(name: str, path: Path):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _FakeTokenizer:
    def decode(self, token_ids: list[int]) -> str:
        return f"tok{token_ids[0]}"


def test_score_token_space_prefers_matching_direction() -> None:
    sonar = _load_module("stage24a_sonar", SONAR)
    directions = np.eye(3)
    output_w = np.eye(3)

    scores = sonar._score_token_space(directions, output_w)

    assert scores.shape == (3, 3)
    assert scores.argmax(axis=0).tolist() == [0, 1, 2]


def test_top_tokens_reports_positive_and_negative_tokens() -> None:
    sonar = _load_module("stage24a_sonar_top", SONAR)
    scores = np.zeros((8, 28), dtype=np.float64)
    scores[7, 0] = 10.0
    scores[1, 0] = -5.0

    top = sonar._top_tokens(scores, _FakeTokenizer(), 1)

    assert top["F1T"]["positive"][0]["token"] == "tok7"
    assert top["F1T"]["negative"][0]["token"] == "tok1"


def test_top_token_readability_flags_artifacts() -> None:
    sonar = _load_module("stage24a_sonar_readability", SONAR)
    block = {
        "F1T": {
            "positive": [{"token": " useful", "token_id": 1}, {"token": "�", "token_id": 2}],
            "negative": [{"token": "x", "token_id": 3}, {"token": " stable", "token_id": 4}],
        }
    }

    summary = sonar._top_token_readability(block)

    assert summary["total_top_tokens"] == 4
    assert summary["readable_top_tokens"] == 2
    assert summary["readable_rate"] == 0.5


def test_status_marks_artifact_dominated_top_tokens_null() -> None:
    sonar = _load_module("stage24a_sonar_status", SONAR)
    controls = {
        "same_drive_minus_hard_partner": {"empirical_p_random_ge_actual": 0.01},
        "same_register_minus_hard_partner": {"empirical_p_random_ge_actual": 0.01},
    }

    status = sonar._status_from_controls(controls, {"readable_rate": 0.25})

    assert status == "STAGE24A_SONAR_TOKEN_SIGNATURES_NULL_ARTIFACT_DOMINATED"


def test_status_marks_hash_mismatch_diagnostic_only() -> None:
    sonar = _load_module("stage24a_sonar_hash_status", SONAR)
    controls = {
        "same_drive_minus_hard_partner": {"empirical_p_random_ge_actual": 0.01},
        "same_register_minus_hard_partner": {"empirical_p_random_ge_actual": 0.01},
    }

    status = sonar._status_from_controls(
        controls,
        {"readable_rate": 1.0},
        {"formal_gate_valid": False},
    )

    assert status == "STAGE24A_SONAR_TOKEN_SIGNATURES_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"


def test_artifact_contract_detects_manifest_mismatch() -> None:
    sonar = _load_module("stage24a_sonar_contract", SONAR)
    manifest = ROOT / "__stage24a_contract_manifest_test.json"
    try:
        manifest.write_text('{"output_sha256": "expected"}', encoding="utf-8")
        contract = sonar._artifact_contract("actual", manifest)
    finally:
        if manifest.exists():
            manifest.unlink()

    assert contract["status"] == "LOCAL_RECAPTURE_HASH_MISMATCH"
    assert contract["formal_gate_valid"] is False


def test_pair_sets_include_same_drive_same_register_and_hard_partner() -> None:
    sonar = _load_module("stage24a_sonar_pairs", SONAR)
    rows = [
        {"foundation_label": "F1T", "hard_contrast_foundations": ["F2T", "F7E"]},
        {"foundation_label": "F2T", "hard_contrast_foundations": ["F1T"]},
    ]

    pairs = sonar._class_pair_sets(rows)

    assert (0, 1) in pairs["same_drive"]  # F1T/F1A
    assert (0, 4) in pairs["same_register"]  # F1T/F2T
    assert (0, 4) in pairs["hard_partner"]


def test_similarity_metrics_reward_grouped_class_signatures() -> None:
    sonar = _load_module("stage24a_sonar_metrics", SONAR)
    rows = [{"foundation_label": "F1T", "hard_contrast_foundations": ["F7E"]}]
    pairs = sonar._class_pair_sets(rows)
    scores = np.zeros((12, 28), dtype=np.float64)
    for class_idx, label in enumerate(sonar._FOUNDATION_LABELS):
        drive, register = sonar._parse_foundation(label)
        scores[drive - 1, class_idx] = 2.0
        scores[7 + "TAfE".index(register), class_idx] = 1.0

    metrics = sonar._similarity_metrics(scores, pairs)

    assert metrics["same_drive_mean_cosine"] > metrics["different_drive_register_mean_cosine"]
    assert metrics["same_register_mean_cosine"] > metrics["different_drive_register_mean_cosine"]


def test_missing_activation_artifact_fails_explicitly() -> None:
    sonar = _load_module("stage24a_sonar_missing", SONAR)
    missing_dir = ROOT / "__stage24a_missing__"
    args = type(
        "Args",
        (),
        {
            "input": str(missing_dir / "missing.jsonl"),
            "activations": str(missing_dir / "missing.npz"),
            "activation_manifest": str(missing_dir / "missing_manifest.json"),
            "stage7_report": str(missing_dir / "missing_report.json"),
            "allow_download": False,
            "n_random": 1,
            "seed": 1,
            "top_k": 1,
        },
    )()

    try:
        sonar.build_report(args)
    except FileNotFoundError as exc:
        assert "Stage 24A requires locked Stage 7 activations" in str(exc)
    else:
        raise AssertionError("expected missing activation artifact to fail explicitly")
