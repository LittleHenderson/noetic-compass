"""Long-running supervisor for the CAS Forex session autowake runner.

The supervisor takes a "tick" callable (e.g. one evaluation of the session
autowake runner), runs it on a fixed cadence, logs each tick's outcome, and
restarts on uncaught exceptions with capped exponential backoff. It is built
to be unit-testable without real wall-clock sleeps: callers inject a ``clock``
(monotonic time source) and a ``sleeper`` (sleep callable). A shutdown
``threading.Event`` lets a signal handler request graceful exit.

The supervisor itself does not implement any trading or broker logic — it is a
pure scheduling primitive. The tick callable is responsible for actually
evaluating session autowake events, running cycles, etc. See
``cas_forex.session_autowake_runner`` for the production tick target.
"""

from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Optional


__all__ = [
    "SupervisorTickResult",
    "SupervisorRunSummary",
    "AutowakeSupervisor",
    "STOP_MAX_TICKS",
    "STOP_SHUTDOWN_SIGNAL",
    "STOP_MAX_CONSECUTIVE_FAILURES",
    "STOP_DURATION_CAP",
]


STOP_MAX_TICKS = "max_ticks"
STOP_SHUTDOWN_SIGNAL = "shutdown_signal"
STOP_MAX_CONSECUTIVE_FAILURES = "max_consecutive_failures"
STOP_DURATION_CAP = "duration_cap"

_BACKOFF_CAP_MULTIPLIER = 30


@dataclass(frozen=True)
class SupervisorTickResult:
    """Outcome of a single supervisor tick.

    Attributes
    ----------
    tick_index:
        Zero-based index of this tick across the supervisor run.
    started_at_iso:
        UTC ISO-8601 timestamp captured just before calling the tick.
    completed_at_iso:
        UTC ISO-8601 timestamp captured after the tick returned. ``None`` if
        the tick raised an exception.
    succeeded:
        ``True`` when the tick returned a payload without raising.
    error_message:
        Short string describing the exception when the tick failed; ``None``
        on success.
    payload:
        The mapping returned by the tick callable on success; ``None`` when
        the tick raised.
    """

    tick_index: int
    started_at_iso: str
    completed_at_iso: Optional[str]
    succeeded: bool
    error_message: Optional[str]
    payload: Optional[Mapping[str, Any]]


@dataclass(frozen=True)
class SupervisorRunSummary:
    """Aggregate outcome of a supervisor ``run()`` invocation."""

    total_ticks: int
    successful_ticks: int
    failed_ticks: int
    consecutive_failures_at_stop: int
    stopped_reason: str
    last_tick_result: Optional[SupervisorTickResult]


class AutowakeSupervisor:
    """Schedule a tick callable on a fixed cadence with backoff and shutdown.

    Parameters
    ----------
    tick:
        Callable invoked once per iteration. On success it must return a
        mapping (typically the session autowake report). Exceptions are
        caught and logged; they do not propagate out of ``run()`` unless
        they come from the injected ``clock``, ``sleeper``, or ``on_tick``.
    tick_interval_seconds:
        Base cadence between ticks. Must be > 0.
    max_ticks:
        Optional cap on total ticks executed. ``None`` means unbounded.
    max_consecutive_failures:
        Stop after this many consecutive failures. Must be >= 1.
    max_total_duration_seconds:
        Optional wall-clock cap measured against ``clock()``. ``None`` means
        unbounded.
    clock:
        Monotonic time source. Defaults to ``time.monotonic``. Tests inject
        a fake clock to advance virtual time.
    sleeper:
        Sleep callable taking seconds. Defaults to ``time.sleep``. Tests
        inject a fake sleeper.
    on_tick:
        Optional callback invoked once per tick with the recorded
        ``SupervisorTickResult``. Useful for structured logging.
    shutdown_event:
        Optional ``threading.Event``. When set at the start of an iteration
        the supervisor exits with reason ``"shutdown_signal"``.
    """

    def __init__(
        self,
        *,
        tick: Callable[[], Mapping[str, Any]],
        tick_interval_seconds: float,
        max_ticks: Optional[int] = None,
        max_consecutive_failures: int = 5,
        max_total_duration_seconds: Optional[float] = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        on_tick: Optional[Callable[[SupervisorTickResult], None]] = None,
        shutdown_event: Optional[threading.Event] = None,
    ) -> None:
        if tick_interval_seconds <= 0:
            raise ValueError("tick_interval_seconds must be > 0")
        if max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be >= 1")
        if max_ticks is not None and max_ticks < 1:
            raise ValueError("max_ticks must be >= 1 when provided")
        if max_total_duration_seconds is not None and max_total_duration_seconds <= 0:
            raise ValueError("max_total_duration_seconds must be > 0 when provided")

        self._tick = tick
        self._tick_interval_seconds = float(tick_interval_seconds)
        self._max_ticks = max_ticks
        self._max_consecutive_failures = int(max_consecutive_failures)
        self._max_total_duration_seconds = max_total_duration_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._on_tick = on_tick
        self._shutdown_event = shutdown_event

    def run(self) -> SupervisorRunSummary:
        """Run the supervisor loop until a stop condition fires."""

        start_time = self._clock()
        total_ticks = 0
        successful_ticks = 0
        failed_ticks = 0
        consecutive_failures = 0
        last_result: Optional[SupervisorTickResult] = None

        def summary(reason: str) -> SupervisorRunSummary:
            return SupervisorRunSummary(
                total_ticks=total_ticks,
                successful_ticks=successful_ticks,
                failed_ticks=failed_ticks,
                consecutive_failures_at_stop=consecutive_failures,
                stopped_reason=reason,
                last_tick_result=last_result,
            )

        while True:
            if self._shutdown_event is not None and self._shutdown_event.is_set():
                return summary(STOP_SHUTDOWN_SIGNAL)

            if (
                self._max_total_duration_seconds is not None
                and (self._clock() - start_time) >= self._max_total_duration_seconds
            ):
                return summary(STOP_DURATION_CAP)

            tick_index = total_ticks
            started_at_iso = _utc_now_iso()
            payload: Optional[Mapping[str, Any]] = None
            completed_at_iso: Optional[str] = None
            succeeded = False
            error_message: Optional[str] = None

            try:
                result = self._tick()
                payload = result if isinstance(result, Mapping) else {"value": result}
                completed_at_iso = _utc_now_iso()
                succeeded = True
            except Exception as exc:  # noqa: BLE001 — supervisor must absorb tick errors
                error_message = _format_error(exc)
                succeeded = False

            tick_result = SupervisorTickResult(
                tick_index=tick_index,
                started_at_iso=started_at_iso,
                completed_at_iso=completed_at_iso,
                succeeded=succeeded,
                error_message=error_message,
                payload=payload,
            )
            last_result = tick_result
            total_ticks += 1
            if succeeded:
                successful_ticks += 1
                consecutive_failures = 0
            else:
                failed_ticks += 1
                consecutive_failures += 1

            if self._on_tick is not None:
                self._on_tick(tick_result)

            if consecutive_failures >= self._max_consecutive_failures:
                return summary(STOP_MAX_CONSECUTIVE_FAILURES)

            if self._max_ticks is not None and total_ticks >= self._max_ticks:
                return summary(STOP_MAX_TICKS)

            sleep_seconds = self._compute_sleep_seconds(succeeded, consecutive_failures)
            self._sleeper(sleep_seconds)

    def _compute_sleep_seconds(self, succeeded: bool, consecutive_failures: int) -> float:
        """Return the cadence delay for the next iteration."""

        if succeeded:
            return self._tick_interval_seconds
        backoff_multiplier = 2 ** consecutive_failures
        capped = min(backoff_multiplier, _BACKOFF_CAP_MULTIPLIER)
        return self._tick_interval_seconds * capped


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _format_error(exc: BaseException) -> str:
    name = type(exc).__name__
    text = str(exc).strip()
    if text:
        return f"{name}: {text}"
    # No message; surface the last traceback line for debuggability.
    tb = traceback.format_exception_only(type(exc), exc)
    return "".join(tb).strip() or name
