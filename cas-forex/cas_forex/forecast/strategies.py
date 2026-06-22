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
