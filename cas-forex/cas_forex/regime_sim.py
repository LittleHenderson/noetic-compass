"""Market-regime simulator for CAS Forex strategy/condition analysis.

The CAS-SDG idea applied to whole market REGIMES: generate synthetic OHLC paths
under named conditions (trend, range, high/low vol, vol-cluster, shock) so we can
play out how each strategy + setting behaves across conditions we can't always
find enough of in one slice of history.

Each (strategy x regime) result is classified into a CJT operating region
(cutoff / active / saturation / breakdown) with a gain (beta) estimate. Across
the matrix we compute a LACUNARITY map — where do we have NO validated edge
(gaps), and nested gaps across a second axis (volatility level). That coverage
map is what drives strategy/setting switching (RPM prerequisite routing).

Synthetic paths characterize how a strategy *behaves* under assumed conditions.
They cannot prove the real market will produce those conditions, nor that an edge
survives live — they are a stress map, read as a gauge, not a guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from cas_forex.instruments import default_mid, price_unit_size, round_price
from cas_forex.schemas.cjt import CjtRegion
from cas_forex.schemas.forecast import pip_multiplier

REGIMES = [
    "trend_up", "trend_down", "range", "high_vol", "low_vol", "vol_cluster", "shock",
]


def generate_regime_candles(
    regime: str,
    symbol: str = "EUR/USD",
    bars: int = 400,
    seed: int = 0,
    vol_mult: float = 1.0,
    base: Optional[float] = None,
) -> List[dict]:
    """Generate synthetic OHLC candles for a named market regime (seeded)."""
    rng = np.random.default_rng(seed)
    pip = 1.0 / pip_multiplier(symbol)
    if base is None:
        base = default_mid(symbol)
    # Base per-bar volatility in price units (~ a daily candle), scaled by vol_mult.
    if symbol == "USD/JPY":
        base_unit = 0.55
    else:
        unit_size = price_unit_size(symbol)
        base_unit = max(base * 0.0008, unit_size)
    unit = base_unit * vol_mult

    price = float(base)
    closes = [price]
    burst = False
    for i in range(bars - 1):
        z = rng.standard_normal()
        if regime == "trend_up":
            drift, sigma = 0.14 * unit, 0.55 * unit
        elif regime == "trend_down":
            drift, sigma = -0.14 * unit, 0.55 * unit
        elif regime == "range":
            # Ornstein-Uhlenbeck pull back toward base.
            drift, sigma = -0.06 * (price - base), 0.7 * unit
        elif regime == "high_vol":
            drift, sigma = 0.0, 2.2 * unit
        elif regime == "low_vol":
            drift, sigma = 0.0, 0.25 * unit
        elif regime == "vol_cluster":
            if rng.random() < (0.04 if not burst else 0.2):
                burst = not burst
            sigma = (2.4 if burst else 0.3) * unit
            drift = 0.0
        elif regime == "shock":
            sigma = 0.4 * unit
            drift = 0.0
            if i == int(bars * 0.6):
                drift = (1.0 if rng.random() < 0.5 else -1.0) * 9.0 * unit
        else:
            drift, sigma = 0.0, unit
        price = max(price + drift + sigma * z, pip)  # keep > 0
        closes.append(price)

    candles: List[dict] = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i > 0 else c
        wick = abs(rng.standard_normal()) * 0.4 * unit + pip
        candles.append({
            "timestamp": f"2026-01-01T00:{i % 60:02d}:00",
            "open": round_price(symbol, o),
            "high": round_price(symbol, max(o, c) + wick),
            "low": round_price(symbol, max(min(o, c) - wick, pip)),
            "close": round_price(symbol, c),
            "volume": 1000 + i,
        })
    return candles


@dataclass
class CellResult:
    strategy: str
    regime: str
    vol_mult: float
    mean_return_pct: float
    mean_max_dd_pct: float
    mean_trades: float
    win_rate: float
    region: CjtRegion
    beta: float          # gain estimate: return per unit of drawdown taken
    is_gap: bool         # lacuna: no validated positive edge in this cell


def classify_region(return_pct: float, max_dd_pct: float, n_trades: float) -> Tuple[CjtRegion, float]:
    """Map an aggregate backtest result to a CJT operating region + gain (beta).

    cutoff     - signal barely conducted (too few trades)
    breakdown  - hard boundary failed (deep drawdown / blow-up)
    saturation - very active but not converting activity to return
    active     - trades, controlled drawdown, working as designed
    beta       - return amplification per unit of drawdown risk taken
    """
    beta = return_pct / max(max_dd_pct, 1e-6)
    if n_trades <= 2:
        return CjtRegion.CUTOFF, 0.0
    if max_dd_pct >= 25.0:
        return CjtRegion.BREAKDOWN, beta
    if n_trades >= 250 and return_pct <= 0:
        return CjtRegion.SATURATION, beta
    return CjtRegion.ACTIVE, beta


def cell_is_gap(region: CjtRegion, mean_return_pct: float) -> bool:
    """A lacuna = no validated positive edge: cutoff, breakdown, or non-positive."""
    return region in (CjtRegion.CUTOFF, CjtRegion.BREAKDOWN) or mean_return_pct <= 0.0


def lacunarity(cells: List[CellResult]) -> float:
    """Fraction of cells with no validated edge (0 = full coverage, 1 = all gaps)."""
    if not cells:
        return 1.0
    return sum(1 for c in cells if c.is_gap) / len(cells)


def nested_lacunarity(cells: List[CellResult]) -> Dict[str, float]:
    """Lacunarity nested by strategy, then reported per volatility level too.

    Returns a dict with overall, per-strategy, and per-(strategy,vol) gap fractions —
    gaps within gaps: a strategy may cover normal vol but be all-gaps at high vol.
    """
    out: Dict[str, float] = {"overall": lacunarity(cells)}
    strategies = sorted({c.strategy for c in cells})
    vols = sorted({c.vol_mult for c in cells})
    for s in strategies:
        s_cells = [c for c in cells if c.strategy == s]
        out[f"strategy::{s}"] = lacunarity(s_cells)
        for v in vols:
            sv = [c for c in s_cells if c.vol_mult == v]
            if sv:
                out[f"strategy::{s}::vol::{v}"] = lacunarity(sv)
    return out


# ---- Live regime detection + strategy switching ----

# Default routing derived from the simulator's RPM seed: regime -> strategy name
# (None = lacuna, sit out). Overridable.
DEFAULT_ROUTING: Dict[str, Optional[str]] = {
    "trend_up": "breakout",
    "trend_down": "breakout",
    "high_vol": "breakout",
    "low_vol": "trend_sma",
    "range": "meanrev",
    "shock": "meanrev",
    "vol_cluster": None,  # no validated edge -> do not trade
}


def detect_regime(
    closes: List[float],
    window: int = 60,
    baseline: int = 180,
    er_trend: float = 0.35,
    shock_z: float = 4.0,
    hi_vol: float = 1.5,
    lo_vol: float = 0.6,
) -> str:
    """Classify the current market regime from real trailing closes.

    Features (all standard, robust): Kaufman efficiency ratio (trend vs chop),
    realized vol vs a longer baseline (high/low vol), last-bar return z-score
    (shock), and vol-of-vol (clustering). Returns one of REGIMES.
    """
    w = np.asarray(closes[-window:], dtype=float)
    if len(w) < 10 or np.any(w <= 0):
        return "range"
    rets = np.diff(np.log(w))
    vol = float(rets.std())
    if vol <= 0:
        return "low_vol"
    net = abs(w[-1] - w[0])
    path = float(np.abs(np.diff(w)).sum())
    er = net / path if path > 0 else 0.0  # efficiency ratio in [0,1]
    bw = np.asarray(closes[-baseline:], dtype=float) if len(closes) >= baseline else w
    bvol = float(np.diff(np.log(bw)).std()) or vol
    vol_ratio = vol / bvol
    last_z = abs(rets[-1]) / vol

    if last_z > shock_z:
        return "shock"
    if er > er_trend:
        return "trend_up" if w[-1] > w[0] else "trend_down"
    if vol_ratio > hi_vol:
        half = len(rets) // 2
        early = float(rets[:half].std())
        late = float(rets[half:].std())
        if early > 0 and late / early > 1.8:
            return "vol_cluster"
        return "high_vol"
    if vol_ratio < lo_vol:
        return "low_vol"
    return "range"


def make_regime_switching_signal(
    sub_signals: Dict[str, object],
    routing: Optional[Dict[str, Optional[str]]] = None,
    detect_window: int = 60,
    **detect_kwargs,
):
    """Build a signal_fn that detects the regime each bar and routes to the
    matching sub-strategy (or sits out where the routing is a lacuna).

    The returned function carries a ``regime_counts`` dict so the caller can see
    the regime distribution and the sit-out rate after a run.
    """
    routing = routing or DEFAULT_ROUTING
    from collections import Counter
    counts: "Counter" = Counter()

    def signal(closes: List[float]):
        if len(closes) < detect_window:
            return None
        regime = detect_regime(closes, window=detect_window, **detect_kwargs)
        strat = routing.get(regime)
        counts[regime] += 1
        if not strat:
            counts["__sit_out__"] += 1
            return None
        sub = sub_signals.get(strat)
        if sub is None:
            return None
        result = sub(closes)
        if result is None:
            counts["__no_signal__"] += 1
        return result

    signal.regime_counts = counts  # type: ignore[attr-defined]
    return signal


def best_strategy_per_regime(cells: List[CellResult]) -> Dict[str, Optional[str]]:
    """RPM seed: for each regime, the non-gap strategy with the best gain (beta).

    None means a lacuna — no strategy has a validated edge in that regime, so the
    honest action is to not trade it (or flag for review), not to force a pick.
    """
    out: Dict[str, Optional[str]] = {}
    regimes = sorted({c.regime for c in cells})
    for r in regimes:
        candidates = [c for c in cells if c.regime == r and not c.is_gap]
        out[r] = max(candidates, key=lambda c: c.beta).strategy if candidates else None
    return out
