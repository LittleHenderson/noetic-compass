"""Unit tests for ``cas_forex.notification_dispatcher_loop``.

Tests use a fake clock, fake sleeper, fake subscription store, and fake
dispatch closure so the loop is exercised without any real wall-clock
waits or real Web Push delivery.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable, List, Mapping

import pytest

from cas_forex.notification_dispatcher_loop import (
    STOP_MAX_CONSECUTIVE_FAILURES,
    STOP_MAX_TICKS,
    STOP_SHUTDOWN_SIGNAL,
    NotificationDispatcherLoop,
    NotificationLoopRunSummary,
    NotificationLoopTickResult,
)
from cas_forex.push_notifications import (
    PushDispatchResult,
    PushSubscription,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)


class FakeSleeper:
    def __init__(self, clock: FakeClock | None = None) -> None:
        self.clock = clock
        self.calls: List[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(float(seconds))
        if self.clock is not None:
            self.clock.advance(float(seconds))


class FakeStore:
    """In-memory stand-in for :class:`PushSubscriptionStore`."""

    def __init__(self, subs: List[PushSubscription] | None = None) -> None:
        self._subs = list(subs or [])

    def list_all(self) -> List[PushSubscription]:
        return list(self._subs)


def _make_sub(endpoint: str = "https://push.example/abc") -> PushSubscription:
    return PushSubscription(
        endpoint=endpoint,
        keys_p256dh="p256_" + endpoint[-6:],
        keys_auth="auth_" + endpoint[-6:],
        created_at_iso="2026-06-25T00:00:00+00:00",
    )


def _ok_dispatch(_sub: PushSubscription, _payload: dict) -> PushDispatchResult:
    return PushDispatchResult(
        endpoint=_sub.endpoint, success=True, status_code=201, error_message=None
    )


def _make_loader(snapshots: List[Mapping[str, Any] | Exception]):
    """Return a loader that yields the next snapshot/exception per call."""

    state = {"i": 0}

    def load() -> Mapping[str, Any]:
        i = state["i"]
        state["i"] = i + 1
        if i >= len(snapshots):
            return {}
        outcome = snapshots[i]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return load


def _trade_executed_snapshot(
    *,
    cycle_id: str = "cyc-1",
    broker_ticket: str = "T-1",
) -> dict[str, Any]:
    """A state snapshot that fires the TRADE_EXECUTED detector."""
    return {
        "latest_cycle_report": {
            "cycle_id": cycle_id,
            "broker_ticket": broker_ticket,
            "receipt_verified": True,
            "side": "buy",
            "symbol": "EURUSD",
            "lots": 0.01,
        },
        "latest_decision": None,
        "loop_health": None,
        "mt5_probe": None,
        "readiness": None,
    }


# ---------------------------------------------------------------------------
# 1. max_ticks with no events
# ---------------------------------------------------------------------------


def test_max_ticks_with_no_events(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([{}, {}, {}]),
        store=FakeStore([_make_sub()]),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=tmp_path / "prev.json",
        tick_interval_seconds=10.0,
        max_ticks=3,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    assert isinstance(summary, NotificationLoopRunSummary)
    assert summary.total_ticks == 3
    assert summary.events_fired_total == 0
    assert summary.events_dispatched_total == 0
    assert summary.stopped_reason == STOP_MAX_TICKS
    assert summary.last_tick is not None
    assert summary.last_tick.snapshot_loaded is True
    assert sleeper.calls == [10.0, 10.0]


# ---------------------------------------------------------------------------
# 2. Single TRADE_EXECUTED event fires once per tick × subscriptions
# ---------------------------------------------------------------------------


def test_trade_executed_fires_per_subscription(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    subs = [_make_sub("https://push.example/a"), _make_sub("https://push.example/b")]
    dispatched: List[tuple[str, str]] = []

    def dispatch(sub: PushSubscription, payload: dict) -> PushDispatchResult:
        dispatched.append((sub.endpoint, payload["event_kind"]))
        return _ok_dispatch(sub, payload)

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([_trade_executed_snapshot()]),
        store=FakeStore(subs),
        dispatch_fn=dispatch,
        previous_snapshot_path=tmp_path / "prev.json",
        tick_interval_seconds=10.0,
        max_ticks=1,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    assert summary.total_ticks == 1
    assert summary.events_fired_total == 1
    # 1 event × 2 subs = 2 dispatches
    assert summary.events_dispatched_total == 2
    assert len(dispatched) == 2
    assert all(kind == "TRADE_EXECUTED" for _, kind in dispatched)
    assert summary.last_tick is not None
    assert summary.last_tick.events_fired == ("TRADE_EXECUTED",)
    assert summary.last_tick.subscriptions_count == 2


# ---------------------------------------------------------------------------
# 3. Same event NOT re-fired on second tick (previous_snapshot dedupe)
# ---------------------------------------------------------------------------


def test_event_not_refired_when_previous_snapshot_persisted(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    prev_path = tmp_path / "prev.json"
    snap = _trade_executed_snapshot()

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([snap, snap]),
        store=FakeStore([_make_sub()]),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=prev_path,
        tick_interval_seconds=10.0,
        max_ticks=2,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    assert summary.total_ticks == 2
    # Tick 1 fires once (first observation). Tick 2 dedupes via persisted prev.
    assert summary.events_fired_total == 1
    assert summary.events_dispatched_total == 1
    # Persisted file must exist and round-trip JSON.
    assert prev_path.exists()
    persisted = json.loads(prev_path.read_text(encoding="utf-8"))
    assert persisted["latest_cycle_report"]["cycle_id"] == "cyc-1"


# ---------------------------------------------------------------------------
# 4. shutdown_event set → stops with "shutdown_signal"
# ---------------------------------------------------------------------------


def test_shutdown_event_stops_loop(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    event = threading.Event()
    event.set()  # set before run() so first iteration check stops it.

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([{}]),
        store=FakeStore(),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=tmp_path / "prev.json",
        tick_interval_seconds=10.0,
        clock=clock,
        sleeper=sleeper,
        shutdown_event=event,
    )

    summary = loop.run()

    assert summary.stopped_reason == STOP_SHUTDOWN_SIGNAL
    assert summary.total_ticks == 0
    assert sleeper.calls == []


# ---------------------------------------------------------------------------
# 5. snapshot load raises → tick recorded as failed, counts toward
#    consecutive failures
# ---------------------------------------------------------------------------


def test_snapshot_load_failure_marks_tick_failed(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    boom = RuntimeError("disk on fire")

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([boom, {}, {}]),
        store=FakeStore(),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=tmp_path / "prev.json",
        tick_interval_seconds=10.0,
        max_ticks=3,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    assert summary.total_ticks == 3
    # The first tick failed with the documented error message; second/third are clean.
    assert summary.last_tick is not None
    assert summary.last_tick.error_message is None
    # Sleeper saw a backoff on tick 0 (factor 2) then nominal intervals.
    assert sleeper.calls == [20.0, 10.0]


# ---------------------------------------------------------------------------
# 6. max_consecutive_failures reached → stops with that reason
# ---------------------------------------------------------------------------


def test_max_consecutive_failures_stops_loop(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    boom = RuntimeError("nope")

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([boom, boom, boom]),
        store=FakeStore(),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=tmp_path / "prev.json",
        tick_interval_seconds=1.0,
        max_consecutive_failures=2,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    assert summary.stopped_reason == STOP_MAX_CONSECUTIVE_FAILURES
    assert summary.total_ticks == 2
    assert summary.last_tick is not None
    assert summary.last_tick.error_message is not None
    assert "nope" in summary.last_tick.error_message


# ---------------------------------------------------------------------------
# 7. Corrupted previous_snapshot_path → tick proceeds with previous=None
# ---------------------------------------------------------------------------


def test_corrupted_previous_snapshot_treated_as_none(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    prev_path = tmp_path / "prev.json"
    prev_path.write_text("{this is not json", encoding="utf-8")

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([_trade_executed_snapshot()]),
        store=FakeStore([_make_sub()]),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=prev_path,
        tick_interval_seconds=10.0,
        max_ticks=1,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    # Previous treated as None → first observation fires TRADE_EXECUTED.
    assert summary.events_fired_total == 1
    assert summary.events_dispatched_total == 1
    # The corrupted file is overwritten by the atomic persist.
    persisted = json.loads(prev_path.read_text(encoding="utf-8"))
    assert persisted["latest_cycle_report"]["cycle_id"] == "cyc-1"


# ---------------------------------------------------------------------------
# 8. Atomic persist: simulated I/O error → previous file unchanged
# ---------------------------------------------------------------------------


def test_atomic_persist_failure_leaves_previous_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    prev_path = tmp_path / "prev.json"
    # Pre-seed with a known-good baseline state we expect to survive the failure.
    baseline = {"sentinel": "untouched"}
    prev_path.write_text(json.dumps(baseline), encoding="utf-8")

    # Force os.replace to raise so the atomic swap fails.
    real_replace = os.replace

    def boom_replace(src: str, dst: str) -> None:
        if str(dst) == str(prev_path):
            raise OSError("simulated replace failure")
        real_replace(src, dst)

    monkeypatch.setattr(
        "cas_forex.notification_dispatcher_loop.os.replace", boom_replace
    )

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([_trade_executed_snapshot()]),
        store=FakeStore([_make_sub()]),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=prev_path,
        tick_interval_seconds=10.0,
        max_ticks=1,
        clock=clock,
        sleeper=sleeper,
    )

    summary = loop.run()

    # The dispatch still happened; only the persist failed.
    assert summary.events_dispatched_total == 1
    # Baseline file content survived.
    persisted = json.loads(prev_path.read_text(encoding="utf-8"))
    assert persisted == baseline
    # Tick's error_message surfaces the persist failure.
    assert summary.last_tick is not None
    assert summary.last_tick.error_message is not None
    assert "simulated replace failure" in summary.last_tick.error_message
    # No leftover .tmp files in the directory.
    leftover_tmps = [p for p in prev_path.parent.iterdir() if p.suffix == ".tmp"]
    assert leftover_tmps == []


# ---------------------------------------------------------------------------
# 9. on_tick callback called once per tick with the right result
# ---------------------------------------------------------------------------


def test_on_tick_callback_called_per_tick(tmp_path: Path) -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    received: List[NotificationLoopTickResult] = []

    loop = NotificationDispatcherLoop(
        load_state_snapshot=_make_loader([{}, {}, {}]),
        store=FakeStore([_make_sub()]),
        dispatch_fn=_ok_dispatch,
        previous_snapshot_path=tmp_path / "prev.json",
        tick_interval_seconds=5.0,
        max_ticks=3,
        clock=clock,
        sleeper=sleeper,
        on_tick=received.append,
    )

    summary = loop.run()

    assert summary.total_ticks == 3
    assert len(received) == 3
    assert [r.tick_index for r in received] == [0, 1, 2]
    assert all(r.snapshot_loaded for r in received)
    assert all(isinstance(r, NotificationLoopTickResult) for r in received)
