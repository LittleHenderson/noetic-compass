"""Tests for LLM connectors."""

from types import SimpleNamespace

import pytest

from api.llm_connectors.base import (
    BaseLLMConnector,
    provider_idempotency_headers,
)
from api.llm_connectors.mock_connector import MockLLMConnector
from api.llm_connectors.openai_connector import OpenAIConnector
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
    """Should fail if key not configured (skip if key is present in env)."""
    from api.config import settings

    if settings.openai_api_key:
        pytest.skip("OpenAI key is configured — cannot test missing-key path")
    with pytest.raises(LLMError, match="API key not configured"):
        get_connector("openai")


def test_registry_explicit_provider_respected():
    """Explicit provider='mock' returns mock; explicit 'openai' does NOT
    fall back to mock — it raises because no API key is set."""
    from api.config import settings

    mock = get_connector("mock")
    assert isinstance(mock, MockLLMConnector)

    if settings.openai_api_key:
        # Key is present — connector should be created successfully (not mock)
        connector = get_connector("openai")
        assert not isinstance(connector, MockLLMConnector)
    else:
        with pytest.raises(LLMError, match="API key not configured"):
            get_connector("openai")


@pytest.mark.asyncio
async def test_provider_operation_can_disable_application_retries():
    class AlwaysFails(BaseLLMConnector):
        max_retries = 3
        base_delay = 0

        def __init__(self):
            self.calls = 0

        async def _generate(self, prompt, system_prompt="", **kwargs):
            self.calls += 1
            raise RuntimeError("ambiguous provider failure")

    connector = AlwaysFails()
    with pytest.raises(RuntimeError, match="ambiguous provider failure"):
        await connector.generate("one spend only", retry_attempts=1)
    assert connector.calls == 1


def test_provider_idempotency_header_is_exact_and_omits_blank_values():
    assert provider_idempotency_headers(
        {"idempotency_key": "cas-run-stable"}
    ) == {"Idempotency-Key": "cas-run-stable"}
    assert provider_idempotency_headers({"idempotency_key": "  "}) is None
    assert provider_idempotency_headers({}) is None


@pytest.mark.asyncio
async def test_openai_provider_operation_disables_sdk_retry_and_sends_same_key():
    captured: dict[str, object] = {}

    class Completions:
        async def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage=None,
                model="gpt-test",
            )

    no_retry_client = SimpleNamespace(
        chat=SimpleNamespace(completions=Completions())
    )

    class RootClient:
        def with_options(self, *, max_retries):
            captured["max_retries"] = max_retries
            return no_retry_client

        @property
        def chat(self):
            raise AssertionError("journaled calls must use the no-retry SDK client")

    connector = object.__new__(OpenAIConnector)
    connector.client = RootClient()
    connector.model = "gpt-test"
    response = await connector._generate(
        "provider request",
        idempotency_key="cas-run-sdk-no-retry",
    )

    assert response.text == "ok"
    assert captured["max_retries"] == 0
    assert captured["request"]["extra_headers"] == {
        "Idempotency-Key": "cas-run-sdk-no-retry"
    }
