"""Multi-Timeframe Monitor — pure-function snapshot composer.

Sits one level above ``MultiTimeframeRuntime``: given the runtime's current
active-timeframe state plus per-(symbol, tf) direction and risk inputs from
upstream feeds, produces a per-symbol snapshot of aggregated risk and signal
alignment, and identifies which symbols are currently tradeable.

The monitor is deliberately pure:
- It does NOT subscribe to candle feeds.
- It does NOT compute direction (BUY/SELL) — that's MTFA's job upstream.
- It does NOT call the broker.

Its job is to orchestrate the runtime's aggregation helpers across every
active symbol and return a single composed snapshot the bot, the LLM, and
the UI can render. This keeps the wiring testable in-memory and lets
upstream feed implementations evolve independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

from cas_forex.multi_timeframe_runtime import (
    AggregatedRisk,
    MultiTimeframeRuntime,
    SignalAlignment,
)


@dataclass(frozen=True)
class SymbolMonitorSnapshot:
    """Per-symbol monitor snapshot composed from runtime + upstream inputs."""

    symbol: str
    active_timeframes: frozenset[str]
    aggregated_risk: AggregatedRisk
    signal_alignment: SignalAlignment


@dataclass(frozen=True)
class MonitorSnapshot:
    """Whole-monitor snapshot. ``symbols`` is sorted by symbol for stable
    rendering."""

    symbols: Tuple[SymbolMonitorSnapshot, ...]

    def for_symbol(self, symbol: str) -> SymbolMonitorSnapshot | None:
        for snap in self.symbols:
            if snap.symbol == symbol:
                return snap
        return None


@dataclass(frozen=True)
class TradeableSymbol:
    """A symbol whose active timeframes agree on direction and whose
    aggregated risk fits within the operator's per-symbol cap."""

    symbol: str
    direction: str  # "BUY" or "SELL"
    aggregated_risk: float
    active_timeframes: frozenset[str]


def compose_monitor_snapshot(
    runtime: MultiTimeframeRuntime,
    *,
    risk_by_symbol: Mapping[str, Mapping[str, float]] | None = None,
    direction_by_symbol: Mapping[str, Mapping[str, str]] | None = None,
) -> MonitorSnapshot:
    """Compose a snapshot across every symbol with at least one active TF.

    Inputs are dicts keyed by symbol then by timeframe. Missing entries are
    treated as "no input" (consistent with runtime semantics: an active TF
    that supplies no risk number does not count as zero — it simply does
    not contribute). Inactive TFs in the input are ignored even if present.

    Symbols are emitted in sorted order so downstream rendering is stable.
    """
    risk_by_symbol = risk_by_symbol or {}
    direction_by_symbol = direction_by_symbol or {}

    snapshots = []
    for symbol in sorted(runtime.all_active().keys()):
        active_tfs = runtime.active_timeframes_for(symbol)
        risk_input = risk_by_symbol.get(symbol, {})
        direction_input = direction_by_symbol.get(symbol, {})
        snapshots.append(
            SymbolMonitorSnapshot(
                symbol=symbol,
                active_timeframes=active_tfs,
                aggregated_risk=runtime.aggregate_risk(symbol, risk_input),
                signal_alignment=runtime.signals_align(symbol, direction_input),
            )
        )
    return MonitorSnapshot(symbols=tuple(snapshots))


def find_tradeable_symbols(
    snapshot: MonitorSnapshot,
    *,
    max_risk_per_symbol: float,
) -> Tuple[TradeableSymbol, ...]:
    """Filter the snapshot to symbols that are currently tradeable.

    A symbol is tradeable when:
      - every voting active TF agrees on direction (alignment ∈ {BUY, SELL}),
        AND
      - the aggregated sum of per-TF risk is within ``max_risk_per_symbol``.

    MIXED and EMPTY alignments are skipped. Symbols whose aggregated risk
    exceeds the cap are skipped. The result is in the same sorted order as
    the snapshot so the bot can report "what's tradeable right now" with
    stable ordering.
    """
    tradeable = []
    for sym_snap in snapshot.symbols:
        alignment = sym_snap.signal_alignment.alignment
        if alignment not in ("BUY", "SELL"):
            continue
        if sym_snap.aggregated_risk.sum_risk > max_risk_per_symbol:
            continue
        tradeable.append(
            TradeableSymbol(
                symbol=sym_snap.symbol,
                direction=alignment,
                aggregated_risk=sym_snap.aggregated_risk.sum_risk,
                active_timeframes=sym_snap.active_timeframes,
            )
        )
    return tuple(tradeable)
