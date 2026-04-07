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
    assert "Drive Scores:" in resp.text


def test_registry_returns_mock():
    connector = get_connector("mock")
    assert isinstance(connector, MockLLMConnector)


def test_registry_unknown_provider():
    """When mock_llm=False, unknown provider should raise LLMError."""
    import api.config
    original = api.config.settings.mock_llm
    api.config.settings.mock_llm = False
    try:
        with pytest.raises(LLMError, match="Unknown provider"):
            get_connector("unknown_provider")
    finally:
        api.config.settings.mock_llm = original


def test_registry_openai_no_key():
    """Should fail if key not configured and not in mock mode."""
    import api.config
    original = api.config.settings.mock_llm
    api.config.settings.mock_llm = False
    try:
        with pytest.raises(LLMError, match="API key not configured"):
            get_connector("openai")
    finally:
        api.config.settings.mock_llm = original


def test_registry_mock_mode_overrides():
    """When mock_llm=True, any provider returns mock."""
    connector = get_connector("openai")
    assert isinstance(connector, MockLLMConnector)
