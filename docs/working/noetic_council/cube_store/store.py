"""store.py -- Persistence and governance invariants for Unified Cube Store.

Enforces:
- Section 4 / 5: provenance.source must be USER_SAID, AUTHORED, or CHECKED. Never NONE.
- Section 5: Only a WRITE creates knowledge. REFUSE and CLARIFY write no cube.
- Section 6: LearnerView / TeacherTarget visibility boundary enforced.
- Section 10: Zero training weights, zero neural components, deterministic storage.
"""
from __future__ import annotations

import copy
import json
from typing import Dict, List, Optional

from cube import (
    Branch,
    CubeNode,
    CubeValidationError,
    apply_learner_view,
    validate_branch,
    validate_cube,
)


class AdmissionRefusal(ValueError):
    """Raised when admission of an invalid or ungrounded cube into the store is refused."""
    pass


class CubeStore:
    def __init__(self, context_id: str = "default_store"):
        self.context_id = context_id
        self.nodes: Dict[str, CubeNode] = {}
        self.branches: List[Branch] = []
        self.write_history: List[str] = []

    def write_cube(self, cube: CubeNode) -> None:
        """Writes a cube node into the store under strict admission gating."""
        validate_cube(cube)

        # Section 5 & Addition 4 rule: Never NONE.
        if cube.provenance.source == "NONE":
            raise AdmissionRefusal("source=NONE is forbidden; ungrounded knowledge rejected.")

        if cube.provenance.source not in ("USER_SAID", "AUTHORED", "CHECKED"):
            raise AdmissionRefusal(f"Invalid provenance source for store admission: {cube.provenance.source}")

        if cube.node_id in self.nodes:
            prev = self.nodes[cube.node_id]
            if cube.revision <= prev.revision:
                raise AdmissionRefusal(
                    f"Revision must increase: new revision {cube.revision} <= current {prev.revision}"
                )

        self.nodes[cube.node_id] = copy.deepcopy(cube)
        self.write_history.append(cube.node_id)

    def write_branch(self, branch: Branch) -> None:
        """Writes a relational branch between cubes into the store."""
        validate_branch(branch)

        # Ensure endpoints exist or are known
        if branch.source_node_id not in self.nodes:
            raise AdmissionRefusal(f"Branch source node not in store: {branch.source_node_id}")

        self.branches.append(copy.deepcopy(branch))

    def get_cube(self, node_id: str, view_profile: str = "LearnerView") -> Optional[CubeNode]:
        """Retrieves a cube from the store applying the requested visibility profile."""
        if node_id not in self.nodes:
            return None
        node = self.nodes[node_id]
        if view_profile == "LearnerView":
            return apply_learner_view(node)
        return copy.deepcopy(node)

    def find_cubes_by_kind(self, kind: str, view_profile: str = "LearnerView") -> List[CubeNode]:
        out = []
        for n in self.nodes.values():
            if n.core.kind == kind:
                out.append(apply_learner_view(n) if view_profile == "LearnerView" else copy.deepcopy(n))
        return out

    def find_cubes_by_label(self, label: str, view_profile: str = "LearnerView") -> List[CubeNode]:
        clean = label.strip().lower()
        out = []
        for n in self.nodes.values():
            if n.core.label.strip().lower() == clean:
                out.append(apply_learner_view(n) if view_profile == "LearnerView" else copy.deepcopy(n))
        return out

    def get_outgoing_branches(self, source_id: str, predicate: Optional[str] = "contains") -> List[Branch]:
        return [
            copy.deepcopy(b) for b in self.branches
            if b.source_node_id == source_id and (predicate is None or b.predicate == predicate)
        ]

    def get_incoming_branches(self, target_id: str, predicate: Optional[str] = "contains") -> List[Branch]:
        return [
            copy.deepcopy(b) for b in self.branches
            if b.target_node_id == target_id and (predicate is None or b.predicate == predicate)
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "branches": [b.to_dict() for b in self.branches],
            "write_history": list(self.write_history),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CubeStore:
        store = cls(context_id=d.get("context_id", "default_store"))
        for k, v in d.get("nodes", {}).items():
            store.nodes[k] = CubeNode.from_dict(v)
        for b in d.get("branches", []):
            store.branches.append(Branch.from_dict(b))
        store.write_history = list(d.get("write_history", []))
        return store
