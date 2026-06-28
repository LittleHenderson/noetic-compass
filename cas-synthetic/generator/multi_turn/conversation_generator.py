"""Synthetic multi-turn conversation generator.

Produces ``ConversationRecord`` instances that simulate a CAS-Native
chat exchange across multiple turns. The dialog path (sequence of
TurnType values) is drawn deterministically from the admissibility
graph defined in ``cas_native.dst.dialog_grammar``; per-turn
utterances come from a small templates table; assistant CAS states
come from a tiny rule lexicon (a fragment of what
``DefaultStubPredictor`` uses) so the synthetic conversations have
plausible CAS evolution.

This is **scaffolding**:

  - The template table is small and the variety is intentionally
    limited. The follow-on session widens it and adds bucket-specific
    flavor (v74 / v75 / v76 / v77 / meta_logic).
  - There is NO coherence constraint across CAS states within a single
    record. The follow-on session adds a coherence guarantee (e.g. the
    final ANSWER must agree with the prior MIRROR up to a refinement).
  - The generator does NOT call into ``ConversationEngine``. It builds
    records directly from templates so it can run without any model
    inference. The follow-on session will provide an
    ``engine_grounded`` mode that uses the engine for a subset of
    records.

Authoritative Noetic / Domain / Drive / Register names follow
``noetic-compass-scaffold/noetic-compass/CLAUDE.md``.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import random
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Dialog grammar import (with fallback for direct script use)
# ---------------------------------------------------------------------------

def _load_dialog_grammar():
    """Import ``cas_native.dst.dialog_grammar`` even when the cas_native
    package alias is not yet registered.

    In test environments, ``conftest.py`` registers ``cas_native``
    pointing at ``cas-native/``. When the generator is run directly
    (e.g. ``python -m cas_synthetic.generator.multi_turn.conversation_generator``)
    that alias may not be set; we fall back to importing the file by
    path.
    """
    try:
        return importlib.import_module("cas_native.dst.dialog_grammar")
    except Exception:
        pass

    here = Path(__file__).resolve()
    repo_root = None
    for ancestor in here.parents:
        if (ancestor / "noetic-compass-scaffold").exists():
            repo_root = ancestor
            break
    if repo_root is None:
        raise RuntimeError(
            "cannot locate repo root with noetic-compass-scaffold/ from "
            f"{here}"
        )

    cas_native_dir = (
        repo_root / "noetic-compass-scaffold" / "noetic-compass" / "cas-native"
    )
    if "cas_native" not in sys.modules:
        pkg = types.ModuleType("cas_native")
        pkg.__file__ = str(cas_native_dir / "__init__.py")
        pkg.__path__ = [str(cas_native_dir)]
        sys.modules["cas_native"] = pkg
    return importlib.import_module("cas_native.dst.dialog_grammar")


_grammar = _load_dialog_grammar()
TurnType = _grammar.TurnType
ADMISSIBILITY = _grammar.ADMISSIBILITY
is_admissible = _grammar.is_admissible
CAS_LOAD_BEARING = _grammar.CAS_LOAD_BEARING


# ---------------------------------------------------------------------------
# Record type
# ---------------------------------------------------------------------------

@dataclass
class ConversationRecord:
    """A synthetic multi-turn conversation.

    Fields mirror the dict shape returned by ``generate_conversation``.
    Wrapping in a dataclass makes downstream consumers (e.g. a JSONL
    writer) cleaner, and keeps the test contract explicit.
    """

    id: str
    turns: list[dict[str, Any]]
    final_cas_state: str
    dialog_path: list[TurnType]
    buckets_visited: list[str]
    num_repairs: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "turns": [dict(t) for t in self.turns],
            "final_cas_state": self.final_cas_state,
            "dialog_path": [t.value for t in self.dialog_path],
            "buckets_visited": list(self.buckets_visited),
            "num_repairs": self.num_repairs,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

# (bucket, user_template, cas_expr, transition_label)
_USER_TEMPLATES: tuple[tuple[str, str, str, str], ...] = (
    ("v74_baseline",  "I can't stand it when people interrupt me",
        "^3^E|f", "visceral aversion"),
    ("v74_baseline",  "I love how the morning light comes through the window",
        "^2^E|f", "felt attraction"),
    ("v75_register",  "It just popped into my head out of nowhere",
        "^9^C|A", "Idea brought to Mind"),
    ("v75_register",  "I keep practicing the same scale every day",
        "^7^O|E", "rhythmic entrainment"),
    ("v76_production","Producing trustworthy work needs care plus discipline",
        "^6^P|A", "compositional decomposition"),
    ("v77_omega",     "When I feel adverse and at the same time drawn to it",
        "^3^P|f + ^2^P|f", "co-presence"),
    ("meta_logic",    "Walking it through, that argument doesn't hold up",
        "^6^C|A", "compositional decomposition"),
)

_USER_REPAIR_TEMPLATES: tuple[str, ...] = (
    "no wait, that's not right -- it's closer to grief than aversion",
    "actually, I meant something more like awe",
    "no, more like resignation than hatred",
    "wait, back up -- the earlier reading fit better",
)

_USER_CLARIFY_RESPONSE_TEMPLATES: tuple[str, ...] = (
    "well, the part that hits hardest is the powerlessness",
    "I think it's mostly the surprise",
    "what stays is the warmth",
)

_USER_FOLLOWUP_TEMPLATES: tuple[str, ...] = (
    "and then it reminds me of something from years ago",
    "and that brought up a lot",
    "now I'm curious what comes next",
)

_USER_CLOSE_TEMPLATES: tuple[str, ...] = (
    "thanks, that's it",
    "bye for now",
)

_ASSISTANT_TEMPLATES: dict[TurnType, tuple[str, ...]] = {
    TurnType.ACK: (
        "Got it.",
        "Okay -- I'm with you.",
    ),
    TurnType.MIRROR: (
        "If I'm hearing you, the structural reading is {cas}.",
        "What's landing for me is {cas}. Does that fit?",
    ),
    TurnType.CLARIFY: (
        "Walk it back -- what's closer to your felt sense?",
        "Help me anchor this: which part lands hardest?",
    ),
    TurnType.EMPATHIZE: (
        "That sounds like a lot.",
        "Yeah. That's heavy.",
    ),
    TurnType.ANSWER: (
        "The reading I'd stand behind is {cas}.",
        "Best fit I can give is {cas}.",
    ),
    TurnType.PLAN: (
        "Given {cas}, the next step on the pathway would be to strengthen "
        "the prerequisite that's currently weakest.",
    ),
    TurnType.REFUSE: (
        "I can't take that turn -- it would break the admissibility of "
        "the dialog. Want to try a different angle?",
    ),
    TurnType.REFUSE_CLAIM: (
        "I don't think the structure you're proposing fits. The closer "
        "reading I'd stand behind is {cas}.",
    ),
    TurnType.CLOSE: (
        "Thanks for walking through that.",
        "Take care.",
    ),
}


# ---------------------------------------------------------------------------
# Path generation
# ---------------------------------------------------------------------------

# Realistic-feeling distribution. We deliberately bias toward MIRROR,
# ANSWER, REPAIR so the synthetic corpus exercises the repair surface.
_TURN_TYPE_WEIGHTS: dict[TurnType, float] = {
    TurnType.ACK: 0.5,
    TurnType.MIRROR: 1.5,
    TurnType.CLARIFY: 1.0,
    TurnType.EMPATHIZE: 0.7,
    TurnType.ANSWER: 1.5,
    TurnType.PLAN: 0.4,
    TurnType.REFUSE: 0.1,
    TurnType.REFUSE_CLAIM: 0.2,
    TurnType.REPAIR: 1.2,
    TurnType.OPEN: 0.6,        # users sometimes pivot to a fresh thread
    TurnType.CLOSE: 0.0,       # we close deliberately, not via sampling
}


def generate_dialog_path(seed: int, target_turns: int) -> list[TurnType]:
    """Build a valid dialog path through the admissibility graph.

    Algorithm:
      - Start at OPEN.
      - At each step, sample the next turn type from the admissibility
        set of the current type, weighted by ``_TURN_TYPE_WEIGHTS``.
      - Stop early if the path lands on a turn type whose admissibility
        set is empty (only CLOSE).
      - At the target length, force CLOSE if it is admissible from the
        current state. Otherwise, walk one more step toward a state
        from which CLOSE is reachable.

    Determinism: same seed -> same path.
    """
    if target_turns < 1:
        return [TurnType.OPEN]

    rng = random.Random(seed)
    path: list[TurnType] = [TurnType.OPEN]
    while len(path) < target_turns:
        cur = path[-1]
        candidates = list(ADMISSIBILITY[cur])
        if not candidates:
            break
        # Filter CLOSE out of mid-stream sampling unless we are at the
        # last position; CLOSE is the explicit terminator we add at end.
        non_close = [c for c in candidates if c != TurnType.CLOSE]
        pool = non_close if non_close else candidates
        weights = [_TURN_TYPE_WEIGHTS[c] for c in pool]
        nxt = rng.choices(pool, weights=weights, k=1)[0]
        path.append(nxt)

    # Try to terminate cleanly with CLOSE.
    if TurnType.CLOSE in ADMISSIBILITY[path[-1]]:
        path.append(TurnType.CLOSE)
    else:
        # One more step toward something with a CLOSE outgoing edge.
        candidates = [
            c for c in ADMISSIBILITY[path[-1]]
            if TurnType.CLOSE in ADMISSIBILITY[c]
        ]
        if candidates:
            nxt = sorted(candidates, key=lambda c: c.value)[0]
            path.append(nxt)
            path.append(TurnType.CLOSE)
    return path


# ---------------------------------------------------------------------------
# Per-turn rendering
# ---------------------------------------------------------------------------

def _render_turn(
    turn_type: TurnType,
    rng: random.Random,
    *,
    current_cas: str,
    target_buckets: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Render a single turn as a plain dict.

    Returns: {"role", "text", "turn_type", "cas_state_after", "bucket"}.
    The cas_state_after field is None for CAS-neutral turns.
    """
    if turn_type == TurnType.OPEN:
        # Pick a user opening template.
        candidates = _USER_TEMPLATES
        if target_buckets:
            filtered = [t for t in candidates if t[0] in target_buckets]
            if filtered:
                candidates = tuple(filtered)
        bucket, text, cas, transition = rng.choice(candidates)
        return {
            "role": "user",
            "text": text,
            "turn_type": turn_type,
            "cas_state_after": None,
            "bucket": bucket,
            "transition": None,
        }

    if turn_type == TurnType.REPAIR:
        return {
            "role": "user",
            "text": rng.choice(_USER_REPAIR_TEMPLATES),
            "turn_type": turn_type,
            "cas_state_after": None,
            "bucket": None,
            "transition": "user repair",
        }

    if turn_type == TurnType.CLOSE:
        # CLOSE can come from either side; bias toward user.
        if rng.random() < 0.5:
            return {
                "role": "user",
                "text": rng.choice(_USER_CLOSE_TEMPLATES),
                "turn_type": turn_type,
                "cas_state_after": None,
                "bucket": None,
                "transition": None,
            }
        return {
            "role": "assistant",
            "text": rng.choice(_ASSISTANT_TEMPLATES[TurnType.CLOSE]),
            "turn_type": turn_type,
            "cas_state_after": None,
            "bucket": None,
            "transition": None,
        }

    # All remaining turn types are assistant-emitted.
    template = rng.choice(_ASSISTANT_TEMPLATES[turn_type])
    if turn_type in CAS_LOAD_BEARING:
        # Pick a CAS state for the assistant to commit to.
        candidates = _USER_TEMPLATES
        if target_buckets:
            filtered = [t for t in candidates if t[0] in target_buckets]
            if filtered:
                candidates = tuple(filtered)
        bucket, _, cas, transition = rng.choice(candidates)
        text = template.format(cas=cas)
        return {
            "role": "assistant",
            "text": text,
            "turn_type": turn_type,
            "cas_state_after": cas,
            "bucket": bucket,
            "transition": transition,
        }
    text = template
    return {
        "role": "assistant",
        "text": text,
        "turn_type": turn_type,
        "cas_state_after": None,
        "bucket": None,
        "transition": None,
    }


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def _stable_id(seed: int, path: list[TurnType]) -> str:
    """Build a stable, short ID from the seed + path."""
    h = hashlib.sha256()
    h.update(str(seed).encode("utf-8"))
    h.update(b"|")
    h.update(",".join(t.value for t in path).encode("utf-8"))
    return f"mt-{h.hexdigest()[:12]}"


def generate_conversation(
    *,
    seed: int,
    target_turns: int = 6,
    target_buckets: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Generate a synthetic multi-turn conversation.

    Args:
      seed:           int seed for determinism.
      target_turns:   target dialog length (number of turns including
                      OPEN and CLOSE). The realised length may be one
                      or two off depending on terminal logic.
      target_buckets: if provided, only utterances from these buckets
                      are sampled. Useful for bucket-specific corpora.

    Returns a dict with keys:
      id                -- stable string ID
      turns             -- list of turn dicts
      final_cas_state   -- last assistant CAS commitment ("" if none)
      dialog_path       -- list of TurnType values
      buckets_visited   -- distinct buckets across CAS-load-bearing
                           assistant turns
      num_repairs       -- count of REPAIR user turns
      metadata          -- {"seed", "target_turns", "target_buckets"}
    """
    rng = random.Random(seed)
    path = generate_dialog_path(seed, target_turns)

    turns: list[dict[str, Any]] = []
    current_cas = ""
    buckets_visited: list[str] = []
    num_repairs = 0
    for tt in path:
        rendered = _render_turn(tt, rng, current_cas=current_cas, target_buckets=target_buckets)
        if rendered["cas_state_after"]:
            current_cas = rendered["cas_state_after"]
            if rendered["bucket"] and rendered["bucket"] not in buckets_visited:
                buckets_visited.append(rendered["bucket"])
        if tt == TurnType.REPAIR:
            num_repairs += 1
        # Stringify turn_type for the dict shape downstream consumers
        # actually want.
        rendered = dict(rendered)
        rendered["turn_type"] = tt.value
        turns.append(rendered)

    record = ConversationRecord(
        id=_stable_id(seed, path),
        turns=turns,
        final_cas_state=current_cas,
        dialog_path=path,
        buckets_visited=buckets_visited,
        num_repairs=num_repairs,
        metadata={
            "seed": seed,
            "target_turns": target_turns,
            "target_buckets": list(target_buckets or []),
        },
    )
    return record.to_dict()


__all__ = [
    "ConversationRecord",
    "generate_conversation",
    "generate_dialog_path",
]


# ---------------------------------------------------------------------------
# Script entry point: generate a small sample for inspection.
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import json
    rec = generate_conversation(seed=42, target_turns=6)
    print(json.dumps(rec, indent=2))
