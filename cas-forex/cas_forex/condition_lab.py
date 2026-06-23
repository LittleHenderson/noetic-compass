"""CAS FOREX condition lab.

This is the deeper simulator layer above ``regime_sim``. It sweeps strategy
settings across synthetic or real market-condition samples, classifies each
strategy/setting/condition cell into a CJT operating region, computes nested
lacunarity, and emits an RPM routing table for switching.

The output is a research stress map. It can recommend what to test next or route
in paper mode, but it cannot unlock live trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import blake2b
from math import log1p, sqrt
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from cas_forex.backtest.engine import BacktestEngine, BacktestResult
from cas_forex.event_context import (
    EVENT_CONTEXT_NORMAL,
    EventWindow,
    event_context_for_candles,
    event_context_vol_multiplier,
    normalize_event_context,
)
from cas_forex.forecast.strategies import (
    make_donchian_breakout_signal,
    make_mean_reversion_signal,
    make_low_vol_range_scalper_signal,
    make_sma_trend_signal,
    make_time_series_momentum_signal,
    make_trend_pullback_signal,
)
from cas_forex.regime_sim import (
    REGIMES,
    cell_is_gap,
    classify_region,
    detect_regime,
    generate_regime_candles,
)
from cas_forex.schemas.cjt import CjtRegion
from cas_forex.schemas.forecast import Direction

SignalFactory = Callable[[], object]


@dataclass(frozen=True)
class StrategySetting:
    name: str
    family: str
    params: Dict[str, object]
    factory: SignalFactory

    def make_signal(self):
        return self.factory()


@dataclass
class SampleMetrics:
    return_pct: float
    max_dd_pct: float
    total_trades: int
    win_rate: float
    profit_factor: float
    suppressed_trades: int


@dataclass
class ConditionCell:
    source: str
    symbol: str
    regime: str
    vol_mult: float
    timeframe: str
    time_scale: str
    event_context: str
    setting: str
    family: str
    params: Dict[str, object]
    sample_count: int
    mean_return_pct: float
    mean_max_dd_pct: float
    mean_trades: float
    win_rate: float
    profit_factor: float
    suppressed_trades: float
    region: CjtRegion
    beta: float
    score: float
    is_gap: bool
    notes: List[str] = field(default_factory=list)


def stable_seed(*parts: object) -> int:
    """Deterministic 32-bit seed independent of Python hash randomization."""
    h = blake2b(digest_size=8)
    h.update("|".join(str(p) for p in parts).encode("utf-8"))
    return int.from_bytes(h.digest()[:4], "big", signed=False)


def normalize_timeframe(timeframe: str) -> str:
    """Return the canonical CAS timeframe label.

    CAS uses MetaTrader-style labels where M means minute and MN means month.
    """
    tf = str(timeframe).strip().upper().replace(" ", "")
    aliases = {
        "1S": "S1",
        "5S": "S5",
        "15S": "S15",
        "30S": "S30",
        "1SEC": "S1",
        "5SEC": "S5",
        "15SEC": "S15",
        "30SEC": "S30",
        "1M": "M1",
        "5M": "M5",
        "15M": "M15",
        "30M": "M30",
        "1MIN": "M1",
        "5MIN": "M5",
        "15MIN": "M15",
        "30MIN": "M30",
        "1H": "H1",
        "4H": "H4",
        "1D": "D1",
        "1W": "W1",
        "1WK": "W1",
        "1MO": "MN1",
        "1MON": "MN1",
        "1MONTH": "MN1",
        "MO1": "MN1",
        "Y1": "Y1",
        "1Y": "Y1",
        "1YR": "Y1",
        "1YEAR": "Y1",
    }
    tf = aliases.get(tf, tf)
    if tf.startswith("MN") and tf[2:].isdigit():
        return tf
    if len(tf) >= 2 and tf[0] in {"S", "M", "H", "D", "W", "Y"} and tf[1:].isdigit():
        return tf
    raise ValueError(f"Unsupported timeframe: {timeframe!r}")


def time_scale_for_timeframe(timeframe: str) -> str:
    """Map a canonical timeframe to the nested lacunarity scale bucket."""
    tf = normalize_timeframe(timeframe)
    if tf.startswith("S"):
        return "second"
    if tf.startswith("M") and not tf.startswith("MN"):
        return "minute"
    if tf.startswith("H"):
        return "hour"
    if tf.startswith("D"):
        return "day"
    if tf.startswith("W"):
        return "week"
    if tf.startswith("MN"):
        return "month"
    if tf.startswith("Y"):
        return "year"
    raise ValueError(f"Unsupported timeframe: {timeframe!r}")


def timeframe_bar_days(timeframe: str) -> float:
    """Approximate bar length in trading days for synthetic volatility scaling."""
    tf = normalize_timeframe(timeframe)
    if tf.startswith("MN"):
        return float(tf[2:]) * 21.0
    unit = tf[0]
    value = float(tf[1:])
    if unit == "S":
        return value / 86_400.0
    if unit == "M":
        return value / 1_440.0
    if unit == "H":
        return value / 24.0
    if unit == "D":
        return value
    if unit == "W":
        return value * 5.0
    if unit == "Y":
        return value * 252.0
    raise ValueError(f"Unsupported timeframe: {timeframe!r}")


def timeframe_vol_scale(timeframe: str) -> float:
    """Scale daily synthetic volatility to the requested bar duration."""
    return sqrt(max(timeframe_bar_days(timeframe), 1e-9))


def yfinance_interval_for_timeframe(timeframe: str) -> Optional[str]:
    """Best available Yahoo interval for a CAS timeframe, if one exists."""
    tf = normalize_timeframe(timeframe)
    return {
        "M1": "1m",
        "M5": "5m",
        "M15": "15m",
        "M30": "30m",
        "H1": "1h",
        "D1": "1d",
        "W1": "1wk",
        "MN1": "1mo",
    }.get(tf)


def default_real_period_for_timeframe(timeframe: str) -> str:
    """Yahoo-safe default history window for each supported real-data interval."""
    tf = normalize_timeframe(timeframe)
    scale = time_scale_for_timeframe(tf)
    if tf == "M1":
        return "7d"
    if scale == "minute":
        return "60d"
    if scale == "hour":
        return "2y"
    if scale in {"day", "week", "month"}:
        return "5y"
    return "5y"


def build_strategy_settings() -> List[StrategySetting]:
    """Strategy/setting grid for the first condition-lab sweep.

    Keep the grid intentionally finite and inspectable. "Every possible setting"
    becomes "every setting in the registry"; expanding the search is just adding
    more named settings here.
    """
    return [
        StrategySetting(
            name="trend_sma_5_20_50",
            family="trend_sma",
            params={"fast": 5, "mid": 20, "slow": 50},
            factory=lambda: make_sma_trend_signal(fast=5, mid=20, slow=50),
        ),
        StrategySetting(
            name="trend_sma_10_50_100",
            family="trend_sma",
            params={"fast": 10, "mid": 50, "slow": 100},
            factory=lambda: make_sma_trend_signal(fast=10, mid=50, slow=100),
        ),
        StrategySetting(
            name="breakout_20_1p5_3",
            family="breakout",
            params={"lookback": 20, "sl_mult": 1.5, "tp_mult": 3.0},
            factory=lambda: make_donchian_breakout_signal(lookback=20, sl_mult=1.5, tp_mult=3.0),
        ),
        StrategySetting(
            name="breakout_55_2_6",
            family="breakout",
            params={"lookback": 55, "sl_mult": 2.0, "tp_mult": 6.0},
            factory=lambda: make_donchian_breakout_signal(lookback=55, sl_mult=2.0, tp_mult=6.0),
        ),
        StrategySetting(
            name="meanrev_20_z2",
            family="meanrev",
            params={"lookback": 20, "z_entry": 2.0, "trend_filter": False},
            factory=lambda: make_mean_reversion_signal(lookback=20, z_entry=2.0),
        ),
        StrategySetting(
            name="meanrev_20_z2_tf",
            family="meanrev",
            params={"lookback": 20, "z_entry": 2.0, "trend_filter": True},
            factory=lambda: make_mean_reversion_signal(lookback=20, z_entry=2.0, trend_filter=True),
        ),
        StrategySetting(
            name="range_scalper_24_120",
            family="range_scalper",
            params={
                "lookback": 24,
                "baseline": 120,
                "z_entry": 1.2,
                "max_vol_ratio": 0.75,
                "max_efficiency_ratio": 0.35,
            },
            factory=lambda: make_low_vol_range_scalper_signal(
                lookback=24,
                baseline=120,
                z_entry=1.2,
                max_vol_ratio=0.75,
                max_efficiency_ratio=0.35,
            ),
        ),
        StrategySetting(
            name="range_scalper_12_80",
            family="range_scalper",
            params={
                "lookback": 12,
                "baseline": 80,
                "z_entry": 1.0,
                "max_vol_ratio": 0.8,
                "max_efficiency_ratio": 0.4,
            },
            factory=lambda: make_low_vol_range_scalper_signal(
                lookback=12,
                baseline=80,
                z_entry=1.0,
                max_vol_ratio=0.8,
                max_efficiency_ratio=0.4,
            ),
        ),
        StrategySetting(
            name="tsmom_126_250_2_6",
            family="tsmom",
            params={"lookback": 126, "min_return_bps": 250.0, "sl_mult": 2.0, "tp_mult": 6.0},
            factory=lambda: make_time_series_momentum_signal(
                lookback=126, min_return_bps=250.0, sl_mult=2.0, tp_mult=6.0
            ),
        ),
        StrategySetting(
            name="tsmom_126_250_2_10",
            family="tsmom",
            params={"lookback": 126, "min_return_bps": 250.0, "sl_mult": 2.0, "tp_mult": 10.0},
            factory=lambda: make_time_series_momentum_signal(
                lookback=126, min_return_bps=250.0, sl_mult=2.0, tp_mult=10.0
            ),
        ),
        StrategySetting(
            name="tsmom_252_500_2_8",
            family="tsmom",
            params={"lookback": 252, "min_return_bps": 500.0, "sl_mult": 2.0, "tp_mult": 8.0},
            factory=lambda: make_time_series_momentum_signal(
                lookback=252, min_return_bps=500.0, sl_mult=2.0, tp_mult=8.0
            ),
        ),
        StrategySetting(
            name="pullback_126_5",
            family="pullback",
            params={"trend_lookback": 126, "pullback_lookback": 5},
            factory=lambda: make_trend_pullback_signal(trend_lookback=126, pullback_lookback=5),
        ),
        StrategySetting(
            name="pullback_252_10",
            family="pullback",
            params={"trend_lookback": 252, "pullback_lookback": 10},
            factory=lambda: make_trend_pullback_signal(trend_lookback=252, pullback_lookback=10),
        ),
    ]


def run_candles_sample(
    candles: List[dict],
    symbol: str,
    setting: StrategySetting,
    *,
    starting_balance: float,
    position_lots: float,
    spread_pips: float,
    extra_cost_pips: float,
    warmup_bars: Optional[int] = None,
) -> SampleMetrics:
    signal = setting.make_signal()
    engine = BacktestEngine(
        initial_balance=starting_balance,
        position_size_lots=position_lots,
        spread_pips=spread_pips,
        extra_cost_pips=extra_cost_pips,
        signal_fn=signal,
    )
    warmup = warmup_bars if warmup_bars is not None else min(80, max(50, len(candles) // 8))
    result: BacktestResult = engine.run(candles, symbol=symbol, warmup_bars=warmup)
    ret = (result.ending_balance - result.starting_balance) / max(result.starting_balance, 1) * 100.0
    return SampleMetrics(
        return_pct=float(ret),
        max_dd_pct=float(result.max_drawdown_pct),
        total_trades=int(result.total_trades),
        win_rate=float(result.win_rate),
        profit_factor=float(result.profit_factor),
        suppressed_trades=int(result.suppressed_trades),
    )


def aggregate_cell(
    *,
    source: str,
    symbol: str,
    regime: str,
    vol_mult: float,
    timeframe: str = "D1",
    event_context: str = EVENT_CONTEXT_NORMAL,
    setting: StrategySetting,
    samples: Sequence[SampleMetrics],
) -> ConditionCell:
    canonical_timeframe = normalize_timeframe(timeframe)
    time_scale = time_scale_for_timeframe(canonical_timeframe)
    event_context = normalize_event_context(event_context)
    returns = np.asarray([s.return_pct for s in samples], dtype=float)
    dds = np.asarray([s.max_dd_pct for s in samples], dtype=float)
    trades = np.asarray([s.total_trades for s in samples], dtype=float)
    wins = np.asarray([s.win_rate for s in samples], dtype=float)
    pfs = np.asarray([s.profit_factor for s in samples], dtype=float)
    suppressed = np.asarray([s.suppressed_trades for s in samples], dtype=float)

    mean_ret = float(returns.mean()) if len(returns) else 0.0
    mean_dd = float(dds.mean()) if len(dds) else 0.0
    mean_trades = float(trades.mean()) if len(trades) else 0.0
    region, raw_beta = classify_region(mean_ret, mean_dd, mean_trades)
    beta = mean_ret / max(mean_dd, 0.25) if mean_ret > 0 else raw_beta
    is_gap = cell_is_gap(region, mean_ret)
    score = score_cell(mean_ret, mean_dd, mean_trades, beta, is_gap)
    notes: List[str] = []
    if region == CjtRegion.BREAKDOWN:
        notes.append("CJT breakdown: drawdown boundary breached.")
    if is_gap:
        notes.append("Nested lacuna: no validated positive edge for this condition.")
    return ConditionCell(
        source=source,
        symbol=symbol,
        regime=regime,
        vol_mult=float(vol_mult),
        timeframe=canonical_timeframe,
        time_scale=time_scale,
        event_context=event_context,
        setting=setting.name,
        family=setting.family,
        params=dict(setting.params),
        sample_count=len(samples),
        mean_return_pct=round(mean_ret, 4),
        mean_max_dd_pct=round(mean_dd, 4),
        mean_trades=round(mean_trades, 2),
        win_rate=round(float(wins.mean()) if len(wins) else 0.0, 4),
        profit_factor=round(float(pfs.mean()) if len(pfs) else 0.0, 4),
        suppressed_trades=round(float(suppressed.mean()) if len(suppressed) else 0.0, 2),
        region=region,
        beta=round(float(beta), 4),
        score=round(float(score), 4),
        is_gap=is_gap,
        notes=notes,
    )


def score_cell(return_pct: float, max_dd_pct: float, trades: float, beta: float, is_gap: bool) -> float:
    """RPM selection score for non-gap cells.

    Rewards return, beta, and enough observations; penalizes drawdown. The score
    is intentionally simple and explainable so routing is auditable.
    """
    if is_gap:
        return -1_000.0
    effective_dd = max(max_dd_pct, 0.25)
    capped_return = min(max(return_pct, 0.0), 100.0)
    capped_beta = min(max(beta, 0.0), 12.0)
    drawdown_penalty = 1.0 + effective_dd / 10.0
    trade_weight = min(log1p(max(trades, 0.0)) / log1p(100.0), 1.5)
    return (capped_return * capped_beta * max(trade_weight, 0.1)) / drawdown_penalty


def run_synthetic_condition_grid(
    *,
    symbols: Sequence[str],
    settings: Sequence[StrategySetting],
    regimes: Sequence[str] = REGIMES,
    vol_mults: Sequence[float] = (0.5, 1.0, 2.0),
    timeframes: Sequence[str] = ("D1",),
    event_contexts: Sequence[str] = (EVENT_CONTEXT_NORMAL,),
    seeds: int = 3,
    bars: int = 420,
    starting_balance: float = 10_000.0,
    position_lots: float = 0.05,
    spread_pips: float = 1.0,
    extra_cost_pips: float = 0.5,
) -> List[ConditionCell]:
    cells: List[ConditionCell] = []
    canonical_timeframes = [normalize_timeframe(timeframe) for timeframe in timeframes]
    canonical_event_contexts = [normalize_event_context(event_context) for event_context in event_contexts]
    for symbol in symbols:
        for setting in settings:
            for timeframe in canonical_timeframes:
                tf_vol_scale = timeframe_vol_scale(timeframe)
                for event_context in canonical_event_contexts:
                    event_vol_scale = event_context_vol_multiplier(event_context)
                    for regime in regimes:
                        for vol_mult in vol_mults:
                            samples: List[SampleMetrics] = []
                            synthetic_vol_mult = vol_mult * tf_vol_scale * event_vol_scale
                            for seed_idx in range(seeds):
                                seed = stable_seed(symbol, setting.name, timeframe, event_context, regime, vol_mult, seed_idx)
                                candles = generate_regime_candles(
                                    regime,
                                    symbol=symbol,
                                    bars=bars,
                                    seed=seed,
                                    vol_mult=synthetic_vol_mult,
                                )
                                samples.append(
                                    run_candles_sample(
                                        candles,
                                        symbol,
                                        setting,
                                        starting_balance=starting_balance,
                                        position_lots=position_lots,
                                        spread_pips=spread_pips,
                                        extra_cost_pips=extra_cost_pips,
                                    )
                                )
                            cells.append(
                                aggregate_cell(
                                    source="synthetic",
                                    symbol=symbol,
                                    regime=regime,
                                    vol_mult=vol_mult,
                                    timeframe=timeframe,
                                    event_context=event_context,
                                    setting=setting,
                                    samples=samples,
                                )
                            )
    return cells


def make_real_condition_samples(
    candles: List[dict],
    *,
    segment_bars: int = 420,
    step_bars: int = 60,
    event_windows: Optional[Sequence[EventWindow]] = None,
) -> List[Tuple[str, float, str, List[dict]]]:
    """Slice real candles into condition samples labeled by detector + vol bucket."""
    if len(candles) < segment_bars:
        return []
    samples: List[Tuple[str, float, str, List[dict]]] = []
    for start in range(0, len(candles) - segment_bars + 1, step_bars):
        segment = candles[start : start + segment_bars]
        regime, vol_mult = condition_label_for_candles(segment, baseline_candles=candles)
        event_context = event_context_for_candles(segment, event_windows=event_windows)
        samples.append((regime, vol_mult, event_context, segment))
    return samples


def condition_label_for_candles(
    candles: List[dict],
    *,
    baseline_candles: Optional[List[dict]] = None,
) -> Tuple[str, float]:
    """Detect the regime and volatility bucket for one candle segment."""
    closes = [c["close"] for c in candles if c.get("close", 0) > 0]
    if len(closes) < 3:
        return "unknown", 1.0

    regime = detect_regime(closes, window=min(60, max(10, len(closes) - 1)))
    baseline = baseline_candles or candles
    baseline_closes = np.asarray([c["close"] for c in baseline if c.get("close", 0) > 0], dtype=float)
    if len(baseline_closes) < 3:
        return regime, 1.0
    baseline_rets = np.diff(np.log(baseline_closes))
    baseline_vol = float(baseline_rets.std()) or 1e-9
    seg_rets = np.diff(np.log(np.asarray(closes, dtype=float)))
    vol_ratio = float(seg_rets.std()) / baseline_vol if len(seg_rets) else 1.0
    if vol_ratio < 0.75:
        return regime, 0.5
    if vol_ratio > 1.35:
        return regime, 2.0
    return regime, 1.0


def run_real_condition_grid(
    *,
    candles_by_symbol: Dict[str, List[dict]],
    settings: Sequence[StrategySetting],
    timeframe: str = "D1",
    event_windows: Optional[Sequence[EventWindow]] = None,
    segment_bars: int = 420,
    step_bars: int = 60,
    starting_balance: float = 10_000.0,
    position_lots: float = 0.05,
    spread_pips: float = 1.0,
    extra_cost_pips: float = 0.5,
) -> List[ConditionCell]:
    grouped: Dict[Tuple[str, str, float, str, str], List[SampleMetrics]] = {}
    setting_lookup = {s.name: s for s in settings}
    for symbol, candles in candles_by_symbol.items():
        samples = make_real_condition_samples(
            candles,
            segment_bars=segment_bars,
            step_bars=step_bars,
            event_windows=event_windows,
        )
        for regime, vol_mult, event_context, segment in samples:
            for setting in settings:
                key = (symbol, regime, vol_mult, event_context, setting.name)
                grouped.setdefault(key, []).append(
                    run_candles_sample(
                        segment,
                        symbol,
                        setting,
                        starting_balance=starting_balance,
                        position_lots=position_lots,
                        spread_pips=spread_pips,
                        extra_cost_pips=extra_cost_pips,
                    )
                )

    cells: List[ConditionCell] = []
    for (symbol, regime, vol_mult, event_context, setting_name), samples in grouped.items():
        setting = setting_lookup[setting_name]
        cells.append(
            aggregate_cell(
                source="real",
                symbol=symbol,
                regime=regime,
                vol_mult=vol_mult,
                timeframe=timeframe,
                event_context=event_context,
                setting=setting,
                samples=samples,
            )
        )
    return cells


def lacunarity_fraction(cells: Sequence[ConditionCell]) -> float:
    if not cells:
        return 1.0
    return sum(1 for c in cells if c.is_gap) / len(cells)


def nested_lacunarity_by_axes(
    cells: Sequence[ConditionCell],
    axes: Sequence[str] = ("source", "symbol", "time_scale", "timeframe", "event_context", "regime", "vol_mult", "family"),
) -> Dict[str, float]:
    """Gap fraction nested by progressive axes: source -> symbol -> regime ..."""
    out: Dict[str, float] = {"overall": round(lacunarity_fraction(cells), 4)}
    for depth in range(1, len(axes) + 1):
        groups: Dict[str, List[ConditionCell]] = {}
        for cell in cells:
            key_parts = [f"{axis}={getattr(cell, axis)}" for axis in axes[:depth]]
            groups.setdefault("|".join(key_parts), []).append(cell)
        for key, group in groups.items():
            out[key] = round(lacunarity_fraction(group), 4)
    return out


def rpm_route_table(
    cells: Sequence[ConditionCell],
    *,
    group_axes: Sequence[str] = ("source", "symbol", "time_scale", "timeframe", "event_context", "regime", "vol_mult"),
    min_trades: float = 5.0,
    max_drawdown_pct: float = 20.0,
    min_return_pct: float = 0.0,
) -> Dict[str, Dict[str, object]]:
    """Pick the best non-gap setting per condition, or route to no-trade."""
    groups: Dict[str, List[ConditionCell]] = {}
    for cell in cells:
        key = "|".join(f"{axis}={getattr(cell, axis)}" for axis in group_axes)
        groups.setdefault(key, []).append(cell)

    routes: Dict[str, Dict[str, object]] = {}
    for key, group in sorted(groups.items()):
        candidates = [
            c for c in group
            if not c.is_gap
            and c.mean_trades >= min_trades
            and c.mean_max_dd_pct <= max_drawdown_pct
            and c.mean_return_pct > min_return_pct
            and c.region == CjtRegion.ACTIVE
        ]
        if not candidates:
            routes[key] = {
                "action": "NO_TRADE",
                "reason": "RPM prerequisites failed or nested lacuna detected.",
                "candidate_count": 0,
            }
            continue
        best = max(candidates, key=lambda c: c.score)
        routes[key] = {
            "action": "ROUTE",
            "setting": best.setting,
            "family": best.family,
            "params": best.params,
            "score": best.score,
            "region": best.region.value,
            "beta": best.beta,
            "mean_return_pct": best.mean_return_pct,
            "mean_max_dd_pct": best.mean_max_dd_pct,
            "mean_trades": best.mean_trades,
            "candidate_count": len(candidates),
            "rpm_prerequisites": {
                "non_gap": True,
                "region": "active",
                "min_trades": min_trades,
                "max_drawdown_pct": max_drawdown_pct,
                "min_return_pct": min_return_pct,
            },
        }
    return routes


def serialize_cell(cell: ConditionCell) -> Dict[str, object]:
    data = dict(cell.__dict__)
    data["region"] = cell.region.value
    return data
