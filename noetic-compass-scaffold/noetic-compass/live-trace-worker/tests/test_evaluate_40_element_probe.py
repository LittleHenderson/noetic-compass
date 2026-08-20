from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
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


def test_group_split_has_no_group_overlap_and_is_deterministic():
    groups = np.repeat(np.array([f"g{i}" for i in range(20)]), 2)
    features = np.zeros((len(groups), 2, 3), dtype=np.float32)
    labels = np.array([f"c{i % 4}" for i in range(len(groups))])

    first = evaluate_40_element_probe.build_group_train_validation_test_split(
        features,
        labels,
        groups,
        validation_size=0.2,
        test_size=0.2,
        seed=17,
    )
    second = evaluate_40_element_probe.build_group_train_validation_test_split(
        features,
        labels,
        groups,
        validation_size=0.2,
        test_size=0.2,
        seed=17,
    )

    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    train, validation, test = first
    train_groups = set(groups[train])
    validation_groups = set(groups[validation])
    test_groups = set(groups[test])
    assert not train_groups & validation_groups
    assert not train_groups & test_groups
    assert not validation_groups & test_groups
    assert sorted(np.concatenate(first).tolist()) == list(range(len(groups)))


@pytest.mark.parametrize(
    ("validation_size", "test_size"),
    [(0.0, 0.2), (0.2, 0.0), (0.6, 0.4), (1.0, 0.1)],
)
def test_group_split_rejects_invalid_fractions(validation_size, test_size):
    values = np.zeros((10, 1))
    with pytest.raises(ValueError):
        evaluate_40_element_probe.build_group_train_validation_test_split(
            values,
            np.arange(10),
            np.arange(10),
            validation_size=validation_size,
            test_size=test_size,
            seed=1,
        )


def test_layer_selection_reads_validation_only_and_has_fixed_tie_break():
    rows = [
        {"layer": 9, "validation_acc": 0.90, "validation_macro_f1": 0.80},
        {"layer": 3, "validation_acc": 0.95, "validation_macro_f1": 0.70},
        {"layer": 2, "validation_acc": 0.95, "validation_macro_f1": 0.70},
        {"layer": 4, "validation_acc": 0.95, "validation_macro_f1": 0.80},
    ]

    assert evaluate_40_element_probe.select_layer_on_validation(rows)["layer"] == 4


def test_layer_selection_rejects_test_metrics_in_selection_rows():
    with pytest.raises(ValueError, match="validation metrics only"):
        evaluate_40_element_probe.select_layer_on_validation(
            [
                {
                    "layer": 0,
                    "validation_acc": 0.5,
                    "validation_macro_f1": 0.5,
                    "test_acc": 1.0,
                }
            ]
        )


def test_registered_split_contract_uses_manifest_split_and_pair_id(tmp_path):
    scenario_ids = np.array([f"s-{split}-{cell}" for split in ("train", "val", "test") for cell in range(40)])
    labels = np.array(
        [
            cell
            for _split in ("train", "val", "test")
            for cell in evaluate_40_element_probe.EXPECTED_40E_CELLS
        ]
    )
    scenarios = []
    for scenario_id, label in zip(scenario_ids.tolist(), labels.tolist(), strict=True):
        _, split, cell_index = scenario_id.split("-")
        operator, domain = label.split("|")
        pair_index = int(cell_index) // 2
        focus = "A" if int(cell_index) % 2 == 0 else "B"
        scenarios.append(
            {
                "id": scenario_id,
                "metadata": {
                    "split": split,
                    "counterfactual_pair_id": f"pair-{split}-{pair_index}",
                },
                "expected_cas_axes": {
                    "element": label,
                    "operator": operator,
                    "domain": domain,
                },
                "prompt": f"Registered contrast {split} {pair_index}. Focus: {focus}.",
            }
        )
    manifest = tmp_path / "scenarios.json"
    manifest.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    train, validation, test, pair_ids = (
        evaluate_40_element_probe.load_registered_split_contract(
            scenario_manifest=manifest,
            scenario_ids=scenario_ids,
            labels=labels,
        )
    )

    assert len(train) == len(validation) == len(test) == 40
    assert set(pair_ids[train]).isdisjoint(set(pair_ids[validation]))
    assert set(pair_ids[train]).isdisjoint(set(pair_ids[test]))


def test_scenario_manifest_resolves_metadata_sibling_by_declared_basename(tmp_path):
    metadata_path = tmp_path / "capture.metadata.json"
    manifest = tmp_path / "registered_scenarios.json"
    manifest.write_text('{"scenarios":[]}', encoding="utf-8")

    resolved = evaluate_40_element_probe.resolve_scenario_manifest(
        metadata={"scenario_path": "data/registered_scenarios.json"},
        metadata_path=metadata_path,
        explicit_path=None,
    )

    assert resolved == manifest.resolve()


def test_registered_split_contract_rejects_pair_crossing_splits(tmp_path):
    scenario_ids = np.array([f"s-{split}-{cell}" for split in ("train", "val", "test") for cell in range(40)])
    labels = np.array(
        [
            cell
            for _split in ("train", "val", "test")
            for cell in evaluate_40_element_probe.EXPECTED_40E_CELLS
        ]
    )
    scenarios = []
    for scenario_id, label in zip(scenario_ids.tolist(), labels.tolist(), strict=True):
        _, split, cell_index = scenario_id.split("-")
        pair_index = int(cell_index) // 2
        pair_id = "crossing" if cell_index == "0" else f"pair-{split}-{pair_index}"
        focus = "A" if int(cell_index) % 2 == 0 else "B"
        scenarios.append(
            {
                "id": scenario_id,
                "metadata": {"split": split, "counterfactual_pair_id": pair_id},
                "expected_cas_axes": {"element": label},
                "prompt": f"Registered contrast {split} {pair_index}. Focus: {focus}.",
            }
        )
    manifest = tmp_path / "scenarios.json"
    manifest.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    with pytest.raises(ValueError, match="counterfactual pair crosses splits"):
        evaluate_40_element_probe.load_registered_split_contract(
            scenario_manifest=manifest,
            scenario_ids=scenario_ids,
            labels=labels,
        )


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
        scenario_ids=np.array(["s1", "s2", "s3"]),
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

    assert report["status"] == "blocked_unverified_registered_artifact_or_model_binding"
    assert report["schema_version"] == "cas_harness_40_element_probe_eval.v3"
    assert (
        report["readiness_gate"]["registered_artifact_binding"]["packet_eligibility"]
        == "NOT_PACKET_ELIGIBLE"
    )
    assert report["model_id"] == "unit-test-model"
    assert report["readiness_gate"]["packet_ready"] is False
    assert report["readiness_gate"]["missing_cells"]
    assert report["artifacts"][0]["artifact_id"] == "activation_dataset_npz"
    assert report["method_contract"]["readout"] == "StandardScaler + LogisticRegression"


def test_safe_npz_loader_never_unpickles_historical_object_prompts(tmp_path):
    dataset = tmp_path / "object_prompts.npz"
    np.savez(
        dataset,
        features=np.zeros((2, 1, 2), dtype=np.float32),
        layers=np.array([0]),
        labels_domain=np.array(["P", "P"]),
        labels_operator=np.array(["^0", "^1"]),
        prompts=np.array(["a", "b"], dtype=object),
        scenario_ids=np.array(["s1", "s2"]),
    )

    loaded = evaluate_40_element_probe.load_npz_without_pickle(dataset)

    assert loaded["prompts"] is None
    assert loaded["features"].shape == (2, 1, 2)


def test_group_null_permutes_whole_two_label_counterfactual_vectors():
    labels = np.array(["A", "B", "C", "D", "E", "F"])
    groups = np.array(["p1", "p1", "p2", "p2", "p3", "p3"])
    split = np.arange(6)

    permuted = evaluate_40_element_probe._permute_group_labels_within_splits(
        labels,
        groups,
        (split, np.array([], dtype=int), np.array([], dtype=int)),
        np.random.default_rng(4),
    )

    original_vectors = {("A", "B"), ("C", "D"), ("E", "F")}
    observed_vectors = {
        tuple(permuted[index : index + 2].tolist()) for index in (0, 2, 4)
    }
    assert observed_vectors == original_vectors


def test_historical_metadata_is_permanently_model_revision_unavailable():
    binding, failures = evaluate_40_element_probe.build_registered_artifact_binding(
        dataset_sha256=evaluate_40_element_probe.REGISTERED_STAGE9_DATASET_SHA256,
        metadata_sha256=evaluate_40_element_probe.REGISTERED_STAGE9_METADATA_SHA256,
        scenario_sha256=evaluate_40_element_probe.REGISTERED_STAGE9_SCENARIO_SHA256,
        metadata={
            "model_id": evaluate_40_element_probe.REGISTERED_STAGE9_MODEL_ID,
            "model_revision": "a" * 40,
        },
    )

    assert binding["identity_status"] == "MODEL_REVISION_UNAVAILABLE"
    assert binding["packet_eligibility"] == "NOT_PACKET_ELIGIBLE"
    assert "MODEL_REVISION_UNAVAILABLE" in failures


def test_npz_parse_and_digest_share_one_verified_file_handle(tmp_path):
    dataset = tmp_path / "dataset.npz"
    np.savez(
        dataset,
        features=np.zeros((2, 1, 2), dtype=np.float32),
        layers=np.array([0]),
        labels_domain=np.array(["P", "C"]),
        labels_operator=np.array(["^0", "^1"]),
        prompts=np.array(["a", "b"]),
        scenario_ids=np.array(["s1", "s2"]),
    )
    snapshot = {}

    loaded = evaluate_40_element_probe.load_npz_without_pickle(
        dataset,
        snapshot_out=snapshot,
    )

    assert loaded["features"].shape == (2, 1, 2)
    assert snapshot["content_sha256"] == hashlib.sha256(dataset.read_bytes()).hexdigest()
    assert "same open file handle" in snapshot["snapshot_semantics"]


def test_npz_loader_rejects_bytes_mutated_between_hash_and_parse(tmp_path):
    dataset = tmp_path / "dataset.npz"
    replacement = tmp_path / "replacement.npz"
    for path, fill in ((dataset, 0.0), (replacement, 1.0)):
        np.savez(
            path,
            features=np.full((2, 1, 2), fill, dtype=np.float32),
            layers=np.array([0]),
            labels_domain=np.array(["P", "C"]),
            labels_operator=np.array(["^0", "^1"]),
            prompts=np.array(["a", "b"]),
            scenario_ids=np.array(["s1", "s2"]),
        )

    with pytest.raises(ValueError, match="changed during|path was replaced|Bad CRC"):
        evaluate_40_element_probe.load_npz_without_pickle(
            dataset,
            after_first_hash_hook=lambda: dataset.write_bytes(replacement.read_bytes()),
        )


def test_json_manifest_parse_and_hash_use_same_byte_snapshot(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"scenarios":[]}', encoding="utf-8")
    original = manifest.read_bytes()

    payload, snapshot = evaluate_40_element_probe.load_json_snapshot(
        manifest,
        after_read_hook=lambda: manifest.write_text(
            '{"scenarios":[{"id":"swapped"}]}', encoding="utf-8"
        ),
    )

    assert payload == {"scenarios": []}
    assert snapshot["content_sha256"] == hashlib.sha256(original).hexdigest()
    assert snapshot["content_sha256"] != hashlib.sha256(manifest.read_bytes()).hexdigest()
