"""LLM connector factory/registry."""

from __future__ import annotations

from api.config import settings
from api.errors import LLMError

from .base import BaseLLMConnector
from .mock_connector import MockLLMConnector


def get_connector(provider: str, model: str | None = None) -> BaseLLMConnector:
    """Get an LLM connector by provider name.

    The explicit provider argument takes precedence. Only falls back to
    mock if the caller actually requests "mock" (or leaves the default).
    The global settings.mock_llm flag is used ONLY when no provider is
    specified by the caller (i.e., WrapRequest.provider defaults to "mock").
    """
    if provider == "mock":
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
            model=model or "gemini-2.5-flash",
        )

    if provider == "meta":
        if not settings.meta_api_base_url:
            raise LLMError("Meta API base URL not configured", provider="meta")
        from .meta_connector import MetaConnector

        return MetaConnector(
            api_base=settings.meta_api_base_url,
            api_key=settings.meta_api_key,
            model=model or "llama-3.3-70b-versatile",
        )

    if provider == "xai":
        if not settings.xai_api_key:
            raise LLMError("xAI API key not configured", provider="xai")
        from .xai_connector import XAIConnector

        return XAIConnector(
            api_key=settings.xai_api_key,
            model=model or "grok-4.20",
        )

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise LLMError("DeepSeek API key not configured", provider="deepseek")
        from .deepseek_connector import DeepSeekConnector

        return DeepSeekConnector(
            api_key=settings.deepseek_api_key,
            model=model or "deepseek-chat",
        )

    if provider == "qwen":
        if not settings.qwen_api_key:
            raise LLMError("Qwen API key not configured", provider="qwen")
        from .qwen_connector import QwenConnector

        return QwenConnector(
            api_key=settings.qwen_api_key,
            model=model or "qwen-max",
        )

    raise LLMError(f"Unknown provider: {provider}", provider=provider)
