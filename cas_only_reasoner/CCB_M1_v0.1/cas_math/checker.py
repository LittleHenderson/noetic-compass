"""The trusted proof checker - the sole validity authority.

Walks proof steps in order (oscilloscope walk-down), enforces
continuity, verifies axiom steps structurally, validates procedure
steps with exact sample evaluation, and finally requires canonical
equality with the target. Returns VERIFIED or REJECTED with the first
invalid step. No mathematical conclusion is VERIFIED without this
checker's acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import product
from typing import Dict, List, Optional, Tuple

from .expr import (canonical, equal, eval_at, from_json, to_json,
                   variables)
from .rules import apply_rule, kind_of


@dataclass
class CheckOutcome:
    verdict: str                  # VERIFIED | REJECTED
    first_invalid_step: Optional[int]   # 0-based step index, or None
    reason: str
    sample_witness: Optional[Dict] = None   # for procedure failures

    def to_json(self) -> Dict:
        return {
            "verdict": self.verdict,
            "first_invalid_step": self.first_invalid_step,
            "reason": self.reason,
            "sample_witness": self.sample_witness,
        }


def _sample_points(var_names: List[str],
                   values: Tuple[int, ...] = (1, 2, 3)) -> List[Dict[str, Fraction]]:
    if len(var_names) > 3:
        raise ValueError("sample validation caps at three variables in v0.1")
    return [dict(zip(var_names, combo))
            for combo in product((Fraction(v) for v in values),
                                 repeat=len(var_names))]


def check(premise: object, target: object, steps: List[Dict],
          sample_values: Tuple[int, ...] = (1, 2, 3)) -> CheckOutcome:
    current = premise
    for index, step in enumerate(steps):
        rule_id = step.get("rule")
        focus = tuple(step.get("focus", []))
        claimed = from_json(step["to"])
        try:
            applied = apply_rule(rule_id, current, focus)
        except Exception as exc:  # RuleError or navigation failure
            return CheckOutcome("REJECTED", index,
                                f"step {index}: rule {rule_id} failed: {exc}")
        if not equal(applied, claimed):
            return CheckOutcome("REJECTED", index,
                                f"step {index}: {rule_id} output does not "
                                f"match the claimed expression")
        if kind_of(rule_id) == "procedure":
            vars_here = sorted(set(variables(current) + variables(claimed)))
            for point in _sample_points(vars_here, sample_values):
                left = eval_at(current, point)
                right = eval_at(claimed, point)
                if left != right:
                    return CheckOutcome(
                        "REJECTED", index,
                        f"step {index}: procedure {rule_id} is not "
                        f"equality-preserving at {point}: "
                        f"{left} != {right}",
                        sample_witness={"point": {k: str(v) for k, v in point.items()},
                                        "left": str(left), "right": str(right)})
        current = claimed

    if not equal(current, target):
        return CheckOutcome("REJECTED", None,
                            "conclusion does not match the target; "
                            "canonical forms differ")
    return CheckOutcome("VERIFIED", None, "all steps valid; target reached")
