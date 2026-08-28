"""The measurement protocol: manifests, disjoint splits, sources."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple


class ProtocolError(Exception):
    pass


def make_manifest(profile_id: str, calibration: List[int],
                  validation: List[int], doses: List[float],
                  responses: List[float], source: str = "synthetic_mock") -> Dict:
    if len(doses) != len(responses):
        raise ProtocolError("doses and responses must align")
    if not calibration or not validation:
        raise ProtocolError("both splits are required")
    overlap = set(calibration) & set(validation)
    if overlap:
        raise ProtocolError(
            f"calibration and validation splits must be DISJOINT; "
            f"overlap {sorted(overlap)} (R7)")
    for index in list(calibration) + list(validation):
        if not 0 <= index < len(doses):
            raise ProtocolError(f"index {index} out of range")
    manifest = {
        "profile_id": profile_id,
        "calibration_indices": list(calibration),
        "validation_indices": list(validation),
        "typed_quantities": {
            "alpha_dose": list(doses),
            "activation_response": list(responses),
        },
        "source": source,
    }
    manifest["digest"] = _digest(manifest)
    return manifest


def _digest(obj: Dict) -> str:
    payload = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def synthetic_series(profile_id: str, seed: int = 7,
                     n: int = 12) -> Tuple[List[float], List[float]]:
    """A deterministic synthetic activation source. Explicitly NOT a
    model: the label synthetic_mock travels with every report."""
    doses: List[float] = []
    responses: List[float] = []
    state = seed
    for i in range(n):
        state = (state * 1103515245 + 12345) % (2 ** 31)
        dose = 0.2 + (state % 90) / 100.0
        state = (state * 1103515245 + 12345) % (2 ** 31)
        noise = ((state % 21) - 10) / 500.0
        response = 0.9 * dose + 0.1 + noise
        doses.append(round(dose, 3))
        responses.append(round(max(response, 0.0), 4))
    return doses, responses
