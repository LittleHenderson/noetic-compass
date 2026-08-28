"""ASOM: operating condition from region and outcome, independently.

Active does not mean intelligent. High gain does not mean correct.
Saturation does not mean expert. The classification keeps the region
axis and the outcome axis SEPARATE and reports the cell.
"""

from __future__ import annotations

from typing import Dict, List

REGIONS = ("cutoff", "active", "saturation", "breakdown")
OUTCOMES = ("correct", "incorrect", "off_axis", "unknown")


def classify(region: str, outcome: str) -> str:
    if region not in REGIONS:
        raise ValueError(f"unknown region {region}")
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome {outcome}")
    if region == "active" and outcome == "correct":
        return "Aligned"
    if region == "active":
        return "Misaligned"          # active but wrong or off-axis
    if region in ("cutoff", "breakdown"):
        return "Starved" if region == "cutoff" else "Misaligned"
    # saturation: output is bounded; correctness is decided by OUTCOME.
    return "Oversaturated" if outcome == "correct" else "Misaligned"


def classify_batch(rows: List[Dict]) -> List[Dict]:
    return [{"region": r["region"], "outcome": r["outcome"],
             "asom": classify(r["region"], r["outcome"])} for r in rows]
