from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.build_foundation28_scenarios import (
    build_payload,
    validate_payload,
)
from scripts.probe_dataset_common import load_labeled_scenarios


def test_build_payload_is_balanced_foundation28():
    payload = build_payload(examples_per_class=3)
    scenarios = payload["scenarios"]

    counts = Counter(item["expected_cas_axes"]["foundation"] for item in scenarios)
    assert len(scenarios) == 84
    assert len(counts) == 28
    assert set(counts.values()) == {3}
    assert counts["F1|T"] == 3
    assert counts["F7|E"] == 3
    assert payload["source_profile"] == "source_derived_from_original_stage7_tks28_glosses"


def test_build_payload_preserves_legacy_tks_foundation_codes():
    payload = build_payload(examples_per_class=3)
    by_legacy = {item["metadata"]["legacy_foundation_code"]: item for item in payload["scenarios"]}

    assert by_legacy["1a"]["expected_cas_axes"]["foundation"] == "F1|T"
    assert by_legacy["1b"]["expected_cas_axes"]["foundation"] == "F1|A"
    assert by_legacy["1c"]["expected_cas_axes"]["foundation"] == "F1|f"
    assert by_legacy["1d"]["expected_cas_axes"]["foundation"] == "F1|E"
    assert by_legacy["7d"]["expected_cas_axes"]["foundation"] == "F7|E"


def test_build_payload_does_not_put_class_codes_in_prompts():
    payload = build_payload(examples_per_class=3)

    for item in payload["scenarios"]:
        axes = item["expected_cas_axes"]
        assert axes["foundation"] not in item["prompt"]
        assert axes["drive"] not in item["prompt"]


def test_generated_payload_loads_as_foundation_axis(tmp_path: Path):
    path = tmp_path / "foundation28.json"
    payload = build_payload(examples_per_class=3)
    validate_payload(payload, expected_per_class=3)
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    scenarios = load_labeled_scenarios(path)
    labels = Counter(scenario.labels["foundation"] for scenario in scenarios)

    assert len(scenarios) == 84
    assert len(labels) == 28
    assert set(labels.values()) == {3}
    assert scenarios[0].labels["drive"] == "F1"
    assert scenarios[0].labels["register"] == "T"
    assert scenarios[0].labels["foundation"] == "F1|T"


def test_validate_payload_rejects_unbalanced_counts():
    payload = build_payload(examples_per_class=3)
    payload["scenarios"].pop()

    with pytest.raises(ValueError, match="unbalanced|mismatch"):
        validate_payload(payload, expected_per_class=3)
