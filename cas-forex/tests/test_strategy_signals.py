import pytest

from cas_forex.backtest.engine import BacktestEngine
from cas_forex.forecast.strategies import (
    make_low_vol_range_scalper_signal,
    make_time_series_momentum_signal,
    make_trend_pullback_signal,
)
from cas_forex.schemas.forecast import Direction


def test_time_series_momentum_defaults_to_long_or_flat():
    closes = [100.0] * 20 + [101.0 + i for i in range(20)]
    signal = make_time_series_momentum_signal(lookback=20, min_return_bps=500.0)

    direction, confidence, sl_mult, tp_mult = signal(closes)

    assert direction == Direction.LONG
    assert confidence >= 0.35
    assert sl_mult == pytest.approx(2.0)
    assert tp_mult == pytest.approx(6.0)


def test_time_series_momentum_does_not_short_indices_unless_enabled():
    closes = [120.0] * 20 + [119.0 - i for i in range(20)]

    assert make_time_series_momentum_signal(lookback=20, min_return_bps=500.0)(closes) is None
    direction, *_ = make_time_series_momentum_signal(
        lookback=20,
        min_return_bps=500.0,
        allow_short=True,
    )(closes)
    assert direction == Direction.SHORT


def test_trend_pullback_buys_short_dip_inside_larger_uptrend():
    closes = [100.0 + i * 0.5 for i in range(30)]
    closes.extend([116.0, 114.0, 112.0])
    signal = make_trend_pullback_signal(
        trend_lookback=20,
        pullback_lookback=3,
        min_trend_bps=500.0,
        pullback_bps=150.0,
    )

    direction, confidence, sl_mult, tp_mult = signal(closes)

    assert direction == Direction.LONG
    assert confidence >= 0.35
    assert sl_mult == pytest.approx(1.5)
    assert tp_mult == pytest.approx(3.0)


def test_backtest_engine_recomputes_atr_each_bar():
    candles = []
    for i in range(25):
        close = 100.0 + i
        width = 1.0 if i < 16 else 12.0
        candles.append({
            "timestamp": f"2026-01-{i + 1:02d}T00:00:00",
            "open": close,
            "high": close + width,
            "low": close - width,
            "close": close,
            "volume": 1000,
        })

    observed_atr = []
    engine = BacktestEngine()
    engine._generate_proposal = lambda symbol, cs, horizon, atr: observed_atr.append(atr) or None

    engine.run(candles, symbol="NAS100", warmup_bars=15)

    assert len(observed_atr) > 2
    assert observed_atr[-1] > observed_atr[0]


def test_low_vol_range_scalper_fades_quiet_range_extension():
    closes = []
    for i in range(140):
        closes.append(100.0 + (0.05 if i % 2 == 0 else -0.05))
    closes.extend([100.04, 100.05, 100.06, 100.35])
    signal = make_low_vol_range_scalper_signal(
        lookback=24,
        baseline=120,
        z_entry=1.0,
        max_vol_ratio=1.2,
        max_efficiency_ratio=0.6,
    )

    direction, confidence, sl_mult, tp_mult = signal(closes)

    assert direction == Direction.SHORT
    assert confidence >= 0.35
    assert sl_mult == pytest.approx(2.0)
    assert tp_mult == pytest.approx(0.8)


def test_low_vol_range_scalper_rejects_trending_conditions():
    closes = [100.0 + i * 0.2 for i in range(150)]
    signal = make_low_vol_range_scalper_signal(
        lookback=24,
        baseline=120,
        z_entry=1.0,
        max_vol_ratio=1.2,
        max_efficiency_ratio=0.35,
    )

    assert signal(closes) is None
