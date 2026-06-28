"""Idea Atlas data model — IdeaNode, IdeaEdge, IdeaAtlas.

The atlas is a navigable map of the ^0/^5 substrate (per CLAUDE.md
authoritative Noetic definitions) lit up by a CAS-Native prediction.

Design constraints
------------------

* **Pure stdlib.** No torch, no numpy, no third-party deps. The atlas is a
  serializable spec; rendering happens in the dashboard.
* **Immutable.** All dataclasses are ``frozen=True``. Atlases are
  derived artifacts of a prediction, not mutable state.
* **Tuples not lists.** Frozen dataclasses with hashable members enable
  set-membership tests and dict keys (e.g. for de-duplication during
  diff between two consecutive predictions in the same conversation).
* **JSON round-trippable.** ``IdeaAtlas.to_dict()`` and
  ``IdeaAtlas.from_dict()`` form the wire protocol between the Python
  inference path and the TypeScript dashboard. The TS types in
  ``dashboard/src/components/IdeaAtlas/types.ts`` mirror this schema
  exactly.

Authoritative Noetic primitives (CLAUDE.md, verbatim from the Tootra
Math Handbook):

* ^0 Idea — All things in and outside the Mind.
* ^1 Mind — Various degrees of awareness.
* ^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
* ^3 Negative — An Idea the Mind is adverse to and repelled by.
* ^4 Vibration — The degree to which an Idea resonates with the Mind.
* ^5 Female — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
* ^6 Male — An Idea impregnated with another Idea.
* ^7 Rhythm — The rate and pattern a Mind is exposed to an Idea.
* ^8 Above/Cause — An Idea that triggers a different Idea to come to Mind.
* ^9 Below/Effect — The Idea brought to Mind by an Above/Cause trigger.

Involution pairs (positive ↔ negative-space shadow):
``^2↔^3``, ``^5↔^6``, ``^8↔^9``. Self-duals: ``^0``, ``^1``, ``^4``, ``^7``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping


# ---------------------------------------------------------------------------
# Authoritative ontology constants
# ---------------------------------------------------------------------------

NOETIC_LABELS: tuple[str, ...] = (
    "Idea",
    "Mind",
    "Positive",
    "Negative",
    "Vibration",
    "Female",
    "Male",
    "Rhythm",
    "Above/Cause",
    "Below/Effect",
)

DOMAIN_LABELS: tuple[str, ...] = ("P", "C", "E", "O")
DRIVE_LABELS: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
REGISTER_LABELS: tuple[str, ...] = ("T", "A", "f", "E")

# Involution pairs (CLAUDE.md "Structural invariants"): if a Noetic in the
# left column is lit positively, the right-column Noetic is the negative-space
# shadow. The map is symmetric.
INVOLUTION_PAIRS: tuple[tuple[int, int], ...] = (
    (2, 3),
    (5, 6),
    (8, 9),
)

# Self-duals — no involution shadow.
SELF_DUAL_NOETICS: tuple[int, ...] = (0, 1, 4, 7)

# Domain Descent (causation): P → C → E → O. The reverse arrow O → P is the
# feedback signal path; emitted by `prediction_to_atlas` when the prediction
# has multiple domains lit.
DOMAIN_DESCENT_ORDER: tuple[str, ...] = ("P", "C", "E", "O")

# Drive inversion pairs (CLAUDE.md): F1↔F7, F2↔F6, F3↔F5. F4 self-dual.
DRIVE_INVERSION_PAIRS: tuple[tuple[str, str], ...] = (
    ("F1", "F7"),
    ("F2", "F6"),
    ("F3", "F5"),
)


# Permitted edge_kind values. Exposed as a constant so the dashboard renderer
# can switch on a closed enum instead of stringly-typed lookups.
EDGE_KINDS: tuple[str, ...] = (
    "involution_pair",        # ^2↔^3, ^5↔^6, ^8↔^9 (between same-domain states)
    "domain_descent",         # P → C → E → O on the same Noetic
    "domain_feedback",        # O → P feedback signal path
    "drive_inversion",        # F1↔F7, F2↔F6, F3↔F5
    "rpm_chain",              # A0 → Dn → Wn → Pn (Capability Pathway)
    "cluster_member",         # NoeticCluster / StateSet / etc. membership
    "register_co_presence",   # `+` operator (Clarification 10)
    "register_integration",   # `×` with explicit emergent (Clarification 10)
    "recipe_prerequisite",    # Θ recipe input → Ω
    "production_target",      # input → Ω target
    "trace",                  # Generic structural trace from compiler diagram
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def _validate_noetic(noetic: str) -> None:
    """Validate a Noetic label of the form ``^N`` where N ∈ {0..9}."""
    if not isinstance(noetic, str):
        raise TypeError(f"noetic must be str, got {type(noetic).__name__}")
    if len(noetic) != 2 or noetic[0] != "^" or noetic[1] not in "0123456789":
        raise ValueError(
            f"noetic must be of the form '^N' where N ∈ 0..9, got {noetic!r}"
        )


def _validate_domain(domain: str | None) -> None:
    if domain is None:
        return
    if domain not in DOMAIN_LABELS:
        raise ValueError(f"domain must be one of {DOMAIN_LABELS} or None, got {domain!r}")


def _validate_drive(drive: str | None) -> None:
    if drive is None:
        return
    if drive not in DRIVE_LABELS:
        raise ValueError(f"drive must be one of {DRIVE_LABELS} or None, got {drive!r}")


def _validate_register(register: str | None) -> None:
    if register is None:
        return
    if register not in REGISTER_LABELS:
        raise ValueError(
            f"register must be one of {REGISTER_LABELS} or None, got {register!r}"
        )


def _validate_intensity(intensity: float) -> None:
    if not isinstance(intensity, (int, float)):
        raise TypeError(
            f"intensity must be float, got {type(intensity).__name__}"
        )
    if not 0.0 <= float(intensity) <= 1.0:
        raise ValueError(f"intensity must be in [0, 1], got {intensity}")


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Defensive shallow copy. Frozen dataclasses cannot prevent inner-dict
    mutation, but copying at construction time prevents the most common
    foot-gun (caller mutates the dict it passed in)."""
    if metadata is None:
        return {}
    return dict(metadata)


@dataclass(frozen=True)
class IdeaNode:
    """An Idea in the atlas.

    An IdeaNode is the atlas-level representation of a single CAS primitive
    or compound state lit up by a prediction. ``intensity`` is the
    (normalized) activation level inferred from the prediction; for a v77
    structured-token prediction, this is typically derived from the softmax
    probability of the argmax label.

    Positive vs negative space:

    * ``is_positive_space=True`` — the Idea is *lit* by the prediction
      (e.g. ``^3`` is the argmax noetic).
    * ``is_positive_space=False`` — the Idea is the involution-pair shadow
      of a positive-space node (e.g. when ``^3`` is lit, ``^2`` is rendered
      in negative space at low intensity to surface the involution
      structure). The atlas surfaces both — the user's vision is to make
      the *absent* Ideas visible alongside the *present* ones.

    The ``id`` field is unique within an atlas. By convention it is built as
    ``"<noetic>[<^domain>][_{<drive>}][|<register>][:negspace]"`` (e.g.
    ``"^3^E_{F2}|A"``, or ``"^2^E_{F2}|A:negspace"`` for the involution
    shadow), but callers may use any unique string. The dashboard only relies
    on stability across an atlas, not on a particular format.
    """

    id: str
    label: str
    noetic: str
    domain: str | None
    drive: str | None
    register: str | None
    intensity: float
    is_positive_space: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("IdeaNode.id must be a non-empty string")
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("IdeaNode.label must be a non-empty string")
        _validate_noetic(self.noetic)
        _validate_domain(self.domain)
        _validate_drive(self.drive)
        _validate_register(self.register)
        _validate_intensity(self.intensity)
        if not isinstance(self.is_positive_space, bool):
            raise TypeError(
                "IdeaNode.is_positive_space must be bool, got "
                f"{type(self.is_positive_space).__name__}"
            )
        # Defensive copy of metadata (frozen dataclass keeps the dict
        # reference frozen; we still want to detach it from caller-owned
        # state at construction time).
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def noetic_index(self) -> int:
        """Numeric index 0..9 of the Noetic primitive."""
        return int(self.noetic[1])

    @property
    def noetic_name(self) -> str:
        """Authoritative Noetic name (e.g. ``Negative`` for ``^3``)."""
        return NOETIC_LABELS[self.noetic_index]

    @property
    def is_compound_state(self) -> bool:
        """True if the node carries domain + drive (compound CAS state)."""
        return self.domain is not None and self.drive is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "noetic": self.noetic,
            "domain": self.domain,
            "drive": self.drive,
            "register": self.register,
            "intensity": float(self.intensity),
            "is_positive_space": self.is_positive_space,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IdeaNode":
        return cls(
            id=data["id"],
            label=data["label"],
            noetic=data["noetic"],
            domain=data.get("domain"),
            drive=data.get("drive"),
            register=data.get("register"),
            intensity=float(data["intensity"]),
            is_positive_space=bool(data["is_positive_space"]),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class IdeaEdge:
    """A relationship between two Ideas in the atlas.

    Edge kinds are drawn from :data:`EDGE_KINDS`. The ``label`` is an
    optional human-readable annotation rendered by the dashboard near the
    edge midpoint (e.g. ``"P→C"`` for a domain-descent edge, ``"a=2.0"``
    for a recipe weight).
    """

    source_id: str
    target_id: str
    edge_kind: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id:
            raise ValueError("IdeaEdge.source_id must be a non-empty string")
        if not isinstance(self.target_id, str) or not self.target_id:
            raise ValueError("IdeaEdge.target_id must be a non-empty string")
        if self.source_id == self.target_id:
            raise ValueError(
                f"IdeaEdge source_id and target_id must differ "
                f"(both = {self.source_id!r})"
            )
        if self.edge_kind not in EDGE_KINDS:
            raise ValueError(
                f"IdeaEdge.edge_kind must be one of {EDGE_KINDS}, "
                f"got {self.edge_kind!r}"
            )
        if self.label is not None and not isinstance(self.label, str):
            raise TypeError(
                f"IdeaEdge.label must be str or None, got "
                f"{type(self.label).__name__}"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_kind": self.edge_kind,
            "label": self.label,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IdeaEdge":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            edge_kind=data["edge_kind"],
            label=data.get("label"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class IdeaAtlas:
    """The full atlas for a single CAS-Native prediction.

    An IdeaAtlas is the navigable map of the ^0/^5 substrate this prediction
    lit up. It carries:

    * ``nodes`` — every Idea in the atlas, positive and negative space.
    * ``edges`` — every relationship between Ideas (involution pairs,
      domain descent, drive inversion, RPM chain, cluster membership,
      register co-presence/integration, recipe prerequisites, generic
      compiler-diagram traces).
    * ``generation_id`` — 1:1 mapping back to the prediction that produced
      this atlas (UUID4 hex). Same UUID is attached to the compiler-produced
      diagram for the same prediction; the dashboard uses it to highlight
      corresponding elements across the Atlas ↔ Diagram toggle.
    * ``cas_expression`` — the rendered CAS expression (e.g. ``"^3^E_{F2}|A"``)
      that this atlas summarizes. Useful for breadcrumbs and tooltips.
    * ``metadata`` — free-form, JSON-safe key/value pairs (timestamp_ms,
      checkpoint_id, model_version, etc.).

    Invariants enforced at construction time:

    1. Every edge's ``source_id`` and ``target_id`` reference an existing
       node ``id``.
    2. Node ``id``s are unique within the atlas.
    3. ``generation_id`` is a non-empty string.
    """

    nodes: tuple[IdeaNode, ...]
    edges: tuple[IdeaEdge, ...]
    generation_id: str
    cas_expression: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.nodes, tuple):
            object.__setattr__(self, "nodes", tuple(self.nodes))
        if not isinstance(self.edges, tuple):
            object.__setattr__(self, "edges", tuple(self.edges))
        if not isinstance(self.generation_id, str) or not self.generation_id:
            raise ValueError(
                "IdeaAtlas.generation_id must be a non-empty string"
            )
        if not isinstance(self.cas_expression, str):
            raise TypeError(
                "IdeaAtlas.cas_expression must be str, got "
                f"{type(self.cas_expression).__name__}"
            )

        seen_ids: set[str] = set()
        for node in self.nodes:
            if not isinstance(node, IdeaNode):
                raise TypeError(
                    f"IdeaAtlas.nodes must contain IdeaNode, got "
                    f"{type(node).__name__}"
                )
            if node.id in seen_ids:
                raise ValueError(
                    f"IdeaAtlas.nodes contains duplicate id: {node.id!r}"
                )
            seen_ids.add(node.id)

        for edge in self.edges:
            if not isinstance(edge, IdeaEdge):
                raise TypeError(
                    f"IdeaAtlas.edges must contain IdeaEdge, got "
                    f"{type(edge).__name__}"
                )
            if edge.source_id not in seen_ids:
                raise ValueError(
                    f"IdeaEdge.source_id {edge.source_id!r} not in atlas nodes"
                )
            if edge.target_id not in seen_ids:
                raise ValueError(
                    f"IdeaEdge.target_id {edge.target_id!r} not in atlas nodes"
                )

        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    # ---- Convenience accessors -------------------------------------------

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def positive_space_nodes(self) -> tuple[IdeaNode, ...]:
        return tuple(n for n in self.nodes if n.is_positive_space)

    @property
    def negative_space_nodes(self) -> tuple[IdeaNode, ...]:
        return tuple(n for n in self.nodes if not n.is_positive_space)

    def node_by_id(self, node_id: str) -> IdeaNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def edges_for_node(self, node_id: str) -> tuple[IdeaEdge, ...]:
        return tuple(
            e for e in self.edges if node_id in (e.source_id, e.target_id)
        )

    def with_metadata(self, **updates: Any) -> "IdeaAtlas":
        """Return a copy with ``metadata`` merged with ``updates``."""
        merged = {**self.metadata, **updates}
        return replace(self, metadata=merged)

    # ---- Serialization ---------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "generation_id": self.generation_id,
            "cas_expression": self.cas_expression,
            "metadata": dict(self.metadata),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IdeaAtlas":
        nodes = tuple(IdeaNode.from_dict(n) for n in data["nodes"])
        edges = tuple(IdeaEdge.from_dict(e) for e in data["edges"])
        return cls(
            nodes=nodes,
            edges=edges,
            generation_id=data["generation_id"],
            cas_expression=data["cas_expression"],
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_json(cls, text: str) -> "IdeaAtlas":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# generation_id helpers
# ---------------------------------------------------------------------------


def new_generation_id() -> str:
    """Return a fresh canonical-hex UUID4 (32 chars, no dashes).

    Compact form chosen so it works inline in CLI output, log lines, and URL
    fragments without quoting. The dashboard URL pattern is:
    ``/atlas/<generation_id>``.

    Why hex (not str(uuid.uuid4())) — `cas chat` may print this on the same
    line as a CAS expression; the no-dash form is unambiguous when the line
    wraps. The dashboard accepts either form via a regex strip on the URL
    parser.
    """
    return uuid.uuid4().hex


def is_generation_id(value: Any) -> bool:
    """Return True if ``value`` matches our canonical hex UUID4 form.

    Used by the dashboard transport layer to decide whether a string is a
    generation_id or a free-form id (e.g. a Diagram-side node id).
    """
    if not isinstance(value, str) or len(value) != 32:
        return False
    try:
        uuid.UUID(hex=value)
    except (ValueError, AttributeError):
        return False
    return True


__all__ = [
    "DOMAIN_DESCENT_ORDER",
    "DOMAIN_LABELS",
    "DRIVE_INVERSION_PAIRS",
    "DRIVE_LABELS",
    "EDGE_KINDS",
    "INVOLUTION_PAIRS",
    "IdeaAtlas",
    "IdeaEdge",
    "IdeaNode",
    "NOETIC_LABELS",
    "REGISTER_LABELS",
    "SELF_DUAL_NOETICS",
    "is_generation_id",
    "new_generation_id",
]
