"""Mock LLM connector for testing."""

from __future__ import annotations

import asyncio
import hashlib
import random

from .base import BaseLLMConnector, LLMResponse


class MockLLMConnector(BaseLLMConnector):
    """Returns synthetic CAS-formatted responses for testing.

    Uses a deterministic seed derived from prompt content so that
    identical inputs always produce identical outputs.
    """

    provider_name = "mock"
    max_retries = 1

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        # Simulate slight latency
        await asyncio.sleep(0.01)

        # Deterministic seed from prompt hash for reproducibility
        seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # Generate synthetic operator scores and assessment text
        scores = [round(rng.uniform(0.4, 0.95), 3) for _ in range(10)]

        text = (
            f"CAS Assessment Result:\n"
            f"Operator Scores: {scores}\n"
            f"Analysis: The subject demonstrates moderate cognitive alignment "
            f"with balanced operator involution pairs. Domain coherence is "
            f"within acceptable parameters.\n"
            f"Input length: {len(prompt)} chars"
        )

        return LLMResponse(
            text=text,
            model="mock-cas-v1",
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(text) // 4},
        )
