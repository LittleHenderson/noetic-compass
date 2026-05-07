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


# ---------------------------------------------------------------------------
# CAS surface-token pre-filter (Step E calibration)
# ---------------------------------------------------------------------------
#
# Pre-calibration audit (cas-native/evaluation/runs/
# b4_product_routing_eval_b3_full_50k_prodshape.json) showed the K=9 OOD
# verdict over-fires on prompts that explicitly contain CAS notation: the
# classifier emits "no CAS signal detected" because the surface form (Θ, Ω,
# ⟨2:3:6⟩, NoeticCluster{...}) sits outside the rewrite shim's recognized
# patterns, and the gate then blocks the pipeline. Result: 100% fail on
# valid_cas_notation, v76_production, v77_omega, meta_logic, and
# fractal_composition; 25% route_match overall.
#
# The pre-filter below detects CAS surface tokens deterministically and,
# when matched, OVERRIDES the OOD verdict. Coverage spans seven categories;
# meta-logic constructors and Cognitive Fractal angle-bracket sequences are
# both included — these were the categories the v0 corpus / earlier regex
# sketches forgot.
#
# Coverage policy: false-positive (treating non-CAS as CAS) is much cheaper
# than false-negative (blocking real CAS). Default to PIPELINE when ambiguous.
#
# 1. State literals — ``^N`` (Noetic 0..9) and ``^N^D`` where D ∈ {P,C,E,O}.
#    Permits trailing extras like ``_{F2}``, ``|A``, ``|⟨A,f,T⟩``.
_CAS_STATE_LITERAL_RE = re.compile(r"\^[0-9](?:\^[PCEO])?")
# 2. Drive subscripts — ``F1``..``F7`` and ``_{F1}``..``_{F7}``.
_CAS_DRIVE_RE = re.compile(r"(?:_\{F[1-7]\}|F[1-7])(?![0-9])")
# 3a. Single register tags — ``|T``, ``|A``, ``|f``, ``|E``.
_CAS_SINGLE_REGISTER_RE = re.compile(r"\|[TAfE](?![A-Za-z])")
# 3b. Multi-register set notation — ``|⟨A,f,T⟩`` (Unicode) or ``|<A,f,T>`` ASCII.
_CAS_MULTI_REGISTER_UNICODE_RE = re.compile(
    r"\|⟨\s*[TAfE](?:\s*,\s*[TAfE])*\s*⟩"
)
_CAS_MULTI_REGISTER_ASCII_RE = re.compile(
    r"\|<\s*[TAfE](?:\s*,\s*[TAfE])+\s*>"
)
# 4a. CAS operator unicode glyphs (Ω, Θ, ∘, →, ×, ⊗, ⊆, ∈, ∪, ∩, ∖, ⟨, ⟩).
#     ``+`` and ``=`` and ``*`` are too generic to flag on their own; we use
#     them only as part of richer patterns below.
_CAS_OPERATOR_GLYPH_RE = re.compile(r"[ΩΘ∘→×⊗⊆∈∪∩∖⟨⟩]")
# 4b. ASCII operator forms used in fixture surface forms (-> arrow, *, =).
#     We match these only when they co-occur with CAS-y context (state
#     literal, named omega, recipe word, set-constructor) — matching ``->``
#     unconditionally would flag non-CAS English. Captured by the
#     compound-recipe rule below.
# 4c. Named emergent omega — ``Ω_<name>`` (Unicode) or ``Omega_<name>`` ASCII.
_CAS_NAMED_OMEGA_RE = re.compile(
    r"(?:Ω|\bOmega)_[A-Za-z][A-Za-z0-9_]*"
)
# 5a. Production recipe (v7.6) — ``Θ(...)`` or ``Theta(...)``.
_CAS_THETA_RECIPE_RE = re.compile(
    r"(?:Θ|\bTheta)\s*\(\s*(?:Ω|Omega)"
)
# 5b. ``Recipe Theta(...) = ... -> Omega_X`` (free-form recipe surface).
#     Fires when both the Theta keyword AND a recipe arrow appear in the
#     prompt. Caught by the union of _CAS_THETA_RECIPE_RE and the named
#     emergent regex above.
# 5c. Coefficient-times-state pattern: ``0.53*^7^P``, ``2*^3``, ``1.0*^4^E``.
_CAS_COEFF_STATE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*\*\s*\^[0-9]"
)
# 6a. Meta-logic / set constructors (the category the v0 corpus FORGOT).
#     ``NoeticCluster{...}``, ``StateSet{...}``, ``RelationCluster{...}``,
#     ``Tuple(...)``, ``Coordinate(...)``, ``Product(...)``,
#     ``CoverOf(...)``, ``PartitionOf(...)``.
_CAS_META_CONSTRUCTOR_RE = re.compile(
    r"\b(?:NoeticCluster|StateSet|RelationCluster|Tuple|Coordinate|Product|"
    r"CoverOf|PartitionOf|ChainEntails|Involute|PrecedesDomain)\s*[\(\{]"
)
# 6b. ``let`` bindings — ``let X = ^3^P``, ``let cluster = NoeticCluster{...}``.
#     Conservative: only fire when ``let <ident> = ^...`` or ``let <ident> = <CAS-y RHS>``.
_CAS_LET_BINDING_RE = re.compile(
    r"\blet\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*"
    r"(?:\^[0-9]|NoeticCluster|StateSet|RelationCluster|Tuple|Coordinate|"
    r"Product|CoverOf|PartitionOf|Ω|Θ|Omega|Theta)"
)
# 6c. Membership / subset relations in CAS context — ``^3^P ∈ NoeticCluster``,
#     ``X ⊆ StateSet{...}``. ASCII fallbacks ``in`` / ``subset`` are too
#     generic to fire on alone — we cover only the unicode glyphs (already
#     in _CAS_OPERATOR_GLYPH_RE) plus explicit constructor co-occurrence.
# 6d. Diagram-export keywords (compiler surface form: ``diagram { ... }``,
#     ``DiagramOf``, ``export_diagram``).
_CAS_DIAGRAM_KEYWORD_RE = re.compile(
    r"\b(?:diagram\s*\{|DiagramOf|export_diagram)\b"
)
# 6e. RPM capability-pathway nodes — ``A0 -> D2 -> W2 -> P2``. Pure A0/Dn/Wn/Pn
#     tokens are too generic on their own (P2 could mean "page 2") so we only
#     fire when at least two distinct capability-pathway tokens co-occur with
#     an arrow (Unicode → or ASCII ->) between them. ``A0`` alone with an
#     arrow is also load-bearing (A0 is the unique Pure-Desire root).
_CAS_RPM_CHAIN_RE = re.compile(
    r"\b(?:A0|[DWP][1-7])\s*(?:→|->)\s*(?:A0|[DWP][1-7])\b"
)
# 7a. Cognitive Fractal angle-bracket sequence — ``⟨2:3:6⟩`` or
#     ``⟨k₁:k₂:⋯:kₙ⟩``. Each kᵢ is a Noetic index 0..9.
_CAS_FRACTAL_SEQ_UNICODE_RE = re.compile(
    r"⟨\s*[0-9](?:\s*[:∶]\s*[0-9])+\s*⟩"
)
# 7b. ASCII fallback — ``<k1:k2:k3>`` with digits only.
_CAS_FRACTAL_SEQ_ASCII_RE = re.compile(
    r"<\s*[0-9](?:\s*:\s*[0-9])+\s*>"
)
# 7c. X.Y.Z fractal composition — ``^5.^7.^2``, ``^a.^b`` Noetic dot chain.
_CAS_FRACTAL_DOTCHAIN_RE = re.compile(
    r"\^[0-9](?:(?:\^[PCEO])?\.\^[0-9])+"
)
# 7d. FractalClass / FractalConvergence / Cognitive Fractal keywords.
_CAS_FRACTAL_KEYWORD_RE = re.compile(
    r"\b(?:FractalClass|FractalConvergence|CognitiveFractal)\b"
)


# All CAS surface-token detectors, in evaluation order. The pre-filter
# returns True on the first match; ordering is informational only.
_CAS_SURFACE_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 1. State literals
    _CAS_STATE_LITERAL_RE,
    # 2. Drive subscripts
    _CAS_DRIVE_RE,
    # 3. Register tags (single + multi-register)
    _CAS_SINGLE_REGISTER_RE,
    _CAS_MULTI_REGISTER_UNICODE_RE,
    _CAS_MULTI_REGISTER_ASCII_RE,
    # 4. Operators / named omegas
    _CAS_OPERATOR_GLYPH_RE,
    _CAS_NAMED_OMEGA_RE,
    # 5. Production recipes
    _CAS_THETA_RECIPE_RE,
    _CAS_COEFF_STATE_RE,
    # 6. Meta-logic / set constructors / let / diagram
    _CAS_META_CONSTRUCTOR_RE,
    _CAS_LET_BINDING_RE,
    _CAS_DIAGRAM_KEYWORD_RE,
    _CAS_RPM_CHAIN_RE,
    # 7. Cognitive Fractal sequences / dot-chains / keywords
    _CAS_FRACTAL_SEQ_UNICODE_RE,
    _CAS_FRACTAL_SEQ_ASCII_RE,
    _CAS_FRACTAL_DOTCHAIN_RE,
    _CAS_FRACTAL_KEYWORD_RE,
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
        cas_surface_bypass: bool = True,
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
        self.cas_surface_bypass = bool(cas_surface_bypass)

    # ------------------------------------------------------------------
    # CAS surface-token pre-filter (Step E calibration)
    # ------------------------------------------------------------------

    @staticmethod
    def _has_cas_surface_tokens(prompt: str) -> bool:
        """Return True iff the prompt contains an unambiguous CAS surface token.

        The K=9 OOD detector flags prompts whose surface form falls outside
        its training distribution — including prompts that explicitly contain
        CAS notation (Θ recipes, named Ω targets, ⟨k₁:k₂:k₃⟩ fractal
        sequences, NoeticCluster{...} constructors, |⟨A,f,T⟩ register sets).
        Pre-calibration eval showed those buckets at 100% fail rate because
        the gate consulted the OOD verdict blindly and blocked pipeline
        entry. This helper deterministically detects CAS surface tokens
        across the seven required coverage categories:

          1. State literals (``^N`` and ``^N^D``).
          2. Drive subscripts (``F1``..``F7``, ``_{F1}``..``_{F7}``).
          3. Register tags (``|T``, ``|A``, ``|f``, ``|E``, plus
             multi-register ``|⟨A,f,T⟩`` / ``|<A,f,T>``).
          4. Operators (``Ω``, ``Θ``, ``∘``, ``→``, ``×``, ``⊗``, ``∈``,
             ``⊆``, ``∪``, ``∩``, ``∖``, ``⟨…⟩``, plus named ``Ω_<name>`` /
             ``Omega_<name>``).
          5. Production recipes (``Θ(Ω_X) = ...``, ``Theta(Omega_X) = ...``,
             coefficient-times-state ``0.53*^7^P``).
          6. Meta-logic / set constructors (``NoeticCluster``, ``StateSet``,
             ``RelationCluster``, ``Tuple``, ``Coordinate``, ``Product``,
             ``CoverOf``, ``PartitionOf``, plus relations like
             ``ChainEntails``, ``Involute``, ``PrecedesDomain``, plus
             ``let`` bindings and diagram keywords).
          7. Cognitive Fractal angle-bracket sequences (``⟨2:3:6⟩``,
             ``<2:3:6>``), X.Y.Z dot-chains (``^5.^7.^2``), and Fractal
             keywords (``FractalClass``, ``FractalConvergence``,
             ``CognitiveFractal``).

        Returns True on the first match — ordering is informational, not
        load-bearing. False positives (treating non-CAS as CAS) are
        cheap; false negatives (blocking real CAS) are not.
        """
        if not isinstance(prompt, str) or not prompt:
            return False
        for pattern in _CAS_SURFACE_TOKEN_PATTERNS:
            if pattern.search(prompt):
                return True
        return False

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

        # 0. CAS surface-token bypass (Step E calibration). The K=9 OOD
        #    detector over-fires on prompts that contain CAS notation it
        #    doesn't surface-match (Θ recipes, ⟨k₁:k₂:k₃⟩ fractal
        #    sequences, NoeticCluster{...}, |⟨A,f,T⟩, named Ω targets, …).
        #    When the prompt explicitly carries CAS surface tokens we route
        #    to the pipeline regardless of the OOD verdict — false-positive
        #    pipeline-entry is much cheaper than false-negative blocking of
        #    real CAS. The bypass is opt-out via ``cas_surface_bypass=False``
        #    so test suites can exercise the pure OOD-only logic path.
        if self.cas_surface_bypass and self._has_cas_surface_tokens(prompt):
            return GateResult(
                decision=RouteDecision.CAS_PIPELINE,
                canned_response=None,
                reason="cas_surface_tokens_detected",
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
