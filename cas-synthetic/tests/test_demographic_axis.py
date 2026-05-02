"""Tests for demographic_axis.py — SDG demographic + tonal variety axis.

Verifies:
1.  The CAS expression is byte-for-byte identical across all 36 renderings.
2.  Soft targets are unchanged.
3.  Output is fully deterministic under seed.
4.  Invalid axis values raise ValueError.
5.  Provenance is enriched with demographic metadata.
6.  Tags contain per-axis labels.
7.  All 36 grid cells execute without error.
8.  The rendered user_prompt is actually different from the original.
"""

from __future__ import annotations

import copy

import pytest

from cas_synthetic.generator.demographic_axis import (
    AGE_BANDS,
    AXIS_GRID,
    CULTURAL_REGISTERS,
    TONALS,
    DemographicAxisSpec,
    apply_demographic_axis,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_record(**overrides: object) -> dict:
    """Minimal valid Level 3 record for testing."""
    base: dict = {
        "id": "l3conv-abc123def456",
        "source_level2_id": "level2-000042",
        "bucket": "v74_baseline",
        "cas_expression": "^2^P_{F3}|A",
        "user_prompt": "Can you map this situation into CAS notation and explain the main axes?",
        "natural_language_mapping": "Maps the prompt to a principled cognitive state.",
        "assistant_response": "The expression is ^2^P_{F3}|A, marking affinity in the principled domain.",
        "follow_up_question": "What evidence would change your confidence?",
        "soft_operator_targets": [0.1] * 10,
        "soft_domain_targets": [0.6, 0.2, 0.1, 0.1],
        "tags": ["level3", "conversational", "v74_baseline"],
        "provenance": {
            "level3_spec_version": "0.1.0",
            "generation_method": "deterministic_template",
            "seed": 42,
        },
    }
    base.update(overrides)
    return base


def _default_spec(**kwargs: object) -> DemographicAxisSpec:
    return DemographicAxisSpec(
        age_band=kwargs.get("age_band", "adult"),
        cultural_register=kwargs.get("cultural_register", "western_academic"),
        tonal=kwargs.get("tonal", "formal"),
        seed=kwargs.get("seed", 42),
    )


# ---------------------------------------------------------------------------
# Core invariant: CAS expression unchanged
# ---------------------------------------------------------------------------


def test_cas_expression_unchanged_across_all_36_cells():
    """The central invariant: cas_expression must be identical for every cell."""
    record = _make_record()
    expression = record["cas_expression"]
    for age_band, cultural_register, tonal in AXIS_GRID:
        spec = DemographicAxisSpec(
            age_band=age_band,
            cultural_register=cultural_register,
            tonal=tonal,
            seed=42,
        )
        out = apply_demographic_axis(record, spec)
        assert out["cas_expression"] == expression, (
            f"cas_expression changed for cell ({age_band}, {cultural_register}, {tonal})"
        )


def test_soft_operator_targets_unchanged():
    record = _make_record()
    spec = _default_spec()
    out = apply_demographic_axis(record, spec)
    assert out["soft_operator_targets"] == record["soft_operator_targets"]


def test_soft_domain_targets_unchanged():
    record = _make_record()
    spec = _default_spec()
    out = apply_demographic_axis(record, spec)
    assert out["soft_domain_targets"] == record["soft_domain_targets"]


def test_input_record_not_mutated():
    """apply_demographic_axis must not mutate the caller's dict."""
    record = _make_record()
    original_tags = list(record["tags"])
    original_prompt = record["user_prompt"]
    _ = apply_demographic_axis(record, _default_spec())
    assert record["tags"] == original_tags
    assert record["user_prompt"] == original_prompt


# ---------------------------------------------------------------------------
# Determinism under seed
# ---------------------------------------------------------------------------


def test_deterministic_same_seed():
    record = _make_record()
    spec = _default_spec(seed=7)
    out1 = apply_demographic_axis(record, spec)
    out2 = apply_demographic_axis(record, spec)
    assert out1 == out2


def test_deterministic_all_36_cells():
    """Every cell is stable: calling twice with same spec yields identical output."""
    record = _make_record()
    for age_band, cultural_register, tonal in AXIS_GRID:
        spec = DemographicAxisSpec(
            age_band=age_band, cultural_register=cultural_register, tonal=tonal, seed=99
        )
        assert apply_demographic_axis(record, spec) == apply_demographic_axis(record, spec)


def test_different_seeds_produce_different_prompts():
    """Different seeds should typically (not guaranteed always) differ for a given cell."""
    record = _make_record()
    prompts = set()
    for s in range(10):
        spec = DemographicAxisSpec(
            age_band="youth", cultural_register="western_vernacular", tonal="casual", seed=s
        )
        prompts.add(apply_demographic_axis(record, spec)["user_prompt"])
    # At least 2 distinct outputs across 10 seeds (phrase pools have 3 options each)
    assert len(prompts) >= 2


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_invalid_age_band_raises():
    with pytest.raises(ValueError, match="age_band"):
        DemographicAxisSpec(
            age_band="teenager", cultural_register="western_academic", tonal="formal"
        )


def test_invalid_cultural_register_raises():
    with pytest.raises(ValueError, match="cultural_register"):
        DemographicAxisSpec(
            age_band="adult", cultural_register="martian", tonal="formal"
        )


def test_invalid_tonal_raises():
    with pytest.raises(ValueError, match="tonal"):
        DemographicAxisSpec(
            age_band="adult", cultural_register="western_academic", tonal="sarcastic"
        )


# ---------------------------------------------------------------------------
# Provenance enrichment
# ---------------------------------------------------------------------------


def test_provenance_has_demographic_fields():
    record = _make_record()
    spec = DemographicAxisSpec(
        age_band="older", cultural_register="non_western", tonal="technical", seed=5
    )
    out = apply_demographic_axis(record, spec)
    prov = out["provenance"]
    assert prov["demographic_age_band"] == "older"
    assert prov["demographic_cultural_register"] == "non_western"
    assert prov["demographic_tonal"] == "technical"
    assert prov["demographic_seed"] == 5
    assert prov["demographic_cell_key"] == "older__non_western__technical"


def test_provenance_original_fields_preserved():
    record = _make_record()
    spec = _default_spec()
    out = apply_demographic_axis(record, spec)
    prov = out["provenance"]
    assert prov["level3_spec_version"] == "0.1.0"
    assert prov["generation_method"] == "deterministic_template"


# ---------------------------------------------------------------------------
# Tags enrichment
# ---------------------------------------------------------------------------


def test_tags_have_demographic_labels():
    record = _make_record()
    spec = DemographicAxisSpec(
        age_band="youth", cultural_register="western_vernacular", tonal="casual", seed=1
    )
    out = apply_demographic_axis(record, spec)
    assert "demo_age_youth" in out["tags"]
    assert "demo_culture_western_vernacular" in out["tags"]
    assert "tonal_casual" in out["tags"]
    assert "demographic_variant" in out["tags"]


def test_tags_original_labels_preserved():
    record = _make_record()
    spec = _default_spec()
    out = apply_demographic_axis(record, spec)
    for original_tag in record["tags"]:
        assert original_tag in out["tags"]


def test_tags_no_duplicates():
    record = _make_record()
    spec = _default_spec()
    out = apply_demographic_axis(record, spec)
    assert len(out["tags"]) == len(set(out["tags"]))


# ---------------------------------------------------------------------------
# User prompt modification
# ---------------------------------------------------------------------------


def test_user_prompt_differs_from_source():
    """The rendered prompt must differ from the neutral original."""
    record = _make_record()
    original_prompt = record["user_prompt"]
    any_different = False
    for age_band, cultural_register, tonal in AXIS_GRID:
        spec = DemographicAxisSpec(
            age_band=age_band, cultural_register=cultural_register, tonal=tonal, seed=42
        )
        out = apply_demographic_axis(record, spec)
        if out["user_prompt"] != original_prompt:
            any_different = True
            break
    assert any_different, "No cell produced a different user_prompt from the original"


def test_user_prompt_contains_original_content():
    """The original prompt text should appear inside the rewritten version."""
    record = _make_record()
    original_prompt = record["user_prompt"]
    spec = _default_spec()
    out = apply_demographic_axis(record, spec)
    assert original_prompt in out["user_prompt"]


# ---------------------------------------------------------------------------
# Axis vocabulary constants
# ---------------------------------------------------------------------------


def test_axis_grid_has_36_cells():
    assert len(AXIS_GRID) == 36


def test_axis_grid_cells_are_unique():
    assert len(set(AXIS_GRID)) == 36


def test_all_age_bands_present_in_grid():
    grid_age_bands = {t[0] for t in AXIS_GRID}
    assert grid_age_bands == set(AGE_BANDS)


def test_all_cultural_registers_present_in_grid():
    grid_cultural = {t[1] for t in AXIS_GRID}
    assert grid_cultural == set(CULTURAL_REGISTERS)


def test_all_tonals_present_in_grid():
    grid_tonals = {t[2] for t in AXIS_GRID}
    assert grid_tonals == set(TONALS)


# ---------------------------------------------------------------------------
# DemographicAxisSpec cell_key and tag_labels
# ---------------------------------------------------------------------------


def test_cell_key_format():
    spec = DemographicAxisSpec(
        age_band="youth", cultural_register="non_western", tonal="plain_speech"
    )
    assert spec.cell_key == "youth__non_western__plain_speech"


def test_tag_labels_format():
    spec = DemographicAxisSpec(
        age_band="adult", cultural_register="western_academic", tonal="technical"
    )
    labels = spec.tag_labels()
    assert labels == [
        "demo_age_adult",
        "demo_culture_western_academic",
        "tonal_technical",
    ]


# ---------------------------------------------------------------------------
# All 36 cells produce a valid record without error
# ---------------------------------------------------------------------------


def test_all_36_cells_execute_without_error():
    record = _make_record()
    for age_band, cultural_register, tonal in AXIS_GRID:
        spec = DemographicAxisSpec(
            age_band=age_band,
            cultural_register=cultural_register,
            tonal=tonal,
            seed=42,
        )
        out = apply_demographic_axis(record, spec)
        assert isinstance(out["user_prompt"], str)
        assert len(out["user_prompt"]) > 0
        assert out["cas_expression"] == record["cas_expression"]
