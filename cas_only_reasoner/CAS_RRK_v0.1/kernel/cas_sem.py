"""CAS-Sem v0.1: the minimal content and inference model.

Propositions, rules, pattern matching, backward chaining, and the four
evidence statuses. INFER produces SUPPORTED conclusions only along a
complete proof path; the transaction coordinator re-proves every claimed
inference (the proof kernel decides validity).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .schemas import Proposition, Rule


def is_var(token: str) -> bool:
    return token.startswith("?")


def is_ground(prop: Proposition) -> bool:
    return not any(is_var(a) for a in prop.args)


def match(pattern: Proposition, fact: Proposition,
          bindings: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    if bindings is None:
        bindings = {}
    if pattern.pred != fact.pred:
        return None
    if len(pattern.args) != len(fact.args):
        return None
    extended = dict(bindings)
    for p_token, f_token in zip(pattern.args, fact.args):
        if is_var(p_token):
            if p_token in extended and extended[p_token] != f_token:
                return None
            extended[p_token] = f_token
        elif p_token != f_token:
            return None
    return extended


def instantiate(prop: Proposition, bindings: Dict[str, str]) -> Proposition:
    return Proposition(prop.pred, tuple(bindings.get(a, a) for a in prop.args))


def opposite(prop: Proposition) -> Proposition:
    if prop.pred.startswith("not_"):
        return Proposition(prop.pred[4:], prop.args)
    return Proposition("not_" + prop.pred, prop.args)


def _prove(goal: Proposition, bindings: Dict[str, str],
           props: List[Proposition], rules: List[Rule],
           used_rules: List[str], used_premises: List[Proposition],
           depth: int, max_depth: int,
           seen: Set[Tuple[str, Tuple[str, ...]]]) -> Optional[Dict[str, str]]:
    if depth > max_depth:
        return None
    g = instantiate(goal, bindings)
    for fact in props:
        b = match(g, fact, bindings)
        if b is not None:
            used_premises.append(fact)
            return b
    for rule in rules:
        b = match(rule.conclusion, g)
        if b is None:
            continue
        current = dict(b)
        guard = (rule.rule_id, g.args)
        if guard in seen:
            continue
        seen.add(guard)
        rl, fl = len(used_rules), len(used_premises)
        ok = True
        for prem in rule.premises:
            r = _prove(prem, current, props, rules, used_rules, used_premises,
                       depth + 1, max_depth, seen)
            if r is None:
                ok = False
                break
            current = r
        seen.discard(guard)
        if ok:
            used_rules.append(rule.rule_id)
            return current
        del used_rules[rl:]
        del used_premises[fl:]
    return None


class Proof:
    def __init__(self, success: bool, rules_used: List[str],
                 premises_used: List[Proposition]) -> None:
        self.success = success
        self.rules_used = rules_used
        self.premises_used = premises_used


def prove(goal: Proposition, props: List[Proposition], rules: List[Rule],
          max_depth: int = 8) -> Proof:
    used_rules: List[str] = []
    used_premises: List[Proposition] = []
    bindings = _prove(goal, {}, props, rules, used_rules, used_premises,
                      0, max_depth, set())
    if bindings is None:
        return Proof(False, [], [])
    return Proof(True, used_rules, used_premises)


def evidence(target: Proposition, props: List[Proposition],
             rules: List[Rule]) -> Tuple[str, Optional[Proof]]:
    """The four evidence statuses, with the proof when one exists."""
    proof = prove(target, props, rules)
    opp_proof = prove(opposite(target), props, rules)
    if proof.success and opp_proof.success:
        return "CONTRADICTED", proof
    if proof.success:
        return "SUPPORTED", proof
    if opp_proof.success:
        return "FALSIFIED", opp_proof
    return "UNSUPPORTED", None
