"""The instrument report: every restriction printed verbatim."""

from __future__ import annotations

from typing import Dict, List

RESTRICTIONS = [
    "R1: CAS-Ohm is NOT physical Ohm's law.",
    "R2: It is NOT an electrical implementation.",
    "R3: It is NOT a measure of attention.",
    "R4: It is NOT a causal law.",
    "R5: Series, parallel, and gain composition are capability-gated "
    "structural research calculations, not universal laws.",
    "R6: A residual can rank follow-up probes; it CANNOT identify a "
    "hidden cause, policy, bypass, or failure by sign alone.",
    "R7: No live calibration is admitted; calibration and validation "
    "splits are disjoint and enforced.",
    "R8: History-dependent dynamics remain open.",
    "R9: Whether the model predicts anything is decided by controlled, "
    "independently audited experiments.",
    "R10: The reasoning runtime does not depend on any CAS-Ohm quantity.",
]


def format_report(result: Dict) -> str:
    lines: List[str] = ["CAS-OHM INSTRUMENT REPORT", ""]
    lines.append(f"Profile:")
    lines.append(f"    {result['manifest']['profile_id']}")
    lines.append("")
    lines.append(f"Source:")
    lines.append(f"    {result['manifest']['source']} "
                 f"(deterministic; no model was measured)")
    lines.append("")
    lines.append(f"Calibration:")
    lines.append(f"    R_eff = {result['calibration']['effective_resistance']} "
                 f"(profile-specific design quantity, "
                 f"fitted on {result['calibration']['fitted_on_indices']})")
    lines.append("")
    lines.append(f"Validation:")
    lines.append(f"    {len(result['validation']['validation_rows'])} "
                 f"disjoint held-out rows; residuals RANK follow-up probes "
                 f"only, and identify NO causes (R6)")
    lines.append("")
    lines.append(f"ASOM (operating condition, not intelligence):")
    for row in result["asom_rows"]:
        lines.append(f"    {row['region']:<12} + {row['outcome']:<10} "
                     f"-> {row['asom']}")
    lines.append("")
    lines.append("Boundary statements:")
    for restriction in RESTRICTIONS:
        lines.append(f"    {restriction}")
    lines.append("")
    lines.append("Live calibration admitted: NO")
    lines.append("Causal claims made: NONE")
    lines.append("Attention measured: NO")
    lines.append("Controlled experiments: PENDING")
    return "\n".join(lines)
