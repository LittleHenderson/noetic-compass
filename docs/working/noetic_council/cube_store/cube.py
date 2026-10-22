"""cube.py -- Logical record contract and validation for Unified Cube Store.

Implements Cube_Node_Schema_v0.1.md extended with the 5 additions from
SPEC_CUBE_STORE_UNIFIED_20261018.md section 4:
  1. core.kind gains "directive" (concept | instance | event | procedure | directive)
  2. turn_index : integer (order in conversation)
  3. confidence : object | null (separate from availability; unknown != uncertain)
  4. provenance.source : "USER_SAID" | "AUTHORED" | "CHECKED" | "NONE"
  5. polarity : reference to existing cce.py polarity (POSITIVE, NEGATIVE, etc.)

No sixth addition. Precedence rule: Cube_Node_Schema_v0.1.md wins if disagreement.
Inherited rule section 3:
  "Missing knowledge must not be filled with fabricated content merely to complete a cube."
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "cas.cube-node/0.1"

# Addition 1: core.kind gains "directive"
ALLOWED_KINDS = ("concept", "instance", "event", "procedure", "directive")

ALLOWED_AVAILABILITY = ("populated", "unknown", "not_applicable")

# Addition 4: provenance.source kinds
ALLOWED_SOURCES = ("USER_SAID", "AUTHORED", "CHECKED", "NONE")

# Addition 5: polarity split into assertion (F14) and valence (Noetic ^2 / ^3)
ALLOWED_ASSERTIONS = ("ASSERTED", "DENIED")
ALLOWED_VALENCES = ("POSITIVE", "NEGATIVE", "NEUTRAL")
ALLOWED_POLARITIES = ("POSITIVE", "NEGATIVE", "NEUTRAL", "ASSERTED", "DENIED")  # Backwards compatibility


class CubeValidationError(ValueError):
    """Raised when a Cube or Branch violates the v0.1 data contract."""
    pass


@dataclass
class Face:
    availability: str = "populated"
    human_text: str = ""
    structured: Dict[str, Any] = field(default_factory=dict)
    provenance_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability": self.availability,
            "human_text": self.human_text,
            "structured": copy.deepcopy(self.structured),
            "provenance_refs": list(self.provenance_refs),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Face:
        return cls(
            availability=d.get("availability", "populated"),
            human_text=d.get("human_text", ""),
            structured=copy.deepcopy(d.get("structured", {})),
            provenance_refs=list(d.get("provenance_refs", [])),
        )


@dataclass
class Core:
    label: str
    kind: str  # concept | instance | event | procedure | directive
    identity_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "kind": self.kind,
            "identity_statement": self.identity_statement,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Core:
        return cls(
            label=d.get("label", ""),
            kind=d.get("kind", "concept"),
            identity_statement=d.get("identity_statement", ""),
        )


@dataclass
class Provenance:
    source: str = "USER_SAID"  # USER_SAID | AUTHORED | CHECKED | NONE
    refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "refs": list(self.refs),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Provenance:
        return cls(
            source=d.get("source", "USER_SAID"),
            refs=list(d.get("refs", [])),
        )


@dataclass
class CubeNode:
    node_id: str
    core: Core
    faces: Dict[str, Face]
    context_id: str = "default_context"
    revision: int = 1
    schema_version: str = SCHEMA_VERSION
    provenance_refs: List[str] = field(default_factory=list)

    # The 5 additions from SPEC_CUBE_STORE_UNIFIED_20261018.md section 4:
    turn_index: Optional[int] = None
    confidence: Optional[Dict[str, Any]] = None
    provenance: Provenance = field(default_factory=Provenance)
    assertion: str = "ASSERTED"  # ASSERTED | DENIED (Section 4 & F14)
    valence: str = "NEUTRAL"     # POSITIVE | NEGATIVE | NEUTRAL (Section 4 & Noetic ^2/^3)
    polarity: Optional[str] = None
    """DEPRECATED: Legacy compatibility alias only. Conflates assertion with valence.
    Do not read or write in new code. Use `assertion` and `valence` instead."""

    def to_dict(self) -> Dict[str, Any]:
        pol = self.polarity if self.polarity is not None else (self.valence if self.valence != "NEUTRAL" else self.assertion)
        return {
            "schema_version": self.schema_version,
            "node_id": self.node_id,
            "revision": self.revision,
            "context_id": self.context_id,
            "core": self.core.to_dict(),
            "faces": {k: v.to_dict() for k, v in self.faces.items()},
            "provenance_refs": list(self.provenance_refs),
            "turn_index": self.turn_index,
            "confidence": copy.deepcopy(self.confidence),
            "provenance": self.provenance.to_dict(),
            "assertion": self.assertion,
            "valence": self.valence,
            "polarity": pol,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CubeNode:
        faces = {}
        raw_faces = d.get("faces", {})
        for k in ("face_1", "face_2", "face_3", "face_4", "face_5", "face_6"):
            if k in raw_faces:
                faces[k] = Face.from_dict(raw_faces[k])
            else:
                faces[k] = Face(availability="unknown", human_text="Not populated")

        core = Core.from_dict(d.get("core", {}))
        provenance = Provenance.from_dict(d.get("provenance", {}))

        assertion = d.get("assertion", "ASSERTED")
        valence = d.get("valence", "NEUTRAL")
        if "polarity" in d and "assertion" not in d and "valence" not in d:
            pol = d["polarity"]
            if pol in ("ASSERTED", "DENIED"):
                assertion = pol
                valence = "NEUTRAL"
            elif pol in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                assertion = "ASSERTED"
                valence = pol

        return cls(
            node_id=d.get("node_id", ""),
            core=core,
            faces=faces,
            context_id=d.get("context_id", "default_context"),
            revision=d.get("revision", 1),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            provenance_refs=list(d.get("provenance_refs", [])),
            turn_index=d.get("turn_index"),
            confidence=copy.deepcopy(d.get("confidence")),
            provenance=provenance,
            assertion=assertion,
            valence=valence,
            polarity=d.get("polarity"),
        )


@dataclass
class Branch:
    branch_id: str
    context_id: str
    source_node_id: str
    predicate: str  # "contains" | "depends_on" | "corresponds_to"
    target_node_id: str
    commonality: Dict[str, Any] = field(default_factory=dict)
    provenance_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "context_id": self.context_id,
            "source_node_id": self.source_node_id,
            "predicate": self.predicate,
            "target_node_id": self.target_node_id,
            "commonality": copy.deepcopy(self.commonality),
            "provenance_refs": list(self.provenance_refs),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Branch:
        return cls(
            branch_id=d.get("branch_id", ""),
            context_id=d.get("context_id", ""),
            source_node_id=d.get("source_node_id", ""),
            predicate=d.get("predicate", "contains"),
            target_node_id=d.get("target_node_id", ""),
            commonality=copy.deepcopy(d.get("commonality", {})),
            provenance_refs=list(d.get("provenance_refs", [])),
        )


def validate_cube(cube: CubeNode) -> None:
    """Validates that a cube conforms strictly to Cube_Node_Schema_v0.1 and the 5 additions."""
    if cube.schema_version != SCHEMA_VERSION:
        raise CubeValidationError(f"Invalid schema_version: {cube.schema_version!r} != {SCHEMA_VERSION!r}")

    if not cube.node_id or not isinstance(cube.node_id, str):
        raise CubeValidationError("node_id must be a non-empty string")

    if not isinstance(cube.revision, int) or cube.revision < 1:
        raise CubeValidationError("revision must be a positive integer >= 1")

    # Addition 1 check: core.kind
    if cube.core.kind not in ALLOWED_KINDS:
        raise CubeValidationError(
            f"core.kind {cube.core.kind!r} not in allowed kinds: {ALLOWED_KINDS}"
        )

    # All six face keys MUST exist
    required_faces = ("face_1", "face_2", "face_3", "face_4", "face_5", "face_6")
    for f_key in required_faces:
        if f_key not in cube.faces:
            raise CubeValidationError(f"Missing required face key: {f_key}")

        face = cube.faces[f_key]
        if face.availability not in ALLOWED_AVAILABILITY:
            raise CubeValidationError(
                f"Face {f_key} availability {face.availability!r} not in {ALLOWED_AVAILABILITY}"
            )

        # Inherited Section 3 rule:
        # unknown and not_applicable MUST carry an explanation; their structured object is empty.
        # "Missing knowledge must not be filled with fabricated content merely to complete a cube."
        if face.availability in ("unknown", "not_applicable"):
            if not face.human_text.strip():
                raise CubeValidationError(
                    f"Face {f_key} has availability={face.availability!r} but lacks required explanation text"
                )
            if face.structured:
                raise CubeValidationError(
                    f"Face {f_key} has availability={face.availability!r} but non-empty structured data"
                )

    # Addition 4 check: provenance.source
    if cube.provenance.source not in ALLOWED_SOURCES:
        raise CubeValidationError(
            f"provenance.source {cube.provenance.source!r} not in allowed: {ALLOWED_SOURCES}"
        )

    # Addition 5 check: assertion, valence, and polarity
    if cube.assertion not in ALLOWED_ASSERTIONS:
        raise CubeValidationError(
            f"assertion {cube.assertion!r} not in allowed assertions: {ALLOWED_ASSERTIONS}"
        )
    if cube.valence not in ALLOWED_VALENCES:
        raise CubeValidationError(
            f"valence {cube.valence!r} not in allowed valences: {ALLOWED_VALENCES}"
        )
    if cube.polarity is not None and cube.polarity not in ALLOWED_POLARITIES:
        raise CubeValidationError(
            f"polarity {cube.polarity!r} not in allowed polarities: {ALLOWED_POLARITIES}"
        )


def validate_branch(branch: Branch) -> None:
    """Validates that a branch conforms to the v0.1 connector contract."""
    if not branch.branch_id:
        raise CubeValidationError("branch_id must not be empty")
    if not branch.source_node_id:
        raise CubeValidationError("source_node_id must not be empty")
    if not branch.target_node_id:
        raise CubeValidationError("target_node_id must not be empty")
    if branch.source_node_id == branch.target_node_id:
        raise CubeValidationError(f"Self-loop branch rejected: {branch.source_node_id}")


# Section 6: Visibility Boundary (One rule, two uses)
def apply_learner_view(cube: CubeNode) -> CubeNode:
    """Creates a LearnerView of the cube where solved answers and authoring secrets are masked.
    - A test must not see a solved face (face_5 direct decomposition answers or face_6 solved sequence).
    - Missing knowledge remains explicitly unknown with an explanation.
    """
    clone = copy.deepcopy(cube)
    if clone.provenance.source == "AUTHORED":
        # Mask face 5 solved list and face 6 solved sequence
        if clone.faces["face_5"].availability == "populated":
            clone.faces["face_5"].availability = "unknown"
            clone.faces["face_5"].human_text = "Withheld for unassisted evaluation."
            clone.faces["face_5"].structured = {}

        if clone.faces["face_6"].availability == "populated":
            clone.faces["face_6"].availability = "unknown"
            clone.faces["face_6"].human_text = "Withheld for unassisted evaluation."
            clone.faces["face_6"].structured = {}
    return clone
