"""Phase 8: CDAB candidate comparison.

The Cognitive Differential Amplifier Board compares two ideas under a
SHARED bias, cancels what they have in common, and amplifies only their
meaningful divergence. The non-negotiable invariants are matched gains and
a shared bias; otherwise the comparator invents differences from its own
asymmetry (spec Ch. 10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .ontology import GAIN_EVAL
from .terms import Atom, match


@dataclass
class DifferenceReport:
    a_id: str
    b_id: str
    shared_bias: str
    matched_gain: float
    common: List[str] = field(default_factory=list)
    divergence: Dict[str, str] = field(default_factory=dict)
    winner: Optional[str] = None
    reason: str = ""

    def to_dict(self):
        return {
            "a": self.a_id,
            "b": self.b_id,
            "shared_bias": self.shared_bias,
            "matched_gain": self.matched_gain,
            "common": list(self.common),
            "divergence": dict(self.divergence),
            "winner": self.winner,
            "reason": self.reason,
        }


def candidate_merit(candidate, decomposition, inference, goal):
    """Deterministic structural merit under the shared goal bias.

    Returns (eligible, score_tuple, explanation). Ineligible candidates are
    those that do not target the goal's desired outcome or are FALSIFIED.
    A CONTRADICTED candidate remains eligible so the contradiction can
    surface as a conflict instead of being silently eliminated.
    """
    goal_match = match(goal.desired_outcome, candidate.target) is not None
    provable = inference.success
    if not goal_match:
        return False, None, "does not target the goal's desired outcome"
    if inference.contradiction_status == "FALSIFIED":
        return False, None, "falsified: the negation is proven"
    if not provable:
        return False, None, "unsupported: no complete proof path"
    goal_delta = decomposition.predicted_effects.get(goal.foundation_ref, 0.0)
    clean = 1 if inference.contradiction_status == "NONE" else 0
    score = (
        goal_delta,                             # advance toward the goal channel
        clean,                                  # clean over contradicted
        len(inference.premises_used),           # more support is better
        inference.confidence,                   # then confidence
        -len(inference.unresolved_unknowns),    # fewer unknowns
        -ord(candidate.candidate_id[-1]),       # deterministic tiebreak
    )
    return True, score, "admissible and proven"


class CDAB:
    def compare(self, a, b, goal, decomposition_map, inference_map,
                effects_map) -> DifferenceReport:
        shared_bias = goal.foundation_ref
        report = DifferenceReport(a_id=a.candidate_id, b_id=b.candidate_id,
                                  shared_bias=shared_bias, matched_gain=GAIN_EVAL)

        ia, ib = inference_map[a.candidate_id], inference_map[b.candidate_id]
        da, db = decomposition_map[a.candidate_id], decomposition_map[b.candidate_id]

        common_premises = set(da.premises_matched) & set(db.premises_matched)
        report.common = sorted(common_premises)

        report.divergence = {
            "conclusion_a": str(a.target),
            "conclusion_b": str(b.target),
            "support_a": f"{len(ia.premises_used)} premises via {ia.rules_used or 'no rules'}",
            "support_b": f"{len(ib.premises_used)} premises via {ib.rules_used or 'no rules'}",
            "contradiction_a": ia.contradiction_status,
            "contradiction_b": ib.contradiction_status,
            "unknowns_a": f"{len(ia.unresolved_unknowns)}",
            "unknowns_b": f"{len(ib.unresolved_unknowns)}",
        }
        # Foundation-profile divergence under the shared bias.
        for channel, delta_a in da.predicted_effects.items():
            delta_b = db.predicted_effects.get(channel, 0.0)
            if delta_a != delta_b:
                report.divergence[f"channel_{channel}"] = f"{delta_a:+.2f} vs {delta_b:+.2f}"

        eligible_a, score_a, reason_a = candidate_merit(a, da, ia, goal)
        eligible_b, score_b, reason_b = candidate_merit(b, db, ib, goal)

        if eligible_a and eligible_b:
            if score_a > score_b:
                report.winner, report.reason = a.candidate_id, "higher structural support"
            else:
                report.winner, report.reason = b.candidate_id, "higher structural support"
        elif eligible_a:
            report.winner, report.reason = a.candidate_id, f"b ineligible: {reason_b}"
        elif eligible_b:
            report.winner, report.reason = b.candidate_id, f"a ineligible: {reason_a}"
        else:
            report.winner, report.reason = None, f"both ineligible: {reason_a} | {reason_b}"
        return report


class Tournament:
    """Deterministic elimination tree over the candidate set."""

    def run(self, candidates, goal, decomposition_map, inference_map,
            effects_map) -> Dict:
        reports: List[DifferenceReport] = []
        eliminated: Dict[str, str] = {}
        cdab = CDAB()
        active = sorted(candidates, key=lambda c: c.candidate_id)
        if not active:
            return {"winner": None, "reports": [], "eliminated": {},
                    "explanation": "no candidates to compare"}

        while len(active) > 1:
            a, b = active[0], active[1]
            report = cdab.compare(a, b, goal, decomposition_map, inference_map,
                                  effects_map)
            reports.append(report)
            if report.winner == a.candidate_id:
                eliminated[b.candidate_id] = report.reason
                active = [a] + active[2:]
            elif report.winner == b.candidate_id:
                eliminated[a.candidate_id] = report.reason
                active = [b] + active[2:]
            else:
                # Neither eligible: both leave the bracket; no winner advances.
                eliminated[a.candidate_id] = report.reason
                eliminated[b.candidate_id] = report.reason
                active = active[2:]

        winner = active[0].candidate_id if active else None
        return {
            "winner": winner,
            "reports": [r.to_dict() for r in reports],
            "eliminated": eliminated,
            "targets": {c.candidate_id: str(c.target) for c in candidates},
            "candidates": [c.candidate_id for c in candidates],
            "explanation": "pairwise elimination under shared bias and matched gain",
        }
