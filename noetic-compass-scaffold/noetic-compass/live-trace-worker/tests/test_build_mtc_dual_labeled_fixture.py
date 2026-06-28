from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_mtc_dual_labeled_fixture.py"
)
SPEC = importlib.util.spec_from_file_location("build_mtc_dual_labeled_fixture", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
fixture_builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_builder
SPEC.loader.exec_module(fixture_builder)

MATERIALIZER_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "materialize_matched_taxonomy_assignments.py"
)
MATERIALIZER_SPEC = importlib.util.spec_from_file_location(
    "materialize_matched_taxonomy_assignments_for_fixture", MATERIALIZER_PATH
)
assert MATERIALIZER_SPEC is not None and MATERIALIZER_SPEC.loader is not None
materializer = importlib.util.module_from_spec(MATERIALIZER_SPEC)
sys.modules[MATERIALIZER_SPEC.name] = materializer
MATERIALIZER_SPEC.loader.exec_module(materializer)

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "scenarios"
    / "matched_taxonomy_control_manifest_20260530.json"
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_builds_balanced_40e_fixture_and_materializer_accepts_it(tmp_path: Path):
    manifest = _manifest()
    spec = fixture_builder._axis_spec(
        axis="40e",
        manifest=manifest,
        rows_per_class=2,
        train_per_class=1,
    )
    payload = fixture_builder.build_fixture(spec)
    rows = payload["records"]

    cas_counts = Counter(row["labels_40e"] for row in rows)
    control_counts = Counter(
        f"NC40_{row['control_semantic']['topic_40']}_{row['control_semantic']['frame_40']}"
        for row in rows
    )

    assert payload["row_count"] == 80
    assert set(cas_counts.values()) == {2}
    assert set(control_counts.values()) == {2}
    assert rows[0]["expected_cas_axes"]["element"] == rows[0]["labels_40e"]

    scenario_path = tmp_path / "mtc40.json"
    output_path = tmp_path / "mtc40_assignments.json"
    scenario_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = materializer.main(
        [
            "--scenarios",
            str(scenario_path),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(output_path),
            "--axis",
            "40e",
        ]
    )

    assignment = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert assignment["status"] == "completed"
    assert assignment["blocked"] is False


def test_builds_balanced_f28_fixture_and_materializer_accepts_it(tmp_path: Path):
    manifest = _manifest()
    spec = fixture_builder._axis_spec(
        axis="f28",
        manifest=manifest,
        rows_per_class=2,
        train_per_class=1,
    )
    payload = fixture_builder.build_fixture(spec)
    rows = payload["records"]

    cas_counts = Counter(row["labels_f28"] for row in rows)
    control_counts = Counter(
        f"NC28_{row['control_semantic']['topic_7']}_{row['control_semantic']['function_4']}"
        for row in rows
    )

    assert payload["row_count"] == 56
    assert set(cas_counts.values()) == {2}
    assert set(control_counts.values()) == {2}
    assert rows[0]["expected_cas_axes"]["foundation"] == rows[0]["labels_f28"]

    scenario_path = tmp_path / "mtcf28.json"
    output_path = tmp_path / "mtcf28_assignments.json"
    scenario_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = materializer.main(
        [
            "--scenarios",
            str(scenario_path),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(output_path),
            "--axis",
            "f28",
        ]
    )

    assignment = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert assignment["status"] == "completed"
    assert assignment["blocked"] is False
