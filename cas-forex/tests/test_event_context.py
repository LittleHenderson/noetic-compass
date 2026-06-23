from datetime import UTC, datetime, timedelta

from cas_forex.event_context import (
    event_context_for_candles,
    event_context_vol_multiplier,
    event_windows_from_macro_events,
    manual_event_window,
)
from cas_forex.schemas.macro import MacroEventState, MacroEventType


def _candles(start: datetime, count: int):
    return [
        {
            "timestamp": (start + timedelta(minutes=i)).isoformat(),
            "open": 1.0,
            "high": 1.1,
            "low": 0.9,
            "close": 1.0,
        }
        for i in range(count)
    ]


def test_macro_events_create_pre_and_post_context_windows():
    scheduled = datetime(2026, 7, 2, 12, 30, tzinfo=UTC)
    event = MacroEventState(
        event_id="nfp-test",
        event_type=MacroEventType.NFP,
        scheduled_at_utc=scheduled,
        blackout_before_minutes=15,
        blackout_after_minutes=15,
    )
    windows = event_windows_from_macro_events([event])

    assert event_context_for_candles(_candles(scheduled - timedelta(minutes=10), 3), event_windows=windows) == "pre_NFP"
    assert event_context_for_candles(_candles(scheduled + timedelta(minutes=1), 3), event_windows=windows) == "post_NFP"


def test_manual_conflict_window_overrides_macro_priority():
    scheduled = datetime(2026, 7, 2, 12, 30, tzinfo=UTC)
    event = MacroEventState(
        event_id="nfp-test",
        event_type=MacroEventType.NFP,
        scheduled_at_utc=scheduled,
    )
    windows = event_windows_from_macro_events([event])
    windows.append(
        manual_event_window(
            "conflict_shock",
            scheduled - timedelta(hours=1),
            scheduled + timedelta(hours=1),
            event_ref="manual-conflict",
            severity=1.0,
        )
    )

    assert event_context_for_candles(_candles(scheduled, 3), event_windows=windows) == "conflict_shock"
    assert event_context_vol_multiplier("conflict_shock") > event_context_vol_multiplier("post_NFP")
