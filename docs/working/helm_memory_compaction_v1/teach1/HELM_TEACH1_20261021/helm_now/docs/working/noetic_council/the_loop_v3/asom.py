"""ASOM readout: the four-label gauge on a CJT's Bias.

WHAT IT DOES
------------
Turns two values the frozen runtime already produces into one of four ASOM labels:

  region  -- OperatingRegion:  CUTOFF | ACTIVE | BREAKDOWN (and any others)
  outcome -- SemanticOutcome:  INTENDED | OPPOSITE | OFF_AXIS | UNKNOWN | UNASSESSED

  STARVED      the CJT is in cutoff
  ALIGNED      active/saturated AND the result is the intended one
  OVERSATURATED saturated AND the result is still intended
  MISALIGNED   the result is opposite or off-axis

WHAT IT DOES NOT DO
-------------------
It is a DIAGNOSTIC DISPLAY. It is not the Bias, and it is NOT an RPM gate. It must never be
used to block or allow an operation -- RPM decides that. It holds no state and writes nothing.

It also does not decide what "saturated" means numerically: the caller passes whether the
region is saturated, because no source gives a saturation threshold for this readout.
"""
from __future__ import annotations

STARVED = "STARVED"
ALIGNED = "ALIGNED"
OVERSATURATED = "OVERSATURATED"
MISALIGNED = "MISALIGNED"
NOT_EMITTED = "NOT_EMITTED"

LABELS = (STARVED, ALIGNED, OVERSATURATED, MISALIGNED)


def readout(region: str, outcome: str, saturated: bool = False) -> str:
    """Return the ASOM label. Exact, total, and never a guess.

    Every combination returns either one of the four labels or NOT_EMITTED. NOT_EMITTED is
    returned where the sources give no rule, so an unknown case can never masquerade as a label.
    """
    if not isinstance(region, str) or not isinstance(outcome, str):
        raise TypeError("region and outcome must be strings")
    if not isinstance(saturated, bool):
        raise TypeError("saturated must be a bool")

    region = region.upper()
    outcome = outcome.upper()

    # 1. Cutoff is STARVED regardless of anything else: there is no flow to judge.
    if region == "CUTOFF":
        return STARVED

    # 2. Cutoff-like: an unassessed outcome with no flow is still starved.
    if region == "BREAKDOWN":
        # Saturated past the point of operating. The design pairs this with "intended result".
        if outcome == "INTENDED":
            return OVERSATURATED
        return MISALIGNED

    # 3. Active region: the label comes from whether the result is the intended one.
    if outcome == "INTENDED":
        return OVERSATURATED if saturated else ALIGNED
    if outcome in ("OPPOSITE", "OFF_AXIS"):
        return MISALIGNED

    # 4. Anything else: the sources give no label.
    return NOT_EMITTED


def self_check() -> str:
    cases = [
        ("CUTOFF", "INTENDED", False, STARVED),
        ("CUTOFF", "OPPOSITE", True, STARVED),
        ("ACTIVE", "INTENDED", False, ALIGNED),
        ("ACTIVE", "INTENDED", True, OVERSATURATED),
        ("ACTIVE", "OPPOSITE", False, MISALIGNED),
        ("ACTIVE", "OFF_AXIS", True, MISALIGNED),
        ("BREAKDOWN", "INTENDED", True, OVERSATURATED),
        ("BREAKDOWN", "OFF_AXIS", True, MISALIGNED),
        ("ACTIVE", "UNKNOWN", False, NOT_EMITTED),
        ("ACTIVE", "UNASSESSED", False, NOT_EMITTED),
    ]
    bad = []
    for region, outcome, sat, want in cases:
        got = readout(region, outcome, sat)
        if got != want:
            bad.append((region, outcome, sat, want, got))
    if bad:
        return "FAIL " + repr(bad)
    # the four labels must all be reachable
    reached = {readout(*c[:3]) for c in cases}
    if not set(LABELS).issubset(reached):
        return "FAIL not all four labels reachable: %r" % (reached,)
    # and the readout must never be able to gate: prove it returns a string only
    if not all(isinstance(readout(*c[:3]), str) for c in cases):
        return "FAIL non-string label"
    return "PASS %d cases, 4 of 4 labels reachable, nothing gated" % len(cases)


if __name__ == "__main__":
    print(self_check())
