"""Condition outcome tallies for CAS FOREX walk-forward evidence.

This is the scoreboard for the analyze/simulate/switch loop. It groups
walk-forward windows by market condition so strong pockets stay visible while
the broader simulator keeps expanding.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Sequence


DEFAULT_TALLY_AXES = (
    "symbol",
    "timeframe",
    "test_event_context",
    "test_regime",
    "route_action",
    "setting",
)

CLAIM_BOUNDARY = "Research-only condition tally. Live trading remains NOT LICENSED."


@dataclass
class ConditionOutcomeBucket:
    key: str
    axes: Dict[str, Any]
    windows: int = 0
    routed_windows: int = 0
    no_trade_windows: int = 0
    active_windows: int = 0
    positive_windows: int = 0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    trades: int = 0
    settings_seen: set[str] = field(default_factory=set)

    def add(self, window: Any) -> None:
        route_action = str(_window_value(window, "route_action", "NO_TRADE"))
        setting = str(_window_value(window, "setting", "NO_TRADE") or "NO_TRADE")
        return_pct = float(_window_value(window, "test_return_pct", 0.0) or 0.0)
        drawdown_pct = float(_window_value(window, "test_max_dd_pct", 0.0) or 0.0)
        trades = int(_window_value(window, "test_trades", 0) or 0)

        self.windows += 1
        self.settings_seen.add(setting)
        self.total_return_pct += return_pct
        self.max_drawdown_pct = max(self.max_drawdown_pct, drawdown_pct)
        self.trades += trades
        if route_action == "ROUTE":
            self.routed_windows += 1
            if trades > 0:
                self.active_windows += 1
            if return_pct > 0:
                self.positive_windows += 1
        else:
            self.no_trade_windows += 1

    def as_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "axes": dict(self.axes),
            "windows": self.windows,
            "routed_windows": self.routed_windows,
            "no_trade_windows": self.no_trade_windows,
            "active_windows": self.active_windows,
            "positive_windows": self.positive_windows,
            "positive_window_rate": round(self.positive_windows / self.windows, 4) if self.windows else 0.0,
            "active_window_rate": round(self.active_windows / self.windows, 4) if self.windows else 0.0,
            "total_return_pct": round(self.total_return_pct, 4),
            "mean_return_pct": round(self.total_return_pct / self.windows, 4) if self.windows else 0.0,
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "trades": self.trades,
            "settings_seen": sorted(self.settings_seen),
        }


def tally_walk_forward_conditions(
    windows: Sequence[Any],
    *,
    axes: Sequence[str] = DEFAULT_TALLY_AXES,
) -> Dict[str, Any]:
    """Aggregate walk-forward windows by condition axes."""
    buckets: dict[str, ConditionOutcomeBucket] = {}
    for window in windows:
        axes_values = {axis: _axis_value(window, axis) for axis in axes}
        key = "|".join(f"{axis}={axes_values[axis]}" for axis in axes)
        if key not in buckets:
            buckets[key] = ConditionOutcomeBucket(key=key, axes=axes_values)
        buckets[key].add(window)

    bucket_dicts = [bucket.as_dict() for bucket in buckets.values()]
    bucket_dicts.sort(
        key=lambda bucket: (
            bucket["routed_windows"],
            bucket["positive_window_rate"],
            bucket["mean_return_pct"],
            -bucket["max_drawdown_pct"],
        ),
        reverse=True,
    )
    return {
        "summary": _summary(windows, bucket_dicts),
        "axes": list(axes),
        "buckets": bucket_dicts,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def tally_by_event_context(windows: Sequence[Any]) -> Dict[str, Any]:
    """Convenience tally for NFP/CPI/FOMC/conflict-style condition review."""
    return tally_walk_forward_conditions(
        windows,
        axes=("test_event_context", "symbol", "timeframe", "route_action", "setting"),
    )


def _summary(windows: Sequence[Any], bucket_dicts: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    routed = sum(1 for window in windows if _window_value(window, "route_action", "NO_TRADE") == "ROUTE")
    positive = sum(
        1
        for window in windows
        if _window_value(window, "route_action", "NO_TRADE") == "ROUTE"
        and float(_window_value(window, "test_return_pct", 0.0) or 0.0) > 0.0
    )
    events: dict[str, int] = defaultdict(int)
    for window in windows:
        events[str(_window_value(window, "test_event_context", "normal") or "normal")] += 1
    return {
        "windows": len(windows),
        "buckets": len(bucket_dicts),
        "routed_windows": routed,
        "no_trade_windows": len(windows) - routed,
        "positive_routed_windows": positive,
        "positive_routed_window_rate": round(positive / routed, 4) if routed else 0.0,
        "event_context_counts": dict(sorted(events.items())),
    }


def _axis_value(window: Any, axis: str) -> Any:
    value = _window_value(window, axis, None)
    if axis == "setting" and not value:
        return "NO_TRADE"
    if "event_context" in axis and value is None:
        return "normal"
    if value is None:
        return "unknown"
    return value


def _window_value(window: Any, field_name: str, default: Any = None) -> Any:
    aliases = {
        "event_context": "test_event_context",
        "regime": "test_regime",
        "vol_mult": "test_vol_mult",
    }
    lookup_name = aliases.get(field_name, field_name)
    if isinstance(window, Mapping):
        if lookup_name in window:
            return window.get(lookup_name, default)
        if lookup_name == "test_event_context":
            return window.get("event_context", default)
        if lookup_name == "test_regime":
            return window.get("regime", default)
        if lookup_name == "test_vol_mult":
            return window.get("vol_mult", default)
        return default
    return getattr(window, lookup_name, default)
