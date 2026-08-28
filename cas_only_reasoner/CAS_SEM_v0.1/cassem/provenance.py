"""Provenance: who said it, when, and what evidence supports it."""

from __future__ import annotations

from typing import Dict, Optional

PROVENANCE_SOURCES = (
    "teacher", "book", "prior_proof", "generated_conjecture",
    "verified_calculation", "observation",
)


class ProvenanceViolation(Exception):
    pass


def provenance(source: str, evidence: Optional[str] = None,
               when: Optional[str] = None) -> Dict:
    if source not in PROVENANCE_SOURCES:
        raise ProvenanceViolation(f"unknown provenance source '{source}'")
    record: Dict = {"source": source}
    if evidence is not None:
        record["evidence"] = evidence
    if when is not None:
        record["when"] = when
    return record
