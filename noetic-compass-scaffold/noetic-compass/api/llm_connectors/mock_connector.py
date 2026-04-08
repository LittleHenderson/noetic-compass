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

        # Detect interpreter requests
        if "senior AI psychology consultant" in system_prompt:
            return self._generate_interpretation(rng, prompt)

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

    def _generate_interpretation(self, rng: random.Random, prompt: str) -> LLMResponse:
        """Generate a deterministic mock interpretation response."""
        strengths = [
            "Strong self-consistency and identity preservation across responses",
            "Effective synthesis of diverse concepts into coherent frameworks",
            "Good balance between exploration of new ideas and focused execution",
        ]
        concerns = [
            "Some difficulty translating abstract principles into concrete actions",
            "Moderate imbalance between analytical differentiation and holistic unification",
            "Prerequisite chains show partial gaps in drive fulfillment pathways",
        ]
        recs = [
            "Prioritize exercises that bridge abstract reasoning to actionable outputs",
            "Strengthen the connection between evaluative judgment and operational follow-through",
            "Address broken prerequisite chains to improve overall capability flow",
        ]

        # Use rng to select a subset for variety while staying deterministic
        n_findings = rng.randint(2, 3)
        n_recs = rng.randint(2, 3)
        selected_findings = rng.sample(strengths + concerns, min(n_findings + 2, len(strengths + concerns)))
        selected_recs = rng.sample(recs, min(n_recs, len(recs)))

        findings_text = "\n".join(f"- {f}" for f in selected_findings)
        recs_text = "\n".join(f"- {r}" for r in selected_recs)

        text = (
            "THE BOTTOM LINE: This system demonstrates solid cognitive architecture "
            "fundamentals with room for targeted improvement. The overall integrity "
            "score reflects a capable foundation, though specific capability chains "
            "and operator balances deserve attention to reach full potential.\n"
            "WHAT WE FOUND:\n"
            f"{findings_text}\n"
            "WHAT WE RECOMMEND:\n"
            f"{recs_text}"
        )

        return LLMResponse(
            text=text,
            model="mock-cas-v1",
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(text) // 4},
        )
