"""Tests for the real-time CAS notation synthesizer."""

import pytest

from api.pipeline.notation_synthesizer import (
    SynthesizedNotation,
    synthesize_notation,
    _pick_significant_operators,
    _pick_significant_domains,
    _pick_significant_drives,
    _pick_flagged_inversions,
    _build_expression,
)


# ---------------------------------------------------------------------------
# Helpers — default pipeline output for a "typical" assessment
# ---------------------------------------------------------------------------

def _default_kwargs(**overrides):
    base = dict(
        operator_scores=[0.6, 0.7, 0.5, 0.8, 0.4, 0.9, 0.3, 0.7, 0.6, 0.5],
        raw_scores_0_to_10=[6.0, 7.0, 5.0, 8.0, 4.0, 9.0, 3.0, 7.0, 6.0, 5.0],
        domain_averages=[0.7, 0.6, 0.5, 0.4],
        drive_chains=[
            [0.8, 0.7, 0.6],  # F1 — full chain passes
            [0.9, 0.8, 0.7],  # F2 — full chain passes
            [0.3, 0.2, 0.1],  # F3 — fails
            [0.6, 0.5, 0.4],  # F4 — partial
            [0.7, 0.6, 0.5],  # F5 — full chain passes
            [0.4, 0.3, 0.2],  # F6 — fails
            [0.8, 0.7, 0.6],  # F7 — full chain passes
        ],
        a0_score=0.75,
        rpm_completeness=0.65,
        inversion_axis_scores=[0.8, 0.3, 0.9, 0.7, 0.4, 0.6, 0.5],
        fractal_sequence=[5, 3, 1, 7, 0],
        fractal_classification="stabilizing",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Component extraction tests
# ---------------------------------------------------------------------------

class TestPickSignificantOperators:
    def test_selects_above_threshold(self):
        raw = [6.0, 7.0, 4.0, 8.0, 3.0, 9.0, 2.0, 7.0, 5.0, 5.0]
        result = _pick_significant_operators(raw)
        # CO-5 (9.0), CO-3 (8.0), CO-1 (7.0), CO-7 (7.0) — top 4
        assert result == [5, 3, 1, 7]

    def test_caps_at_max(self):
        raw = [10.0] * 10
        result = _pick_significant_operators(raw)
        assert len(result) <= 4

    def test_empty_when_all_below(self):
        raw = [2.0, 3.0, 4.0, 1.0, 0.0, 4.9, 3.5, 2.1, 1.0, 0.5]
        result = _pick_significant_operators(raw)
        assert result == []


class TestPickSignificantDomains:
    def test_selects_above_threshold(self):
        result = _pick_significant_domains([0.7, 0.6, 0.5, 0.4])
        assert result == ["P", "C", "E"]

    def test_all_strong(self):
        result = _pick_significant_domains([0.8, 0.7, 0.6, 0.5])
        assert result == ["P", "C", "E", "O"]

    def test_none_significant(self):
        result = _pick_significant_domains([0.1, 0.2, 0.3, 0.4])
        assert result == []


class TestPickSignificantDrives:
    def test_separates_rpm_and_plain(self):
        drive_chains = [
            [0.8, 0.7, 0.6],  # F1 — all pass → RPM
            [0.3, 0.2, 0.1],  # F2 — all fail → neither
            [0.7, 0.6, 0.4],  # F3 — D+W pass, P fails → plain
            [0.8, 0.7, 0.6],  # F4 — all pass → RPM
            [0.1, 0.1, 0.1],  # F5 — all fail
            [0.1, 0.1, 0.1],  # F6 — all fail
            [0.1, 0.1, 0.1],  # F7 — all fail
        ]
        rpm, plain = _pick_significant_drives(drive_chains, a0_score=0.7)
        assert 0 in rpm  # F1
        assert 3 in rpm  # F4
        assert 2 in plain  # F3 — active but incomplete chain


class TestPickFlaggedInversions:
    def test_flags_low_resistance(self):
        scores = [0.8, 0.3, 0.9, 0.7, 0.4, 0.6, 0.5]
        result = _pick_flagged_inversions(scores)
        assert "W" in result  # 0.3
        assert "S" in result  # 0.4


# ---------------------------------------------------------------------------
# Expression building tests
# ---------------------------------------------------------------------------

class TestBuildExpression:
    def test_operators_with_domains(self):
        expr = _build_expression(
            operators=[3, 5],
            domains=["P", "C"],
            rpm_drives=[],
            plain_drives=[],
            fractal_sequence=None,
            fractal_classification=None,
        )
        assert "CO-3^P" in expr
        assert "CO-5^P" in expr  # both ops appear in primary domain
        # Domain descent appears as separate statement
        assert "->" in expr

    def test_rpm_drives(self):
        expr = _build_expression(
            operators=[5],
            domains=["C"],
            rpm_drives=[4],
            plain_drives=[],
            fractal_sequence=None,
            fractal_classification=None,
        )
        assert "RPM(F5)" in expr
        assert "CO-5^C" in expr

    def test_plain_drives(self):
        expr = _build_expression(
            operators=[],
            domains=[],
            rpm_drives=[],
            plain_drives=[2],
            fractal_sequence=None,
            fractal_classification=None,
        )
        assert expr == "F3"

    def test_fractal_included_when_non_neutral(self):
        expr = _build_expression(
            operators=[5],
            domains=["C"],
            rpm_drives=[],
            plain_drives=[],
            fractal_sequence=[5, 3, 1],
            fractal_classification="stabilizing",
        )
        assert "Phi<" in expr

    def test_fractal_excluded_when_neutral(self):
        expr = _build_expression(
            operators=[5],
            domains=["C"],
            rpm_drives=[],
            plain_drives=[],
            fractal_sequence=[5, 3, 1],
            fractal_classification="neutral",
        )
        assert "Phi" not in expr

    def test_empty_when_nothing_significant(self):
        expr = _build_expression([], [], [], [], None, None)
        assert expr == ""


# ---------------------------------------------------------------------------
# Full synthesis integration tests
# ---------------------------------------------------------------------------

class TestSynthesizeNotation:
    def test_produces_valid_compiled_notation(self):
        result = synthesize_notation(**_default_kwargs())
        assert isinstance(result, SynthesizedNotation)
        assert result.valid is True
        assert result.source  # non-empty
        assert result.english  # non-empty
        assert result.provenance["compiler_valid"] is True

    def test_includes_dominant_operators(self):
        result = synthesize_notation(**_default_kwargs())
        # CO-5 scored 9.0, CO-3 scored 8.0 — both should appear
        assert "CO-5" in result.source
        assert "CO-3" in result.source

    def test_includes_rpm_for_complete_chains(self):
        result = synthesize_notation(**_default_kwargs())
        # F1 and F2 have complete chains — at least one should have RPM
        assert "RPM(" in result.source

    def test_includes_fractal_for_non_neutral(self):
        result = synthesize_notation(**_default_kwargs(
            fractal_sequence=[5, 3, 1, 7],
            fractal_classification="stabilizing",
        ))
        assert "Phi<" in result.source

    def test_auto_generates_fractal_from_operator_order(self):
        """Even with neutral classification, 3+ operators auto-generate Phi<>."""
        result = synthesize_notation(**_default_kwargs(
            fractal_classification="neutral",
        ))
        # 4 operators above threshold → auto-generated fractal sequence
        assert "Phi<" in result.source

    def test_handles_all_below_threshold(self):
        result = synthesize_notation(**_default_kwargs(
            raw_scores_0_to_10=[2.0, 3.0, 1.0, 4.0, 0.5, 4.9, 1.0, 2.0, 3.0, 1.5],
            domain_averages=[0.1, 0.2, 0.3, 0.1],
            drive_chains=[[0.1, 0.1, 0.1]] * 7,
            a0_score=0.2,
            fractal_classification="neutral",
        ))
        assert result.valid is False
        assert "below significance" in result.provenance.get("reason", "")

    def test_provenance_tracks_components(self):
        result = synthesize_notation(**_default_kwargs())
        prov = result.provenance
        assert "operators_found" in prov
        assert "domains_found" in prov
        assert "rpm_drives" in prov
        assert "compiler_engine" in prov

    def test_deterministic(self):
        """Same inputs produce the same notation every time."""
        kwargs = _default_kwargs()
        r1 = synthesize_notation(**kwargs)
        r2 = synthesize_notation(**kwargs)
        assert r1.source == r2.source
        assert r1.valid == r2.valid
