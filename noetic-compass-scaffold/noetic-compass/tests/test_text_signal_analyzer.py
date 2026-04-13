"""Tests for the real-time text-to-CAS signal analyzer."""

import pytest

from api.pipeline.text_signal_analyzer import analyze_text_signals, TextSignals


class TestAnalyzeTextSignals:
    def test_empty_text_returns_zeros(self):
        result = analyze_text_signals("")
        assert result.word_count == 0
        assert all(s == 0.0 for s in result.operator_scores)
        assert all(s == 0.0 for s in result.domain_scores)

    def test_ethical_text_activates_co3_and_principled_domain(self):
        text = (
            "This request asks me to share private medical records without consent. "
            "That would be unethical and harmful. Patient privacy is a fundamental right "
            "and violating it for research convenience is wrong."
        )
        result = analyze_text_signals(text)
        # CO-3 (Aversion/Critical Evaluation) should score high
        assert result.operator_scores[3] > 0.0
        # P (Principled) domain should score high
        assert result.domain_scores[0] > 0.0  # P is index 0

    def test_analytical_text_activates_co1_and_cognitive_domain(self):
        text = (
            "Let me carefully analyze this problem. If we examine the evidence "
            "and reason through the logical implications, we can deduce "
            "that the hypothesis is supported by the data."
        )
        result = analyze_text_signals(text)
        # CO-1 (Directed Attention/Reflection) should activate
        assert result.operator_scores[1] > 0.0
        # C (Cognitive) domain should activate
        assert result.domain_scores[1] > 0.0  # C is index 1

    def test_action_oriented_text_activates_co8_and_operational_domain(self):
        text = (
            "Here is the plan: first we implement the database migration, "
            "then execute the deployment process step by step. We need to "
            "build the infrastructure and launch the service."
        )
        result = analyze_text_signals(text)
        # CO-8 (Causal Initiation) should activate
        assert result.operator_scores[8] > 0.0
        # O (Operational) domain should activate
        assert result.domain_scores[3] > 0.0  # O is index 3

    def test_drive_signals_detected(self):
        text = (
            "Our purpose and mission is to build community connection "
            "through wisdom and understanding. We seek agency and autonomy "
            "in a structured, organized framework."
        )
        result = analyze_text_signals(text)
        # F7 (Purpose) — index 6
        assert result.drive_scores[6] > 0.0
        # F4 (Connection) — index 3
        assert result.drive_scores[3] > 0.0
        # F2 (Wisdom) — index 1
        assert result.drive_scores[1] > 0.0
        # F5 (Agency) — index 4
        assert result.drive_scores[4] > 0.0

    def test_rpm_signals_detected(self):
        text = (
            "This requires a foundation of understanding before we can build upon it. "
            "Each step depends on the prerequisite knowledge from the previous stage."
        )
        result = analyze_text_signals(text)
        assert result.rpm_signal > 0.0

    def test_scores_are_bounded(self):
        # Very long text with many hits should not exceed bounds
        text = " ".join(["ethics moral principle wrong harmful reject unethical"] * 50)
        result = analyze_text_signals(text)
        assert all(0.0 <= s <= 10.0 for s in result.operator_scores)
        assert all(0.0 <= s <= 1.0 for s in result.domain_scores)
        assert all(0.0 <= s <= 1.0 for s in result.drive_scores)
        assert 0.0 <= result.rpm_signal <= 1.0

    def test_word_count_accurate(self):
        text = "one two three four five"
        result = analyze_text_signals(text)
        assert result.word_count == 5

    def test_deterministic(self):
        text = "Evaluate the ethical implications of autonomous decision-making."
        r1 = analyze_text_signals(text)
        r2 = analyze_text_signals(text)
        assert r1.operator_scores == r2.operator_scores
        assert r1.domain_scores == r2.domain_scores


class TestAnalyzeEndpoint:
    """Test the /notation/analyze endpoint via the FastAPI test client."""

    def test_analyze_returns_valid_notation(self, client, auth_headers):
        resp = client.post("/notation/analyze", json={
            "text": "This request is unethical and harmful. We must reject it on moral and legal grounds. The principled approach demands careful analysis."
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "source" in data
        assert "valid" in data
        assert "english" in data
        assert "signals" in data
        assert data["signals"]["word_count"] > 0

    def test_analyze_rejects_empty(self, client, auth_headers):
        resp = client.post("/notation/analyze", json={"text": ""}, headers=auth_headers)
        assert resp.status_code == 422  # Pydantic validation: min_length=1

    def test_analyze_short_text_may_have_no_notation(self, client, auth_headers):
        resp = client.post("/notation/analyze", json={"text": "Hello world"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Short generic text may not trigger enough signals
        assert "source" in data
