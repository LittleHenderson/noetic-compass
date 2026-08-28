"""Truth statuses and the truth discipline.

VERIFIED and CONTRADICTED are mutually exclusive. DERIVED claims must
carry a derivation. CONTRADICTED claims must carry the pair of
conflicting supports.
"""

from __future__ import annotations

from typing import Dict, List, Optional

TRUTH_STATUSES = (
    "GIVEN", "ASSUMED", "DERIVED", "OBSERVED", "VERIFIED",
    "CONJECTURED", "CONTRADICTED", "UNKNOWN", "UNDERDETERMINED",
)


class TruthViolation(Exception):
    pass


def claim(idea: Dict, truth: str, provenance: Dict,
          derivation: Optional[Dict] = None,
          conflict: Optional[Dict] = None) -> Dict:
    if truth not in TRUTH_STATUSES:
        raise TruthViolation(f"unknown truth status '{truth}'")
    record = {"idea": idea, "truth": truth, "provenance": provenance}
    if derivation is not None:
        record["derivation"] = derivation
    if conflict is not None:
        record["conflict"] = conflict
    check_claim(record)
    return record


def check_claim(record: Dict) -> None:
    truth = record.get("truth")
    if truth == "DERIVED" and not record.get("derivation"):
        raise TruthViolation("DERIVED claim must carry a derivation")
    if truth == "CONTRADICTED" and not record.get("conflict"):
        raise TruthViolation(
            "CONTRADICTED claim must carry the conflicting support pair")


def check_pairwise(a: Dict, b: Dict) -> None:
    """Two claims about the SAME idea must not be VERIFIED and
    CONTRADICTED together."""
    if a.get("idea") != b.get("idea"):
        return
    truths = {a.get("truth"), b.get("truth")}
    if truths == {"VERIFIED", "CONTRADICTED"}:
        raise TruthViolation(
            f"idea {a['idea']} is both VERIFIED and CONTRADICTED")
