"""The mathematics student: a PERSISTENT, GATED skill store and the
solver that may use only promoted skills.

The gate is the learnable surface: the exact engine can compute
anything in its class, but the STUDENT may only use an operation,
rewrite rule, or method once the ladder promoted that skill. An
unpromoted skill yields a typed CANNOT - capability honesty, the same
law as the language board's UNSUPPORTED_LANGUAGE.

Every claimed equation solution is verified by SUBSTITUTION into the
ORIGINAL equation before it is returned - the checker's substitution
law is the sole validity authority; the solver never returns an
unverified answer.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .mathir import (Add, Mul, Neg, Num, Pow, Var, canonical,
                     eval_at, parse_equation, parse_expr, variables)


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str)
        .encode("utf-8")).hexdigest()[:16]


def _q(text: str) -> Fraction:
    if "/" in text:
        p, q = text.split("/")
        return Fraction(int(p), int(q))
    return Fraction(int(text))


def _q_str(q: Fraction) -> str:
    return (str(q.numerator) if q.denominator == 1
            else f"{q.numerator}/{q.denominator}")


class SkillStoreError(Exception):
    pass


class SkillStore:
    """Versioned, digest-checked, coordinator-written. Only the
    ladder's commit path calls _commit_skill, and only on PROMOTED."""

    def __init__(self) -> None:
        self.skills: Dict[str, Dict] = {}
        self.revision = 0
        self.history: List[Dict] = []

    # -- reads ---------------------------------------------------------
    def promoted_ids(self) -> List[str]:
        return sorted(self.skills)

    def get(self, skill_id: str) -> Optional[Dict]:
        return self.skills.get(skill_id)

    # -- coordinator-only write ---------------------------------------
    def _commit_skill(self, record: Dict, provenance: str) -> Dict:
        if record["skill_id"] in self.skills:
            raise SkillStoreError(
                f"skill {record['skill_id']} already promoted - "
                f"re-teaching does not overwrite (rollback first)")
        stored = copy.deepcopy(record)
        stored["provenance"] = provenance
        stored["record_digest"] = _digest(
            {k: v for k, v in stored.items() if k != "record_digest"})
        self.skills[record["skill_id"]] = stored
        self.revision += 1
        self.history.append({"revision": self.revision,
                             "action": "PROMOTED",
                             "skill_id": record["skill_id"],
                             "provenance": provenance})
        return stored

    # -- persistence ---------------------------------------------------
    def to_json(self) -> Dict:
        payload = {"revision": self.revision, "history": self.history,
                   "skills": self.skills}
        payload["store_digest"] = _digest(
            {k: v for k, v in payload.items() if k != "store_digest"})
        return payload

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_json(), fh, indent=1, sort_keys=True)

    @classmethod
    def load(cls, path: str) -> "SkillStore":
        store = cls()
        if not os.path.exists(path):
            return store
        payload = json.load(open(path, encoding="utf-8"))
        claimed = payload.get("store_digest")
        actual = _digest({k: v for k, v in payload.items()
                          if k != "store_digest"})
        if claimed != actual:
            raise SkillStoreError(
                f"skill store digest mismatch ({claimed} != {actual})"
                " - refusing a tampered store")
        store.revision = payload["revision"]
        store.history = payload["history"]
        store.skills = payload["skills"]
        return store


# ---------------------------------------------------------------- unifier
def _unify(pattern, expr, bindings: Dict) -> Optional[Dict]:
    """Structural first-order matching: pattern metavariables (Var)
    bind whole subexpressions."""
    if isinstance(pattern, Var):
        bound = bindings.get(pattern.name)
        if bound is None:
            out = dict(bindings)
            out[pattern.name] = expr
            return out
        return bindings if bound == expr else None
    if isinstance(pattern, Num):
        return bindings if isinstance(expr, Num) \
            and expr.q == pattern.q else None
    if isinstance(pattern, Neg) and isinstance(expr, Neg):
        return _unify(pattern.operand, expr.operand, bindings)
    for cls, field in ((Add, "terms"), (Mul, "factors")):
        if isinstance(pattern, cls) and isinstance(expr, cls):
            p_parts = getattr(pattern, field)
            e_parts = getattr(expr, field)
            if len(p_parts) != len(e_parts):
                return None
            current = bindings
            for p_part, e_part in zip(p_parts, e_parts):
                current = _unify(p_part, e_part, current)
                if current is None:
                    return None
            return current
    if isinstance(pattern, Pow) and isinstance(expr, Pow) \
            and pattern.exp == expr.exp:
        return _unify(pattern.base, expr.base, bindings)
    return None


def _instantiate(template, bindings: Dict):
    if isinstance(template, Var):
        if template.name not in bindings:
            raise SkillStoreError(
                f"rule right side uses unbound metavariable "
                f"{template.name!r}")
        return bindings[template.name]
    if isinstance(template, Num):
        return template
    if isinstance(template, Neg):
        return Neg(_instantiate(template.operand, bindings))
    if isinstance(template, Add):
        return Add(tuple(_instantiate(t, bindings)
                         for t in template.terms))
    if isinstance(template, Mul):
        return Mul(tuple(_instantiate(f, bindings)
                         for f in template.factors))
    if isinstance(template, Pow):
        return Pow(_instantiate(template.base, bindings),
                   template.exp)
    raise SkillStoreError(f"cannot instantiate {template!r}")


# ---------------------------------------------------------------- student
_OP_SKILL = {"add": "addition", "sub": "subtraction",
             "mul": "multiplication", "div": "division"}


class Student:
    """Solves exercises using ONLY promoted skills (plus at most one
    candidate skill under examination)."""

    def __init__(self, store: SkillStore,
                 candidate: Optional[Dict] = None) -> None:
        self.store = store
        self.candidate = candidate

    def _has(self, skill_id: str) -> bool:
        if self.store.get(skill_id) is not None:
            return True
        return (self.candidate is not None
                and self.candidate.get("skill_id") == skill_id)

    def _skill(self, skill_id: str) -> Optional[Dict]:
        record = self.store.get(skill_id)
        if record is not None:
            return record
        if self.candidate is not None \
                and self.candidate.get("skill_id") == skill_id:
            return self.candidate
        return None

    def solve(self, exercise: Dict) -> Dict:
        try:
            return self._solve(exercise)
        except SkillStoreError as exc:
            return {"status": "ERROR", "detail": str(exc)}

    def _cannot(self, skill_id: str) -> Dict:
        return {"status": "CANNOT_MISSING_SKILL",
                "missing_skill": skill_id,
                "detail": f"i have not learned {skill_id} yet"}

    def _solve(self, exercise: Dict) -> Dict:
        kind = exercise["kind"]
        if kind == "scene_count":
            if not self._has("quantity_grounding"):
                return self._cannot("quantity_grounding")
            return {"status": "SOLVED",
                    "answer": str(len(exercise["scene"]))}
        if kind == "scene_compare":
            if not self._has("quantity_grounding"):
                return self._cannot("quantity_grounding")
            a = len(exercise["scene_a"])
            b = len(exercise["scene_b"])
            answer = "same" if a == b else ("more" if a > b
                                            else "less")
            return {"status": "SOLVED", "answer": answer}
        if kind in ("successor", "predecessor"):
            if not self._has("counting_order"):
                return self._cannot("counting_order")
            n = int(exercise["n"])
            return {"status": "SOLVED",
                    "answer": str(n + 1 if kind == "successor"
                                  else n - 1)}
        if kind == "compare":
            a, b = _q(exercise["a"]), _q(exercise["b"])
            fractional = a.denominator != 1 or b.denominator != 1
            if fractional and not self._has("fractions"):
                return self._cannot("fractions")
            if not fractional and not self._has("integer_comparison"):
                return self._cannot("integer_comparison")
            answer = "equal" if a == b else ("greater" if a > b
                                             else "less")
            return {"status": "SOLVED", "answer": answer}
        if kind == "arith":
            op = exercise["op"]
            skill_id = _OP_SKILL[op]
            if not self._has(skill_id):
                return self._cannot(skill_id)
            a, b = _q(exercise["a"]), _q(exercise["b"])
            if (a.denominator != 1 or b.denominator != 1) \
                    and not self._has("fractions"):
                return self._cannot("fractions")
            if op == "div" and b == 0:
                return {"status": "ERROR",
                        "detail": "division by zero is undefined"}
            value = {"add": a + b, "sub": a - b, "mul": a * b,
                     "div": a / b if b else None}[op]
            return {"status": "SOLVED", "answer": _q_str(value)}
        if kind == "expand":
            return self._solve_expand(exercise)
        if kind == "solve":
            return self._solve_equation(exercise)
        return {"status": "ERROR", "detail": f"unknown kind {kind}"}

    # -- learned rewrite application ----------------------------------
    def _apply_rule(self, skill_record: Dict, expr):
        lhs = parse_expr(skill_record["formal"]["lhs"])
        rhs = parse_expr(skill_record["formal"]["rhs"])
        bindings = _unify(lhs, expr, {})
        if bindings is None:
            return None
        return _instantiate(rhs, bindings)

    def _solve_expand(self, exercise: Dict) -> Dict:
        skill = self._skill("algebra_distribute")
        if skill is None:
            return self._cannot("algebra_distribute")
        expr = parse_expr(exercise["expr"])
        rewritten = self._apply_rule(skill, expr)
        if rewritten is None:
            return {"status": "ERROR",
                    "detail": "my learned rule does not match this "
                              "expression"}
        from .mathir import render_expr
        return {"status": "SOLVED",
                "answer_expr": render_expr(rewritten),
                "canonical_equal_to_input":
                    canonical(rewritten) == canonical(expr)}

    # -- learned equation method --------------------------------------
    def _solve_equation(self, exercise: Dict) -> Dict:
        skill = self._skill("linear_equations")
        if skill is None:
            return self._cannot("linear_equations")
        method = skill["formal"].get("method", [])
        lhs, rhs = parse_equation(exercise["equation"])
        variable = exercise["variable"]
        current = lhs
        if "expand" in method:
            distribute = self._skill("algebra_distribute")
            if distribute is None:
                return self._cannot("algebra_distribute")
            rewritten = self._apply_rule(distribute, current)
            if rewritten is not None:
                current = rewritten
        if "isolate" not in method:
            return {"status": "ERROR",
                    "detail": "my learned method cannot isolate the "
                              "unknown"}
        # collect: canonical(lhs - rhs) must be linear in the unknown
        diff = canonical(Add((current, Neg(rhs))))
        constant = diff.get((), Fraction(0))
        slope = diff.get(((variable, 1),), Fraction(0))
        others = {m for m in diff
                  if m not in ((), ((variable, 1),))}
        if others or slope == 0:
            return {"status": "ERROR",
                    "detail": "this equation is not linear in the "
                              "unknown - outside my learned method"}
        solution = -constant / slope
        # THE SUBSTITUTION LAW: verify against the ORIGINAL equation
        point = {variable: solution}
        if eval_at(lhs, point) != eval_at(rhs, point):
            return {"status": "ERROR",
                    "detail": "my candidate solution failed the "
                              "substitution check - refusing to "
                              "answer"}
        return {"status": "SOLVED", "answer": _q_str(solution),
                "verified_by": "substitution_into_original"}
