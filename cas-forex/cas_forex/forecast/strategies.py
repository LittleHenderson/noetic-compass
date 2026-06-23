"""Rule-based directional strategies for the CAS Forex backtest harness.

Each strategy is a callable: given the trailing close series, it returns either
None (no trade) or a tuple the engine understands:

    (Direction, confidence)                      -> engine uses default ATR stops
    (Direction, confidence, sl_mult, tp_mult)    -> strategy sets ATR stop multiples

sl_mult / tp_mult are multiples of ATR. A mean-reversion fade typically wants a
wider stop (beyond the extreme) and a smaller target (back toward the mean), e.g.
sl_mult=2.0, tp_mult=1.0 — the "high win rate, small wins" profile. We TEST whether
that profile is net-profitable after costs; we do not assume it.

Honesty note: no strategy here uses martingale, grid averaging, or a no-stop-loss
mode. Real money is going in; every strategy must have a hard stop.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import numpy as np

from cas_forex.schemas.forecast import Direction

SignalResult = Optional[Tuple]


def make_mean_reversion_signal(
    lookback: int = 20,
    z_entry: float = 2.0,
    sl_mult: float = 2.0,
    tp_mult: float = 1.0,
    max_confidence: float = 0.9,
    trend_filter: bool = False,
    trend_lookback: int = 60,
    trend_skip_bps: float = 150.0,
) -> Callable[[List[float]], SignalResult]:
    """Z-score fade: short when price is z_entry sigmas above its mean, long when
    z_entry sigmas below. Targets reversion toward the mean (ATR-scaled stops).

    With trend_filter on, skip a fade when a strong trend over `trend_lookback`
    bars runs against it (don't fade strength) — mean-reversion's known weakness.
    A "strong" trend is a move larger than `trend_skip_bps` basis points.
    """

    def signal(closes: List[float]) -> SignalResult:
        if len(closes) < lookback + 1:
            return None
        window = np.asarray(closes[-lookback:], dtype=float)
        mean = float(window.mean())
        std = float(window.std())
        if std <= 0:
            return None
        z = (closes[-1] - mean) / std
        if z >= z_entry:
            direction = Direction.SHORT  # extended above mean -> fade down
        elif z <= -z_entry:
            direction = Direction.LONG   # extended below mean -> fade up
        else:
            return None

        if trend_filter and len(closes) > trend_lookback:
            past = closes[-trend_lookback]
            if past > 0:
                trend_bps = (closes[-1] - past) / past * 10_000.0
                # Strong uptrend -> don't SHORT into it; strong downtrend -> don't LONG.
                if direction == Direction.SHORT and trend_bps > trend_skip_bps:
                    return None
                if direction == Direction.LONG and trend_bps < -trend_skip_bps:
                    return None

        confidence = min(max_confidence, 0.3 + (abs(z) - z_entry) * 0.2)
        return direction, round(confidence, 4), sl_mult, tp_mult

    return signal


def make_sma_trend_signal(
    fast: int = 5, mid: int = 20, slow: int = 50, max_confidence: float = 0.75,
) -> Callable[[List[float]], SignalResult]:
    """SMA5/20/50 trend signal as a composable signal_fn (mirrors the engine's
    built-in trend logic, so it can be routed to by the regime switcher)."""

    def signal(closes: List[float]) -> SignalResult:
        if len(closes) < mid:
            return None
        cur = closes[-1]
        sma_f = float(np.mean(closes[-fast:]))
        sma_m = float(np.mean(closes[-mid:]))
        sma_s = float(np.mean(closes[-slow:])) if len(closes) >= slow else sma_m
        if sma_f > sma_m > sma_s:
            direction = Direction.LONG
        elif sma_f < sma_m < sma_s:
            direction = Direction.SHORT
        else:
            return None
        confidence = min(abs(sma_f - sma_m) / cur * 500, max_confidence)
        if confidence < 0.3:
            return None
        return direction, round(confidence, 4)

    return signal


def make_donchian_breakout_signal(
    lookback: int = 20,
    sl_mult: float = 1.5,
    tp_mult: float = 3.0,
    max_confidence: float = 0.85,
) -> Callable[[List[float]], SignalResult]:
    """Breakout: long when price makes a new `lookback`-bar high, short on a new
    low. Trend-continuation profile (small stop, larger target)."""

    def signal(closes: List[float]) -> SignalResult:
        if len(closes) < lookback + 1:
            return None
        window = closes[-(lookback + 1):-1]  # exclude the current bar
        hi = max(window)
        lo = min(window)
        price = closes[-1]
        if price > hi:
            direction = Direction.LONG
            edge = (price - hi) / hi
        elif price < lo:
            direction = Direction.SHORT
            edge = (lo - price) / lo
        else:
            return None
        confidence = min(max_confidence, 0.3 + edge * 2000.0)
        return direction, round(confidence, 4), sl_mult, tp_mult

    return signal


def make_time_series_momentum_signal(
    lookback: int = 126,
    skip_recent: int = 0,
    min_return_bps: float = 250.0,
    allow_short: bool = False,
    sl_mult: float = 2.0,
    tp_mult: float = 6.0,
    max_confidence: float = 0.9,
) -> Callable[[List[float]], SignalResult]:
    """Time-series momentum: trade in the direction of a sustained move.

    This is the daily-bar version of the evidence-backed trend-following family:
    if the prior lookback return is strongly positive, go long; if it is strongly
    negative and ``allow_short`` is true, go short. For equity indices the default
    is long-or-flat because the long-term drift makes constant shorting expensive.
    """

    def signal(closes: List[float]) -> SignalResult:
        min_len = lookback + skip_recent + 1
        if len(closes) < min_len:
            return None

        end_idx = -1 - skip_recent if skip_recent > 0 else -1
        recent = closes[end_idx]
        past = closes[end_idx - lookback]
        if past <= 0:
            return None

        ret_bps = (recent / past - 1.0) * 10_000.0
        if ret_bps >= min_return_bps:
            direction = Direction.LONG
        elif allow_short and ret_bps <= -min_return_bps:
            direction = Direction.SHORT
        else:
            return None

        strength = max(abs(ret_bps) - min_return_bps, 0.0)
        confidence = min(max_confidence, 0.35 + strength / 5000.0)
        return direction, round(confidence, 4), sl_mult, tp_mult

    return signal


def make_trend_pullback_signal(
    trend_lookback: int = 126,
    pullback_lookback: int = 5,
    min_trend_bps: float = 500.0,
    pullback_bps: float = 150.0,
    allow_short: bool = False,
    sl_mult: float = 1.5,
    tp_mult: float = 3.0,
    max_confidence: float = 0.85,
) -> Callable[[List[float]], SignalResult]:
    """Enter on a short pullback inside a larger trend.

    For NAS100/US30 this tests a practical hypothesis: the index has a persistent
    upward regime, but buying only after a short-term dip may reduce chasing.
    """

    def signal(closes: List[float]) -> SignalResult:
        min_len = max(trend_lookback, pullback_lookback) + 1
        if len(closes) < min_len:
            return None

        trend_base = closes[-trend_lookback]
        pullback_base = closes[-pullback_lookback]
        current = closes[-1]
        if trend_base <= 0 or pullback_base <= 0:
            return None

        trend_bps = (current / trend_base - 1.0) * 10_000.0
        recent_bps = (current / pullback_base - 1.0) * 10_000.0

        if trend_bps >= min_trend_bps and recent_bps <= -pullback_bps:
            direction = Direction.LONG
        elif allow_short and trend_bps <= -min_trend_bps and recent_bps >= pullback_bps:
            direction = Direction.SHORT
        else:
            return None

        trend_strength = max(abs(trend_bps) - min_trend_bps, 0.0)
        pullback_strength = max(abs(recent_bps) - pullback_bps, 0.0)
        confidence = min(max_confidence, 0.35 + (trend_strength + pullback_strength) / 7500.0)
        return direction, round(confidence, 4), sl_mult, tp_mult

    return signal


def make_low_vol_range_scalper_signal(
    lookback: int = 24,
    baseline: int = 120,
    z_entry: float = 1.2,
    max_vol_ratio: float = 0.75,
    max_efficiency_ratio: float = 0.35,
    sl_mult: float = 2.0,
    tp_mult: float = 0.8,
    max_confidence: float = 0.8,
) -> Callable[[List[float]], SignalResult]:
    """Low-volatility range fade inspired by public EA/range-bot patterns.

    It only trades when recent volatility is below its baseline and directional
    efficiency is low, then fades a short-term z-score extension. This captures
    the public Forex Fury-style idea (range/low-volatility, small targets) without
    copying proprietary set files or assuming profitability.
    """

    def signal(closes: List[float]) -> SignalResult:
        min_len = max(lookback + 1, baseline + 1)
        if len(closes) < min_len:
            return None

        recent = np.asarray(closes[-lookback:], dtype=float)
        base = np.asarray(closes[-baseline:], dtype=float)
        if np.any(recent <= 0) or np.any(base <= 0):
            return None

        recent_rets = np.diff(np.log(recent))
        base_rets = np.diff(np.log(base))
        base_vol = float(base_rets.std())
        recent_vol = float(recent_rets.std())
        if base_vol <= 0 or recent_vol <= 0:
            return None
        if recent_vol / base_vol > max_vol_ratio:
            return None

        path = float(np.abs(np.diff(recent)).sum())
        efficiency = abs(float(recent[-1] - recent[0])) / path if path > 0 else 0.0
        if efficiency > max_efficiency_ratio:
            return None

        mean = float(recent.mean())
        std = float(recent.std())
        if std <= 0:
            return None
        z = (closes[-1] - mean) / std
        if z >= z_entry:
            direction = Direction.SHORT
        elif z <= -z_entry:
            direction = Direction.LONG
        else:
            return None

        edge = min(abs(z) - z_entry, 3.0)
        confidence = min(max_confidence, 0.35 + edge * 0.12)
        return direction, round(confidence, 4), sl_mult, tp_mult

    return signal
