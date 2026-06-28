"""Conversational move types and admissibility relations for the DST.

This module is the *grammar* layer of the Phase 2 Dialogue State Tracker.
It defines:

  1. The 11 ``TurnType`` values that a turn can take.
  2. The admissibility graph: which next-turn types are valid after a
     given previous turn type.
  3. CAS-state semantics per turn type: which moves carry a CAS prediction,
     which are CAS-neutral, and which can mutate the running CAS state.

Mathematical posture:
  Following Correction 1 in ``CLAUDE.md``, every operator-style transition
  in CAS is gated by an admissibility relation D ⊆ I × I. The dialog
  grammar mirrors this discipline at the conversational layer: a dialog
  move can only follow another move if the (prev, next) pair is in the
  admissibility relation. This keeps the chat surface aligned with the
  algebraic posture of the rest of the framework.

This file is **scaffolding**. The 11 turn types, their admissibility
edges, and their CAS semantics are stable. The follow-on session can
extend them (e.g., adding a CONFIRM turn type, or refining what counts
as a CAS-mutation move) without restructuring the API.

Authoritative Noetic / Domain / Drive / Register names follow the
Project Identity section of ``noetic-compass-scaffold/noetic-compass/CLAUDE.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


# ---------------------------------------------------------------------------
# Turn type enumeration
# ---------------------------------------------------------------------------

# We use ``str, Enum`` rather than ``StrEnum`` for compatibility with
# Python 3.10. Behaviorally identical: TurnType.OPEN == "OPEN" still holds.
class TurnType(str, Enum):
    """The 11 turn types recognised by the Phase 2 DST.

    The naming maps to standard task-oriented dialog move taxonomies but is
    re-grounded against the CAS state-tracking semantics. Each turn type is
    annotated below with:

      - role: which side typically emits this turn (user / assistant /
        either)
      - cas_load_bearing: whether this turn type *carries* a CAS prediction
      - cas_mutating: whether applying this turn updates the running CAS
        state
    """

    # User-side opener.
    OPEN = "OPEN"

    # Assistant moves
    ACK = "ACK"                     # short acknowledgement, no CAS claim
    MIRROR = "MIRROR"               # echo / reflect structure of user input
    CLARIFY = "CLARIFY"             # ask for refinement
    EMPATHIZE = "EMPATHIZE"         # hold space, no CAS proposal
    ANSWER = "ANSWER"               # give CAS prediction
    PLAN = "PLAN"                   # propose pathway (RPM-style)
    REFUSE = "REFUSE"               # decline due to admissibility / safety
    REFUSE_CLAIM = "REFUSE_CLAIM"   # reject user's CAS claim, not the request

    # User-side correction.
    REPAIR = "REPAIR"

    # Either-side terminal.
    CLOSE = "CLOSE"


# ---------------------------------------------------------------------------
# Admissibility relation
# ---------------------------------------------------------------------------

# ADMISSIBILITY[T] = the set of turn types that are valid *immediately
# after* a turn of type T. This mirrors Correction 1's admissibility
# relation D ⊆ I × I at the conversation layer.
ADMISSIBILITY: dict[TurnType, frozenset[TurnType]] = {
    TurnType.OPEN: frozenset({
        TurnType.ACK,
        TurnType.MIRROR,
        TurnType.EMPATHIZE,
        TurnType.CLARIFY,
        TurnType.ANSWER,           # short, well-anchored prompts allow direct ANSWER
        TurnType.REFUSE,
        TurnType.REFUSE_CLAIM,
    }),
    TurnType.ACK: frozenset({
        TurnType.MIRROR,
        TurnType.CLARIFY,
        TurnType.ANSWER,
        TurnType.EMPATHIZE,
    }),
    TurnType.MIRROR: frozenset({
        TurnType.ANSWER,
        TurnType.CLARIFY,
        TurnType.REPAIR,
        TurnType.PLAN,
        TurnType.OPEN,           # user pivots to a new thread
        TurnType.CLOSE,          # user closes after MIRROR
    }),
    TurnType.CLARIFY: frozenset({
        TurnType.ANSWER,
        TurnType.REPAIR,
        TurnType.OPEN,             # user starts a fresh thread mid-clarify
    }),
    TurnType.EMPATHIZE: frozenset({
        TurnType.MIRROR,
        TurnType.CLARIFY,
        TurnType.ANSWER,
        TurnType.CLOSE,
    }),
    TurnType.ANSWER: frozenset({
        TurnType.REPAIR,
        TurnType.PLAN,
        TurnType.CLOSE,
        TurnType.OPEN,             # user pivots to a new thread after answer
    }),
    TurnType.PLAN: frozenset({
        TurnType.CLOSE,
        TurnType.REPAIR,
        TurnType.OPEN,
    }),
    TurnType.REFUSE: frozenset({
        TurnType.CLOSE,
        TurnType.REPAIR,
        TurnType.OPEN,
    }),
    TurnType.REFUSE_CLAIM: frozenset({
        TurnType.CLOSE,
        TurnType.REPAIR,
        TurnType.CLARIFY,
        TurnType.OPEN,
    }),
    TurnType.REPAIR: frozenset({
        TurnType.MIRROR,
        TurnType.ANSWER,
        TurnType.CLARIFY,
        TurnType.REFUSE_CLAIM,
    }),
    TurnType.CLOSE: frozenset(),   # terminal; nothing follows in-conversation
}


def is_admissible(prev: TurnType, next_: TurnType) -> bool:
    """Return True iff (prev, next_) is in the admissibility relation.

    Special case: when ``prev`` is ``None`` -- i.e. the conversation has
    not started yet -- only ``OPEN`` is admissible. Callers that allow
    assistant-initiated openings should bypass this guard explicitly.
    """
    if prev is None:
        return next_ == TurnType.OPEN
    return next_ in ADMISSIBILITY[prev]


def admissible_next(prev: TurnType | None) -> frozenset[TurnType]:
    """Return the set of admissible next turn types after ``prev``."""
    if prev is None:
        return frozenset({TurnType.OPEN})
    return ADMISSIBILITY[prev]


# ---------------------------------------------------------------------------
# CAS-state semantics
# ---------------------------------------------------------------------------

# Turn types that carry a CAS prediction. Their assistant text is
# *grounded* in a specific CAS expression and the engine writes that
# expression into ``DialogState.current_cas_state``.
CAS_LOAD_BEARING: frozenset[TurnType] = frozenset({
    TurnType.MIRROR,
    TurnType.ANSWER,
    TurnType.PLAN,
    TurnType.REFUSE_CLAIM,         # rejecting a user CAS claim implies an alternative state
})

# Turn types that update the running CAS state when applied.
# - MIRROR / ANSWER write the new prediction.
# - PLAN does NOT mutate state by itself; it operates over the *current*
#   state to suggest a pathway.
# - REPAIR may mutate state via the repair strategy (handled separately).
CAS_MUTATING: frozenset[TurnType] = frozenset({
    TurnType.MIRROR,
    TurnType.ANSWER,
    TurnType.REFUSE_CLAIM,
    TurnType.REPAIR,
})

# Turn types that DO NOT carry a CAS prediction. The engine should leave
# ``current_cas_state`` untouched (or, for REPAIR, defer the mutation
# to the repair strategy applier) and emit a templated NL response.
#
# REPAIR is here because the user's repair utterance does not itself
# carry a CAS commitment -- the *follow-on* assistant turn does. REPAIR
# still appears in CAS_MUTATING because applying a REPAIR turn mutates
# state via the repair-strategy pipeline.
CAS_NEUTRAL: frozenset[TurnType] = frozenset({
    TurnType.ACK,
    TurnType.CLARIFY,
    TurnType.EMPATHIZE,
    TurnType.REFUSE,
    TurnType.CLOSE,
    TurnType.OPEN,                 # user side; engine never *emits* OPEN
    TurnType.REPAIR,               # user correction; CAS state changes via repair strategy
})


def carries_cas(turn_type: TurnType) -> bool:
    """Return True iff turns of this type carry a CAS expression."""
    return turn_type in CAS_LOAD_BEARING


def mutates_cas_state(turn_type: TurnType) -> bool:
    """Return True iff turns of this type mutate the running CAS state."""
    return turn_type in CAS_MUTATING


# ---------------------------------------------------------------------------
# User-side vs assistant-side
# ---------------------------------------------------------------------------

# User-emitted turn types.
USER_EMITTED: frozenset[TurnType] = frozenset({
    TurnType.OPEN,
    TurnType.REPAIR,
    # CLARIFY can be user-emitted ("what do you mean?") but is rare; the
    # asymmetric scaffold treats CLARIFY as assistant-emitted by default.
})

# Assistant-emitted turn types.
ASSISTANT_EMITTED: frozenset[TurnType] = frozenset({
    TurnType.ACK,
    TurnType.MIRROR,
    TurnType.CLARIFY,
    TurnType.EMPATHIZE,
    TurnType.ANSWER,
    TurnType.PLAN,
    TurnType.REFUSE,
    TurnType.REFUSE_CLAIM,
})

# Either side can close.
EITHER_EMITTED: frozenset[TurnType] = frozenset({TurnType.CLOSE})


def expected_role(turn_type: TurnType) -> str:
    """Return ``"user"`` / ``"assistant"`` / ``"either"`` for this turn type."""
    if turn_type in USER_EMITTED:
        return "user"
    if turn_type in ASSISTANT_EMITTED:
        return "assistant"
    return "either"


# ---------------------------------------------------------------------------
# Reachability check (used by the smoke test)
# ---------------------------------------------------------------------------

def reachable_from(start: TurnType) -> frozenset[TurnType]:
    """Return the set of turn types reachable from ``start`` via the
    admissibility graph (transitive closure)."""
    seen: set[TurnType] = set()
    frontier: list[TurnType] = [start]
    while frontier:
        cur = frontier.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in ADMISSIBILITY[cur]:
            if nxt not in seen:
                frontier.append(nxt)
    return frozenset(seen)


def admissibility_graph_is_connected() -> bool:
    """Every TurnType (except OPEN itself) must be reachable from OPEN.

    OPEN is the only valid first turn, so any unreachable node is dead
    code in the conversation engine.
    """
    reach = reachable_from(TurnType.OPEN)
    all_types = set(TurnType)
    return reach == all_types


# ---------------------------------------------------------------------------
# Lightweight per-turn metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TurnSemantics:
    """Static description of a turn type's role in the DST.

    Useful for UI and for the conversation engine's bookkeeping. Pure
    data; no methods.
    """

    turn_type: TurnType
    carries_cas: bool
    mutates_state: bool
    role: str            # "user" | "assistant" | "either"
    description: str


TURN_SEMANTICS: dict[TurnType, TurnSemantics] = {
    TurnType.OPEN: TurnSemantics(
        TurnType.OPEN, False, False, "user",
        "User opens the conversation with an initial utterance.",
    ),
    TurnType.ACK: TurnSemantics(
        TurnType.ACK, False, False, "assistant",
        "Short assistant acknowledgement; no CAS commitment.",
    ),
    TurnType.MIRROR: TurnSemantics(
        TurnType.MIRROR, True, True, "assistant",
        "Assistant echoes the structural reading of the user input as a "
        "candidate CAS expression and invites confirmation or repair.",
    ),
    TurnType.CLARIFY: TurnSemantics(
        TurnType.CLARIFY, False, False, "assistant",
        "Assistant asks for refinement before committing to a CAS state.",
    ),
    TurnType.EMPATHIZE: TurnSemantics(
        TurnType.EMPATHIZE, False, False, "assistant",
        "Assistant holds space without proposing a CAS reading.",
    ),
    TurnType.ANSWER: TurnSemantics(
        TurnType.ANSWER, True, True, "assistant",
        "Assistant commits to a CAS prediction grounded in the dialog state.",
    ),
    TurnType.PLAN: TurnSemantics(
        TurnType.PLAN, True, False, "assistant",
        "Assistant proposes an RPM-style pathway over the current state.",
    ),
    TurnType.REFUSE: TurnSemantics(
        TurnType.REFUSE, False, False, "assistant",
        "Assistant declines due to admissibility or safety constraints.",
    ),
    TurnType.REFUSE_CLAIM: TurnSemantics(
        TurnType.REFUSE_CLAIM, True, True, "assistant",
        "Assistant rejects a CAS claim from the user and proposes an "
        "alternative reading.",
    ),
    TurnType.REPAIR: TurnSemantics(
        TurnType.REPAIR, False, True, "user",
        "User corrects the assistant's previous CAS reading.",
    ),
    TurnType.CLOSE: TurnSemantics(
        TurnType.CLOSE, False, False, "either",
        "End-of-conversation marker.",
    ),
}


def describe(turn_type: TurnType) -> TurnSemantics:
    """Return the static semantics for ``turn_type``."""
    return TURN_SEMANTICS[turn_type]


__all__ = [
    "TurnType",
    "ADMISSIBILITY",
    "is_admissible",
    "admissible_next",
    "carries_cas",
    "mutates_cas_state",
    "expected_role",
    "reachable_from",
    "admissibility_graph_is_connected",
    "CAS_LOAD_BEARING",
    "CAS_MUTATING",
    "CAS_NEUTRAL",
    "USER_EMITTED",
    "ASSISTANT_EMITTED",
    "EITHER_EMITTED",
    "TurnSemantics",
    "TURN_SEMANTICS",
    "describe",
]
