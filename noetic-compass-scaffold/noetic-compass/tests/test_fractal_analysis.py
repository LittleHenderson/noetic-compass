"""Tests for api.pipeline.fractal_analysis."""

from api.pipeline.fractal_analysis import (
    analyze_fractal,
    canonicalize,
    classify_fractal,
    extract_dominant_sequence,
    is_dual_pair,
)


class TestDualPairs:
    def test_involution_pairs(self):
        assert is_dual_pair(2, 3)
        assert is_dual_pair(3, 2)
        assert is_dual_pair(5, 6)
        assert is_dual_pair(8, 9)

    def test_non_pairs(self):
        assert not is_dual_pair(1, 2)
        assert not is_dual_pair(0, 0)


class TestCanonicalize:
    def test_cancel_co2_co3(self):
        canonical, n = canonicalize([1, 2, 3, 4])
        assert canonical == [1, 4]
        assert n == 1

    def test_cancel_all_pairs(self):
        canonical, n = canonicalize([2, 3, 5, 6, 8, 9])
        assert canonical == [0]
        assert n == 3

    def test_identity_preserved(self):
        canonical, n = canonicalize([0])
        assert canonical == [0]
        assert n == 0

    def test_no_cancellations(self):
        canonical, n = canonicalize([1, 4, 7])
        assert canonical == [1, 4, 7]
        assert n == 0

    def test_identity_elimination(self):
        canonical, _ = canonicalize([1, 0, 4])
        assert canonical == [1, 4]


class TestClassify:
    def test_neutral(self):
        assert classify_fractal([0]) == "neutral"

    def test_empty(self):
        assert classify_fractal([]) == "neutral"

    def test_self_dual_stabilizes(self):
        # ⟨1:4:7⟩ — all self-dual, should stabilize or oscillate
        result = classify_fractal([1, 4, 7])
        assert result in ("stabilizing", "oscillatory")


class TestExtractSequence:
    def test_extracts_top_5(self):
        scores = [0.1, 0.9, 0.8, 0.2, 0.7, 0.3, 0.6, 0.4, 0.5, 0.05]
        seq = extract_dominant_sequence(scores, top_n=5)
        # Top 5 by score: indices 1(0.9), 2(0.8), 4(0.7), 6(0.6), 8(0.5)
        assert seq == [1, 2, 4, 6, 8]

    def test_empty_scores(self):
        assert extract_dominant_sequence([]) == [0]


class TestAnalyzeFractal:
    def test_full_analysis(self):
        scores = [0.5, 0.7, 0.8, 0.3, 0.9, 0.6, 0.4, 0.5, 0.65, 0.8]
        result = analyze_fractal(scores)
        assert len(result.dominant_sequence) > 0
        assert len(result.canonical_form) > 0
        assert result.classification in ("stabilizing", "amplifying", "oscillatory", "neutral")
        assert result.orbit_length >= 1

    def test_analysis_has_all_fields(self):
        result = analyze_fractal([0.5] * 10)
        assert hasattr(result, "dominant_sequence")
        assert hasattr(result, "canonical_form")
        assert hasattr(result, "cancellations_detected")
        assert hasattr(result, "classification")
        assert hasattr(result, "orbit_length")
        assert hasattr(result, "has_fixed_point")
