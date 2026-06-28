"""Repair-strategy selection and application for the Phase 2 DST.

When the user emits a REPAIR turn ("no, wait, that's not right"), the
engine must decide *how* to repair:

  - WALK_BACK: the previous CAS state was closer; pop it off the
    walk-back stack and restore.
  - REFINE: the prior reading was directionally right but missed a
    nuance; ask the predictor to re-run with the user correction as
    additional context.
  - CLARIFY: the user signal is ambiguous; ask a targeted clarifying
    question rather than re-predicting.
  - RESET: too many failed repairs in a row; drop committed state and
    let the conversation restart.

This module implements the *selection* logic (which strategy to use)
and the *application* logic (how the selected strategy mutates
DialogState). The selection logic is heuristic in the scaffold; the
follow-on session can replace it with a learned policy.

Mathematical posture:
  Per Correction 2 (RPM is section-retraction), walk-back is *not*
  inverse application. We restore from a cached CAS state on the
  walk-back stack rather than computing an inverse transition.
"""

from __future__ import annotations

import re
from dataclasses import replace
from enum import Enum
from typing import Optional

from .dialog_grammar import TurnType
from .state_tracker import DialogState, Turn, make_turn


# ---------------------------------------------------------------------------
# Strategy enumeration
# ---------------------------------------------------------------------------

class RepairStrategy(str, Enum):
    """The four repair strategies recognised by the DST."""

    WALK_BACK = "walk_back"
    REFINE = "refine"
    CLARIFY = "clarify"
    RESET = "reset"


# Threshold: after this many repairs in a row, escalate to RESET.
RESET_AFTER_REPAIRS: int = 3


# ---------------------------------------------------------------------------
# Heuristic cues
# ---------------------------------------------------------------------------

# "Closer to..." / "more like..." / "what I meant was..." -> REFINE
_REFINE_TRIGGERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bcloser to\b", re.I),
    re.compile(r"\bmore like\b", re.I),
    re.compile(r"\bwhat I meant\b", re.I),
    re.compile(r"\bI meant\b", re.I),
    re.compile(r"\bit'?s really\b", re.I),
    re.compile(r"\bactually\b", re.I),
)

# "Go back" / "rewind" / "before that" / "that earlier reading" -> WALK_BACK
_WALK_BACK_TRIGGERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(go|back|step) back\b", re.I),
    re.compile(r"\brewind\b", re.I),
    re.compile(r"\bbefore that\b", re.I),
    re.compile(r"\bthe (earlier|previous) (reading|one|answer)\b", re.I),
    re.compile(r"\bfirst (reading|answer|one)\b", re.I),
)

# "I don't know" / "I'm not sure" / "what do you mean" -> CLARIFY
_CLARIFY_TRIGGERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bI don'?t know\b", re.I),
    re.compile(r"\bI'?m not sure\b", re.I),
    re.compile(r"\bwhat do you mean\b", re.I),
    re.compile(r"\bI can'?t tell\b", re.I),
    re.compile(r"\beither\b.*\bor\b", re.I),
)


def select_repair_strategy(
    state: DialogState,
    user_correction: str,
) -> RepairStrategy:
    """Pick the repair strategy for ``user_correction`` given ``state``.

    Decision order:
      1. If repair_count + 1 reaches ``RESET_AFTER_REPAIRS`` and a fresh
         repair is incoming, escalate to RESET.
      2. If WALK_BACK triggers fire AND the walk-back stack is non-empty,
         use WALK_BACK.
      3. If CLARIFY triggers fire (user is unsure rather than
         correcting), use CLARIFY.
      4. If REFINE triggers fire, use REFINE.
      5. Default: REFINE (the most common case -- user adjusts the
         reading rather than vetoing it).
    """
    text = (user_correction or "").strip()

    if state.repair_count + 1 >= RESET_AFTER_REPAIRS:
        return RepairStrategy.RESET

    if state.cas_state_history and any(rx.search(text) for rx in _WALK_BACK_TRIGGERS):
        return RepairStrategy.WALK_BACK

    if any(rx.search(text) for rx in _CLARIFY_TRIGGERS):
        return RepairStrategy.CLARIFY

    if any(rx.search(text) for rx in _REFINE_TRIGGERS):
        return RepairStrategy.REFINE

    return RepairStrategy.REFINE


# ---------------------------------------------------------------------------
# Strategy application
# ---------------------------------------------------------------------------

def apply_repair(
    state: DialogState,
    strategy: RepairStrategy,
    correction_signal: str,
) -> DialogState:
    """Apply ``strategy`` to ``state`` and return a new ``DialogState``.

    Note: this function does NOT add a Turn. Adding the user's REPAIR
    turn is the caller's responsibility (do that *first*, with
    ``apply_turn``). This function only adjusts the *follow-on* engine
    state -- the walk-back / refine / clarify / reset side-effects.

    For WALK_BACK: pops the most-recent state off the walk-back stack
    and restores it as ``current_cas_state``.

    For REFINE: leaves ``current_cas_state`` unchanged (the predictor
    will re-run and a subsequent ANSWER turn will overwrite it). Stores
    the correction signal in ``metadata`` so the predictor can pick it up.

    For CLARIFY: leaves CAS state untouched. Stores the correction
    signal in ``metadata`` so the engine can build a targeted clarifying
    question.

    For RESET: clears ``current_cas_state``, ``cas_state_history``, and
    resets the satisfaction estimate. Repair count is preserved -- it's
    a count of how many we've done, not a budget.
    """
    if strategy == RepairStrategy.WALK_BACK:
        if not state.cas_state_history:
            # Nothing to walk back to. Fall through to REFINE behaviour.
            return apply_repair(state, RepairStrategy.REFINE, correction_signal)
        restored, *rest = state.cas_state_history
        new_metadata = dict(state.metadata)
        new_metadata["last_repair_strategy"] = strategy.value
        new_metadata["last_correction_signal"] = correction_signal
        return replace(
            state,
            current_cas_state=restored,
            cas_state_history=tuple(rest),
            metadata=new_metadata,
        )

    if strategy == RepairStrategy.REFINE:
        new_metadata = dict(state.metadata)
        new_metadata["last_repair_strategy"] = strategy.value
        new_metadata["last_correction_signal"] = correction_signal
        new_metadata["pending_refinement"] = True
        return replace(state, metadata=new_metadata)

    if strategy == RepairStrategy.CLARIFY:
        new_metadata = dict(state.metadata)
        new_metadata["last_repair_strategy"] = strategy.value
        new_metadata["last_correction_signal"] = correction_signal
        new_metadata["pending_clarification"] = True
        return replace(state, metadata=new_metadata)

    if strategy == RepairStrategy.RESET:
        new_metadata = dict(state.metadata)
        new_metadata["last_repair_strategy"] = strategy.value
        new_metadata["last_correction_signal"] = correction_signal
        new_metadata["reset_count"] = new_metadata.get("reset_count", 0) + 1
        return replace(
            state,
            current_cas_state="",
            cas_state_history=(),
            user_satisfaction_estimate=0.5,  # neutral after reset
            metadata=new_metadata,
        )

    raise ValueError(f"unknown repair strategy: {strategy!r}")


# ---------------------------------------------------------------------------
# Repair plumbing helpers (used by ConversationEngine)
# ---------------------------------------------------------------------------

def derive_followup_turn_type(strategy: RepairStrategy) -> TurnType:
    """Return the TurnType the *engine* should emit in response to a repair.

    Mapping:
      WALK_BACK -> MIRROR (echo the restored reading and ask user to
                            confirm)
      REFINE    -> ANSWER (re-run the predictor with the correction
                            and commit)
      CLARIFY   -> CLARIFY
      RESET     -> CLARIFY (best opener after a reset is a clarifying
                            question)
    """
    return {
        RepairStrategy.WALK_BACK: TurnType.MIRROR,
        RepairStrategy.REFINE: TurnType.ANSWER,
        RepairStrategy.CLARIFY: TurnType.CLARIFY,
        RepairStrategy.RESET: TurnType.CLARIFY,
    }[strategy]


__all__ = [
    "RepairStrategy",
    "RESET_AFTER_REPAIRS",
    "select_repair_strategy",
    "apply_repair",
    "derive_followup_turn_type",
]
