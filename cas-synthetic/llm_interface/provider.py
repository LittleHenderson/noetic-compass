"""Abstract LLM provider interface.

Each concrete provider implements `generate(prompt, system_prompt)` and
returns a `ProviderResponse`. Providers are paraphrase-layer-only in the
Level 2 scaffold — templates handle structural correctness, LLM adds
semantic diversity. If every provider is unavailable (no keys configured),
the scaffold falls back to template-only generation gracefully.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


class ProviderUnavailableError(RuntimeError):
    """Raised when an LLM provider cannot serve a request (missing key,
    rate-limit, network failure). Scaffold catches this and falls back to
    template-only generation for the current example."""


@dataclass
class ProviderResponse:
    text: str
    provider_name: str
    tokens_used: int | None = None


class BaseProvider(abc.ABC):
    """Abstract LLM paraphrase provider."""

    #: Canonical provider name, e.g. "claude", "openai", "local".
    NAME: str = ""

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        """Produce one paraphrase. Synchronous.

        Raises:
            ProviderUnavailableError on any provider-side failure.
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """True iff this provider has credentials or endpoint configured.
        Default implementation always returns True — concrete providers
        override to check environment variables.
        """
        return True
