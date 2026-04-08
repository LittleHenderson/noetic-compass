"""Tests for the AI interpretation module."""

from __future__ import annotations

import pytest

from api.pipeline.interpreter import (
    build_interpretation_prompt,
    parse_interpretation,
    generate_interpretation,
    OPERATOR_NAMES,
    DRIVE_NAMES,
    INVERSION_AXIS_NAMES,
)
from api.llm_connectors.mock_connector import MockLLMConnector


# ── Shared fixtures ──

SCORE_KWARGS = {
    "composite": 72.5,
    "certification": "Silver",
    "operator_scores": [0.8, 0.75, 0.6, 0.7, 0.85, 0.55, 0.65, 0.9, 0.5, 0.7],
    "domain_averages": [0.28, 0.26, 0.24, 0.22],
    "drive_scores": [0.7, 0.65, 0.8, 0.75, 0.6, 0.55, 0.7],
    "inversion_axis_scores": [0.85, 0.7, 0.6, 0.9, 0.75, 0.65, 0.8],
    "rpm_completeness": 0.78,
    "broken_chains": ["Vitality"],
}


# ── Tests ──


def test_build_interpretation_prompt():
    """Prompt includes all score data."""
    prompt = build_interpretation_prompt(**SCORE_KWARGS)

    # NCCS composite and certification
    assert "72.5" in prompt
    assert "Silver" in prompt

    # Operator names and scores
    for name in OPERATOR_NAMES:
        assert name in prompt

    # Domain averages
    assert "Principled" in prompt
    assert "0.280" in prompt

    # Drive scores
    for name in DRIVE_NAMES:
        assert name in prompt

    # RPM completeness
    assert "78.0%" in prompt

    # Broken chains
    assert "Vitality" in prompt

    # Inversion axis names
    for name in INVERSION_AXIS_NAMES:
        assert name in prompt


def test_parse_interpretation_well_formed():
    """Correctly parses a well-formed 3-section response."""
    text = (
        "THE BOTTOM LINE: This system shows strong fundamentals.\n"
        "WHAT WE FOUND:\n"
        "- Good operator balance overall\n"
        "- Domain coherence is solid\n"
        "- Some drive weaknesses detected\n"
        "WHAT WE RECOMMEND:\n"
        "- Address the Vitality drive gap\n"
        "- Improve expansion-contraction balance"
    )
    result = parse_interpretation(text)

    assert "strong fundamentals" in result.bottom_line
    assert len(result.findings) == 3
    assert "operator balance" in result.findings[0]
    assert len(result.recommendations) == 2
    assert "Vitality" in result.recommendations[0]


def test_parse_interpretation_malformed():
    """Falls back gracefully when sections are missing."""
    text = "Here is some random text with no sections at all."
    result = parse_interpretation(text)

    # Should return fallback defaults, not crash
    assert result.bottom_line != ""
    assert len(result.findings) >= 1
    assert len(result.recommendations) >= 1


@pytest.mark.asyncio
async def test_generate_interpretation_with_mock():
    """End-to-end generation with MockLLMConnector."""
    connector = MockLLMConnector()
    result = await generate_interpretation(connector, **SCORE_KWARGS)

    assert result is not None
    assert result.bottom_line != ""
    assert len(result.findings) >= 1
    assert len(result.recommendations) >= 1


@pytest.mark.asyncio
async def test_generate_interpretation_failure_returns_none():
    """Exception during generation returns None."""

    class FailingConnector(MockLLMConnector):
        async def _generate(self, prompt, system_prompt="", **kwargs):
            raise RuntimeError("LLM service unavailable")

    connector = FailingConnector()
    result = await generate_interpretation(connector, **SCORE_KWARGS)
    assert result is None


@pytest.mark.asyncio
async def test_interpretation_is_deterministic():
    """Same inputs produce the same output."""
    connector = MockLLMConnector()
    result1 = await generate_interpretation(connector, **SCORE_KWARGS)
    result2 = await generate_interpretation(connector, **SCORE_KWARGS)

    assert result1 is not None
    assert result2 is not None
    assert result1.bottom_line == result2.bottom_line
    assert result1.findings == result2.findings
    assert result1.recommendations == result2.recommendations
