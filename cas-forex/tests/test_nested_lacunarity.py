"""Tests for the nested-lacunarity bias-state map (CAS Forex piece b).

These are pure-measurement tests: no network, synthetic candles only. The most
important one is ``test_tf_alignment_excludes_forming_bar`` - the cardinal-sin
regression test that locks in the anti-lookahead TF-alignment guarantee. The
honest-expectation test (``test_cell_all_gaps_on_price_only``) would FAIL LOUDLY
if a future change ever manufactured a fake edge from price-only signals.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from cas_forex import nested_lacunarity as nl
from cas_forex import regime_sim
from cas_forex.edge_oos import EDGE_CLAIM_BOUNDARY
from cas_forex.nested_lacunarity import (
    TFCellResult,
    TimeframeAlignedView,
    build_gap_map,
    build_synthetic_grid,
    evaluate_cell_oos,
    find_fractal_coherent_cells,
    make_regime_gated_sub_signals,
    nested_lacunarity_tf,
    serialize_nested_lacunarity_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cell(**overrides) -> TFCellResult:
    data = dict(
        symbol="EUR/USD",
        timeframe="D1",
        time_scale="day",
        regime="trend_up",
        is_gap=True,
        verdict="NO_EDGE",
        cost_pips_tested=3.0,
        oos_windows=0,
        oos_trades=0,
        switch_total_return_pct=0.0,
        best_single_total_return_pct=0.0,
        null_total_return_pct=0.0,
        beats_single_window_rate=0.0,
        beats_null_window_rate=0.0,
        regime_detected_bars=0,
        gap_reason="no_oos_edge",
    )
    data.update(overrides)
    return TFCellResult(**data)


# ---------------------------------------------------------------------------
# Synthetic grid
# ---------------------------------------------------------------------------


def test_synthetic_grid_deterministic():
    symbols = ["EUR/USD"]
    timeframes = ["H1", "D1"]
    regimes = ["trend_up", "range", "trend_down"]
    g1 = build_synthetic_grid(symbols, timeframes, regimes, bars_per_regime=30, seed_base=11)
    g2 = build_synthetic_grid(symbols, timeframes, regimes, bars_per_regime=30, seed_base=11)

    # Byte-identical across two calls (deterministic).
    assert g1 == g2

    for tf in ("H1", "D1"):
        series = g1["EUR/USD"][tf]
        # Length == bars_per_regime * n_regimes.
        assert len(series) == 30 * len(regimes)
        # Close prices strictly positive.
        assert all(bar["close"] > 0 for bar in series)
        # Timestamps strictly increasing (advance by the TF's real duration).
        ts = [nl._parse_timestamp(b["timestamp"]) for b in series]
        assert all(b > a for a, b in zip(ts, ts[1:]))


# ---------------------------------------------------------------------------
# THE cardinal-sin regression test: no still-forming higher-TF bar can leak.
# ---------------------------------------------------------------------------


def test_tf_alignment_excludes_forming_bar():
    grid = build_synthetic_grid(["EUR/USD"], ["H1", "D1"], ["trend_up", "range"], bars_per_regime=40, seed_base=3)
    d1 = grid["EUR/USD"]["D1"]
    h1 = grid["EUR/USD"]["H1"]
    view = TimeframeAlignedView("D1", d1)

    d1_close_times = sorted(
        TimeframeAlignedView.bar_close_time(b["timestamp"], "D1") for b in d1
    )

    # For EVERY H1 decision time, every returned D1 bar must be already closed,
    # and the first still-forming D1 bar must NOT be returned.
    for bar in h1:
        decision_time = TimeframeAlignedView.bar_close_time(bar["timestamp"], "H1")
        closed = view.closed_higher_bars(decision_time)
        for cb in closed:
            assert TimeframeAlignedView.bar_close_time(cb["timestamp"], "D1") <= decision_time

        returned_close_times = {
            TimeframeAlignedView.bar_close_time(cb["timestamp"], "D1") for cb in closed
        }
        forming = [ct for ct in d1_close_times if ct > decision_time]
        if forming:
            first_forming = min(forming)
            # The first still-forming higher-TF bar is structurally excluded.
            assert first_forming not in returned_close_times

    # Exact-boundary case: a D1 bar closing EXACTLY at the decision instant IS
    # included; the same instant minus one second excludes it.
    target_close = TimeframeAlignedView.bar_close_time(d1[5]["timestamp"], "D1")
    at_boundary = view.closed_higher_bars(target_close)
    one_sec_before = view.closed_higher_bars(target_close - timedelta(seconds=1))
    assert len(at_boundary) == len(one_sec_before) + 1
    # The extra bar at the boundary is exactly the one closing at target_close.
    boundary_close_times = {
        TimeframeAlignedView.bar_close_time(b["timestamp"], "D1") for b in at_boundary
    }
    assert target_close in boundary_close_times


def test_tf_alignment_no_backdoor():
    grid = build_synthetic_grid(["EUR/USD"], ["D1"], ["trend_up"], bars_per_regime=20, seed_base=1)
    d1 = grid["EUR/USD"]["D1"]
    view = TimeframeAlignedView("D1", d1)

    # The only public read path is closed_higher_bars(); there is NO public
    # attribute or method that hands back the raw, unfiltered higher-TF list.
    public_names = [n for n in dir(view) if not n.startswith("_")]
    assert "closed_higher_bars" in public_names
    for forbidden in ("bars", "close_times", "candles", "raw", "higher_candles", "all_bars"):
        assert forbidden not in public_names
        assert not hasattr(view, forbidden)

    # The raw list lives under a name-mangled private attribute, not the public API.
    mangled = [n for n in dir(view) if "TimeframeAlignedView__" in n]
    assert any("bars" in n for n in mangled)
    # Sanity: the filtered API actually works and returns dict bars.
    last_decision = TimeframeAlignedView.bar_close_time(d1[-1]["timestamp"], "D1")
    out = view.closed_higher_bars(last_decision)
    assert out and all(isinstance(b, dict) for b in out)


# ---------------------------------------------------------------------------
# Causal regime gating
# ---------------------------------------------------------------------------


def test_regime_gated_signal_is_causal(monkeypatch):
    seen_lengths = []
    real_detect = regime_sim.detect_regime

    def spy_detect(closes, *args, **kwargs):
        seen_lengths.append(len(closes))
        return real_detect(closes, *args, **kwargs)

    # The gating closure imports detect_regime into the nested_lacunarity module
    # namespace, so patch it there.
    monkeypatch.setattr(nl, "detect_regime", spy_detect)

    captured = {}

    def base_signal(closes):
        captured["last_len"] = len(closes)
        return ("LONG", 0.6)

    gated = make_regime_gated_sub_signals({"x": base_signal}, "trend_up", detect_window=10)["x"]

    # Feed prefixes closes[:t+1] for growing t and assert detect_regime got exactly
    # that slice length each call (proving no future bars are consulted).
    closes = [1.0 + 0.001 * i for i in range(60)]
    for t in range(10, 60):
        seen_lengths.clear()
        gated(closes[: t + 1])
        assert seen_lengths, "detect_regime was not called"
        assert all(length == t + 1 for length in seen_lengths)


# ---------------------------------------------------------------------------
# Honest expected result: all gaps for price-only signals.
# ---------------------------------------------------------------------------


def test_cell_all_gaps_on_price_only():
    # A small but sufficient grid: 1 symbol x 2 timeframes, multi-regime so the
    # causal detector sees enough of the target regimes to actually run OOS.
    grid = build_synthetic_grid(
        ["EUR/USD"],
        ["H1", "D1"],
        ["trend_up", "trend_down", "range", "high_vol"],
        bars_per_regime=130,
        seed_base=7,
    )

    report = build_gap_map(
        grid,
        regimes=["trend_up", "range"],
        costs=(1.0, 2.0, 3.0),
        train_bars=120,
        test_bars=40,
        detect_window=40,
        n_null=3,
        min_cell_trades=30,
        min_regime_bars=20,
    )

    s = report.summary
    # Price-only signals clear nothing: the honest, expected bias-state.
    assert s["overall_gap_fraction"] == 1.0
    assert report.non_gap_cells == []
    assert report.fractal_coherent_cells == []
    assert s["bias_state_verdict"].startswith("ALL_GAPS")
    # Every cell is a gap with a precise, non-empty reason.
    assert s["total_cells"] == s["gap_cells"]
    assert all(c.is_gap for c in report.cells)
    assert all(c.gap_reason for c in report.cells)
    # The claim boundary is carried verbatim from edge_oos.
    assert report.claim_boundary == EDGE_CLAIM_BOUNDARY


# ---------------------------------------------------------------------------
# Nested roll-up keys + values
# ---------------------------------------------------------------------------


def test_nested_rollup_keys_and_values():
    cells = [
        _cell(symbol="EUR/USD", regime="trend_up", timeframe="H1", is_gap=False),
        _cell(symbol="EUR/USD", regime="trend_up", timeframe="D1", is_gap=True),
        _cell(symbol="EUR/USD", regime="range", timeframe="H1", is_gap=True),
        _cell(symbol="EUR/USD", regime="range", timeframe="D1", is_gap=True),
    ]

    lac = nested_lacunarity_tf(cells)

    # Documented key shape is present.
    assert "overall" in lac
    assert "symbol::EUR/USD" in lac
    assert "symbol::EUR/USD::regime::trend_up" in lac
    assert "symbol::EUR/USD::regime::trend_up::tf::H1" in lac  # leaf
    assert "tf::H1" in lac and "tf::D1" in lac                 # marginal

    # Single source of truth: overall == regime_sim.lacunarity(cells).
    assert lac["overall"] == regime_sim.lacunarity(cells)
    # Hand-computed fractions: 3 of 4 are gaps overall.
    assert lac["overall"] == 3 / 4
    # symbol::trend_up has one gap of two cells.
    assert lac["symbol::EUR/USD::regime::trend_up"] == 1 / 2
    # Leaf H1/trend_up is the single non-gap cell.
    assert lac["symbol::EUR/USD::regime::trend_up::tf::H1"] == 0.0
    # Marginal H1 across both regimes: H1 has one gap of two -> 0.5.
    assert lac["tf::H1"] == 1 / 2
    assert lac["tf::D1"] == 1.0


# ---------------------------------------------------------------------------
# Fractal-coherence detection
# ---------------------------------------------------------------------------


def test_fractal_coherent_detection():
    cells = [
        # (EUR/USD, trend_up) non-gap at BOTH M15 and H1 -> fractal-coherent.
        _cell(symbol="EUR/USD", regime="trend_up", timeframe="M15", time_scale="minute", is_gap=False),
        _cell(symbol="EUR/USD", regime="trend_up", timeframe="H1", time_scale="hour", is_gap=False),
        # (EUR/USD, range) non-gap at ONLY D1 -> single-scale, excluded.
        _cell(symbol="EUR/USD", regime="range", timeframe="D1", is_gap=False),
        # noise gaps
        _cell(symbol="EUR/USD", regime="range", timeframe="H1", is_gap=True),
    ]

    coherent = find_fractal_coherent_cells(cells, min_timeframes=2)

    assert len(coherent) == 1
    entry = coherent[0]
    assert entry["symbol"] == "EUR/USD"
    assert entry["regime"] == "trend_up"
    assert entry["timeframes"] == ["H1", "M15"]  # sorted
    assert entry["n_timeframes"] == 2


# ---------------------------------------------------------------------------
# Gates: min_regime_bars / min_trades / insufficient_history.
# ---------------------------------------------------------------------------


def test_min_regime_bars_and_min_trades_gates():
    # A short single-regime series where the *target* regime ("shock") barely
    # occurs under the causal detector -> the cell must be a gap, never a silent
    # CANDIDATE_EDGE.
    grid = build_synthetic_grid(
        ["EUR/USD"],
        ["D1"],
        ["range"],
        bars_per_regime=220,
        seed_base=2,
    )
    candles = grid["EUR/USD"]["D1"]

    cell = evaluate_cell_oos(
        "EUR/USD",
        candles,
        "shock",            # a regime that barely occurs in a pure range series
        "D1",
        costs=(1.0, 2.0, 3.0),
        train_bars=120,
        test_bars=40,
        detect_window=40,
        n_null=3,
        min_cell_trades=30,
        min_regime_bars=20,
    )

    assert cell.is_gap is True
    assert cell.gap_reason in {
        "insufficient_regime_bars",
        "insufficient_history",
        "insufficient_trades",
        "no_oos_edge",
    }
    assert cell.verdict != "CANDIDATE_EDGE"


# ---------------------------------------------------------------------------
# Serialization round-trips.
# ---------------------------------------------------------------------------


def test_serialize_round_trips():
    cells = [
        _cell(symbol="EUR/USD", regime="trend_up", timeframe="H1", is_gap=False),
        _cell(symbol="EUR/USD", regime="range", timeframe="D1", is_gap=True),
    ]
    levels = nested_lacunarity_tf(cells)
    fractal = find_fractal_coherent_cells(cells, min_timeframes=2)
    report = nl.NestedLacunarityReport(
        cells=cells,
        gap_fraction_per_level=levels,
        non_gap_cells=[c for c in cells if not c.is_gap],
        fractal_coherent_cells=fractal,
        summary=nl._summarize_map(cells, levels, fractal),
    )

    payload = serialize_nested_lacunarity_report(report)
    # JSON-serializable (no exceptions).
    text = json.dumps(payload)
    assert text
    # Carries the claim boundary verbatim and the full nested level map.
    assert payload["claim_boundary"] == EDGE_CLAIM_BOUNDARY
    assert payload["summary"]["claim_boundary"] == EDGE_CLAIM_BOUNDARY
    assert payload["gap_fraction_per_level"]["overall"] == regime_sim.lacunarity(cells)
    assert "tf::H1" in payload["gap_fraction_per_level"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
