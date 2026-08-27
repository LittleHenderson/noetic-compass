"""Cognitive Differential Amplifier Board — controlled comparison.

The design requirement the audit credited: candidates must be compared under
matched gain and a shared bias, so the comparator amplifies only genuine
divergence. Otherwise "the comparator invents differences from its own
asymmetry" — an artifact of the instrument, not a finding about the candidates.

This module enforces that rather than documenting it: a comparison with
mismatched gain or unshared bias raises, it does not silently return a number.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class CdabError(ValueError):
    """The comparator refuses to run — its own asymmetry would fake a result."""


@dataclass(frozen=True)
class Candidate:
    label: str
    bias: str
    beta: float
    activation: float


@dataclass(frozen=True)
class Difference:
    winner: str | None
    margin: float
    common_mode_rejected: float
    note: str = ""


def compare(a: Candidate, b: Candidate, *, tolerance: float = 1e-9) -> Difference:
    """Differential comparison of two candidates under a shared bias.

    Rejects the common mode (what the candidates share) and returns only the
    divergence. A tie inside `tolerance` has no winner — the comparator does not
    manufacture a preference it cannot see.
    """
    if a.bias != b.bias:
        raise CdabError(
            f"unshared bias: {a.label} biased by {a.bias!r}, {b.label} by {b.bias!r}; "
            "a differential comparison requires the same bias on both inputs"
        )
    if not math.isclose(a.beta, b.beta, rel_tol=1e-12, abs_tol=1e-12):
        raise CdabError(
            f"mismatched gain: {a.label} beta={a.beta}, {b.label} beta={b.beta}; "
            "matched gain is required or the comparator's asymmetry becomes the result"
        )

    common = min(a.activation, b.activation)
    delta = (a.activation - b.activation) * a.beta

    if abs(delta) <= tolerance:
        return Difference(None, 0.0, common, "tie — no meaningful divergence")
    winner = a.label if delta > 0 else b.label
    return Difference(winner, abs(delta), common)


def tournament(candidates: list[Candidate], *, tolerance: float = 1e-9) -> Difference:
    """Scale past two candidates without one opaque comparison.

    Runs a knockout of pairwise CDAB comparisons, which keeps every step
    individually probeable. A tie retains the incumbent.
    """
    if len(candidates) < 2:
        raise CdabError("a tournament requires at least two candidates")

    incumbent = candidates[0]
    last = Difference(incumbent.label, 0.0, incumbent.activation, "single entrant")
    for challenger in candidates[1:]:
        last = compare(incumbent, challenger, tolerance=tolerance)
        if last.winner == challenger.label:
            incumbent = challenger
    return Difference(incumbent.label, last.margin, last.common_mode_rejected)
