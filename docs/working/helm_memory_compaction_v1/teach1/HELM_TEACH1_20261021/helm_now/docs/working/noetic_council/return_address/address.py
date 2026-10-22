"""address.py -- the exact address of one suspended thread, and the root observation reference.

WHAT THIS MODULE DOES
---------------------
  * It implements, in code, the owner's ruling of 2026-09-24: "as the sub recurses
    throughout the RPM system through the Atlas, or the RPA, the coordinate system, or system
    of coordinates, could be used to establish its way back through the RPM, through the
    recursive prerequisite system, back to the original CJT."
    [D:\\tksCAS-agent-bus\\CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 7]
  * ``ReturnAddress`` binds ONE open thread to an exact address: the episode, the branch, the
    saved snapshot (as that snapshot's own sha256 digest), the Bias version, and the call
    occurrence. Every one of those fields is required, typed, and checked. A field that is
    not supplied is a typed refusal (``MISSING_FIELD``), never a default and never a guess.
  * ``is_exact(other)`` compares every field. A partial match is NOT a match: nothing here
    answers "the nearest address", "the closest match", "the latest same-named CJT" or "the
    same thing in another snapshot". ``require_exact(other)`` turns a partial match into the
    typed refusal ``INEXACT_ADDRESS`` and names the fields that differ.
  * ``child_of(parent_address, call_id)`` produces the child occurrence's address, so one
    call occurrence is distinguishable from another: "A module's identity alone is not a call
    identity: one CJT can be invoked more than once." [addendum, line 12]
  * ``to_root(address)`` returns an ``ObservationReference``: the root reference kept "for
    the original goal/CJT throughout", and it is a different type from a return address on
    purpose, so a root reference can never be mistaken for a way back. ``is_return_path`` is
    ``True`` on every address and ``False`` on every observation reference, and
    ``ObservationReference.as_return_destination()`` refuses with ``NO_ROOT_SHORTCUT``.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide where a thread is. An address is assembled from values the caller
    states; nothing here walks an atlas, searches for a node, or infers a branch.
  * It does NOT hold the threads, the suspension state, or the repair. That is ``stack.py``.
    This module is the address and nothing else: no lookup, no ordering, no waiting caller.
  * It does NOT use profile coordinates or screen position to locate anything. The addendum
    keeps three kinds of location distinct [addendum, lines 11-15]: distance to zero, nearest
    flower, nearest profile and recentring are all excluded here by there being no such
    function and no such field.
  * It does NOT treat an address as authority. "The exact address is a lookup key, not
    authority by itself." [addendum, line 25] The coordinator in ``stack.py`` still checks
    that the caller is waiting, that the result is valid for it, and that resumption is
    permitted.
  * It does NOT compute a digest. ``snapshot_digest`` is a sha256 the atlas model computed
    over a saved snapshot; this module checks that it is shaped like one and copies it.
  * It does NOT read the clock, the file system, the network, or persist anything.

CANON, QUOTED VERBATIM (ASCII transliteration only)
---------------------------------------------------
    OWNER_SENTENCE               -- the owner's addition, addendum line 7
    ADDENDUM_RETURN_RULE         -- addendum line 9, the immediate-caller rule
    ADDENDUM_CALL_IDENTITY       -- addendum line 12, occurrence identity
    ADDENDUM_LOOKUP_KEY          -- addendum line 25, address is a key, not authority
    CANON_THM_27_3               -- Theorem 27.3, depth-wise integrity, Chapter_27 line 61
    CANON_DIRTY_PROPAGATION      -- the dirty-child rule, Chapter_27 line 63

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NO CIRCUIT USES THIS YET.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "ReturnAddress",
    "ObservationReference",
    "ReturnRefusal",
    "AddressRefusal",
    "child_of",
    "to_root",
    "exactness_report",
    "NO_ROOT_SHORTCUT",
    "NOT_A_RETURN_PATH",
    "MISSING_FIELD",
    "BAD_FIELD_TYPE",
    "EMPTY_FIELD",
    "BAD_SNAPSHOT_DIGEST",
    "BAD_BIAS_VERSION",
    "INEXACT_ADDRESS",
    "BAD_PARENT",
    "DUPLICATE_CALL_ID",
    "ROOT_NOT_RESOLVABLE",
    "OWNER_SENTENCE",
    "ADDENDUM_RETURN_RULE",
    "ADDENDUM_CALL_IDENTITY",
    "ADDENDUM_LOOKUP_KEY",
    "CANON_THM_27_3",
    "CANON_DIRTY_PROPAGATION",
]

# --------------------------------------------------------------------------- #
# The canon this module is written against, quoted verbatim
# --------------------------------------------------------------------------- #

OWNER_SENTENCE = (
    '"Also, as the sub recurses throughout the RPM system through the Atlas, or the RPA, the '
    'coordinate system, or system of coordinates, could be used to establish its way back '
    'through the RPM, through the recursive prerequisite system, back to the original CJT."  '
    "[CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 7]"
)

ADDENDUM_RETURN_RULE = (
    '"A successfully checked child result returns to its immediate waiting caller. That caller '
    'completes its own remaining work before its result returns further. Retain a root '
    'reference to the original goal/CJT throughout. A direct root shortcut must not mark '
    'intermediate prerequisites complete."  [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 9]'
)

ADDENDUM_CALL_IDENTITY = (
    '"Reuse existing stable runtime identifiers and the atlas\'s snapshot-bound address '
    'scheme. A module\'s identity alone is not a call identity: one CJT can be invoked more '
    'than once."  [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 12]'
)

ADDENDUM_LOOKUP_KEY = (
    '"The exact address is a lookup key, not authority by itself. The coordinator still checks '
    'whether the caller is waiting, the result is valid for it, and resumption is permitted."  '
    "[CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 25]"
)

CANON_THM_27_3 = (
    '"Theorem 27.3 (Depth-Wise Integrity). For any recursive depth n, the Section-Retraction '
    'identity \\varepsilon^(n) \\circ \\eta^(n) = \\id^(n) must hold independently."  '
    "[Chapter_27_RPM_Structure.md, line 61]"
)

CANON_DIRTY_PROPAGATION = (
    '"This ensures that a child chain cannot resolve a block by violating the architecture. If '
    'a child chain at any level uses a \'dirty\' resolution (e.g., a Power bypass), the '
    'retraction morphism fails, the block propagates back up the stack, and the entire parent '
    'chain is invalidated."  [Chapter_27_RPM_Structure.md, line 63]'
)

# --------------------------------------------------------------------------- #
# Refusal codes. One word per refusal, and a refusal is never a default.
# --------------------------------------------------------------------------- #

NOT_A_RETURN_PATH = "NOT_A_RETURN_PATH"
MISSING_FIELD = "MISSING_FIELD"
BAD_FIELD_TYPE = "BAD_FIELD_TYPE"
EMPTY_FIELD = "EMPTY_FIELD"
BAD_SNAPSHOT_DIGEST = "BAD_SNAPSHOT_DIGEST"
BAD_BIAS_VERSION = "BAD_BIAS_VERSION"
INEXACT_ADDRESS = "INEXACT_ADDRESS"
BAD_PARENT = "BAD_PARENT"
DUPLICATE_CALL_ID = "DUPLICATE_CALL_ID"
ROOT_NOT_RESOLVABLE = "ROOT_NOT_RESOLVABLE"
NO_ROOT_SHORTCUT = "NO_ROOT_SHORTCUT"

#: A saved snapshot is named by the sha256 the atlas model computed over it.
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")

#: The sentinel that says "this argument was not supplied at all". It is deliberately not
#: ``None``: ``None`` is a value a caller may have to state explicitly (``parent_call_id`` on
#: the root call), so it cannot double as "absent".
_UNSET = object()


class ReturnRefusal(Exception):
    """A refusal with a stable code. Nothing is repaired, guessed, defaulted or filled in.

    One refusal type serves ``address.py``, ``stack.py``, ``dirty.py`` and
    ``atlas_binding.py``, so a caller catches one class and reads ``.code`` for the word.
    ``AddressRefusal`` is an alias of this class, for readers who expect that name here.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


#: The same class under the name a reader of this module may reach for.
AddressRefusal = ReturnRefusal


# --------------------------------------------------------------------------- #
# Field readers: every field is required and typed
# --------------------------------------------------------------------------- #
def _text(name: str, value) -> str:
    """A required non-blank string field, or the typed refusal that says why not."""
    if value is _UNSET:
        raise ReturnRefusal(
            MISSING_FIELD,
            f"{name} was not supplied. Every field of a return address is required; there is "
            f"no default and nothing is filled in on the caller's behalf",
        )
    if not isinstance(value, str):
        raise ReturnRefusal(
            BAD_FIELD_TYPE, f"{name} must be a str, got {type(value).__name__}"
        )
    if not value.strip():
        raise ReturnRefusal(EMPTY_FIELD, f"{name} is blank; a blank field names nothing")
    return value


def _snapshot_digest(name: str, value) -> str:
    """A required saved-snapshot digest: a sha256, as the atlas model computes one."""
    text = _text(name, value)
    if _DIGEST.match(text) is None:
        raise ReturnRefusal(
            BAD_SNAPSHOT_DIGEST,
            f"{name} {text!r} is not a sha256 digest. A snapshot digest is a number the atlas "
            f"model computed over a saved snapshot and this build copies it; no digest is "
            f"invented here",
        )
    return text


def _bias_version(name: str, value) -> int:
    """A required Bias version: a whole number >= 0. ``True`` is not a version."""
    if value is _UNSET:
        raise ReturnRefusal(
            MISSING_FIELD,
            f"{name} was not supplied. A returned thread must carry a strictly newer Bias "
            f"than the one it suspended, so the suspended one has to be named exactly",
        )
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReturnRefusal(
            BAD_BIAS_VERSION, f"{name} must be a whole number, got {type(value).__name__}"
        )
    if value < 0:
        raise ReturnRefusal(BAD_BIAS_VERSION, f"{name} must be >= 0, got {value}")
    return value


def _parent_call_id(value):
    """The parent call occurrence: a non-blank string, or an explicit ``None`` for the root."""
    if value is _UNSET:
        raise ReturnRefusal(
            MISSING_FIELD,
            "parent_call_id was not supplied. A thread is either a child of a named call "
            "occurrence or the root call, and the root is stated explicitly as None",
        )
    if value is None:
        return None
    return _text("parent_call_id", value)


# --------------------------------------------------------------------------- #
# The return address
# --------------------------------------------------------------------------- #
class ReturnAddress:
    """The exact address of one open thread. Five named fields, plus the parent occurrence.

    ``episode``         the root goal this thread belongs to.
    ``branch``          the branch the thread is on.
    ``snapshot_digest`` the saved snapshot the thread is bound to, as that snapshot's own
                        sha256 digest (the atlas model computes it; this build copies it).
    ``bias_version``    the Bias version at suspension. A return must carry a strictly newer
                        one -- see ``stack.py``.
    ``call_id``         the call OCCURRENCE. One CJT can be invoked more than once, so the
                        occurrence is named, not the module or the node.
    ``parent_call_id``  the immediate waiting caller's occurrence, or ``None`` on the root
                        call (stated explicitly, never defaulted).

    The address is immutable, hashable and comparable by every field. There is no depth
    field, no coordinate, no screen position and no distance: an address is a lookup key, not
    authority, and not a chart reading. See the UNDECIDED markers below for the three field
    questions the sources do not settle.
    """

    __slots__ = ("_episode", "_branch", "_snapshot_digest", "_bias_version", "_call_id",
                 "_parent_call_id")

    #: The field names in the order they are printed and compared.
    FIELDS = ("episode", "branch", "snapshot_digest", "bias_version", "call_id",
              "parent_call_id")

    def __init__(
        self,
        *,
        episode=_UNSET,
        branch=_UNSET,
        snapshot_digest=_UNSET,
        bias_version=_UNSET,
        call_id=_UNSET,
        parent_call_id=_UNSET,
    ) -> None:
        object.__setattr__(self, "_episode", _text("episode", episode))
        object.__setattr__(self, "_branch", _text("branch", branch))
        # UNDECIDED IN SOURCES: does a child inherit the parent's snapshot digest or take its own -- the addendum binds the suspended caller's address to a snapshot (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:22) and says an updated live observation is a new source-bound view (line 36), and settles neither for a child.
        object.__setattr__(self, "_snapshot_digest",
                           _snapshot_digest("snapshot_digest", snapshot_digest))
        # UNDECIDED IN SOURCES: must a return address carry the recursion depth n -- Theorem 27.3 is stated depth-wise (Chapter_27_RPM_Structure.md:61) and the addendum's field list (lines 19-24) names no depth, so no depth field is carried here.
        object.__setattr__(self, "_bias_version", _bias_version("bias_version", bias_version))
        object.__setattr__(self, "_call_id", _text("call_id", call_id))
        object.__setattr__(self, "_parent_call_id", _parent_call_id(parent_call_id))

    # -- immutability ------------------------------------------------------ #
    def __setattr__(self, name, value):  # pragma: no cover - one line, always refuses
        raise AttributeError(
            "a ReturnAddress is immutable: an address that could be re-pointed after a "
            "suspension would be exactly the shortcut this build refuses"
        )

    # -- the fields -------------------------------------------------------- #
    @property
    def episode(self) -> str:
        return self._episode

    @property
    def branch(self) -> str:
        return self._branch

    @property
    def snapshot_digest(self) -> str:
        return self._snapshot_digest

    @property
    def bias_version(self) -> int:
        return self._bias_version

    @property
    def call_id(self) -> str:
        return self._call_id

    @property
    def parent_call_id(self):
        return self._parent_call_id

    @property
    def is_root(self) -> bool:
        """True when this address is the root call: the original goal/CJT itself."""
        return self._parent_call_id is None

    @property
    def is_return_path(self) -> bool:
        """True on every address, and False on every observation reference."""
        return True

    # -- comparison -------------------------------------------------------- #
    def key(self) -> tuple:
        """Every field, in order. The one comparison an exact match is made from."""
        return (self._episode, self._branch, self._snapshot_digest, self._bias_version,
                self._call_id, self._parent_call_id)

    def place(self) -> tuple:
        """Where the thread is, without which occurrence it is: episode, branch, snapshot.

        Two occurrences of one CJT share a place and not an address. The distinction is what
        stops a return from being delivered to the nearest same-named call.
        """
        return (self._episode, self._branch, self._snapshot_digest)

    def is_exact(self, other) -> bool:
        """True only when every field of ``other`` equals every field of this address.

        A partial match is not a match. An ``ObservationReference`` is never a match: it is
        not a return path at all.
        """
        return type(other) is ReturnAddress and self.key() == other.key()

    def differing_fields(self, other) -> tuple:
        """The names of the fields that differ from ``other``. Empty means exact."""
        if type(other) is not ReturnAddress:
            raise ReturnRefusal(
                NOT_A_RETURN_PATH,
                f"{type(other).__name__} is not a ReturnAddress, so no field of it can match "
                f"an address",
            )
        mine, theirs = self.key(), other.key()
        return tuple(name for name, a, b in zip(self.FIELDS, mine, theirs) if a != b)

    def require_exact(self, other) -> bool:
        """True when ``other`` is exact, or ``INEXACT_ADDRESS`` naming what differs."""
        differing = self.differing_fields(other)
        if differing:
            raise ReturnRefusal(
                INEXACT_ADDRESS,
                f"the address differs in {differing}. A partial match is not a match: this "
                f"build does not return to the nearest, the closest or the latest same-named "
                f"call",
            )
        return True

    # -- reading it out ---------------------------------------------------- #
    def as_dict(self) -> dict:
        """The six leaf values, for a log line or a receipt. No live object crosses."""
        return {
            "episode": self._episode,
            "branch": self._branch,
            "snapshot_digest": self._snapshot_digest,
            "bias_version": self._bias_version,
            "call_id": self._call_id,
            "parent_call_id": self._parent_call_id,
            "is_root": self.is_root,
            "is_return_path": True,
        }

    def __eq__(self, other) -> bool:
        return self.is_exact(other)

    def __ne__(self, other) -> bool:
        return not self.is_exact(other)

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        parent = self._parent_call_id if self._parent_call_id is not None else "ROOT"
        return (
            f"ReturnAddress(episode={self._episode!r}, branch={self._branch!r}, "
            f"snapshot={self._snapshot_digest[:12]}..., bias={self._bias_version}, "
            f"call={self._call_id!r}, parent={parent!r})"
        )


def exactness_report(first, second) -> dict:
    """A small owned dict saying whether two addresses are exact and what differs.

    Refuses ``NOT_A_RETURN_PATH`` when either side is not a ``ReturnAddress`` -- including
    when one side is an ``ObservationReference``, because a root reference is not a way back.
    """
    if type(first) is not ReturnAddress or type(second) is not ReturnAddress:
        raise ReturnRefusal(
            NOT_A_RETURN_PATH,
            "an exactness report is made between two ReturnAddresses, got "
            f"{type(first).__name__} and {type(second).__name__}",
        )
    differing = first.differing_fields(second)
    return {
        "exact": not differing,
        "differing_fields": differing,
        "first_call_id": first.call_id,
        "second_call_id": second.call_id,
    }


# --------------------------------------------------------------------------- #
# The child occurrence
# --------------------------------------------------------------------------- #
# UNDECIDED IN SOURCES: must a child thread stay on its parent's branch, or may a child open a new branch -- the addendum lists the caller's current branch (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:19) and never says whether a child inherits it, so child_of inherits the parent's branch unless the caller states a different one.
def child_of(parent_address, call_id, *, snapshot_digest=None, bias_version=None,
             branch=None) -> ReturnAddress:
    """The address of a child occurrence dispatched by ``parent_address``'s call.

    The child belongs to the parent's episode. It inherits the parent's branch, snapshot
    digest and Bias version unless the caller states its own; nothing is invented, and what
    was inherited is visible in the address that comes out.

    Two refusals of its own:

      * ``DUPLICATE_CALL_ID`` when the child is given the parent's own occurrence id -- one
        occurrence is one call, and a child that reuses its parent's id would make the
        return ambiguous by construction;
      * ``BAD_PARENT`` when the parent is not a ``ReturnAddress``.
    """
    if type(parent_address) is not ReturnAddress:
        raise ReturnRefusal(
            BAD_PARENT,
            f"a child address is made from a parent ReturnAddress, got "
            f"{type(parent_address).__name__}",
        )
    child_call_id = _text("call_id", call_id)
    if child_call_id == parent_address.call_id:
        raise ReturnRefusal(
            DUPLICATE_CALL_ID,
            f"the child occurrence id {child_call_id!r} is the parent's own. One call "
            f"occurrence is one occurrence: a child must get its own id or the return cannot "
            f"say which call it is coming back to",
        )
    return ReturnAddress(
        episode=parent_address.episode,
        branch=parent_address.branch if branch is None else branch,
        snapshot_digest=(parent_address.snapshot_digest
                         if snapshot_digest is None else snapshot_digest),
        bias_version=(parent_address.bias_version
                      if bias_version is None else bias_version),
        call_id=child_call_id,
        parent_call_id=parent_address.call_id,
    )


# --------------------------------------------------------------------------- #
# The root reference: for observation, never for returning
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ObservationReference:
    """A reference to the root call of an episode, kept to LOOK at, never to RETURN to.

    This type exists so that "keep a root reference throughout" and "no root shortcut" are
    not the same object. It has no ``call_id`` a return could be delivered on, its
    ``is_return_path`` is ``False``, and ``as_return_destination()`` refuses with
    ``NO_ROOT_SHORTCUT``. A caller that mixes the two up is refused, not quietly served.
    """

    episode: str
    root_call_id: str
    snapshot_digest: str
    taken_from_call_id: str

    #: Deliberately a class attribute and not a field: a root reference cannot be told to
    #: become a return path, not even by being rebuilt with a different value.
    is_return_path = False

    def as_return_destination(self):
        """Refuse. A root reference is an observation handle, not a way back."""
        raise ReturnRefusal(
            NO_ROOT_SHORTCUT,
            f"the root reference for episode {self.episode!r} (root call "
            f"{self.root_call_id!r}) is for observation only. A return goes to the immediate "
            f"waiting caller, which finishes its own remaining work first; skipping the levels "
            f"would mark intermediate prerequisites complete that nobody completed",
        )

    def as_dict(self) -> dict:
        return {
            "episode": self.episode,
            "root_call_id": self.root_call_id,
            "snapshot_digest": self.snapshot_digest,
            "taken_from_call_id": self.taken_from_call_id,
            "is_return_path": False,
        }

    def __repr__(self) -> str:
        return (
            f"ObservationReference(episode={self.episode!r}, "
            f"root_call_id={self.root_call_id!r}, observation only)"
        )


# UNDECIDED IN SOURCES: must the root observation reference be held for the whole episode or may it be dropped once the chain is entered -- the addendum says to retain a root reference to the original goal/CJT throughout (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:9) without saying when it may be released, so this build never releases it and never reads it as a return path.
def to_root(address, stack=None) -> ObservationReference:
    """The root observation reference of ``address``'s episode.

    With no ``stack``, this answers only when ``address`` IS the root call; otherwise it
    refuses ``ROOT_NOT_RESOLVABLE`` rather than guess which call is the root. With a
    ``ReturnStack``, the root is found by walking the recorded parent occurrences; a chain
    that does not reach the root refuses the same way.

    What comes back is an ``ObservationReference`` -- distinguishable from any return path by
    its type, by ``is_return_path``, and by refusing to be used as a destination.
    """
    if type(address) is not ReturnAddress:
        raise ReturnRefusal(
            NOT_A_RETURN_PATH,
            f"to_root() takes a ReturnAddress, got {type(address).__name__}",
        )
    if stack is None:
        if not address.is_root:
            raise ReturnRefusal(
                ROOT_NOT_RESOLVABLE,
                f"call {address.call_id!r} is not the root call and no stack was supplied to "
                f"walk its parents. The root is never guessed here, and never taken as "
                f"'the closest one'",
            )
        root = address
    else:
        root = stack.root_address_of(address)
    return ObservationReference(
        episode=root.episode,
        root_call_id=root.call_id,
        snapshot_digest=root.snapshot_digest,
        taken_from_call_id=address.call_id,
    )
