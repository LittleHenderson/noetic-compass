from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "evaluate_40_element_probe.py"
)
SPEC = importlib.util.spec_from_file_location("evaluate_40_element_probe", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
evaluate_40_element_probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate_40_element_probe)


def _full_40e_distribution(samples_per_cell: int = 10) -> dict[str, int]:
    return {
        f"^{operator}|{domain}": samples_per_cell
        for operator in range(10)
        for domain in ("P", "C", "E", "O")
    }


def test_linear_probe_contract_matches_original_balanced_logistic_method():
    probe = evaluate_40_element_probe._build_linear_probe(C=0.25, max_iter=123)

    assert isinstance(probe, Pipeline)
    assert isinstance(probe.named_steps["standardscaler"], StandardScaler)

    logistic = probe.named_steps["logisticregression"]
    assert isinstance(logistic, LogisticRegression)
    assert logistic.C == 0.25
    assert logistic.max_iter == 123
    assert logistic.class_weight == "balanced"
    assert logistic.solver == "lbfgs"


def test_40e_readiness_gate_passes_complete_balanced_grid():
    gate = evaluate_40_element_probe.build_40e_readiness_gate(
        _full_40e_distribution(samples_per_cell=10),
        min_samples_per_cell=10,
    )

    assert gate["status"] == "packet_ready"
    assert gate["packet_ready"] is True
    assert gate["populated_expected_cells"] == 40
    assert gate["missing_cells"] == []
    assert gate["sparse_cells"] == {}
    assert gate["unexpected_cells"] == []
    assert gate["blocking_reasons"] == []


def test_40e_readiness_gate_blocks_missing_sparse_and_unexpected_cells():
    distribution = _full_40e_distribution(samples_per_cell=10)
    distribution.pop("^9|O")
    distribution["^0|P"] = 3
    distribution["bad|P"] = 7

    gate = evaluate_40_element_probe.build_40e_readiness_gate(
        distribution,
        min_samples_per_cell=10,
    )

    assert gate["status"] == "blocked_missing_balanced_40e_artifact"
    assert gate["packet_ready"] is False
    assert gate["missing_cells"] == ["^9|O"]
    assert gate["sparse_cells"] == {"^0|P": 3}
    assert gate["unexpected_cells"] == ["bad|P"]
    assert len(gate["blocking_reasons"]) == 3
    assert gate["required_artifact"]["name"] == "balanced_40_element_activation_dataset"
    assert "features" in gate["required_artifact"]["required_npz_keys"]
    assert "--require-balanced-40e" in gate["required_artifact"]["how_to_supply"]


def test_artifact_descriptor_hashes_file_for_packet_readiness(tmp_path):
    artifact = tmp_path / "metadata.json"
    artifact.write_text('{"model_id":"unit-test"}', encoding="utf-8")

    descriptor = evaluate_40_element_probe._artifact_descriptor(
        "metadata_json",
        "40e_capture_metadata_json",
        artifact,
    )

    expected_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert descriptor["artifact_id"] == "metadata_json"
    assert descriptor["artifact_type"] == "40e_capture_metadata_json"
    assert descriptor["content_sha256"] == expected_hash
    assert descriptor["byte_count"] == artifact.stat().st_size
    assert descriptor["storage_uri"] == str(artifact)


def test_require_balanced_40e_writes_guard_report_without_training(tmp_path, monkeypatch):
    dataset = tmp_path / "incomplete_40e.npz"
    metadata = tmp_path / "incomplete_40e.metadata.json"
    output = tmp_path / "guard_report.json"
    np.savez(
        dataset,
        features=np.zeros((3, 1, 2), dtype=np.float32),
        layers=np.array([0]),
        labels_domain=np.array(["P", "P", "P"]),
        labels_operator=np.array(["^0", "^0", "^0"]),
        prompts=np.array(["[a] prompt", "[b] prompt", "[c] prompt"]),
    )
    metadata.write_text('{"model_id":"unit-test-model"}', encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_40_element_probe.py",
            "--dataset",
            str(dataset),
            "--metadata",
            str(metadata),
            "--output",
            str(output),
            "--require-balanced-40e",
        ],
    )

    assert evaluate_40_element_probe.main() == 2
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["status"] == "blocked_missing_balanced_40e_artifact"
    assert report["model_id"] == "unit-test-model"
    assert report["readiness_gate"]["packet_ready"] is False
    assert report["readiness_gate"]["missing_cells"]
    assert report["artifacts"][0]["artifact_id"] == "activation_dataset_npz"
    assert report["method_contract"]["readout"] == "StandardScaler + LogisticRegression"
