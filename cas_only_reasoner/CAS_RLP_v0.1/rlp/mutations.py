"""Candidate mutations and their ring classification.

A mutation is a typed, versioned change to CONTENT (rules, parameters),
never to the kernel. Ring R3 targets are rejected before sandboxing.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict, List, Optional

from .diagnosis import FaultRecord

R3_PROTECTED = [
    "kernel", "sole_writer", "proof_checker", "trace_integrity",
    "benchmarks", "expectations", "rollback", "authority",
]


class ProtectedTarget(Exception):
    """Raised when a mutation targets the protected set (ring R3)."""


@dataclass
class Mutation:
    mutation_id: str
    ring: str                  # R0 | R1 | R2 | R3
    target: str                # rule id, parameter name, or protected name
    change: Dict               # {"kind": "restrict_rule", "guard": "gt", ...}
    note: str = ""

    def to_json(self) -> Dict:
        return {
            "mutation_id": self.mutation_id,
            "ring": self.ring,
            "target": self.target,
            "change": self.change,
            "note": self.note,
        }


# The NEUTRAL candidate pool: every comparison predicate the runtime
# knows, in alphabetical order. Deliberately free of domain knowledge -
# an unstrategic searcher tries eq first and burns budget. The ORDER
# that repairs a fault class within budget is exactly what procedural
# learning must supply; the causal ablation (no strategy -> budget
# exhausted) depends on this pool staying neutral.
DEFAULT_GUARD_POOL = ("eq", "gt", "lt")


def _magnitude_args(package: Dict, rule_id: str) -> List[str]:
    """The guard's variables, extracted STRUCTURALLY from the guilty
    rule: the two same-predicate binary premises carry the magnitudes,
    ordered to align with the conclusion's entity order - so the repair
    transfers to rules with different predicate and variable names or
    reordered premises."""
    for group in ("regression", "held_out"):
        for task in package.get("tasks", {}).get(group, []):
            for rule in task.get("rules", []):
                if rule.get("rule_id") != rule_id:
                    continue
                premises = rule.get("premises", [])
                by_pred: Dict[str, List[Dict]] = {}
                for prem in premises:
                    if len(prem.get("args", [])) == 2:
                        by_pred.setdefault(prem.get("pred"), []).append(prem)
                concl_args = rule.get("conclusion", {}).get("args", [])
                for prems in by_pred.values():
                    if len(prems) != 2 or len(concl_args) != 2:
                        continue
                    entity_to_mag = {prem["args"][0]: prem["args"][1]
                                     for prem in prems}
                    if set(entity_to_mag) == set(concl_args):
                        return [entity_to_mag[concl_args[0]],
                                entity_to_mag[concl_args[1]]]
    return ["?Hx", "?Hy"]


def propose_repairs(fault: FaultRecord, package: Dict,
                     guard_order=None) -> List[Mutation]:
    """Turn a classified fault into a bounded set of candidate repairs.

    guard_order is the STRATEGY: the order in which candidate guards are
    tried. Procedural learning (ring R1) learns which order fits the
    repair budget for a fault class. Without a strategy the pool is
    DEFAULT_GUARD_POOL - neutral, alphabetical, unstrategic.
    """
    repairs: List[Mutation] = []
    if fault.classification == "overgeneral_rule":
        guards = list(guard_order or DEFAULT_GUARD_POOL)
        for i, rule_id in enumerate(sorted(set(fault.guilty_rules)), start=1):
            guard_args = _magnitude_args(package, rule_id)
            for guard in guards:
                repairs.append(Mutation(
                    mutation_id=f"restrict_{rule_id}_{guard}",
                    ring="R1",
                    target=rule_id,
                    change={"kind": "restrict_rule",
                            "guard_pred": guard,
                            "guard_args": guard_args},
                    note=(f"add {guard} guard to {rule_id} "
                          f"(candidate repair {i})"),
                ))
    elif fault.classification == "missing_rule":
        # v0.1: no autonomous rule invention from nothing; a curriculum or
        # external teacher must supply the candidate. Honest emptiness.
        pass
    return repairs


def apply_mutation(package: Dict, mutation: Mutation) -> Dict:
    """Build the descendant package. Raises ProtectedTarget for R3."""
    if mutation.ring == "R3" or any(
            mutation.target == p or mutation.target.startswith(p + ".")
            for p in R3_PROTECTED):
        raise ProtectedTarget(
            f"mutation {mutation.mutation_id} targets protected set: "
            f"{mutation.target}")
    child = copy.deepcopy(package)
    child["revision"] = package.get("revision", 0) + 1
    child["parent_revision"] = package.get("revision", 0)
    child["last_mutation"] = mutation.to_json()

    if mutation.change.get("kind") == "restrict_rule":
        guard_pred = mutation.change["guard_pred"]
        guard_args = mutation.change.get("guard_args", [])
        guard = {"pred": guard_pred, "args": list(guard_args)}
        for group in ("regression", "held_out"):
            for task in child.get("tasks", {}).get(group, []):
                new_rules = []
                for rule in task.get("rules", []):
                    if rule.get("rule_id") == mutation.target:
                        new_rules.append({
                            "rule_id": rule["rule_id"] + "_v" + str(child["revision"]),
                            "premises": rule.get("premises", []) + [guard],
                            "conclusion": rule["conclusion"],
                            "source": "rlp:" + mutation.mutation_id,
                        })
                    else:
                        new_rules.append(rule)
                task["rules"] = new_rules
        return child

    if mutation.change.get("kind") == "param_change":
        child.setdefault("parameters", {})[mutation.target] = mutation.change["value"]
        return child

    raise ValueError(f"unknown mutation kind {mutation.change.get('kind')}")
