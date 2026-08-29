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
        return self._solve_advanced(exercise)

    # ------------------------------------------------- L5..L10 kinds
    def _promoted_schemas(self):
        """Every promoted rewrite-rule schema (plus the candidate if
        it is one) - the student's own proof library."""
        schemas = []
        for skill_id in list(self.store.promoted_ids()):
            record = self.store.get(skill_id)
            if record.get("kind") == "rewrite_rule":
                schemas.append((skill_id, record["formal"]["lhs"],
                                record["formal"]["rhs"]))
        if self.candidate is not None \
                and self.candidate.get("kind") == "rewrite_rule":
            schemas.append((self.candidate["skill_id"],
                            self.candidate["formal"]["lhs"],
                            self.candidate["formal"]["rhs"]))
        return schemas

    def _solve_advanced(self, exercise: Dict) -> Dict:
        from fractions import Fraction

        from . import advanced as adv
        from .mathir import parse_expr, render_expr
        kind = exercise["kind"]
        if kind == "func_eval":
            if not self._has("functions_evaluation"):
                return self._cannot("functions_evaluation")
            value = adv.eval_at(parse_expr(exercise["fn"]),
                                {"x": adv.q(exercise["at"])})
            return {"status": "SOLVED", "answer": adv.q_str(value)}
        if kind == "slope":
            if not self._has("coordinate_slope"):
                return self._cannot("coordinate_slope")
            m = adv.slope(exercise["p1"], exercise["p2"])
            if m is None:
                return {"status": "ERROR",
                        "detail": "a vertical line has no slope"}
            return {"status": "SOLVED", "answer": adv.q_str(m)}
        if kind in ("midpoint", "distance_squared"):
            if not self._has("geometry_points"):
                return self._cannot("geometry_points")
            if kind == "midpoint":
                mx, my = adv.midpoint(exercise["p1"], exercise["p2"])
                return {"status": "SOLVED",
                        "answer": f"{adv.q_str(mx)},{adv.q_str(my)}"}
            d2 = adv.distance_squared(exercise["p1"], exercise["p2"])
            return {"status": "SOLVED", "answer": adv.q_str(d2)}
        if kind in ("tri_area", "right_angle"):
            if not self._has("geometry_shapes"):
                return self._cannot("geometry_shapes")
            if kind == "tri_area":
                area = adv.triangle_area(exercise["a"], exercise["b"],
                                         exercise["c"])
                return {"status": "SOLVED", "answer": adv.q_str(area)}
            right = adv.is_right_angle_at(exercise["vertex"],
                                          exercise["p1"],
                                          exercise["p2"])
            return {"status": "SOLVED",
                    "answer": "yes" if right else "no"}
        if kind in ("seq_term", "seq_sum"):
            if not self._has("sequences"):
                return self._cannot("sequences")
            a1 = adv.q(exercise["a1"])
            n = int(exercise["n"])
            if kind == "seq_term" and exercise["type"] == "arith":
                value = a1 + (n - 1) * adv.q(exercise["d"])
            elif kind == "seq_term":
                value = a1 * adv.q(exercise["r"]) ** (n - 1)
            else:
                d = adv.q(exercise["d"])
                value = Fraction(n, 2) * (2 * a1 + (n - 1) * d)
            return {"status": "SOLVED", "answer": adv.q_str(value)}
        if kind == "derivative":
            if not self._has("derivatives_polynomial"):
                return self._cannot("derivatives_polynomial")
            derived = adv.derivative_canonical(
                parse_expr(exercise["expr"]),
                exercise.get("variable", "x"))
            return {"status": "SOLVED",
                    "answer_expr": render_expr(
                        adv.canonical_to_expr(derived))}
        if kind == "integral":
            if not self._has("integrals_polynomial"):
                return self._cannot("integrals_polynomial")
            value = adv.definite_integral(
                parse_expr(exercise["expr"]),
                exercise.get("variable", "x"),
                adv.q(exercise["a"]), adv.q(exercise["b"]))
            return {"status": "SOLVED", "answer": adv.q_str(value),
                    "verified_by": "differentiate_back_check"}
        if kind == "mat_det":
            if not self._has("matrices_2x2"):
                return self._cannot("matrices_2x2")
            return {"status": "SOLVED",
                    "answer": adv.q_str(adv.mat_det(exercise["m"]))}
        if kind == "mat_mul":
            if not self._has("matrices_2x2"):
                return self._cannot("matrices_2x2")
            return {"status": "SOLVED",
                    "answer": adv.mat_str(adv.mat_mul(
                        exercise["m"], exercise["n"]))}
        if kind in ("prob", "prob_and", "prob_complement"):
            if not self._has("probability_finite"):
                return self._cannot("probability_finite")
            if kind == "prob":
                value = Fraction(int(exercise["favorable"]),
                                 int(exercise["total"]))
            elif kind == "prob_and":
                value = adv.q(exercise["p1"]) * adv.q(exercise["p2"])
            else:
                value = 1 - adv.q(exercise["p"])
            return {"status": "SOLVED", "answer": adv.q_str(value)}
        if kind in ("stat_mean", "stat_median"):
            if not self._has("statistics_basic"):
                return self._cannot("statistics_basic")
            values = sorted(adv.q(v) for v in exercise["values"])
            if kind == "stat_mean":
                value = sum(values, Fraction(0)) / len(values)
            elif len(values) % 2 == 1:
                value = values[len(values) // 2]
            else:
                middle = len(values) // 2
                value = (values[middle - 1] + values[middle]) / 2
            return {"status": "SOLVED", "answer": adv.q_str(value)}
        if kind == "rewrite":
            skill = self._skill(exercise["rule_skill"])
            if skill is None:
                return self._cannot(exercise["rule_skill"])
            expr = parse_expr(exercise["expr"])
            rewritten = self._apply_rule(skill, expr)
            if rewritten is None:
                results = adv.rewrite_everywhere(
                    expr, skill["formal"]["lhs"],
                    skill["formal"]["rhs"])
                if not results:
                    return {"status": "ERROR",
                            "detail": "my learned rule does not "
                                      "match this expression"}
                rewritten = results[0]
            return {"status": "SOLVED",
                    "answer_expr": render_expr(rewritten),
                    "canonical_equal_to_input":
                        adv.canonical(rewritten)
                        == adv.canonical(expr)}
        if kind == "prove":
            if not self._has("formal_proofs"):
                return self._cannot("formal_proofs")
            schemas = self._promoted_schemas()
            steps = adv.prove_equal(
                parse_expr(exercise["lhs_text"]),
                parse_expr(exercise["rhs_text"]), schemas)
            if steps is None:
                return {"status": "ERROR",
                        "detail": "no proof found within my rule "
                                  "library and search bound - i "
                                  "cannot prove this"}
            return {"status": "SOLVED", "answer": "proved",
                    "steps": steps,
                    "verified_by": "independent_step_replay"}
        if kind == "discovery_round":
            if not self._has("conjecture_discovery"):
                return self._cannot("conjecture_discovery")
            library = [(l, r) for _, l, r
                       in self._promoted_schemas()]
            result = adv.discovery_round(int(exercise["seed"]),
                                         int(exercise["budget"]),
                                         library)
            result["status"] = "SOLVED"
            result["answer"] = "discovery_verified"
            result["library_used"] = library
            return result
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
