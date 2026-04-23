"""Local model provider — paraphrase layer.

Posts to an HTTP endpoint configured via the `LOCAL_MODEL_ENDPOINT` env var
(or passed at construction time). Expects OpenAI-compatible schema:
  POST {endpoint}/v1/chat/completions
  body: {model, messages, max_tokens, temperature}
  response: {choices: [{message: {content: ...}}]}

Compatible with llama-server, vllm, and text-generation-inference in
OpenAI-compat mode.
"""

from __future__ import annotations

import os
from typing import Any

from .provider import BaseProvider, ProviderResponse, ProviderUnavailableError


class LocalProvider(BaseProvider):
    NAME = "local"

    def __init__(
        self,
        endpoint: str | None = None,
        model: str = "local",
        timeout: float = 60.0,
    ) -> None:
        self.endpoint = endpoint or os.environ.get("LOCAL_MODEL_ENDPOINT")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.endpoint)

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        if not self.endpoint:
            raise ProviderUnavailableError("LOCAL_MODEL_ENDPOINT not set")
        try:
            import urllib.request
            import json as _json
        except ImportError as exc:  # pragma: no cover - stdlib always available
            raise ProviderUnavailableError(f"stdlib missing: {exc}") from exc

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        data = _json.dumps(body).encode("utf-8")
        url = self.endpoint.rstrip("/") + "/v1/chat/completions"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = _json.loads(resp.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"].strip()
            if not text:
                raise ProviderUnavailableError("Local model returned empty response")
            return ProviderResponse(text=text, provider_name=self.NAME)
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - network path
            raise ProviderUnavailableError(f"Local call failed: {exc}") from exc
