"""Tests for the multi-timeframe monitor — pure composition over the runtime."""

from __future__ import annotations

import pytest

from cas_forex.multi_timeframe_runtime import MultiTimeframeRuntime
from cas_forex.mtf_monitor import (
    MonitorSnapshot,
    SymbolMonitorSnapshot,
    TradeableSymbol,
    compose_monitor_snapshot,
    find_tradeable_symbols,
)


# ---------------------------------------------------------------------------
# Snapshot composition
# ---------------------------------------------------------------------------


def test_empty_runtime_yields_empty_snapshot():
    runtime = MultiTimeframeRuntime()
    snapshot = compose_monitor_snapshot(runtime)
    assert snapshot.symbols == ()


def test_snapshot_lists_symbols_in_sorted_order():
    runtime = MultiTimeframeRuntime()
    runtime.activate("USDJPY", "M5")
    runtime.activate("EURUSD", "H1")
    runtime.activate("GBPUSD", "D1")

    snapshot = compose_monitor_snapshot(runtime)

    assert [s.symbol for s in snapshot.symbols] == ["EURUSD", "GBPUSD", "USDJPY"]


def test_snapshot_carries_active_timeframes_per_symbol():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("EURUSD", "H1")

    snapshot = compose_monitor_snapshot(runtime)
    sym = snapshot.for_symbol("EURUSD")
    assert sym is not None
    assert sym.active_timeframes == frozenset({"M5", "H1"})


def test_snapshot_aggregates_only_active_timeframes_risk():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("EURUSD", "H1")

    snapshot = compose_monitor_snapshot(
        runtime,
        risk_by_symbol={
            "EURUSD": {
                "M5": 0.5,
                "H1": 1.0,
                "D1": 99.0,  # inactive — must be ignored
            }
        },
    )

    sym = snapshot.for_symbol("EURUSD")
    assert sym is not None
    assert sym.aggregated_risk.sum_risk == 1.5
    assert sym.aggregated_risk.max_risk == 1.0
    assert sym.aggregated_risk.contributing_timeframes == frozenset({"M5", "H1"})


def test_snapshot_signal_alignment_all_buy():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("EURUSD", "H1")

    snapshot = compose_monitor_snapshot(
        runtime,
        direction_by_symbol={"EURUSD": {"M5": "BUY", "H1": "BUY"}},
    )

    sym = snapshot.for_symbol("EURUSD")
    assert sym is not None
    assert sym.signal_alignment.alignment == "BUY"


def test_snapshot_signal_alignment_mixed():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("EURUSD", "H1")

    snapshot = compose_monitor_snapshot(
        runtime,
        direction_by_symbol={"EURUSD": {"M5": "BUY", "H1": "SELL"}},
    )

    sym = snapshot.for_symbol("EURUSD")
    assert sym is not None
    assert sym.signal_alignment.alignment == "MIXED"


def test_snapshot_signal_alignment_empty_when_no_inputs():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")

    snapshot = compose_monitor_snapshot(runtime)
    sym = snapshot.for_symbol("EURUSD")
    assert sym is not None
    assert sym.signal_alignment.alignment == "EMPTY"


def test_snapshot_missing_symbol_inputs_does_not_crash():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("GBPUSD", "H1")

    # Only supply input for one of two active symbols.
    snapshot = compose_monitor_snapshot(
        runtime,
        risk_by_symbol={"EURUSD": {"M5": 0.5}},
        direction_by_symbol={"EURUSD": {"M5": "BUY"}},
    )

    eurusd = snapshot.for_symbol("EURUSD")
    gbpusd = snapshot.for_symbol("GBPUSD")
    assert eurusd is not None and gbpusd is not None
    assert eurusd.signal_alignment.alignment == "BUY"
    assert gbpusd.signal_alignment.alignment == "EMPTY"
    assert gbpusd.aggregated_risk.sum_risk == 0.0


# ---------------------------------------------------------------------------
# Tradeable filter — "what should I trade right now?"
# ---------------------------------------------------------------------------


def test_tradeable_filter_skips_mixed_and_empty():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("EURUSD", "H1")
    runtime.activate("USDJPY", "M5")
    runtime.activate("USDJPY", "H1")
    runtime.activate("GBPUSD", "M5")

    snapshot = compose_monitor_snapshot(
        runtime,
        direction_by_symbol={
            "EURUSD": {"M5": "BUY", "H1": "BUY"},       # aligned BUY
            "USDJPY": {"M5": "BUY", "H1": "SELL"},      # MIXED — skip
            # GBPUSD has no input → EMPTY → skip
        },
        risk_by_symbol={
            "EURUSD": {"M5": 0.2, "H1": 0.3},
            "USDJPY": {"M5": 0.1, "H1": 0.1},
        },
    )

    tradeable = find_tradeable_symbols(snapshot, max_risk_per_symbol=1.0)
    assert [t.symbol for t in tradeable] == ["EURUSD"]
    assert tradeable[0].direction == "BUY"
    assert tradeable[0].aggregated_risk == pytest.approx(0.5)


def test_tradeable_filter_respects_risk_cap():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("EURUSD", "H1")

    snapshot = compose_monitor_snapshot(
        runtime,
        direction_by_symbol={"EURUSD": {"M5": "SELL", "H1": "SELL"}},
        risk_by_symbol={"EURUSD": {"M5": 0.6, "H1": 0.6}},  # sum 1.2
    )

    assert find_tradeable_symbols(snapshot, max_risk_per_symbol=1.0) == ()


def test_tradeable_filter_returns_all_aligned_within_budget():
    runtime = MultiTimeframeRuntime()
    runtime.activate("EURUSD", "M5")
    runtime.activate("GBPUSD", "H1")
    runtime.activate("USDJPY", "D1")

    snapshot = compose_monitor_snapshot(
        runtime,
        direction_by_symbol={
            "EURUSD": {"M5": "BUY"},
            "GBPUSD": {"H1": "SELL"},
            "USDJPY": {"D1": "BUY"},
        },
        risk_by_symbol={
            "EURUSD": {"M5": 0.3},
            "GBPUSD": {"H1": 0.4},
            "USDJPY": {"D1": 0.5},
        },
    )

    tradeable = find_tradeable_symbols(snapshot, max_risk_per_symbol=1.0)
    assert [t.symbol for t in tradeable] == ["EURUSD", "GBPUSD", "USDJPY"]
    assert {t.direction for t in tradeable} == {"BUY", "SELL"}


def test_tradeable_filter_preserves_sorted_order_from_snapshot():
    runtime = MultiTimeframeRuntime()
    runtime.activate("USDJPY", "M5")
    runtime.activate("EURUSD", "M5")
    runtime.activate("AUDUSD", "M5")

    snapshot = compose_monitor_snapshot(
        runtime,
        direction_by_symbol={
            "USDJPY": {"M5": "BUY"},
            "EURUSD": {"M5": "BUY"},
            "AUDUSD": {"M5": "BUY"},
        },
    )

    tradeable = find_tradeable_symbols(snapshot, max_risk_per_symbol=10.0)
    # Snapshot composes sorted; tradeable preserves that order.
    assert [t.symbol for t in tradeable] == ["AUDUSD", "EURUSD", "USDJPY"]
