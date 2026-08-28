"""The capability ladder runner and report generator.

Runs every LADDER spec, grades it against its expected typed terminal
status and conclusion, and produces the capability report. Frontier (L6)
probes are graded on HONEST REFUSAL: NEEDS_INFORMATION is the correct
answer when the operator does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .terms import Atom

# Tier mapping covers ATTAINED capability only (L0..L5). L6 is the
# frontier: its probes are graded on honest refusal, and refusing them is
# honesty, not attainment - so L6 can never raise the tier.
TIER_NAMES = [
    ("L0", "R0"), ("L1", "R0"),
    ("L2", "R1"),
    ("L3", "R2"), ("L4", "R2"),
    ("L5", "R3"),
]


@dataclass
class LevelResult:
    level: str
    name: str
    status: str
    output: Optional[str]
    passed: bool
    ticks: int
    proof: str
    note: str

    def row(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return (f"{mark:<4} {self.level:<3} {self.name:<28} "
                f"{self.status:<22} {self.output or '-'}")

    def to_dict(self) -> Dict:
        return {
            "level": self.level, "name": self.name, "status": self.status,
            "output": self.output, "passed": self.passed, "ticks": self.ticks,
            "proof": self.proof, "note": self.note,
        }


def run_level(spec: Dict) -> LevelResult:
    from cas_rr.runtime import CASRuntime, default_constitution
    from tasks import battery

    constitution_factory = (battery._plan_constitution
                            if spec.get("constitution") == "plan"
                            else default_constitution)
    problem = spec["builder"]()

    if spec.get("protocol") == "memory":
        run1 = CASRuntime(constitution_factory(), problem).run()
        rt2 = CASRuntime(constitution_factory(), problem)
        rt2.cmb.store_atom(Atom("has", ("b", "y")), "^5", "C", "semantic",
                           "verified_memory_episode_1")
        run2 = rt2.run()
        out = run2["output"]["conclusion"] if run2["output"] else None
        passed = (run1["terminal_status"] == "NEEDS_INFORMATION"
                  and run2["terminal_status"] == spec["expected_status"]
                  and (spec["expected_output"] is None
                       or out == spec["expected_output"]))
        status = f"{run1['terminal_status']} -> {run2['terminal_status']}"
        return LevelResult(spec["level"], spec["name"], status, out, passed,
                           run2["ticks"], "", spec["note"])

    packet = CASRuntime(constitution_factory(), problem).run()
    out = packet["output"]["conclusion"] if packet["output"] else None
    passed = (packet["terminal_status"] == spec["expected_status"]
              and (spec["expected_output"] is None
                   or out == spec["expected_output"]))
    proof = ""
    if out:
        for rec in packet["inferences"].values():
            if rec["conclusion"] == out and rec["success"]:
                proof = f"rules={rec['rules_used']} premises={len(rec['premises_used'])}"
                break
    return LevelResult(spec["level"], spec["name"], packet["terminal_status"],
                       out, passed, packet["ticks"], proof, spec["note"])


def run_ladder(specs: List[Dict]) -> List[LevelResult]:
    return [run_level(s) for s in specs]


def tier_of(results: List[LevelResult]) -> str:
    """Highest tier whose levels are ALL passed, in ladder order."""
    by_level: Dict[str, List[bool]] = {}
    for r in results:
        by_level.setdefault(r.level, []).append(r.passed)
    tier = "R0"
    for level, tier_name in TIER_NAMES:
        if level in by_level and all(by_level[level]):
            tier = tier_name
        else:
            break
    return tier


def report_text(results: List[LevelResult]) -> str:
    lines = ["CAS-RR v0.1 - Capability Ladder Report",
             "=" * 60,
             "level  task                          status                output"]
    for r in results:
        lines.append(f"{r.level:<5} {r.name:<28} {r.status:<22} {r.output or '-'}")
    lines.append("-" * 60)
    frontier = [r for r in results if r.level == "L6"]
    core = [r for r in results if r.level != "L6"]
    core_passed = sum(1 for r in core if r.passed)
    frontier_honest = sum(1 for r in frontier
                          if r.passed and r.status == "NEEDS_INFORMATION")
    lines.append(f"core levels:     {core_passed}/{len(core)} passed")
    lines.append(f"frontier probes: {frontier_honest}/{len(frontier)} refused honestly")
    lines.append(f"capability tier: {tier_of(results)}")
    lines.append("")
    lines.append("Per-level detail (difficulty axes: D proof depth, B branching,")
    lines.append("C constraints, N negations, U uncertainty, M memory, R recursion):")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"  {mark} {r.level} {r.name}: {r.note}"
                     + (f" | {r.proof}" if r.proof else ""))
    return "\n".join(lines)
