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
        "functions_evaluation": _func_eval,
        "coordinate_slope": _slope_ex,
        "geometry_points": _geo_points,
        "geometry_shapes": _geo_shapes,
        "sequences": _sequences,
        "derivatives_polynomial": _derivative_ex,
        "integrals_polynomial": _integral_ex,
        "matrices_2x2": _matrices,
        "probability_finite": _probability,
        "statistics_basic": _statistics,
        "axiom_commutativity": lambda r, i: _rewrite_ex(
            r, i, "axiom_commutativity"),
        "axiom_square_expand": lambda r, i: _rewrite_ex(
            r, i, "axiom_square_expand"),
        "formal_proofs": _prove_ex,
        "conjecture_discovery": _discovery_ex,
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


# ------------------------------------------------------- L5..L10 makers
def _q_str(value: Fraction) -> str:
    return (str(value.numerator) if value.denominator == 1
            else f"{value.numerator}/{value.denominator}")


def _func_eval(rng: random.Random, index: int) -> Dict:
    a, b = rng.randint(1, 9), rng.randint(0, 9)
    at = Fraction(rng.randint(-6, 6))
    if index % 2 == 0:
        fn = f"{a} * x + {b}"
        expected = a * at + b
    else:
        c = rng.randint(1, 5)
        fn = f"{c} * x^2 + {a} * x + {b}"
        expected = c * at * at + a * at + b
    return {"kind": "func_eval", "fn": fn, "at": _q_str(at),
            "expected": _q_str(expected)}


def _slope_ex(rng: random.Random, index: int) -> Dict:
    x1, y1 = rng.randint(-6, 6), rng.randint(-6, 6)
    x2 = x1 + rng.randint(1, 6)
    y2 = rng.randint(-6, 6)
    expected = Fraction(y2 - y1, x2 - x1)
    return {"kind": "slope", "p1": [str(x1), str(y1)],
            "p2": [str(x2), str(y2)], "expected": _q_str(expected)}


def _geo_points(rng: random.Random, index: int) -> Dict:
    p1 = [rng.randint(-6, 6), rng.randint(-6, 6)]
    p2 = [rng.randint(-6, 6), rng.randint(-6, 6)]
    if index % 2 == 0:
        mx = Fraction(p1[0] + p2[0], 2)
        my = Fraction(p1[1] + p2[1], 2)
        return {"kind": "midpoint",
                "p1": [str(v) for v in p1],
                "p2": [str(v) for v in p2],
                "expected": f"{_q_str(mx)},{_q_str(my)}"}
    d2 = Fraction((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
    return {"kind": "distance_squared",
            "p1": [str(v) for v in p1], "p2": [str(v) for v in p2],
            "expected": _q_str(d2)}


def _geo_shapes(rng: random.Random, index: int) -> Dict:
    from .advanced import is_right_angle_at, triangle_area
    if index % 2 == 0:
        a = [rng.randint(-5, 5), rng.randint(-5, 5)]
        b = [a[0] + rng.randint(1, 6), a[1]]
        c = [a[0], a[1] + rng.randint(1, 6)]
        area = triangle_area(a, b, c)
        return {"kind": "tri_area",
                "a": [str(v) for v in a], "b": [str(v) for v in b],
                "c": [str(v) for v in c],
                "expected": _q_str(area)}
    vertex = [rng.randint(-4, 4), rng.randint(-4, 4)]
    dx, dy = rng.randint(1, 4), rng.randint(1, 4)
    p1 = [vertex[0] + dx, vertex[1] + dy]
    if index % 4 == 1:
        p2 = [vertex[0] - dy, vertex[1] + dx]      # perpendicular
    else:
        p2 = [vertex[0] + dx + 1, vertex[1] + dy]  # not
    expected = "yes" if is_right_angle_at(
        [str(v) for v in vertex], [str(v) for v in p1],
        [str(v) for v in p2]) else "no"
    return {"kind": "right_angle",
            "vertex": [str(v) for v in vertex],
            "p1": [str(v) for v in p1], "p2": [str(v) for v in p2],
            "expected": expected}


def _sequences(rng: random.Random, index: int) -> Dict:
    a1 = rng.randint(-5, 9)
    n = rng.randint(3, 9)
    if index % 3 == 0:
        d = rng.randint(1, 6)
        return {"kind": "seq_term", "type": "arith", "a1": str(a1),
                "d": str(d), "n": str(n),
                "expected": str(a1 + (n - 1) * d)}
    if index % 3 == 1:
        r = rng.randint(2, 3)
        a1 = rng.randint(1, 4)
        n = rng.randint(2, 5)
        return {"kind": "seq_term", "type": "geom", "a1": str(a1),
                "r": str(r), "n": str(n),
                "expected": str(a1 * r ** (n - 1))}
    d = rng.randint(1, 5)
    total = Fraction(n, 2) * (2 * a1 + (n - 1) * d)
    return {"kind": "seq_sum", "type": "arith", "a1": str(a1),
            "d": str(d), "n": str(n), "expected": _q_str(total)}


def _poly_text(rng: random.Random) -> str:
    a = rng.randint(1, 6)
    b = rng.randint(1, 9)
    c = rng.randint(0, 9)
    degree = rng.choice((2, 3))
    if degree == 2:
        return f"{a} * x^2 + {b} * x + {c}"
    return f"{a} * x^3 + {b} * x^2 + {c} * x"


def _derivative_ex(rng: random.Random, index: int) -> Dict:
    from .advanced import (canonical_to_expr, derivative_canonical)
    from .mathir import parse_expr, render_expr
    text = _poly_text(rng)
    expected = render_expr(canonical_to_expr(
        derivative_canonical(parse_expr(text), "x")))
    return {"kind": "derivative", "expr": text, "variable": "x",
            "expected_equal_to": expected}


def _integral_ex(rng: random.Random, index: int) -> Dict:
    from .advanced import definite_integral
    from .mathir import parse_expr
    a = rng.randint(1, 4)
    b = rng.randint(0, 6)
    text = f"{a} * x + {b}" if index % 2 == 0         else f"{a} * x^2 + {b}"
    lower = Fraction(rng.randint(-2, 1))
    upper = lower + rng.randint(1, 4)
    value = definite_integral(parse_expr(text), "x", lower, upper)
    return {"kind": "integral", "expr": text, "variable": "x",
            "a": _q_str(lower), "b": _q_str(upper),
            "expected": _q_str(value)}


def _matrices(rng: random.Random, index: int) -> Dict:
    from .advanced import mat_det, mat_mul, mat_str, q_str
    m = [[str(rng.randint(-4, 6)) for _ in range(2)]
         for _ in range(2)]
    if index % 2 == 0:
        return {"kind": "mat_det", "m": m,
                "expected": q_str(mat_det(m))}
    n = [[str(rng.randint(-4, 6)) for _ in range(2)]
         for _ in range(2)]
    return {"kind": "mat_mul", "m": m, "n": n,
            "expected": mat_str(mat_mul(m, n))}


def _probability(rng: random.Random, index: int) -> Dict:
    if index % 3 == 0:
        total = rng.randint(4, 12)
        favorable = rng.randint(1, total)
        expected = Fraction(favorable, total)
        return {"kind": "prob", "favorable": str(favorable),
                "total": str(total), "expected": _q_str(expected)}
    if index % 3 == 1:
        p1 = Fraction(1, rng.randint(2, 6))
        p2 = Fraction(1, rng.randint(2, 6))
        return {"kind": "prob_and", "p1": _q_str(p1),
                "p2": _q_str(p2), "expected": _q_str(p1 * p2)}
    p = Fraction(rng.randint(1, 5), 6)
    return {"kind": "prob_complement", "p": _q_str(p),
            "expected": _q_str(1 - p)}


def _statistics(rng: random.Random, index: int) -> Dict:
    values = [rng.randint(-5, 12)
              for _ in range(rng.randint(3, 6))]
    if index % 2 == 0:
        mean = Fraction(sum(values), len(values))
        return {"kind": "stat_mean",
                "values": [str(v) for v in values],
                "expected": _q_str(mean)}
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        median = Fraction(ordered[middle])
    else:
        median = Fraction(ordered[middle - 1] + ordered[middle], 2)
    return {"kind": "stat_median",
            "values": [str(v) for v in values],
            "expected": _q_str(median)}


_AXIOM_INSTANCES = {
    "axiom_commutativity": [
        ("x + 3", "3 + x"), ("2 + y", "y + 2"), ("x + y", "y + x"),
        ("5 + 7", "7 + 5")],
    "axiom_square_expand": [
        ("(x + 2)^2", "x^2 + 4 * x + 4"),
        ("(y + 3)^2", "y^2 + 6 * y + 9"),
        ("(x + 1)^2", "x^2 + 2 * x + 1"),
        ("(z + 5)^2", "z^2 + 10 * z + 25")],
}


def _rewrite_ex(rng: random.Random, index: int,
                rule_skill: str) -> Dict:
    instances = _AXIOM_INSTANCES[rule_skill]
    expr, expected = instances[
        rng.randint(0, len(instances) - 1)]
    return {"kind": "rewrite", "rule_skill": rule_skill,
            "expr": expr, "expected_equal_to": expected}


_PROOF_PAIRS = [
    ("(x + 2)^2", "x^2 + 4 * x + 4"),
    ("(y + 1)^2", "y^2 + 2 * y + 1"),
    ("2 * (x + 3)", "2 * x + 6"),
    ("(x + 2)^2", "4 * x + 4 + x^2"),
    ("3 * (y + 1)", "3 + 3 * y"),
    ("(z + 3)^2", "z^2 + 6 * z + 9"),
]


def _prove_ex(rng: random.Random, index: int) -> Dict:
    lhs, rhs = _PROOF_PAIRS[rng.randint(0, len(_PROOF_PAIRS) - 1)]
    return {"kind": "prove", "lhs_text": lhs, "rhs_text": rhs,
            "expected": "proved"}


def _discovery_ex(rng: random.Random, index: int) -> Dict:
    return {"kind": "discovery_round",
            "seed": rng.randint(1, 10 ** 6), "budget": 30,
            "min_proved": 1, "min_refuted": 2,
            "expected": "discovery_verified"}
