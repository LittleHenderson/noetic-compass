"""The counterexample generator: exact search over the declared domain.

A counterexample immediately invalidates a universal conjecture under
the same declared assumptions. The witness carries exact evaluations.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Dict, List, Tuple

from .expr import eval_at, from_json
from .exact import q_str, relation_holds


def find_counterexample(statement: Dict, domain: Tuple[int, ...] = (1, 2, 3, 4, 5),
                        max_vars: int = 3) -> Dict:
    var_names = list(statement.get("vars", []))
    if len(var_names) > max_vars:
        raise ValueError(f"counterexample search caps at {max_vars} variables")
    relation = statement["relation"]
    left = from_json(statement["left"])
    right = from_json(statement["right"])

    for combo in product(domain, repeat=len(var_names)):
        env = {name: Fraction(value) for name, value in zip(var_names, combo)}
        left_v = eval_at(left, env)
        right_v = eval_at(right, env)
        if not relation_holds(relation, left_v, right_v):
            return {
                "found": True,
                "point": {k: str(v) for k, v in env.items()},
                "left_value": q_str(left_v),
                "right_value": q_str(right_v),
                "witness_relation": f"{q_str(left_v)} does not satisfy "
                                    f"{relation} vs {q_str(right_v)}",
            }
    return {
        "found": False,
        "searched": len(domain) ** len(var_names),
        "note": f"no counterexample in domain {list(domain)} "
                f"over variables {var_names}",
    }
