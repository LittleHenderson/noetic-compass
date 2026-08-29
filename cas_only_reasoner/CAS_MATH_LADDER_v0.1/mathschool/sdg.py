"""CAS-SDG for mathematics: seeded, deterministic exercise
generation (independent of the teacher's examples) and the
counterexample ATTACK.

Two seeds, two channels: the development seed is visible machinery;
the PROTECTED seed lives in the examiner's channel and its exercises
are never shown to the teacher. Answer keys come from the exact
engine here - the examiner's key, never the student's own path.
"""

from __future__ import annotations

import random
from fractions import Fraction
from itertools import product
from typing import Dict, List, Optional, Tuple

from .mathir import (equal, eval_at, parse_equation, parse_expr,
                     variables)

DEV_SEED = 1101
PROTECTED_SEED = 90210      # the examiner's channel
RETENTION_SEED = 424242

_ATTACK_VALUES = (Fraction(0), Fraction(1), Fraction(2), Fraction(3),
                  Fraction(-1), Fraction(1, 2))


def attack_equation(text: str) -> Optional[Dict]:
    """Hunt an exact witness that the equation is FALSE. Returns the
    witness (possibly the empty point for variable-free equations) or
    None when no witness is found on the grid. Sound: a returned
    witness is a real refutation, exactly evaluated."""
    lhs, rhs = parse_equation(text)
    names = sorted(set(variables(lhs) + variables(rhs)))
    if len(names) > 3:
        return {"error": "attack caps at three variables in v0.1"}
    for combo in product(_ATTACK_VALUES, repeat=len(names)):
        point = dict(zip(names, combo))
        left = eval_at(lhs, point)
        right = eval_at(rhs, point)
        if left != right:
            return {"point": {k: str(v) for k, v in point.items()},
                    "left": str(left), "right": str(right)}
    return None


def verify_identity(text: str) -> Tuple[bool, Optional[Dict]]:
    """An equation offered as TRUE: canonical equality decides it
    (sound and complete for the polynomial class). Returns
    (holds, witness-if-not)."""
    lhs, rhs = parse_equation(text)
    if equal(lhs, rhs):
        return True, None
    return False, attack_equation(text)


# ---------------------------------------------------------------- exercises
def _rng(seed: int, skill_id: str, salt: str) -> random.Random:
    return random.Random(f"{seed}:{skill_id}:{salt}")


def generate(skill_id: str, kind: str, seed: int,
             count: int) -> List[Dict]:
    rng = _rng(seed, skill_id, "gen")
    makers = {
        "quantity_grounding": _quantity,
        "counting_order": _counting,
        "integer_comparison": _comparison,
        "addition": lambda r, i: _arith(r, i, "add", skill_id),
        "subtraction": lambda r, i: _arith(r, i, "sub", skill_id),
        "multiplication": lambda r, i: _arith(r, i, "mul", skill_id),
        "division": lambda r, i: _arith(r, i, "div", skill_id),
        "fractions": _fractions,
        "algebra_distribute": _distribute,
        "linear_equations": _equation,
    }
    maker = makers[skill_id]
    exercises = []
    for index in range(count):
        exercise = maker(rng, index)
        exercise["exercise_id"] = f"{skill_id}:{seed}:{index}"
        exercise["skill_id"] = skill_id
        exercises.append(exercise)
    return exercises


def _quantity(rng: random.Random, index: int) -> Dict:
    if index % 3 == 2:
        a, b = rng.randint(0, 9), rng.randint(0, 9)
        relation = "same" if a == b else ("more" if a > b else "less")
        return {"kind": "scene_compare",
                "scene_a": ["block"] * a, "scene_b": ["block"] * b,
                "expected": relation}
    n = rng.randint(0, 12)
    return {"kind": "scene_count", "scene": ["block"] * n,
            "expected": str(n)}


def _counting(rng: random.Random, index: int) -> Dict:
    if index % 2 == 0:
        n = rng.randint(0, 19)
        return {"kind": "successor", "n": n, "expected": str(n + 1)}
    n = rng.randint(1, 20)
    return {"kind": "predecessor", "n": n, "expected": str(n - 1)}


def _comparison(rng: random.Random, index: int) -> Dict:
    a = rng.randint(-12, 12)
    b = a if index % 4 == 3 else rng.randint(-12, 12)
    expected = "equal" if a == b else ("greater" if a > b else "less")
    return {"kind": "compare", "a": str(a), "b": str(b),
            "expected": expected}


def _arith(rng: random.Random, index: int, op: str,
           skill_id: str) -> Dict:
    a = Fraction(rng.randint(0, 12))
    b = Fraction(rng.randint(0, 12))
    if op == "sub" and b > a:
        a, b = b, a
    if op == "div":
        b = Fraction(rng.randint(1, 12))
    expected = {"add": a + b, "sub": a - b, "mul": a * b,
                "div": a / b if b else None}[op]
    return {"kind": "arith", "op": op, "a": str(a), "b": str(b),
            "expected": (str(expected) if expected.denominator == 1
                         else f"{expected.numerator}/"
                              f"{expected.denominator}")}


def _fractions(rng: random.Random, index: int) -> Dict:
    a = Fraction(rng.randint(1, 9), rng.randint(2, 9))
    b = Fraction(rng.randint(1, 9), rng.randint(2, 9))
    if index % 2 == 0:
        expected = a + b
        return {"kind": "arith", "op": "add",
                "a": f"{a.numerator}/{a.denominator}",
                "b": f"{b.numerator}/{b.denominator}",
                "expected": (str(expected)
                             if expected.denominator == 1 else
                             f"{expected.numerator}/"
                             f"{expected.denominator}")}
    expected = "equal" if a == b else ("greater" if a > b else "less")
    return {"kind": "compare",
            "a": f"{a.numerator}/{a.denominator}",
            "b": f"{b.numerator}/{b.denominator}",
            "expected": expected}


def _distribute(rng: random.Random, index: int) -> Dict:
    k = rng.randint(2, 9)
    m = rng.randint(1, 9)
    variable = rng.choice(["x", "y", "z"])
    text = f"{k} * ({variable} + {m})"
    return {"kind": "expand", "expr": text,
            "expected_equal_to": f"{k} * {variable} + {k * m}"}


def _equation(rng: random.Random, index: int) -> Dict:
    a = rng.randint(2, 9)
    b = rng.randint(1, 9)
    x = Fraction(rng.randint(-9, 9))
    variable = rng.choice(["x", "y", "z"])
    if index % 2 == 0:
        c = a * (x + b)
        text = f"{a} * ({variable} + {b}) = {c}"
    else:
        c = a * x + b
        text = f"{a} * {variable} + {b} = {c}"
    return {"kind": "solve", "equation": text, "variable": variable,
            "expected": (str(x) if x.denominator == 1
                         else f"{x.numerator}/{x.denominator}")}
