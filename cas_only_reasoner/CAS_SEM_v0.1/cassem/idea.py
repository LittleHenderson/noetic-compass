"""Idea structures: the semantic payloads of CAS-Sem.

Every idea is a JSON-safe dict with a kind discriminator.
"""

from __future__ import annotations

from typing import Dict, List


def property_idea(entity: str, prop: str) -> Dict:
    return {"kind": "property", "entity": entity, "property": prop}


def relation_idea(pred: str, roles: Dict[str, str]) -> Dict:
    return {"kind": "relation", "pred": pred, "roles": dict(roles)}


def event_idea(pred: str, roles: Dict[str, str], time: str,
               aspect: str = "completed") -> Dict:
    return {"kind": "event", "pred": pred, "roles": dict(roles),
            "time": time, "aspect": aspect}


def negation_idea(inner: Dict) -> Dict:
    return {"kind": "negation", "inner": inner}


def quantifier_idea(q: str, variable: str, inner: Dict) -> Dict:
    return {"kind": "quantifier", "quantifier": q, "variable": variable,
            "inner": inner}


def modality_idea(m: str, inner: Dict) -> Dict:
    return {"kind": "modality", "modality": m, "inner": inner}


def walk_ideas(idea: Dict) -> List[Dict]:
    """All nested ideas, in document order."""
    out = [idea]
    if idea.get("kind") == "negation":
        out.extend(walk_ideas(idea["inner"]))
    elif idea.get("kind") in ("quantifier", "modality"):
        out.extend(walk_ideas(idea["inner"]))
    return out


def entity_refs(idea: Dict) -> List[str]:
    """Every entity id mentioned anywhere inside the idea."""
    refs: List[str] = []
    for node in walk_ideas(idea):
        if node.get("kind") == "property":
            refs.append(node["entity"])
        elif node.get("kind") in ("relation", "event"):
            refs.extend(node.get("roles", {}).values())
    return refs
