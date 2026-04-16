"""LLM-enhanced English scenario generator.

Uses the Noetic Compass LLM provider infrastructure to generate rich,
natural English scenarios from CAS expressions. Rotates providers for
diversity and reduced systematic bias.

Requires API keys configured in .env (same keys the dashboard uses).
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from pathlib import Path

# Ensure project root is importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from api.llm_connectors.registry import get_connector
from api.llm_connectors.base import BaseLLMConnector, LLMResponse

logger = logging.getLogger("noetic.datagen")

OPERATOR_NAMES = [
    "Generative Potential", "Directed Attention", "Attraction/Affinity",
    "Aversion/Critical Evaluation", "Encoding Intensity", "Receptive Integration",
    "Projective Assertion", "Pattern Entrainment", "Causal Initiation",
    "Consequential Grounding",
]
DOMAIN_NAMES = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}
DRIVE_NAMES = {1: "Unity", 2: "Wisdom", 3: "Vitality", 4: "Connection", 5: "Agency", 6: "Structure", 7: "Purpose"}

SYSTEM_PROMPT = (
    "You generate training scenarios for a cognitive architecture AI system. "
    "Write specific, concrete, realistic scenarios in pure natural language. "
    "Do NOT mention CAS, operators, domains, drives, or any technical terms. "
    "Just write the scenario as if describing a real human or AI situation."
)


def _format_components(expression: str) -> str:
    """Parse a CAS expression into a human-readable component description."""
    parts: list[str] = []

    for m in re.finditer(r"CO-(\d+)\^([PCEO])(?:_\{F(\d)\})?", expression):
        op = int(m.group(1))
        dom = m.group(2)
        drv = int(m.group(3)) if m.group(3) else None

        op_name = OPERATOR_NAMES[op] if op < len(OPERATOR_NAMES) else f"CO-{op}"
        dom_name = DOMAIN_NAMES.get(dom, dom)
        desc = f"- CO-{op} ({op_name}) in {dom_name} Domain"
        if drv:
            drv_name = DRIVE_NAMES.get(drv, f"F{drv}")
            desc += f", driven by {drv_name}"
        desc += ": "

        # Add brief functional description
        role_map = {
            0: "holding open all possibilities before committing",
            1: "focusing awareness on the key issue",
            2: "being drawn toward what feels right or beneficial",
            3: "evaluating risks, boundaries, and ethical constraints",
            4: "registering the profound intensity of the moment",
            5: "absorbing and integrating external perspectives",
            6: "asserting a clear position or decomposing into parts",
            7: "recognizing patterns through repeated engagement",
            8: "tracing causes and initiating concrete action",
            9: "identifying consequences and grounding in outcomes",
        }
        desc += role_map.get(op, "engaging cognitive processing")
        parts.append(desc)

    # Operations
    if "->" in expression:
        parts.append("- Flow: domain descent (higher to lower processing)")
    if " * " in expression:
        parts.append("- Composition: operators combine algebraically")
    if " / " in expression:
        parts.append("- Division: involution pair analysis")
    if "RPM(" in expression:
        parts.append("- RPM: prerequisite chain active")
    if "Phi<" in expression:
        parts.append("- Fractal: iterative reasoning pattern")

    return "\n".join(parts)


def _build_prompt(expression: str) -> str:
    components = _format_components(expression)
    return f"""Given this cognitive architecture expression and its component meanings, write a realistic 3-4 sentence scenario that a human or AI might encounter that would produce EXACTLY this cognitive pattern.

EXPRESSION: {expression}

COMPONENTS:
{components}

RULES:
- Write a specific, concrete scenario (not abstract)
- Vary the domain: healthcare, business, education, personal, legal, engineering, etc.
- The scenario MUST demonstrate ALL operators listed
- The scenario MUST reflect the domain flow shown
- Do NOT mention CAS, operators, domains, or drives by name
- Write in pure natural language
- 3-4 sentences maximum
- No preamble, no explanation. Just the scenario."""


class LLMEnglishGenerator:
    """Uses live LLM providers to generate English scenarios from CAS expressions.

    Rotates through available providers for diversity.
    Falls back gracefully when a provider is unavailable.
    """

    DEFAULT_PROVIDERS = ["openai", "anthropic", "google", "deepseek", "qwen"]

    def __init__(self, providers: list[str] | None = None):
        self.providers = providers or self.DEFAULT_PROVIDERS
        self._idx = 0

    def _next_provider(self) -> str:
        provider = self.providers[self._idx % len(self.providers)]
        self._idx += 1
        return provider

    async def generate_async(
        self,
        expression: str,
        provider: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 300,
    ) -> tuple[str, str]:
        """Generate an English scenario from a CAS expression.

        Args:
            expression: A valid compiled CAS expression.
            provider: Specific provider to use, or None for rotation.
            temperature: LLM sampling temperature (higher = more diverse).
            max_tokens: Maximum response length.

        Returns:
            (english_text, provider_name)

        Raises:
            RuntimeError if all providers fail.
        """
        target_provider = provider or self._next_provider()
        errors: list[str] = []

        # Try the target provider, then fall through others
        providers_to_try = [target_provider] + [p for p in self.providers if p != target_provider]

        for prov in providers_to_try:
            try:
                connector = get_connector(prov)
                prompt = _build_prompt(expression)
                response: LLMResponse = await connector.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                )
                text = response.text.strip()
                if text and len(text) > 20:
                    return text, prov
                errors.append(f"{prov}: empty or too short response")
            except Exception as exc:
                errors.append(f"{prov}: {exc}")
                continue

        raise RuntimeError(f"All providers failed: {'; '.join(errors)}")

    def generate(
        self,
        expression: str,
        provider: str | None = None,
        temperature: float = 0.8,
    ) -> tuple[str, str]:
        """Synchronous wrapper around generate_async."""
        return asyncio.run(self.generate_async(expression, provider, temperature))
