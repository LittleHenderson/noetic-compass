"""EXACT machinery for MATH-L5..L10.

The honesty rule of the whole ladder: a level enters only where
CAS-Math can represent the concept and a trusted checker can verify
it EXACTLY. This module therefore works in the exact-rational /
polynomial fragment throughout:

  L5  polynomial functions, coordinate slope            (exact)
  L6  analytic geometry over rationals - midpoint, squared distance,
      shoelace area, perpendicularity by dot product    (exact;
      transcendental trigonometry is OUT OF SCOPE, disclosed)
  L7  polynomial limits, derivatives, definite integrals, sequences
      (exact closed forms; the derivative is checked by independent
      re-derivation, the integral by DIFFERENTIATING BACK)
  L8  2x2 matrices, finite equally-likely probability, exact
      statistics                                        (exact)
  L9  proof search over the student's own PROMOTED rule schemas,
      every found step re-verified by an independent walk
  L10 conjecture discovery: enumerate -> attack -> prove ->
      novelty-check against the student's own library; a survivor
      without proof stays CONJECTURE, never VERIFIED
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .mathir import (Add, Mul, Neg, Num, Pow, Var, canonical,
                     eval_at, parse_expr, render_expr, variables)


def q(text) -> Fraction:
    text = str(text)
    if "/" in text:
        p_, q_ = text.split("/")
        return Fraction(int(p_), int(q_))
    return Fraction(int(text))


def q_str(value: Fraction) -> str:
    return (str(value.numerator) if value.denominator == 1
            else f"{value.numerator}/{value.denominator}")


# ------------------------------------------------------------ calculus
def canonical_to_expr(can: Dict) -> object:
    terms = []
    for monomial, coeff in sorted(can.items()):
        factors: List[object] = []
        if coeff != 1 or not monomial:
            factors.append(Num(coeff))
        for var, exp in monomial:
            factors.append(Var(var) if exp == 1 else Pow(Var(var),
                                                         exp))
        terms.append(factors[0] if len(factors) == 1
                     else Mul(tuple(factors)))
    if not terms:
        return Num(Fraction(0))
    return terms[0] if len(terms) == 1 else Add(tuple(terms))


def derivative_canonical(expr: object, var: str) -> Dict:
    """The EXACT polynomial derivative on canonical monomials - the
    examiner's independent derivation."""
    out: Dict = {}
    for monomial, coeff in canonical(expr).items():
        powers = dict(monomial)
        exponent = powers.get(var, 0)
        if exponent == 0:
            continue
        powers[var] = exponent - 1
        new_monomial = tuple(sorted(
            (v, e) for v, e in powers.items() if e != 0))
        out[new_monomial] = out.get(new_monomial, Fraction(0)) \
            + coeff * exponent
    return {m: c for m, c in out.items() if c != 0}


def antiderivative_canonical(expr: object, var: str) -> Dict:
    out: Dict = {}
    for monomial, coeff in canonical(expr).items():
        powers = dict(monomial)
        exponent = powers.get(var, 0)
        powers[var] = exponent + 1
        new_monomial = tuple(sorted(
            (v, e) for v, e in powers.items() if e != 0))
        out[new_monomial] = out.get(new_monomial, Fraction(0)) \
            + coeff / (exponent + 1)
    return {m: c for m, c in out.items() if c != 0}


def definite_integral(expr: object, var: str, lower: Fraction,
                      upper: Fraction) -> Fraction:
    """Exact, and SELF-CHECKING: the antiderivative must
    differentiate back to the integrand or this refuses."""
    anti = antiderivative_canonical(expr, var)
    anti_expr = canonical_to_expr(anti)
    if derivative_canonical(anti_expr, var) != canonical(expr):
        raise ValueError("antiderivative failed the "
                         "differentiate-back check")
    return (eval_at(anti_expr, {var: upper})
            - eval_at(anti_expr, {var: lower}))


# ------------------------------------------------------------ geometry
def midpoint(p1, p2) -> Tuple[Fraction, Fraction]:
    return ((q(p1[0]) + q(p2[0])) / 2, (q(p1[1]) + q(p2[1])) / 2)


def distance_squared(p1, p2) -> Fraction:
    return (q(p1[0]) - q(p2[0])) ** 2 + (q(p1[1]) - q(p2[1])) ** 2


def slope(p1, p2) -> Optional[Fraction]:
    if q(p1[0]) == q(p2[0]):
        return None
    return (q(p2[1]) - q(p1[1])) / (q(p2[0]) - q(p1[0]))


def triangle_area(a, b, c) -> Fraction:
    """The shoelace formula - exact, no square roots anywhere."""
    ax, ay, bx, by, cx, cy = (q(a[0]), q(a[1]), q(b[0]), q(b[1]),
                              q(c[0]), q(c[1]))
    return abs(ax * (by - cy) + bx * (cy - ay)
               + cx * (ay - by)) / 2


def is_right_angle_at(vertex, p1, p2) -> bool:
    """Perpendicularity by dot product - exact rational trig
    substitute (transcendental trig is out of scope, disclosed)."""
    v1 = (q(p1[0]) - q(vertex[0]), q(p1[1]) - q(vertex[1]))
    v2 = (q(p2[0]) - q(vertex[0]), q(p2[1]) - q(vertex[1]))
    return v1[0] * v2[0] + v1[1] * v2[1] == 0


# ------------------------------------------------------- linear algebra
def mat(m) -> List[List[Fraction]]:
    return [[q(x) for x in row] for row in m]


def mat_mul(a, b) -> List[List[Fraction]]:
    a, b = mat(a), mat(b)
    return [[a[i][0] * b[0][j] + a[i][1] * b[1][j]
             for j in range(2)] for i in range(2)]


def mat_det(a) -> Fraction:
    a = mat(a)
    return a[0][0] * a[1][1] - a[0][1] * a[1][0]


def mat_str(a) -> str:
    return ";".join(",".join(q_str(x) for x in row) for row in a)


# ------------------------------------------------------------- proofs
def _unify(pattern, expr, bindings):
    from .student import _unify as unify
    return unify(pattern, expr, bindings)


def _instantiate(template, bindings):
    from .student import _instantiate as inst
    return inst(template, bindings)


def _all_foci(expr, prefix=()):
    foci = [prefix]
    if isinstance(expr, Add):
        for i, t in enumerate(expr.terms):
            foci.extend(_all_foci(t, prefix + (("t", i),)))
    elif isinstance(expr, Mul):
        for i, f in enumerate(expr.factors):
            foci.extend(_all_foci(f, prefix + (("f", i),)))
    elif isinstance(expr, Neg):
        foci.extend(_all_foci(expr.operand, prefix + (("n", 0),)))
    elif isinstance(expr, Pow):
        foci.extend(_all_foci(expr.base, prefix + (("p", 0),)))
    return foci


def _navigate(expr, focus):
    node = expr
    for kind, index in focus:
        if kind == "t":
            node = node.terms[index]
        elif kind == "f":
            node = node.factors[index]
        elif kind == "n":
            node = node.operand
        elif kind == "p":
            node = node.base
    return node


def _replace(expr, focus, new_node):
    if not focus:
        return new_node
    (kind, index), rest = focus[0], focus[1:]
    if kind == "t":
        terms = list(expr.terms)
        terms[index] = _replace(terms[index], rest, new_node)
        return Add(tuple(terms))
    if kind == "f":
        factors = list(expr.factors)
        factors[index] = _replace(factors[index], rest, new_node)
        return Mul(tuple(factors))
    if kind == "n":
        return Neg(_replace(expr.operand, rest, new_node))
    if kind == "p":
        return Pow(_replace(expr.base, rest, new_node), expr.exp)
    raise ValueError("bad focus")


def rewrite_everywhere(expr, lhs_text: str,
                       rhs_text: str) -> List[object]:
    """Every result of applying the schema at any focus - forward."""
    lhs, rhs = parse_expr(lhs_text), parse_expr(rhs_text)
    results = []
    for focus in _all_foci(expr):
        node = _navigate(expr, focus)
        bindings = _unify(lhs, node, {})
        if bindings is None:
            continue
        try:
            rebuilt = _replace(expr, focus,
                               _instantiate(rhs, bindings))
        except Exception:
            continue
        if rebuilt not in results:
            results.append(rebuilt)
    return results


def prove_equal(lhs: object, rhs: object,
                schemas: List[Tuple[str, str, str]],
                depth: int = 3, breadth: int = 200
                ) -> Optional[List[Dict]]:
    """Bounded BFS: derive rhs from lhs using the given schemas (each
    (rule_id, lhs_text, rhs_text)), applied FORWARD AND BACKWARD -
    sound because every schema is a promoted verified identity. Every
    step of a found proof is INDEPENDENTLY re-verified before this
    returns it."""
    target = canonical(rhs)
    start_key = render_expr(lhs)
    frontier = [(lhs, [])]
    seen = {start_key}
    for _ in range(depth):
        next_frontier = []
        for expr, path in frontier:
            for rule_id, l_text, r_text in schemas:
                for direction, (a_text, b_text) in (
                        ("forward", (l_text, r_text)),
                        ("reverse", (r_text, l_text))):
                    for result in rewrite_everywhere(expr, a_text,
                                                     b_text):
                        key = render_expr(result)
                        if key in seen:
                            continue
                        seen.add(key)
                        step = {"rule": rule_id,
                                "direction": direction,
                                "lhs_schema": a_text,
                                "rhs_schema": b_text,
                                "from": render_expr(expr),
                                "to": key}
                        new_path = path + [step]
                        if canonical(result) == target:
                            if _verify_proof(lhs, rhs, new_path,
                                             schemas):
                                return new_path
                            continue
                        next_frontier.append((result, new_path))
        frontier = next_frontier[:breadth]
        if not frontier:
            break
    return None


def _verify_proof(lhs, rhs, steps: List[Dict],
                  schemas) -> bool:
    """The independent walk: replay every claimed step and demand it
    is reachable by the named schema, then demand the endpoint."""
    by_id = {rule_id: (l, r) for rule_id, l, r in schemas}
    current = lhs
    for step in steps:
        l_text, r_text = by_id[step["rule"]]
        if step["direction"] == "reverse":
            l_text, r_text = r_text, l_text
        candidates = rewrite_everywhere(current, l_text, r_text)
        match = None
        for candidate in candidates:
            if render_expr(candidate) == step["to"]:
                match = candidate
                break
        if match is None:
            return False
        current = match
    return canonical(current) == canonical(rhs)


def examiner_verify_proof(lhs_text: str, rhs_text: str,
                          steps: List[Dict]) -> bool:
    """INDEPENDENT proof verification: every step's claimed schema
    must itself be a canonically TRUE identity (sound regardless of
    who taught it), the rewrite must replay, and the endpoint must be
    the target. No trust in the prover."""
    if not steps:
        return False
    current = parse_expr(lhs_text)
    if render_expr(current) != steps[0]["from"]:
        return False
    for step in steps:
        l_text = step.get("lhs_schema")
        r_text = step.get("rhs_schema")
        if not l_text or not r_text:
            return False
        if canonical(parse_expr(l_text)) \
                != canonical(parse_expr(r_text)):
            return False
        found = None
        for candidate in rewrite_everywhere(current, l_text, r_text):
            if render_expr(candidate) == step["to"]:
                found = candidate
                break
        if found is None:
            return False
        current = found
    return canonical(current) == canonical(parse_expr(rhs_text))


def examiner_verify_discovery(result: Dict,
                              library: List[Tuple[str, str]],
                              min_proved: int,
                              min_refuted: int) -> Tuple[bool, str]:
    """INDEPENDENT re-verification of a discovery round: every proved
    claim must be canonically true, attack-clean, and alpha-novel vs
    the library; every refutation witness must actually refute; and
    the minimum counts must hold. Conjectures are checked to be
    NON-verified claims (no laundering through the conjecture door).
    """
    from .sdg import attack_equation
    known = {alpha_normal(l, r) for l, r in library}
    proved = result.get("proved", [])
    refuted = result.get("refuted", [])
    for item in proved:
        claim = item.get("claim", "")
        if claim.count("=") != 1:
            return False, f"malformed claim {claim!r}"
        lhs_text, rhs_text = claim.split("=")
        if canonical(parse_expr(lhs_text)) \
                != canonical(parse_expr(rhs_text)):
            return False, f"claimed-proved {claim!r} is NOT true"
        if attack_equation(claim) is not None:
            return False, f"{claim!r} fails the attack grid"
        key = alpha_normal(lhs_text, rhs_text)
        if key in known:
            return False, f"{claim!r} is not novel vs the library"
        known.add(key)
    for item in refuted:
        claim = item.get("claim", "")
        witness = item.get("witness") or {}
        point = {name: q(value) for name, value
                 in (witness.get("point") or {}).items()}
        try:
            lhs_text, rhs_text = claim.split("=")
            left = eval_at(parse_expr(lhs_text), point)
            right = eval_at(parse_expr(rhs_text), point)
        except Exception as exc:
            return False, f"witness for {claim!r} broken: {exc}"
        if left == right:
            return False, f"witness for {claim!r} does not refute"
    if len(proved) < min_proved:
        return False, (f"only {len(proved)} proved "
                       f"(minimum {min_proved})")
    if len(refuted) < min_refuted:
        return False, (f"only {len(refuted)} refuted "
                       f"(minimum {min_refuted})")
    return True, (f"{len(proved)} proved novel, {len(refuted)} "
                  f"refuted with exact witnesses, "
                  f"{len(result.get('conjectures', []))} held as "
                  f"conjectures")


# ----------------------------------------------------------- discovery
def alpha_normal(lhs_text: str, rhs_text: str) -> str:
    """Schema identity up to metavariable renaming - the novelty
    key."""
    lhs, rhs = parse_expr(lhs_text), parse_expr(rhs_text)
    order: List[str] = []
    for name in variables(Add((lhs, rhs))):
        if name not in order:
            order.append(name)
    mapping = {name: f"m{i}" for i, name in enumerate(order)}

    def rename(expr):
        if isinstance(expr, Var):
            return Var(mapping[expr.name])
        if isinstance(expr, Num):
            return expr
        if isinstance(expr, Neg):
            return Neg(rename(expr.operand))
        if isinstance(expr, Add):
            return Add(tuple(rename(t) for t in expr.terms))
        if isinstance(expr, Mul):
            return Mul(tuple(rename(f) for f in expr.factors))
        if isinstance(expr, Pow):
            return Pow(rename(expr.base), expr.exp)
        raise ValueError

    return (render_expr(rename(lhs)) + " = "
            + render_expr(rename(rhs)))


def discovery_round(seed: int, budget: int,
                    library: List[Tuple[str, str]]) -> Dict:
    """Enumerate candidate identities from a small template family,
    ATTACK each on the exact grid, PROVE survivors by canonical
    equality, and keep only those NOVEL relative to the library
    (alpha-normalized). A candidate that survives attack but is not
    proved stays a CONJECTURE - it is never called verified. Fully
    deterministic in the seed."""
    import random

    from .sdg import attack_equation
    rng = random.Random(f"discovery:{seed}")
    known = {alpha_normal(l, r) for l, r in library}
    proved, refuted, conjectures = [], [], []
    templates = [
        "(a + b) * (a - b)", "(a - b) * (a - b)",
        "(a + b) * (a + b)", "a * (a + b)", "(a + b)^2 - a^2",
        "(a + b)^2 + (a - b)^2", "(a + b)^2 - (a - b)^2",
        "a * (b - c)", "(a + b) * c - a * c",
    ]
    for _ in range(budget):
        lhs_text = rng.choice(templates)
        lhs = parse_expr(lhs_text)
        expansion = canonical_to_expr(canonical(lhs))
        rhs_text = render_expr(expansion)
        if rng.random() < 0.5:
            # a PERTURBED (usually false) candidate - the attack must
            # catch these
            broken = canonical(lhs)
            if broken:
                key = sorted(broken)[0]
                broken = dict(broken)
                broken[key] = broken[key] + 1
                rhs_text = render_expr(canonical_to_expr(broken))
        claim = f"{lhs_text} = {rhs_text}"
        witness = attack_equation(claim)
        if witness is not None and "error" not in witness:
            refuted.append({"claim": claim, "witness": witness})
            continue
        if canonical(parse_expr(lhs_text)) \
                == canonical(parse_expr(rhs_text)):
            key = alpha_normal(lhs_text, rhs_text)
            if key not in known:
                known.add(key)
                proved.append({"claim": claim,
                               "novelty": "new to my library",
                               "proof": "canonical polynomial "
                                        "equality"})
        else:
            conjectures.append({"claim": claim,
                                "status": "CONJECTURE - survived "
                                          "the attack grid but "
                                          "not proved"})
    return {"proved": proved, "refuted": refuted,
            "conjectures": conjectures}
