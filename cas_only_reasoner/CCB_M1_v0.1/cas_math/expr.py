"""The expression IR: variables, exact numbers, add, mul, pow, neg.

Canonical form: every expression expands to a dict mapping a sorted
monomial (tuple of (var, exponent) pairs) to an exact rational
coefficient. Polynomial identity over exact rationals is decided
exactly by canonical equality - sound and complete for that class.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .exact import parse_q

Monomial = Tuple[Tuple[str, int], ...]
Canonical = Dict[Monomial, Fraction]


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Num:
    q: Fraction


@dataclass(frozen=True)
class Neg:
    operand: "Expr"


@dataclass(frozen=True)
class Add:
    terms: Tuple["Expr", ...]


@dataclass(frozen=True)
class Mul:
    factors: Tuple["Expr", ...]


@dataclass(frozen=True)
class Pow:
    base: "Expr"
    exp: int


Expr = object  # typing alias placeholder; real union is the classes above


def from_json(node: Dict) -> object:
    kind = node["kind"]
    if kind == "var":
        return Var(node["name"])
    if kind == "num":
        return Num(parse_q(node["q"]))
    if kind == "neg":
        return Neg(from_json(node["operand"]))
    if kind == "add":
        return Add(tuple(from_json(t) for t in node["terms"]))
    if kind == "mul":
        return Mul(tuple(from_json(f) for f in node["factors"]))
    if kind == "pow":
        return Pow(from_json(node["base"]), int(node["exp"]))
    raise ValueError(f"unknown expr kind {kind}")


def to_json(expr: object) -> Dict:
    if isinstance(expr, Var):
        return {"kind": "var", "name": expr.name}
    if isinstance(expr, Num):
        q = expr.q
        text = str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"
        return {"kind": "num", "q": text}
    if isinstance(expr, Neg):
        return {"kind": "neg", "operand": to_json(expr.operand)}
    if isinstance(expr, Add):
        return {"kind": "add", "terms": [to_json(t) for t in expr.terms]}
    if isinstance(expr, Mul):
        return {"kind": "mul", "factors": [to_json(f) for f in expr.factors]}
    if isinstance(expr, Pow):
        return {"kind": "pow", "base": to_json(expr.base), "exp": expr.exp}
    raise ValueError(f"unknown expr object {expr!r}")


def str_of(expr: object) -> str:
    import json
    return json.dumps(to_json(expr), sort_keys=True)


def _merge_monomials(left: Canonical, right: Canonical) -> Canonical:
    out: Canonical = {}
    for m, c in list(left.items()) + list(right.items()):
        out[m] = out.get(m, Fraction(0)) + c
    return {m: c for m, c in out.items() if c != 0}


def _negate(c: Canonical) -> Canonical:
    return {m: -v for m, v in c.items() if v != 0}


def _multiply(left: Canonical, right: Canonical) -> Canonical:
    out: Canonical = {}
    for m1, c1 in left.items():
        for m2, c2 in right.items():
            merged = _merge_monomial(m1, m2)
            out[merged] = out.get(merged, Fraction(0)) + c1 * c2
    return {m: c for m, c in out.items() if c != 0}


def _merge_monomial(m1: Monomial, m2: Monomial) -> Monomial:
    powers: Dict[str, int] = {}
    for var, exp in list(m1) + list(m2):
        powers[var] = powers.get(var, 0) + exp
    return tuple(sorted((v, e) for v, e in powers.items() if e != 0))


def canonical(expr: object) -> Canonical:
    if isinstance(expr, Var):
        return {((expr.name, 1),): Fraction(1)}
    if isinstance(expr, Num):
        return {(): expr.q} if expr.q != 0 else {}
    if isinstance(expr, Neg):
        return _negate(canonical(expr.operand))
    if isinstance(expr, Add):
        out: Canonical = {}
        for term in expr.terms:
            out = _merge_monomials(out, canonical(term))
        return out
    if isinstance(expr, Mul):
        out: Canonical = {(): Fraction(1)}
        for factor in expr.factors:
            out = _multiply(out, canonical(factor))
        return out
    if isinstance(expr, Pow):
        if expr.exp < 0:
            raise ValueError("negative exponents are not supported in v0.1")
        out: Canonical = {(): Fraction(1)}
        base = canonical(expr.base)
        for _ in range(expr.exp):
            out = _multiply(out, base)
        return out
    raise ValueError(f"cannot canonicalize {expr!r}")


def equal(left: object, right: object) -> bool:
    return canonical(left) == canonical(right)


def eval_at(expr: object, env: Dict[str, Fraction]) -> Fraction:
    if isinstance(expr, Var):
        if expr.name not in env:
            raise KeyError(f"variable {expr.name} not bound")
        return env[expr.name]
    if isinstance(expr, Num):
        return expr.q
    if isinstance(expr, Neg):
        return -eval_at(expr.operand, env)
    if isinstance(expr, Add):
        total = Fraction(0)
        for term in expr.terms:
            total += eval_at(term, env)
        return total
    if isinstance(expr, Mul):
        total = Fraction(1)
        for factor in expr.factors:
            total *= eval_at(factor, env)
        return total
    if isinstance(expr, Pow):
        return eval_at(expr.base, env) ** expr.exp
    raise ValueError(f"cannot evaluate {expr!r}")


def variables(expr: object) -> List[str]:
    found: List[str] = []
    if isinstance(expr, Var):
        found.append(expr.name)
    elif isinstance(expr, Neg):
        found.extend(variables(expr.operand))
    elif isinstance(expr, Add):
        for t in expr.terms:
            found.extend(variables(t))
    elif isinstance(expr, Mul):
        for f in expr.factors:
            found.extend(variables(f))
    elif isinstance(expr, Pow):
        found.extend(variables(expr.base))
    return sorted(set(found))
