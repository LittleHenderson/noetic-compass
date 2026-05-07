"""OOD (out-of-distribution) routing gate for the CAS-Native v0 chat REPL.

Background
==========

The K=9 structured-token classifier already detects out-of-distribution
free-form English. When given casual prompts ("what up?", "this shit is wack",
"Bro I don't know") the rewrite shim emits a system note containing the string

    "no CAS signal detected in free-form input; predicting on the raw text.
    The K=9 baseline tends to collapse to its prior on out-of-distribution
    colloquial English (documented modality limitation)."

Until 2026-05-07 the chat REPL surfaced that note but **still shipped** the
resulting CAS classification + native generation. The v0 human-relevance audit
(``docs/working/path_B4_human_relevance_failure_2026_05_07.md``) recorded
several confidently-wrong CAS classifications produced from clearly casual
input. This is a routing failure, not a model failure: the detection works,
the routing is broken.

This module is the routing fix. It does NOT add new OOD detection logic — it
**consults** the existing detector's verdict and decides what to do with it:

* ``CONVERSATIONAL_FALLBACK`` — short, casual-looking, no CAS signal: ship a
  canned plain-English reply and SKIP the native generator.
* ``CLARIFICATION``         — longer free-form input with no CAS signal: ask
  the user what they meant, do not invent a CAS state.
* ``NEED_CONTEXT``          — K=9 ran but its top-head confidence is below
  the gate threshold (default 0.4): say "I need more context" rather than
  ship a low-confidence classification as if it were trustworthy.
* ``CAS_PIPELINE``          — trustworthy K=9 result: route through the
  existing K=9 -> native pipeline as before.

The gate is purely deterministic. It introspects:

* a ``notes`` list / ``note`` string / any string-valued field on the K=9
  result for the OOD-detection sentinel substring, and
* the maximum confidence across the standard head-confidence keys produced
  by the K=9 predictor.

No model weights are loaded, no tokenizer is touched, no I/O happens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class RouteDecision(str, Enum):
    """Where the gate sends a (prompt, k9_result) pair."""

    CAS_PIPELINE = "cas_pipeline"
    CLARIFICATION = "clarification"
    NEED_CONTEXT = "need_context"
    CONVERSATIONAL_FALLBACK = "conv_fallback"


@dataclass
class GateResult:
    """Verdict from ``OODGate.route``.

    Attributes:
        decision: which branch the chat REPL should follow.
        canned_response: plain-English reply to display when ``decision`` is
            anything other than ``CAS_PIPELINE``. ``None`` when the gate
            green-lights the K=9 -> native pipeline.
        reason: short human-readable explanation for telemetry / verbose mode.
    """

    decision: RouteDecision
    canned_response: str | None
    reason: str


# ---------------------------------------------------------------------------
# Heuristic constants
# ---------------------------------------------------------------------------


# The exact sentinel emitted by chat.py / rewrite_shim when the K=9 detector
# decides no CAS signal is present. We match against the load-bearing prefix
# rather than the full sentence so cosmetic edits to the note text don't
# silently bypass the gate.
_OOD_NOTE_PREFIX = "no CAS signal detected"


# Tokens that mark a prompt as casual/colloquial English. Hits + short length
# route to CONVERSATIONAL_FALLBACK rather than CLARIFICATION; the user isn't
# asking a question, they're greeting / venting / acknowledging.
_CASUAL_TOKEN_PATTERNS = (
    r"\b(?:yo|sup|hey|hi|hello|howdy)\b",
    r"\bwhat'?s?\s*up\b",
    r"\bwhat\s*up\b",
    r"\bbro\b",
    r"\bdude\b",
    r"\bnah\b",
    r"\byeah\b",
    r"\bok(?:ay)?\b",
    r"\bcool\b",
    r"\bwack\b",
    r"\bdope\b",
    r"\blit\b",
    r"\bwtf\b",
    r"\bidk\b",
    r"\bi\s*don'?t\s*know\b",
    r"\bfuck\b",
    r"\bshit\b",
    r"\bdamn\b",
    r"\bwhatever\b",
    r"\bnope\b",
    r"\bsure\b",
    r"\bhuh\?\b",
)

_CASUAL_RE = re.compile("|".join(_CASUAL_TOKEN_PATTERNS), re.IGNORECASE)


# Standard K=9 head-confidence keys we look at when no explicit "confidence"
# scalar is present. The list mirrors the per-head structure produced by
# ``cas_native.inference.predict_cas._decode_outputs`` callers / trace builder.
_HEAD_CONFIDENCE_KEYS = (
    "confidence",
    "noetic_confidence",
    "domain_confidence",
    "drive_confidence",
    "register_confidence",
    "expression_family_confidence",
    "transition_kind_confidence",
)


# Canned replies. Plain-English on purpose — no CAS notation, no register
# vocabulary. The point of the gate is precisely to avoid shipping CAS in
# response to non-CAS input.
_CANNED_FALLBACK = (
    "Hey — that one's outside what I can read as CAS structure. "
    "If you want me to classify something specific, paste a sentence that "
    "describes a thought, feeling, habit, or response."
)

_CANNED_CLARIFICATION = (
    "I can't tell what you'd like me to do with that. Could you say a bit "
    "more? For CAS classification I need a sentence describing a thought, "
    "feeling, habit, or response — for general questions, just ask plainly."
)

_CANNED_NEED_CONTEXT = (
    "I'm not confident enough about that one to ship a CAS classification. "
    "If there's more context — a longer sentence, what triggered it, or "
    "what you're trying to figure out — I can take another pass."
)


# ---------------------------------------------------------------------------
# OODGate
# ---------------------------------------------------------------------------


class OODGate:
    """Routing gate that decides whether the K=9 -> native pipeline should run.

    Construct once per session; ``route`` is pure and side-effect free.

    Args:
        confidence_threshold: minimum K=9 head confidence (in [0, 1]) below
            which a result is treated as untrustworthy and routed to
            ``NEED_CONTEXT``. Default 0.4.
        casual_word_limit: prompts at or below this whitespace-token count
            with at least one casual hit go to ``CONVERSATIONAL_FALLBACK``;
            longer prompts go to ``CLARIFICATION``. Default 10 to match the
            spec contract (``< 10 words`` casual -> fallback).
    """

    def __init__(
        self,
        confidence_threshold: float = 0.4,
        casual_word_limit: int = 10,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be in [0, 1], got {confidence_threshold!r}"
            )
        if casual_word_limit < 1:
            raise ValueError(
                f"casual_word_limit must be >= 1, got {casual_word_limit!r}"
            )
        self.confidence_threshold = float(confidence_threshold)
        self.casual_word_limit = int(casual_word_limit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, prompt: str, k9_result: dict[str, Any]) -> GateResult:
        """Decide what to do with ``prompt`` given the K=9 ``k9_result``.

        ``k9_result`` is consulted but never mutated. The gate looks for:

        1. The OOD-detector sentinel substring in any string-valued
           ``note`` / ``notes`` field.
        2. The max confidence across the standard K=9 head-confidence keys
           (or an explicit ``confidence`` scalar if present).
        """
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")
        if k9_result is None:
            k9_result = {}
        if not isinstance(k9_result, dict):
            raise TypeError(
                f"k9_result must be dict (or None), got {type(k9_result).__name__}"
            )

        # 1. OOD-detector sentinel takes priority — the K=9 detector itself
        #    has already said the input is out-of-distribution. We do not
        #    second-guess it; we just pick the right canned-response branch.
        if _has_ood_sentinel(k9_result):
            if _looks_casual(prompt, self.casual_word_limit):
                return GateResult(
                    decision=RouteDecision.CONVERSATIONAL_FALLBACK,
                    canned_response=_CANNED_FALLBACK,
                    reason=(
                        "K=9 detector reports no CAS signal in free-form "
                        "input; prompt is short and casual-looking."
                    ),
                )
            return GateResult(
                decision=RouteDecision.CLARIFICATION,
                canned_response=_CANNED_CLARIFICATION,
                reason=(
                    "K=9 detector reports no CAS signal in free-form "
                    "input; prompt is non-casual but unclassifiable."
                ),
            )

        # 2. Confidence floor — even when a CAS signal was detected, an
        #    under-threshold top-head confidence means we should not ship
        #    the classification as confident.
        confidence = _max_head_confidence(k9_result)
        if confidence is not None and confidence < self.confidence_threshold:
            return GateResult(
                decision=RouteDecision.NEED_CONTEXT,
                canned_response=_CANNED_NEED_CONTEXT,
                reason=(
                    f"K=9 top-head confidence {confidence:.3f} is below "
                    f"gate threshold {self.confidence_threshold:.3f}."
                ),
            )

        # 3. Trustworthy K=9 result. Route through the existing pipeline.
        return GateResult(
            decision=RouteDecision.CAS_PIPELINE,
            canned_response=None,
            reason="K=9 result trusted; routing through CAS pipeline.",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_ood_sentinel(k9_result: dict[str, Any]) -> bool:
    """Return True if the OOD-detector sentinel is anywhere in k9_result.

    We look at:
      * top-level ``note`` / ``notes`` (string or iterable-of-strings)
      * any other top-level string field (defensive — chat.py historically
        moved the note between fields).
    """
    for key in ("notes", "note", "ood_note", "system_notes"):
        value = k9_result.get(key)
        if _value_contains_sentinel(value):
            return True
    # Defensive sweep across all string-valued fields. The spec explicitly
    # asks for "the string in any note field", and historically the note has
    # been carried in different keys. Better to scan a small dict than to
    # silently miss the sentinel.
    for value in k9_result.values():
        if _value_contains_sentinel(value):
            return True
    return False


def _value_contains_sentinel(value: Any) -> bool:
    if isinstance(value, str):
        return _OOD_NOTE_PREFIX in value
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_value_contains_sentinel(v) for v in value)
    if isinstance(value, dict):
        return any(_value_contains_sentinel(v) for v in value.values())
    return False


def _max_head_confidence(k9_result: dict[str, Any]) -> float | None:
    """Return the maximum head confidence in [0, 1], or None if absent."""
    seen: list[float] = []
    for key in _HEAD_CONFIDENCE_KEYS:
        value = k9_result.get(key)
        if isinstance(value, (int, float)):
            try:
                seen.append(float(value))
            except (TypeError, ValueError):
                continue
    # Also scan a nested ``confidence`` mapping (some predictors return
    # ``{"confidence": {"noetic": 0.91, ...}}``).
    nested = k9_result.get("confidence")
    if isinstance(nested, dict):
        for v in nested.values():
            if isinstance(v, (int, float)):
                seen.append(float(v))
    if not seen:
        return None
    return max(seen)


def _looks_casual(prompt: str, word_limit: int) -> bool:
    """Casual = short prompt that contains a casual/slang token.

    Returns True iff:
      * the whitespace-token count is strictly less than ``word_limit``, AND
      * at least one casual-token regex matches.
    Empty / whitespace-only prompts are considered casual (greeting attempt).
    """
    stripped = prompt.strip()
    if not stripped:
        return True
    n_words = len(stripped.split())
    if n_words >= word_limit:
        return False
    return bool(_CASUAL_RE.search(stripped))


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


__all__ = ["OODGate", "GateResult", "RouteDecision"]
