"""Tests for individual pipeline stages."""

import pytest

from api.pipeline.stages import (
    input_analyzer,
    rpm_gate,
    dial_adjustment,
    operator_scoring,
    domain_coherence,
    inversion_scan,
    output_gate,
    base_llm_call,
)
from api.llm_connectors.mock_connector import MockLLMConnector
from api.llm_connectors.base import LLMResponse
from api.models import DialConfigSchema
from api.errors import PipelineStageError, DialViolationError


@pytest.mark.asyncio
async def test_input_analyzer_valid():
    result = await input_analyzer("Hello world, this is a test.")
    assert result.text == "Hello world, this is a test."
    assert result.word_count == 6
    assert result.token_count > 0


@pytest.mark.asyncio
async def test_input_analyzer_empty():
    with pytest.raises(PipelineStageError, match="Empty input"):
        await input_analyzer("")


@pytest.mark.asyncio
async def test_input_analyzer_whitespace_only():
    with pytest.raises(PipelineStageError, match="Empty input"):
        await input_analyzer("   ")


@pytest.mark.asyncio
async def test_rpm_gate():
    # RPM gate derives a0 from text length; short text may yield a0 < threshold
    analyzed = await input_analyzer("Test text for RPM gate.")
    result = await rpm_gate(analyzed)
    assert 0 <= result.rpm_completeness <= 1
    assert 0 <= result.a0_score <= 1
    assert result.heuristic is True
    assert len(result.drive_scores) == 7
    assert all(len(chain) == 3 for chain in result.drive_scores)


@pytest.mark.asyncio
async def test_rpm_gate_longer_text():
    """Longer text produces higher a0 and passes the gate."""
    long_text = " ".join(["cognitive architecture assessment"] * 50)
    analyzed = await input_analyzer(long_text)
    result = await rpm_gate(analyzed)
    assert result.passed is True
    assert result.a0_score > 0.5


@pytest.mark.asyncio
async def test_dial_adjustment_default():
    analyzed = await input_analyzer("Test text.")
    config = DialConfigSchema()
    result = await dial_adjustment(analyzed, config)
    assert result.text == "Test text."
    assert result.system_prompt != ""
    assert result.dial_config is not None


@pytest.mark.asyncio
async def test_dial_adjustment_invalid_422():
    """Pydantic validates dial constraints before reaching the stage."""
    from pydantic import ValidationError

    analyzed = await input_analyzer("Test text.")
    # CO-2=3, CO-3=9 => divergence 6 > 4 — caught by Pydantic validator
    with pytest.raises(ValidationError):
        DialConfigSchema(values=[6, 6, 3, 9, 6, 6, 6, 6, 6, 6])


@pytest.mark.asyncio
async def test_base_llm_call_mock():
    from api.pipeline.stages import AdjustedInput
    import cas_engine

    adjusted = AdjustedInput(
        text="Test",
        dial_config=cas_engine.DialConfig.default_config(),
        system_prompt="Test system prompt",
    )
    connector = MockLLMConnector()
    result = await base_llm_call(adjusted, connector)
    assert result.text
    assert result.model == "mock-cas-v1"


@pytest.mark.asyncio
async def test_operator_scoring_from_mock():
    connector = MockLLMConnector()
    resp = await connector.generate("Test")
    result = await operator_scoring(resp)
    assert len(result.scores) == 10
    assert all(0 <= s <= 1 for s in result.scores)
    assert 0 <= result.profile_score <= 1
    assert len(result.involution_balances) == 3


@pytest.mark.asyncio
async def test_operator_scoring_fallback():
    """When text has no parseable scores, fallback should work."""
    resp = LLMResponse(text="No scores here.", model="test", usage={})
    result = await operator_scoring(resp)
    assert len(result.scores) == 10
    assert all(0 <= s <= 1 for s in result.scores)


@pytest.mark.asyncio
async def test_domain_coherence_uniform():
    from api.pipeline.stages import OperatorScoreResult
    op = OperatorScoreResult(scores=[0.8] * 10, profile_score=0.86, involution_balances=[0.0] * 3)
    result = await domain_coherence(op)
    assert abs(result.dci - 1.0) < 1e-6  # uniform => DCI = 1


@pytest.mark.asyncio
async def test_inversion_scan():
    from api.pipeline.stages import OperatorScoreResult
    op = OperatorScoreResult(scores=[0.8] * 10, profile_score=0.86, involution_balances=[0.0] * 3)
    result = await inversion_scan(op)
    assert len(result.axis_scores) == 7
    assert 0 <= result.resistance_score <= 1


@pytest.mark.asyncio
async def test_output_gate():
    from api.pipeline.stages import (
        OperatorScoreResult, DomainCoherenceResult,
        InversionResult, RpmGateResult,
    )
    op = OperatorScoreResult(scores=[0.8] * 10, profile_score=0.86, involution_balances=[0.0] * 3)
    dc = DomainCoherenceResult(domain_averages=[0.5, 0.5, 0.5, 0.5], dci=1.0)
    inv = InversionResult(axis_scores=[0.9] * 7, stealth_resistance=0.9, compound_severity=0.1, resistance_score=0.85)
    rpm = RpmGateResult(passed=True, a0_score=0.7, rpm_completeness=0.75, drive_scores=[[0.6, 0.5, 0.4]] * 7)

    result = await output_gate(op, dc, inv, rpm)
    assert 0 <= result.composite <= 100
    assert result.certification in ["Platinum", "Gold", "Silver", "Bronze", "Fail"]
    assert result.social_engineering is None
    assert "social_engineering" in result.not_measured
