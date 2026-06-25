"""Unit tests for ``cas_forex.autowake_supervisor.AutowakeSupervisor``.

Tests use a fake clock and fake sleeper so the supervisor loop can be
exercised without any real wall-clock waits.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, List, Mapping

import pytest

from cas_forex.autowake_supervisor import (
    AutowakeSupervisor,
    STOP_DURATION_CAP,
    STOP_MAX_CONSECUTIVE_FAILURES,
    STOP_MAX_TICKS,
    STOP_SHUTDOWN_SIGNAL,
    SupervisorRunSummary,
    SupervisorTickResult,
)


class FakeClock:
    """Monotonic-style clock whose ``advance_on_sleep`` flag lets the
    sleeper move virtual time forward by the requested seconds."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)


class FakeSleeper:
    """Sleeper that records its calls and (optionally) advances a clock."""

    def __init__(self, clock: FakeClock | None = None) -> None:
        self.clock = clock
        self.calls: List[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(float(seconds))
        if self.clock is not None:
            self.clock.advance(float(seconds))


def _make_tick_sequence(outcomes: List[Mapping[str, Any] | Exception]) -> Callable[[], Mapping[str, Any]]:
    """Build a tick callable that walks through ``outcomes`` one per call."""

    state = {"i": 0}

    def tick() -> Mapping[str, Any]:
        i = state["i"]
        state["i"] = i + 1
        if i >= len(outcomes):
            return {"ok": True, "index": i}
        outcome = outcomes[i]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return tick


def test_supervisor_stops_at_max_ticks_with_all_successes() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    tick = _make_tick_sequence([
        {"ok": True, "n": 1},
        {"ok": True, "n": 2},
        {"ok": True, "n": 3},
    ])
    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=10.0,
        max_ticks=3,
        clock=clock,
        sleeper=sleeper,
    )

    summary = supervisor.run()

    assert isinstance(summary, SupervisorRunSummary)
    assert summary.total_ticks == 3
    assert summary.successful_ticks == 3
    assert summary.failed_ticks == 0
    assert summary.consecutive_failures_at_stop == 0
    assert summary.stopped_reason == STOP_MAX_TICKS
    assert summary.last_tick_result is not None
    assert summary.last_tick_result.succeeded is True
    assert summary.last_tick_result.payload == {"ok": True, "n": 3}
    # We do not sleep after the terminating tick.
    assert sleeper.calls == [10.0, 10.0]


def test_supervisor_stops_at_max_consecutive_failures_when_every_tick_raises() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    tick = _make_tick_sequence([RuntimeError("boom")] * 20)
    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=1.0,
        max_ticks=10,
        max_consecutive_failures=4,
        clock=clock,
        sleeper=sleeper,
    )

    summary = supervisor.run()

    assert summary.stopped_reason == STOP_MAX_CONSECUTIVE_FAILURES
    assert summary.total_ticks == 4
    assert summary.failed_ticks == 4
    assert summary.successful_ticks == 0
    assert summary.consecutive_failures_at_stop == 4
    assert summary.last_tick_result is not None
    assert summary.last_tick_result.succeeded is False
    assert summary.last_tick_result.error_message is not None
    assert "RuntimeError" in summary.last_tick_result.error_message


def test_supervisor_resets_consecutive_failures_after_success() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    tick = _make_tick_sequence([
        RuntimeError("first"),
        RuntimeError("second"),
        {"ok": True},          # success resets counter
        RuntimeError("third"),
        RuntimeError("fourth"),
        {"ok": True, "final": True},
    ])
    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=1.0,
        max_ticks=6,
        max_consecutive_failures=3,
        clock=clock,
        sleeper=sleeper,
    )

    summary = supervisor.run()

    assert summary.stopped_reason == STOP_MAX_TICKS
    assert summary.total_ticks == 6
    assert summary.successful_ticks == 2
    assert summary.failed_ticks == 4
    assert summary.consecutive_failures_at_stop == 0
    assert summary.last_tick_result is not None
    assert summary.last_tick_result.succeeded is True
    assert summary.last_tick_result.payload == {"ok": True, "final": True}


def test_supervisor_exits_immediately_when_shutdown_event_pre_set() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    tick_calls = {"count": 0}

    def tick() -> Mapping[str, Any]:
        tick_calls["count"] += 1
        return {"ok": True}

    shutdown = threading.Event()
    shutdown.set()
    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=1.0,
        max_ticks=5,
        clock=clock,
        sleeper=sleeper,
        shutdown_event=shutdown,
    )

    summary = supervisor.run()

    assert summary.stopped_reason == STOP_SHUTDOWN_SIGNAL
    assert summary.total_ticks == 0
    assert tick_calls["count"] == 0
    assert sleeper.calls == []
    assert summary.last_tick_result is None


def test_supervisor_stops_when_duration_cap_reached_via_fake_clock() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)  # sleeper advances the clock by sleep seconds
    tick = _make_tick_sequence([{"ok": True}] * 10)
    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=0.4,
        max_total_duration_seconds=1.0,
        clock=clock,
        sleeper=sleeper,
    )

    summary = supervisor.run()

    assert summary.stopped_reason == STOP_DURATION_CAP
    # Each successful tick sleeps 0.4s; we run 3 ticks (advancing clock to
    # 0.4, 0.8, 1.2) before the next iteration's duration check fires.
    assert summary.total_ticks == 3
    assert summary.successful_ticks == 3
    assert summary.failed_ticks == 0
    assert clock.now >= 1.0


def test_supervisor_backs_off_at_least_twice_interval_on_failure() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    tick = _make_tick_sequence([
        RuntimeError("oops"),
        {"ok": True, "recovered": True},
    ])
    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=2.0,
        max_ticks=2,
        max_consecutive_failures=3,
        clock=clock,
        sleeper=sleeper,
    )

    summary = supervisor.run()

    assert summary.stopped_reason == STOP_MAX_TICKS
    assert summary.total_ticks == 2
    assert summary.successful_ticks == 1
    assert summary.failed_ticks == 1
    # After the first failure consecutive_failures=1, backoff = 2 * 2**1 = 4.
    assert sleeper.calls, "expected at least one sleep call after the failed tick"
    assert sleeper.calls[0] >= 2.0 * 2
    assert sleeper.calls[0] == pytest.approx(4.0)


def test_supervisor_invokes_on_tick_callback_once_per_tick() -> None:
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    tick = _make_tick_sequence([
        {"ok": True, "n": 1},
        RuntimeError("nope"),
        {"ok": True, "n": 3},
    ])
    seen: List[SupervisorTickResult] = []

    def on_tick(result: SupervisorTickResult) -> None:
        seen.append(result)

    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=1.0,
        max_ticks=3,
        max_consecutive_failures=5,
        clock=clock,
        sleeper=sleeper,
        on_tick=on_tick,
    )

    summary = supervisor.run()

    assert summary.stopped_reason == STOP_MAX_TICKS
    assert len(seen) == 3
    assert [r.tick_index for r in seen] == [0, 1, 2]
    assert seen[0].succeeded is True
    assert seen[0].payload == {"ok": True, "n": 1}
    assert seen[0].completed_at_iso is not None
    assert seen[0].error_message is None
    assert seen[1].succeeded is False
    assert seen[1].payload is None
    assert seen[1].completed_at_iso is None
    assert seen[1].error_message is not None and "RuntimeError" in seen[1].error_message
    assert seen[2].succeeded is True
    assert seen[2].payload == {"ok": True, "n": 3}


def test_supervisor_rejects_invalid_construction_parameters() -> None:
    tick = _make_tick_sequence([{"ok": True}])
    with pytest.raises(ValueError):
        AutowakeSupervisor(tick=tick, tick_interval_seconds=0)
    with pytest.raises(ValueError):
        AutowakeSupervisor(tick=tick, tick_interval_seconds=1.0, max_consecutive_failures=0)
    with pytest.raises(ValueError):
        AutowakeSupervisor(tick=tick, tick_interval_seconds=1.0, max_ticks=0)
    with pytest.raises(ValueError):
        AutowakeSupervisor(
            tick=tick,
            tick_interval_seconds=1.0,
            max_total_duration_seconds=0,
        )
