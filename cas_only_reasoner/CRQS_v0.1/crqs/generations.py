"""CAS-G0 through CAS-G10 capability generations, plus CAS-GΩ.

CAS-GΩ is a research designation, not a tier.
"""

from __future__ import annotations

from typing import Dict, List

GENERATIONS: List[Dict] = [
    {"level": "CAS-G0", "name": "Schematic Only",
     "ability": "design exists; native reasoning not yet demonstrated"},
    {"level": "CAS-G1", "name": "Reactive Junction",
     "ability": "one controlled Cause -> Bias -> Effect transformation"},
    {"level": "CAS-G2", "name": "Sequential Circuit",
     "ability": "multi-stage linear reasoning with local probes"},
    {"level": "CAS-G3", "name": "Compositional Reasoner",
     "ability": "represents propositions, decomposes, derives conclusions"},
    {"level": "CAS-G4", "name": "Deliberative Reasoner",
     "ability": "branches, compares alternatives, commits a justified candidate"},
    {"level": "CAS-G5", "name": "Memory-Grounded Reasoner",
     "ability": "persistent provenance-bearing memory used in later reasoning"},
    {"level": "CAS-G6", "name": "Recursive Planner",
     "ability": "subgoals, returns, parent resumption"},
    {"level": "CAS-G7", "name": "Robust Generalizer",
     "ability": "uncertainty, perturbations, tools, unfamiliar variations"},
    {"level": "CAS-G8", "name": "Adaptive Learner",
     "ability": "corrections retained and transferred without regressions"},
    {"level": "CAS-G9", "name": "Self-Improving Architect",
     "ability": "diagnoses and improves its own procedures via sandboxed descendants"},
    {"level": "CAS-G10", "name": "Integrated Cognitive System",
     "ability": "language, math, memory, tools, long-term goals, learning, self-modeling"},
    {"level": "CAS-GΩ", "name": "Open Frontier",
     "ability": "multi-Mind, open-ended research, expanding ecosystem "
                "(research designation only)"},
]


def index_of(level: str) -> int:
    if level == "CAS-GΩ":
        return 11
    return int(level.split("G")[1])


def next_level(level: str) -> str:
    i = index_of(level)
    for gen in GENERATIONS:
        if index_of(gen["level"]) == i + 1:
            return gen["level"]
    return "CAS-GΩ"


def generation(level: str) -> Dict:
    for gen in GENERATIONS:
        if gen["level"] == level:
            return gen
    raise ValueError(f"unknown generation {level}")
