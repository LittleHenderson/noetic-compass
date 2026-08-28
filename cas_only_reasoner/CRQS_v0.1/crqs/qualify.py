"""The qualifier: manifest -> the five CRQS outputs.

TDG (per task), CAS-G (design ceiling / demonstrated / qualified),
CV (capability vector), E-Tier, A-Level. Strict sequential gating:
a level requires EVERY lower level, so missing tool use caps the
machine at CAS-G6 even when adaptive-learning and self-improvement
components exist. That is the standard working as designed: no
topology medals.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .authority import validate as validate_authority
from .difficulty import grade_task
from .evidence import EVIDENCE_CEILING, tier_from_manifest
from .gates import (gates_pass, hard_gate_violations,
                    performance_gate_failures)
from .generations import GENERATIONS, generation, index_of, next_level
from .repair import MISSING_TOOL_RECOMMENDATIONS, upgrade_path
from .vector import compute_vector, strongest, weakest

# Required topology flags per generation (strict sequential: G_n needs
# all requirements of G_1..G_n present).
REQUIREMENTS: Dict[str, List[str]] = {
    "CAS-G0": [],
    "CAS-G1": ["cjt"],
    "CAS-G2": ["cascade", "trace_replay"],
    "CAS-G3": ["inference"],
    "CAS-G4": ["branches", "cdab", "commitment_latch", "rollback"],
    "CAS-G5": ["working_memory", "episodic_memory", "provenance",
               "lacunarity"],
    "CAS-G6": ["rpm_stack"],
    "CAS-G7": ["typed_uncertainty", "tools", "budget_management",
               "adversarial_suite"],
    "CAS-G8": ["learning_writeback", "procedural_learning"],
    "CAS-G9": ["self_improvement"],
    "CAS-G10": ["language", "mathematics", "long_term_goals", "self_model"],
}


def design_ceiling(manifest: Dict) -> str:
    topology = manifest.get("topology", {})
    level = "CAS-G0"
    for gen in GENERATIONS:
        if gen["level"] == "CAS-GΩ":
            continue
        required = REQUIREMENTS.get(gen["level"], [])
        if all(topology.get(flag) for flag in required):
            level = gen["level"]
        else:
            break
    return level


def _demonstration_grades(manifest: Dict) -> Dict[str, int]:
    grades: Dict[str, int] = {}
    for demo in manifest.get("demonstrations", []):
        if demo.get("passed"):
            key = "stable" if demo.get("stable") else "peak"
            grades[key] = max(grades.get(key, 0),
                              int(demo["difficulty_grade"][1:]))
    return grades


def demonstrated_level(manifest: Dict) -> Dict:
    grades = _demonstration_grades(manifest)
    stable = grades.get("stable", 0)
    peak = grades.get("peak", 0)
    # Strict sequential gate: the demonstrated generation is the highest
    # generation whose ENTIRE suite (and every lower one) is evidenced.
    suites = {s.get("name") for s in manifest.get("evidence", {}).get("suites", [])}
    level = "CAS-G0"
    for gen in GENERATIONS:
        if gen["level"] == "CAS-GΩ":
            continue
        gate = f"suite_{gen['level']}"
        if gate in suites or index_of(gen["level"]) <= 0:
            level = gen["level"]
        else:
            break
    # A demonstrated difficulty also gates the generation: D_n roughly
    # corresponds to G_n.
    demonstrated = min(index_of(level), stable)
    return {
        "level": f"CAS-G{demonstrated}",
        "stable_difficulty": f"D{stable}",
        "peak_difficulty": f"D{peak}" if peak > stable else None,
    }


def evidence_ceiling(manifest: Dict) -> str:
    tier = tier_from_manifest(manifest)
    return EVIDENCE_CEILING[tier]


def qualified_level(manifest: Dict) -> str:
    ceiling = design_ceiling(manifest)
    demonstrated = demonstrated_level(manifest)["level"]
    evidence = evidence_ceiling(manifest)
    levels = [ceiling, demonstrated, evidence]
    return min(levels, key=index_of)


def qualify(manifest: Dict) -> Dict:
    if not validate_authority(manifest.get("authority", "")):
        raise ValueError("manifest authority level invalid")

    ceiling = design_ceiling(manifest)
    demonstrated = demonstrated_level(manifest)
    evidence_tier = tier_from_manifest(manifest)
    qualified = qualified_level(manifest)
    vector = compute_vector(manifest)
    evidence = manifest.get("evidence", {})
    gates_ok = gates_pass(evidence)

    violations = hard_gate_violations(evidence)
    perf_failures = performance_gate_failures(evidence)

    blocking: Dict = {}
    if not gates_ok:
        qualified = "CAS-G0"
        blocking = {"kind": "hard gate", "detail": violations + perf_failures}
    elif not manifest.get("topology", {}).get("tools"):
        blocking = {
            "kind": "missing prerequisite machinery",
            "detail": "no tool-use layer: the strict G7 gate is unmet",
            "recommendations": MISSING_TOOL_RECOMMENDATIONS,
            "next_target": "CAS-G7",
        }

    next_target = blocking.get("next_target",
                               next_level(qualified.split(" /")[0]))
    # The estimated upgrade is always DERIVED from the manifest, so the
    # section-10 report names concrete steps even when nothing blocks.
    if blocking.get("recommendations"):
        upgrade = blocking["recommendations"]
    else:
        upgrade = upgrade_path(manifest, next_target, REQUIREMENTS)

    return {
        "mind_id": manifest.get("mind_id"),
        "board_version": manifest.get("board_version"),
        "compiler": manifest.get("compiler", "not integrated"),
        "runtime": manifest.get("runtime"),
        "qualified_level": f"{qualified} / {evidence_tier} / "
                           f"{manifest.get('authority')}",
        "design_ceiling": ceiling,
        "demonstrated": demonstrated,
        "evidence_tier": evidence_tier,
        "authority": manifest.get("authority"),
        "rmb": manifest.get("rmb", {"status": "NOT RUN"}),
        "capability_vector": vector,
        "strongest": strongest(vector),
        "weakest_dimensions": weakest(vector),
        "critical_violations": len(violations),
        "violations": violations,
        "performance_failures": perf_failures,
        "trace_completeness": evidence.get("trace_completeness", 0.0),
        "replay": "PASS" if evidence.get("replay_equivalence", 0.0) >= 1.0
                  else "FAIL",
        "blocking": blocking,
        "next_target": next_target,
        "estimated_upgrade": upgrade,
        "skill_profile": manifest.get("skill_profile", {}),
    }
