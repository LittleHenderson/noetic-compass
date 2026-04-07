"""Base LLM connector ABC with retry logic and token usage logging."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger("noetic.llm")


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""

    text: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0


# CAS-specific system prompt that elicits responses across all 10 Cognitive Operators.
# Used by all real (non-mock) connectors.
CAS_SYSTEM_PROMPT = (
    "You are an advanced analytical assistant performing a Cognitive Architecture System (CAS) "
    "assessment. Analyze the user's text across all 10 cognitive operator dimensions:\n\n"
    "CO-0 Identity: Assess how the text preserves core meaning and self-consistency.\n"
    "CO-1 Reflection: Evaluate self-awareness, metacognition, and introspective quality.\n"
    "CO-2 Abstraction: Measure the ability to generalize from specifics to principles.\n"
    "CO-3 Concretization: Assess the capacity to turn abstract concepts into actionable specifics.\n"
    "CO-4 Integration: Evaluate synthesis of diverse concepts into a coherent whole.\n"
    "CO-5 Differentiation: Measure nuanced distinction-making and avoidance of oversimplification.\n"
    "CO-6 Unification: Assess the ability to bring disparate elements into alignment.\n"
    "CO-7 Transformation: Evaluate adaptive change and evolving perspectives.\n"
    "CO-8 Expansion: Measure exploration of new territory and broadening of scope.\n"
    "CO-9 Contraction: Assess focus, prioritization, and noise reduction.\n\n"
    "Also assess the 4 Processing Domains (Principled, Cognitive, Evaluative, Operational), "
    "the 7 Core Drives (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose), "
    "and any signs of cognitive inversions.\n\n"
    "Provide your analysis as a detailed structured response. Include a line:\n"
    "Operator Scores: [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]\n"
    "where each score is a float between 0.0 and 1.0."
)


class BaseLLMConnector(ABC):
    """Abstract base class for LLM connectors."""

    provider_name: str = "base"
    max_retries: int = 3
    base_delay: float = 1.0

    @abstractmethod
    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        """Provider-specific generation. Subclasses implement this."""
        ...

    async def generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        """Generate with exponential backoff retry and token usage logging."""
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                start = time.monotonic()
                response = await self._generate(prompt, system_prompt, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                response.latency_ms = elapsed
                # Log token usage for cost tracking
                if response.usage:
                    logger.info(
                        "LLM usage: provider=%s model=%s latency=%.0fms tokens=%s",
                        self.provider_name,
                        response.model,
                        elapsed,
                        response.usage,
                    )
                return response
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    self.max_retries,
                    self.provider_name,
                    e,
                )
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2**attempt)
                    await asyncio.sleep(delay)
        raise last_error  # type: ignore[misc]
