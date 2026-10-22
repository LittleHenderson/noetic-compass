"""atlas.py -- a minimal Recursive Possibility Atlas: nodes, edges, and sub-atlases.

WHAT THIS MODULE DOES
---------------------
  * It names the four node kinds the HELM vision requires to stay apart -- ``FACT``,
    ``GUESS``, ``POSSIBILITY`` and ``CONTEXT`` -- and refuses any other kind
    (HELM_VISION_AND_ROADMAP.md:21, ability 6: "an RPA (Recursive Possibility Atlas)
    organizing retained knowledge and possibilities, while keeping facts, guesses and
    separate contexts distinct"). Owner's words on the name: "RPA IS ATLAS I MEANT ATLAS"
    (OWNER_RULING_RPA_ATLAS_20261015.md:4).
  * It holds an ``AtlasNode``: a stable id, exactly one of those four kinds, a canonical
    payload (a dict that is JSON-canonicalisable), and a digest computed over
    {id, kind, payload}. Two nodes are the same node only if their digests match.
  * It holds an ``AtlasEdge``: from-node id, to-node id, a relation name, an explicit
    ``cross_kind_declared`` flag, and a digest. Edges are directed, and a self-loop is
    refused when the edge is built as well as when it is added.
  * It holds an ``Atlas``: nodes, edges, and SUB-ATLASES registered at entry ids, which
    is how the atlas is recursive (OWNER_RULING_RPA_ATLAS_20261015.md:16-18: "the next
    atlas entry ... may be a sub-atlas (the atlas is recursive)"). The maximum depth is
    declared by the caller. The atlas refuses a duplicate entry id whose digest differs,
    a duplicate entry id already used by a sub-atlas, an edge naming a missing node, a
    self-loop, and a cycle unless the caller marks the circle allowed.
  * ``entry(entry_id)`` returns the entry, which is either a node or a sub-atlas;
    ``entry_digest(entry_id)`` returns that entry's digest and ``entry_sort(entry_id)``
    says which of the two it is. ``neighbours(node_id)`` returns the outgoing edges in a
    deterministic order. ``frozen_digest()`` is one sha256 over the whole atlas in
    canonical order, sub-atlases included.
  * ``mixed_kind_edge(edge)`` answers whether an edge's two endpoints are of different
    kinds. ``kind_pollution_report()`` lists every edge that joins different kinds and
    raises ``KIND_POLLUTION`` when one of those edges was not explicitly declared
    ``cross_kind_declared=True``. The vision's own rule -- facts and guesses stay
    distinct -- is enforced here, not merely displayed.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide a number the design does not give. The maximum sub-atlas depth has
    no source anywhere in the packet, so ``Atlas`` refuses to be built without a declared
    ``max_depth`` and invents no default. The relation vocabulary is not decided either,
    so a relation name is copied byte for byte and checked against no list. Both are
    marked ``# UNDECIDED IN DESIGN`` where they are used and listed in README.md.
  * It does NOT promote anything. A ``POSSIBILITY`` or a ``GUESS`` never becomes a
    ``FACT`` here: there is no function in this file that changes a node's kind, and
    re-registering the same id with another kind or another payload is refused.
  * It does NOT reuse the CAS-RPU atlas model (``rpa_model.py`` at commit ``eb99855``),
    whose node statuses are OBSERVED / HYPOTHETICAL / UNKNOWN / REJECTED / VERIFIED and
    whose snapshot carries ``current_state_id`` / ``focus_node_id`` /
    ``hypothesis_branch_id``. The vision forbids building a parallel memory framework, so
    this module says plainly that it is a smaller object with a different vocabulary and
    that the mapping between the two vocabularies is NOT done here.
  * It does NOT hold language. No payload is parsed, rendered, tokenised or interpreted;
    a payload is data the caller hands in, and this module only canonicalises and hashes
    it. Nothing in this file reads or writes prose.
  * It does NOT decide that a thought may cross an edge at all -- that is crossings.py --
    and it does not decide what a station holds -- that is stations.py.
  * It does NOT read the clock, the network, or any file. Nothing here persists.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# --------------------------------------------------------------------------- #
# The four kinds, and the two sorts of entry
# --------------------------------------------------------------------------- #

#: The four node kinds. Exactly these four, and no fifth. HELM_VISION_AND_ROADMAP.md:21
#: names what must stay distinct: "facts, guesses and separate contexts", and what the
#: atlas holds together with them: "retained knowledge and possibilities".
FACT = "FACT"
GUESS = "GUESS"
POSSIBILITY = "POSSIBILITY"
CONTEXT = "CONTEXT"
KINDS = (FACT, GUESS, POSSIBILITY, CONTEXT)

#: An atlas entry is one of exactly two sorts: a node, or a sub-atlas (the recursion).
ENTRY_NODE = "NODE"
ENTRY_SUB_ATLAS = "SUB_ATLAS"

#: The maximum sub-atlas depth this module will use on its own: ``None``, because there is
#: none to use.
# UNDECIDED IN DESIGN: what the maximum depth of sub-atlas nesting is -- CONTINUITY.md:28 and STATIONS.md:143 give a cap of 5 for NESTED RPM LEVELS and the packet gives no number for ATLAS nesting, so this build invents none: the Atlas class refuses to be built without a caller-declared max_depth and never defaults it.
MAX_ATLAS_DEPTH = None

#: Refusal codes.
BAD_NODE_ID = "BAD_NODE_ID"
BAD_KIND = "BAD_KIND"
BAD_PAYLOAD = "BAD_PAYLOAD"
BAD_EDGE = "BAD_EDGE"
BAD_RELATION = "BAD_RELATION"
DIGEST_MISMATCH = "DIGEST_MISMATCH"
DUPLICATE_NODE_ID = "DUPLICATE_NODE_ID"
DUPLICATE_ENTRY_ID = "DUPLICATE_ENTRY_ID"
MISSING_NODE = "MISSING_NODE"
SELF_LOOP = "SELF_LOOP"
CYCLE_NOT_ALLOWED = "CYCLE_NOT_ALLOWED"
ENTRY_NOT_FOUND = "ENTRY_NOT_FOUND"
ENTRY_IS_NOT_A_NODE = "ENTRY_IS_NOT_A_NODE"
ATLAS_DEPTH_UNDECIDED = "ATLAS_DEPTH_UNDECIDED"
BAD_DEPTH = "BAD_DEPTH"
ATLAS_DEPTH_CAP = "ATLAS_DEPTH_CAP"
CROSS_KIND_UNDECLARED = "CROSS_KIND_UNDECLARED"
KIND_POLLUTION = "KIND_POLLUTION"
BAD_ATLAS = "BAD_ATLAS"


class AtlasRefusal(Exception):
    """A refusal with a stable code. Nothing is repaired, promoted or guessed."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# Canonical form: one way to write a payload, so one way to hash it
# --------------------------------------------------------------------------- #
def canonical_json(value) -> str:
    """Canonical JSON: sorted keys, no whitespace, ASCII only."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_of(text: str) -> str:
    """The hex sha256 of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _to_plain(value):
    """Turn a mapping or a sequence into plain JSON types. Nothing is interpreted."""
    if isinstance(value, Mapping):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    return value


def canonical_payload(payload, name: str = "payload") -> dict:
    """Return the payload as a plain dict in its canonical form, or refuse.

    The payload must be a mapping whose contents are JSON-canonicalisable. It is written
    out once, read back, and kept in that form, so two callers who hand in equal payloads
    hash to the same digest. Mapping keys are written as strings on the way through, which
    is the one conversion this function makes. Refuses ``BAD_PAYLOAD`` otherwise. Nothing
    in the payload is read, checked for truth, or interpreted: it is data, and it is
    copied, not judged.
    """
    if payload is None or not isinstance(payload, Mapping):
        raise AtlasRefusal(
            BAD_PAYLOAD, f"{name} must be a mapping, got {type(payload).__name__}"
        )
    plain = _to_plain(payload)
    if not isinstance(plain, dict):
        raise AtlasRefusal(BAD_PAYLOAD, f"{name} must be a mapping with string keys")
    try:
        text = canonical_json(plain)
    except (TypeError, ValueError) as exc:
        raise AtlasRefusal(
            BAD_PAYLOAD, f"{name} is not JSON-canonicalisable ({exc})"
        ) from exc
    return json.loads(text)


def _require_id(value, name: str, code: str = BAD_NODE_ID) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AtlasRefusal(code, f"{name} must be a non-empty string, got {value!r}")
    return value


# --------------------------------------------------------------------------- #
# A node
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AtlasNode:
    """One atlas node: a stable id, one kind, a canonical payload, and a digest.

    ``kind`` is exactly one of ``FACT``, ``GUESS``, ``POSSIBILITY`` or ``CONTEXT``. The
    digest is the sha256 of the canonical JSON of {id, kind, payload}, so two nodes are the
    same node if and only if their digests are equal -- and a node whose id matches another
    node's id but whose kind or payload differs is a different node, which is exactly why
    an atlas refuses to hold both under one id.
    """

    node_id: str
    kind: str
    payload: Mapping
    digest: str = ""

    def __post_init__(self) -> None:
        _require_id(self.node_id, "node_id")
        if self.kind not in KINDS:
            raise AtlasRefusal(
                BAD_KIND,
                f"kind {self.kind!r} is not one of the four kinds {KINDS}; facts, guesses, "
                f"possibilities and contexts are kept apart by kind and no fifth kind is "
                f"defined",
            )
        plain = canonical_payload(self.payload, f"payload of {self.node_id!r}")
        object.__setattr__(self, "payload", MappingProxyType(plain))
        computed = sha256_of(
            canonical_json({"id": self.node_id, "kind": self.kind, "payload": plain})
        )
        if self.digest and self.digest != computed:
            raise AtlasRefusal(
                DIGEST_MISMATCH,
                f"node {self.node_id!r} was given digest {self.digest!r} but its id, kind "
                f"and payload hash to {computed!r}",
            )
        object.__setattr__(self, "digest", computed)

    @property
    def canonical_payload_json(self) -> str:
        """The payload as canonical JSON text. What the digest covers."""
        return canonical_json(dict(self.payload))

    def as_dict(self) -> dict:
        """A small owned dict for a log line. No live object is carried across."""
        return {
            "entry_id": self.node_id,
            "entry_sort": ENTRY_NODE,
            "kind": self.kind,
            "payload": dict(self.payload),
            "digest": self.digest,
        }


# --------------------------------------------------------------------------- #
# An edge
# --------------------------------------------------------------------------- #
# UNDECIDED IN DESIGN: which relation names an atlas edge may carry -- no source in the packet names an atlas relation vocabulary, so this build copies the caller's relation name byte for byte and checks it against no list.
@dataclass(frozen=True)
class AtlasEdge:
    """One directed atlas edge: from a node, to a node, along a named relation.

    The digest covers {from_node_id, to_node_id, relation, cross_kind_declared}. The
    declaration is inside the digest on purpose: an edge that claims it is allowed to join
    two kinds is a different edge from one that makes no such claim, and a reader who is
    handed only a digest should not be able to confuse the two.

    A self-loop is refused here, at construction, because the design has no use for one:
    a thought that crosses from a node to itself has not crossed.
    """

    from_node_id: str
    to_node_id: str
    relation: str
    cross_kind_declared: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        _require_id(self.from_node_id, "from_node_id")
        _require_id(self.to_node_id, "to_node_id")
        if not isinstance(self.relation, str) or not self.relation.strip():
            raise AtlasRefusal(
                BAD_RELATION, f"relation must be a non-empty string, got {self.relation!r}"
            )
        if not isinstance(self.cross_kind_declared, bool):
            raise AtlasRefusal(
                BAD_EDGE,
                f"cross_kind_declared must be True or False, got "
                f"{self.cross_kind_declared!r}; a declared crossing is a claim, so it is "
                f"never inferred from anything else",
            )
        if self.from_node_id == self.to_node_id:
            raise AtlasRefusal(
                SELF_LOOP,
                f"edge {self.from_node_id!r} -> {self.to_node_id!r} is a self-loop; an "
                f"edge joins two different atlas nodes",
            )
        computed = sha256_of(
            canonical_json(
                {
                    "from": self.from_node_id,
                    "to": self.to_node_id,
                    "relation": self.relation,
                    "cross_kind_declared": self.cross_kind_declared,
                }
            )
        )
        if self.digest and self.digest != computed:
            raise AtlasRefusal(
                DIGEST_MISMATCH,
                f"edge {self.from_node_id!r} -> {self.to_node_id!r} was given digest "
                f"{self.digest!r} but its ends, relation and declaration hash to "
                f"{computed!r}",
            )
        object.__setattr__(self, "digest", computed)

    def as_dict(self) -> dict:
        """A small owned dict for a log line. No live object is carried across."""
        return {
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "relation": self.relation,
            "cross_kind_declared": self.cross_kind_declared,
            "digest": self.digest,
        }


# --------------------------------------------------------------------------- #
# The atlas
# --------------------------------------------------------------------------- #
_UNSET = object()


class Atlas:
    """Nodes, edges, and sub-atlases, with the vision's kind rule enforced.

    ``atlas_id`` names the atlas (the root's name is the caller's). ``max_depth`` is how
    deep sub-atlas nesting may go and must be declared: this build has no default because
    the design gives no number. ``depth`` is this atlas's own level, 0 for the root and one
    more for each sub-atlas.

    Everything the object refuses, it refuses at the moment of asking, with a code: a
    duplicate node id whose digest differs, a second entry under an id already used by a
    sub-atlas, an edge naming a node that is not here, a self-loop, a cycle that was not
    marked allowed, a sub-atlas below the declared maximum depth, and an undeclared edge
    between two different kinds.
    """

    def __init__(
        self,
        atlas_id: str = "root",
        max_depth=_UNSET,
        depth: int = 0,
    ) -> None:
        _require_id(atlas_id, "atlas_id", BAD_ATLAS)
        if max_depth is _UNSET or max_depth is None:
            raise AtlasRefusal(
                ATLAS_DEPTH_UNDECIDED,
                "no maximum sub-atlas depth was declared; the packet gives no number for "
                "atlas nesting, so this build refuses rather than invent one (the 5 in "
                "STATIONS.md:143 is the cap on nested RPM levels, not on atlas nesting)",
            )
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
            raise AtlasRefusal(
                BAD_DEPTH, f"max_depth {max_depth!r} is not a whole number of levels >= 0"
            )
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
            raise AtlasRefusal(BAD_DEPTH, f"depth {depth!r} is not a whole number >= 0")
        if depth > max_depth:
            raise AtlasRefusal(
                ATLAS_DEPTH_CAP,
                f"this atlas sits at depth {depth} but the declared maximum is {max_depth}",
            )
        self.atlas_id = atlas_id
        self.max_depth = max_depth
        self.depth = depth
        self._entries: dict[str, AtlasNode | Atlas] = {}
        self._edges: list[AtlasEdge] = []

    # -- reading ---------------------------------------------------------- #
    @property
    def entries(self) -> dict:
        """A read-only view: entry id -> node, or entry id -> sub-atlas."""
        return MappingProxyType(dict(self._entries))

    @property
    def edges(self) -> tuple:
        """The edges, in the order they were added."""
        return tuple(self._edges)

    def entry_ids(self) -> tuple:
        """Every entry id, sorted, so a digest never depends on insertion order."""
        return tuple(sorted(self._entries))

    def entry(self, entry_id: str):
        """The atlas entry: a node or a sub-atlas. Refuses ``ENTRY_NOT_FOUND``."""
        try:
            return self._entries[entry_id]
        except KeyError:
            raise AtlasRefusal(
                ENTRY_NOT_FOUND,
                f"atlas {self.atlas_id!r} holds no entry {entry_id!r}; its entries are "
                f"{self.entry_ids()}",
            ) from None

    def entry_sort(self, entry_id: str) -> str:
        """``NODE`` or ``SUB_ATLAS``: which sort of entry this id names."""
        return self._sort_of(self.entry(entry_id))

    @staticmethod
    def _sort_of(entry) -> str:
        return ENTRY_NODE if isinstance(entry, AtlasNode) else ENTRY_SUB_ATLAS

    def node(self, node_id: str) -> AtlasNode:
        """The node at this id. Refuses ``ENTRY_IS_NOT_A_NODE`` for a sub-atlas."""
        entry = self.entry(node_id)
        if not isinstance(entry, AtlasNode):
            raise AtlasRefusal(
                ENTRY_IS_NOT_A_NODE,
                f"entry {node_id!r} is a sub-atlas, not a node; a sub-atlas is an atlas "
                f"position and not an edge endpoint",
            )
        return entry

    def entry_digest(self, entry_id: str) -> str:
        """The digest of an entry: a node's digest, or a sub-atlas's frozen digest."""
        entry = self.entry(entry_id)
        if isinstance(entry, AtlasNode):
            return entry.digest
        return entry.frozen_digest()

    def has_edge(self, edge) -> bool:
        """Whether this exact edge (by digest) is held by the atlas."""
        if not isinstance(edge, AtlasEdge):
            raise AtlasRefusal(BAD_EDGE, f"an edge must be an AtlasEdge, got {type(edge).__name__}")
        return any(held.digest == edge.digest for held in self._edges)

    # -- building --------------------------------------------------------- #
    def add_node(self, node_id: str, kind: str, payload) -> AtlasNode:
        """Add a node and return it. Refuses a same-id node with a different digest.

        Adding the same node twice is allowed and returns the node already held: the same
        digest is the same node. Anything else under an id already in use is refused.
        """
        node = AtlasNode(node_id=node_id, kind=kind, payload=payload)
        existing = self._entries.get(node.node_id)
        if existing is not None:
            if isinstance(existing, AtlasNode) and existing.digest == node.digest:
                return existing
            held_digest = (
                existing.digest if isinstance(existing, AtlasNode) else existing.frozen_digest()
            )
            code = DUPLICATE_NODE_ID if isinstance(existing, AtlasNode) else DUPLICATE_ENTRY_ID
            raise AtlasRefusal(
                code,
                f"entry id {node.node_id!r} is already held by this atlas with digest "
                f"{held_digest!r}, and the node handed in has digest {node.digest!r}; two "
                f"different nodes may not share one id",
            )
        self._entries[node.node_id] = node
        return node

    def add_sub_atlas(self, atlas_id: str) -> "Atlas":
        """Add a sub-atlas one level deeper and return it. Enforces the declared maximum."""
        if atlas_id in self._entries:
            raise AtlasRefusal(
                DUPLICATE_ENTRY_ID,
                f"entry id {atlas_id!r} is already used by this atlas ({self._sort_of(self._entries[atlas_id])})",
            )
        sub = Atlas(atlas_id=atlas_id, max_depth=self.max_depth, depth=self.depth + 1)
        self._entries[atlas_id] = sub
        return sub

    def add_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        relation: str,
        cross_kind_declared: bool = False,
        allow_cycle: bool = False,
    ) -> AtlasEdge:
        """Add a directed edge. Refuses a missing endpoint, a self-loop, and a cycle.

        A FACT -> GUESS edge (or any edge joining two different kinds) is refused as
        ``CROSS_KIND_UNDECLARED`` unless the caller passes ``cross_kind_declared=True``.
        The refusal is what "facts and guesses stay distinct" looks like when it is
        enforced rather than described.

        ``allow_cycle=True`` is the caller's explicit mark that this circle is intended;
        without it a cycle is refused as ``CYCLE_NOT_ALLOWED``.
        """
        from_node = self._endpoint(from_node_id)
        to_node = self._endpoint(to_node_id)
        edge = AtlasEdge(
            from_node_id=from_node.node_id,
            to_node_id=to_node.node_id,
            relation=relation,
            cross_kind_declared=cross_kind_declared,
        )
        if from_node.kind != to_node.kind and not edge.cross_kind_declared:
            # UNDECIDED IN DESIGN: who may declare a cross-kind edge legal, and on what evidence -- the vision says facts and guesses stay distinct and names no declaring act, so this build accepts an explicit cross_kind_declared=True from the caller, records it on the edge and inside the edge's digest, and never infers it.
            raise AtlasRefusal(
                CROSS_KIND_UNDECLARED,
                f"edge {from_node.node_id!r} ({from_node.kind}) -> {to_node.node_id!r} "
                f"({to_node.kind}) joins two different kinds; the vision keeps facts, "
                f"guesses and contexts distinct, so such an edge must be declared with "
                f"cross_kind_declared=True and is never inferred",
            )
        if self._reaches(edge.to_node_id, edge.from_node_id):
            if not allow_cycle:
                raise AtlasRefusal(
                    CYCLE_NOT_ALLOWED,
                    f"adding {edge.from_node_id!r} -> {edge.to_node_id!r} would close a "
                    f"cycle; pass allow_cycle=True to mark the circle intended",
                )
        if not self.has_edge(edge):
            self._edges.append(edge)
        return edge

    def _endpoint(self, node_id: str) -> AtlasNode:
        if not isinstance(node_id, str) or not node_id.strip():
            raise AtlasRefusal(BAD_NODE_ID, f"endpoint {node_id!r} is not a node id")
        if node_id not in self._entries:
            raise AtlasRefusal(
                MISSING_NODE,
                f"edge names node {node_id!r}, which this atlas does not hold; its nodes "
                f"are {tuple(sorted(k for k, v in self._entries.items() if isinstance(v, AtlasNode)))}",
            )
        return self.node(node_id)

    def _reaches(self, start_id: str, target_id: str) -> bool:
        """Whether ``target_id`` is reachable from ``start_id`` along the held edges."""
        stack = [start_id]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == target_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            for edge in self._edges:
                if edge.from_node_id == current:
                    stack.append(edge.to_node_id)
        return False

    # -- the kind rule ---------------------------------------------------- #
    def mixed_kind_edge(self, edge) -> bool:
        """Whether this edge joins two endpoints of DIFFERENT kinds.

        Both endpoints must be nodes of this atlas; anything else is refused rather than
        answered, because an edge into a sub-atlas is not an edge of this atlas at all.
        """
        if not isinstance(edge, AtlasEdge):
            raise AtlasRefusal(BAD_EDGE, f"an edge must be an AtlasEdge, got {type(edge).__name__}")
        from_node = self.node(edge.from_node_id)
        to_node = self.node(edge.to_node_id)
        return from_node.kind != to_node.kind

    def kind_pollution_report(self, edges=None, strict: bool = True) -> dict:
        """Every edge that joins two different kinds, and a hard failure if undeclared.

        ``edges`` defaults to the edges this atlas holds. It may also be handed a sequence
        of candidate edges -- including an edge that was refused -- so a caller can see
        what a refusal was about without the refusal having to insert anything.

        With ``strict=True`` (the default) an undeclared cross-kind edge raises
        ``KIND_POLLUTION``: that is the hard failure the vision's rule demands. With
        ``strict=False`` the same finding is returned as data instead, so it can be printed.
        """
        scan = tuple(self._edges) if edges is None else tuple(edges)
        rows = []
        for edge in scan:
            if not isinstance(edge, AtlasEdge):
                raise AtlasRefusal(
                    BAD_EDGE, f"an edge must be an AtlasEdge, got {type(edge).__name__}"
                )
            from_node = self.node(edge.from_node_id)
            to_node = self.node(edge.to_node_id)
            if from_node.kind == to_node.kind:
                continue
            rows.append(
                {
                    "from_node_id": edge.from_node_id,
                    "from_kind": from_node.kind,
                    "to_node_id": edge.to_node_id,
                    "to_kind": to_node.kind,
                    "relation": edge.relation,
                    "cross_kind_declared": edge.cross_kind_declared,
                    "digest": edge.digest,
                }
            )
        undeclared = [row for row in rows if not row["cross_kind_declared"]]
        declared = [row for row in rows if row["cross_kind_declared"]]
        report = {
            "atlas_id": self.atlas_id,
            "atlas_digest": self.frozen_digest(),
            "kind_pollution": len(undeclared),
            "cross_kind_edges": tuple(rows),
            "undeclared": tuple(undeclared),
            "declared": tuple(declared),
        }
        if strict and undeclared:
            first = undeclared[0]
            raise AtlasRefusal(
                KIND_POLLUTION,
                f"{len(undeclared)} edge(s) join different kinds without being declared: "
                f"{first['from_node_id']!r} ({first['from_kind']}) -> "
                f"{first['to_node_id']!r} ({first['to_kind']}); facts and guesses must stay "
                f"distinct unless the crossing is declared",
            )
        return report

    # -- order and digest ------------------------------------------------- #
    def neighbours(self, node_id: str) -> tuple:
        """The outgoing edges from a node, sorted deterministically by destination."""
        node = self.node(node_id)
        outgoing = [edge for edge in self._edges if edge.from_node_id == node.node_id]
        return tuple(
            sorted(outgoing, key=lambda edge: (edge.to_node_id, edge.relation, edge.digest))
        )

    def canonical_form(self) -> dict:
        """The whole atlas as one canonical structure, sub-atlases included.

        Nodes and sub-atlas entries are ordered by entry id, and edges by (from, to,
        relation, digest), so the form does not depend on the order anything was added.
        """
        entries = []
        for entry_id in self.entry_ids():
            entry = self._entries[entry_id]
            if isinstance(entry, AtlasNode):
                entries.append(
                    {
                        "entry_id": entry.node_id,
                        "entry_sort": ENTRY_NODE,
                        "kind": entry.kind,
                        "payload": dict(entry.payload),
                        "digest": entry.digest,
                    }
                )
            else:
                entries.append(
                    {
                        "entry_id": entry.atlas_id,
                        "entry_sort": ENTRY_SUB_ATLAS,
                        "depth": entry.depth,
                        "digest": entry.frozen_digest(),
                    }
                )
        edges = [
            {
                "from_node_id": edge.from_node_id,
                "to_node_id": edge.to_node_id,
                "relation": edge.relation,
                "cross_kind_declared": edge.cross_kind_declared,
                "digest": edge.digest,
            }
            for edge in sorted(
                self._edges,
                key=lambda edge: (
                    edge.from_node_id,
                    edge.to_node_id,
                    edge.relation,
                    edge.digest,
                ),
            )
        ]
        return {
            "atlas_id": self.atlas_id,
            "depth": self.depth,
            "max_depth": self.max_depth,
            "entries": entries,
            "edges": edges,
        }

    def canonical_json_text(self) -> str:
        """The canonical form as canonical JSON text (the exact text that is hashed)."""
        return canonical_json(self.canonical_form())

    def frozen_digest(self) -> str:
        """One sha256 over the whole atlas in canonical order."""
        return sha256_of(self.canonical_json_text())

    def summary(self) -> dict:
        """Small counts. No live object is carried across."""
        nodes = [entry for entry in self._entries.values() if isinstance(entry, AtlasNode)]
        subs = [entry for entry in self._entries.values() if isinstance(entry, Atlas)]
        return {
            "atlas_id": self.atlas_id,
            "depth": self.depth,
            "max_depth": self.max_depth,
            "nodes": len(nodes),
            "sub_atlases": len(subs),
            "edges": len(self._edges),
            "kinds": tuple(sorted({node.kind for node in nodes})),
            "frozen_digest": self.frozen_digest(),
        }
