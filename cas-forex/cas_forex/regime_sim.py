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
        base = 150.0 if symbol == "USD/JPY" else 1.10
    # Base per-bar volatility in price units (~ a daily candle), scaled by vol_mult.
    unit = (0.55 if symbol == "USD/JPY" else 0.0009) * vol_mult

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
            "open": round(o, 5),
            "high": round(max(o, c) + wick, 5),
            "low": round(max(min(o, c) - wick, pip), 5),
            "close": round(c, 5),
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
