"""Dialogue State Tracker (DST) data model and update functions.

This module is the *state* layer of Phase 2. It owns:

  - ``Turn``: a single utterance with role, text, turn type, and -- when
    applicable -- the CAS expression and CAS transition produced by it.
  - ``DialogState``: the running dialog state. Holds turn history, CAS
    state history (for walk-back), the admissibility surface for the
    next move, and bookkeeping fields.
  - Pure update functions (``apply_turn``, ``compress_history``,
    ``detect_repair``, etc.) that produce a *new* DialogState from an
    existing one. State is treated as a value, not a mutable object;
    every update returns a fresh instance.

This file is **scaffolding**. The CAS-state field is currently a string
that the engine writes to; the follow-on session can replace it with a
strongly-typed CAS expression once the rendering pipeline is wired up.
The walk-back stack is implemented and tested; repair is detected
heuristically and produces the right state transitions, but the actual
*re-prediction* is delegated to the predictor (which is itself stubbed
in the scaffold).

Mathematical posture:
  Per Correction 2 (RPM is section-retraction, NOT adjunction), state
  walk-back is one-directional: we can roll back to a previous CAS state
  but we do NOT assume that re-applying the inverse transition recovers
  the post-transition state. The walk-back stack is therefore a *cache*,
  not an inverse computation.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Literal, Optional

from .dialog_grammar import (
    ADMISSIBILITY,
    CAS_LOAD_BEARING,
    CAS_MUTATING,
    TurnType,
    admissible_next,
    is_admissible,
    mutates_cas_state,
)


# ---------------------------------------------------------------------------
# Turn
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Turn:
    """A single utterance in the dialog history.

    Frozen for safety: we never mutate a turn after appending it. CAS
    fields are optional because not every turn carries a CAS prediction.
    """

    role: Literal["user", "assistant"]
    text: str
    turn_type: TurnType
    cas_state_after: Optional[str] = None     # CAS expression after this turn (None for non-CAS turns)
    cas_transition: Optional[str] = None      # human-readable description of the change
    timestamp_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "turn_type": self.turn_type.value,
            "cas_state_after": self.cas_state_after,
            "cas_transition": self.cas_transition,
            "timestamp_ms": self.timestamp_ms,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# DialogState
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DialogState:
    """The running dialog state tracked across turns.

    Frozen + immutable. ``apply_turn`` returns a new ``DialogState``
    rather than mutating in place. Lists are stored as tuples internally
    to keep the dataclass hashable and to discourage accidental mutation.

    Fields:
      turn_history          -- all turns so far, oldest first.
      current_cas_state     -- the running CAS expression. Empty string
                               means "no commitment yet". Per the
                               grammar, only CAS_MUTATING turns update
                               this.
      cas_state_history     -- stack of prior CAS states, newest first.
                               Used by the repair walk-back strategy.
      admissible_next_moves -- frozenset of TurnType values that may
                               legally follow the most recent turn.
      repair_count          -- number of REPAIR turns so far. Used by
                               the engine to escalate to RESET after
                               repeated failed repairs.
      user_satisfaction_estimate -- engine's running estimate of dialog
                               alignment, in [0, 1]. 1.0 = no repairs
                               and confirming utterances; 0.0 = nothing
                               but repairs. Phase-2-scaffold uses a
                               simple decay-from-repairs heuristic; the
                               follow-on session can swap in a learned
                               estimator.
      metadata              -- free-form bag for engine bookkeeping
                               (predictor confidence, register
                               specification, etc.).
    """

    turn_history: tuple[Turn, ...] = ()
    current_cas_state: str = ""
    cas_state_history: tuple[str, ...] = ()
    admissible_next_moves: frozenset[TurnType] = frozenset({TurnType.OPEN})
    repair_count: int = 0
    user_satisfaction_estimate: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    # ----- introspection helpers -----

    @property
    def num_turns(self) -> int:
        return len(self.turn_history)

    @property
    def last_turn(self) -> Optional[Turn]:
        return self.turn_history[-1] if self.turn_history else None

    @property
    def last_turn_type(self) -> Optional[TurnType]:
        return self.last_turn.turn_type if self.last_turn else None

    def has_committed_cas(self) -> bool:
        """True iff the running CAS state is non-empty."""
        return bool(self.current_cas_state)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_history": [t.to_dict() for t in self.turn_history],
            "current_cas_state": self.current_cas_state,
            "cas_state_history": list(self.cas_state_history),
            "admissible_next_moves": sorted(t.value for t in self.admissible_next_moves),
            "repair_count": self.repair_count,
            "user_satisfaction_estimate": round(self.user_satisfaction_estimate, 3),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# State updates
# ---------------------------------------------------------------------------

def initial_state() -> DialogState:
    """Return a fresh DialogState ready for the first user OPEN turn."""
    return DialogState()


def _push_history(stack: tuple[str, ...], item: str, *, cap: int = 32) -> tuple[str, ...]:
    """Push ``item`` onto a newest-first stack, capped at ``cap`` entries."""
    new_stack = (item, *stack)
    if len(new_stack) > cap:
        new_stack = new_stack[:cap]
    return new_stack


def apply_turn(state: DialogState, turn: Turn, *, enforce_admissibility: bool = True) -> DialogState:
    """Apply ``turn`` to ``state`` and return a new ``DialogState``.

    Behaviour:
      - If the turn is CAS-mutating and carries a non-None
        ``cas_state_after``, push the previous ``current_cas_state`` onto
        the walk-back stack and update the running state.
      - If the turn type is REPAIR, increment the repair counter and
        decay the satisfaction estimate.
      - Update ``admissible_next_moves`` to the admissibility set of the
        new turn type.
      - Append the turn to ``turn_history``.

    When ``enforce_admissibility`` is True (default), we sanity-check
    that the turn is admissible after the previous turn. The conversation
    engine should normally choose admissible moves; this guard catches
    accidental violations during scaffold testing. Violations raise
    ``ValueError``. Set to False for low-level testing of the data model.
    """
    if enforce_admissibility:
        prev_type = state.last_turn_type
        if not is_admissible(prev_type, turn.turn_type):
            raise ValueError(
                f"turn type {turn.turn_type.value!r} is not admissible after "
                f"{(prev_type.value if prev_type else None)!r}"
            )

    new_history = (*state.turn_history, turn)

    new_cas_state = state.current_cas_state
    new_cas_history = state.cas_state_history
    if mutates_cas_state(turn.turn_type) and turn.cas_state_after is not None:
        new_cas_history = _push_history(state.cas_state_history, state.current_cas_state)
        new_cas_state = turn.cas_state_after

    new_repair_count = state.repair_count
    new_satisfaction = state.user_satisfaction_estimate
    if turn.turn_type == TurnType.REPAIR:
        new_repair_count = state.repair_count + 1
        # Simple decay: each repair drops satisfaction by 0.2, floored at 0.
        new_satisfaction = max(0.0, state.user_satisfaction_estimate - 0.2)
    elif turn.turn_type in (TurnType.ANSWER, TurnType.MIRROR, TurnType.PLAN):
        # A successful CAS turn nudges satisfaction back up modestly.
        new_satisfaction = min(1.0, state.user_satisfaction_estimate + 0.05)

    new_admissible = ADMISSIBILITY[turn.turn_type]

    return replace(
        state,
        turn_history=new_history,
        current_cas_state=new_cas_state,
        cas_state_history=new_cas_history,
        admissible_next_moves=new_admissible,
        repair_count=new_repair_count,
        user_satisfaction_estimate=new_satisfaction,
    )


def compress_history(state: DialogState, max_turns: int = 10) -> DialogState:
    """Compress ``turn_history`` by dropping the oldest turns.

    Keeps the most recent ``max_turns`` turns. The CAS state history is
    preserved in full because the walk-back depth is independent of the
    user-visible context window.

    No semantic state is lost: ``current_cas_state`` is the sufficient
    statistic for what the engine has committed to, and the walk-back
    stack records the path. The dropped turns are still in
    ``state.metadata['compressed_count']`` for diagnostics.
    """
    if state.num_turns <= max_turns:
        return state

    dropped = state.num_turns - max_turns
    new_history = state.turn_history[-max_turns:]
    new_metadata = dict(state.metadata)
    new_metadata["compressed_count"] = new_metadata.get("compressed_count", 0) + dropped

    return replace(state, turn_history=new_history, metadata=new_metadata)


# ---------------------------------------------------------------------------
# Repair detection
# ---------------------------------------------------------------------------

# Surface forms that strongly suggest a repair from the user. These are
# the high-precision triggers; the follow-on session can extend with a
# learned classifier. Anti-drift note: this is *correction-language*
# detection, not affect detection ("I hate that" is NOT a repair).
_REPAIR_TRIGGERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bno,?\s+(wait|actually|that'?s not|I meant|I mean)\b", re.I),
    re.compile(r"\bthat'?s not (right|what I|quite)", re.I),
    re.compile(r"\bnot quite\b", re.I),
    re.compile(r"\bwait[, ]\s*(?:no|that)", re.I),
    re.compile(r"\bactually,?\s+(I|it|that|no)\b", re.I),
    re.compile(r"\bI meant\b", re.I),
    re.compile(r"\bnope\b", re.I),
    re.compile(r"\bcorrection\b", re.I),
    re.compile(r"\bthat doesn'?t (capture|describe|fit)\b", re.I),
    re.compile(r"\bcloser to\b", re.I),
    re.compile(r"\brewind\b", re.I),
    re.compile(r"\bback up\b", re.I),
)


def detect_repair(state: DialogState, user_text: str) -> bool:
    """Heuristic: does ``user_text`` look like a REPAIR turn?

    A repair is a user utterance that *corrects* a prior assistant CAS
    claim. Detection requires:

      1. The most recent assistant turn was CAS-load-bearing (MIRROR,
         ANSWER, PLAN, REFUSE_CLAIM). Otherwise there is nothing to
         repair.
      2. The user text contains a repair trigger.

    If condition 1 fails, the user utterance is treated as an OPEN /
    follow-up rather than a REPAIR even if trigger words appear.
    """
    if state.num_turns == 0:
        return False

    last = state.last_turn
    if last is None or last.role != "assistant":
        return False
    if last.turn_type not in CAS_LOAD_BEARING:
        return False

    text = (user_text or "").strip()
    if not text:
        return False
    return any(rx.search(text) for rx in _REPAIR_TRIGGERS)


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def make_turn(
    role: Literal["user", "assistant"],
    text: str,
    turn_type: TurnType,
    *,
    cas_state_after: Optional[str] = None,
    cas_transition: Optional[str] = None,
    timestamp_ms: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Turn:
    """Construct a Turn with sensible defaults.

    ``timestamp_ms`` defaults to the current wall-clock time in
    milliseconds. ``metadata`` defaults to an empty dict.
    """
    return Turn(
        role=role,
        text=text,
        turn_type=turn_type,
        cas_state_after=cas_state_after,
        cas_transition=cas_transition,
        timestamp_ms=timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
        metadata=dict(metadata or {}),
    )


__all__ = [
    "Turn",
    "DialogState",
    "initial_state",
    "apply_turn",
    "compress_history",
    "detect_repair",
    "make_turn",
]
