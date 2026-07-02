"""Tests for the MultiTimeframeRuntime skeleton."""

from __future__ import annotations

import pytest

from cas_forex.multi_timeframe_runtime import (
    CANONICAL_TIMEFRAMES,
    AggregatedRisk,
    MultiTimeframeRuntime,
    SignalAlignment,
    TimeframeKey,
    TimeframeSelection,
    UnknownTimeframeError,
)


def test_empty_state_returns_empty_frozenset() -> None:
    rt = MultiTimeframeRuntime()
    assert rt.active_timeframes_for("EURUSD") == frozenset()
    assert rt.all_active() == {}


def test_single_timeframe_activation() -> None:
    rt = MultiTimeframeRuntime()
    rt.activate("EURUSD", "M5")
    assert rt.active_timeframes_for("EURUSD") == frozenset({"M5"})
    sel = rt.selection_for("EURUSD")
    assert isinstance(sel, TimeframeSelection)
    assert sel.symbol == "EURUSD"
    assert sel.active_timeframes == frozenset({"M5"})


def test_multiple_timeframes_active_per_symbol() -> None:
    rt = MultiTimeframeRuntime()
    rt.activate("EURUSD", "M5")
    rt.activate("EURUSD", "H1")
    rt.activate("EURUSD", "H4")
    # Re-activation is idempotent.
    rt.activate("EURUSD", "M5")
    rt.activate("GBPUSD", "D1")

    assert rt.active_timeframes_for("EURUSD") == frozenset({"M5", "H1", "H4"})
    assert rt.active_timeframes_for("GBPUSD") == frozenset({"D1"})

    snapshot = rt.all_active()
    assert snapshot == {
        "EURUSD": frozenset({"M5", "H1", "H4"}),
        "GBPUSD": frozenset({"D1"}),
    }


def test_state_path_persists_active_timeframes_across_runtime_restart(tmp_path) -> None:
    state_path = tmp_path / "multi-timeframe-runtime.json"
    rt = MultiTimeframeRuntime(state_path)
    rt.activate("NAS100", "D1")
    rt.activate("NAS100", "H1")
    rt.activate("US30", "M15")

    reloaded = MultiTimeframeRuntime(state_path)

    assert reloaded.active_timeframes_for("NAS100") == frozenset({"D1", "H1"})
    assert reloaded.active_timeframes_for("US30") == frozenset({"M15"})

    reloaded.deactivate("NAS100", "H1")
    reloaded_again = MultiTimeframeRuntime(state_path)

    assert reloaded_again.active_timeframes_for("NAS100") == frozenset({"D1"})
    assert reloaded_again.active_timeframes_for("US30") == frozenset({"M15"})


def test_deactivate_removes_only_target_timeframe() -> None:
    rt = MultiTimeframeRuntime()
    rt.activate("EURUSD", "M5")
    rt.activate("EURUSD", "H1")
    rt.activate("EURUSD", "H4")

    rt.deactivate("EURUSD", "H1")
    assert rt.active_timeframes_for("EURUSD") == frozenset({"M5", "H4"})

    # Deactivating something not active is a no-op.
    rt.deactivate("EURUSD", "D1")
    assert rt.active_timeframes_for("EURUSD") == frozenset({"M5", "H4"})

    # Deactivating an unknown symbol is a no-op.
    rt.deactivate("UNKNOWN_PAIR", "M5")

    # Drain the symbol; once empty it disappears from all_active.
    rt.deactivate("EURUSD", "M5")
    rt.deactivate("EURUSD", "H4")
    assert rt.active_timeframes_for("EURUSD") == frozenset()
    assert "EURUSD" not in rt.all_active()


def test_aggregate_risk_uses_active_only_with_sum_and_max() -> None:
    rt = MultiTimeframeRuntime()
    rt.activate("EURUSD", "M5")
    rt.activate("EURUSD", "H1")

    # H4 is in the input but NOT active — must be ignored.
    result = rt.aggregate_risk(
        "EURUSD",
        {"M5": 0.25, "H1": 0.75, "H4": 99.0},
    )
    assert isinstance(result, AggregatedRisk)
    assert result.symbol == "EURUSD"
    assert result.sum_risk == pytest.approx(1.0)
    assert result.max_risk == pytest.approx(0.75)
    assert result.contributing_timeframes == frozenset({"M5", "H1"})

    # Symbol with no active TFs → zero aggregate, empty contributors.
    empty = rt.aggregate_risk("GBPUSD", {"M5": 1.0})
    assert empty.sum_risk == 0.0
    assert empty.max_risk == 0.0
    assert empty.contributing_timeframes == frozenset()


def test_signals_align_buy_sell_mixed_and_empty() -> None:
    rt = MultiTimeframeRuntime()
    rt.activate("EURUSD", "M5")
    rt.activate("EURUSD", "H1")
    rt.activate("EURUSD", "H4")

    # All-BUY (case-insensitive).
    buy = rt.signals_align(
        "EURUSD",
        {"M5": "BUY", "H1": "buy", "H4": "Buy"},
    )
    assert isinstance(buy, SignalAlignment)
    assert buy.alignment == "BUY"
    assert buy.votes == {"M5": "BUY", "H1": "BUY", "H4": "BUY"}

    # All-SELL.
    sell = rt.signals_align(
        "EURUSD",
        {"M5": "SELL", "H1": "SELL", "H4": "SELL"},
    )
    assert sell.alignment == "SELL"

    # Mixed votes → MIXED.
    mixed = rt.signals_align(
        "EURUSD",
        {"M5": "BUY", "H1": "SELL", "H4": "BUY"},
    )
    assert mixed.alignment == "MIXED"

    # No active TF supplied a vote → EMPTY (D1 not active here).
    empty = rt.signals_align("EURUSD", {"D1": "BUY"})
    assert empty.alignment == "EMPTY"
    assert empty.votes == {}

    # Unknown direction labels collapse to MIXED rather than being dropped.
    weird = rt.signals_align(
        "EURUSD",
        {"M5": "BUY", "H1": "HOLD", "H4": "BUY"},
    )
    assert weird.alignment == "MIXED"
    assert weird.votes["H1"] == "HOLD"


def test_unknown_timeframe_is_rejected_with_clear_error() -> None:
    rt = MultiTimeframeRuntime()
    with pytest.raises(UnknownTimeframeError) as exc_info:
        rt.activate("EURUSD", "M3")
    msg = str(exc_info.value)
    assert "M3" in msg
    # Error message must enumerate the canonical set so the operator can
    # see what was expected.
    for canonical in CANONICAL_TIMEFRAMES:
        assert canonical in msg

    with pytest.raises(UnknownTimeframeError):
        rt.deactivate("EURUSD", "M2")

    rt.activate("EURUSD", "M5")
    with pytest.raises(UnknownTimeframeError):
        rt.aggregate_risk("EURUSD", {"M5": 1.0, "BOGUS_TF": 2.0})
    with pytest.raises(UnknownTimeframeError):
        rt.signals_align("EURUSD", {"BOGUS_TF": "BUY"})


def test_timeframe_key_enum_matches_canonical_set() -> None:
    enum_values = {member.value for member in TimeframeKey}
    assert enum_values == CANONICAL_TIMEFRAMES
    # Enum values must be usable as activate() inputs (string-valued enum).
    rt = MultiTimeframeRuntime()
    rt.activate("EURUSD", TimeframeKey.H1.value)
    assert rt.active_timeframes_for("EURUSD") == frozenset({"H1"})
