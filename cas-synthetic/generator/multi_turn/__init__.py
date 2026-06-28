"""Synthetic multi-turn conversation generator for the Phase 2 DST.

Produces synthetic ``DialogState``-shaped records that simulate a user +
assistant exchange across multiple turns. Each record consists of:

  - a dialog path (sequence of TurnType values) drawn from the
    admissibility graph defined in ``cas_native.dst.dialog_grammar``;
  - per-turn user and assistant utterances rendered from templates;
  - a final CAS state (``current_cas_state`` after the last turn);
  - bucket annotations identifying which CAS-Native training buckets
    (v74_baseline, v75_register, ...) each ANSWER turn aligns with.

This is **scaffolding**: the templates are deterministic and small, and
narrative coherence across turns is rudimentary. The follow-on session
will (a) widen the template pool, (b) plug in the real
``ConversationEngine`` for grounding, and (c) introduce a coherence
constraint across CAS states within a single conversation.

The generator is path-of-pure-Python and reuses the dialog grammar
defined in the cas-native package; it does NOT import torch and does
NOT touch the K=9 baseline checkpoint.
"""

from __future__ import annotations

from .conversation_generator import (
    ConversationRecord,
    generate_conversation,
    generate_dialog_path,
)

__all__ = [
    "ConversationRecord",
    "generate_conversation",
    "generate_dialog_path",
]
