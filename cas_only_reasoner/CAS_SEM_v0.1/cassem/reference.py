"""References and binding: which entity a word or pronoun refers to."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .entity import EntityRegistry


class UnresolvedReference(Exception):
    def __init__(self, ref: Dict, detail: str) -> None:
        super().__init__(f"unresolved reference {ref}: {detail}")
        self.ref = ref
        self.detail = detail


@dataclass
class DiscourseState:
    last_entity: Optional[str] = None

    def mention(self, entity_id: str) -> None:
        self.last_entity = entity_id


class Resolver:
    def __init__(self, registry: EntityRegistry,
                 discourse: Optional[DiscourseState] = None) -> None:
        self.registry = registry
        self.discourse = discourse or DiscourseState()

    def resolve(self, ref: Dict) -> str:
        kind = ref.get("kind")
        if kind == "name":
            entity_id = ref["id"]
            if not self.registry.has(entity_id):
                raise UnresolvedReference(ref, f"entity '{entity_id}' missing")
            self.discourse.mention(entity_id)
            return entity_id
        if kind == "pronoun":
            if self.discourse.last_entity is None:
                raise UnresolvedReference(ref, "pronoun has no antecedent")
            return self.discourse.last_entity
        if kind == "description":
            entity_type = ref.get("type")
            constraints = ref.get("constraints", {})
            matches = [eid for eid in self.registry.ids()
                       if self.registry.type_of(eid) == entity_type
                       and all(self.registry.property_of(eid, k) == v
                               for k, v in constraints.items())]
            if len(matches) == 1:
                self.discourse.mention(matches[0])
                return matches[0]
            if not matches:
                raise UnresolvedReference(ref, "no entity matches description")
            raise UnresolvedReference(ref, f"ambiguous: {matches}")
        raise UnresolvedReference(ref, f"unknown reference kind {kind}")
