from cas_forex.condition_lab import (
    ConditionCell,
    build_strategy_settings,
    default_real_period_for_timeframe,
    nested_lacunarity_by_axes,
    rpm_route_table,
    run_synthetic_condition_grid,
    stable_seed,
    time_scale_for_timeframe,
    timeframe_bar_days,
    yfinance_interval_for_timeframe,
)
from cas_forex.regime_sim import generate_regime_candles
from cas_forex.schemas.cjt import CjtRegion


def _cell(**overrides):
    data = {
        "source": "synthetic",
        "symbol": "NAS100",
        "regime": "trend_up",
        "vol_mult": 1.0,
        "timeframe": "D1",
        "time_scale": "day",
        "event_context": "normal",
        "setting": "tsmom_252_500_2_8",
        "family": "tsmom",
        "params": {"lookback": 252},
        "sample_count": 3,
        "mean_return_pct": 20.0,
        "mean_max_dd_pct": 6.0,
        "mean_trades": 12.0,
        "win_rate": 0.55,
        "profit_factor": 1.4,
        "suppressed_trades": 2.0,
        "region": CjtRegion.ACTIVE,
        "beta": 3.33,
        "score": 8.0,
        "is_gap": False,
        "notes": [],
    }
    data.update(overrides)
    return ConditionCell(**data)


def test_stable_seed_is_deterministic():
    assert stable_seed("NAS100", "trend_up", 1.0, 0) == stable_seed("NAS100", "trend_up", 1.0, 0)
    assert stable_seed("NAS100", "trend_up", 1.0, 0) != stable_seed("NAS100", "trend_up", 1.0, 1)


def test_regime_generator_uses_instrument_scale_for_indices():
    candles = generate_regime_candles("trend_up", symbol="NAS100", bars=20, seed=1)

    assert candles[0]["close"] > 1_000
    assert candles[0]["high"] >= candles[0]["low"]


def test_strategy_setting_registry_contains_tsmom_and_pullback():
    names = {setting.name for setting in build_strategy_settings()}

    assert "tsmom_252_500_2_8" in names
    assert "pullback_126_5" in names


def test_timeframe_helpers_cover_nested_scales():
    assert time_scale_for_timeframe("S1") == "second"
    assert time_scale_for_timeframe("M15") == "minute"
    assert time_scale_for_timeframe("H1") == "hour"
    assert time_scale_for_timeframe("D1") == "day"
    assert time_scale_for_timeframe("MN1") == "month"
    assert time_scale_for_timeframe("Y1") == "year"
    assert timeframe_bar_days("M1") < timeframe_bar_days("H1") < timeframe_bar_days("D1")
    assert yfinance_interval_for_timeframe("S1") is None
    assert yfinance_interval_for_timeframe("MN1") == "1mo"
    assert default_real_period_for_timeframe("M1") == "7d"


def test_synthetic_condition_grid_nests_timeframes():
    setting = next(s for s in build_strategy_settings() if s.name == "trend_sma_5_20_50")

    cells = run_synthetic_condition_grid(
        symbols=["NAS100"],
        settings=[setting],
        regimes=["trend_up"],
        vol_mults=[1.0],
        timeframes=["S1", "D1"],
        seeds=1,
        bars=90,
    )

    assert len(cells) == 2
    assert {cell.timeframe for cell in cells} == {"S1", "D1"}
    assert {cell.time_scale for cell in cells} == {"second", "day"}


def test_synthetic_condition_grid_nests_event_contexts():
    setting = next(s for s in build_strategy_settings() if s.name == "trend_sma_5_20_50")

    cells = run_synthetic_condition_grid(
        symbols=["NAS100"],
        settings=[setting],
        regimes=["trend_up"],
        vol_mults=[1.0],
        timeframes=["D1"],
        event_contexts=["normal", "pre_NFP"],
        seeds=1,
        bars=90,
    )

    assert len(cells) == 2
    assert {cell.event_context for cell in cells} == {"normal", "pre_NFP"}


def test_default_nested_lacunarity_includes_time_axes():
    cells = [
        _cell(is_gap=False, timeframe="M1", time_scale="minute"),
        _cell(setting="bad", family="breakout", is_gap=True, mean_return_pct=-1.0, timeframe="D1", time_scale="day"),
    ]

    lac = nested_lacunarity_by_axes(cells)

    assert lac["overall"] == 0.5
    assert lac["source=synthetic|symbol=NAS100|time_scale=minute|timeframe=M1|event_context=normal"] == 0.0
    assert lac["source=synthetic|symbol=NAS100|time_scale=day|timeframe=D1|event_context=normal"] == 1.0


def test_nested_lacunarity_by_axes_marks_gaps():
    cells = [
        _cell(is_gap=False),
        _cell(setting="bad", family="breakout", is_gap=True, mean_return_pct=-1.0),
    ]

    lac = nested_lacunarity_by_axes(cells, axes=("source", "symbol", "family"))

    assert lac["overall"] == 0.5
    assert lac["source=synthetic|symbol=NAS100|family=breakout"] == 1.0
    assert lac["source=synthetic|symbol=NAS100|family=tsmom"] == 0.0


def test_rpm_route_table_selects_best_non_gap_or_no_trade():
    good = _cell(setting="good", score=5.0)
    better = _cell(setting="better", score=9.0, mean_return_pct=25.0)
    bad_gap = _cell(setting="gap", is_gap=True, score=-1000.0, mean_return_pct=-2.0)
    no_trade_only = _cell(
        symbol="US30",
        setting="gap2",
        is_gap=True,
        score=-1000.0,
        mean_return_pct=-5.0,
        regime="range",
    )

    routes = rpm_route_table([good, better, bad_gap, no_trade_only])

    nas_route = routes["source=synthetic|symbol=NAS100|time_scale=day|timeframe=D1|event_context=normal|regime=trend_up|vol_mult=1.0"]
    us_route = routes["source=synthetic|symbol=US30|time_scale=day|timeframe=D1|event_context=normal|regime=range|vol_mult=1.0"]

    assert nas_route["action"] == "ROUTE"
    assert nas_route["setting"] == "better"
    assert us_route["action"] == "NO_TRADE"
