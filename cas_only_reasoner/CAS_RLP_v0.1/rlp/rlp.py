"""CAS-RLP orchestrator: the full improvement cycle above the kernel."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional

from .acceptance import decide
from .diagnosis import diagnose
from .mutations import Mutation, ProtectedTarget, apply_mutation, propose_repairs
from .sandbox import grade, replay_ok, run_suite
from .versioning import VersionHistory


class CAS_RLP:
    def __init__(self, package: Dict) -> None:
        self.original = copy.deepcopy(package)
        self.current_package = copy.deepcopy(package)
        self.history = VersionHistory(package)
        self.experience: List[Dict] = []
        self.decisions: List[Dict] = []

    # ----------------------------------------------------------------
    # R0: experience, automatic with provenance.
    def record_experience(self, problem_id: str, outcome: Dict,
                          source: str) -> Dict:
        entry = {
            "ring": "R0",
            "problem_id": problem_id,
            "outcome": outcome,
            "source": source,
            "provenance": {
                "status": outcome.get("terminal_status"),
                "trace_digest": outcome.get("trace_digest"),
            },
        }
        self.experience.append(entry)
        return entry

    def consult_experience(self, problem_id: str) -> List[Dict]:
        return [e for e in self.experience if e["problem_id"] == problem_id]

    # ----------------------------------------------------------------
    # The improvement cycle.
    def improve(self, guard_order=None, max_evaluations: Optional[int] = None) -> Dict:
        self.decisions = []
        self.evaluations_used = 0
        parent_results, _ = run_suite(self.current_package)
        parent_grades = grade(self.current_package, parent_results)
        expectations = self.current_package.get("expectations", {})

        for task in self.current_package.get("tasks", {}).get("held_out", []):
            pid = task["problem_id"]
            packet = parent_results.get(pid)
            if packet is None:
                continue
            fault = diagnose(packet, expectations.get(pid, {}))
            if fault is None:
                continue
            self.record_experience(pid, packet, "held_out_failure")
            promoted_decision = None
            for mutation in propose_repairs(fault, self.current_package,
                                            guard_order=guard_order):
                if max_evaluations is not None and \
                        self.evaluations_used >= max_evaluations:
                    self.decisions.append({
                        "verdict": "BUDGET_EXHAUSTED",
                        "mutation": mutation.to_json(),
                        "detail": (f"repair budget {max_evaluations} exhausted "
                                   f"before {mutation.mutation_id}"),
                    })
                    continue
                self.evaluations_used += 1
                # Every candidate is evaluated against the ORIGINAL parent
                # and every decision is recorded as evidence; the first
                # accepted repair wins.
                decision = self._evaluate_mutation(mutation, parent_grades)
                decision["evaluations_used"] = self.evaluations_used
                self.decisions.append(decision)
                if decision["verdict"] == "PROMOTED" and promoted_decision is None:
                    promoted_decision = decision
            if promoted_decision is not None:
                self._promote(promoted_decision)

        return self._seal_cycle()

    def _evaluate_mutation(self, mutation: Mutation,
                           parent_grades: Dict) -> Dict:
        try:
            child_package = apply_mutation(self.current_package, mutation)
        except ProtectedTarget as exc:
            return {"verdict": "REJECTED_AS_PROTECTED",
                    "mutation": mutation.to_json(),
                    "detail": str(exc),
                    "checks": [{"check": "authority_invariants",
                                "passed": False, "detail": str(exc)}]}

        child_results, _ = run_suite(child_package)
        child_grades = grade(child_package, child_results)
        ok, detail = replay_ok(child_package, child_results)
        decision = decide(self.current_package, child_package, mutation,
                          parent_grades, child_grades, ok, detail)
        decision["child_package_digest"] = VersionEntry_digest(child_package)
        decision["child_package"] = child_package
        return decision

    def _promote(self, decision: Dict) -> None:
        child_package = decision["child_package"]
        self.history.add_child(self.history.current(),
                               decision["mutation"].get("mutation_id"),
                               child_package)
        self.current_package = child_package

    def _seal_cycle(self) -> Dict:
        packet = {
            "processor_id": self.current_package.get("processor_id"),
            "parent_revision": self.original.get("revision"),
            "current_revision": self.current_package.get("revision"),
            "decisions": self.decisions,
            "version_history": self.history.snapshot_list(),
            "experience_count": len(self.experience),
            "evaluations_used": self.evaluations_used,
        }
        payload = json.dumps(packet, sort_keys=True, default=str)
        packet["cycle_digest"] = hashlib.sha256(
            payload.encode("utf-8")).hexdigest()[:16]
        return packet

    # ----------------------------------------------------------------
    def rollback(self) -> Dict:
        restored = self.history.rollback()
        self.current_package = copy.deepcopy(restored.package_snapshot)
        results, _ = run_suite(self.current_package)
        grades = grade(self.current_package, results)
        regression_ok = all(g["passed"] for g in grades.values()
                            if g["group"] == "regression")
        return {
            "action": "ROLLBACK",
            "restored_revision": restored.revision,
            "regression_ok": regression_ok,
            "digest": restored.digest,
        }


def VersionEntry_digest(package: Dict) -> str:
    payload = json.dumps(package, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
