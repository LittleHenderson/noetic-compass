"""The mathematics curriculum: a prerequisite DAG, ordered.

Repetition is not drilling the same problem endlessly - it is varied
examples that preserve the same underlying structure. Each stage's
tasks are versioned fixtures; ordering is deterministic.
"""

from __future__ import annotations

from typing import Dict, List

STAGES: Dict[str, List[str]] = {
    "exact_arithmetic": [],
    "substitution": ["exact_arithmetic"],
    "axiom_identities": ["exact_arithmetic"],
    "counterexamples": ["exact_arithmetic"],
    "procedure_proofs": ["axiom_identities"],
    "mistake_recovery": ["procedure_proofs", "counterexamples"],
}

STAGE_FIXTURES: Dict[str, str] = {
    "exact_arithmetic": "arithmetic_tasks.json",
    "substitution": "arithmetic_tasks.json",
    "axiom_identities": "identity_tasks.json",
    "counterexamples": "conjecture_tasks.json",
    "procedure_proofs": "identity_tasks.json",
    "mistake_recovery": "mistake_package.json",
}


def curriculum_order() -> List[str]:
    """Deterministic topological order of the stage DAG."""
    order: List[str] = []
    remaining = dict(STAGES)
    while remaining:
        ready = sorted(s for s, prereqs in remaining.items()
                       if all(p in order for p in prereqs))
        if not ready:
            raise ValueError(f"curriculum DAG has a cycle: {remaining}")
        order.append(ready[0])
        del remaining[ready[0]]
    return order


def prerequisites_of(stage: str) -> List[str]:
    return list(STAGES.get(stage, []))


def fixture_of(stage: str) -> str:
    return STAGE_FIXTURES[stage]
