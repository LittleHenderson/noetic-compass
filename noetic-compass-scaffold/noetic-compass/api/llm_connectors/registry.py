"""LLM connector factory/registry."""

from __future__ import annotations

from api.config import settings
from api.errors import LLMError

from .base import BaseLLMConnector
from .mock_connector import MockLLMConnector


def get_connector(provider: str, model: str | None = None) -> BaseLLMConnector:
    """Get an LLM connector by provider name.

    Falls back to mock if MOCK_LLM is set or provider is "mock".
    """
    if settings.mock_llm or provider == "mock":
        return MockLLMConnector()

    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMError("OpenAI API key not configured", provider="openai")
        from .openai_connector import OpenAIConnector

        return OpenAIConnector(
            api_key=settings.openai_api_key,
            model=model or "gpt-4",
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMError("Anthropic API key not configured", provider="anthropic")
        from .anthropic_connector import AnthropicConnector

        return AnthropicConnector(
            api_key=settings.anthropic_api_key,
            model=model or "claude-sonnet-4-6",
        )

    if provider == "google":
        if not settings.google_api_key:
            raise LLMError("Google API key not configured", provider="google")
        from .google_connector import GoogleConnector

        return GoogleConnector(
            api_key=settings.google_api_key,
            model=model or "gemini-1.5-pro",
        )

    if provider == "meta":
        if not settings.meta_api_base_url:
            raise LLMError("Meta API base URL not configured", provider="meta")
        from .meta_connector import MetaConnector

        return MetaConnector(
            api_base=settings.meta_api_base_url,
            api_key=settings.meta_api_key,
            model=model or "llama-3-70b",
        )

    raise LLMError(f"Unknown provider: {provider}", provider=provider)
