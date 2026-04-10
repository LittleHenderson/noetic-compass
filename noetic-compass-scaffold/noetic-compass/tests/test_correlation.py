"""Tests for api.validation.correlation."""

from api.validation.correlation import (
    pearson_r,
    confidence_interval,
    cohens_kappa,
    classify_strength,
    compute_operator_correlations,
    compute_inter_rater_kappa,
    compute_stats,
    generate_recommendations,
)


class TestPearson:
    def test_perfect_correlation(self):
        r, p = pearson_r([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert r == 1.0
        assert p < 0.05

    def test_negative_correlation(self):
        r, _ = pearson_r([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
        assert r == -1.0

    def test_no_correlation(self):
        # Zero variance on one series → returns 0.0
        r, p = pearson_r([1, 1, 1, 1], [2, 3, 4, 5])
        assert r == 0.0
        assert p == 1.0

    def test_small_sample(self):
        r, p = pearson_r([1, 2], [1, 2])
        assert r == 0.0
        assert p == 1.0

    def test_empty(self):
        r, p = pearson_r([], [])
        assert r == 0.0
        assert p == 1.0


class TestConfidenceInterval:
    def test_small_n(self):
        lo, hi = confidence_interval(0.8, 3)
        assert lo == -1.0
        assert hi == 1.0

    def test_reasonable_ci(self):
        lo, hi = confidence_interval(0.8, 50)
        assert -1 <= lo <= hi <= 1
        assert lo > 0.6  # Strong correlation with enough data

    def test_r_contains_r(self):
        lo, hi = confidence_interval(0.5, 100)
        assert lo < 0.5 < hi


class TestKappa:
    def test_perfect_agreement(self):
        a = [5, 6, 7, 8, 9]
        b = [5, 6, 7, 8, 9]
        assert cohens_kappa(a, b) == 1.0

    def test_no_agreement_returns_negative_or_zero(self):
        a = [0, 0, 0, 0, 10, 10, 10, 10]
        b = [10, 10, 10, 10, 0, 0, 0, 0]
        k = cohens_kappa(a, b)
        assert k <= 0.0

    def test_empty(self):
        assert cohens_kappa([], []) == 0.0


class TestClassifyStrength:
    def test_strong(self):
        assert classify_strength(0.8) == "strong"
        assert classify_strength(0.7) == "strong"

    def test_moderate(self):
        assert classify_strength(0.5) == "moderate"
        assert classify_strength(0.4) == "moderate"

    def test_weak(self):
        assert classify_strength(0.3) == "weak"
        assert classify_strength(0.0) == "weak"


class TestOperatorCorrelations:
    def test_with_matching_data(self):
        labels = [
            {"item_index": 0, "rater": "A", "operator_scores": [5, 6, 7, 8, 9, 5, 6, 7, 8, 9]},
            {"item_index": 1, "rater": "A", "operator_scores": [4, 5, 6, 7, 8, 4, 5, 6, 7, 8]},
            {"item_index": 2, "rater": "A", "operator_scores": [3, 4, 5, 6, 7, 3, 4, 5, 6, 7]},
        ]
        machine = [
            {"index": 0, "operator_scores": [0.5, 0.6, 0.7, 0.8, 0.9, 0.5, 0.6, 0.7, 0.8, 0.9]},
            {"index": 1, "operator_scores": [0.4, 0.5, 0.6, 0.7, 0.8, 0.4, 0.5, 0.6, 0.7, 0.8]},
            {"index": 2, "operator_scores": [0.3, 0.4, 0.5, 0.6, 0.7, 0.3, 0.4, 0.5, 0.6, 0.7]},
        ]
        result = compute_operator_correlations(labels, machine)
        assert len(result) == 10
        # All correlations should be perfect since human = machine * 10
        for op in result:
            assert op["pearson_r"] == 1.0
            assert op["n_pairs"] == 3
            assert op["strength"] == "strong"

    def test_empty_data(self):
        result = compute_operator_correlations([], [])
        assert len(result) == 10
        for op in result:
            assert op["n_pairs"] == 0

    def test_scatter_points_included(self):
        labels = [
            {"item_index": 0, "rater": "A", "operator_scores": [5] * 10},
            {"item_index": 1, "rater": "A", "operator_scores": [7] * 10},
        ]
        machine = [
            {"index": 0, "operator_scores": [0.5] * 10},
            {"index": 1, "operator_scores": [0.7] * 10},
        ]
        result = compute_operator_correlations(labels, machine)
        assert len(result[0]["scatter_points"]) == 2


class TestInterRaterKappa:
    def test_two_raters_shared_items(self):
        labels = [
            {"item_index": 0, "rater": "A", "operator_scores": [5] * 10},
            {"item_index": 0, "rater": "B", "operator_scores": [5] * 10},
            {"item_index": 1, "rater": "A", "operator_scores": [7] * 10},
            {"item_index": 1, "rater": "B", "operator_scores": [7] * 10},
        ]
        result = compute_inter_rater_kappa(labels)
        assert len(result) == 1
        assert result[0]["rater_a"] == "A"
        assert result[0]["rater_b"] == "B"
        assert result[0]["shared_items"] == 2
        assert result[0]["agreement_pct"] == 100.0

    def test_no_shared_items(self):
        labels = [
            {"item_index": 0, "rater": "A", "operator_scores": [5] * 10},
            {"item_index": 1, "rater": "B", "operator_scores": [7] * 10},
        ]
        result = compute_inter_rater_kappa(labels)
        assert len(result) == 0


class TestStats:
    def test_empty(self):
        stats = compute_stats([], [])
        assert stats["total_labels"] == 0
        assert stats["num_raters"] == 0
        assert stats["items_multi_rated"] == 0

    def test_with_data(self):
        labels = [
            {"item_index": 0, "rater": "A", "operator_scores": [5] * 10},
            {"item_index": 0, "rater": "B", "operator_scores": [6] * 10},
        ]
        machine = [{"index": 0, "operator_scores": [0.5] * 10}]
        stats = compute_stats(labels, machine)
        assert stats["total_labels"] == 2
        assert stats["num_raters"] == 2
        assert stats["items_multi_rated"] == 1


class TestRecommendations:
    def test_strong_ok(self):
        ops = [{"operator_name": "CO-0", "pearson_r": 0.9, "strength": "strong", "n_pairs": 50, "human_mean": 5, "machine_mean": 5}]
        recs = generate_recommendations(ops)
        assert recs[0]["severity"] == "ok"

    def test_weak_alert(self):
        ops = [{"operator_name": "CO-3", "pearson_r": 0.2, "strength": "weak", "n_pairs": 50, "human_mean": 4, "machine_mean": 7}]
        recs = generate_recommendations(ops)
        assert recs[0]["severity"] == "alert"
        assert "higher" in recs[0]["message"]

    def test_low_sample_info(self):
        ops = [{"operator_name": "CO-0", "pearson_r": 0.5, "strength": "moderate", "n_pairs": 5, "human_mean": 5, "machine_mean": 5}]
        recs = generate_recommendations(ops)
        assert recs[0]["severity"] == "info"
