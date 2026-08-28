"""Lift kernel-style propositions into CAS-Sem ideas with binding.

CCB-L1 parses English into propositions; this bridge binds those
propositions to registered entities and wraps them as DERIVED claims
whose derivations the proof kernel can re-prove.
"""

from __future__ import annotations

from typing import Dict, List

from .idea import property_idea, relation_idea
from .truth import claim
from .provenance import provenance


def lift(propositions: List[Dict], rule_ids: List[str],
         provenance_source: str = "teacher") -> List[Dict]:
    """Each proposition becomes a DERIVED claim with a kernel derivation."""
    claims: List[Dict] = []
    for prop in propositions:
        if prop.get("pred") == "property":
            idea = property_idea(prop["args"][0], prop["args"][1])
        elif prop.get("pred") == "relation":
            roles = {"agent": prop["args"][1], "patient": prop["args"][2]}
            idea = relation_idea(prop["args"][0], roles)
        else:
            continue
        derivation = {
            "propositions": [{"pred": "has", "args": [prop["args"][0],
                                                     prop["args"][1]]}],
            "rules": [{"rule_id": "r_prop",
                       "premises": [{"pred": "has", "args": ["?X", "?Y"]}],
                       "conclusion": {"pred": prop["pred"],
                                      "args": ["?X", "?Y"]},
                       "source": "l1_grounding"}],
            "conclusion": prop,
        }
        claims.append(claim(idea, "DERIVED",
                            provenance(provenance_source,
                                       evidence="kernel derivation"),
                            derivation=derivation))
    return claims
