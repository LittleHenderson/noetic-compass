"""crossings.py -- the CJT crossing: a thought moving from one atlas node to another.

WHAT THIS MODULE DOES
---------------------
  * It defines the owner's correction to the atlas, in his own ruling's words: "a CJT is
    the crossing, not the node" (OWNER_RULING_RPA_ATLAS_20261015.md:16-18 records that S0
    is a POSITION in the atlas, and the atlas holds nodes and edges). The atlas holds the
    nodes and the edges; a ``Crossing`` is what happens when a thought travels from one node
    to another along one edge.
  * ``Crossing`` carries the four things the act is made of plus its own digest: the node it
    left (``from_node``), the edge it took (``edge``), the node it arrived at (``to_node``),
    the ``tick`` it happened on, the ``thought_id`` it belongs to, and the crossing digest,
    which is a sha256 over {from digest, edge digest, to digest, tick, thought_id}.
  * ``cross(atlas, from_node_id, edge, to_node_id)`` validates the act and returns the
    ``Crossing`` or raises a typed refusal. It refuses an edge that is not an edge, an edge
    this atlas does not hold, an edge whose start is not ``from_node_id``, an edge whose end
    is not ``to_node_id``, an endpoint that is missing or is a sub-atlas rather than a node,
    and an edge that joins two different kinds without having been declared a cross-kind
    edge. It never repairs any of those into a crossing.
  * ``is_cjt(obj)`` answers True for a ``Crossing`` and for nothing else, so no node, no
    edge, no dict and no station record can be mistaken for the junction's crossing.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT build, extend or mutate an atlas. An atlas is handed in, read, and left
    exactly as it was: every method used here is a read.
  * It does NOT decide what a tick is, or whether an atlas crossing spends a tick at all.
    CONTINUITY.md:21 indexes the path by station and tick and says nothing about crossings
    between atlas nodes, so the tick is supplied by the caller and never stamped here.
    This is marked ``# UNDECIDED IN DESIGN`` below and listed in README.md.
  * It does NOT carry language. Nothing in a crossing is parsed, rendered, or written as
    prose; what moves is a reference to two nodes and the edge between them, and the
    payloads stay where they were, in the nodes.
  * It does NOT decide what a crossing means, whether it was a good crossing, or whether
    the arriving node is true. There is no scoring, no verdict, and no promotion of a
    GUESS or a POSSIBILITY to a FACT.
  * It does NOT read the clock, the network, or any file, and it does not persist.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

from dataclasses import dataclass

import atlas as atlas_module
from atlas import Atlas, AtlasEdge, AtlasNode, canonical_json, sha256_of

#: Refusal codes.
BAD_ATLAS = "BAD_ATLAS"
BAD_EDGE = "BAD_EDGE"
EDGE_NOT_IN_ATLAS = "EDGE_NOT_IN_ATLAS"
EDGE_FROM_MISMATCH = "EDGE_FROM_MISMATCH"
EDGE_TO_MISMATCH = "EDGE_TO_MISMATCH"
MISSING_END_NODE = "MISSING_END_NODE"
ENDPOINT_IS_NOT_A_NODE = "ENDPOINT_IS_NOT_A_NODE"
CROSS_KIND_UNDECLARED = "CROSS_KIND_UNDECLARED"
BAD_TICK = "BAD_TICK"
BAD_THOUGHT_ID = "BAD_THOUGHT_ID"
DIGEST_MISMATCH = "DIGEST_MISMATCH"


class CrossingRefusal(Exception):
    """A refusal with a stable code. A refusal is never repaired into a crossing."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The crossing
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Crossing:
    """One CJT: a thought moving from one atlas node to another along one edge.

    A CJT is the crossing and not the node. The two nodes and the edge are references the
    caller already holds; nothing here is a copy of an atlas, and nothing here changes one.

    ``thought_id`` names the thought the crossing belongs to and may be ``None`` when the
    caller is not tracking thoughts -- in which case no thought is claimed. ``tick`` is the
    tick the crossing is stamped with, supplied by the caller.
    """

    from_node: AtlasNode
    edge: AtlasEdge
    to_node: AtlasNode
    tick: int = 0
    thought_id: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.from_node, AtlasNode):
            raise CrossingRefusal(
                MISSING_END_NODE,
                f"from_node must be an AtlasNode, got {type(self.from_node).__name__}",
            )
        if not isinstance(self.to_node, AtlasNode):
            raise CrossingRefusal(
                MISSING_END_NODE,
                f"to_node must be an AtlasNode, got {type(self.to_node).__name__}",
            )
        if not isinstance(self.edge, AtlasEdge):
            raise CrossingRefusal(
                BAD_EDGE, f"edge must be an AtlasEdge, got {type(self.edge).__name__}"
            )
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise CrossingRefusal(BAD_TICK, f"tick {self.tick!r} is not a whole number of ticks")
        if self.thought_id is not None and (
            not isinstance(self.thought_id, str) or not self.thought_id.strip()
        ):
            raise CrossingRefusal(
                BAD_THOUGHT_ID,
                f"thought_id must be a non-empty string or None, got {self.thought_id!r}",
            )
        computed = sha256_of(
            canonical_json(
                {
                    "from_node_digest": self.from_node.digest,
                    "edge_digest": self.edge.digest,
                    "to_node_digest": self.to_node.digest,
                    "tick": self.tick,
                    "thought_id": self.thought_id,
                }
            )
        )
        if self.digest and self.digest != computed:
            raise CrossingRefusal(
                DIGEST_MISMATCH,
                f"crossing was given digest {self.digest!r} but its two nodes, its edge, "
                f"its tick and its thought hash to {computed!r}",
            )
        object.__setattr__(self, "digest", computed)

    # -- the leaf fields a reader may need -------------------------------- #
    @property
    def from_node_id(self) -> str:
        return self.from_node.node_id

    @property
    def to_node_id(self) -> str:
        return self.to_node.node_id

    @property
    def from_digest(self) -> str:
        return self.from_node.digest

    @property
    def to_digest(self) -> str:
        return self.to_node.digest

    @property
    def relation(self) -> str:
        return self.edge.relation

    @property
    def cross_kind_declared(self) -> bool:
        return self.edge.cross_kind_declared

    @property
    def joins_different_kinds(self) -> bool:
        """True when this crossing went from a node of one kind to a node of another."""
        return self.from_node.kind != self.to_node.kind

    def as_dict(self) -> dict:
        """A small owned dict for a log line. No live object is carried across."""
        return {
            "from_node_id": self.from_node_id,
            "from_node_digest": self.from_digest,
            "from_kind": self.from_node.kind,
            "to_node_id": self.to_node_id,
            "to_node_digest": self.to_digest,
            "to_kind": self.to_node.kind,
            "relation": self.relation,
            "cross_kind_declared": self.cross_kind_declared,
            "joins_different_kinds": self.joins_different_kinds,
            "tick": self.tick,
            "thought_id": self.thought_id,
            "digest": self.digest,
        }


def is_cjt(obj) -> bool:
    """True only for a ``Crossing``. A node, an edge, a dict or a station record is not one.

    The owner's ruling is what this guards: a CJT is the crossing, not the node. A
    possibility node, the relation that joins two nodes, and anything that merely carries
    the fields of a crossing are all something else, and this function says so.
    """
    return isinstance(obj, Crossing)


# --------------------------------------------------------------------------- #
# The act
# --------------------------------------------------------------------------- #
# UNDECIDED IN DESIGN: what tick an atlas crossing is stamped with, and whether an atlas crossing spends a tick at all -- CONTINUITY.md:21 indexes a thought's path by station and tick and gives no tick semantics for a crossing between atlas nodes (the tick is described there as a station boundary), so this build takes the tick from the caller and never stamps or increments one.
def cross(
    atlas: Atlas,
    from_node_id: str,
    edge,
    to_node_id: str,
    thought_id: str | None = None,
    tick: int = 0,
) -> Crossing:
    """Validate the crossing and return it, or raise a typed refusal.

    Five checks, in this order, each with its own code:

      1. ``atlas`` is an ``Atlas`` and ``edge`` is an ``AtlasEdge`` (``BAD_ATLAS``,
         ``BAD_EDGE``);
      2. both endpoints are nodes of that atlas (``MISSING_END_NODE``,
         ``ENDPOINT_IS_NOT_A_NODE``);
      3. the edge starts at ``from_node_id`` and ends at ``to_node_id``
         (``EDGE_FROM_MISMATCH``, ``EDGE_TO_MISMATCH``);
      4. that exact edge is held by the atlas (``EDGE_NOT_IN_ATLAS``);
      5. if the two endpoints are of different kinds, the edge must carry
         ``cross_kind_declared=True`` (``CROSS_KIND_UNDECLARED``).

    Check 3 is the one the design turns on: a crossing is accepted only when the edge
    actually connects those two nodes.
    """
    if not isinstance(atlas, Atlas):
        raise CrossingRefusal(
            BAD_ATLAS, f"an Atlas is required here, got {type(atlas).__name__}"
        )
    if not isinstance(edge, AtlasEdge):
        raise CrossingRefusal(
            BAD_EDGE, f"edge must be an AtlasEdge, got {type(edge).__name__}"
        )

    from_node = _endpoint(atlas, from_node_id, "from_node_id")
    to_node = _endpoint(atlas, to_node_id, "to_node_id")

    if edge.from_node_id != from_node.node_id:
        raise CrossingRefusal(
            EDGE_FROM_MISMATCH,
            f"the edge starts at {edge.from_node_id!r}, not at {from_node.node_id!r}; a "
            f"crossing starts where its edge starts",
        )
    if edge.to_node_id != to_node.node_id:
        raise CrossingRefusal(
            EDGE_TO_MISMATCH,
            f"the edge ends at {edge.to_node_id!r}, not at {to_node.node_id!r}; a crossing "
            f"arrives where its edge arrives",
        )
    if not atlas.has_edge(edge):
        raise CrossingRefusal(
            EDGE_NOT_IN_ATLAS,
            f"the edge {edge.from_node_id!r} -> {edge.to_node_id!r} along "
            f"{edge.relation!r} (digest {edge.digest!r}) is not held by atlas "
            f"{atlas.atlas_id!r}; nothing may be crossed that is not in the atlas",
        )
    if from_node.kind != to_node.kind and not edge.cross_kind_declared:
        raise CrossingRefusal(
            CROSS_KIND_UNDECLARED,
            f"the crossing leaves a {from_node.kind} for a {to_node.kind} and the edge was "
            f"not declared cross-kind; facts and guesses stay distinct unless the crossing "
            f"is declared",
        )

    return Crossing(
        from_node=from_node,
        edge=edge,
        to_node=to_node,
        tick=tick,
        thought_id=thought_id,
    )


def _endpoint(atlas: Atlas, node_id: str, name: str) -> AtlasNode:
    """The node at this id, or a refusal saying which kind of wrong it is."""
    if not isinstance(node_id, str) or not node_id.strip():
        raise CrossingRefusal(
            MISSING_END_NODE, f"{name} {node_id!r} is not a node id at all"
        )
    try:
        entry = atlas.entry(node_id)
    except atlas_module.AtlasRefusal as refusal:
        if refusal.code == atlas_module.ENTRY_NOT_FOUND:
            raise CrossingRefusal(
                MISSING_END_NODE, f"{name} {node_id!r} is not an entry of atlas {atlas.atlas_id!r}"
            ) from refusal
        raise
    if not isinstance(entry, AtlasNode):
        raise CrossingRefusal(
            ENDPOINT_IS_NOT_A_NODE,
            f"{name} {node_id!r} names a sub-atlas, and a crossing runs between nodes",
        )
    return entry
