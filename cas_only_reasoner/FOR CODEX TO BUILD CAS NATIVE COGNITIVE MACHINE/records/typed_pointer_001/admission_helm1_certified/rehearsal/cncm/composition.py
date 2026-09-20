"""A composition layer: derive the readings of an entity instead of classifying them.

The measured gap this answers
-----------------------------
`records/encoder_capacity_001/DECISION_STRUCTURE_RESULT.md` decomposes the recorded score
**exactly** by the shape of the decision each question kind requires:

    ONE DECISION                                     265 questions   11.32% -> 65.66%
    MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY      299 questions    3.01% ->  5.02%

and the two halves sum to the recorded total with nothing left over (30 + 9 = 39 at cursor 0,
174 + 15 = 189 at cursor 160). The second group — `edge_account` 16 binary slots, `role_set` 6,
`parts` 4, `context` 5, `definition` 3 — is the half that does not learn, and
`admissible_answer_count` is **1** for every question in it, in both arms at both cursors. Those
slots are not sixteen questions; they are sixteen readings of one entity.

The forward pass emits **one vector per slot** and the readout takes an **independent argmax per
slot**, so nothing can force slot 3 to agree with slot 1 and nothing knows the sixteen edge slots
describe one graph. This module supplies the missing mechanism.

What it does
------------
Two operations, both structural and neither of them learned:

1. **Binding.** An entity the question has resolved is committed once, and every later reference
   to it must denote the same thing. :meth:`Binding.commit` refuses a second, different value,
   so referential consistency is a property of the object rather than a hope about the argmax.
2. **Derivation.** A slot whose value is a reading of a bound entity is **computed** from that
   entity's declared structure instead of being classified. :func:`compose` returns which slots
   the structure determines and which it does not.

What it deliberately does NOT do
--------------------------------
It does not resolve the entity. Deciding *which* world a question is about remains the machine's
job, and this module takes that decision as an input. The distinction matters and is the whole
boundary of the proposal: **task deletion gives the machine the answer in its input; this gives it
a way to keep its own answer consistent.** It is the second.

Nothing here reads a packet, a target or a model. The caller adapts its own material into
:class:`DeclaredStructure`. Pure standard library, no device, no clock, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math

from .canonical import digest

SCHEMA_VERSION = "cncm.composition/0.1"


class CompositionError(ValueError):
    """A binding was contradicted, or a structure was malformed."""


class BindingConflict(CompositionError):
    """Two references to the same role were resolved to different entities."""


#: The roles a question can bind. One world, optionally one node inside it.
WORLD_ROLE = "world"
NODE_ROLE = "node"

#: Fields a world declares, in the order `answers.declaration_ref` allows.
DECLARATION_FIELDS = ("kind", "function", "setting")


@dataclass
class Binding:
    """Entities the question has resolved, committed once and never silently revised.

    The point of the class is :meth:`commit`. A reference slot that must denote the world the
    question is about commits ``WORLD_ROLE``; a second slot resolving the same role to a
    different world raises :class:`BindingConflict` rather than quietly disagreeing. That is the
    measured defect — `definition` cites the focus world for one reference and a different world
    for the other in 70 of 70 answers — turned into a refusal.
    """

    _committed: dict = field(default_factory=dict)
    _conflicts: int = 0

    def commit(self, role: str, entity: str) -> str:
        """Commit ``role`` to ``entity`` and return it. Re-committing the same value is fine."""
        if not isinstance(role, str) or not role:
            raise CompositionError("a role must be a non-empty string")
        if not isinstance(entity, str) or not entity:
            raise CompositionError("an entity must be a non-empty string")
        existing = self._committed.get(role)
        if existing is None:
            self._committed[role] = entity
            return entity
        if existing != entity:
            self._conflicts += 1
            raise BindingConflict(
                f"role {role!r} was committed to {existing!r} and cannot be re-committed to "
                f"{entity!r}; a reference that must denote the same entity may not denote two"
            )
        return entity

    def resolved(self, role: str) -> str | None:
        return self._committed.get(role)

    def is_resolved(self, role: str) -> bool:
        return role in self._committed

    @property
    def conflicts(self) -> int:
        return self._conflicts

    def identity(self) -> str:
        return digest({"schema": SCHEMA_VERSION, "committed": dict(sorted(self._committed.items()))})

    def snapshot(self) -> dict:
        return dict(sorted(self._committed.items()))


@dataclass(frozen=True)
class DeclaredStructure:
    """What one entity declares about itself. The caller builds this from its own material."""

    declarations: dict = field(default_factory=dict)
    nodes: tuple = field(default_factory=tuple)
    edges: frozenset = field(default_factory=frozenset)
    contains: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in self.declarations.items():
            if name not in DECLARATION_FIELDS:
                raise CompositionError(f"unknown declaration field {name!r}")
            if not isinstance(value, str) or not value:
                raise CompositionError(f"declaration {name!r} must be a non-empty string")
        for node in self.nodes:
            if not isinstance(node, str) or not node:
                raise CompositionError("node references must be non-empty strings")
        if len(set(self.nodes)) != len(self.nodes):
            raise CompositionError("node references must be distinct")
        for edge in self.edges:
            if not isinstance(edge, tuple) or len(edge) != 2:
                raise CompositionError("an edge must be a (source, target) pair")
            for endpoint in edge:
                if endpoint not in self.nodes:
                    raise CompositionError(
                        f"edge endpoint {endpoint!r} is not one of this entity's declared nodes"
                    )
        for whole, members in self.contains.items():
            if whole not in self.nodes:
                raise CompositionError(f"containment key {whole!r} is not a declared node")
            for member in members:
                if member not in self.nodes:
                    raise CompositionError(f"contained node {member!r} is not a declared node")

    def declaration_ref(self, entity: str, field_name: str) -> str:
        """``<entity>/decl/<field>`` — the same spelling `answers.declaration_ref` uses."""
        if field_name not in DECLARATION_FIELDS:
            raise CompositionError(f"unknown declaration field {field_name!r}")
        return f"{entity}/decl/{field_name}"

    def present_edges(self) -> tuple:
        return tuple(sorted(self.edges))

    def absent_edges(self) -> tuple:
        every = ((a, b) for a in self.nodes for b in self.nodes)
        return tuple(sorted(pair for pair in every if pair not in self.edges))


class Axis(Enum):
    """Which shape a kind's decision has, as measured."""

    ONE_DECISION = "ONE_DECISION"
    MANY_DECISIONS_ONE_ENTITY = "MANY_DECISIONS_ONE_ENTITY"


#: The measured shape of each kind, from `DECISION_STRUCTURE_RESULT.md`, with the slot roles the
#: declared structure determines once the entity is bound.
KIND_SHAPES: dict[str, dict] = {
    # one decision: the answer is a single choice and the structure determines none of it
    "reach": {"axis": Axis.ONE_DECISION, "slots": 1, "derived": ()},
    "analogy": {"axis": Axis.ONE_DECISION, "slots": 1, "derived": ()},
    "correspondence": {"axis": Axis.ONE_DECISION, "slots": 1, "derived": ()},
    # many decisions about one entity: every slot is a reading of the bound world
    "context": {
        "axis": Axis.MANY_DECISIONS_ONE_ENTITY,
        "slots": 5,
        "derived": ("setting_ref", "participants"),
    },
    "definition": {
        "axis": Axis.MANY_DECISIONS_ONE_ENTITY,
        "slots": 3,
        "derived": ("kind_ref", "function_ref", "whole"),
    },
    "edge_account": {
        "axis": Axis.MANY_DECISIONS_ONE_ENTITY,
        "slots": 16,
        "derived": ("edge_presence",),
    },
    "parts": {
        "axis": Axis.MANY_DECISIONS_ONE_ENTITY,
        "slots": 4,
        "derived": ("contained_nodes",),
    },
    "role_set": {
        "axis": Axis.MANY_DECISIONS_ONE_ENTITY,
        "slots": 6,
        "derived": (),
    },
}


@dataclass(frozen=True)
class Composition:
    """Which slots the declared structure determines, and which stay with the network.

    ``binding`` is carried because a composition is *the readings of a particular entity*. Two
    entities can declare coincidentally identical structure — for `edge_account` and `parts` the
    derived values are node-pair readings and the entity's own identifier never appears in them —
    so without the binding the identity of those two compositions would collide. That was caught
    by a test, not by inspection.
    """

    kind: str
    axis: Axis
    derived: dict
    undetermined: tuple
    binding: dict

    @property
    def bound_roles(self) -> tuple:
        return tuple(sorted(self.binding))

    @property
    def derived_count(self) -> int:
        return len(self.derived)

    def as_dict(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "kind": self.kind,
            "axis": self.axis.value,
            "binding": dict(sorted(self.binding.items())),
            "derived": {name: _plain(value) for name, value in sorted(self.derived.items())},
            "undetermined": list(self.undetermined),
        }

    def digest(self) -> str:
        return digest(self.as_dict())


def _plain(value):
    """Recursively convert to JSON primitives.

    The mapping branch matters: `edge_account`'s derived value is a dict of two tuples of pairs,
    and without it the nested tuples reached ``as_dict`` unconverted.
    """
    if isinstance(value, dict):
        return {str(name): _plain(inner) for name, inner in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(item) for item in value)
    return value


def compose(
    kind: str,
    binding: Binding,
    structure: DeclaredStructure,
    *,
    arguments: dict | None = None,
) -> Composition:
    """Derive every slot the bound entity's declared structure determines.

    ``binding`` must already have committed ``WORLD_ROLE``; this function does not resolve the
    entity, it only reads it. Kinds whose shape is :attr:`Axis.ONE_DECISION` derive nothing and
    return the whole decision to the network.
    """
    shape = KIND_SHAPES.get(kind)
    if shape is None:
        raise CompositionError(f"unknown question kind {kind!r}")
    arguments = {} if arguments is None else dict(arguments)
    world = binding.resolved(WORLD_ROLE)
    if world is None:
        raise CompositionError(
            "the world role is not bound; compose derives readings of a resolved entity and "
            "does not resolve it"
        )

    derived: dict = {}
    if shape["axis"] is Axis.MANY_DECISIONS_ONE_ENTITY:
        if kind == "definition":
            for name in ("kind", "function"):
                if name not in structure.declarations:
                    raise CompositionError(
                        f"the bound entity declares no {name!r}; the answer is not derivable"
                    )
                derived[f"{name}_ref"] = structure.declaration_ref(world, name)
            node = binding.resolved(NODE_ROLE) or (structure.nodes[0] if structure.nodes else None)
            if node is None:
                raise CompositionError("the bound entity declares no nodes")
            if node not in structure.nodes:
                raise CompositionError(f"bound node {node!r} is not declared by {world!r}")
            derived["whole"] = node
        elif kind == "context":
            if "setting" not in structure.declarations:
                raise CompositionError("the bound entity declares no 'setting'")
            derived["setting_ref"] = structure.declaration_ref(world, "setting")
            derived["participants"] = tuple(structure.nodes)
        elif kind == "edge_account":
            derived["edge_presence"] = {
                "present": structure.present_edges(),
                "absent": structure.absent_edges(),
            }
        elif kind == "parts":
            whole = arguments.get("whole")
            if whole is None:
                raise CompositionError("parts needs the 'whole' argument to read containment")
            members = structure.contains.get(whole)
            if members is None:
                raise CompositionError(f"{whole!r} is not a declared containment scope")
            derived["contained_nodes"] = tuple(members)
        # role_set derives nothing here: its answer depends on a supplied focal excerpt, which is
        # an argument rather than a reading of the bound entity. It is reported as undetermined.

    declared = set(shape["derived"])
    return Composition(
        kind=kind,
        axis=shape["axis"],
        derived=derived,
        undetermined=tuple(sorted(declared - set(derived))),
        binding=binding.snapshot(),
    )


def derivation_profile() -> dict:
    """Per kind: measured shape, slot count, and how many slots the structure can determine."""
    rows = []
    for kind, shape in sorted(KIND_SHAPES.items()):
        rows.append({
            "kind": kind,
            "axis": shape["axis"].value,
            "slots": shape["slots"],
            "roles_declared_derivable": list(shape["derived"]),
            "roles_defined_in_compose": len(shape["derived"]),
        })
    one = [row for row in rows if row["axis"] == Axis.ONE_DECISION.value]
    many = [row for row in rows if row["axis"] == Axis.MANY_DECISIONS_ONE_ENTITY.value]
    return {
        "schema": SCHEMA_VERSION,
        "one_decision_kinds": [row["kind"] for row in one],
        "many_decision_kinds": [row["kind"] for row in many],
        "one_decision_slots_derived": sum(row["roles_defined_in_compose"] for row in one),
        "many_decision_slots": sum(row["slots"] for row in many),
        "many_decision_slots_derived": sum(row["roles_defined_in_compose"] for row in many),
        "rows": rows,
        "note": (
            "slot counts are the medians measured from the public plans in "
            "records/encoder_capacity_001/answer_conjunction.txt; role names are this module's "
            "own and are not part of the frozen course contract"
        ),
    }


__all__ = [
    "Axis",
    "Binding",
    "BindingConflict",
    "Composition",
    "CompositionError",
    "DECLARATION_FIELDS",
    "DeclaredStructure",
    "KIND_SHAPES",
    "NODE_ROLE",
    "SCHEMA_VERSION",
    "WORLD_ROLE",
    "compose",
    "derivation_profile",
]
