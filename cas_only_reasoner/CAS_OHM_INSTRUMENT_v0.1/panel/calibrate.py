"""Calibration and validation, profile-specific and split-disjoint."""

from __future__ import annotations

from typing import Dict, List, Tuple

from .protocol import ProtocolError


def fit_effective_resistance(manifest: Dict) -> Dict:
    """Fit R_eff on the CALIBRATION split only (design quantity)."""
    doses = manifest["typed_quantities"]["alpha_dose"]
    responses = manifest["typed_quantities"]["activation_response"]
    indices = manifest["calibration_indices"]
    ratios = []
    for i in indices:
        r = responses[i]
        d = doses[i]
        ratios.append(d / r if r > 0 else float("inf"))
    r_eff = sum(ratios) / len(ratios) if ratios else 0.0
    return {
        "profile_id": manifest["profile_id"],
        "effective_resistance": round(r_eff, 4),
        "fitted_on_indices": list(indices),
        "note": "profile-specific design quantity; no live calibration "
                "is admitted (R7)",
    }


def validate(manifest: Dict, calibration: Dict) -> Dict:
    """Predict on the DISJOINT validation split and rank residuals."""
    doses = manifest["typed_quantities"]["alpha_dose"]
    responses = manifest["typed_quantities"]["activation_response"]
    r_eff = calibration["effective_resistance"]
    rows = []
    for i in manifest["validation_indices"]:
        predicted = doses[i] / r_eff if r_eff > 0 else 0.0
        residual = responses[i] - predicted
        rows.append({
            "index": i,
            "observed": responses[i],
            "predicted": round(predicted, 4),
            "residual": round(residual, 4),
        })
    rows.sort(key=lambda r: -abs(r["residual"]))
    return {
        "profile_id": manifest["profile_id"],
        "validation_rows": rows,
        "residuals_rank_follow_up_probes": True,
        "residuals_identify_causes": False,   # R6: never by sign alone
    }
