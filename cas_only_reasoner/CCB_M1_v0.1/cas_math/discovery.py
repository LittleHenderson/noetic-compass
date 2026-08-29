"""Discovery: the machine generates, tests, and PROVES identities it
was never given.

The loop shape is conjecture -> counterexample-test -> proof:
  1. ENUMERATE candidate expressions: atoms and one-operation
     combinations, PLUS a hand-authored composite layer (an audit
     found the original "generic space" wording false: the composite
     layer contains both sides of showcase identities by construction
     - that fact is now disclosed here and in the packet);
  2. CONJECTURE candidate identities (syntactically distinct pairs);
  3. TEST each conjecture at exact sample points - falsified
     conjectures die with a witness;
  4. PROVE survivors through the TRUSTED checker (canonical polynomial
     expansion - sound and complete for this class; the prover is
     independent of the generator);
  5. KNOWN-CONTENT GATES: (a) fixture identities are excluded
     (alpha-normalized, variable-name-blind); (b) any identity
     derivable in ONE application of a taught executable axiom
     (rules.py) is marked derived_from_taught_axiom and NOT counted
     novel - closing the instantiation hole the audit found.

HONESTY LINE (state it wherever this capability is quoted): this is
VERIFIED IDENTITY SEARCH over a small, partly hand-authored space -
NOT novel research under CRQS section 4 (every result has an answer
known to mathematics). Surviving "novel_to_machine" items are merely
absent from fixtures and not one-step-derivable from taught axioms.
The CAS-G10 D10 novel-research floor claim built on v1 of this module
was REFUTED by adversarial audit (2026-08-28) and is withdrawn.
"""

from __future__ import annotations

import hashlib
import json
import os
from fractions import Fraction
from itertools import combinations
from typing import Dict, List, Tuple

from .expr import (Add, Mul, Neg, Num, Pow, Var, canonical, equal,
                   eval_at, str_of, to_json)

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "fixtures")

# Exact test points: negatives and a fraction so sign and scale errors
# both surface. The PROOF step is the authority; testing only prunes.
TEST_POINTS: List[Dict[str, Fraction]] = [
    {"x": Fraction(2), "y": Fraction(3)},
    {"x": Fraction(-1), "y": Fraction(2)},
    {"x": Fraction(1, 2), "y": Fraction(-3)},
    {"x": Fraction(5), "y": Fraction(7)},
]


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def enumerate_expressions() -> List[object]:
    """The generic candidate space, deterministically ordered: atoms,
    one-operation combinations, and squares of variables."""
    atoms: List[object] = [Var("x"), Var("y"),
                           Num(Fraction(0)), Num(Fraction(1)),
                           Num(Fraction(2))]
    exprs: List[object] = list(atoms)
    for left in atoms:
        for right in atoms:
            exprs.append(Add((left, right)))
            exprs.append(Mul((left, right)))
    for atom in atoms:
        exprs.append(Neg(atom))
    exprs.append(Pow(Var("x"), 2))
    exprs.append(Pow(Var("y"), 2))
    # HAND-AUTHORED composite layer - DISCLOSED: these six expressions
    # include both sides of showcase identities by construction; any
    # theorem formed from them is search-confirmation of an authored
    # pair, not discovery
    x, y = Var("x"), Var("y")
    one = Num(Fraction(1))
    exprs += [
        Mul((x, Add((y, one)))),           # x*(y+1)
        Add((Mul((x, y)), x)),             # x*y + x
        Mul((Add((x, y)), Add((x, y)))),   # (x+y)*(x+y)
        Add((Add((Pow(x, 2), Mul((Num(Fraction(2)), Mul((x, y)))))),
             Pow(y, 2))),                  # x^2 + 2xy + y^2
        Mul((Add((x, one)), Add((x, one)))),          # (x+1)^2 spelled out
        Add((Add((Pow(x, 2), Mul((Num(Fraction(2)), x)))), one)),
    ]
    # dedupe by exact syntax, preserve deterministic order
    seen = set()
    unique: List[object] = []
    for expr in exprs:
        key = str_of(expr)
        if key not in seen:
            seen.add(key)
            unique.append(expr)
    return unique


def _known_identity_keys() -> set:
    """Canonical-pair keys of every identity already in the fixtures -
    the novelty gate discards rediscoveries of taught content."""
    keys = set()
    for name in ("identity_tasks.json", "mistake_package.json",
                 "arithmetic_tasks.json", "conjecture_tasks.json"):
        path = os.path.join(FIXTURE_DIR, name)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        for task in payload.get("tasks", []):
            for side_l, side_r in (("premise", "target"),
                                   ("left", "right")):
                left = task.get(side_l) or task.get(
                    "statement", {}).get(side_l)
                right = task.get(side_r) or task.get(
                    "statement", {}).get(side_r)
                if left and right:
                    try:
                        from .expr import from_json
                        keys.add(_pair_key(from_json(left),
                                           from_json(right)))
                    except Exception:
                        continue
    return keys


def _canon_key(expr: object) -> str:
    """Alpha-normalized canonical key: variable names are replaced by
    their alphabetical rank (a,b / x,y both become v0,v1), so the
    novelty gate is variable-name-blind - an identity taught as (a+b)
    blocks its rediscovery as (x+y)."""
    canon = canonical(expr)
    names = sorted({var for monomial in canon for var, _ in monomial})
    rename = {name: f"v{i}" for i, name in enumerate(names)}
    normalized = []
    for monomial, coeff in canon.items():
        remapped = tuple(sorted((rename[var], exp)
                                for var, exp in monomial))
        normalized.append((json.dumps(remapped), str(coeff)))
    return json.dumps(sorted(normalized))


def _pair_key(left: object, right: object) -> str:
    return "|".join(sorted((_canon_key(left), _canon_key(right))))


def _is_interesting(left: object, right: object) -> bool:
    """A conjecture is interesting when the two sides have different
    shapes (different root kinds) and mention at least one variable -
    filtering re-spellings and pure arithmetic."""
    if type(left) is type(right):
        return False
    has_var = any(isinstance(e, Var) for e in (left, right)) or \
        "var" in str_of(left) or "var" in str_of(right)
    return has_var


def _derivable_from_taught_axiom(left: object, right: object) -> bool:
    """The instantiation gate (audit-closure): if ONE application of a
    taught executable axiom to either side yields the other, the
    identity is an instance of taught content, not machine-novel.
    Bound disclosed: one step, either direction."""
    try:
        from .rules import AXIOM_IDS, apply_rule
    except Exception:
        return False
    for axiom_id in AXIOM_IDS:
        for source, target in ((left, right), (right, left)):
            try:
                produced = apply_rule(axiom_id, source, ())
            except Exception:
                continue
            if produced is not None and equal(produced, target):
                return True
    return False


def discover(max_theorems: int = 8) -> Dict:
    """The full discovery cycle: sealed, deterministic."""
    space = enumerate_expressions()
    known = _known_identity_keys()

    conjectures = 0
    falsified = 0
    witnesses: List[Dict] = []
    proven: List[Dict] = []
    seen_pairs = set()

    for left, right in combinations(space, 2):
        if not _is_interesting(left, right):
            continue
        conjectures += 1
        # TEST: cheap exact pruning with witnesses
        killed = None
        for point in TEST_POINTS:
            try:
                lv = eval_at(left, point)
                rv = eval_at(right, point)
            except Exception:
                killed = {"reason": "evaluation error"}
                break
            if lv != rv:
                killed = {"point": {k: str(v) for k, v in point.items()},
                          "left_value": str(lv), "right_value": str(rv)}
                break
        if killed is not None:
            falsified += 1
            if len(witnesses) < 5:
                witnesses.append({"left": str_of(left),
                                  "right": str_of(right),
                                  "witness": killed})
            continue
        # PROVE: the trusted checker is the sole validity authority
        if not equal(left, right):
            falsified += 1
            continue
        pair = _pair_key(left, right)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        derived = _derivable_from_taught_axiom(left, right)
        novel = (pair not in known) and not derived
        theorem = {
            "left": to_json(left),
            "right": to_json(right),
            "certificate": "canonical polynomial forms identical",
            "novel_to_machine": novel,
            "derived_from_taught_axiom": derived,
        }
        if novel and len(proven) < max_theorems:
            proven.append(theorem)

    packet = {
        "capability": "verified identity search v0.2 "
                      "(audit-corrected; not novel research)",
        "space_size": len(space),
        "conjectures_tested": conjectures,
        "falsified": falsified,
        "sample_witnesses": witnesses,
        "theorems": proven,
        "honesty": ("VERIFIED IDENTITY SEARCH, not novel research "
                    "(CRQS section 4: no unknown answers here); the "
                    "composite layer of the space is hand-authored and "
                    "contains showcase pairs by construction; "
                    "novel_to_machine means only: absent from fixtures "
                    "AND not one-step-derivable from taught axioms; "
                    "trivial to human mathematics"),
    }
    packet["discovery_digest"] = _digest(packet)
    return packet
