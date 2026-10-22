"""stack.py -- the return stack: suspended threads, the exact return, and the caller's own work.

WHAT THIS MODULE DOES
---------------------
  * ``ReturnStack`` holds the suspended threads. Each thread records its exact
    ``ReturnAddress``, the Bias version at suspension, its call occurrence and its saved
    continuation. Suspending is how a caller waits; resuming is how a checked child result
    comes back to it.
  * ``suspend(address, bias_version, payload)`` puts one thread on the stack. It refuses a
    Bias version that disagrees with the address (``BIAS_ADDRESS_MISMATCH``), a second
    suspension of the same address (``THREAD_ALREADY_SUSPENDED``), one occurrence id used at
    two different places (``CALL_ID_REUSED``), and a payload that was not supplied
    (``MISSING_PAYLOAD``).
  * ``resume(address, returned_bias_version, payload)`` is the return. It refuses, each with
    its own word, and in this order:

        1. ``NOT_A_RETURN_PATH``        -- an ObservationReference is not a way back
        2. ``NO_SUCH_THREAD``           -- nothing was ever suspended here
           ``CALL_ID_MISMATCH``         -- a thread waits at this exact place under a
                                           DIFFERENT call occurrence: never substitute the
                                           nearest or latest same-named call
           ``INEXACT_ADDRESS``          -- that occurrence exists, another field differs
        3. ``THREAD_CANCELLED``         -- a cancelled thread never wakes
        4. ``THREAD_ALREADY_FINISHED``  -- a duplicate finish is not a second resume
        5. ``THREAD_INVALIDATED`` / ``ANCESTOR_INVALIDATED`` -- Theorem 27.3: a dirty child
                                           invalidates the whole ancestor chain, so an
                                           invalidated caller cannot accept a return
        6. ``MISSING_PAYLOAD``          -- a return carries a result, or it is not a return
        7. ``BIAS_EQUAL_NOT_NEWER``     -- strictly newer is required
           ``BIAS_OLDER_THAN_SUSPENDED``
        8. ``GLUE_VERDICT_NOT_FROM_REAL_MODEL`` / ``GLUE_BACK_REFUSED_BY_REAL_MODEL``
  * ``no_root_shortcut(address)`` returns the immediate waiting caller's address and refuses
    to jump to the root: the back-pointer is followed one link, and the root reference is an
    observation handle, not a destination.
  * ``remaining_work(address)`` reports the caller's own unfinished steps; a ``Resumption``
    will not return further until they are done, so "the caller completes its own remaining
    work before its result returns further" is enforced rather than described.
  * ``cancel`` and ``finish`` complete the small state machine (SUSPENDED -> FINISHED, or
    SUSPENDED -> CANCELLED). A consumed return token, a duplicate finish and a cancelled
    thread are three different refusals, not one.
  * ``receipt()`` is the ordered log of call/return edges and state events, each with its
    relation type, its source event and leaf values only.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide that a result is good. The child's result is checked by whatever
    checked it (the RPM gate, the caller's postcondition) before ``resume`` is called; this
    module checks that the return is the RIGHT return to the RIGHT caller, not that it is
    correct.
  * It does NOT glue the child back onto its parent. When a glue verdict is supplied it must
    be the real atlas model's own verdict, produced by ``atlas_binding.glue_back``; this
    module only refuses when that verdict says no. There is no glue rule here.
  * It does NOT decide the Bias. The versions are the caller's; this module only enforces
    that the one that comes back is strictly newer than the one that left.
  * It does NOT look anything up by proximity. There is no nearest, closest, latest,
    most-recent or same-name lookup in this file: a lookup is by exact occurrence id, and a
    failure to match is reported with what actually differs.
  * It does NOT restore or rewind. Returning is forward progress with a result: the child's
    work stays done and the finished thread stays finished. There is no un-resume.
  * It does NOT persist or journal. The addendum points at the runtime's existing
    transaction/journal path for that [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 28];
    this build is in memory and writes nothing.
  * It does NOT run a coordinator, a scheduler or a circuit. No recursion is running here.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NO CIRCUIT USES THIS YET.
"""

from __future__ import annotations

from dataclasses import dataclass

import atlas_binding
from address import (
    NOT_A_RETURN_PATH,
    NO_ROOT_SHORTCUT,
    ROOT_NOT_RESOLVABLE,
    ReturnAddress,
    ReturnRefusal,
)

__all__ = [
    "ReturnStack",
    "Thread",
    "ThreadState",
    "Resumption",
    "RemainingWork",
    "no_root_shortcut",
    "remaining_work",
    "SUSPENDED",
    "FINISHED",
    "CANCELLED",
    "CALL",
    "RETURN",
    "NO_SUCH_THREAD",
    "CALL_ID_MISMATCH",
    "CALL_ID_REUSED",
    "INEXACT_ADDRESS",
    "THREAD_ALREADY_SUSPENDED",
    "THREAD_ALREADY_FINISHED",
    "THREAD_ALREADY_CANCELLED",
    "THREAD_CANCELLED",
    "THREAD_INVALIDATED",
    "ANCESTOR_INVALIDATED",
    "BIAS_EQUAL_NOT_NEWER",
    "BIAS_OLDER_THAN_SUSPENDED",
    "BIAS_ADDRESS_MISMATCH",
    "MISSING_BIAS_VERSION",
    "BAD_BIAS_VERSION",
    "MISSING_PAYLOAD",
    "MISSING_REMAINING_WORK",
    "BAD_REMAINING_WORK",
    "BAD_CANCEL_REASON",
    "NO_WAITING_CALLER",
    "CALLER_NOT_WAITING",
    "ALREADY_AT_ROOT",
    "REMAINING_WORK_UNFINISHED",
    "NOT_NEXT_STEP",
    "NO_REMAINING_WORK",
    "GLUE_VERDICT_NOT_FROM_REAL_MODEL",
    "GLUE_BACK_REFUSED_BY_REAL_MODEL",
    "ALREADY_DIRTY",
    "ALREADY_INVALID",
    "OWNER_RETURN_RULE",
    "ADDENDUM_DUPLICATE_DELIVERY",
    "ADDENDUM_SAME_LOGICAL_CALLER",
]

# --------------------------------------------------------------------------- #
# Canon this module is written against, quoted verbatim
# --------------------------------------------------------------------------- #

OWNER_RETURN_RULE = (
    '"A successfully checked child result returns to its immediate waiting caller. That caller '
    'completes its own remaining work before its result returns further. Retain a root '
    'reference to the original goal/CJT throughout. A direct root shortcut must not mark '
    'intermediate prerequisites complete."  [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 9]'
)

ADDENDUM_DUPLICATE_DELIVERY = (
    '"On completion, verify the child\'s result and its episode, branch, occurrence and '
    'expected parent. Commit the accepted result/update and consume its return token through '
    'the existing coordinator. Duplicate delivery must not cause a second committed resume or '
    'a second application of the repair."  [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 29]'
)

ADDENDUM_SAME_LOGICAL_CALLER = (
    '"Resume the same logical caller at its saved next stage, carrying only qualified repair '
    'deltas and rechecking invalidated prerequisites. A legitimate repair may change Bias and '
    'current-state identity; do not require the old state hash to remain the live hash or '
    'restore the pre-repair Bias over the new one. Preserve the old hash as history."  '
    "[CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 30]"
)

# --------------------------------------------------------------------------- #
# Codes and words
# --------------------------------------------------------------------------- #

#: Thread states. Three, and a finished thread does not go back to waiting.
SUSPENDED = "SUSPENDED"
FINISHED = "FINISHED"
CANCELLED = "CANCELLED"

#: Edge relation types on the receipt. The addendum asks for both to be kept.
CALL = "CALL"
RETURN = "RETURN"

NO_SUCH_THREAD = "NO_SUCH_THREAD"
CALL_ID_MISMATCH = "CALL_ID_MISMATCH"
CALL_ID_REUSED = "CALL_ID_REUSED"
INEXACT_ADDRESS = "INEXACT_ADDRESS"
THREAD_ALREADY_SUSPENDED = "THREAD_ALREADY_SUSPENDED"
THREAD_ALREADY_FINISHED = "THREAD_ALREADY_FINISHED"
THREAD_ALREADY_CANCELLED = "THREAD_ALREADY_CANCELLED"
THREAD_CANCELLED = "THREAD_CANCELLED"
THREAD_INVALIDATED = "THREAD_INVALIDATED"
ANCESTOR_INVALIDATED = "ANCESTOR_INVALIDATED"
BIAS_EQUAL_NOT_NEWER = "BIAS_EQUAL_NOT_NEWER"
BIAS_OLDER_THAN_SUSPENDED = "BIAS_OLDER_THAN_SUSPENDED"
BIAS_ADDRESS_MISMATCH = "BIAS_ADDRESS_MISMATCH"
MISSING_BIAS_VERSION = "MISSING_BIAS_VERSION"
BAD_BIAS_VERSION = "BAD_BIAS_VERSION"
MISSING_PAYLOAD = "MISSING_PAYLOAD"
MISSING_REMAINING_WORK = "MISSING_REMAINING_WORK"
BAD_REMAINING_WORK = "BAD_REMAINING_WORK"
BAD_CANCEL_REASON = "BAD_CANCEL_REASON"
NO_WAITING_CALLER = "NO_WAITING_CALLER"
CALLER_NOT_WAITING = "CALLER_NOT_WAITING"
ALREADY_AT_ROOT = "ALREADY_AT_ROOT"
REMAINING_WORK_UNFINISHED = "REMAINING_WORK_UNFINISHED"
NOT_NEXT_STEP = "NOT_NEXT_STEP"
NO_REMAINING_WORK = "NO_REMAINING_WORK"
GLUE_VERDICT_NOT_FROM_REAL_MODEL = "GLUE_VERDICT_NOT_FROM_REAL_MODEL"
GLUE_BACK_REFUSED_BY_REAL_MODEL = "GLUE_BACK_REFUSED_BY_REAL_MODEL"
ALREADY_DIRTY = "ALREADY_DIRTY"
ALREADY_INVALID = "ALREADY_INVALID"

#: The sentinel for "this argument was not supplied at all".
_UNSET = object()


def _whole_number(name: str, value) -> int:
    """A Bias version as a whole number >= 0, or the refusal that says which is wrong."""
    if value is _UNSET:
        raise ReturnRefusal(
            MISSING_BIAS_VERSION,
            f"{name} was not supplied. The Bias version is part of the comparison that decides "
            f"whether a return may wake this caller, so it is never defaulted",
        )
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReturnRefusal(
            BAD_BIAS_VERSION, f"{name} must be a whole number, got {type(value).__name__}"
        )
    if value < 0:
        raise ReturnRefusal(BAD_BIAS_VERSION, f"{name} must be >= 0, got {value}")
    return value


def _work_items(value) -> tuple:
    """A caller's remaining work: a sequence of named, non-blank steps."""
    if value is _UNSET:
        raise ReturnRefusal(
            MISSING_REMAINING_WORK,
            "remaining_work was not supplied. A caller that has nothing left to do says so "
            "with an empty sequence; it is never assumed",
        )
    if isinstance(value, str) or not isinstance(value, (tuple, list)):
        raise ReturnRefusal(
            BAD_REMAINING_WORK,
            f"remaining_work must be a tuple or list of step names, got "
            f"{type(value).__name__}",
        )
    steps = []
    for step in value:
        if not isinstance(step, str) or not step.strip():
            raise ReturnRefusal(
                BAD_REMAINING_WORK, f"a remaining-work step {step!r} is not a non-blank string"
            )
        steps.append(step)
    return tuple(steps)


# --------------------------------------------------------------------------- #
# The thread record
# --------------------------------------------------------------------------- #
class Thread:
    """One suspended thread: its address, its Bias, its saved continuation, its own work.

    The record is the stack's storage. It is handed out read-only in spirit: ``dirty.py`` is
    the only module that sets ``dirty``/``invalid``, and the stack is the only module that
    moves ``status``. Transitions are refused rather than overwritten, so a cancelled thread
    cannot become a waiting one again.
    """

    __slots__ = (
        "address", "bias_version", "payload", "remaining_work", "finished_work", "status",
        "dirty", "dirty_reason", "invalid", "invalid_reason", "returned_bias_version",
        "returned_payload", "glue", "suspend_seq", "resume_seq", "cancel_reason",
    )

    def __init__(self, address, bias_version, payload, remaining_work, suspend_seq):
        self.address = address
        self.bias_version = bias_version
        self.payload = payload
        self.remaining_work = list(remaining_work)
        self.finished_work = []
        self.status = SUSPENDED
        self.dirty = False
        self.dirty_reason = None
        self.invalid = False
        self.invalid_reason = None
        self.returned_bias_version = None
        self.returned_payload = None
        self.glue = None
        self.suspend_seq = suspend_seq
        self.resume_seq = None
        self.cancel_reason = None

    # -- readings ---------------------------------------------------------- #
    @property
    def call_id(self) -> str:
        return self.address.call_id

    @property
    def parent_call_id(self):
        return self.address.parent_call_id

    @property
    def is_waiting(self) -> bool:
        return self.status == SUSPENDED

    @property
    def is_finished(self) -> bool:
        return self.status == FINISHED

    @property
    def is_cancelled(self) -> bool:
        return self.status == CANCELLED

    @property
    def is_invalid(self) -> bool:
        return self.invalid

    @property
    def is_dirty(self) -> bool:
        return self.dirty

    @property
    def remaining(self) -> tuple:
        return tuple(self.remaining_work)

    @property
    def may_return_further(self) -> bool:
        return not self.remaining_work

    # -- the state machine, in one place ----------------------------------- #
    def mark_finished(self, returned_bias_version, payload, glue, resume_seq):
        if self.status is CANCELLED:
            raise ReturnRefusal(
                THREAD_CANCELLED,
                f"call {self.call_id!r} was cancelled and cannot be finished; cancelled work "
                f"never wakes and never completes",
            )
        if self.status is FINISHED:
            raise ReturnRefusal(
                THREAD_ALREADY_FINISHED,
                f"call {self.call_id!r} already finished at receipt step {self.resume_seq}. A "
                f"duplicate delivery must not cause a second committed resume",
            )
        self.status = FINISHED
        self.returned_bias_version = returned_bias_version
        self.returned_payload = payload
        self.glue = glue
        self.resume_seq = resume_seq

    def mark_cancelled(self, reason, seq):
        if self.status is FINISHED:
            raise ReturnRefusal(
                THREAD_ALREADY_FINISHED,
                f"call {self.call_id!r} already finished at receipt step {self.resume_seq}; "
                f"completed work stays charged and is never refunded by a late cancel",
            )
        if self.status is CANCELLED:
            raise ReturnRefusal(
                THREAD_ALREADY_CANCELLED, f"call {self.call_id!r} was already cancelled"
            )
        self.status = CANCELLED
        self.resume_seq = seq
        self.cancel_reason = reason

    # -- the dirty markings, set by dirty.py ------------------------------- #
    def mark_dirty(self, reason):
        if self.dirty:
            raise ReturnRefusal(
                ALREADY_DIRTY,
                f"call {self.call_id!r} is already marked dirty ({self.dirty_reason!r}); the "
                f"first reason is the record and it is not overwritten",
            )
        self.dirty = True
        self.dirty_reason = reason

    def mark_invalid(self, reason):
        if self.invalid:
            raise ReturnRefusal(
                ALREADY_INVALID,
                f"call {self.call_id!r} is already invalidated ({self.invalid_reason!r})",
            )
        self.invalid = True
        self.invalid_reason = reason

    # -- a frozen copy for a reader ---------------------------------------- #
    def as_state(self) -> "ThreadState":
        return ThreadState(
            call_id=self.call_id,
            address=self.address,
            bias_version=self.bias_version,
            status=self.status,
            remaining_work=tuple(self.remaining_work),
            finished_work=tuple(self.finished_work),
            returned_bias_version=self.returned_bias_version,
            dirty=self.dirty,
            dirty_reason=self.dirty_reason,
            invalid=self.invalid,
            invalid_reason=self.invalid_reason,
            payload=self.payload,
            returned_payload=self.returned_payload,
            glue_ok=None if self.glue is None else self.glue.ok,
        )

    def __repr__(self) -> str:
        return (
            f"Thread(call={self.call_id!r}, status={self.status}, "
            f"bias={self.bias_version}, parent={self.parent_call_id!r}, "
            f"remaining={len(self.remaining_work)})"
        )


@dataclass(frozen=True)
class ThreadState:
    """A frozen snapshot of one thread, for a receipt, a report or a test.

    ``payload`` is the caller's own saved continuation, returned as it was handed in; this
    build neither reads nor rewrites it.
    """

    call_id: str
    address: ReturnAddress
    bias_version: int
    status: str
    remaining_work: tuple
    finished_work: tuple
    returned_bias_version: int | None
    dirty: bool
    dirty_reason: str | None
    invalid: bool
    invalid_reason: str | None
    payload: object = None
    returned_payload: object = None
    glue_ok: bool | None = None
    @property
    def may_return_further(self) -> bool:
        return not self.remaining_work

    def as_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "address": self.address.as_dict(),
            "bias_version": self.bias_version,
            "status": self.status,
            "remaining_work": self.remaining_work,
            "finished_work": self.finished_work,
            "returned_bias_version": self.returned_bias_version,
            "dirty": self.dirty,
            "dirty_reason": self.dirty_reason,
            "invalid": self.invalid,
            "invalid_reason": self.invalid_reason,
            "may_return_further": self.may_return_further,
            "returned_payload": self.returned_payload,
            "glue_ok": self.glue_ok,
        }


# --------------------------------------------------------------------------- #
# The small reports the two named readers answer with
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RemainingWork:
    """What a caller still owes before its result may return further."""

    call_id: str
    remaining: tuple
    finished: tuple
    may_return_further: bool

    def as_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "remaining": self.remaining,
            "finished": self.finished,
            "may_return_further": self.may_return_further,
        }


class Resumption:
    """One accepted return: the caller is awake, and it owes its own work before going up.

    ``return_further()`` is the only way back up, and it refuses while any of the caller's
    own steps is undone (``REMAINING_WORK_UNFINISHED``), refuses a root jump
    (``NO_ROOT_SHORTCUT``), and otherwise returns the immediate waiting caller's address --
    one link, never the root.
    """

    __slots__ = ("_stack", "_thread", "payload", "returned_bias_version")

    def __init__(self, stack, thread, payload, returned_bias_version):
        self._stack = stack
        self._thread = thread
        self.payload = payload
        self.returned_bias_version = returned_bias_version

    # -- readings ---------------------------------------------------------- #
    @property
    def address(self) -> ReturnAddress:
        """The address of the caller that has just been resumed."""
        return self._thread.address

    @property
    def call_id(self) -> str:
        return self._thread.call_id

    @property
    def remaining_work(self) -> tuple:
        return tuple(self._thread.remaining_work)

    @property
    def finished_work(self) -> tuple:
        return tuple(self._thread.finished_work)

    @property
    def may_return_further(self) -> bool:
        return not self._thread.remaining_work

    @property
    def resumption_stage(self) -> str:
        """The next stage this caller resumes at: its first undone step, or its return."""
        if self._thread.remaining_work:
            return f"{self._thread.call_id}:{self._thread.remaining_work[0]}"
        return f"{self._thread.call_id}:return"

    @property
    def caller_address(self):
        """The immediate waiting caller's address, or ``None`` when there is none to show."""
        parent_call_id = self._thread.address.parent_call_id
        if parent_call_id is None:
            return None
        try:
            return self._stack.thread_of(parent_call_id).address
        except ReturnRefusal:
            return None

    # -- the caller's own work --------------------------------------------- #
    def complete_next_step(self, step=None) -> str:
        """Mark the next undone step done, and answer which one it was.

        With ``step`` given, it must be the next undone step; taking a later one first is
        refused as ``NOT_NEXT_STEP``, because a caller that skips its own work is the shortcut
        the rule forbids one level up.
        """
        if not self._thread.remaining_work:
            raise ReturnRefusal(
                NO_REMAINING_WORK,
                f"call {self._thread.call_id!r} has no remaining work; its result may return "
                f"further now",
            )
        head = self._thread.remaining_work[0]
        if step is not None and step != head:
            raise ReturnRefusal(
                NOT_NEXT_STEP,
                f"the next step for call {self._thread.call_id!r} is {head!r}, not {step!r}",
            )
        self._thread.remaining_work.pop(0)
        self._thread.finished_work.append(head)
        return head

    def finish_all_remaining_work(self) -> tuple:
        """Mark every remaining step done, in order. Answers the steps, in that order."""
        done = []
        while self._thread.remaining_work:
            done.append(self.complete_next_step())
        return tuple(done)

    # -- the way up -------------------------------------------------------- #
    def return_further(self, *, to_root=False) -> ReturnAddress:
        """Return this caller's own result to its immediate waiting caller.

        Refuses, in this order: ``REMAINING_WORK_UNFINISHED`` while any step is undone,
        ``THREAD_INVALIDATED`` / ``ANCESTOR_INVALIDATED`` when the chain is invalid, and
        ``NO_ROOT_SHORTCUT`` when asked for the root. What it returns is one address: the
        caller one level up.
        """
        if self._thread.remaining_work:
            raise ReturnRefusal(
                REMAINING_WORK_UNFINISHED,
                f"call {self._thread.call_id!r} still owes {tuple(self._thread.remaining_work)}. "
                f"A caller finishes its own remaining work before its result returns further",
            )
        if self._thread.invalid:
            raise ReturnRefusal(
                THREAD_INVALIDATED,
                f"call {self._thread.call_id!r} was invalidated: {self._thread.invalid_reason}",
            )
        if self._stack.ancestors_invalid(self._thread.address):
            raise ReturnRefusal(
                ANCESTOR_INVALIDATED,
                f"an ancestor of call {self._thread.call_id!r} is invalid; Theorem 27.3: a "
                f"dirty child invalidates the whole parent chain",
            )
        destination = self._stack.no_root_shortcut(self._thread.address, to_root=to_root)
        self._stack._record(
            event="RETURN_FURTHER",
            relation=RETURN,
            thread=self._thread,
            note=f"finished its own work: {tuple(self._thread.finished_work)}",
        )
        return destination

    def as_dict(self) -> dict:
        return {
            "call_id": self._thread.call_id,
            "address": self._thread.address.as_dict(),
            "returned_bias_version": self.returned_bias_version,
            "remaining_work": tuple(self._thread.remaining_work),
            "finished_work": tuple(self._thread.finished_work),
            "may_return_further": self.may_return_further,
            "resumption_stage": self.resumption_stage,
            "caller_call_id": None
            if self._thread.address.parent_call_id is None
            else self._thread.address.parent_call_id,
            "payload": self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"Resumption(call={self._thread.call_id!r}, "
            f"remaining={len(self._thread.remaining_work)}, "
            f"bias={self.returned_bias_version})"
        )


# --------------------------------------------------------------------------- #
# The stack
# --------------------------------------------------------------------------- #
class ReturnStack:
    """The suspended threads, the return path, and the refusals that guard it.

    Nothing here searches for a near match. A lookup is by exact call occurrence; when that
    occurrence is absent, the answer says what is actually there instead -- another
    occurrence at the same place (``CALL_ID_MISMATCH``), the same occurrence with a different
    field (``INEXACT_ADDRESS``), or nothing (``NO_SUCH_THREAD``).
    """

    def __init__(self) -> None:
        self._by_call = {}     # call_id -> Thread. One occurrence id, one place.
        self._order = []       # Threads in suspension order.
        self._receipt = []     # Small owned dicts, in order.

    # -- the receipt ------------------------------------------------------- #
    def _record(self, event, relation, thread, note=""):
        entry = {
            "seq": len(self._receipt) + 1,
            "event": event,
            "relation": relation,
            "call_id": thread.call_id,
            "parent_call_id": thread.address.parent_call_id,
            "episode": thread.address.episode,
            "branch": thread.address.branch,
            "snapshot_digest": thread.address.snapshot_digest,
            "bias_version": thread.bias_version,
            "note": note,
        }
        self._receipt.append(entry)
        return entry

    def receipt(self) -> list:
        """The ordered call/return edges and state events. Copies, never live records."""
        return [dict(entry) for entry in self._receipt]

    def record_event(self, event, call_id, note="", relation="NONE"):
        """Append one state event for a named call occurrence to the receipt.

        Used by ``dirty.py`` so the dirty and invalid markings appear in the same ordered log
        as the calls and the returns.
        """
        thread = self.thread_of(call_id)
        return self._record(event=event, relation=relation, thread=thread, note=note)

    def edges(self) -> list:
        """Only the entries that are edges: a CALL or a RETURN, each with its event."""
        return [dict(entry) for entry in self._receipt
                if entry["relation"] in (CALL, RETURN)]

    # -- readings ---------------------------------------------------------- #
    def records(self) -> tuple:
        """The live thread records, in suspension order. For ``dirty.py`` and for reading."""
        return tuple(self._order)

    def threads(self) -> tuple:
        """Frozen copies of every thread, in suspension order."""
        return tuple(thread.as_state() for thread in self._order)

    def waiting_callers(self) -> tuple:
        """Frozen copies of the threads that are still waiting."""
        return tuple(thread.as_state() for thread in self._order if thread.is_waiting)

    def thread_of(self, call_id) -> Thread:
        """The live record for one call occurrence, or ``NO_SUCH_THREAD``."""
        if not isinstance(call_id, str) or not call_id.strip():
            raise ReturnRefusal(
                NO_SUCH_THREAD, f"{call_id!r} is not a call occurrence id at all"
            )
        thread = self._by_call.get(call_id)
        if thread is None:
            raise ReturnRefusal(
                NO_SUCH_THREAD,
                f"no thread was ever suspended under call occurrence {call_id!r}; the "
                f"occurrences on this stack are {tuple(sorted(self._by_call))}",
            )
        return thread

    def state_of(self, address) -> ThreadState:
        """A frozen copy of the thread this address names, by exact lookup."""
        return self._lookup(address).as_state()

    # -- the exact lookup -------------------------------------------------- #
    def _lookup(self, address, what="resume"):
        """Find the ONE thread this address names, or refuse with what is actually there."""
        if type(address) is not ReturnAddress:
            raise ReturnRefusal(
                NOT_A_RETURN_PATH,
                f"{what}() takes a ReturnAddress, got {type(address).__name__}. An "
                f"ObservationReference is a root handle for looking, not a way back",
            )
        thread = self._by_call.get(address.call_id)
        if thread is not None:
            differing = thread.address.differing_fields(address)
            if not differing:
                return thread
            raise ReturnRefusal(
                INEXACT_ADDRESS,
                f"call occurrence {address.call_id!r} was suspended at a different address: "
                f"{differing} differ. A partial match is not a match",
            )
        for other in self._order:
            if other.address.place() == address.place():
                raise ReturnRefusal(
                    CALL_ID_MISMATCH,
                    f"a thread does wait at this exact place, but under call occurrence "
                    f"{other.call_id!r}, not {address.call_id!r}. One CJT can be invoked more "
                    f"than once and the nearest or latest same-named call is never substituted",
                )
        raise ReturnRefusal(
            NO_SUCH_THREAD,
            f"no thread was ever suspended for call occurrence {address.call_id!r}",
        )

    # -- suspend ----------------------------------------------------------- #
    def suspend(self, address, bias_version=_UNSET, payload=_UNSET, *, remaining_work=_UNSET):
        """Put a caller on the stack: it is now waiting for the child it dispatched.

        Refusals: ``NOT_A_RETURN_PATH``, ``MISSING_BIAS_VERSION`` / ``BAD_BIAS_VERSION``,
        ``BIAS_ADDRESS_MISMATCH`` when the version handed in is not the one the address names,
        ``CALL_ID_REUSED`` when an occurrence id is already on the stack at another place,
        ``THREAD_ALREADY_SUSPENDED`` / ``THREAD_ALREADY_FINISHED``, ``MISSING_PAYLOAD``,
        ``MISSING_REMAINING_WORK`` / ``BAD_REMAINING_WORK``.
        """
        if type(address) is not ReturnAddress:
            raise ReturnRefusal(
                NOT_A_RETURN_PATH,
                f"suspend() takes a ReturnAddress, got {type(address).__name__}",
            )
        version = _whole_number("bias_version", bias_version)
        if version != address.bias_version:
            raise ReturnRefusal(
                BIAS_ADDRESS_MISMATCH,
                f"the address names Bias version {address.bias_version} and {version} was "
                f"suspended. Two versions for one suspension is a mix-up, not a detail",
            )
        if payload is _UNSET:
            raise ReturnRefusal(
                MISSING_PAYLOAD,
                "payload was not supplied. A suspension saves the caller's continuation; an "
                "empty one is stated as None, never assumed",
            )
        work = _work_items(remaining_work)

        existing = self._by_call.get(address.call_id)
        if existing is not None:
            if existing.address.differing_fields(address):
                raise ReturnRefusal(
                    CALL_ID_REUSED,
                    f"call occurrence {address.call_id!r} is already on this stack at "
                    f"{existing.address.place()}; one occurrence id names one place, so it "
                    f"cannot name a second",
                )
            if existing.is_finished:
                raise ReturnRefusal(
                    THREAD_ALREADY_FINISHED,
                    f"call occurrence {address.call_id!r} already finished at receipt step "
                    f"{existing.resume_seq}; a finished occurrence is not re-suspended",
                )
            raise ReturnRefusal(
                THREAD_ALREADY_SUSPENDED,
                f"call occurrence {address.call_id!r} is already suspended and waiting",
            )

        thread = Thread(address, version, payload, work, suspend_seq=len(self._receipt) + 1)
        self._by_call[address.call_id] = thread
        self._order.append(thread)
        self._record(event="SUSPEND", relation=CALL, thread=thread,
                     note=f"waiting on {len(work)} own step(s)")
        return thread.as_state()

    # -- resume: the return ------------------------------------------------ #
    def resume(self, address, returned_bias_version=_UNSET, payload=_UNSET, *, glue=None):
        """Accept a checked child result for the caller this address names.

        The checks, in the order the module docstring lists them, with one word each. What
        comes back is a ``Resumption``: the caller is awake and owes its own work.
        """
        thread = self._lookup(address, "resume")

        if thread.is_cancelled:
            raise ReturnRefusal(
                THREAD_CANCELLED,
                f"call occurrence {thread.call_id!r} was cancelled; a cancelled thread cannot "
                f"be resumed and a cancelled result wakes nobody",
            )
        if thread.is_finished:
            raise ReturnRefusal(
                THREAD_ALREADY_FINISHED,
                f"call occurrence {thread.call_id!r} already finished at receipt step "
                f"{thread.resume_seq}; its return token is consumed, so a duplicate finish may "
                f"not cause a second resume",
            )
        if thread.invalid:
            raise ReturnRefusal(
                THREAD_INVALIDATED,
                f"call occurrence {thread.call_id!r} was invalidated: {thread.invalid_reason}",
            )
        if self.ancestors_invalid(thread.address):
            raise ReturnRefusal(
                ANCESTOR_INVALIDATED,
                f"an ancestor of call occurrence {thread.call_id!r} is invalid; Theorem 27.3: "
                f"the block propagates back up and the entire parent chain is invalidated",
            )
        if payload is _UNSET:
            raise ReturnRefusal(
                MISSING_PAYLOAD,
                "payload was not supplied. A return carries the child's checked result; a "
                "return with nothing in it is not a return",
            )
        version = _whole_number("returned_bias_version", returned_bias_version)
        if version == thread.bias_version:
            raise ReturnRefusal(
                BIAS_EQUAL_NOT_NEWER,
                f"the returned Bias version {version} is the one that was suspended. A returned "
                f"thread must carry a strictly newer Bias: an equal version means nothing "
                f"changed, so there is nothing new to wake the caller with",
            )
        if version < thread.bias_version:
            raise ReturnRefusal(
                BIAS_OLDER_THAN_SUSPENDED,
                f"the returned Bias version {version} is older than the suspended "
                f"{thread.bias_version}. A stale finish may not wake a caller that has moved "
                f"on; the pre-repair Bias is history, not the live one",
            )

        # The glue-back verdict, when one is supplied, is the real atlas model's verdict.
        if glue is not None:
            if type(glue) is not atlas_binding.GlueBack:
                raise ReturnRefusal(
                    GLUE_VERDICT_NOT_FROM_REAL_MODEL,
                    f"a glue verdict must be the record atlas_binding.glue_back returns, got "
                    f"{type(glue).__name__}. This build holds no glue rule, so a hand-made "
                    f"verdict has nothing behind it",
                )
            if not glue.ok:
                raise ReturnRefusal(
                    GLUE_BACK_REFUSED_BY_REAL_MODEL,
                    f"the real atlas model did not glue the child back: compatible="
                    f"{glue.compatible}, certificate={glue.certificate_id!r}, conflicting field"
                    f"s={glue.conflicting_fields!r}. The return is refused, and no rule of "
                    f"this build overrides the real model",
                )

        thread.mark_finished(version, payload, glue, resume_seq=len(self._receipt) + 1)
        self._record(
            event="RESUME",
            relation=RETURN,
            thread=thread,
            note=(f"bias {thread.bias_version} -> {version}; "
                  f"{len(thread.remaining_work)} own step(s) before returning further"),
        )
        return Resumption(self, thread, payload, version)

    # -- finish and cancel ------------------------------------------------- #
    def finish(self, address):
        """Record a completion nobody took: the thread is finished, and stays that way."""
        thread = self._lookup(address, "finish")
        if thread.is_cancelled:
            raise ReturnRefusal(
                THREAD_CANCELLED,
                f"call occurrence {thread.call_id!r} was cancelled; cancelled work does not "
                f"finish",
            )
        thread.mark_finished(None, None, None, resume_seq=len(self._receipt) + 1)
        self._record(event="FINISH", relation="NONE", thread=thread,
                     note="finished without a resume")
        return thread.as_state()

    def cancel(self, address, reason=_UNSET):
        """Cancel a waiting thread. A cancelled thread cannot be resumed, ever.

        A finished thread cannot be cancelled: "Rollback or canceled work never refunds
        execution already performed." [addendum, line 31]
        """
        thread = self._lookup(address, "cancel")
        if reason is _UNSET or not isinstance(reason, str) or not reason.strip():
            raise ReturnRefusal(
                BAD_CANCEL_REASON,
                f"a cancellation is stated with a reason, got {reason!r}. An unnamed cancel "
                f"cannot be told apart from a mistake",
            )
        thread.mark_cancelled(reason, seq=len(self._receipt) + 1)
        self._record(event="CANCEL", relation="NONE", thread=thread, note=reason)
        return thread.as_state()

    # -- the ancestor chain ------------------------------------------------ #
    def chain_of(self, address) -> tuple:
        """(this address, its parent's, ..., the root's), or a refusal if the chain breaks."""
        current = self._lookup(address, "chain_of")
        chain = [current.address]
        seen = {current.call_id}
        while current.address.parent_call_id is not None:
            parent_call_id = current.address.parent_call_id
            if parent_call_id in seen:
                raise ReturnRefusal(
                    ROOT_NOT_RESOLVABLE,
                    f"the recorded parent links cycle at {parent_call_id!r}; there is no root "
                    f"to walk to and none is assumed",
                )
            seen.add(parent_call_id)
            parent = self._by_call.get(parent_call_id)
            if parent is None:
                raise ReturnRefusal(
                    ROOT_NOT_RESOLVABLE,
                    f"call occurrence {current.call_id!r} names parent {parent_call_id!r}, "
                    f"which is not on this stack. The chain does not reach the root, and the "
                    f"root is never guessed",
                )
            current = parent
            chain.append(current.address)
        return tuple(chain)

    def root_address_of(self, address) -> ReturnAddress:
        """The root call's address of this address's episode, by walking parent links."""
        return self.chain_of(address)[-1]

    def ancestors_invalid(self, address) -> bool:
        """True when any RECORDED ancestor above this address is invalid."""
        parent_call_id = address.parent_call_id
        seen = set()
        while parent_call_id is not None and parent_call_id not in seen:
            seen.add(parent_call_id)
            parent = self._by_call.get(parent_call_id)
            if parent is None:
                return False
            if parent.invalid:
                return True
            parent_call_id = parent.address.parent_call_id
        return False

    # -- the one step up --------------------------------------------------- #
    def no_root_shortcut(self, address, *, to_root=False) -> ReturnAddress:
        """The immediate waiting caller's address. Never the root; never a skip.

        Refuses ``NO_ROOT_SHORTCUT`` when the root is asked for, ``ALREADY_AT_ROOT`` when the
        address is the root call, ``NO_WAITING_CALLER`` when no caller above it is on the
        stack, and ``CALLER_NOT_WAITING`` when the caller is there but not waiting (cancelled
        or finished).
        """
        thread = self._lookup(address, "no_root_shortcut")
        if to_root:
            raise ReturnRefusal(
                NO_ROOT_SHORTCUT,
                f"the return from call occurrence {thread.call_id!r} is asked to jump to the "
                f"root. It goes to the immediate waiting caller, which finishes its own "
                f"remaining work first: a direct root shortcut must not mark intermediate "
                f"prerequisites complete",
            )
        if thread.address.parent_call_id is None:
            raise ReturnRefusal(
                ALREADY_AT_ROOT,
                f"call occurrence {thread.call_id!r} is the root call; there is no caller "
                f"above it to return to",
            )
        parent = self._by_call.get(thread.address.parent_call_id)
        if parent is None:
            raise ReturnRefusal(
                NO_WAITING_CALLER,
                f"call occurrence {thread.call_id!r} names parent "
                f"{thread.address.parent_call_id!r}, which is not on this stack; no caller is "
                f"waiting there and none is substituted",
            )
        if not parent.is_waiting:
            raise ReturnRefusal(
                CALLER_NOT_WAITING,
                f"the caller of {thread.call_id!r} is {parent.status}, not waiting; a named "
                f"stale/cancelled outcome is the answer, never a substitute caller",
            )
        return parent.address

    def remaining_work(self, address) -> RemainingWork:
        """What the caller at this address still owes before its result returns further."""
        thread = self._lookup(address, "remaining_work")
        return RemainingWork(
            call_id=thread.call_id,
            remaining=tuple(thread.remaining_work),
            finished=tuple(thread.finished_work),
            may_return_further=thread.may_return_further,
        )

    # -- the dirty markings arrive from dirty.py --------------------------- #
    def mark_dirty(self, call_id, reason):
        """The brief's ``mark_dirty(call_id, reason)``: the record lives on this stack."""
        import dirty

        return dirty.mark_dirty(self, call_id, reason)

    def invalidate_ancestors(self, call_id):
        """The brief's ``invalidate_ancestors(stack, call_id)``, as a method."""
        import dirty

        return dirty.invalidate_ancestors(self, call_id)

    def __repr__(self) -> str:
        waiting = sum(1 for thread in self._order if thread.is_waiting)
        return (
            f"ReturnStack({len(self._order)} thread(s), {waiting} waiting, "
            f"{len(self._receipt)} receipt step(s))"
        )


# --------------------------------------------------------------------------- #
# The two named readers, as plain module functions
# --------------------------------------------------------------------------- #
def no_root_shortcut(stack, address, *, to_root=False):
    """``stack.no_root_shortcut(address)``: the immediate waiting caller's address."""
    if not isinstance(stack, ReturnStack):
        raise ReturnRefusal(
            NOT_A_RETURN_PATH,
            f"no_root_shortcut() takes a ReturnStack first, got {type(stack).__name__}",
        )
    return stack.no_root_shortcut(address, to_root=to_root)


def remaining_work(stack, address):
    """``stack.remaining_work(address)``: the caller's own unfinished steps."""
    if not isinstance(stack, ReturnStack):
        raise ReturnRefusal(
            NOT_A_RETURN_PATH,
            f"remaining_work() takes a ReturnStack first, got {type(stack).__name__}",
        )
    return stack.remaining_work(address)


# UNDECIDED IN SOURCES: must a returned Bias be newer by exactly one version or merely greater -- the addendum says a legitimate repair may change Bias (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:30) and the owning brief says strictly newer, and neither fixes the step size, so any strictly greater version is accepted here.
# UNDECIDED IN SOURCES: may a caller invalidated by a dirty child be resumed at all, or must it be revalidated from the root first -- the addendum names a stale or canceled outcome and an explicit revalidation (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:32) but never names an ancestor invalidated by a dirty child (Chapter_27_RPM_Structure.md:63), so this build refuses the return with ANCESTOR_INVALIDATED and performs no revalidation of its own.
# UNDECIDED IN SOURCES: may a resume proceed with no glue-back verdict when no atlas nodes are supplied -- the addendum requires the child's result and its expected parent to be verified (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:29) and the owning brief makes glue-back the real model's decision, but the resume signature carries no nodes, so glue is an optional real-model verdict and its absence is recorded as no verdict rather than as success.
# UNDECIDED IN SOURCES: must one accepted result wake only one waiting caller, or may it notify several compatible callers -- the addendum allows one qualified result to notify multiple compatible waiting callers and also defers general fan-out beyond the first nested demo (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:33), so this build is one thread per call occurrence and does not fan out.
# UNDECIDED IN SOURCES: what a caller's remaining work IS and how a step counts as done -- the addendum says the caller completes its own remaining work before its result returns further (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:9) and names no work items and no completion procedure, so the steps are named by the caller and marked done in the order they were given.
# UNDECIDED IN SOURCES: is a duplicate finish refused because the return token was consumed or because the thread is finished -- the addendum forbids a second committed resume (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:29) and names neither mechanism, so this build models one finish per call occurrence and reports both cases with THREAD_ALREADY_FINISHED.
