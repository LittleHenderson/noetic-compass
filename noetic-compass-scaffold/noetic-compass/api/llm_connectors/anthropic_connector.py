"""Anthropic LLM connector (Claude)."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from .base import BaseLLMConnector, LLMResponse


class AnthropicConnector(BaseLLMConnector):
    """Anthropic SDK connector."""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        model = kwargs.get("model", self.model) or self.model
        create_kwargs: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        response = await self.client.messages.create(**create_kwargs)

        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return LLMResponse(
            text=text,
            model=response.model,
            usage=usage,
        )
