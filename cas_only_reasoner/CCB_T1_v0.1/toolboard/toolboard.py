"""CCB-T1 orchestrator: kernel -> typed need -> tool -> kernel again."""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_KERNEL = os.path.join(_CAS_ONLY, "CAS_RRK_v0.1")
if _KERNEL not in sys.path:
    sys.path.insert(0, _KERNEL)

from kernel.kernel import CAS_RRK  # noqa: E402

from .intent import execute  # noqa: E402
from .tools import (AmbiguousToolNeed, ContraToolResult,  # noqa: E402
                    ToolBudgetExhausted, ToolError, ToolFailure,
                    ToolPermissionDenied, ToolProvenanceViolation,
                    ToolRegistry, ToolUnknown)


def _facts_of(problem: Dict) -> List[Dict]:
    return list(problem.get("propositions", []))


def _match(pattern: Dict, fact: Dict, bindings: Dict) -> Optional[Dict]:
    if pattern.get("pred") != fact.get("pred"):
        return None
    if len(pattern.get("args", [])) != len(fact.get("args", [])):
        return None
    extended = dict(bindings)
    for p, f in zip(pattern.get("args", []), fact.get("args", [])):
        if str(p).startswith("?"):
            if p in extended and extended[p] != f:
                return None
            extended[p] = f
        elif p != f:
            return None
    return extended


def _instantiate(pattern: Dict, bindings: Dict) -> Dict:
    return {"pred": pattern.get("pred"),
            "args": [bindings.get(a, a) for a in pattern.get("args", [])]}


def _needs_of(problem: Dict) -> List[Dict]:
    """The first typed missing needs, derived from the rules.

    A premise is covered when its predicate appears among the facts or
    is derivable (it is some rule's conclusion). The first uncovered
    premise, instantiated against the facts, is the tool need.
    """
    facts = _facts_of(problem)
    fact_preds = {f.get("pred") for f in facts}
    conclusion_preds = {r.get("conclusion", {}).get("pred")
                        for r in problem.get("rules", [])}
    needs: List[Dict] = []
    for rule in problem.get("rules", []):
        bindings: Dict = {}
        used: List[Dict] = []
        for prem in rule.get("premises", []):
            chosen = None
            # Prefer facts not already used by an earlier premise, so
            # distinct variables bind to distinct entities.
            for fact in facts:
                if fact in used:
                    continue
                b = _match(prem, fact, bindings)
                if b is not None:
                    chosen = b
                    used.append(fact)
                    break
            if chosen is None:
                for fact in facts:
                    b = _match(prem, fact, bindings)
                    if b is not None:
                        chosen = b
                        break
            if chosen is not None:
                bindings = chosen
        for prem in rule.get("premises", []):
            instantiated = _instantiate(prem, bindings)
            covered = (instantiated["pred"] in fact_preds
                       or instantiated["pred"] in conclusion_preds)
            if not covered and instantiated not in needs:
                needs.append(instantiated)
    return needs


class CCB_T1:
    def __init__(self, problem: Dict, registry: Optional[ToolRegistry] = None,
                 authority: int = 0, budget: float = 5.0) -> None:
        self.problem = dict(problem)
        self.registry = registry
        self.authority = authority
        self.budget = budget
        self.remaining = budget
        self.tool_records: List[Dict] = []
        self.packets: List[Dict] = []

    # Every tool fault becomes a TYPED terminal status of the board -
    # a halt, never a crash and never a fabricated continuation.
    FAULT_STATUS = {
        ToolPermissionDenied: "TOOL_PERMISSION_DENIED",
        ToolBudgetExhausted: "TOOL_BUDGET_EXHAUSTED",
        ToolProvenanceViolation: "TOOL_PROVENANCE_VIOLATION",
        ContraToolResult: "CONTRA_TOOL_RESULT",
        AmbiguousToolNeed: "AMBIGUOUS_TOOL_NEED",
        ToolUnknown: "TOOL_UNKNOWN",
        ToolFailure: "TOOL_FAILURE",
    }

    def _result(self, packet: Dict, status: Optional[str] = None,
                fault: Optional[str] = None) -> Dict:
        return {
            "terminal_status": status or packet.get("terminal_status"),
            "conclusion": packet.get("conclusion"),
            "fault": fault,
            "packets": self.packets,
            "tool_records": self.tool_records,
            "budget_remaining": self.remaining,
            "kernel_final_hash": packet.get("final_state_hash"),
        }

    def run(self) -> Dict:
        packet = CAS_RRK(self.problem, run_id="ccb_t1", seed=0).run()
        self.packets.append(packet)

        while packet.get("terminal_status") == "NEEDS_INFORMATION":
            needs = _needs_of(self.problem)
            if not needs:
                break
            # Only the FIRST missing need is served per round; ambiguity
            # or absence is typed, never improvised.
            need = needs[0]
            candidates = self.registry.match(need)
            if not candidates:
                break
            try:
                if len(candidates) > 1:
                    raise AmbiguousToolNeed(
                        f"{len(candidates)} tools match {need}")
                tool = candidates[0]
                intent = {
                    "tool": tool.name,
                    "need": need,
                    "provenance": {
                        "committed_outcome": True,
                        "sealed_trace": True,
                        "branch_id": None,
                        "problem_id": self.problem.get("problem_id"),
                    },
                }
                record = execute(intent, self.registry, self.authority,
                                 self.remaining, _facts_of(self.problem))
            except ToolError as exc:
                status = self.FAULT_STATUS.get(type(exc), "TOOL_FAILURE")
                return self._result(packet, status=status, fault=str(exc))
            self.remaining -= record["cost"]
            self.tool_records.append(record)
            # Progress guard: a round that adds no NEW fact can never
            # unblock the kernel; halt typed instead of looping.
            before = list(self.problem.get("propositions", []))
            for fact in record["result"].get("add_facts", []):
                if fact not in self.problem.setdefault("propositions", []):
                    self.problem["propositions"].append(fact)
            if self.problem.get("propositions", []) == before:
                return self._result(packet, status="NO_TOOL_PROGRESS",
                                    fault=f"tool {record['tool']} added no "
                                          f"new fact for need {need}")
            packet = CAS_RRK(self.problem, run_id="ccb_t1", seed=0).run()
            self.packets.append(packet)

        return self._result(packet)
