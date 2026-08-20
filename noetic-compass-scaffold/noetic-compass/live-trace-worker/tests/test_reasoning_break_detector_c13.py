"""Adversarial offline tests for the first C13 detector pipeline."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_reasoning_break_detector_c13.py"
)
SPEC = importlib.util.spec_from_file_location("run_reasoning_break_detector_c13", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
c13 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = c13
SPEC.loader.exec_module(c13)


@pytest.fixture(scope="module")
def config() -> dict:
    return c13.build_default_preregistration()


@pytest.fixture(scope="module")
def dataset(config: dict) -> dict:
    return c13.build_canonical_synthetic_fixture(config)


@pytest.fixture(scope="module")
def result(config: dict, dataset: dict) -> dict:
    return c13.run_pipeline(dataset, config, code_path=SCRIPT_PATH)


def _resign_config(config: dict) -> dict:
    return c13.self_hash(config, "config_sha256")


def _resign_only_dataset_root(dataset: dict) -> dict:
    return c13.self_hash(dataset, "dataset_sha256")


def _row_for_split(dataset: dict, split: str) -> int:
    return next(
        index
        for index, row in enumerate(dataset["feature_records"])
        if row["split"] == split
    )


def test_operational_pipeline_is_calibrated_temporal_controlled_and_truthfully_bounded(
    config: dict, dataset: dict, result: dict
) -> None:
    assert result["schema_version"] == c13.RESULT_SCHEMA
    assert result["capability_id"] == c13.CAPABILITY_ID
    assert result["status"] == c13.RESULT_STATUS
    assert result["packet_eligibility"] == "NOT_PACKET_ELIGIBLE"
    assert result["real_model_verification"] == "NOT_REAL_MODEL_VERIFIED"
    assert result["scientific_status"] == "NOT_A_SCIENTIFIC_RESULT"
    assert result["boundaries"] == {
        "packet_eligibility": "NOT_PACKET_ELIGIBLE",
        "real_model_verification": "NOT_REAL_MODEL_VERIFIED",
        "scientific_status": "NOT_A_SCIENTIFIC_RESULT",
        "claim_boundary": c13.RESULT_CLAIM_BOUNDARY,
    }

    provenance = result["provenance"]
    assert provenance["input_artifact"]["raw_sha256"] == c13.sha256_bytes(
        c13.canonical_json_bytes(dataset)
    )
    assert provenance["input_artifact"]["self_hash_sha256"] == dataset["dataset_sha256"]
    assert provenance["input_artifact"]["tree_sha256"] == dataset["registration"]["tree_sha256"]
    assert provenance["configuration"]["raw_sha256"] == c13.sha256_bytes(
        c13.canonical_json_bytes(config)
    )
    assert provenance["configuration"]["self_hash_sha256"] == config["config_sha256"]
    assert provenance["code"]["sha256"] == c13.sha256_bytes(SCRIPT_PATH.read_bytes())

    candidates = result["selection"]["candidates_validation_only"]
    assert {row["window"] for row in candidates} == {"W0", "W1", "Wk"}
    assert {row["layer"] for row in candidates} == {0, 1, 2}
    assert all(set(row) == c13.CANDIDATE_ROW_KEYS for row in candidates)
    assert all(not any("test" in key for key in row) for row in candidates)
    assert result["selection"]["test_access_audit"] == {
        "policy": c13.TEST_POLICY,
        "reads_before_freeze": 0,
        "reads_after_freeze": 1,
    }
    assert result["selection"]["frozen_decision"]["thresholds"] == config["decision"]["thresholds"]
    assert result["calibration"]["fit_partition"] == "validation"
    assert result["calibration"]["threshold_source"] == "preregistration_exact_no_runtime_override"

    test_metrics = result["hidden_detector"]["test_metrics"]
    assert 0.0 <= test_metrics["brier"] <= 1.0
    assert 0.0 <= test_metrics["ece"] <= 1.0
    assert 0.0 <= test_metrics["coverage"] <= 1.0
    assert sum(test_metrics["decision_counts"].values()) == result["split_audit"]["counts"]["test"]
    assert all(
        0.0 <= row["calibrated_break_risk"] <= 1.0
        and row["decision"] in {"CLEAR", "ALERT", "ABSTAIN"}
        for row in result["hidden_detector"]["test_predictions"]
    )

    surface = result["controls"]["surface_only"]
    assert surface["feature_source"] == "surface_text_only_no_trajectory_values"
    shuffled = result["controls"]["shuffled_labels"]
    assert shuffled["selection_aware"] is True
    assert shuffled["group_vectors_permuted_without_crossing_splits"] is True
    assert len(shuffled["trials"]) == config["negative_control"]["trials"]
    assert result["preregistered_decision_gates"]["scope"] == "SYNTHETIC_ENGINEERING_ONLY"
    assert result["preregistered_decision_gates"]["status"] in {
        "PASS_SYNTHETIC_ENGINEERING_GATES",
        "FAIL_SYNTHETIC_ENGINEERING_GATES",
    }
    assert c13.verify_result(result, dataset, config, code_path=SCRIPT_PATH) == result


def test_fixture_labels_are_independent_table_rows_fixed_before_features(
    dataset: dict,
) -> None:
    assert dataset["label_contract"] == {
        "task": "BINARY_REASONING_BREAK_EVENT",
        "values": {"0": "NO_BREAK", "1": "BREAK"},
        "source": c13.LABEL_SOURCE,
        "assignment_stage": c13.LABEL_STAGE,
        "feature_table_contains_labels": False,
    }
    assert all("break_label" not in row for row in dataset["feature_records"])
    assert all(
        row["annotation_source"] == c13.LABEL_SOURCE
        and row["label_assignment_stage"] == c13.LABEL_STAGE
        and row["annotated_without_trajectory_access"] is True
        for row in dataset["event_labels"]
    )


def test_registered_split_is_group_disjoint_and_each_split_has_both_classes(
    config: dict, dataset: dict
) -> None:
    view = c13.validate_dataset(dataset, config)
    groups = {
        split: set(view.group_ids[view.indices[split]].tolist()) for split in c13.SPLITS
    }
    assert not groups["train"] & groups["validation"]
    assert not groups["train"] & groups["test"]
    assert not groups["validation"] & groups["test"]
    assert all(set(view.labels[view.indices[split]].tolist()) == {0, 1} for split in c13.SPLITS)


def test_temporal_feature_contract_has_w0_w1_and_wk(config: dict, dataset: dict) -> None:
    view = c13.validate_dataset(dataset, config)
    hidden = dataset["capture_contract"]["hidden_width"] * 2
    k = config["windows"]["k"]
    assert c13.temporal_features(view, window="W0", layer=1, k=k).shape == (
        len(view.labels),
        hidden,
    )
    assert c13.temporal_features(view, window="W1", layer=1, k=k).shape == (
        len(view.labels),
        hidden * 2,
    )
    assert c13.temporal_features(view, window="Wk", layer=1, k=k).shape == (
        len(view.labels),
        hidden * 4,
    )


def test_group_leakage_is_rejected_even_after_all_hashes_are_recomputed(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    first = attacked["feature_records"][0]
    sibling_index = next(
        index
        for index, row in enumerate(attacked["feature_records"][1:], start=1)
        if row["group_id"] == first["group_id"]
    )
    attacked["feature_records"][sibling_index]["split"] = "validation"
    attacked["event_labels"][sibling_index]["split"] = "validation"
    attacked = c13.resign_dataset(attacked)
    with pytest.raises(ValueError, match="group leakage"):
        c13.validate_dataset(attacked, config)


def test_label_feature_mismatch_is_rejected_after_rehash(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    attacked["event_labels"][0]["event_id"] = "independent-but-wrong-event"
    attacked = c13.resign_dataset(attacked)
    with pytest.raises(ValueError, match="label/feature mismatch for event_id"):
        c13.validate_dataset(attacked, config)


def test_test_metric_cannot_enter_candidate_selection() -> None:
    row = {
        "window": "W1",
        "layer": 1,
        "validation_brier": 0.1,
        "validation_ece": 0.1,
        "validation_balanced_accuracy": 0.9,
        "validation_coverage": 0.9,
        "validation_selective_balanced_accuracy": 0.9,
        "test_balanced_accuracy": 1.0,
    }
    with pytest.raises(ValueError, match="test peeking rejected"):
        c13.select_candidate_on_validation([row], window_order=c13.WINDOWS)


def test_test_partition_guard_refuses_read_before_freeze() -> None:
    guard = c13.TestPartitionGuard(np.asarray([7, 8, 9]))
    with pytest.raises(RuntimeError, match="before decision freeze"):
        guard.read("A" * 64)
    assert guard.reads_before_freeze == 1
    freeze_hash = "B" * 64
    guard.freeze(freeze_hash)
    with pytest.raises(RuntimeError, match="freeze hash mismatch"):
        guard.read("C" * 64)
    assert guard.read(freeze_hash).tolist() == [7, 8, 9]


def test_duplicate_record_ids_are_rejected_after_rehash(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    attacked["feature_records"][1]["record_id"] = attacked["feature_records"][0]["record_id"]
    attacked["event_labels"][1]["record_id"] = attacked["event_labels"][0]["record_id"]
    attacked = c13.resign_dataset(attacked)
    with pytest.raises(ValueError, match="duplicate record IDs"):
        c13.validate_dataset(attacked, config)


def test_nonfinite_trajectory_data_is_rejected_before_hashing(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    attacked["feature_records"][0]["trajectory"]["residual_states"][0][0][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite data"):
        c13.validate_dataset(attacked, config)


def test_dataset_self_hash_tamper_is_rejected(config: dict, dataset: dict) -> None:
    attacked = deepcopy(dataset)
    attacked["feature_records"][0]["surface_text"] += " tampered"
    with pytest.raises(ValueError, match="dataset self-hash mismatch"):
        c13.validate_dataset(attacked, config)


def test_input_tree_tamper_is_rejected_even_with_valid_root_self_hash(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    attacked["registration"]["tree_sha256"] = "A" * 64
    attacked = _resign_only_dataset_root(attacked)
    with pytest.raises(ValueError, match="input tree hash mismatch"):
        c13.validate_dataset(attacked, config)


def test_threshold_drift_is_rejected_by_dataset_preregistration_binding(
    config: dict, dataset: dict
) -> None:
    drifted = deepcopy(config)
    drifted["decision"]["thresholds"]["alert_min_risk"] = 0.75
    drifted = _resign_config(drifted)
    c13.validate_preregistration(drifted)
    with pytest.raises(ValueError, match="threshold/config drift"):
        c13.validate_dataset(dataset, drifted)


def test_result_threshold_drift_is_rejected_even_if_result_is_rehashed(
    config: dict, dataset: dict, result: dict
) -> None:
    attacked = deepcopy(result)
    attacked["calibration"]["thresholds"]["alert_min_risk"] = 0.75
    attacked = c13.self_hash(attacked, "result_sha256")
    with pytest.raises(ValueError, match="result threshold drift"):
        c13.verify_result(attacked, dataset, config, code_path=SCRIPT_PATH)


def test_result_self_hash_tamper_is_rejected(
    config: dict, dataset: dict, result: dict
) -> None:
    attacked = deepcopy(result)
    attacked["status"] = "FABRICATED_PASS"
    with pytest.raises(ValueError, match="result.status"):
        c13.verify_result(attacked, dataset, config, code_path=SCRIPT_PATH)


def test_all_one_class_labels_are_rejected_after_rehash(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    for row in attacked["event_labels"]:
        row["break_label"] = 1
    attacked = c13.resign_dataset(attacked)
    with pytest.raises(ValueError, match="all-one-class labels"):
        c13.validate_dataset(attacked, config)


def test_feature_table_cannot_smuggle_the_target_label(
    config: dict, dataset: dict
) -> None:
    attacked = deepcopy(dataset)
    attacked["feature_records"][0]["break_label"] = 1
    attacked = c13.resign_dataset(attacked)
    with pytest.raises(ValueError, match=r"feature_records\[0\] keyset mismatch"):
        c13.validate_dataset(attacked, config)


def test_canonical_json_reader_rejects_duplicate_nonfinite_and_pretty_bytes() -> None:
    with pytest.raises(ValueError, match="duplicate JSON key"):
        c13.strict_json_bytes(b'{"a":1,"a":2}', label="attack", max_bytes=100)
    with pytest.raises(ValueError, match="non-finite JSON number"):
        c13.strict_json_bytes(b'{"a":NaN}', label="attack", max_bytes=100)
    with pytest.raises(ValueError, match="not canonical JSON"):
        c13.strict_json_bytes(b'{"a": 1}', label="attack", max_bytes=100)


def test_config_rejects_invalid_abstention_threshold_order(config: dict) -> None:
    attacked = deepcopy(config)
    attacked["decision"]["thresholds"] = {
        "clear_max_risk": 0.70,
        "alert_min_risk": 0.80,
    }
    attacked = _resign_config(attacked)
    with pytest.raises(ValueError, match="must straddle 0.5"):
        c13.validate_preregistration(attacked)


def test_canonical_cli_artifacts_are_create_new_and_verifiable(tmp_path: Path) -> None:
    output_dir = tmp_path / "c13"
    assert c13.main(["emit-synthetic", "--directory", str(output_dir)]) == 0
    config_path = output_dir / "c13.preregistration.json"
    dataset_path = output_dir / "c13.synthetic-dataset.json"
    result_path = output_dir / "c13.result.json"
    assert config_path.read_bytes() == c13.canonical_json_bytes(
        json.loads(config_path.read_text(encoding="utf-8"))
    )
    assert dataset_path.read_bytes() == c13.canonical_json_bytes(
        json.loads(dataset_path.read_text(encoding="utf-8"))
    )
    assert c13.main(
        [
            "evaluate",
            "--config",
            str(config_path),
            "--dataset",
            str(dataset_path),
            "--output",
            str(result_path),
        ]
    ) == 0
    assert c13.main(
        [
            "verify",
            "--config",
            str(config_path),
            "--dataset",
            str(dataset_path),
            "--result",
            str(result_path),
        ]
    ) == 0
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        c13.main(
            [
                "evaluate",
                "--config",
                str(config_path),
                "--dataset",
                str(dataset_path),
                "--output",
                str(result_path),
            ]
        )


def test_all_result_numbers_are_finite(result: dict) -> None:
    def walk(value: object) -> None:
        if isinstance(value, float):
            assert math.isfinite(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    walk(result)
