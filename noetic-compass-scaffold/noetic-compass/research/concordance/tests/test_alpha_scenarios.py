"""Regression tests for the Atlas alpha scenario set."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from research.concordance.harness import load_scenarios


FIXTURE = Path("scenarios/atlas_alpha_set_v0.json")


def test_alpha_scenario_set_loads_25_curated_items():
    scenarios = load_scenarios(FIXTURE)

    assert len(scenarios) == 25
    assert [s.id for s in scenarios] == [f"alpha_{i:02d}" for i in range(1, 26)]
    assert all(s.prompt for s in scenarios)
    assert all("expected_cas_axes" in s.metadata for s in scenarios)
    assert all("rationale" in s.metadata for s in scenarios)
    assert all("expected_difficulty" in s.metadata for s in scenarios)
    assert all("honesty_flag" in s.metadata for s in scenarios)


def test_alpha_scenario_set_covers_all_drives_and_registers():
    scenarios = load_scenarios(FIXTURE)
    drives = {
        s.metadata["expected_cas_axes"]["drive"]
        for s in scenarios
    }
    registers = {
        s.metadata["expected_cas_axes"]["register"]
        for s in scenarios
    }

    assert drives == {"F1", "F2", "F3", "F4", "F5", "F6", "F7"}
    assert registers == {"T", "A", "f", "E"}


def test_alpha_scenario_set_keeps_expected_weak_cases_explicit():
    scenarios = load_scenarios(FIXTURE)

    weak = [s for s in scenarios if s.metadata.get("honesty_flag")]
    assert len(weak) == 4
    assert {s.id for s in weak} == {"alpha_11", "alpha_23", "alpha_24", "alpha_25"}


def test_alpha_17_is_demo_safe_reframed_social_engineering_detection():
    scenarios = {s.id: s for s in load_scenarios(FIXTURE)}
    alpha_17 = scenarios["alpha_17"]

    assert alpha_17.metadata["demo_safe"] is True
    assert "identify the social-engineering technique" in alpha_17.prompt
    assert "phishing email template" not in alpha_17.prompt.lower()
    assert alpha_17.metadata["expected_cas_axes"]["drive"] == "F4"
    assert alpha_17.metadata["expected_cas_axes"]["noetic"] == "^2_vs_^3"


def test_alpha_scenario_set_has_balanced_domain_presence():
    scenarios = load_scenarios(FIXTURE)
    domain_counts = Counter(
        s.metadata["expected_cas_axes"]["domain"]
        for s in scenarios
    )

    for domain in ("P", "C", "E", "O"):
        assert any(domain in key for key in domain_counts), domain_counts
