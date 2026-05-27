from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.build_tks40_scenarios import build_payload, validate_payload
from scripts.probe_dataset_common import load_labeled_scenarios


def test_build_payload_is_balanced_tks40():
    payload = build_payload(examples_per_class=3)
    scenarios = payload["scenarios"]

    counts = Counter(item["expected_cas_axes"]["element"] for item in scenarios)
    assert len(scenarios) == 120
    assert len(counts) == 40
    assert set(counts.values()) == {3}
    assert counts["^1|P"] == 3
    assert counts["^0|O"] == 3
    assert payload["source_profile"] == "source_derived_from_original_stage9_tks40_glosses"


def test_build_payload_preserves_legacy_tks_codes_in_metadata():
    payload = build_payload(examples_per_class=3)
    by_code = {item["metadata"]["legacy_element_code"]: item for item in payload["scenarios"]}

    assert by_code["A1"]["expected_cas_axes"]["element"] == "^1|P"
    assert by_code["A10"]["expected_cas_axes"]["element"] == "^0|P"
    assert by_code["D10"]["expected_cas_axes"]["element"] == "^0|O"
    assert by_code["B8"]["metadata"]["legacy_domain_name"] == "mental"


def test_build_payload_does_not_put_class_codes_in_prompts():
    payload = build_payload(examples_per_class=3)

    for item in payload["scenarios"]:
        axes = item["expected_cas_axes"]
        assert item["metadata"]["legacy_element_code"] not in item["prompt"]
        assert axes["element"] not in item["prompt"]
        assert axes["operator"] not in item["prompt"]


def test_generated_payload_loads_as_element_axis(tmp_path: Path):
    path = tmp_path / "tks40.json"
    payload = build_payload(examples_per_class=3)
    validate_payload(payload, expected_per_class=3)
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    scenarios = load_labeled_scenarios(path)
    labels = Counter(scenario.labels["element"] for scenario in scenarios)

    assert len(scenarios) == 120
    assert len(labels) == 40
    assert set(labels.values()) == {3}
    assert scenarios[0].labels["domain"] == "P"
    assert scenarios[0].labels["operator"] == "^1"
    assert scenarios[0].labels["element"] == "^1|P"


def test_validate_payload_rejects_unbalanced_counts():
    payload = build_payload(examples_per_class=3)
    payload["scenarios"].pop()

    with pytest.raises(ValueError, match="unbalanced|mismatch"):
        validate_payload(payload, expected_per_class=3)
