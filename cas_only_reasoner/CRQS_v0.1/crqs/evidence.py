"""Evidence maturity tiers: E0 Claimed through E6 Independently Replicated."""

from __future__ import annotations

from typing import Dict, List

TIERS: List[Dict] = [
    {"tier": "E0", "meaning": "someone says the capability exists"},
    {"tier": "E1", "meaning": "required components and connections appear present"},
    {"tier": "E2", "meaning": "compiler and design-rule checks pass"},
    {"tier": "E3", "meaning": "behavior runs in the declared deterministic simulator"},
    {"tier": "E4", "meaning": "public and protected conformance suites pass"},
    {"tier": "E5", "meaning": "capability generalizes to unseen tasks"},
    {"tier": "E6", "meaning": "a separate implementation or evaluator reproduces it"},
]

# v0.1 defaults: the highest generation a given evidence tier can support.
EVIDENCE_CEILING = {
    "E0": "CAS-G0", "E1": "CAS-G1", "E2": "CAS-G2", "E3": "CAS-G3",
    "E4": "CAS-G7", "E5": "CAS-G9", "E6": "CAS-G10",
}


def tier_from_manifest(manifest: Dict) -> str:
    evidence = manifest.get("evidence", {})
    suites = evidence.get("suites", [])
    if not suites:
        return "E0"
    if all(s.get("passed", 0) == s.get("tests", 0) for s in suites) \
            and evidence.get("violations"):
        if any(s.get("held_out") for s in suites):
            return "E5"
        return "E4"
    if manifest.get("topology"):
        return "E1"
    return "E0"
