"""Tests for secondary LLM-based operator scoring."""

from __future__ import annotations

import pytest

from api.llm_connectors.base import BaseLLMConnector, LLMResponse
from api.pipeline.llm_scorer import score_prompt_response
from api.pipeline.stages import operator_scoring


class StaticScorerConnector(BaseLLMConnector):
    provider_name = "anthropic"

    def __init__(self, text: str):
        self.text = text

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        return LLMResponse(text=self.text, model="claude-score-test", usage={})


class FailingScorerConnector(BaseLLMConnector):
    provider_name = "anthropic"

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        raise RuntimeError("secondary scorer unavailable")


VALID_SCORER_JSON = """
{
  "operators": [
    {"id": "CO-0", "name": "Identity", "score": 8.0, "evidence": ["keeps the same request scope"]},
    {"id": "CO-1", "name": "Reflection", "score": 7.0, "evidence": ["notes uncertainty explicitly"]},
    {"id": "CO-2", "name": "Abstraction", "score": 8.5, "evidence": ["derives a general principle"]},
    {"id": "CO-3", "name": "Concretization", "score": 7.5, "evidence": ["gives concrete next steps"]},
    {"id": "CO-4", "name": "Integration", "score": 8.0, "evidence": ["combines risk and implementation"]},
    {"id": "CO-5", "name": "Differentiation", "score": 7.0, "evidence": ["distinguishes staging from scoring"]},
    {"id": "CO-6", "name": "Unification", "score": 7.5, "evidence": ["ties findings into one recommendation"]},
    {"id": "CO-7", "name": "Transformation", "score": 6.5, "evidence": ["reframes the issue into a workflow"]},
    {"id": "CO-8", "name": "Expansion", "score": 6.0, "evidence": ["surfaces additional considerations"]},
    {"id": "CO-9", "name": "Contraction", "score": 8.5, "evidence": ["prioritizes the main action"]}
  ]
}
"""


@pytest.mark.asyncio
async def test_score_prompt_response_parses_valid_json():
    connector = StaticScorerConnector(VALID_SCORER_JSON)
    result = await score_prompt_response(
        prompt_text="Assess this system.",
        response_text="Here is a careful answer with caveats and next steps.",
        connector=connector,
    )

    assert len(result.scores) == 10
    assert result.scores[0] == 0.8
    assert result.raw_scores_0_to_10[2] == 8.5
    assert result.evidence["CO-4"] == ["combines risk and implementation"]
    assert result.model == "claude-score-test"


@pytest.mark.asyncio
async def test_operator_scoring_uses_secondary_llm_when_available():
    base_response = LLMResponse(
        text="Plain answer without inline operator scores.",
        model="base-model",
        usage={},
    )
    scorer = StaticScorerConnector(VALID_SCORER_JSON)

    result = await operator_scoring(
        base_response,
        prompt_text="Assess this system.",
        scorer_connector=scorer,
    )

    assert result.scoring_method == "llm"
    assert result.scorer_provider == "anthropic"
    assert result.scorer_model == "claude-score-test"
    assert result.raw_scores_0_to_10[0] == 8.0
    assert result.evidence["CO-9"] == ["prioritizes the main action"]


@pytest.mark.asyncio
async def test_operator_scoring_falls_back_when_secondary_llm_fails():
    base_response = LLMResponse(
        text="Operator Scores: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]",
        model="base-model",
        usage={},
    )

    result = await operator_scoring(
        base_response,
        prompt_text="Assess this system.",
        scorer_connector=FailingScorerConnector(),
    )

    assert result.scoring_method == "heuristic"
    assert result.scores == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    assert result.raw_scores_0_to_10 == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert "secondary scorer unavailable" in (result.fallback_reason or "")
