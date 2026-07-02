"""Multi-Timeframe Runtime for CAS Forex.

Runtime skeleton that lets operators (a) pick/change the active timeframe(s)
per symbol and (b) trade multiple timeframes concurrently against the same
symbol. This is a pure in-memory state container plus aggregation helpers —
no I/O, no broker calls, no HTTP. The intent is to give the bot, the UI, and
the API a single source of truth for "which timeframes are live for which
symbol" and to surface aggregate risk + signal alignment across them.

Designed to interoperate with ``cas_forex.mtfa`` (which owns the analytics
for a single MTFA style) but does not depend on a specific trading style.
The runtime is style-agnostic: any subset of the canonical timeframes can be
active for any symbol, in any combination.

Public surface:
    CANONICAL_TIMEFRAMES        — the validated timeframe vocabulary.
    TimeframeKey                — Enum form of CANONICAL_TIMEFRAMES.
    TimeframeSelection          — (symbol, active_timeframes) snapshot record.
    AggregatedRisk              — (symbol, sum_risk, max_risk, contributing_timeframes).
    SignalAlignment             — (symbol, alignment, votes).
    UnknownTimeframeError       — raised when an unknown timeframe is supplied.
    MultiTimeframeRuntime       — the runtime state container.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Literal, Mapping, MutableMapping

# Canonical timeframe vocabulary for the runtime. Kept as a tuple so the
# ordering is stable for display and so the set is immutable. We intentionally
# accept a slightly smaller set than ``mtfa.TF_HIERARCHY``: the runtime is
# scoped to actively-traded timeframes (M1..D1) per the 2026-06-21 spec; W1/MN
# remain analytical-only in ``mtfa`` and are not runtime-selectable here.
CANONICAL_TIMEFRAMES: frozenset[str] = frozenset(
    {"M1", "M5", "M15", "H1", "H4", "D1"}
)


class TimeframeKey(str, Enum):
    """Enum mirror of :data:`CANONICAL_TIMEFRAMES`.

    String-valued so ``TimeframeKey.M1 == "M1"`` holds and the enum values
    interoperate directly with the timeframe strings used elsewhere in the
    codebase (``mtfa.tf_minutes``, broker bridge, etc.).
    """

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class UnknownTimeframeError(ValueError):
    """Raised when a caller supplies a timeframe outside the canonical set."""


def _validate_timeframe(tf: str) -> str:
    """Return ``tf`` if canonical, else raise :class:`UnknownTimeframeError`.

    The error message lists the canonical set so the operator can see what
    was expected. This is the single chokepoint for timeframe validation in
    the runtime.
    """
    if tf not in CANONICAL_TIMEFRAMES:
        allowed = ", ".join(sorted(CANONICAL_TIMEFRAMES))
        raise UnknownTimeframeError(
            f"Unknown timeframe {tf!r}; expected one of: {allowed}"
        )
    return tf


@dataclass(frozen=True)
class TimeframeSelection:
    """Snapshot of which timeframes are active for one symbol.

    Frozen so it is safe to hand back to callers from query methods without
    risk of external mutation leaking back into the runtime.
    """

    symbol: str
    active_timeframes: frozenset[str]


@dataclass(frozen=True)
class AggregatedRisk:
    """Aggregate risk across the active timeframes for a symbol.

    ``sum_risk`` is the simple total of the contributing per-TF risk numbers
    (intended for risk-pct or floating-pnl style scalars). ``max_risk`` is
    the largest single per-TF contribution. ``contributing_timeframes`` is
    the subset of active TFs that actually had a value in the input mapping.
    """

    symbol: str
    sum_risk: float
    max_risk: float
    contributing_timeframes: frozenset[str]


AlignmentLabel = Literal["BUY", "SELL", "MIXED", "EMPTY"]


@dataclass(frozen=True)
class SignalAlignment:
    """Whether the active timeframes for a symbol agree on direction.

    ``votes`` is the per-TF direction map restricted to currently-active TFs
    that supplied a vote. ``alignment`` is the aggregate verdict:

    - ``BUY``  — every voting active TF voted BUY.
    - ``SELL`` — every voting active TF voted SELL.
    - ``MIXED`` — the voting active TFs disagreed (or voted something else).
    - ``EMPTY`` — no active TF for this symbol cast a vote.
    """

    symbol: str
    alignment: AlignmentLabel
    votes: Mapping[str, str]


class MultiTimeframeRuntime:
    """In-memory registry of per-symbol active timeframes.

    The runtime is intentionally minimal: it does NOT subscribe to candles,
    does NOT run analytics, and does NOT touch a broker. It is the shared
    state that lets the bot, the UI, and the API ask and answer the same
    two questions:

      1. Which timeframes are currently active for symbol X?
      2. Given per-TF risk numbers / signals from elsewhere, what is the
         aggregate picture across the active TFs for symbol X?

    Concurrency: this class is not thread-safe. If multiple threads need
    to mutate, callers should lock externally. Single-threaded async use
    (the expected case) is fine.
    """

    def __init__(self, state_path: str | Path | None = None) -> None:
        # symbol -> mutable set of active timeframe strings
        self._state: MutableMapping[str, set[str]] = {}
        self._state_path = Path(state_path) if state_path is not None else None
        self._load_state()

    # ---- mutation -------------------------------------------------------

    def activate(self, symbol: str, timeframe: str) -> None:
        """Mark ``timeframe`` active for ``symbol``.

        Idempotent: activating a timeframe that is already active is a
        no-op. Raises :class:`UnknownTimeframeError` for unknown TFs.
        """
        tf = _validate_timeframe(timeframe)
        self._state.setdefault(symbol, set()).add(tf)
        self._persist_state()

    def deactivate(self, symbol: str, timeframe: str) -> None:
        """Mark ``timeframe`` inactive for ``symbol``.

        Idempotent: deactivating a timeframe that wasn't active is a
        no-op. Raises :class:`UnknownTimeframeError` for unknown TFs.
        If the symbol's set becomes empty, the symbol key is dropped so
        :meth:`all_active` stays tidy.
        """
        tf = _validate_timeframe(timeframe)
        bucket = self._state.get(symbol)
        if not bucket:
            return
        bucket.discard(tf)
        if not bucket:
            self._state.pop(symbol, None)
        self._persist_state()

    # ---- queries --------------------------------------------------------

    def active_timeframes_for(self, symbol: str) -> frozenset[str]:
        """Return the active timeframes for ``symbol`` (empty if none)."""
        return frozenset(self._state.get(symbol, ()))

    def all_active(self) -> Mapping[str, frozenset[str]]:
        """Return a snapshot of all symbols with at least one active TF."""
        return {sym: frozenset(tfs) for sym, tfs in self._state.items()}

    def selection_for(self, symbol: str) -> TimeframeSelection:
        """Return a :class:`TimeframeSelection` snapshot for ``symbol``."""
        return TimeframeSelection(
            symbol=symbol,
            active_timeframes=self.active_timeframes_for(symbol),
        )

    # ---- aggregation ----------------------------------------------------

    def aggregate_risk(
        self,
        symbol: str,
        per_timeframe_risk: Mapping[str, float],
    ) -> AggregatedRisk:
        """Aggregate per-TF risk across the currently-active TFs.

        Inactive TFs are ignored even if present in ``per_timeframe_risk``.
        Active TFs that are absent from the input mapping simply do not
        contribute (they are not treated as zero — they are not counted).

        Returns sum and max of the contributing values. With no
        contributions, sum and max are both ``0.0`` and
        ``contributing_timeframes`` is empty.

        Unknown timeframes in ``per_timeframe_risk`` raise
        :class:`UnknownTimeframeError` — this catches operator typos
        before they silently produce wrong aggregates.
        """
        active = self.active_timeframes_for(symbol)
        contributions: Dict[str, float] = {}
        for tf, value in per_timeframe_risk.items():
            _validate_timeframe(tf)
            if tf in active:
                contributions[tf] = float(value)

        if contributions:
            sum_risk = float(sum(contributions.values()))
            max_risk = float(max(contributions.values()))
        else:
            sum_risk = 0.0
            max_risk = 0.0

        return AggregatedRisk(
            symbol=symbol,
            sum_risk=sum_risk,
            max_risk=max_risk,
            contributing_timeframes=frozenset(contributions.keys()),
        )

    def signals_align(
        self,
        symbol: str,
        per_timeframe_direction: Mapping[str, str],
    ) -> SignalAlignment:
        """Determine whether active TFs for ``symbol`` agree on direction.

        ``per_timeframe_direction`` values are compared case-insensitively
        and normalised to upper-case in the returned ``votes``. Recognised
        directions are ``BUY`` and ``SELL``; anything else is preserved in
        ``votes`` but causes the alignment to be ``MIXED`` (so unknown vote
        values are conservatively treated as disagreement rather than
        silently dropped).

        Inactive TFs are ignored even if present in the input mapping.
        Unknown timeframes in the input raise :class:`UnknownTimeframeError`.
        """
        active = self.active_timeframes_for(symbol)
        votes: Dict[str, str] = {}
        for tf, direction in per_timeframe_direction.items():
            _validate_timeframe(tf)
            if tf in active:
                votes[tf] = str(direction).upper()

        if not votes:
            alignment: AlignmentLabel = "EMPTY"
        else:
            unique = set(votes.values())
            if unique == {"BUY"}:
                alignment = "BUY"
            elif unique == {"SELL"}:
                alignment = "SELL"
            else:
                alignment = "MIXED"

        return SignalAlignment(
            symbol=symbol,
            alignment=alignment,
            votes=votes,
        )

    # ---- durability -----------------------------------------------------

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            return
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        symbols = payload.get("symbols") if isinstance(payload, Mapping) else None
        if not isinstance(symbols, Mapping):
            return
        loaded: MutableMapping[str, set[str]] = {}
        for symbol, timeframes in symbols.items():
            if not isinstance(symbol, str) or not isinstance(timeframes, list):
                continue
            valid = {tf for tf in timeframes if isinstance(tf, str) and tf in CANONICAL_TIMEFRAMES}
            if valid:
                loaded[symbol] = valid
        self._state = loaded

    def _persist_state(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "report_kind": "cas_forex_multi_timeframe_runtime",
            "symbols": {
                symbol: sorted(timeframes)
                for symbol, timeframes in sorted(self._state.items())
                if timeframes
            },
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = f"{self._state_path.suffix}.{os.getpid()}.{threading.get_ident()}.tmp"
        tmp = self._state_path.with_suffix(suffix)
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self._state_path)


__all__ = [
    "CANONICAL_TIMEFRAMES",
    "TimeframeKey",
    "TimeframeSelection",
    "AggregatedRisk",
    "SignalAlignment",
    "UnknownTimeframeError",
    "MultiTimeframeRuntime",
]
