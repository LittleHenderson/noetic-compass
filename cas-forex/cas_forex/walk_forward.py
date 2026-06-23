"""Walk-forward validation for CAS FOREX condition routes.

This freezes an RPM route map learned on a training window, then evaluates only
the next untouched test window. It is research evidence, not live permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from cas_forex.condition_lab import (
    SampleMetrics,
    StrategySetting,
    condition_label_for_candles,
    normalize_timeframe,
    rpm_route_table,
    run_candles_sample,
    run_real_condition_grid,
    time_scale_for_timeframe,
)
from cas_forex.event_context import (
    EVENT_CONTEXT_NORMAL,
    EventWindow,
    event_context_for_candles,
    normalize_event_context,
)


@dataclass
class WalkForwardWindow:
    window_index: int
    symbol: str
    timeframe: str
    time_scale: str
    train_start_index: int
    train_end_index: int
    test_start_index: int
    test_end_index: int
    train_start_timestamp: Optional[str]
    train_end_timestamp: Optional[str]
    test_start_timestamp: Optional[str]
    test_end_timestamp: Optional[str]
    test_regime: str
    test_vol_mult: float
    test_event_context: str
    route_key: str
    route_action: str
    setting: Optional[str] = None
    family: Optional[str] = None
    train_cells: int = 0
    train_routes: int = 0
    train_no_trade: int = 0
    test_return_pct: float = 0.0
    test_max_dd_pct: float = 0.0
    test_trades: int = 0
    test_win_rate: float = 0.0
    test_profit_factor: float = 0.0
    test_suppressed_trades: int = 0
    notes: List[str] = field(default_factory=list)


@dataclass
class WalkForwardReport:
    windows: List[WalkForwardWindow]
    summary: Dict[str, object]


def split_walk_forward_ranges(
    total_bars: int,
    *,
    train_bars: int,
    test_bars: int,
    step_bars: Optional[int] = None,
) -> List[Tuple[int, int, int, int]]:
    """Return train/test index ranges as half-open intervals."""
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    step = step_bars or test_bars
    if step <= 0:
        raise ValueError("step_bars must be positive")
    ranges: List[Tuple[int, int, int, int]] = []
    start = 0
    while start + train_bars + test_bars <= total_bars:
        train_start = start
        train_end = start + train_bars
        test_start = train_end
        test_end = test_start + test_bars
        ranges.append((train_start, train_end, test_start, test_end))
        start += step
    return ranges


def summarize_walk_forward_windows(
    windows: Sequence[WalkForwardWindow],
    *,
    min_routed_windows: int = 2,
    max_oos_drawdown_pct: float = 20.0,
    min_positive_window_rate: float = 0.5,
) -> Dict[str, object]:
    routed = [w for w in windows if w.route_action == "ROUTE"]
    active = [w for w in routed if w.test_trades > 0]
    positive = [w for w in routed if w.test_return_pct > 0]
    positive_active = [w for w in active if w.test_return_pct > 0]
    total_return = float(sum(w.test_return_pct for w in routed))
    mean_return = float(np.mean([w.test_return_pct for w in routed])) if routed else 0.0
    active_mean_return = float(np.mean([w.test_return_pct for w in active])) if active else 0.0
    max_dd = float(max((w.test_max_dd_pct for w in routed), default=0.0))
    positive_rate = len(positive) / len(routed) if routed else 0.0
    positive_active_rate = len(positive_active) / len(active) if active else 0.0
    total_trades = int(sum(w.test_trades for w in routed))
    grade = "NOT_PROMOTED"
    if (
        len(routed) >= min_routed_windows
        and mean_return > 0
        and positive_rate >= min_positive_window_rate
        and max_dd <= max_oos_drawdown_pct
        and total_trades > 0
    ):
        grade = "WALK_FORWARD_LEAD"
    return {
        "windows": len(windows),
        "routed_windows": len(routed),
        "no_trade_windows": len(windows) - len(routed),
        "active_routed_windows": len(active),
        "positive_routed_windows": len(positive),
        "positive_routed_window_rate": round(positive_rate, 4),
        "positive_active_routed_windows": len(positive_active),
        "positive_active_routed_window_rate": round(positive_active_rate, 4),
        "routed_total_return_pct_sum": round(total_return, 4),
        "routed_mean_return_pct": round(mean_return, 4),
        "active_routed_mean_return_pct": round(active_mean_return, 4),
        "routed_max_drawdown_pct": round(max_dd, 4),
        "routed_total_trades": total_trades,
        "research_grade": grade,
        "claim_boundary": "Research-only walk-forward result. Live trading remains NOT LICENSED.",
    }


def _route_key(
    symbol: str,
    timeframe: str,
    event_context: str,
    regime: str,
    vol_mult: float,
) -> str:
    tf = normalize_timeframe(timeframe)
    scale = time_scale_for_timeframe(tf)
    event_context = normalize_event_context(event_context)
    return (
        f"source=real|symbol={symbol}|time_scale={scale}|timeframe={tf}|"
        f"event_context={event_context}|regime={regime}|vol_mult={float(vol_mult)}"
    )


def _timestamp(candles: Sequence[dict], index: int) -> Optional[str]:
    if not candles:
        return None
    safe_index = min(max(index, 0), len(candles) - 1)
    value = candles[safe_index].get("timestamp")
    return str(value) if value is not None else None


def required_context_bars(setting: StrategySetting) -> int:
    """Minimum lookback context needed before the first test trade."""
    values = [80]
    for key in ("lookback", "baseline", "trend_lookback", "slow", "mid", "fast", "pullback_lookback"):
        value = setting.params.get(key)
        if isinstance(value, (int, float)) and value > 0:
            values.append(int(value))
    return max(values)


def evaluate_walk_forward_routes(
    *,
    candles_by_symbol: Dict[str, List[dict]],
    settings: Sequence[StrategySetting],
    timeframe: str = "D1",
    event_windows: Optional[Sequence[EventWindow]] = None,
    train_bars: int = 756,
    test_bars: int = 126,
    step_bars: Optional[int] = None,
    train_segment_bars: int = 252,
    train_step_bars: int = 63,
    starting_balance: float = 10_000.0,
    position_lots: float = 0.05,
    spread_pips: float = 1.0,
    extra_cost_pips: float = 0.5,
    rpm_min_trades: float = 5.0,
    rpm_max_dd: float = 20.0,
    rpm_min_return: float = 0.0,
) -> WalkForwardReport:
    """Train RPM routes on rolling history, then test the frozen next window."""
    if not settings:
        raise ValueError("At least one strategy setting is required")

    canonical_tf = normalize_timeframe(timeframe)
    time_scale = time_scale_for_timeframe(canonical_tf)
    setting_lookup = {setting.name: setting for setting in settings}
    windows: List[WalkForwardWindow] = []

    for symbol, candles in candles_by_symbol.items():
        ranges = split_walk_forward_ranges(
            len(candles),
            train_bars=train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
        )
        for window_index, (train_start, train_end, test_start, test_end) in enumerate(ranges):
            train = candles[train_start:train_end]
            test = candles[test_start:test_end]
            train_cells = run_real_condition_grid(
                candles_by_symbol={symbol: train},
                settings=settings,
                timeframe=canonical_tf,
                event_windows=event_windows,
                segment_bars=min(train_segment_bars, len(train)),
                step_bars=max(1, min(train_step_bars, len(train))),
                starting_balance=starting_balance,
                position_lots=position_lots,
                spread_pips=spread_pips,
                extra_cost_pips=extra_cost_pips,
            )
            routes = rpm_route_table(
                train_cells,
                min_trades=rpm_min_trades,
                max_drawdown_pct=rpm_max_dd,
                min_return_pct=rpm_min_return,
            )
            test_regime, test_vol_mult = condition_label_for_candles(test, baseline_candles=train)
            test_event_context = event_context_for_candles(
                test,
                event_windows=event_windows,
                default=EVENT_CONTEXT_NORMAL,
            )
            key = _route_key(symbol, canonical_tf, test_event_context, test_regime, test_vol_mult)
            route = routes.get(key)
            route_count = sum(1 for value in routes.values() if value["action"] == "ROUTE")
            no_trade_count = len(routes) - route_count

            window = WalkForwardWindow(
                window_index=window_index,
                symbol=symbol,
                timeframe=canonical_tf,
                time_scale=time_scale,
                train_start_index=train_start,
                train_end_index=train_end,
                test_start_index=test_start,
                test_end_index=test_end,
                train_start_timestamp=_timestamp(candles, train_start),
                train_end_timestamp=_timestamp(candles, train_end - 1),
                test_start_timestamp=_timestamp(candles, test_start),
                test_end_timestamp=_timestamp(candles, test_end - 1),
                test_regime=test_regime,
                test_vol_mult=float(test_vol_mult),
                test_event_context=test_event_context,
                route_key=key,
                route_action="NO_TRADE",
                train_cells=len(train_cells),
                train_routes=route_count,
                train_no_trade=no_trade_count,
            )

            if route is None:
                window.notes.append("No exact trained RPM route for the future test condition.")
                windows.append(window)
                continue
            if route["action"] != "ROUTE":
                window.notes.append(str(route.get("reason", "RPM selected NO_TRADE.")))
                windows.append(window)
                continue

            setting_name = str(route["setting"])
            setting = setting_lookup[setting_name]
            context_bars = min(len(train), required_context_bars(setting))
            evaluation_candles = train[-context_bars:] + test
            metrics: SampleMetrics = run_candles_sample(
                evaluation_candles,
                symbol,
                setting,
                starting_balance=starting_balance,
                position_lots=position_lots,
                spread_pips=spread_pips,
                extra_cost_pips=extra_cost_pips,
                warmup_bars=context_bars,
            )
            window.route_action = "ROUTE"
            window.setting = setting.name
            window.family = setting.family
            window.notes.append(f"Used {context_bars} prior training bars as signal context; trades begin in test window.")
            window.test_return_pct = round(metrics.return_pct, 4)
            window.test_max_dd_pct = round(metrics.max_dd_pct, 4)
            window.test_trades = metrics.total_trades
            window.test_win_rate = round(metrics.win_rate, 4)
            window.test_profit_factor = round(metrics.profit_factor, 4)
            window.test_suppressed_trades = metrics.suppressed_trades
            windows.append(window)

    return WalkForwardReport(
        windows=windows,
        summary=summarize_walk_forward_windows(windows, max_oos_drawdown_pct=rpm_max_dd),
    )


def serialize_walk_forward_window(window: WalkForwardWindow) -> Dict[str, object]:
    return dict(window.__dict__)


def serialize_walk_forward_report(report: WalkForwardReport) -> Dict[str, object]:
    return {
        "summary": dict(report.summary),
        "windows": [serialize_walk_forward_window(window) for window in report.windows],
    }
