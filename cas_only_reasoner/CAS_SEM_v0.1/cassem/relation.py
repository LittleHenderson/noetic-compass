"""Relation schemas: role positions are part of the content."""

from __future__ import annotations

from typing import Dict, List


class RoleError(Exception):
    pass


class RelationSchema:
    def __init__(self, schemas: Dict[str, List[str]]) -> None:
        # pred -> required role names
        self.schemas = dict(schemas)

    def check(self, pred: str, roles: Dict[str, str]) -> None:
        required = self.schemas.get(pred)
        if required is None:
            raise RoleError(f"no schema for relation '{pred}'")
        missing = [r for r in required if r not in roles]
        if missing:
            raise RoleError(
                f"relation '{pred}' missing roles {missing}")
        unknown = [r for r in roles if r not in required]
        if unknown:
            raise RoleError(
                f"relation '{pred}' has unknown roles {unknown}")
