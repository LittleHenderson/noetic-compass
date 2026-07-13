"""Anthropic LLM connector (Claude)."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from .base import BaseLLMConnector, LLMResponse, provider_idempotency_headers


class AnthropicConnector(BaseLLMConnector):
    """Anthropic SDK connector with timeout and token tracking."""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = AsyncAnthropic(api_key=api_key, timeout=60.0)
        self.model = model

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        model = kwargs.get("model", self.model) or self.model
        temperature = float(kwargs.get("temperature", 0.0))
        create_kwargs: dict = {
            "model": model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        headers = provider_idempotency_headers(kwargs)
        if headers:
            create_kwargs["extra_headers"] = headers

        client = self.client.with_options(max_retries=0) if headers else self.client
        response = await client.messages.create(**create_kwargs)

        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return LLMResponse(
            text=text,
            model=response.model,
            usage=usage,
        )
