"""Tests for adversarial resilience scenario catalog."""

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).parent.parent / "scenarios" / "catalog" / "adversarial_resilience.json"

EXPECTED_GROUPS = {
    "cognitive_bias_resilience",
    "discourse_boundary_resilience",
    "prerequisite_integrity_resilience",
    "domain_coherence_resilience",
    "inversion_detection_resilience",
}


def _load():
    data = json.loads(CATALOG_PATH.read_text())
    return data


class TestAdversarialCatalog:
    def test_file_exists(self):
        assert CATALOG_PATH.exists()

    def test_has_30_scenarios(self):
        data = _load()
        assert len(data["scenarios"]) == 30

    def test_5_groups_6_each(self):
        data = _load()
        groups = {}
        for s in data["scenarios"]:
            g = s["group"]
            groups[g] = groups.get(g, 0) + 1
        assert set(groups.keys()) == EXPECTED_GROUPS
        for group, count in groups.items():
            assert count == 6, f"{group} has {count} scenarios, expected 6"

    def test_all_scenarios_have_required_fields(self):
        data = _load()
        for s in data["scenarios"]:
            assert "id" in s, f"Missing id in {s.get('group')}"
            assert "group" in s
            assert "prompt" in s
            assert len(s["prompt"]) > 20, f"Prompt too short: {s['id']}"

    def test_unique_ids(self):
        data = _load()
        ids = [s["id"] for s in data["scenarios"]]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_cognitive_bias_scenarios_have_resilience_target(self):
        data = _load()
        for s in data["scenarios"]:
            if s["group"] == "cognitive_bias_resilience":
                assert "resilience_target" in s, f"{s['id']} missing resilience_target"
                assert "failure_indicator" in s
                assert "success_indicator" in s

    def test_discourse_scenarios_have_threshold_fields(self):
        data = _load()
        for s in data["scenarios"]:
            if s["group"] == "discourse_boundary_resilience":
                assert "threshold_test" in s, f"{s['id']} missing threshold_test"
                assert "drift_measurement" in s
                assert "baseline_comparison" in s

    def test_prerequisite_scenarios_have_resilience_target(self):
        data = _load()
        for s in data["scenarios"]:
            if s["group"] == "prerequisite_integrity_resilience":
                assert "resilience_target" in s, f"{s['id']} missing resilience_target"

    def test_inversion_scenarios_have_axis(self):
        data = _load()
        for s in data["scenarios"]:
            if s["group"] == "inversion_detection_resilience":
                assert "inversion_axis" in s, f"{s['id']} missing inversion_axis"
                assert "hidden_reversal" in s
                assert "detection_method" in s

    def test_no_offensive_framing(self):
        """Verify no scenario contains offensive capability instructions."""
        data = _load()
        offensive_terms = ["how to attack", "step-by-step attack", "exploit this vulnerability"]
        for s in data["scenarios"]:
            prompt_lower = s["prompt"].lower()
            for term in offensive_terms:
                assert term not in prompt_lower, f"Offensive framing in {s['id']}: '{term}'"
