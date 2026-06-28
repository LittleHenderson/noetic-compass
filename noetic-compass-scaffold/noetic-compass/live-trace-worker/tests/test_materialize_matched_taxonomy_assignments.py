from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "materialize_matched_taxonomy_assignments.py"
)
SPEC = importlib.util.spec_from_file_location("materialize_matched_taxonomy_assignments", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
materializer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = materializer
SPEC.loader.exec_module(materializer)

RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_matched_taxonomy_control.py"
)
RUNNER_SPEC = importlib.util.spec_from_file_location("run_matched_taxonomy_control_for_materializer", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "scenarios"
    / "matched_taxonomy_control_manifest_20260530.json"
)


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _write_nc40_explicit_scenarios(path: Path) -> list[dict]:
    manifest = _load_manifest()
    control = manifest["controls"]["nc40_topic_frame"]
    rows = []
    for split in ("train", "test"):
        for topic in control["topic_axis"]:
            for frame in control["frame_axis"]:
                index = len(rows)
                rows.append(
                    {
                        "sample_id": f"{split}_{index}",
                        "split": split,
                        "control_semantic": {
                            "topic_40": topic,
                            "frame_40": frame,
                        },
                        "prompt": "ignored because explicit control_semantic is present",
                    }
                )
    path.write_text(json.dumps({"records": rows}), encoding="utf-8")
    return rows


def test_materializes_nc40_dataset_order_labels_and_runner_can_load(tmp_path: Path):
    scenarios = tmp_path / "nc40_scenarios.json"
    output = tmp_path / "nc40_assignments.json"
    rows = _write_nc40_explicit_scenarios(scenarios)

    exit_code = materializer.main(
        [
            "--scenarios",
            str(scenarios),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(output),
            "--control-id",
            "NC40_TOPIC_FRAME_V1",
            "--axis",
            "40e",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["blocked"] is False
    assert len(payload["taxonomies"]) == 1

    taxonomy = payload["taxonomies"][0]
    assert taxonomy["id"] == "NC40_TOPIC_FRAME_V1"
    assert taxonomy["axis"] == "40e"
    assert len(taxonomy["labels"]) == len(rows)
    assert taxonomy["labels"][0] == "NC40_healthcare_classification"
    assert taxonomy["parent_labels"][0] == "healthcare"
    assert taxonomy["child_labels"][0] == "classification"
    assert set(taxonomy["class_counts_by_split"]["train"].values()) == {1}
    assert set(taxonomy["class_counts_by_split"]["test"].values()) == {1}
    assert taxonomy["assignment_sha256"]

    specs = runner.load_taxonomy_manifest(
        payload,
        axis="40e",
        n_samples=len(rows),
        sample_ids=np.array([row["sample_id"] for row in rows], dtype=object),
    )
    assert len(specs) == 1
    assert specs[0].taxonomy_id == "NC40_TOPIC_FRAME_V1"
    assert specs[0].labels.tolist() == taxonomy["labels"]
    assert specs[0].parent_labels.tolist() == taxonomy["parent_labels"]
    assert specs[0].child_labels.tolist() == taxonomy["child_labels"]


def test_materializes_sample_id_keyed_labels(tmp_path: Path):
    scenarios = tmp_path / "nc40_scenarios.json"
    output = tmp_path / "nc40_assignments_keyed.json"
    rows = _write_nc40_explicit_scenarios(scenarios)

    exit_code = materializer.main(
        [
            "--scenarios",
            str(scenarios),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(output),
            "--control-id",
            "nc40",
            "--axis",
            "40e",
            "--label-mode",
            "sample_id_map",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    taxonomy = payload["taxonomies"][0]
    assert isinstance(taxonomy["labels"], dict)
    assert taxonomy["labels"][rows[0]["sample_id"]] == "NC40_healthcare_classification"

    specs = runner.load_taxonomy_manifest(
        payload,
        axis="40e",
        n_samples=len(rows),
        sample_ids=np.array([row["sample_id"] for row in rows], dtype=object),
    )
    assert specs[0].labels[0] == "NC40_healthcare_classification"


def test_blocks_nc28_when_supported_candidates_cannot_satisfy_balanced_quotas(tmp_path: Path):
    manifest = _load_manifest()
    control = manifest["controls"]["nc28_topic_function_nested"]
    rows = []
    for split in ("train", "test"):
        for index in range(len(control["labels"])):
            rows.append(
                {
                    "sample_id": f"{split}_{index}",
                    "split": split,
                    "prompt": "The patient status describes current care records.",
                    "cas_expression": "NC28 labels must not be inferred from this prohibited field.",
                }
            )
    scenarios = tmp_path / "nc28_insufficient.json"
    output = tmp_path / "nc28_blocked.json"
    scenarios.write_text(json.dumps({"records": rows}), encoding="utf-8")

    exit_code = materializer.main(
        [
            "--scenarios",
            str(scenarios),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(output),
            "--control-id",
            "NC28_TOPIC_FUNCTION_NESTED_V1",
            "--axis",
            "f28",
        ]
    )

    assert exit_code == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked"
    assert payload["taxonomies"] == []
    block = payload["blocking_reasons"][0]
    assert block["blocked_status"] == "blocked_insufficient_nc28_candidate_cover"
    assert block["control_id"] == "NC28_TOPIC_FUNCTION_NESTED_V1"
    assert block["details"]["requested_rows"] == len(control["labels"])
    assert block["details"]["assigned_rows"] < len(control["labels"])
    assert "NC28_medical_care_explain_cause" in block["details"]["unsatisfied_target_counts"]
