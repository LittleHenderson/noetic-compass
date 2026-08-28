"""Typed entities with identity, and the registry that binds them."""

from __future__ import annotations

from typing import Dict, List, Optional


class UnknownEntity(Exception):
    def __init__(self, entity_id: str) -> None:
        super().__init__(f"unknown entity '{entity_id}'")
        self.entity_id = entity_id


class EntityRegistry:
    def __init__(self, entities: Optional[List[Dict]] = None) -> None:
        self.entities: Dict[str, Dict] = {}
        for raw in entities or []:
            self.register(raw["id"], raw.get("type", "thing"),
                          raw.get("properties", {}))

    def register(self, entity_id: str, entity_type: str,
                 properties: Optional[Dict] = None) -> Dict:
        if entity_id in self.entities:
            raise ValueError(f"entity '{entity_id}' already registered")
        entry = {"id": entity_id, "type": entity_type,
                 "properties": dict(properties or {})}
        self.entities[entity_id] = entry
        return entry

    def has(self, entity_id: str) -> bool:
        return entity_id in self.entities

    def type_of(self, entity_id: str) -> str:
        if entity_id not in self.entities:
            raise UnknownEntity(entity_id)
        return self.entities[entity_id]["type"]

    def property_of(self, entity_id: str, prop: str) -> Optional[str]:
        if entity_id not in self.entities:
            raise UnknownEntity(entity_id)
        return self.entities[entity_id]["properties"].get(prop)

    def remove(self, entity_id: str) -> None:
        if entity_id not in self.entities:
            raise UnknownEntity(entity_id)
        del self.entities[entity_id]

    def ids(self) -> List[str]:
        return sorted(self.entities)
