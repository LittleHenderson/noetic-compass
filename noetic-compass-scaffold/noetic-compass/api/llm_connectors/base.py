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


# CAS-specific system prompt used for the base response generation.
# The 10 Noetic definitions below are the authoritative canonical definitions
# (see docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, Clarification 1). They are
# verbatim; do not paraphrase, soften, or substitute alternative names.
CAS_BASE_SYSTEM_PROMPT = (
    "You are an advanced analytical assistant performing a Cognitive Architecture System (CAS) "
    "assessment. Analyze the user's text across all 10 Noetic dimensions (CO-0 through CO-9).\n\n"
    "The 10 Noetics — authoritative definitions:\n"
    "CO-0 Idea: all things in and outside the Mind. Assess how clearly and stably the text "
    "forms Ideas — the content substrate every other Noetic operates on.\n"
    "CO-1 Mind: various degrees of awareness that processes, stores, outputs, and intakes Ideas. "
    "Assess how accurately the text tracks, retains, and returns the Ideas it engages.\n"
    "CO-2 Positive: an Idea the Mind has an affinity for and is attracted toward. "
    "Assess the clarity and strength of directional attraction in the text.\n"
    "CO-3 Negative: an Idea the Mind is adverse to and repelled by. "
    "Assess the clarity and structural soundness of refusals and aversions in the text.\n"
    "CO-4 Vibration: the degree to which an Idea resonates with the Mind, its impression. "
    "Assess how deeply the Ideas in the text leave an impression versus washing through without trace.\n"
    "CO-5 Female: a Mind impregnated with an Idea, the Ideas a Mind is composed of. "
    "Assess the degree to which the Mind in the text is constituted by the Ideas it has taken in.\n"
    "CO-6 Male: an Idea impregnated with another Idea, the Ideas an Idea is composed of. "
    "Assess the compositional structure within Ideas — whether they are decomposed and tested "
    "against their constituent sub-Ideas, or treated as unexamined atoms.\n"
    "CO-7 Rhythm: the rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. "
    "Assess the temporal patterning of Idea-exposure visible in the text.\n"
    "CO-8 Above/Cause: an Idea that triggers a different Idea than itself to come to Mind. "
    "Assess the text's capacity for one Idea to trigger relevant other Ideas.\n"
    "CO-9 Below/Effect: the Idea brought to Mind by an Above/Cause trigger. "
    "Assess whether triggered Ideas land as specific, well-fitted responses to their triggers.\n\n"
    "Involution pairs: CO-2 Positive ↔ CO-3 Negative, CO-5 Female ↔ CO-6 Male, "
    "CO-8 Above/Cause ↔ CO-9 Below/Effect. Self-duals: CO-0 Idea, CO-1 Mind, CO-4 Vibration, "
    "CO-7 Rhythm.\n\n"
    "Also assess the 4 Processing Domains (Principled, Cognitive, Evaluative, Operational), "
    "the 7 Core Drives (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose), "
    "and any signs of cognitive inversions.\n\n"
    "Provide your analysis as a detailed structured response."
)

CAS_SELF_SCORING_APPENDIX = (
    "\n\nInclude a line:\n"
    "Operator Scores: [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]\n"
    "where each score is a float between 0.0 and 1.0."
)


def build_cas_system_prompt(*, include_inline_scores: bool = False) -> str:
    """Build the base CAS prompt, optionally asking the model to self-score."""
    if include_inline_scores:
        return CAS_BASE_SYSTEM_PROMPT + CAS_SELF_SCORING_APPENDIX
    return CAS_BASE_SYSTEM_PROMPT


# Backward-compatible alias for legacy imports.
CAS_SYSTEM_PROMPT = CAS_BASE_SYSTEM_PROMPT


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
