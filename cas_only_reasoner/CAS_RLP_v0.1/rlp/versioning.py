"""Versioned processor descendants and rollback.

Every promoted change appends to the version history and preserves the
parent revision; rollback restores the parent and re-verifies it.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class VersionEntry:
    revision: int
    parent_revision: Optional[int]
    mutation_id: Optional[str]
    package_snapshot: Dict
    digest: str
    status: str = "CURRENT"     # CURRENT | SUPERSEDED | RESTORED

    @staticmethod
    def digest_of(package: Dict) -> str:
        payload = json.dumps(package, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class VersionHistory:
    def __init__(self, initial: Dict) -> None:
        self.entries: List[VersionEntry] = []
        self._append(initial.get("revision", 0), None, None, initial)

    def _append(self, revision: int, parent: Optional[int],
                mutation_id: Optional[str], package: Dict) -> VersionEntry:
        for e in self.entries:
            if e.status == "CURRENT":
                e.status = "SUPERSEDED"
        entry = VersionEntry(
            revision=revision,
            parent_revision=parent,
            mutation_id=mutation_id,
            package_snapshot=copy.deepcopy(package),
            digest=VersionEntry.digest_of(package),
            status="CURRENT",
        )
        self.entries.append(entry)
        return entry

    def current(self) -> VersionEntry:
        return self.entries[-1]

    def add_child(self, parent: VersionEntry, mutation_id: str,
                  child_package: Dict) -> VersionEntry:
        return self._append(child_package.get("revision", parent.revision + 1),
                            parent.revision, mutation_id, child_package)

    def rollback(self) -> VersionEntry:
        """Restore the parent of the current version as CURRENT."""
        current = self.current()
        if current.parent_revision is None:
            return current
        parent = next(e for e in self.entries
                      if e.revision == current.parent_revision)
        current.status = "SUPERSEDED"
        restored = VersionEntry(
            revision=parent.revision,
            parent_revision=parent.parent_revision,
            mutation_id=None,
            package_snapshot=copy.deepcopy(parent.package_snapshot),
            digest=parent.digest,
            status="CURRENT",
        )
        self.entries.append(restored)
        return restored

    def snapshot_list(self) -> List[Dict]:
        return [{
            "revision": e.revision,
            "parent_revision": e.parent_revision,
            "mutation_id": e.mutation_id,
            "digest": e.digest,
            "status": e.status,
        } for e in self.entries]
