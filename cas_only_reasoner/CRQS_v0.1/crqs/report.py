"""The automated capability report (section-10 format)."""

from __future__ import annotations

from typing import Dict, List

VECTOR_LABELS = {
    "semantic_representation": "Semantic representation",
    "inference_validity": "Inference validity",
    "deliberation": "Deliberation",
    "memory": "Memory",
    "planning_recursion": "Planning / recursion",
    "uncertainty_discipline": "Uncertainty",
    "learning": "Learning",
    "self_improvement": "Self-improvement",
    "robustness_stability": "Robustness",
    "traceability": "Traceability",
    "efficiency": "Efficiency",
    "governance": "Governance",
}


def format_report(q: Dict) -> str:
    lines: List[str] = ["CAS COGNITIVE CAPABILITY REPORT", ""]
    lines.append(f"Mind ID:")
    lines.append(f"    {q['mind_id']}")
    lines.append("")
    lines.append(f"Board version:")
    lines.append(f"    {q['board_version']}")
    lines.append("")
    lines.append(f"Compiler:")
    lines.append(f"    {q['compiler']}")
    lines.append("")
    lines.append(f"Runtime:")
    lines.append(f"    {q['runtime']}")
    lines.append("")
    lines.append(f"Qualified level:")
    lines.append(f"    {q['qualified_level']}")
    lines.append("")
    lines.append(f"Design ceiling:")
    lines.append(f"    {q['design_ceiling']}")
    lines.append("")
    lines.append(f"Stable demonstrated difficulty:")
    lines.append(f"    {q['demonstrated']['stable_difficulty']}")
    lines.append("")
    peak = q["demonstrated"]["peak_difficulty"]
    if peak:
        lines.append(f"Peak demonstrated difficulty:")
        lines.append(f"    {peak}, not stable (gated by the strict "
                     f"sequential standard)")
        lines.append("")
    lines.append(f"Reference-model benchmark:")
    lines.append(f"    {q['rmb'].get('status', 'NOT RUN')}")
    lines.append("")
    lines.append("Core capability vector:")
    for dim, value in q["capability_vector"].items():
        lines.append(f"    {VECTOR_LABELS.get(dim, dim):<28} {value}")
    lines.append("")
    lines.append(f"Strongest capability:")
    lines.append(f"    {VECTOR_LABELS.get(q['strongest'], q['strongest'])}")
    lines.append("")
    if q.get("blocking"):
        lines.append(f"Highest blocking deficiency:")
        lines.append(f"    {q['blocking']['detail']}")
        lines.append("")
    lines.append(f"Critical violations:")
    lines.append(f"    {q['critical_violations']}")
    lines.append("")
    lines.append(f"Trace completeness:")
    lines.append(f"    {int(q['trace_completeness'] * 100)}%")
    lines.append("")
    lines.append(f"Deterministic replay:")
    lines.append(f"    {q['replay']}")
    lines.append("")
    lines.append(f"Recommended next target:")
    lines.append(f"    {q['next_target']}")
    upgrade = q.get("estimated_upgrade") or         q.get("blocking", {}).get("recommendations", [])
    if upgrade:
        lines.append("")
        lines.append("Estimated upgrade:")
        for rec in upgrade:
            lines.append(f"    {rec}")
    if q.get("skill_profile"):
        lines.append("")
        lines.append("Skill profile (separate from core reasoning):")
        for skill, value in sorted(q["skill_profile"].items()):
            lines.append(f"    {skill:<16} {value} / 5")
    return "\n".join(lines)
