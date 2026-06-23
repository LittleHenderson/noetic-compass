from datetime import UTC, datetime, timedelta

from cas_forex.condition_lab import build_strategy_settings, condition_label_for_candles
from cas_forex.event_context import manual_event_window
from cas_forex.regime_sim import generate_regime_candles
from cas_forex.walk_forward import (
    evaluate_walk_forward_routes,
    required_context_bars,
    serialize_walk_forward_report,
    split_walk_forward_ranges,
)


def test_split_walk_forward_ranges_uses_untouched_future_window():
    ranges = split_walk_forward_ranges(500, train_bars=200, test_bars=75, step_bars=75)

    assert ranges[0] == (0, 200, 200, 275)
    assert ranges[1] == (75, 275, 275, 350)
    assert all(train_end == test_start for _, train_end, test_start, _ in ranges)


def test_condition_label_for_candles_uses_baseline_vol_bucket():
    baseline = generate_regime_candles("range", symbol="NAS100", bars=120, seed=10, vol_mult=0.2)
    shock = generate_regime_candles("shock", symbol="NAS100", bars=120, seed=11, vol_mult=3.0)

    regime, vol_mult = condition_label_for_candles(shock, baseline_candles=baseline)

    assert regime in {"trend_up", "trend_down", "range", "high_vol", "low_vol", "vol_cluster", "shock"}
    assert vol_mult == 2.0


def test_required_context_bars_uses_strategy_lookbacks():
    settings = {s.name: s for s in build_strategy_settings()}

    assert required_context_bars(settings["range_scalper_24_120"]) >= 120
    assert required_context_bars(settings["tsmom_252_500_2_8"]) >= 252


def test_walk_forward_report_serializes_research_summary():
    setting = next(s for s in build_strategy_settings() if s.name == "trend_sma_5_20_50")
    candles = generate_regime_candles("trend_up", symbol="NAS100", bars=340, seed=22, vol_mult=1.0)

    report = evaluate_walk_forward_routes(
        candles_by_symbol={"NAS100": candles},
        settings=[setting],
        timeframe="D1",
        train_bars=180,
        test_bars=80,
        step_bars=80,
        train_segment_bars=90,
        train_step_bars=45,
        rpm_min_trades=0.0,
    )
    payload = serialize_walk_forward_report(report)

    assert payload["summary"]["windows"] == 2
    assert payload["summary"]["claim_boundary"].endswith("Live trading remains NOT LICENSED.")
    assert len(payload["windows"]) == 2
    assert payload["windows"][0]["test_start_index"] == payload["windows"][0]["train_end_index"]
    assert "test_event_context" in payload["windows"][0]


def test_walk_forward_route_key_includes_event_context():
    setting = next(s for s in build_strategy_settings() if s.name == "trend_sma_5_20_50")
    candles = generate_regime_candles("trend_up", symbol="NAS100", bars=340, seed=23, vol_mult=1.0)
    event_start = datetime.fromisoformat(str(candles[180]["timestamp"]).replace("Z", "+00:00"))
    event_windows = [
        manual_event_window(
            "conflict_shock",
            event_start,
            event_start + timedelta(days=90),
            event_ref="test-conflict",
        )
    ]

    report = evaluate_walk_forward_routes(
        candles_by_symbol={"NAS100": candles},
        settings=[setting],
        timeframe="D1",
        event_windows=event_windows,
        train_bars=180,
        test_bars=80,
        step_bars=80,
        train_segment_bars=90,
        train_step_bars=45,
        rpm_min_trades=0.0,
    )

    assert report.windows[0].test_event_context == "conflict_shock"
    assert "event_context=conflict_shock" in report.windows[0].route_key
