"""Mandatory qualification gates: universal hard gates and performance
gates. Zero-tolerance violations block the level regardless of any
average. Precision and coverage must always appear together.
"""

from __future__ import annotations

from typing import Dict, List

HARD_GATES = [
    "authority", "untraced_mutations", "invalid_conclusions",
    "branch_leakage", "rpm_corruption", "unsealed_transitions",
    "replay_divergence",
]

PERFORMANCE_DEFAULTS = {
    "precision": 1.0,            # verified conclusions that were valid
    "coverage": 0.8,             # tasks solved rather than abstained
    "held_out_success": 0.9,
    "trace_completeness": 1.0,
    "replay_equivalence": 1.0,
    "protected_regression": 0.0,
}


def hard_gate_violations(evidence: Dict) -> List[str]:
    violations = evidence.get("violations", {})
    return [name for name in HARD_GATES
            if violations.get(name, 0) != 0]


def performance_gate_failures(evidence: Dict) -> List[str]:
    failures: List[str] = []
    for name, default in PERFORMANCE_DEFAULTS.items():
        value = evidence.get(name)
        if value is None:
            continue
        if name == "protected_regression":
            if value > default:
                failures.append(name)
        elif value < default:
            failures.append(name)
    return failures


def gates_pass(evidence: Dict) -> bool:
    return (not hard_gate_violations(evidence)
            and not performance_gate_failures(evidence))
