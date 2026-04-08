"""Tests for scenarios.generator — inversion engine, augmentation, teacher."""

from __future__ import annotations

import json

from scenarios.generator.inversion_engine import (
    Scenario,
    InvertedScenario,
    invert_scenario,
    invert_all_axes,
    invert_n_axis,
    invert_w_axis,
    invert_f_axis,
    AXIS_FUNCTIONS,
    OPERATOR_INVOLUTIONS,
    DRIVE_INVERSIONS,
    DOMAIN_SWAPS,
)
from scenarios.generator.augmentation import (
    load_base_scenarios,
    augment_scenarios,
    _assign_targets,
)
from scenarios.generator.teacher import (
    build_teacher_prompt,
    validate_scenario,
    parse_teacher_response,
)


def _base_scenario() -> Scenario:
    return Scenario(
        id="test_001",
        prompt="Explain the abstract principles behind this ethical decision.",
        target_operators=[2, 5],
        target_domain="P",
        target_drives=[1, 3],
        category="test",
    )


# --- Inversion Engine ---

class TestInversionEngine:
    def test_invert_all_axes_produces_7(self):
        s = _base_scenario()
        results = invert_all_axes(s)
        assert len(results) == 7
        axes = {r.inversion_axis for r in results}
        assert axes == {"N", "W", "F", "E", "S", "A", "P"}

    def test_all_results_are_inverted_scenarios(self):
        s = _base_scenario()
        for r in invert_all_axes(s):
            assert isinstance(r, InvertedScenario)
            assert r.source_scenario_id == "test_001"
            assert r.expected_detection is True
            assert len(r.id) == 12

    def test_n_axis_swaps_involution_pairs(self):
        s = _base_scenario()
        result = invert_n_axis(s)
        # CO-2→CO-3, CO-5→CO-6
        assert 3 in result.target_operators
        assert 6 in result.target_operators
        assert result.inversion_axis == "N"

    def test_w_axis_swaps_domain(self):
        s = _base_scenario()
        result = invert_w_axis(s)
        # P→O
        assert result.target_domain == "O"
        assert result.inversion_axis == "W"

    def test_f_axis_swaps_drives(self):
        s = _base_scenario()
        result = invert_f_axis(s)
        # F2 (idx 1) → F6 (idx 5), F4 (idx 3) stays
        assert 5 in result.target_drives  # F6
        assert 3 in result.target_drives  # F4 self-dual
        assert result.inversion_axis == "F"

    def test_a_axis_adds_skip_instruction(self):
        s = _base_scenario()
        result = invert_scenario(s, "A")
        assert "skip" in result.prompt.lower() or "Skip" in result.prompt

    def test_p_axis_is_compound(self):
        s = _base_scenario()
        result = invert_scenario(s, "P")
        assert result.inversion_axis == "P"
        assert "Compound" in result.inversion_notes

    def test_n_axis_prompt_rewriting(self):
        s = Scenario(
            id="rw_001",
            prompt="Compare and contrast abstract theories in this broad field.",
            target_operators=[2],
            target_domain="C",
            target_drives=[1],
        )
        result = invert_n_axis(s)
        # "abstract" → "concrete", "broad" → "narrow"
        assert "concrete" in result.prompt.lower() or "specific" in result.prompt.lower()

    def test_deterministic_ids(self):
        s = _base_scenario()
        r1 = invert_all_axes(s)
        r2 = invert_all_axes(s)
        for a, b in zip(r1, r2):
            assert a.id == b.id

    def test_involution_pairs_are_symmetric(self):
        for k, v in OPERATOR_INVOLUTIONS.items():
            assert OPERATOR_INVOLUTIONS[v] == k

    def test_domain_swaps_are_symmetric(self):
        for k, v in DOMAIN_SWAPS.items():
            assert DOMAIN_SWAPS[v] == k


# --- Augmentation ---

class TestAugmentation:
    def test_load_base_scenarios(self):
        scenarios = load_base_scenarios()
        assert len(scenarios) > 0
        assert all(isinstance(s, Scenario) for s in scenarios)
        assert all(s.prompt for s in scenarios)

    def test_assign_targets_deterministic(self):
        ops1, dom1, drv1 = _assign_targets("Explain the ethical principles", 42)
        ops2, dom2, drv2 = _assign_targets("Explain the ethical principles", 42)
        assert ops1 == ops2
        assert dom1 == dom2
        assert drv1 == drv2

    def test_augment_produces_8x(self):
        base = [_base_scenario()]
        results = augment_scenarios(base)
        assert len(results) == 8  # 1 original + 7 inversions
        originals = [r for r in results if r["is_original"]]
        inverted = [r for r in results if not r["is_original"]]
        assert len(originals) == 1
        assert len(inverted) == 7

    def test_augment_max_count(self):
        base = load_base_scenarios()[:5]
        results = augment_scenarios(base, max_total=10)
        assert len(results) <= 10

    def test_augmented_has_required_fields(self):
        base = [_base_scenario()]
        results = augment_scenarios(base)
        for r in results:
            assert "id" in r
            assert "prompt" in r
            assert "target_operators" in r
            assert "target_domain" in r
            assert "is_original" in r


# --- Teacher ---

class TestTeacher:
    def test_build_prompt_includes_operators(self):
        prompt = build_teacher_prompt([2, 5], "P", [1, 3], count=5)
        assert "CO-2" in prompt
        assert "CO-5" in prompt
        assert "Principled" in prompt
        assert "5" in prompt  # count

    def test_validate_scenario_valid(self):
        s = {"prompt": "Explain the trolley problem in detail"}
        assert validate_scenario(s, [2], "P", [1]) is True

    def test_validate_scenario_short_prompt(self):
        s = {"prompt": "Hi"}
        assert validate_scenario(s, [2], "P", [1]) is False

    def test_validate_scenario_bad_operator(self):
        s = {"prompt": "A valid prompt here"}
        assert validate_scenario(s, [15], "P", [1]) is False

    def test_validate_scenario_bad_domain(self):
        s = {"prompt": "A valid prompt here"}
        assert validate_scenario(s, [2], "X", [1]) is False

    def test_parse_valid_response(self):
        response = json.dumps([
            {"prompt": "Explain the ethical implications of autonomous vehicles.", "rationale": "Tests CO-2"},
            {"prompt": "Design a framework for evaluating AI decision-making.", "rationale": "Tests CO-4"},
        ])
        results = parse_teacher_response(response, [2, 4], "P", [1])
        assert len(results) == 2
        assert results[0].target_operators == [2, 4]

    def test_parse_markdown_wrapped(self):
        response = '```json\n[{"prompt": "Test scenario here for validation.", "rationale": "r"}]\n```'
        results = parse_teacher_response(response, [5], "C", [3])
        assert len(results) == 1

    def test_parse_invalid_json(self):
        results = parse_teacher_response("not json at all", [2], "P", [1])
        assert len(results) == 0
