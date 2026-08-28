"""Terms and rule machinery: atoms, patterns, rules, backward chaining.

Atoms are ground or patterned predicate applications. Rules are the
knowledge substrate (^5 Female) that the inference stage (^6 Male
decomposition + ^9 Below/Effect conclusion) applies. Association (^8) only
SURFACES rule conclusions as candidates; it never proves anything
(CAS-RR spec Ch. 7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional, Set, Tuple


class Atom(NamedTuple):
    pred: str
    args: Tuple[str, ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.pred
        return f"{self.pred}({','.join(self.args)})"


def is_var(token: str) -> bool:
    return token.startswith("?")


def is_ground(atom: Atom) -> bool:
    return not any(is_var(a) for a in atom.args)


def match(pattern: Atom, fact: Atom, bindings: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    """Pattern-match pattern against fact, extending bindings.

    Variables (tokens starting with ?) bind consistently; constants must be
    equal. Returns the extended bindings or None.
    """
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


def instantiate(atom: Atom, bindings: Dict[str, str]) -> Atom:
    return Atom(atom.pred, tuple(bindings.get(a, a) for a in atom.args))


def unify_conclusion(rule_conclusion: Atom, target: Atom) -> Optional[Dict[str, str]]:
    """Bind a rule conclusion's variables against a (ground) target atom."""
    return match(rule_conclusion, target)


def negated_base(atom: Atom) -> Optional[str]:
    """Convention: not_viable(X) negates viable(X). Returns the base
    predicate name, or None when the atom carries no negation marker."""
    if atom.pred.startswith("not_"):
        return atom.pred[4:]
    return None


@dataclass(frozen=True)
class Rule:
    rule_id: str
    premises: Tuple[Atom, ...]
    conclusion: Atom
    source: str
    note: str = ""


@dataclass
class ProofResult:
    success: bool
    bindings: Dict[str, str] = field(default_factory=dict)
    rules_used: List[str] = field(default_factory=list)
    facts_used: List[Atom] = field(default_factory=list)


def _prove(
    goal: Atom,
    bindings: Dict[str, str],
    facts: List[Atom],
    rules: List[Rule],
    used_rules: List[str],
    used_facts: List[Atom],
    depth: int,
    max_depth: int,
    seen: Set[Tuple[str, Tuple[str, ...]]],
) -> Optional[Dict[str, str]]:
    if depth > max_depth:
        return None
    g = instantiate(goal, bindings)

    # A fact match grounds the goal. Inherited bindings must be
    # preserved: the match extends them, it never replaces them.
    for fact in facts:
        b = match(g, fact, bindings)
        if b is not None:
            used_facts.append(fact)
            return b

    # Rule application: ^6 takes the conclusion apart into its premises,
    # each premise is proven in turn, and ^9 lands the conclusion.
    for rule in rules:
        b = unify_conclusion(rule.conclusion, g)
        if b is None:
            continue
        current = dict(b)
        guard = (rule.rule_id, g.args)
        if guard in seen:
            continue
        seen.add(guard)
        rl, fl = len(used_rules), len(used_facts)
        ok = True
        for prem in rule.premises:
            r = _prove(prem, current, facts, rules, used_rules, used_facts, depth + 1, max_depth, seen)
            if r is None:
                ok = False
                break
            r = r or {}
            current = r
        seen.discard(guard)
        if ok:
            used_rules.append(rule.rule_id)
            return current
        del used_rules[rl:]
        del used_facts[fl:]
    return None


def prove(goal: Atom, facts: List[Atom], rules: List[Rule], max_depth: int = 8) -> ProofResult:
    """Backward-chaining proof of goal from facts via rules.

    Returns the first complete proof found: bindings, the rule chain, and
    the facts consumed. Every conclusion the runtime commits therefore
    carries a full originating path (the provenance invariant).
    """
    used_rules: List[str] = []
    used_facts: List[Atom] = []
    bindings = _prove(goal, {}, facts, rules, used_rules, used_facts, 0, max_depth, set())
    if bindings is None:
        return ProofResult(False)
    return ProofResult(True, bindings, used_rules, used_facts)
