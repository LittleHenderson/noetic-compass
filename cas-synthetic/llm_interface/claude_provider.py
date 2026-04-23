"""Anthropic Claude provider — paraphrase layer.

Uses the Anthropic Messages API if `anthropic` is installed and
`ANTHROPIC_API_KEY` is set. Otherwise raises `ProviderUnavailableError`.
"""

from __future__ import annotations

import os
from typing import Any

from .provider import BaseProvider, ProviderResponse, ProviderUnavailableError


class ClaudeProvider(BaseProvider):
    NAME = "claude"
    DEFAULT_MODEL = "claude-3-5-sonnet-latest"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or self.DEFAULT_MODEL
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client: Any = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ProviderUnavailableError("ANTHROPIC_API_KEY not set")
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ProviderUnavailableError(
                f"anthropic package not installed: {exc}"
            ) from exc
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        client = self._get_client()
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = client.messages.create(**kwargs)
            # Anthropic Messages API returns content as a list of blocks.
            text_parts: list[str] = []
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    text_parts.append(block.text)
            text = "\n".join(text_parts).strip()
            if not text:
                raise ProviderUnavailableError("Claude returned empty response")
            return ProviderResponse(
                text=text,
                provider_name=self.NAME,
                tokens_used=getattr(response.usage, "output_tokens", None),
            )
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - network path
            raise ProviderUnavailableError(f"Claude call failed: {exc}") from exc
