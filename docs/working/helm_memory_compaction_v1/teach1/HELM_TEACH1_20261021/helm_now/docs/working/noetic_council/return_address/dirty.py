"""dirty.py -- a dirty child invalidates the whole ancestor chain, and a clean sibling does not.

WHAT THIS MODULE DOES
---------------------
  * ``mark_dirty(stack, call_id, reason)`` records that one call occurrence resolved DIRTY.
    Canon gives the example and no classification procedure -- *"If a child chain at any level
    uses a 'dirty' resolution (e.g., a Power bypass), the retraction morphism fails"*
    [Chapter_27_RPM_Structure.md, line 63] -- so the reason is named by the caller and is
    never guessed here.
  * ``invalidate_ancestors(stack, call_id)`` then walks the parent links from that child all
    the way to the root and marks EVERY ancestor invalid: *"the block propagates back up the
    stack, and the entire parent chain is invalidated"* [same line]. The walk follows the
    recorded call occurrences one at a time; it does not stop at the first ancestor, and it
    does not consult an address's own opinion of who its grandparent is.
  * It answers with a ``DirtyReport`` naming, in order, the child, every invalidated
    ancestor up to the root, the ancestors that were already invalid, the siblings that are
    left valid, and everything else on the stack, which the dirty child did not touch.
  * The markings are live, in place, and have no undo: retraction in canon *"is destructive
    and cannot be safely undone"*. A thread marked invalid stays invalid, and ``stack.py``
    refuses to resume it (``THREAD_INVALIDATED``) or to let anything above it return
    (``ANCESTOR_INVALIDATED``).

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide that anything is dirty. There is no classifier, no heuristic and no
    score: the caller names the reason, in the same spirit as ``dwp_engine/retraction.py``.
  * It does NOT revalidate, repair, or restore. There is no un-dirty operation, no retry and
    no fallback. Canon makes the invalidation final at that level; the fix, if any, belongs to
    whoever runs the chain again from the root.
  * It does NOT invalidate siblings. Canon names *"the entire parent chain"*, which is the
    ancestor line, and this build follows ``dwp_engine/retraction.py``'s reading of the same
    gap. A dirty sibling does not condemn the parts of a coproduct that resolved cleanly.
  * It does NOT reach an ancestor that is not on the stack. A chain that does not reach the
    root is refused (``ANCESTOR_CHAIN_BROKEN``) rather than quietly stopped at the last
    recorded thread.
  * It does NOT run a circuit, a controller or a repair loop. It marks records and reports.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NO CIRCUIT USES THIS YET.
"""

from __future__ import annotations

from dataclasses import dataclass

from address import ReturnRefusal
from stack import ReturnStack

__all__ = [
    "DirtyMark",
    "DirtyReport",
    "mark_dirty",
    "invalidate_ancestors",
    "is_dirty",
    "is_invalid",
    "ancestor_calls",
    "MISSING_DIRTY_REASON",
    "ANCESTOR_CHAIN_BROKEN",
    "NOT_A_STACK",
    "CANON_DIRTY",
    "CANON_NO_UNDO",
]

CANON_DIRTY = (
    '"This ensures that a child chain cannot resolve a block by violating the architecture. If '
    'a child chain at any level uses a \'dirty\' resolution (e.g., a Power bypass), the '
    'retraction morphism fails, the block propagates back up the stack, and the entire parent '
    'chain is invalidated."  [Chapter_27_RPM_Structure.md, line 63]'
)

CANON_NO_UNDO = (
    '"Returning is forward progress with a result, not reversing time or undoing the child. '
    'Completed work stays charged."  [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 31]'
)

MISSING_DIRTY_REASON = "MISSING_DIRTY_REASON"
ANCESTOR_CHAIN_BROKEN = "ANCESTOR_CHAIN_BROKEN"
NOT_A_STACK = "NOT_A_STACK"


@dataclass(frozen=True)
class DirtyMark:
    """One recorded dirty resolution: which occurrence, why, and where it sits in the log."""

    call_id: str
    reason: str
    seq: int

    def as_dict(self) -> dict:
        return {"call_id": self.call_id, "reason": self.reason, "seq": self.seq}


@dataclass(frozen=True)
class DirtyReport:
    """What one dirty child did to the chain.

    ``invalidated``    the ancestors that were newly marked invalid, nearest first, ending at
                       the root when the chain reaches one.
    ``already_invalid`` ancestors that were invalid before this walk -- a second dirty child
                       under the same parent does not need to mark them again.
    ``siblings``       the dirty child's own siblings, whose ``invalid`` flag this walk left
                       alone.
    ``untouched``      every call occurrence the dirty child did not reach at all: neither the
                       child, nor an ancestor, nor one of its siblings.
    """

    dirty_child: str
    reason: str
    invalidated: tuple
    already_invalid: tuple
    root_call_id: str
    root_invalidated: bool
    siblings: tuple
    untouched: tuple

    def as_dict(self) -> dict:
        return {
            "dirty_child": self.dirty_child,
            "reason": self.reason,
            "invalidated": self.invalidated,
            "already_invalid": self.already_invalid,
            "root_call_id": self.root_call_id,
            "root_invalidated": self.root_invalidated,
            "siblings": self.siblings,
            "untouched": self.untouched,
        }

    def __str__(self) -> str:
        return (
            f"DirtyReport({self.dirty_child} dirty -> invalidated "
            f"{tuple(self.invalidated)}, root {self.root_call_id!r} invalidated="
            f"{self.root_invalidated}, siblings left valid {tuple(self.siblings)})"
        )


def _stack_or_refuse(stack) -> ReturnStack:
    if not isinstance(stack, ReturnStack):
        raise ReturnRefusal(
            NOT_A_STACK,
            f"a dirty marking is made on a ReturnStack, got {type(stack).__name__}",
        )
    return stack


# UNDECIDED IN SOURCES: is a thread marked dirty by canon's rule, a dirty resolution, the same marking as a thread invalidated by a dirty child -- canon uses invalidated for the parents and dirty for the child's own resolution (Chapter_27_RPM_Structure.md:63) and does not say the two words name one state, so this build keeps them as two flags (dirty for the resolution, invalid for the propagated chain).
def mark_dirty(stack, call_id, reason):
    """Record that one call occurrence's resolution came back dirty.

    The reason is required: canon names one example of a dirty resolution and publishes no
    classification procedure, so an unnamed judgement never enters the record. Refusals:
    ``MISSING_DIRTY_REASON``, ``NO_SUCH_THREAD``, ``ALREADY_DIRTY``.
    """
    _stack_or_refuse(stack)
    if not isinstance(reason, str) or not reason.strip():
        raise ReturnRefusal(
            MISSING_DIRTY_REASON,
            f"a dirty resolution is named with a reason, got {reason!r}. Canon names one "
            f"example (a Power bypass) and no classifier, so nothing is judged here",
        )
    thread = stack.thread_of(call_id)
    thread.mark_dirty(reason)
    entry = stack.record_event("DIRTY", call_id, note=reason)
    return DirtyMark(call_id=call_id, reason=reason, seq=entry["seq"])


def ancestor_calls(stack, call_id) -> tuple:
    """The recorded ancestor occurrences of one call, nearest first, ending at the root."""
    _stack_or_refuse(stack)
    thread = stack.thread_of(call_id)
    out, seen = [], {thread.call_id}
    while thread.address.parent_call_id is not None:
        parent_call_id = thread.address.parent_call_id
        if parent_call_id in seen:
            raise ReturnRefusal(
                ANCESTOR_CHAIN_BROKEN,
                f"the parent links cycle at {parent_call_id!r}; there is no root to reach",
            )
        seen.add(parent_call_id)
        try:
            thread = stack.thread_of(parent_call_id)
        except ReturnRefusal:
            raise ReturnRefusal(
                ANCESTOR_CHAIN_BROKEN,
                f"call occurrence {call_id!r} names parent {parent_call_id!r}, which is not on "
                f"this stack. Canon invalidates the ENTIRE parent chain, so a chain that does "
                f"not reach the root is refused rather than stopped early",
            ) from None
        out.append(thread.call_id)
    return tuple(out)


# UNDECIDED IN SOURCES: are the same-level siblings of a dirty child also invalidated -- canon names "the entire parent chain" only (Chapter_27_RPM_Structure.md:63) and says nothing about a coproduct's clean parts, so this build invalidates the ancestor line only and leaves siblings valid, the same reading dwp_engine/retraction.py records for the same gap.
def invalidate_ancestors(stack, call_id):
    """Mark every ancestor of the dirty child invalid, all the way to the root.

    Returns a ``DirtyReport``. Refusals: ``NO_SUCH_THREAD`` when the occurrence is not on the
    stack, ``ANCESTOR_CHAIN_BROKEN`` when the recorded chain does not reach a root.
    """
    _stack_or_refuse(stack)
    child = stack.thread_of(call_id)
    reason = child.dirty_reason or (
        f"a descendant resolution came back dirty at {call_id!r}; canon invalidates the entire "
        f"parent chain"
    )

    invalidated, already = [], []
    current = child
    for parent_call_id in ancestor_calls(stack, call_id):
        parent = stack.thread_of(parent_call_id)
        if parent.invalid:
            already.append(parent.call_id)
        else:
            parent.mark_invalid(
                f"invalidated because descendant {call_id!r} resolved dirty: {reason}"
            )
            stack.record_event("INVALIDATE", parent.call_id, note=reason)
            invalidated.append(parent.call_id)
        current = parent

    root = current
    root_invalidated = bool(root.invalid) or (root.call_id == child.call_id and root.dirty)

    siblings = tuple(
        thread.call_id
        for thread in stack.records()
        if thread.address.parent_call_id is not None
        and thread.address.parent_call_id == child.address.parent_call_id
        and thread.call_id != child.call_id
    )
    in_the_line = {child.call_id, *invalidated, *already}
    untouched = tuple(
        thread.call_id
        for thread in stack.records()
        if thread.call_id not in in_the_line and thread.call_id not in siblings
    )

    return DirtyReport(
        dirty_child=child.call_id,
        reason=reason,
        invalidated=tuple(invalidated),
        already_invalid=tuple(already),
        root_call_id=root.call_id,
        root_invalidated=root_invalidated,
        siblings=siblings,
        untouched=untouched,
    )


def is_dirty(stack, call_id) -> bool:
    """True when this occurrence's own resolution was marked dirty."""
    _stack_or_refuse(stack)
    return stack.thread_of(call_id).dirty


def is_invalid(stack, call_id) -> bool:
    """True when this occurrence was invalidated by a descendant's dirty resolution."""
    _stack_or_refuse(stack)
    return stack.thread_of(call_id).invalid
