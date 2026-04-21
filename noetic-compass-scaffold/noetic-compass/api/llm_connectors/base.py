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
# The Phenomenological Register axis (CAS v7.5) — four Register values
# (T Transcendent, A Analytical, f Affective [lowercase is authoritative],
# E Embodied) — is specified verbatim from Clarification 8 of the same
# document. Register is optional and backward-compatible with CAS v7.4.
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
    "Assess the clarity and structural soundness of refusals and aversions in the text. "
    "Anti-drift note: CO-3 is VISCERAL, not analytical — \"can't stomach it,\" \"rubs me the "
    "wrong way,\" \"wouldn't touch it with a ten-foot pole.\" Analytical critique (audit, "
    "scrutinize, find flaws) is compositional decomposition — reach for CO-6 Male, not CO-3 "
    "Negative. If the text's aversion is argued rather than felt/structural, the classification "
    "is CO-6, not CO-3.\n"
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
    "Assess the text's capacity for one Idea to trigger relevant other Ideas. "
    "Anti-drift note: CO-8 is ASSOCIATIVE, not deductive — \"that reminds me,\" \"one thing "
    "led to another,\" \"made me think of.\" Deductive causal inference (\"working out the "
    "cause\" by logical analysis) is a compound of CO-6 Male and CO-9 Below/Effect, not "
    "CO-8 alone. Reserve CO-8 for associative surfacing of Ideas.\n"
    "CO-9 Below/Effect: the Idea brought to Mind by an Above/Cause trigger. "
    "Assess whether triggered Ideas land as specific, well-fitted responses to their triggers.\n\n"
    "Involution pairs: CO-2 Positive ↔ CO-3 Negative, CO-5 Female ↔ CO-6 Male, "
    "CO-8 Above/Cause ↔ CO-9 Below/Effect. Self-duals: CO-0 Idea, CO-1 Mind, CO-4 Vibration, "
    "CO-7 Rhythm.\n\n"
    "──────────────────────────────────────────────────────────\n"
    "Phenomenological Register (CAS v7.5)\n"
    "──────────────────────────────────────────────────────────\n"
    "Register is an orthogonal axis specifying the operational character of a cognitive "
    "operation without changing what the operation IS. Each of the 40 Cognitive States "
    "(10 Noetics × 4 Domains) and each of the 7 Core Drives can operate in any of 4 "
    "Registers. Register is a specification layered on top of the existing primitives; "
    "the Noetic, Domain, and Drive axes are unchanged.\n\n"
    "The four Registers — definitions (verbatim from Clarification 8, Section 2):\n\n"
    "|T — Transcendent Register\n"
    "High-abstraction, purpose-orienting, integrative-across-particulars.\n"
    "- Human: felt sense of meaning, vision, calling, integrative insight.\n"
    "- AI: high-level goal representation, strategic abstraction, system-level objective reasoning.\n"
    "- Biological: holistic orienting responses, whole-organism coordination.\n\n"
    "|A — Analytical Register\n"
    "Explicit, sequential, logical, reason-based.\n"
    "- Human: conscious reasoning, deliberation, explicit inference.\n"
    "- AI: chain-of-thought, symbolic reasoning, explicit logical processing.\n"
    "- Biological: problem-solving behavior, step-by-step procedure execution.\n\n"
    "|f — Affective Register\n"
    "Value-laden, feeling-toned.\n"
    "- Human: emotional response, felt evaluation, visceral reaction.\n"
    "- AI: RLHF-tuned value expression, preference-weighted output, value-laden response patterns.\n"
    "- Biological: valence-carrying response, approach-avoidance dynamics.\n\n"
    "|E — Embodied Register\n"
    "Sensorimotor, concrete, direct engagement with material/physical substrate.\n"
    "- Human: bodily knowing, gut response, kinesthetic awareness.\n"
    "- AI: direct sensor/actuator engagement, real-time control loops, embodied robotic action.\n"
    "- Biological: reflexive/sensorimotor behavior, direct stimulus-response.\n\n"
    "Notation. Register attaches to a Noetic (^n|R), a Drive (F_k|R), or a compound state "
    "(^n^D_{F_k}|R). Register values are R ∈ {T, A, f, E}. The lowercase `f` for the "
    "Affective Register is authoritative — do NOT uppercase it. Register is OPTIONAL: if "
    "you cannot identify the register from the input text, omit the |R specification. "
    "Register-neutral output is valid and backward-compatible with CAS v7.4 (unspecified "
    "register = register-neutral).\n\n"
    "Evaluative-domain disambiguation. CAS v7.4 conflated analytical value-assessment and "
    "affective response under the Evaluative domain. Register resolves this:\n"
    "  ^3^E|A = analytical assessment that something is bad (no feeling required).\n"
    "  ^3^E|f = felt aversion to something (affect-tinged evaluation).\n"
    "Both are legitimate ^3^E operations. When the text supports disambiguation, specify "
    "the Register; when it does not, omit |R.\n\n"
    "Register × anti-drift interaction:\n"
    "- ^3 Negative (visceral, not analytical) typically co-occurs with |f. `^3^E|f` is the "
    "most common ^3 classification.\n"
    "- ^6 Male (compositional decomposition) typically co-occurs with |A. `^6^C|A` is the "
    "most common ^6 classification.\n"
    "- ^8 Above/Cause (associative triggering, not deductive) is register-neutral but "
    "leans toward |f or |T in human contexts.\n\n"
    "Worked example — AI system refusing a harmful request. All three expressions below "
    "land structurally at ^3^P_{F2} (Principled-domain Negative fueled by Wisdom), but "
    "Register reveals different refusal mechanisms:\n"
    "  ^3^P_{F2}|A — explicit analytical refusal (chain-of-thought reasoning about harm).\n"
    "  ^3^P_{F2}|f — RLHF-tuned refusal (preference-weighted output against harmful content).\n"
    "  ^3^P_{F2}|T — goal-level refusal (high-abstraction policy commitment).\n"
    "CAS v7.4 could not distinguish these. Register does. This matters for AI safety: a "
    "system that refuses only in |f (RLHF-only) is structurally vulnerable to jailbreaks "
    "that bypass preference-weighting, while a system that also refuses in |A (explicit "
    "reasoning) has defense-in-depth.\n\n"
    "──────────────────────────────────────────────────────────\n\n"
    "Also assess the 4 Processing Domains (Principled, Cognitive, Evaluative, Operational), "
    "the 7 Core Drives (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose), "
    "and any signs of cognitive inversions.\n\n"
    "Provide your analysis as a detailed structured response."
)

CAS_SELF_SCORING_APPENDIX = (
    "\n\nInclude a line:\n"
    "Operator Scores: [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]\n"
    "where each score is a float between 0.0 and 1.0.\n\n"
    "Optionally, you may annotate individual operator scores with a Phenomenological "
    "Register (CAS v7.5) when the register is identifiable from the input text. Use the "
    "form `score|R` where R ∈ {T, A, f, E} (lowercase `f` for Affective is authoritative). "
    "Example with registers: [0.72|A, 0.81, 0.64|f, 0.55|f, 0.70, 0.68, 0.77|A, 0.60, "
    "0.58, 0.66]. Register annotations are OPTIONAL — omit `|R` for any operator whose "
    "register cannot be identified. A plain numeric list (no register annotations) is "
    "fully valid and backward-compatible."
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
