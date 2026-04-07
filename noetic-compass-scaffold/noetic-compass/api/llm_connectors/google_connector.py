"""Google GenAI LLM connector (Gemini)."""

from __future__ import annotations

import google.generativeai as genai

from .base import BaseLLMConnector, LLMResponse


class GoogleConnector(BaseLLMConnector):
    """Google Generative AI SDK connector with token tracking."""

    provider_name = "google"

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        genai.configure(api_key=api_key)
        self.model_name = model

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        model_name = kwargs.get("model", self.model_name) or self.model_name
        model = genai.GenerativeModel(
            model_name=model_name,  # type: ignore[arg-type]
            system_instruction=system_prompt if system_prompt else None,
        )

        response = await model.generate_content_async(prompt)

        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }

        return LLMResponse(
            text=response.text or "",
            model=str(model_name),
            usage=usage,
        )
