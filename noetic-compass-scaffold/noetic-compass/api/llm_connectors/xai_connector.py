"""xAI Grok connector via OpenAI-compatible API."""

from __future__ import annotations

from openai import AsyncOpenAI

from .base import BaseLLMConnector, LLMResponse, provider_idempotency_headers


class XAIConnector(BaseLLMConnector):
    """xAI Grok via OpenAI-compatible endpoint."""

    provider_name = "xai"

    def __init__(self, api_key: str, model: str = "grok-4.20"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
        self.model = model

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = kwargs.get("model", self.model) or self.model
        temperature = float(kwargs.get("temperature", 0.0))
        call_kwargs: dict[str, object] = {}
        headers = provider_idempotency_headers(kwargs)
        if headers:
            call_kwargs["extra_headers"] = headers
        client = self.client.with_options(max_retries=0) if headers else self.client
        response = await client.chat.completions.create(
            model=model,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            **call_kwargs,  # type: ignore[arg-type]
        )

        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": (response.usage.prompt_tokens or 0)
                + (response.usage.completion_tokens or 0),
            }

        return LLMResponse(
            text=choice.message.content or "",
            model=response.model,
            usage=usage,
        )
