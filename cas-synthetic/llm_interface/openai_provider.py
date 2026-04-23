"""OpenAI provider — paraphrase layer.

Uses the OpenAI chat completions API if `openai` is installed and
`OPENAI_API_KEY` is set. Otherwise raises `ProviderUnavailableError`.
"""

from __future__ import annotations

import os
from typing import Any

from .provider import BaseProvider, ProviderResponse, ProviderUnavailableError


class OpenAIProvider(BaseProvider):
    NAME = "openai"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or self.DEFAULT_MODEL
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client: Any = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY not set")
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ProviderUnavailableError(
                f"openai package not installed: {exc}"
            ) from exc
        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        client = self._get_client()
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = response.choices[0].message.content or ""
            text = text.strip()
            if not text:
                raise ProviderUnavailableError("OpenAI returned empty response")
            return ProviderResponse(
                text=text,
                provider_name=self.NAME,
                tokens_used=getattr(response.usage, "completion_tokens", None)
                if response.usage else None,
            )
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - network path
            raise ProviderUnavailableError(f"OpenAI call failed: {exc}") from exc
