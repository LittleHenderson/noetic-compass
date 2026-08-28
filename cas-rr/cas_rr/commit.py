"""Phase 10: commitment - Schmitt hysteresis and the halt controller.

The commitment stage may use strong, BOUNDED gain once evidence has been
compared and thresholds crossed, so the machine can commit without
flip-flopping. Two thresholds (commit above T_high, release below T_low)
prevent chatter. The committed state is not the candidate with the highest
activation; it is the candidate that passed a sequence of typed gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .foundations import GoalFrame
from .ontology import TERMINAL


@dataclass
class GateReport:
    gate: str
    passed: bool
    detail: str

    def to_dict(self):
        return {"gate": self.gate, "passed": self.passed, "detail": self.detail}


@dataclass
class Decision:
    committed: bool
    state: str                # RELEASED | HOLD | COMMITTED
    level: float
    gates: List[GateReport]
    terminal_status: Optional[str] = None

    def to_dict(self):
        return {
            "committed": self.committed,
            "state": self.state,
            "level": round(self.level, 4),
            "gates": [g.to_dict() for g in self.gates],
            "terminal_status": self.terminal_status,
        }


class CommitmentController:
    def __init__(self, t_high: float = 0.7, t_low: float = 0.4) -> None:
        if not (0.0 < t_low < t_high <= 1.0):
            raise ValueError("need 0 < t_low < t_high <= 1")
        self.t_high = t_high
        self.t_low = t_low
        self.state = "RELEASED"
        self.level = 0.0

    def hysteresis(self, level: float) -> str:
        self.level = level
        if level >= self.t_high:
            self.state = "COMMITTED"
        elif level < self.t_low:
            self.state = "RELEASED"
        else:
            self.state = "HOLD"
        return self.state

    def evaluate_gates(self, winner, winner_target, tournament: Dict,
                       unmet_prereq: Optional[str], domains, constitution,
                       world, goal: GoalFrame, inference_map) -> List[GateReport]:
        gates: List[GateReport] = []

        if winner is not None:
            gates.append(GateReport("COMPARISON_SURVIVED", True,
                                    f"tournament winner {winner}"))
        else:
            statuses = [inference_map[c].contradiction_status
                        for c in tournament.get("candidates", [])]
            all_falsified = all(s in ("FALSIFIED", "CONTRADICTED") for s in statuses)
            gates.append(GateReport(
                "COMPARISON_SURVIVED", False,
                "no candidate survived comparison; "
                + ("all falsified" if all_falsified else "no proven candidate")))

        gates.append(GateReport(
            "PREREQUISITES_SUFFICIENT", unmet_prereq is None,
            "D/W/P all sufficient" if unmet_prereq is None
            else f"first unmet prerequisite: {unmet_prereq}"))

        if winner is not None and winner in inference_map:
            status = inference_map[winner].contradiction_status
            gates.append(GateReport(
                "NO_FATAL_CONTRADICTION", status == "NONE",
                f"winner contradiction status {status}"))
        else:
            gates.append(GateReport("NO_FATAL_CONTRADICTION", False, "no winner to check"))

        # Principled constraints: a winner tainted by a principled-violation
        # fact is inadmissible regardless of its proof.
        principled_ok = True
        taint = []
        if winner is not None and winner_target is not None:
            for fact in world.sorted_facts():
                if fact.pred in constitution.principled_preds and fact.args:
                    if winner_target.args and fact.args[0] == winner_target.args[0]:
                        principled_ok = False
                        taint.append(str(fact))
        gates.append(GateReport(
            "PRINCIPLED_CONSTRAINTS", principled_ok,
            "clean" if principled_ok else f"tainted by {taint}"))

        gates.append(GateReport(
            "POWER_GOOD", domains.O_ENABLED,
            "O enabled (P, C, E power-good)" if domains.O_ENABLED
            else "operational domain not powered"))

        return gates

    def decide(self, winner, winner_target, tournament: Dict,
               unmet_prereq: Optional[str], domains, constitution, world,
               goal: GoalFrame, inference_map, level: float) -> Decision:
        gates = self.evaluate_gates(winner, winner_target, tournament,
                                    unmet_prereq, domains, constitution, world,
                                    goal, inference_map)
        state = self.hysteresis(level)

        failed = [g for g in gates if not g.passed]
        if failed:
            gate = failed[0].gate
            terminal = self._terminal_for(gate, tournament, inference_map,
                                          unmet_prereq, goal)
            return Decision(False, state, level, gates, terminal)
        if state != "COMMITTED":
            return Decision(False, state, level, gates, None)
        return Decision(True, state, level, gates, None)

    def _terminal_for(self, gate: str, tournament: Dict, inference_map: Dict,
                      unmet_prereq: Optional[str], goal: GoalFrame) -> str:
        if gate == "PREREQUISITES_SUFFICIENT":
            if goal.kind == "subgoal":
                return {
                    "KNOWLEDGE": "NEEDS_INFORMATION",
                    "CAPABILITY": "NEEDS_CAPABILITY",
                    "DESIRE": "CONFLICT_UNRESOLVED",
                }[goal.subgoal_type or "DESIRE"]
            return {"W": "NEEDS_INFORMATION", "P": "NEEDS_CAPABILITY",
                    "D": "CONFLICT_UNRESOLVED"}[unmet_prereq or "D"]
        if gate == "NO_FATAL_CONTRADICTION":
            statuses = [v.contradiction_status for v in inference_map.values()]
            if "CONTRADICTED" in statuses:
                return "CONFLICT_UNRESOLVED"
            return "INADMISSIBLE"
        if gate == "PRINCIPLED_CONSTRAINTS":
            return "INADMISSIBLE"
        if gate == "POWER_GOOD":
            return "INADMISSIBLE"
        # COMPARISON_SURVIVED
        statuses = [v.contradiction_status for v in inference_map.values()]
        all_falsified = statuses and all(
            s in ("FALSIFIED", "CONTRADICTED") for s in statuses)
        return "INADMISSIBLE" if all_falsified else "NEEDS_INFORMATION"
