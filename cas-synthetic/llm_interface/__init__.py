"""LLM provider interface for CAS synthetic data paraphrase layer."""

from .provider import BaseProvider, ProviderResponse, ProviderUnavailableError
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .local_provider import LocalProvider

__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "ProviderUnavailableError",
    "ClaudeProvider",
    "OpenAIProvider",
    "LocalProvider",
    "get_default_provider",
]


def get_default_provider() -> "BaseProvider | None":
    """Return the first provider whose credentials are configured.

    Precedence: Anthropic → OpenAI → Local → None.
    When all return None, the scaffold falls back to template-only generation.
    """
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeProvider()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider()
    if os.environ.get("LOCAL_MODEL_ENDPOINT"):
        return LocalProvider(endpoint=os.environ["LOCAL_MODEL_ENDPOINT"])
    return None
