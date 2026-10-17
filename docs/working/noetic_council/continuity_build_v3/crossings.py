"""crossings.py -- the CJT crossing, carried over the REAL atlas model.

WHAT THIS MODULE DOES
---------------------
  * It keeps the owner's correction to the atlas, in his own ruling's words: "a CJT is the
    crossing, not the node" (OWNER_RULING_RPA_ATLAS_20261015.md:16-18 records that S0 is a
    POSITION in the atlas, and the atlas holds nodes and edges). The atlas holds the nodes
    and the edges; a ``Crossing`` is what happens when a thought travels from one node to
    another along one edge.
  * ``Crossing`` is the real atlas model's crossing record: it holds the real ``AtlasNode``
    the thought left, the real ``AtlasLink`` it took, the real ``AtlasNode`` it arrived at,
    the tick, the thought, and its own digest. ``from_digest`` and ``to_digest`` are the real
    ``AtlasNode.region_digest()`` values, and ``relation`` is the real ``LinkType``.
  * ``cross(real_atlas, from_node_id, link, to_node_id)`` validates the act and returns the
    ``Crossing`` or raises a typed refusal. Every check is made against the real
    ``AtlasSnapshot``: an object that is not that snapshot, a link that is not a real
    ``AtlasLink``, an endpoint the snapshot does not hold, a link that does not start at
    ``from_node_id`` or does not end at ``to_node_id``, a link the snapshot does not hold,
    and an undeclared crossing between two different sorts.
  * ``is_cjt(obj)`` answers True for a ``Crossing`` and for nothing else, so no node, no
    link, no dict and no station record can be mistaken for the junction's crossing.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT define an atlas, a node, a link, a kind vocabulary or a digest scheme. All
    of those are the real model's, imported through ``atlas_adapter``; this module holds no
    second copy of any of them.
  * It does NOT build, extend or mutate an atlas. The snapshot is handed in, read, and left
    exactly as it was: every method used here is a read.
  * It does NOT decide what a tick is, or whether an atlas crossing spends a tick at all.
    CONTINUITY.md:21 indexes the path by station and tick and says nothing about crossings
    between atlas nodes, so the tick is supplied by the caller and never stamped here.
  * It does NOT carry language. Nothing in a crossing is parsed, rendered, or written as
    prose; what moves is a reference to two nodes and the link between them, and the recorded
    fields stay where they were, in the real nodes.
  * It does NOT decide what a crossing means, whether it was a good crossing, or whether the
    arriving node is true. There is no scoring, no verdict, and no promotion of a hypothetical
    node to an observed one.
  * It does NOT read the clock, the network, or any file, and it does not persist.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

import atlas_adapter

#: The crossing record is the adapter's record: real nodes, a real link, real region digests.
Crossing = atlas_adapter.CrossingRecord

#: The refusal type is the adapter's: one type for the whole bridge, with a stable code.
CrossingRefusal = atlas_adapter.AtlasAdapterRefusal

#: Refusal codes, re-exported so a caller of this module reads one vocabulary.
BAD_ATLAS = atlas_adapter.BAD_SNAPSHOT
BAD_LINK = atlas_adapter.BAD_LINK
BAD_EDGE = atlas_adapter.BAD_LINK
EDGE_NOT_IN_ATLAS = atlas_adapter.LINK_NOT_IN_SNAPSHOT
EDGE_FROM_MISMATCH = atlas_adapter.LINK_FROM_MISMATCH
EDGE_TO_MISMATCH = atlas_adapter.LINK_TO_MISMATCH
MISSING_END_NODE = atlas_adapter.MISSING_END_NODE
CROSS_SORT_UNDECLARED = atlas_adapter.CROSS_SORT_UNDECLARED
BAD_TICK = atlas_adapter.BAD_TICK
BAD_THOUGHT_ID = atlas_adapter.BAD_THOUGHT_ID
DIGEST_MISMATCH = atlas_adapter.DIGEST_MISMATCH


def is_cjt(obj) -> bool:
    """True only for a ``Crossing``. A node, a link, a dict or a station record is not one.

    The owner's ruling is what this guards: a CJT is the crossing, not the node. A real
    ``AtlasNode``, the real ``AtlasLink`` that joins two nodes, and anything that merely
    carries the fields of a crossing are all something else, and this function says so.
    """
    return atlas_adapter.is_crossing_record(obj)


# UNDECIDED IN DESIGN: what tick an atlas crossing is stamped with, and whether an atlas crossing spends a tick at all -- CONTINUITY.md:21 indexes a thought's path by station and tick and gives no tick semantics for a crossing between atlas nodes (the tick is described there as a station boundary), so this build takes the tick from the caller and never stamps or increments one.
def cross(
    real_atlas,
    from_node_id,
    link,
    to_node_id,
    thought_id: str | None = None,
    tick: int = 0,
    declared: bool = False,
) -> Crossing:
    """Validate the crossing over the REAL atlas and return it, or raise a typed refusal.

    The checks are the adapter's, made against the real snapshot:

      1. ``real_atlas`` is the real ``AtlasSnapshot`` (``BAD_SNAPSHOT``) and ``link`` is a
         real ``AtlasLink`` (``BAD_LINK``);
      2. both endpoints are nodes of that snapshot (``MISSING_END_NODE``);
      3. the link starts at ``from_node_id`` and ends at ``to_node_id``
         (``LINK_FROM_MISMATCH``, ``LINK_TO_MISMATCH``);
      4. that exact link is held by the snapshot (``LINK_NOT_IN_SNAPSHOT``);
      5. a crossing between two different sorts is refused unless ``declared=True``
         (``CROSS_SORT_UNDECLARED``).

    Check 3 is the one the design turns on: a crossing is accepted only when the link
    actually connects those two nodes.
    """
    return atlas_adapter.cross(
        real_atlas,
        from_node_id,
        link,
        to_node_id,
        thought_id=thought_id,
        tick=tick,
        declared=declared,
    )
