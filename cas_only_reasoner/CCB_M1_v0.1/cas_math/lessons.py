"""Mistake diagnosis and the lesson library.

Diagnosis reads ONLY the checker outcome and the failed proof: it
locates the first invalid step and names the guilty rule. Repairs come
from the bounded lesson library - the board does not invent new math
from nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .checker import CheckOutcome


@dataclass
class MathFault:
    first_invalid_step: Optional[int]
    guilty_rule: Optional[str]
    classification: str      # procedure_not_equality_preserving |
                             # conclusion_mismatch | rule_application_failed
    detail: str

    def to_json(self) -> Dict:
        return {
            "first_invalid_step": self.first_invalid_step,
            "guilty_rule": self.guilty_rule,
            "classification": self.classification,
            "detail": self.detail,
        }


def diagnose(outcome: CheckOutcome, steps: List[Dict]) -> MathFault:
    if outcome.verdict == "VERIFIED":
        raise ValueError("diagnose() needs a rejected outcome")
    index = outcome.first_invalid_step
    guilty = steps[index].get("rule") if index is not None else None
    if "procedure" in outcome.reason:
        return MathFault(index, guilty, "procedure_not_equality_preserving",
                         outcome.reason)
    if "conclusion" in outcome.reason:
        return MathFault(None, None, "conclusion_mismatch", outcome.reason)
    return MathFault(index, guilty, "rule_application_failed", outcome.reason)


# The lesson library: bounded, authored, correct repairs.
LESSON_LIBRARY: Dict[str, List[Dict]] = {
    "square_sum": [
        {
            "kind": "replace_rule",
            "rule_id": "square_sum",
            "replacement": "square_expand",
            "ring": "R1",
            "note": "replace the incorrect (a+b)^2 -> a^2+b^2 procedure "
                    "with the correct square expansion axiom",
        },
    ],
}


def propose_repairs(fault: MathFault) -> List[Dict]:
    if fault.guilty_rule is None:
        return []
    return list(LESSON_LIBRARY.get(fault.guilty_rule, []))
