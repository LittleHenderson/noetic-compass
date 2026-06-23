"""Event-context labels for CAS FOREX condition routing.

These labels let the research harness separate normal market structure from
NFP/CPI/FOMC windows, conflict shocks, weekend gaps, and thin-liquidity states.
They are route-map context, not live-trading authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Sequence

from cas_forex.schemas.macro import MacroEventState, MacroEventType
from cas_forex.time_utils import ensure_utc


EVENT_CONTEXT_NORMAL = "normal"

EVENT_CONTEXT_PRIORITY = {
    "conflict_shock": 100,
    "post_FOMC": 91,
    "pre_FOMC": 90,
    "post_NFP": 81,
    "pre_NFP": 80,
    "post_CPI": 71,
    "pre_CPI": 70,
    "post_RATE_DECISION": 61,
    "pre_RATE_DECISION": 60,
    "post_GDP": 51,
    "pre_GDP": 50,
    "post_UNEMPLOYMENT": 41,
    "pre_UNEMPLOYMENT": 40,
    "post_CENTRAL_BANK_SPEECH": 31,
    "pre_CENTRAL_BANK_SPEECH": 30,
    "weekend_gap": 20,
    "liquidity_thin": 10,
    EVENT_CONTEXT_NORMAL: 0,
}

EVENT_CONTEXT_VOL_MULTIPLIER = {
    EVENT_CONTEXT_NORMAL: 1.0,
    "liquidity_thin": 1.25,
    "weekend_gap": 1.35,
    "pre_NFP": 1.3,
    "post_NFP": 1.7,
    "pre_CPI": 1.25,
    "post_CPI": 1.6,
    "pre_FOMC": 1.35,
    "post_FOMC": 1.8,
    "pre_RATE_DECISION": 1.3,
    "post_RATE_DECISION": 1.75,
    "pre_GDP": 1.15,
    "post_GDP": 1.35,
    "pre_UNEMPLOYMENT": 1.2,
    "post_UNEMPLOYMENT": 1.45,
    "pre_CENTRAL_BANK_SPEECH": 1.15,
    "post_CENTRAL_BANK_SPEECH": 1.35,
    "conflict_shock": 2.5,
}


@dataclass(frozen=True)
class EventWindow:
    label: str
    starts_at: datetime
    ends_at: datetime
    source: str = "manual"
    event_ref: str = ""
    severity: float = 1.0

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return self.starts_at <= end and self.ends_at >= start


def normalize_event_context(label: Optional[str]) -> str:
    raw = str(label or EVENT_CONTEXT_NORMAL).strip()
    return raw or EVENT_CONTEXT_NORMAL


def event_context_priority(label: str) -> int:
    return EVENT_CONTEXT_PRIORITY.get(normalize_event_context(label), 5)


def event_context_vol_multiplier(label: str) -> float:
    return EVENT_CONTEXT_VOL_MULTIPLIER.get(normalize_event_context(label), 1.0)


def _parse_candle_time(candle: dict) -> Optional[datetime]:
    value = candle.get("timestamp")
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    try:
        return ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except Exception:
        return None


def candle_time_range(candles: Sequence[dict]) -> Optional[tuple[datetime, datetime]]:
    times = [_parse_candle_time(candle) for candle in candles]
    valid = [time for time in times if time is not None]
    if not valid:
        return None
    return min(valid), max(valid)


def event_label_for_macro(event_type: MacroEventType, *, after: bool) -> str:
    phase = "post" if after else "pre"
    return f"{phase}_{event_type.value}"


def event_windows_from_macro_events(
    events: Iterable[MacroEventState],
    *,
    pre_minutes: Optional[int] = None,
    post_minutes: Optional[int] = None,
) -> List[EventWindow]:
    windows: List[EventWindow] = []
    for event in events:
        scheduled = ensure_utc(event.scheduled_at_utc)
        before = pre_minutes if pre_minutes is not None else event.blackout_before_minutes
        after = post_minutes if post_minutes is not None else event.blackout_after_minutes
        windows.append(
            EventWindow(
                label=event_label_for_macro(event.event_type, after=False),
                starts_at=scheduled - timedelta(minutes=before),
                ends_at=scheduled,
                source=event.source,
                event_ref=event.event_id,
                severity=0.8,
            )
        )
        windows.append(
            EventWindow(
                label=event_label_for_macro(event.event_type, after=True),
                starts_at=scheduled,
                ends_at=scheduled + timedelta(minutes=after),
                source=event.source,
                event_ref=event.event_id,
                severity=1.0,
            )
        )
    return windows


def event_context_for_candles(
    candles: Sequence[dict],
    *,
    event_windows: Optional[Sequence[EventWindow]] = None,
    default: str = EVENT_CONTEXT_NORMAL,
) -> str:
    if not event_windows:
        return normalize_event_context(default)
    candle_range = candle_time_range(candles)
    if candle_range is None:
        return normalize_event_context(default)
    start, end = candle_range
    matches = [window for window in event_windows if window.overlaps(start, end)]
    if not matches:
        return normalize_event_context(default)
    best = max(matches, key=lambda window: (event_context_priority(window.label), window.severity))
    return normalize_event_context(best.label)


def manual_event_window(
    label: str,
    starts_at: datetime,
    ends_at: datetime,
    *,
    event_ref: str = "",
    severity: float = 1.0,
) -> EventWindow:
    return EventWindow(
        label=normalize_event_context(label),
        starts_at=ensure_utc(starts_at),
        ends_at=ensure_utc(ends_at),
        source="manual",
        event_ref=event_ref,
        severity=severity,
    )
