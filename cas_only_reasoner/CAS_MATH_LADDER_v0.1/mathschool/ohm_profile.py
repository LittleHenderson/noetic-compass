"""The CAS-Ohm learning profile for mathematics: MEASURES how the
student is learning; never decides whether an equation is true.

P_cap = the fraction of the protected exercises the student can
actually solve; R_cap = 1 - P_cap (the capability resistance proxy);
flow = cutoff (nothing passes) / partial / active. Authored, exact,
compute-only - the same authority note as every CAS-Ohm record."""

from __future__ import annotations

from typing import Dict, List

AUTHORITY_NOTE = ("compute-only: no truth, validity, meaning, "
                  "commitment, or permission decision may read this "
                  "record")


def _p_cap(student, exercises: List[Dict]) -> float:
    from .ladder import grade
    passed = sum(1 for e in exercises
                 if grade(e, student.solve(e))["passed"])
    return round(passed / len(exercises), 4) if exercises else 0.0


def _flow(p_cap: float) -> str:
    if p_cap == 0.0:
        return "cutoff"
    if p_cap < 1.0:
        return "partial"
    return "active"


def before(student, held_out: List[Dict]) -> Dict:
    p_cap = _p_cap(student, held_out)
    return {"P_cap_before": p_cap,
            "R_cap_before": round(1.0 - p_cap, 4),
            "flow_before": _flow(p_cap),
            "authority_note": AUTHORITY_NOTE}


def after(profile: Dict, student, held_out: List[Dict]) -> Dict:
    p_cap = _p_cap(student, held_out)
    out = dict(profile)
    out.update({"P_cap_after": p_cap,
                "R_cap_after": round(1.0 - p_cap, 4),
                "flow_after": _flow(p_cap)})
    return out
