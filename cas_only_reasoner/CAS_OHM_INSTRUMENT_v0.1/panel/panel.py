"""The panel orchestrator: manifest -> calibration -> validation ->
ASOM -> report."""

from __future__ import annotations

from typing import Dict, List

from .asom import classify_batch
from .calibrate import fit_effective_resistance, validate
from .protocol import make_manifest, synthetic_series


def run(profile_id: str, calibration: List[int], validation: List[int],
        doses: List[float], responses: List[float],
        asom_rows: List[Dict], source: str = "synthetic_mock") -> Dict:
    manifest = make_manifest(profile_id, calibration, validation,
                             doses, responses, source)
    calibration_record = fit_effective_resistance(manifest)
    validation_record = validate(manifest, calibration_record)
    return {
        "manifest": manifest,
        "calibration": calibration_record,
        "validation": validation_record,
        "asom_rows": classify_batch(asom_rows),
    }


def demo_run() -> Dict:
    doses, responses = synthetic_series("profile_demo")
    asom_rows = [
        {"region": "active", "outcome": "correct"},
        {"region": "active", "outcome": "incorrect"},
        {"region": "saturation", "outcome": "correct"},
        {"region": "cutoff", "outcome": "correct"},
    ]
    return run("profile_demo",
               calibration=[0, 1, 2, 3, 4, 5],
               validation=[6, 7, 8, 9, 10, 11],
               doses=doses, responses=responses,
               asom_rows=asom_rows)
