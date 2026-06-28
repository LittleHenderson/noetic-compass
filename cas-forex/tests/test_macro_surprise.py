"""Tests for the macro-surprise new-information cell.

Two obligations for any honest measurement instrument:
  DISCIPLINE: on pure noise it must report NO_SKILL (not be fooled).
  POWER:      on a planted real signal it must report CANDIDATE_EDGE (can detect).
Plus the anti-lookahead guarantees.
"""

from __future__ import annotations

from cas_forex.macro_surprise import (
    MacroEvent,
    causal_standardized_surprises,
    evaluate_macro_surprise,
    post_release_return,
    synthetic_events_and_candles,
)


def test_discipline_noise_is_no_skill():
    events, candles = synthetic_events_and_candles(mode="noise", n_events=80, seed=1)
    rep = evaluate_macro_surprise(events, candles, symbol="EUR/USD", horizon_bars=4, cost_pips=1.0, seed=5)
    assert rep.summary["verdict"] == "NO_SKILL"
    assert not rep.summary.get("beats_null_p95", False)


def test_power_planted_signal_is_candidate_edge():
    # A strong planted surprise->move link the instrument must be able to detect.
    events, candles = synthetic_events_and_candles(
        mode="signal", n_events=80, effect=0.004, noise=0.0008, seed=2
    )
    rep = evaluate_macro_surprise(events, candles, symbol="EUR/USD", horizon_bars=4, cost_pips=1.0, seed=5)
    assert rep.summary["verdict"] == "CANDIDATE_EDGE"
    assert rep.summary["beats_null_p95"] is True
    assert rep.summary["hit_rate"] > 0.5


def test_underpowered_small_sample():
    events, candles = synthetic_events_and_candles(mode="signal", n_events=10, seed=4)
    rep = evaluate_macro_surprise(events, candles, symbol="EUR/USD", min_test_events=8, seed=5)
    assert rep.summary["verdict"] == "UNDERPOWERED"


def test_causal_surprise_is_prefix_stable():
    """An event's standardized surprise must not depend on any later event."""
    events, _ = synthetic_events_and_candles(mode="signal", n_events=40, seed=7)
    full = causal_standardized_surprises(events, min_history=6)
    prefix = causal_standardized_surprises(events[:20], min_history=6)
    # The first 20 scores are identical whether or not later events exist.
    assert full[:20] == prefix


def test_post_release_return_is_strictly_after_release():
    candles = [
        {"timestamp": "2026-01-01T00:00:00+00:00", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1},
        {"timestamp": "2026-01-01T00:01:00+00:00", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1},
        {"timestamp": "2026-01-01T00:02:00+00:00", "open": 1.0, "high": 1.1, "low": 1.0, "close": 1.1, "volume": 1},
        {"timestamp": "2026-01-01T00:03:00+00:00", "open": 1.1, "high": 1.2, "low": 1.1, "close": 1.2, "volume": 1},
    ]
    # Release at 00:01 -> entry is the 00:01 bar (close 1.0), exit 2 bars later (00:03, close 1.2).
    res = post_release_return(candles, "2026-01-01T00:01:00+00:00", horizon_bars=2)
    assert res is not None
    entry, ret = res
    assert entry == 1.0
    assert abs(ret - 0.2) < 1e-9
    # Pre-release price history cannot affect the post-release move: a release after
    # the last usable bar yields no window.
    assert post_release_return(candles, "2026-01-01T00:03:00+00:00", horizon_bars=2) is None
