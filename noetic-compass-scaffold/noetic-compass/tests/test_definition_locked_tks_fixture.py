from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
SCRIPT_PATH = APP_ROOT / "live-trace-worker" / "scripts" / "build_definition_locked_tks_fixture.py"
LOADER_PATH = APP_ROOT / "live-trace-worker" / "scripts" / "probe_dataset_common.py"
SOURCE_PATH = REPO_ROOT / "docs" / "reference" / "tks_owner_locked_definitions_20260603.json"
FIXTURE_DIR = APP_ROOT / "docs" / "working" / "definition_locked_tks_mtc_20260603"
FIXTURE_PATH = FIXTURE_DIR / "definition_locked_tks40_f28_fixture_20260603.json"
DEFINITIONS_PATH = FIXTURE_DIR / "canonical_tks_cas_axis_definitions_20260603.json"
MANIFEST_PATH = FIXTURE_DIR / "definition_locked_tks40_f28_manifest_20260603.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_definition_locked_tks_fixture", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_probe_dataset_common():
    spec = importlib.util.spec_from_file_location("probe_dataset_common", LOADER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["probe_dataset_common"] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_owner_locked_source_contains_exact_tks_definitions():
    source = _load_json(SOURCE_PATH)

    elements = {item["code"]: item for item in source["tks_40_elements"]}
    foundations = {item["code"]: item for item in source["tks_28_foundations"]}

    assert len(elements) == 40
    assert len(foundations) == 28
    assert list(elements) == [f"{letter}{number}" for letter in "ABCD" for number in range(1, 11)]
    assert list(foundations) == [f"{number}{letter}" for letter in "abcd" for number in range(1, 8)]

    assert "Divine Mind commonly known as God" in elements["A1"]["definition"]
    assert "aether energy, psychic energy" in elements["A4"]["definition"]
    assert "right brain thinking" in elements["B5"]["definition"]
    assert "Emotional Vibration" in elements["C4"]["title"]
    assert "brain organ" in elements["D1"]["definition"]
    assert "dead matter" in elements["D10"]["definition"]

    assert foundations["1a"]["title"] == "Spiritual desire to be and be with God"
    assert "merge with the divine" in foundations["1a"]["definition"]
    assert "mental fuel and food for thought" in foundations["6b"]["definition"]
    assert "To get another to feel how one feels" in foundations["7c"]["definition"]
    assert "Dominance through bodily strength and presence" in foundations["5d"]["definition"]
    assert "optimal offspring" in foundations["7d"]["definition"]


def test_generator_is_source_driven_not_translation_key_driven():
    builder = _load_builder()
    source = builder.load_definition_source(SOURCE_PATH)
    mutated = copy.deepcopy(source)
    mutated["tks_28_foundations"][0]["definition"] = "SENTINEL OWNER LOCKED 1A DEFINITION"
    mutated["tks_40_elements"][0]["definition"] = "SENTINEL OWNER LOCKED A1 DEFINITION"

    rows = builder.build_rows(mutated)

    prompts = "\n".join(row["prompt"] for row in rows)
    assert "SENTINEL OWNER LOCKED 1A DEFINITION" in prompts
    assert "SENTINEL OWNER LOCKED A1 DEFINITION" in prompts
    assert "Drive x Register" not in prompts
    assert "current CAS v7.5 translation key" not in prompts


def test_committed_fixture_is_in_sync_with_locked_source():
    builder = _load_builder()
    source = builder.load_definition_source(SOURCE_PATH)
    expected_rows = builder.build_rows(source)
    expected_definitions = builder.build_definitions(source)
    expected_manifest = builder.build_manifest(expected_rows)

    fixture = _load_json(FIXTURE_PATH)
    definitions = _load_json(DEFINITIONS_PATH)
    manifest = _load_json(MANIFEST_PATH)

    assert definitions == expected_definitions
    assert fixture["schema_version"] == builder.SCHEMA_VERSION
    assert fixture["scenarios"] == expected_rows
    assert manifest == expected_manifest


def test_fixture_labels_are_tks_codes_not_fallback_taxonomy_codes():
    fixture = _load_json(FIXTURE_PATH)
    rows = fixture["scenarios"]
    element_labels = {
        row["expected_cas_axes"]["element"]
        for row in rows
        if row["axis"] == "40e"
    }
    foundation_labels = {
        row["expected_cas_axes"]["foundation"]
        for row in rows
        if row["axis"] == "f28"
    }

    assert element_labels == {f"{letter}{number}" for letter in "ABCD" for number in range(1, 11)}
    assert foundation_labels == {f"{number}{letter}" for letter in "abcd" for number in range(1, 8)}
    assert all("|" not in label for label in element_labels)
    assert all("|" not in label for label in foundation_labels)
    assert len(rows) == 816


def test_live_loader_preserves_tks_element_and_foundation_codes():
    loader = _load_probe_dataset_common()
    rows = loader.load_labeled_scenarios(FIXTURE_PATH)

    element_labels = {
        row.labels.get("element")
        for row in rows
        if row.labels.get("element") in {f"{letter}{number}" for letter in "ABCD" for number in range(1, 11)}
    }
    foundation_labels = {
        row.labels.get("foundation")
        for row in rows
        if row.labels.get("foundation") in {f"{number}{letter}" for letter in "abcd" for number in range(1, 8)}
    }

    assert len(rows) == 816
    assert element_labels == {f"{letter}{number}" for letter in "ABCD" for number in range(1, 11)}
    assert foundation_labels == {f"{number}{letter}" for letter in "abcd" for number in range(1, 8)}
