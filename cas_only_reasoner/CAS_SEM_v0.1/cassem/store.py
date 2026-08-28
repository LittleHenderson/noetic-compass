"""The Semantic CMB: queries over entities, claims, events, truth,
time - and typed lacunae for what is missing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .coherence import CoherenceChecker, Violation
from .entity import EntityRegistry
from .idea import entity_refs


@dataclass
class Lacuna:
    kind: str               # ENTITY_MISSING
    detail: str

    def to_json(self) -> Dict:
        return {"kind": self.kind, "detail": self.detail}


class SemanticCMB:
    def __init__(self, doc: Dict) -> None:
        self.doc = doc
        self.registry = EntityRegistry(doc.get("entities", []))
        self.violations: List[Violation] = CoherenceChecker(doc).check()

    def coherent(self) -> bool:
        return not self.violations

    def by_entity(self, entity_id: str) -> List[Dict]:
        out = []
        for record in self.doc.get("claims", []):
            if entity_id in entity_refs(record.get("idea", {})):
                out.append(record)
        for event in self.doc.get("events", []):
            if entity_id in entity_refs(event):
                out.append(event)
        return out

    def by_truth(self, status: str) -> List[Dict]:
        return [r for r in self.doc.get("claims", [])
                if r.get("truth") == status]

    def events_at_or_before(self, time: str, timeline) -> List[Dict]:
        reachable = set(timeline.at_or_before(time))
        return [e for e in self.doc.get("events", [])
                if e.get("time") in reachable]

    def lacunae(self) -> List[Lacuna]:
        out: List[Lacuna] = []
        for ref in self.doc.get("references", []):
            if ref.get("kind") == "name" and not self.registry.has(ref["id"]):
                out.append(Lacuna("ENTITY_MISSING",
                                  f"reference to unknown entity '{ref['id']}'"))
        for record in self.doc.get("claims", []):
            for entity_id in entity_refs(record.get("idea", {})):
                if not self.registry.has(entity_id):
                    out.append(Lacuna(
                        "ENTITY_MISSING",
                        f"idea references unknown entity '{entity_id}'"))
        return out
