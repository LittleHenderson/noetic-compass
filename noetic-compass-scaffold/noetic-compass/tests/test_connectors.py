"""Tests for LLM connectors."""

import pytest

from api.llm_connectors.mock_connector import MockLLMConnector
from api.llm_connectors.registry import get_connector
from api.errors import LLMError


@pytest.mark.asyncio
async def test_mock_connector_returns_response():
    connector = MockLLMConnector()
    resp = await connector.generate("Hello world")
    assert resp.text
    assert resp.model == "mock-cas-v1"
    assert resp.latency_ms > 0
    assert "prompt_tokens" in resp.usage


@pytest.mark.asyncio
async def test_mock_connector_includes_operator_scores():
    connector = MockLLMConnector()
    resp = await connector.generate("Test prompt")
    assert "Operator Scores:" in resp.text


@pytest.mark.asyncio
async def test_mock_connector_deterministic():
    """Same input should produce same output (reproducibility)."""
    connector = MockLLMConnector()
    resp1 = await connector.generate("Determinism test")
    resp2 = await connector.generate("Determinism test")
    assert resp1.text == resp2.text


def test_registry_returns_mock():
    connector = get_connector("mock")
    assert isinstance(connector, MockLLMConnector)


def test_registry_unknown_provider():
    with pytest.raises(LLMError, match="Unknown provider"):
        get_connector("unknown_provider")


def test_registry_openai_no_key():
    """Should fail if key not configured."""
    with pytest.raises(LLMError, match="API key not configured"):
        get_connector("openai")


def test_registry_explicit_provider_respected():
    """Explicit provider='mock' returns mock; explicit 'openai' does NOT
    fall back to mock — it raises because no API key is set."""
    mock = get_connector("mock")
    assert isinstance(mock, MockLLMConnector)

    with pytest.raises(LLMError, match="API key not configured"):
        get_connector("openai")
