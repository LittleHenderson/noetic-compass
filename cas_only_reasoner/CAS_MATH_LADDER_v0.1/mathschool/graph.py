"""The MATH-L0..L4 prerequisite graph and the RPM selector.

A prerequisite GRAPH, not a staircase (the owner's directive):
branches exist, and the selector names the FIRST missing prerequisite
on the path to a requested skill.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# skill_id -> {level, kind, prerequisites}
SKILLS: Dict[str, Dict] = {
    "quantity_grounding": {
        "level": "MATH-L0", "kind": "grounding",
        "prerequisites": []},
    "counting_order": {
        "level": "MATH-L1", "kind": "computation",
        "prerequisites": ["quantity_grounding"]},
    "integer_comparison": {
        "level": "MATH-L1", "kind": "computation",
        "prerequisites": ["counting_order"]},
    "addition": {
        "level": "MATH-L2", "kind": "computation",
        "prerequisites": ["counting_order"]},
    "subtraction": {
        "level": "MATH-L2", "kind": "computation",
        "prerequisites": ["addition"]},
    "multiplication": {
        "level": "MATH-L2", "kind": "computation",
        "prerequisites": ["addition"]},
    "division": {
        "level": "MATH-L2", "kind": "computation",
        "prerequisites": ["multiplication"]},
    "fractions": {
        "level": "MATH-L3", "kind": "computation",
        "prerequisites": ["division"]},
    "algebra_distribute": {
        "level": "MATH-L4", "kind": "rewrite_rule",
        "prerequisites": ["multiplication", "addition"]},
    "linear_equations": {
        "level": "MATH-L4", "kind": "equation_solving",
        "prerequisites": ["algebra_distribute", "division",
                          "subtraction"]},
}


class GraphError(Exception):
    pass


def skill_info(skill_id: str) -> Dict:
    if skill_id not in SKILLS:
        raise GraphError(f"unknown skill {skill_id!r}")
    return SKILLS[skill_id]


def missing_prerequisites(skill_id: str,
                          promoted: List[str]) -> List[str]:
    """Every not-yet-promoted prerequisite of skill_id, in dependency
    order (deterministic DFS)."""
    seen: List[str] = []

    def walk(current: str) -> None:
        for prerequisite in skill_info(current)["prerequisites"]:
            walk(prerequisite)
            if prerequisite not in promoted \
                    and prerequisite not in seen:
                seen.append(prerequisite)

    walk(skill_id)
    return seen


def next_missing(skill_id: str, promoted: List[str]) -> Optional[str]:
    """RPM: the FIRST missing prerequisite on the way to skill_id,
    or None when the path is clear."""
    missing = missing_prerequisites(skill_id, promoted)
    return missing[0] if missing else None


def teachable_now(promoted: List[str]) -> List[str]:
    """Every skill whose prerequisites are all promoted and which is
    not itself promoted yet - the frontier."""
    return sorted(
        skill_id for skill_id, info in SKILLS.items()
        if skill_id not in promoted
        and all(p in promoted for p in info["prerequisites"]))
