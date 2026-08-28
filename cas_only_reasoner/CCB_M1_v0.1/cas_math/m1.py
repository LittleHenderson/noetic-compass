"""CCB-M1 orchestrator: evaluate, prove, refute, learn, promote.

CAS governs the search; the trusted checker decides validity; repairs
are promoted only under the acceptance law, with versioned rulesets
and rollback preserved.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional, Tuple

from .acceptance import decide_math
from .checker import CheckOutcome, check
from .counterexample import find_counterexample
from .exact import q_str, relation_holds
from .expr import equal, eval_at, from_json, to_json
from .lessons import diagnose, propose_repairs
from .prover import search


def _digest(obj: Dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class CCB_M1:
    def __init__(self, package: Dict) -> None:
        self.original = copy.deepcopy(package)
        self.package = copy.deepcopy(package)
        self.history: List[Dict] = [{
            "revision": package.get("revision", 1),
            "package_digest": _digest(package),
            "ruleset": copy.deepcopy(package.get("ruleset", {})),
        }]
        self.decisions: List[Dict] = []

    # ------------------------------------------------------------------
    def ruleset_of(self, pkg: Optional[Dict] = None) -> Dict:
        pkg = pkg or self.package
        rs = pkg.get("ruleset", {})
        return {"axioms": list(rs.get("axioms", [])),
                "procedures": list(rs.get("procedures", []))}

    def all_rule_ids(self, pkg: Optional[Dict] = None) -> List[str]:
        rs = self.ruleset_of(pkg)
        return rs["axioms"] + rs["procedures"]

    # ------------------------------------------------------------------
    def evaluate(self, task: Dict) -> Dict:
        expr = from_json(task["expression"])
        env = {name: _parse(value) for name, value in task.get("env", {}).items()}
        value = eval_at(expr, env)
        result = {"task_id": task.get("task_id"),
                  "kind": "evaluate",
                  "value": q_str(value),
                  "expected": task.get("expected")}
        result["passed"] = result["value"] == task.get("expected")
        return result

    def verify_identity(self, task: Dict, pkg: Optional[Dict] = None) -> Dict:
        premise = from_json(task["premise"])
        target = from_json(task["target"])
        steps: List[Dict] = []
        if task.get("kind") == "prove":
            # A task may constrain the strategy space ("prove it by
            # expansion, not by commuting"); unavailable rules are
            # simply absent from the search.
            allowed = task.get("allowed_rules")
            if allowed is not None:
                rule_ids = [r for r in allowed if r in self.all_rule_ids(pkg)]
            else:
                rule_ids = self.all_rule_ids(pkg)
            found = search(premise, target, rule_ids, max_depth=4)
            steps = found if found is not None else []
        outcome = check(premise, target, steps)
        expected = task.get("expected", "VERIFIED")
        result = {
            "task_id": task.get("task_id"),
            "kind": task.get("kind"),
            "steps": steps,
            "outcome": outcome.to_json(),
            "expected": expected,
        }
        if expected == "VERIFIED":
            result["passed"] = (outcome.verdict == "VERIFIED"
                                and (not task.get("require_proof_steps")
                                     or bool(steps)))
        elif expected == "REJECTED":
            result["passed"] = outcome.verdict == "REJECTED"
        elif expected == "NO_PROOF":
            result["passed"] = not steps and outcome.verdict == "REJECTED"
        else:
            result["passed"] = False
        return result

    def refute(self, task: Dict) -> Dict:
        result = find_counterexample(task["statement"])
        expect_ce = task.get("expect_counterexample", True)
        result["task_id"] = task.get("task_id")
        result["passed"] = (result["found"] == expect_ce)
        if expect_ce and task.get("expected_point") is not None:
            result["passed"] = result["passed"] and \
                result.get("point", {}) == task["expected_point"]
        return result

    # ------------------------------------------------------------------
    def run_task(self, task: Dict, pkg: Optional[Dict] = None) -> Dict:
        if task.get("kind") == "evaluate":
            return self.evaluate(task)
        if task.get("kind") == "refute":
            return self.refute(task)
        return self.verify_identity(task, pkg)

    def run_suite(self, tasks: List[Dict], pkg: Optional[Dict] = None,
                  group: str = "") -> Dict:
        grades: Dict[str, Dict] = {}
        for task in tasks:
            result = self.run_task(task, pkg)
            grades[task.get("task_id")] = {
                "group": group,
                "passed": result.get("passed", False),
                "result": result,
            }
        return grades

    # ------------------------------------------------------------------
    def mistake_cycle(self, mistake_task: Dict) -> Dict:
        self.decisions = []
        pkg = self.package
        attempt = self.verify_identity(mistake_task, pkg)
        if attempt["outcome"]["verdict"] != "REJECTED":
            raise RuntimeError(
                f"mistake cycle requires a rejected attempt, got "
                f"{attempt['outcome']['verdict']}")

        outcome = CheckOutcome(
            attempt["outcome"]["verdict"],
            attempt["outcome"]["first_invalid_step"],
            attempt["outcome"]["reason"],
            attempt["outcome"].get("sample_witness"))
        fault = diagnose(outcome, attempt["steps"])

        parent_regression = self.run_suite(
            pkg.get("regression", []), pkg, group="regression")
        parent_held = self.run_suite(pkg.get("held_out", []), pkg,
                                     group="held_out")
        parent_grades = {**parent_regression, **parent_held}

        promoted_decision: Optional[Dict] = None
        for repair in propose_repairs(fault):
            child = self._build_descendant(repair)
            child_regression = self.run_suite(
                child.get("regression", []), child, group="regression")
            child_held = self.run_suite(child.get("held_out", []), child,
                                        group="held_out")
            child_grades = {**child_regression, **child_held}
            decision = decide_math(pkg, child, repair,
                                   parent_grades, child_grades)
            decision["fault"] = fault.to_json()
            self.decisions.append(decision)
            if decision["verdict"] == "PROMOTED" and promoted_decision is None:
                promoted_decision = decision
                promoted_decision["child_package"] = child

        if promoted_decision is not None:
            child = promoted_decision["child_package"]
            self.history.append({
                "revision": child.get("revision"),
                "package_digest": _digest(child),
                "ruleset": copy.deepcopy(child.get("ruleset", {})),
            })
            self.package = child

        return self._seal_cycle(attempt, fault)

    def _build_descendant(self, repair: Dict) -> Dict:
        if repair.get("kind") != "replace_rule":
            raise ValueError(f"unknown repair kind {repair.get('kind')}")
        child = copy.deepcopy(self.package)
        child["revision"] = self.package.get("revision", 1) + 1
        child["parent_revision"] = self.package.get("revision", 1)
        removed = repair["rule_id"]
        child["ruleset"]["procedures"] = [
            r for r in child["ruleset"].get("procedures", []) if r != removed]
        replacement = repair["replacement"]
        if replacement not in child["ruleset"].get("axioms", []):
            child["ruleset"].setdefault("axioms", []).append(replacement)
        child["last_repair"] = repair
        return child

    def _seal_cycle(self, attempt: Dict, fault) -> Dict:
        packet = {
            "math_package_id": self.package.get("math_package_id"),
            "parent_revision": self.original.get("revision"),
            "current_revision": self.package.get("revision"),
            "attempt_outcome": attempt["outcome"],
            "fault": fault.to_json(),
            "decisions": self.decisions,
            "history": self.history,
        }
        packet["cycle_digest"] = _digest(packet)
        return packet

    # ------------------------------------------------------------------
    def rollback(self) -> Dict:
        if len(self.history) <= 1:
            return {"action": "ROLLBACK", "restored_revision":
                    self.package.get("revision"), "note": "nothing to restore"}
        parent = self.history[0]
        self.package = copy.deepcopy(self.original)
        return {
            "action": "ROLLBACK",
            "restored_revision": parent["revision"],
            "package_digest": parent["package_digest"],
        }


def _parse(text: str):
    from .exact import parse_q
    return parse_q(text)
