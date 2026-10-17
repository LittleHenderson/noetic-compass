"""atlas_adapter.py -- the one bridge between this circuit build and the REAL atlas model.

WHAT THIS MODULE DOES
---------------------
  * It imports the CAS-RPU Recursive Possibility Atlas that already existed in the
    repository (``real_atlas/rpa_model.py``, branch ``codex/helm-rpa-recorded-run-20260922``,
    commit ``eb9985566bd11a89f485d627186ef0efa7177f02``; the hashes are in
    ``real_atlas/PROVENANCE.md``) and gives this build the two things it needs from it:
      1. ``bind_s0(real_atlas, node_id)`` -- the S0 position of a thought, whose anchor is
         the real ``AtlasNode.region_digest()`` of that node. Nothing here computes a digest:
         the real model computes it and this module copies the value.
      2. ``cross(real_atlas, from_node_id, link, to_node_id)`` -- one CJT crossing, a
         ``CrossingRecord`` holding the real ``AtlasNode`` at each end and the real
         ``AtlasLink`` it travelled along, with both real region digests on the record and
         the real ``LinkType`` as its relation.
  * It answers glue-back with the REAL model's own two verdicts: ``glue_back(nodes)`` calls
    ``compatibility(nodes)`` and ``certify_overlap(nodes, witness)`` and reports what they
    said. ``glue_back_ok(nodes)`` is True only when BOTH real verdicts pass. This module
    contains no glue rule of its own: no field comparison, no overlap test, no witness
    choice. If the real model refuses, the refusal is surfaced as a typed
    ``AtlasAdapterRefusal`` carrying the real model's own message.
  * It re-hashes the six copied real-model files and refuses if any byte changed
    (``verify_real_model()``), so "the real model is the only atlas" is a checkable claim.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT build, extend, or re-implement an atlas. There is no node class, no link
    class, no kind vocabulary, no edge rule and no digest scheme in this file. Every one of
    those is the real model's.
  * It does NOT decide glue-back. The glue answer is ``compatibility()``'s answer and
    ``certify_overlap()``'s answer, joined by ``and``; the docstring says which is which so
    a reader can check that no third rule crept in.
  * It does NOT rename the real model's vocabulary. The real model's ``NodeKind`` (idea
    context / state / region / evidence) and ``NodeStatus`` (observed / hypothetical /
    unknown / rejected / verified) keep their own names and their own values. The one word
    this build adds is "sort", which means exactly the pair (``kind.value``,
    ``status.value``) and nothing else.
  * It does NOT promote anything. A node whose status is ``hypothetical`` is not made
    ``observed`` by any function here. The real model holds the records; this module reads
    them and copies leaves out.
  * It does NOT copy whole live objects across a boundary. What leaves is a frozen record
    of small leaf values (ids, digests, kind and status words, counts).
  * It does NOT read the clock, the network, or any file except the six real-model files it
    hashes. It persists nothing and calls no cloud service.

CLAIM CEILING (corrected in v4 -- S0 anchors on the real atlas model):
    MECHANISM ONLY. S0 ANCHORS TO THE REAL ATLAS MODEL AT COMMIT eb998556; THIS BUILD ADDS NO ATLAS OF ITS OWN. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from real_atlas.canonical import digest as real_digest
from real_atlas.model import ContractError
from real_atlas.rpa_model import (
    MAX_ATLAS_BYTES,
    MAX_DEPTH,
    MAX_NODES,
    AtlasContext,
    AtlasLink,
    AtlasNode,
    AtlasSnapshot,
    CompatibilityReport,
    DeferredExpansion,
    ExpansionResult,
    LinkType,
    NodeKind,
    NodeStatus,
    OverlapCertificate,
    certify_overlap,
    compatibility,
    validate_profile40,
)

#: The real model's interface, re-exported, so a caller of this build imports one place and
#: still gets the real classes. Nothing in this tuple is defined here; each name is the real
#: model's own object, checked by the test that reads this tuple.
REAL_MODEL_EXPORTS = (
    AtlasContext,
    AtlasNode,
    AtlasLink,
    AtlasSnapshot,
    OverlapCertificate,
    CompatibilityReport,
    DeferredExpansion,
    ExpansionResult,
    LinkType,
    NodeKind,
    NodeStatus,
    validate_profile40,
    certify_overlap,
    compatibility,
)

# --------------------------------------------------------------------------- #
# Where the real model came from
# --------------------------------------------------------------------------- #

#: The branch and commit the real model was copied from. Recorded so a reader can re-extract
#: it and compare, without this build having to trust a sentence.
REAL_MODEL_BRANCH = "codex/helm-rpa-recorded-run-20260922"
REAL_MODEL_COMMIT = "eb9985566bd11a89f485d627186ef0efa7177f02"
REAL_MODEL_COMMIT_PATH = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/"

#: The sha256 of every file copied out of that commit, measured on the bytes on disk. The
#: provenance file holds the same numbers with the full source path of each.
REAL_MODEL_SHA256 = {
    "rpa_model.py": "323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01",
    "canonical.py": "424323335452fecd26cd6659136475c0fd19bda695ab07811d34d1734564877a",
    "model.py": "aafa82f0267d0e741a90ba095d939da47401be577b5682832608a6845be54766",
    "rpa_ohm_atlas.py": "6aa030651278f217965a788427d55d3f475bb666b366a8095d6a5fb05be9694f",
    "CAS_RPA_OHM_ATLAS_20260922.md": "516aa180212643c97da6241dfe618548d71be422e3d966d747cad812c95acc34",
    "VERIFICATION.md": "5eec0108af1408d91c44063fb4950723c52e3170856b6947bfad77bef69602d0",
}

#: The folder the real model sits in, beside this file.
REAL_MODEL_DIR = Path(__file__).resolve().parent / "real_atlas"

#: The measured bounds the real model states in its own file. Re-exported so a caller reads
#: one number, from the real source, rather than a number this build remembers.
ATLAS_MAX_NODES = MAX_NODES
ATLAS_MAX_BYTES = MAX_ATLAS_BYTES
ATLAS_MAX_EXPANSION_DEPTH = MAX_DEPTH

#: The one sort of entry the real model holds. The stand-in atlas this build used to carry
#: had two (a node and a sub-atlas); the real model has exactly one, so this build has one.
ENTRY_NODE = "NODE"

#: Refusal codes.
BAD_SNAPSHOT = "BAD_SNAPSHOT"
BAD_NODE_ID = "BAD_NODE_ID"
NODE_NOT_FOUND = "NODE_NOT_FOUND"
BAD_ATLAS_ENTRY = "BAD_ATLAS_ENTRY"
REAL_MODEL_REFUSAL = "REAL_MODEL_REFUSAL"
REAL_MODEL_FILES_CHANGED = "REAL_MODEL_FILES_CHANGED"
BAD_LINK = "BAD_LINK"
MISSING_END_NODE = "MISSING_END_NODE"
LINK_FROM_MISMATCH = "LINK_FROM_MISMATCH"
LINK_TO_MISMATCH = "LINK_TO_MISMATCH"
LINK_NOT_IN_SNAPSHOT = "LINK_NOT_IN_SNAPSHOT"
CROSS_SORT_UNDECLARED = "CROSS_SORT_UNDECLARED"
BAD_TICK = "BAD_TICK"
BAD_THOUGHT_ID = "BAD_THOUGHT_ID"
BAD_DECLARATION = "BAD_DECLARATION"
DIGEST_MISMATCH = "DIGEST_MISMATCH"

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class AtlasAdapterRefusal(Exception):
    """A refusal with a stable code. Nothing is repaired, guessed or defaulted."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The real model's files, hashed
# --------------------------------------------------------------------------- #
def real_model_files() -> dict:
    """The sha256 of every copied real-model file, hashed now. ``{name: hex}``."""
    hashes = {}
    for name in sorted(REAL_MODEL_SHA256):
        path = REAL_MODEL_DIR / name
        if not path.is_file():
            raise AtlasAdapterRefusal(
                REAL_MODEL_FILES_CHANGED, f"real-model file {name!r} is missing from {REAL_MODEL_DIR}"
            )
        hashes[name] = sha256(path.read_bytes()).hexdigest()
    return hashes


def verify_real_model() -> dict:
    """Re-hash the copies and refuse if any byte moved. Returns ``{name: hex}``.

    This is the check behind the sentence "the real model is the only atlas": the six files
    are read-only inputs, and the run fails rather than quietly using a changed one.
    """
    now = real_model_files()
    changed = [name for name in sorted(now) if now[name] != REAL_MODEL_SHA256[name]]
    if changed:
        raise AtlasAdapterRefusal(
            REAL_MODEL_FILES_CHANGED,
            f"{len(changed)} real-model file(s) no longer hash to the recorded value: "
            f"{changed}; the copies are read-only inputs and must not be edited",
        )
    return now


#: The hashes of the copies, checked once at import, so no later caller can proceed on a
#: changed file by forgetting to ask.
REAL_MODEL_VERIFIED = verify_real_model()


# --------------------------------------------------------------------------- #
# Small readings of real values
# --------------------------------------------------------------------------- #
def _real(call, label: str):
    """Run one call on the real model, turning its refusal into this build's typed one."""
    try:
        return call()
    except ContractError as refusal:
        raise AtlasAdapterRefusal(
            REAL_MODEL_REFUSAL, f"the real atlas model refused {label}: {refusal}"
        ) from refusal


def _as_snapshot(real_atlas) -> AtlasSnapshot:
    if type(real_atlas) is not AtlasSnapshot:
        raise AtlasAdapterRefusal(
            BAD_SNAPSHOT,
            f"the real atlas model is an AtlasSnapshot, got {type(real_atlas).__name__}; an "
            f"object that merely carries digest-shaped fields is not the real atlas",
        )
    return real_atlas


def nodes_of(real_atlas) -> dict:
    """The real snapshot's nodes by id. A copy of the real map, not a new one."""
    return _as_snapshot(real_atlas).node_map()


def node_of(real_atlas, node_id) -> AtlasNode:
    """The real ``AtlasNode`` at ``node_id``, or a typed refusal."""
    snapshot = _as_snapshot(real_atlas)
    if not isinstance(node_id, str) or not node_id.strip():
        raise AtlasAdapterRefusal(BAD_NODE_ID, f"{node_id!r} is not a node id at all")
    nodes = snapshot.node_map()
    if node_id not in nodes:
        raise AtlasAdapterRefusal(
            NODE_NOT_FOUND,
            f"the real snapshot holds no node {node_id!r}; its nodes are {tuple(sorted(nodes))}",
        )
    return nodes[node_id]


# UNDECIDED IN DESIGN: which of the vision's four kind words a real node carries -- the real model has NodeKind (idea_context / state / region / evidence) and NodeStatus (observed / hypothetical / unknown / rejected / verified) and no word FACT, GUESS, POSSIBILITY or CONTEXT, so this build compares the real (kind, status) pair as a "sort" and renames none of the real words; the mapping from the vision's four kinds onto that pair is not made here.
def sort_of(node) -> tuple:
    """A node's sort: exactly ``(kind.value, status.value)``, the real model's own two words."""
    if type(node) is not AtlasNode:
        raise AtlasAdapterRefusal(
            BAD_SNAPSHOT, f"a sort is read from a real AtlasNode, got {type(node).__name__}"
        )
    return node.kind.value, node.status.value


def sorts_differ(first, second) -> bool:
    """Whether two real nodes carry different sorts. Never a renamed vocabulary."""
    return sort_of(first) != sort_of(second)


# --------------------------------------------------------------------------- #
# The S0 position
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class S0Anchor:
    """The S0 position of a thought, anchored on a REAL node's region digest.

    ``region_digest`` is the real ``AtlasNode.region_digest()``: the sha256 the real model
    computes over the node's id, its context and its members. ``atlas_digest`` is the real
    snapshot's own digest, so a reader can say which snapshot the position was read from.
    ``node_kind`` and ``node_status`` are the real ``NodeKind`` and ``NodeStatus`` values.
    """

    atlas_digest: str
    node_id: str
    region_digest: str
    context_id: str
    node_kind: str
    node_status: str
    station: str = "S0"

    @property
    def binding(self) -> dict:
        """The ``atlas_entry`` mapping a station crossing carries. A copy, never the record."""
        return {
            "atlas_id": None,
            "atlas_digest": self.atlas_digest,
            "atlas_depth": 0,
            "entry_id": self.node_id,
            "entry_sort": ENTRY_NODE,
            "entry_digest": self.region_digest,
            "node_kind": self.node_kind,
            "node_status": self.node_status,
        }

    def as_dict(self) -> dict:
        return {
            "station": self.station,
            "atlas_digest": self.atlas_digest,
            "node_id": self.node_id,
            "region_digest": self.region_digest,
            "context_id": self.context_id,
            "node_kind": self.node_kind,
            "node_status": self.node_status,
        }


def bind_s0(real_atlas, node_id) -> S0Anchor:
    """Bind S0 to a REAL atlas node and return the position, anchored on its region digest.

    Two refusals and no fallback: ``BAD_SNAPSHOT`` when what was handed in is not the real
    model's ``AtlasSnapshot``, and ``NODE_NOT_FOUND`` when the snapshot holds no such node.
    Nothing is created, hashed or guessed here: the digest is the real model's own
    ``region_digest``, copied as a leaf value.
    """
    snapshot = _as_snapshot(real_atlas)
    node = node_of(snapshot, node_id)
    return S0Anchor(
        atlas_digest=snapshot.snapshot_digest,
        node_id=node.node_id,
        region_digest=node.region_digest,
        context_id=node.context.context_id,
        node_kind=node.kind.value,
        node_status=node.status.value,
    )


def anchor_from_binding(binding) -> str:
    """The anchor a crossing's ``atlas_entry`` binding stands for: a REAL region digest.

    Refuses ``BAD_ATLAS_ENTRY`` when the binding names a sort of entry the real model does not
    have, or when its digest is not a sha256. This is the one place the anchor rule lives, so
    ``continuity.anchor()`` cannot drift away from it.
    """
    if not isinstance(binding, dict) and not hasattr(binding, "get"):
        raise AtlasAdapterRefusal(
            BAD_ATLAS_ENTRY, f"an atlas binding is a mapping, got {type(binding).__name__}"
        )
    entry_sort = binding.get("entry_sort", ENTRY_NODE)
    if entry_sort != ENTRY_NODE:
        raise AtlasAdapterRefusal(
            BAD_ATLAS_ENTRY,
            f"entry_sort {entry_sort!r} is not {ENTRY_NODE}; the real atlas model holds one "
            f"sort of entry (an AtlasNode) and no sub-atlas, so it cannot anchor a position",
        )
    digest = binding.get("entry_digest")
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        raise AtlasAdapterRefusal(
            BAD_ATLAS_ENTRY,
            f"entry_digest {digest!r} is not a sha256; a region digest is a digest somebody "
            f"computed, and no anchor is invented here",
        )
    return digest


# --------------------------------------------------------------------------- #
# The crossing: a real link between two real nodes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CrossingRecord:
    """One CJT: a thought travelling one REAL ``AtlasLink`` between two REAL ``AtlasNode``s.

    The record holds the real node at each end (``from_node``, ``to_node``) and the real link
    it went along (``link``), so ``relation`` is a real ``LinkType``. ``from_digest`` and
    ``to_digest`` are the real ``region_digest`` values. ``declared`` records the caller's
    statement that a crossing between two different sorts is intended; it is inside the
    crossing's own digest, so a declared crossing and an undeclared one are different records.

    ``digest`` is computed by the real model's own canonical hasher over the two region
    digests, the link's own recorded form, the tick, the thought and the declaration.
    """

    from_node: AtlasNode
    link: AtlasLink
    to_node: AtlasNode
    tick: int = 0
    thought_id: str | None = None
    declared: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        if type(self.from_node) is not AtlasNode:
            raise AtlasAdapterRefusal(
                MISSING_END_NODE,
                f"from_node must be a real AtlasNode, got {type(self.from_node).__name__}",
            )
        if type(self.to_node) is not AtlasNode:
            raise AtlasAdapterRefusal(
                MISSING_END_NODE,
                f"to_node must be a real AtlasNode, got {type(self.to_node).__name__}",
            )
        if type(self.link) is not AtlasLink:
            raise AtlasAdapterRefusal(
                BAD_LINK, f"link must be a real AtlasLink, got {type(self.link).__name__}"
            )
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise AtlasAdapterRefusal(BAD_TICK, f"tick {self.tick!r} is not a whole number of ticks")
        if self.thought_id is not None and (
            not isinstance(self.thought_id, str) or not self.thought_id.strip()
        ):
            raise AtlasAdapterRefusal(
                BAD_THOUGHT_ID,
                f"thought_id must be a non-empty string or None, got {self.thought_id!r}",
            )
        if not isinstance(self.declared, bool):
            raise AtlasAdapterRefusal(
                BAD_DECLARATION,
                f"declared must be True or False, got {self.declared!r}; a declaration is a "
                f"claim and is never inferred",
            )
        computed = real_digest(
            {
                "from_region_digest": self.from_node.region_digest,
                "link": self.link.to_dict(),
                "to_region_digest": self.to_node.region_digest,
                "tick": self.tick,
                "thought_id": self.thought_id,
                "declared": self.declared,
            }
        )
        if self.digest and self.digest != computed:
            raise AtlasAdapterRefusal(
                DIGEST_MISMATCH,
                f"the crossing was given digest {self.digest!r} but its two region digests, "
                f"its link, its tick, its thought and its declaration hash to {computed!r}",
            )
        object.__setattr__(self, "digest", computed)

    # -- the leaf values a reader may need -------------------------------- #
    @property
    def from_node_id(self) -> str:
        return self.from_node.node_id

    @property
    def to_node_id(self) -> str:
        return self.to_node.node_id

    @property
    def from_digest(self) -> str:
        """The real ``region_digest`` of the node the crossing left."""
        return self.from_node.region_digest

    @property
    def to_digest(self) -> str:
        """The real ``region_digest`` of the node the crossing arrived at."""
        return self.to_node.region_digest

    @property
    def relation(self) -> LinkType:
        """The real ``LinkType`` the crossing travelled along."""
        return self.link.relation

    @property
    def link_id(self) -> str:
        return self.link.link_id

    @property
    def joins_different_sorts(self) -> bool:
        """True when the two ends differ in the real model's kind or status."""
        return sorts_differ(self.from_node, self.to_node)

    def as_dict(self) -> dict:
        """A small owned dict for a log line. No live object is carried across."""
        return {
            "from_node_id": self.from_node_id,
            "from_region_digest": self.from_digest,
            "from_sort": sort_of(self.from_node),
            "to_node_id": self.to_node_id,
            "to_region_digest": self.to_digest,
            "to_sort": sort_of(self.to_node),
            "link_id": self.link_id,
            "relation": self.relation.value,
            "joins_different_sorts": self.joins_different_sorts,
            "declared": self.declared,
            "tick": self.tick,
            "thought_id": self.thought_id,
            "digest": self.digest,
        }


def is_crossing_record(obj) -> bool:
    """True only for a ``CrossingRecord``. No node, link, dict or station record is one."""
    return isinstance(obj, CrossingRecord)


def _endpoint(snapshot, node_id, name: str) -> AtlasNode:
    """The real node at this id, or the crossing's own refusal naming which end is wrong."""
    try:
        return node_of(snapshot, node_id)
    except AtlasAdapterRefusal as refusal:
        if refusal.code == NODE_NOT_FOUND:
            raise AtlasAdapterRefusal(
                MISSING_END_NODE,
                f"{name} {node_id!r} is not a node of the real snapshot; its nodes are "
                f"{tuple(sorted(snapshot.node_map()))}",
            ) from refusal
        raise


# UNDECIDED IN DESIGN: who may declare a crossing between two different sorts legal, and on what evidence -- the real model's AtlasLink carries no declaration field and the vision says facts and guesses stay distinct without naming a declaring act, so this build takes an explicit declared=True from the caller, records it on the crossing and inside the crossing's digest, and never infers it.
def cross(
    real_atlas,
    from_node_id,
    link,
    to_node_id,
    thought_id: str | None = None,
    tick: int = 0,
    declared: bool = False,
) -> CrossingRecord:
    """Validate one crossing over the REAL atlas and return it, or a typed refusal.

    Six checks, in this order, each with its own code:

      1. ``real_atlas`` is the real ``AtlasSnapshot`` (``BAD_SNAPSHOT``) and ``link`` is a
         real ``AtlasLink`` (``BAD_LINK``);
      2. both endpoints are nodes of that snapshot (``MISSING_END_NODE``);
      3. the link starts at ``from_node_id`` and ends at ``to_node_id``
         (``LINK_FROM_MISMATCH``, ``LINK_TO_MISMATCH``);
      4. that exact link is one the snapshot holds (``LINK_NOT_IN_SNAPSHOT``);
      5. if the two ends carry different sorts, the caller must declare the crossing
         (``CROSS_SORT_UNDECLARED``);
      6. the record's own digest recomputes (``DIGEST_MISMATCH``).

    Check 3 is the one the design turns on: a crossing is accepted only when the link really
    joins those two nodes, and the snapshot is the authority on which links it holds.
    """
    snapshot = _as_snapshot(real_atlas)
    if type(link) is not AtlasLink:
        raise AtlasAdapterRefusal(
            BAD_LINK, f"link must be a real AtlasLink, got {type(link).__name__}"
        )
    from_node = _endpoint(snapshot, from_node_id, "from_node_id")
    to_node = _endpoint(snapshot, to_node_id, "to_node_id")
    if link.source_id != from_node.node_id:
        raise AtlasAdapterRefusal(
            LINK_FROM_MISMATCH,
            f"the link starts at {link.source_id!r}, not at {from_node.node_id!r}; a crossing "
            f"starts where its link starts",
        )
    if link.target_id != to_node.node_id:
        raise AtlasAdapterRefusal(
            LINK_TO_MISMATCH,
            f"the link ends at {link.target_id!r}, not at {to_node.node_id!r}; a crossing "
            f"arrives where its link arrives",
        )
    if not any(held == link for held in snapshot.links):
        raise AtlasAdapterRefusal(
            LINK_NOT_IN_SNAPSHOT,
            f"the link {link.link_id!r} is not one the real snapshot holds; nothing may be "
            f"crossed that the real atlas does not hold",
        )
    if sorts_differ(from_node, to_node) and not declared:
        raise AtlasAdapterRefusal(
            CROSS_SORT_UNDECLARED,
            f"the crossing leaves a node of sort {sort_of(from_node)} for one of sort "
            f"{sort_of(to_node)} and the crossing was not declared; the vision keeps facts, "
            f"guesses and contexts distinct, so such a crossing must be declared and is "
            f"never inferred",
        )
    return CrossingRecord(
        from_node=from_node,
        link=link,
        to_node=to_node,
        tick=tick,
        thought_id=thought_id,
        declared=declared,
    )


# --------------------------------------------------------------------------- #
# Glue-back: the real model's two verdicts, and nothing else
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GlueBack:
    """What the REAL model said about a set of nodes gluing back together.

    Every decision field here is the real model's output, copied: ``compatible``,
    ``same_context``, ``shared_fields`` and ``conflicting_fields`` come from
    ``compatibility()``; ``certificate_id`` and ``witness_id`` come from
    ``certify_overlap()``. ``ok`` is those two verdicts joined with ``and`` and is the only
    thing this build adds, so there is no second glue rule to disagree with the real one.
    """

    node_ids: tuple
    region_digests: tuple
    same_context: bool
    shared_fields: tuple
    conflicting_fields: tuple
    compatible: bool
    witness_id: str | None
    certificate_id: str | None

    @property
    def ok(self) -> bool:
        """True only when the real model both reports compatibility and certifies overlap."""
        return bool(self.compatible and self.certificate_id is not None)

    def as_dict(self) -> dict:
        return {
            "node_ids": self.node_ids,
            "region_digests": self.region_digests,
            "same_context": self.same_context,
            "shared_fields": self.shared_fields,
            "conflicting_fields": self.conflicting_fields,
            "compatible": self.compatible,
            "witness_id": self.witness_id,
            "certificate_id": self.certificate_id,
            "ok": self.ok,
            "boundary": "the real model's shared-field consistency and common-witness "
            "certificate only; not a sheaf gluing proof",
        }


def glue_back(nodes, witness_id=None) -> GlueBack:
    """Ask the REAL model whether these nodes glue back, and report its two answers.

    Both real calls are made and nothing is short-circuited, so the report says what each
    real function said. If the real model refuses -- for example because two regions share no
    member, or because fewer than two typed views were handed in -- the refusal comes out as
    ``AtlasAdapterRefusal(REAL_MODEL_REFUSAL)`` carrying the real model's own message.
    """
    nodes = tuple(nodes) if not isinstance(nodes, tuple) else nodes
    report = _real(lambda: compatibility(nodes), "compatibility")
    certificate = _real(lambda: certify_overlap(nodes, witness_id), "certify_overlap")
    return GlueBack(
        node_ids=report.node_ids,
        region_digests=tuple((node.node_id, node.region_digest) for node in nodes),
        same_context=report.same_context,
        shared_fields=report.shared_fields,
        conflicting_fields=report.conflicting_fields,
        compatible=report.compatible,
        witness_id=certificate.witness_id,
        certificate_id=certificate.certificate_id,
    )


def glue_back_ok(nodes, witness_id=None) -> bool:
    """True only when the real ``compatibility()`` and ``certify_overlap()`` both pass."""
    return glue_back(nodes, witness_id).ok
