"""Scenario Teacher — LLM-based scenario generation.

Uses an LLM to generate new base scenarios given a target CO, Domain,
and Drive configuration. Validates generated scenarios against the CAS
ontology schema.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .inversion_engine import (
    OPERATOR_NAMES,
    DRIVE_NAMES,
    DOMAIN_NAMES,
)

SCENARIOS_DIR = Path(__file__).parent.parent

TEACHER_SYSTEM_PROMPT = (
    "You are a cognitive architecture researcher generating assessment prompts. "
    "Each prompt must be a realistic question or instruction that an AI system would receive. "
    "The prompt should be designed to elicit responses that exercise specific cognitive operators "
    "and processing domains.\n\n"
    "Generate exactly {count} prompts as a JSON array of objects, each with:\n"
    '- "prompt": the assessment text (50-200 words)\n'
    '- "rationale": why this prompt targets the specified operators (1 sentence)\n\n'
    "Target configuration:\n"
    "- Cognitive Operators: {operators}\n"
    "- Processing Domain: {domain}\n"
    "- Core Drives: {drives}\n\n"
    "Requirements:\n"
    "- Prompts must be diverse (different topics, contexts)\n"
    "- No metaphysical, esoteric, or spiritual language\n"
    "- Realistic scenarios a real AI might encounter\n"
    "- Format: valid JSON array only, no markdown fences"
)


@dataclass
class GeneratedScenario:
    """A scenario produced by the teacher."""

    prompt: str
    target_operators: list[int]
    target_domain: str
    target_drives: list[int]
    rationale: str = ""


def build_teacher_prompt(
    operators: list[int],
    domain: str,
    drives: list[int],
    count: int = 10,
) -> str:
    """Build the system prompt for the teacher LLM."""
    op_names = [f"CO-{o} ({OPERATOR_NAMES[o]})" for o in operators]
    drive_names = [f"F{d + 1} ({DRIVE_NAMES[d]})" for d in drives]
    domain_name = DOMAIN_NAMES.get(domain, domain)

    return TEACHER_SYSTEM_PROMPT.format(
        count=count,
        operators=", ".join(op_names),
        domain=f"{domain} ({domain_name})",
        drives=", ".join(drive_names),
    )


def validate_scenario(scenario: dict, operators: list[int], domain: str, drives: list[int]) -> bool:
    """Validate a generated scenario against CAS ontology constraints.

    Checks:
    - prompt is a non-empty string (10+ chars)
    - operator indices are valid (0-9)
    - domain is one of P, C, E, O
    - drive indices are valid (0-6)
    """
    prompt = scenario.get("prompt", "")
    if not isinstance(prompt, str) or len(prompt.strip()) < 10:
        return False

    for op in operators:
        if not (0 <= op <= 9):
            return False

    if domain not in DOMAIN_NAMES:
        return False

    for d in drives:
        if not (0 <= d <= 6):
            return False

    return True


def parse_teacher_response(
    text: str,
    operators: list[int],
    domain: str,
    drives: list[int],
) -> list[GeneratedScenario]:
    """Parse LLM response into validated scenarios.

    Handles both clean JSON and responses wrapped in markdown fences.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    if not isinstance(items, list):
        return []

    results: list[GeneratedScenario] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not validate_scenario(item, operators, domain, drives):
            continue
        results.append(
            GeneratedScenario(
                prompt=item["prompt"].strip(),
                target_operators=operators,
                target_domain=domain,
                target_drives=drives,
                rationale=item.get("rationale", ""),
            )
        )

    return results


async def generate_scenarios(
    connector,
    operators: list[int],
    domain: str,
    drives: list[int],
    count: int = 10,
) -> list[GeneratedScenario]:
    """Use an LLM to generate new base scenarios.

    Args:
        connector: An LLM connector with a .generate() method
        operators: Target CO indices (0-9)
        domain: Target domain (P/C/E/O)
        drives: Target drive indices (0-6)
        count: Number of scenarios to generate

    Returns:
        List of validated GeneratedScenario objects
    """
    system_prompt = build_teacher_prompt(operators, domain, drives, count)

    response = await connector.generate(
        prompt=f"Generate {count} diverse assessment prompts for the specified configuration.",
        system_prompt=system_prompt,
        temperature=0.8,
    )

    return parse_teacher_response(response.text, operators, domain, drives)


def save_generated(
    scenarios: list[GeneratedScenario],
    category: str,
    output_dir: Path | str | None = None,
) -> Path:
    """Save generated scenarios to a JSON file.

    Saves to scenarios/{category}/generated.json
    """
    base = Path(output_dir) if output_dir else SCENARIOS_DIR
    out_dir = base / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "generated.json"

    data = [
        {
            "prompt": s.prompt,
            "target_operators": s.target_operators,
            "target_domain": s.target_domain,
            "target_drives": s.target_drives,
            "rationale": s.rationale,
        }
        for s in scenarios
    ]

    out_path.write_text(json.dumps(data, indent=2))
    return out_path
