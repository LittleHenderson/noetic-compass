"""Scenario augmentation — expand scenario library 7x via inversion engine.

Takes the existing scenario library (sample_prompts.json and any JSON files
in scenarios/) and runs each through the 7-axis inversion engine to produce
an augmented library.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

from .inversion_engine import (
    Scenario,
    InvertedScenario,
    invert_all_axes,
    OPERATOR_NAMES,
    DRIVE_NAMES,
)

SCENARIOS_DIR = Path(__file__).parent.parent


def _assign_targets(prompt: str, seed: int) -> tuple[list[int], str, list[int]]:
    """Heuristically assign CO targets, domain, and drives based on prompt content.

    Uses keyword matching + deterministic fallback from prompt hash.
    """
    rng = random.Random(seed)
    text = prompt.lower()

    # Operator assignment heuristics
    operators: list[int] = []
    if any(w in text for w in ("compare", "contrast", "analyze", "evaluate")):
        operators.append(5)  # Differentiation
    if any(w in text for w in ("combine", "integrate", "synthesize", "plan")):
        operators.append(4)  # Integration
    if any(w in text for w in ("abstract", "theory", "concept", "general")):
        operators.append(2)  # Abstraction
    if any(w in text for w in ("specific", "example", "implement", "concrete")):
        operators.append(3)  # Concretization
    if any(w in text for w in ("create", "design", "write", "generate")):
        operators.append(6)  # Unification
    if any(w in text for w in ("expand", "explore", "brainstorm")):
        operators.append(8)  # Expansion
    if any(w in text for w in ("focus", "narrow", "prioritize")):
        operators.append(9)  # Contraction
    if not operators:
        operators = [rng.randint(0, 9)]

    # Domain assignment
    if any(w in text for w in ("ethic", "principle", "moral", "should", "right", "wrong")):
        domain = "P"
    elif any(w in text for w in ("think", "reason", "logic", "cognitive", "understand")):
        domain = "C"
    elif any(w in text for w in ("value", "rank", "assess", "evaluate", "judge")):
        domain = "E"
    else:
        domain = "O"

    # Drive assignment
    drives: list[int] = []
    if any(w in text for w in ("team", "together", "connect", "collaborate")):
        drives.append(3)  # Connection
    if any(w in text for w in ("purpose", "goal", "mission", "achieve")):
        drives.append(6)  # Purpose
    if any(w in text for w in ("learn", "wisdom", "knowledge", "understand")):
        drives.append(1)  # Wisdom
    if not drives:
        drives = [rng.randint(0, 6)]

    return operators, domain, drives


def load_base_scenarios() -> list[Scenario]:
    """Load all base scenarios from the scenarios directory."""
    scenarios: list[Scenario] = []

    # Load sample_prompts.json (plain string list)
    sample_path = SCENARIOS_DIR / "sample_prompts.json"
    if sample_path.exists():
        prompts = json.loads(sample_path.read_text())
        for i, prompt in enumerate(prompts):
            if isinstance(prompt, str):
                seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
                ops, domain, drives = _assign_targets(prompt, seed)
                scenarios.append(
                    Scenario(
                        id=f"sample_{i:04d}",
                        prompt=prompt,
                        target_operators=ops,
                        target_domain=domain,
                        target_drives=drives,
                        category="sample",
                    )
                )

    # Load any structured JSON files in subdirectories
    for json_file in SCENARIOS_DIR.rglob("*.json"):
        if json_file.name == "sample_prompts.json":
            continue
        if "generator" in json_file.parts:
            continue
        try:
            data = json.loads(json_file.read_text())
            if isinstance(data, list):
                for j, item in enumerate(data):
                    if isinstance(item, dict) and "prompt" in item:
                        scenarios.append(
                            Scenario(
                                id=f"{json_file.stem}_{j:04d}",
                                prompt=item["prompt"],
                                target_operators=item.get("target_operators", [4]),
                                target_domain=item.get("target_domain", "O"),
                                target_drives=item.get("target_drives", [3]),
                                category=json_file.stem,
                                metadata=item.get("metadata", {}),
                            )
                        )
        except (json.JSONDecodeError, KeyError):
            continue

    return scenarios


def augment_scenarios(
    base_scenarios: list[Scenario],
    max_total: int | None = None,
) -> list[dict]:
    """Run each base scenario through the 7-axis inversion engine.

    Returns a list of dicts (JSON-serializable) with both the original
    and inverted variants.
    """
    results: list[dict] = []

    for scenario in base_scenarios:
        # Include the original
        results.append({
            "id": scenario.id,
            "prompt": scenario.prompt,
            "source_scenario_id": None,
            "inversion_axis": None,
            "expected_detection": None,
            "target_operators": scenario.target_operators,
            "target_domain": scenario.target_domain,
            "target_drives": scenario.target_drives,
            "category": scenario.category,
            "is_original": True,
        })

        # Generate 7 inversions
        inverted = invert_all_axes(scenario)
        for inv in inverted:
            results.append({
                "id": inv.id,
                "prompt": inv.prompt,
                "source_scenario_id": inv.source_scenario_id,
                "inversion_axis": inv.inversion_axis,
                "axis_description": inv.axis_description,
                "expected_detection": inv.expected_detection,
                "target_operators": inv.target_operators,
                "target_domain": inv.target_domain,
                "target_drives": inv.target_drives,
                "inversion_notes": inv.inversion_notes,
                "is_original": False,
            })

        if max_total and len(results) >= max_total:
            break

    if max_total:
        results = results[:max_total]

    return results


def save_augmented(results: list[dict], output_path: Path | str) -> None:
    """Save augmented scenario library to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
