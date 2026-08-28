"""Axioms (trusted, versioned) and procedures (learned).

Axioms are equality-preserving by definition. Procedures are learned
transformations that must be validated by the checker on every use.
The lesson library supplies the correct replacement for the known-bad
procedure square_sum.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .expr import Add, Mul, Neg, Num, Pow, Var, equal, from_json, to_json


class RuleError(Exception):
    """A rule does not match the focused node."""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    kind: str            # axiom | procedure
    note: str = ""

    def to_json(self) -> Dict:
        return {"rule_id": self.rule_id, "kind": self.kind, "note": self.note}


# --------------------------------------------------------------------------
def _navigate(expr: object, focus: Tuple[str, ...]) -> object:
    node = expr
    for step in focus:
        if isinstance(node, Add) and step.startswith("t"):
            node = node.terms[int(step[1:])]
        elif isinstance(node, Mul) and step.startswith("f"):
            node = node.factors[int(step[1:])]
        elif isinstance(node, Neg) and step == "op":
            node = node.operand
        elif isinstance(node, Pow) and step == "base":
            node = node.base
        else:
            raise RuleError(f"cannot navigate focus {focus} at {node!r}")
    return node


def _replace(expr: object, focus: Tuple[str, ...], new_node: object) -> object:
    if not focus:
        return new_node
    step, rest = focus[0], focus[1:]
    if isinstance(expr, Add) and step.startswith("t"):
        idx = int(step[1:])
        terms = list(expr.terms)
        terms[idx] = _replace(terms[idx], rest, new_node)
        return Add(tuple(terms))
    if isinstance(expr, Mul) and step.startswith("f"):
        idx = int(step[1:])
        factors = list(expr.factors)
        factors[idx] = _replace(factors[idx], rest, new_node)
        return Mul(tuple(factors))
    if isinstance(expr, Neg) and step == "op":
        return Neg(_replace(expr.operand, rest, new_node))
    if isinstance(expr, Pow) and step == "base":
        return Pow(_replace(expr.base, rest, new_node), expr.exp)
    raise RuleError(f"cannot replace at focus {focus}")


def all_foci(expr: object, prefix: Tuple[str, ...] = ()) -> List[Tuple[str, ...]]:
    foci: List[Tuple[str, ...]] = [prefix]
    if isinstance(expr, Add):
        for i, t in enumerate(expr.terms):
            foci.extend(all_foci(t, prefix + (f"t{i}",)))
    elif isinstance(expr, Mul):
        for i, f in enumerate(expr.factors):
            foci.extend(all_foci(f, prefix + (f"f{i}",)))
    elif isinstance(expr, Neg):
        foci.extend(all_foci(expr.operand, prefix + ("op",)))
    elif isinstance(expr, Pow):
        foci.extend(all_foci(expr.base, prefix + ("base",)))
    return foci


# --------------------------------------------------------------------------
def apply_rule(rule_id: str, expr: object, focus: Tuple[str, ...]) -> object:
    """Apply a named rule at a focus; raises RuleError on mismatch."""
    node = _navigate(expr, focus)
    if rule_id == "commute_add":
        if isinstance(node, Add) and len(node.terms) >= 2:
            terms = list(node.terms)
            terms[0], terms[1] = terms[1], terms[0]
            return _replace(expr, focus, Add(tuple(terms)))
        raise RuleError("commute_add needs an Add with two terms")
    if rule_id == "associate_add":
        if isinstance(node, Add) and len(node.terms) == 2 and \
                isinstance(node.terms[1], Add):
            a, inner = node.terms[0], node.terms[1]
            return _replace(expr, focus, Add((Add((a, inner.terms[0])),
                                             *inner.terms[1:])))
        raise RuleError("associate_add needs a+(b+c)")
    if rule_id == "distribute":
        if isinstance(node, Mul) and len(node.factors) == 2:
            f0, f1 = node.factors
            if isinstance(f0, Add):
                return _replace(expr, focus,
                                Add(tuple(Mul((f0.terms[i], f1))
                                          for i in range(len(f0.terms)))))
            if isinstance(f1, Add):
                return _replace(expr, focus,
                                Add(tuple(Mul((f0, f1.terms[i]))
                                          for i in range(len(f1.terms)))))
        raise RuleError("distribute needs a*(b+c)")
    if rule_id == "square_expand":
        if isinstance(node, Pow) and node.exp == 2 and isinstance(node.base, Add) \
                and len(node.base.terms) == 2:
            a, b = node.base.terms
            return _replace(expr, focus, Add((Pow(a, 2),
                                              Mul((Num(Fraction(2)), a, b)),
                                              Pow(b, 2))))
        raise RuleError("square_expand needs (a+b)^2")
    if rule_id == "square_sum":
        # The LEARNED, INCORRECT procedure: (a+b)^2 -> a^2 + b^2.
        if isinstance(node, Pow) and node.exp == 2 and isinstance(node.base, Add) \
                and len(node.base.terms) == 2:
            a, b = node.base.terms
            return _replace(expr, focus, Add((Pow(a, 2), Pow(b, 2))))
        raise RuleError("square_sum needs (a+b)^2")
    raise RuleError(f"unknown rule {rule_id}")


AXIOM_IDS = {"commute_add", "associate_add", "distribute", "square_expand"}
PROCEDURE_IDS = {"square_sum"}


def kind_of(rule_id: str) -> str:
    if rule_id in AXIOM_IDS:
        return "axiom"
    if rule_id in PROCEDURE_IDS:
        return "procedure"
    raise RuleError(f"unknown rule {rule_id}")
