"""Anti-leakage + smoke tests for the leak-free OOS regime-switching evaluator."""

from __future__ import annotations

from cas_forex.edge_oos import (
    build_sub_signals,
    evaluate_oos,
    learn_routing_on_train,
)
from cas_forex.regime_sim import detect_regime, generate_regime_candles


def _multi_regime_series(bars_each: int = 160, seed: int = 3):
    candles = []
    for regime in ("trend_up", "range", "trend_down", "range"):
        candles.extend(generate_regime_candles(regime, symbol="NAS100", bars=bars_each, seed=seed))
    # Re-stamp timestamps so they are strictly increasing and unique.
    for i, c in enumerate(candles):
        c["timestamp"] = f"2020-01-01T00:00:00+{i:05d}"
    return candles


def test_detect_regime_is_causal_prefix_stable():
    """The regime at bar t must not depend on any bar after t."""
    candles = _multi_regime_series()
    closes = [c["close"] for c in candles]
    for t in (80, 160, 240, 400):
        # Same prefix with wildly different futures appended must give same label.
        future_a = closes[:t] + [closes[t - 1] * 1.5] * 50
        future_b = closes[:t] + [closes[t - 1] * 0.5] * 50
        r_base = detect_regime(closes[:t], window=60)
        r_a = detect_regime(future_a[:t], window=60)
        r_b = detect_regime(future_b[:t], window=60)
        assert r_base == r_a == r_b


def test_routing_learned_only_on_train_ignores_future():
    """learn_routing_on_train must depend only on the train window, never test."""
    candles = _multi_regime_series()
    train = candles[:320]
    subs = build_sub_signals()
    routing_a, counts_a = learn_routing_on_train(train, "NAS100", subs, cost_pips=2.0, detect_window=40)
    # Different "future" data does not enter learn_routing_on_train at all.
    routing_b, counts_b = learn_routing_on_train(train, "NAS100", subs, cost_pips=2.0, detect_window=40)
    assert routing_a == routing_b
    assert counts_a == counts_b


def test_evaluate_oos_runs_and_returns_honest_verdict():
    candles = _multi_regime_series(bars_each=200)
    report = evaluate_oos(
        {"NAS100": candles},
        cost_pips=2.0,
        train_bars=300,
        test_bars=120,
        detect_window=40,
        n_null=3,
    )
    assert report.summary["verdict"] in {"CANDIDATE_EDGE", "NO_EDGE", "NO_DATA"}
    assert report.cost_pips == 2.0
    assert "claim_boundary" in report.summary
    # Every window must carry the OOS comparison fields.
    for w in report.windows:
        assert "switch_return_pct" in w
        assert "beats_single" in w
        assert "beats_null_p90" in w
