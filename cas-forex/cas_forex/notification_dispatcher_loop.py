"""Notification dispatcher loop primitive.

Periodically calls a state-snapshot loader, runs the pure
:func:`cas_forex.notification_triggers.detect_all` observer suite over
``(current_snapshot, previous_snapshot)``, dispatches each fired event
to every persisted Web Push subscription via an injected ``dispatch_fn``,
and persists ``current_snapshot`` to disk so the NEXT tick can use it as
``previous_snapshot`` for dedupe.

Pure-ish: every external interaction (snapshot load, previous-state file
read/write, dispatch transport, clock, sleep, shutdown signal) is
injected. Tests use fakes. The launcher script (``scripts/run_notification_dispatcher.py``)
wires real implementations.

Loop semantics mirror :class:`cas_forex.autowake_supervisor.AutowakeSupervisor`:

* Fixed cadence, with exponential backoff on consecutive failures
  capped at ``2 ** N`` where the cap multiplier is 16.
* Optional ``max_ticks``, ``max_consecutive_failures``,
  ``max_total_duration_seconds`` stop conditions.
* Optional ``shutdown_event`` (``threading.Event``) so a SIGINT/SIGTERM
  handler can request graceful exit between ticks.
* Optional ``on_tick`` callback invoked once per tick with the
  recorded :class:`NotificationLoopTickResult`.

Framing note: notifications and the loop that ships them are
OBSERVATIONAL only — what the system did. Never advisory.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from cas_forex.notification_triggers import NotificationEvent, detect_all
from cas_forex.push_notifications import (
    PushDispatchResult,
    PushSubscription,
    PushSubscriptionStore,
)


__all__ = [
    "NotificationLoopTickResult",
    "NotificationLoopRunSummary",
    "NotificationDispatcherLoop",
    "STOP_MAX_TICKS",
    "STOP_SHUTDOWN_SIGNAL",
    "STOP_MAX_CONSECUTIVE_FAILURES",
    "STOP_DURATION_CAP",
]


STOP_MAX_TICKS = "max_ticks"
STOP_SHUTDOWN_SIGNAL = "shutdown_signal"
STOP_MAX_CONSECUTIVE_FAILURES = "max_consecutive_failures"
STOP_DURATION_CAP = "duration_cap"

_BACKOFF_CAP_MULTIPLIER = 16


@dataclass(frozen=True)
class NotificationLoopTickResult:
    """Outcome of one dispatcher loop tick."""

    tick_index: int
    tick_started_at_iso: str
    tick_completed_at_iso: Optional[str]
    snapshot_loaded: bool
    events_fired: tuple[str, ...] = field(default_factory=tuple)
    events_dispatched: int = 0
    subscriptions_count: int = 0
    error_message: Optional[str] = None


@dataclass(frozen=True)
class NotificationLoopRunSummary:
    """Aggregate outcome of a :meth:`NotificationDispatcherLoop.run` invocation."""

    total_ticks: int
    events_fired_total: int
    events_dispatched_total: int
    stopped_reason: str
    last_tick: Optional[NotificationLoopTickResult]


class NotificationDispatcherLoop:
    """Schedule the notification dispatcher on a fixed cadence.

    Parameters
    ----------
    load_state_snapshot:
        Zero-arg callable returning the current ``state_snapshot`` mapping
        (matching :func:`detect_all`'s contract). Exceptions are caught
        and recorded as tick failures.
    store:
        :class:`PushSubscriptionStore` from which to read the current
        subscription list each tick.
    dispatch_fn:
        Callable invoked once per ``(subscription, event_payload)`` pair
        returning a :class:`PushDispatchResult`. Tests inject a stub;
        production wiring passes :func:`cas_forex.push_notifications.dispatch_test_push`
        bound to a transport (or the documented stub failure).
    previous_snapshot_path:
        JSON file where ``current_snapshot`` is persisted after each
        successful tick so the NEXT tick can read it as
        ``previous_snapshot``. Writes are atomic (temp file + ``os.replace``).
    tick_interval_seconds:
        Base cadence. Must be > 0.
    max_ticks:
        Optional cap on total ticks.
    max_consecutive_failures:
        Stop after this many consecutive tick failures.
    max_total_duration_seconds:
        Optional wall-clock cap measured against ``clock()``.
    clock:
        Monotonic time source.
    sleeper:
        Sleep callable taking seconds.
    on_tick:
        Optional callback invoked once per tick with the recorded
        :class:`NotificationLoopTickResult`.
    shutdown_event:
        Optional ``threading.Event``; when set at the start of an
        iteration the loop exits with reason ``"shutdown_signal"``.
    """

    def __init__(
        self,
        *,
        load_state_snapshot: Callable[[], Mapping[str, Any]],
        store: PushSubscriptionStore,
        dispatch_fn: Callable[[PushSubscription, dict], PushDispatchResult],
        previous_snapshot_path: Path,
        tick_interval_seconds: float = 60.0,
        max_ticks: Optional[int] = None,
        max_consecutive_failures: int = 10,
        max_total_duration_seconds: Optional[float] = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        on_tick: Optional[Callable[[NotificationLoopTickResult], None]] = None,
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

        self._load_state_snapshot = load_state_snapshot
        self._store = store
        self._dispatch_fn = dispatch_fn
        self._previous_snapshot_path = Path(previous_snapshot_path)
        self._tick_interval_seconds = float(tick_interval_seconds)
        self._max_ticks = max_ticks
        self._max_consecutive_failures = int(max_consecutive_failures)
        self._max_total_duration_seconds = max_total_duration_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._on_tick = on_tick
        self._shutdown_event = shutdown_event

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> NotificationLoopRunSummary:
        """Run the dispatcher loop until a stop condition fires."""

        start_time = self._clock()
        total_ticks = 0
        events_fired_total = 0
        events_dispatched_total = 0
        consecutive_failures = 0
        last_result: Optional[NotificationLoopTickResult] = None

        def summary(reason: str) -> NotificationLoopRunSummary:
            return NotificationLoopRunSummary(
                total_ticks=total_ticks,
                events_fired_total=events_fired_total,
                events_dispatched_total=events_dispatched_total,
                stopped_reason=reason,
                last_tick=last_result,
            )

        while True:
            if self._shutdown_event is not None and self._shutdown_event.is_set():
                return summary(STOP_SHUTDOWN_SIGNAL)

            if (
                self._max_total_duration_seconds is not None
                and (self._clock() - start_time) >= self._max_total_duration_seconds
            ):
                return summary(STOP_DURATION_CAP)

            tick_result = self._run_one_tick(tick_index=total_ticks)
            last_result = tick_result
            total_ticks += 1
            events_fired_total += len(tick_result.events_fired)
            events_dispatched_total += tick_result.events_dispatched

            if tick_result.error_message is not None:
                consecutive_failures += 1
            else:
                consecutive_failures = 0

            if self._on_tick is not None:
                self._on_tick(tick_result)

            if consecutive_failures >= self._max_consecutive_failures:
                return summary(STOP_MAX_CONSECUTIVE_FAILURES)

            if self._max_ticks is not None and total_ticks >= self._max_ticks:
                return summary(STOP_MAX_TICKS)

            sleep_seconds = self._compute_sleep_seconds(consecutive_failures)
            self._sleeper(sleep_seconds)

    # ------------------------------------------------------------------
    # Per-tick logic
    # ------------------------------------------------------------------

    def _run_one_tick(self, *, tick_index: int) -> NotificationLoopTickResult:
        tick_started_at_iso = _utc_now_iso()

        # 1. Load current snapshot.
        try:
            current_snapshot = self._load_state_snapshot()
        except Exception as exc:  # noqa: BLE001 — loop must absorb loader errors
            return NotificationLoopTickResult(
                tick_index=tick_index,
                tick_started_at_iso=tick_started_at_iso,
                tick_completed_at_iso=None,
                snapshot_loaded=False,
                events_fired=tuple(),
                events_dispatched=0,
                subscriptions_count=0,
                error_message=_format_error(exc),
            )

        # 2. Load previous snapshot from disk (missing/corrupt -> None).
        previous_snapshot = self._read_previous_snapshot()

        # 3. Run pure detector suite.
        try:
            events = detect_all(
                state_snapshot=current_snapshot,
                previous_snapshot=previous_snapshot,
            )
        except Exception as exc:  # noqa: BLE001
            return NotificationLoopTickResult(
                tick_index=tick_index,
                tick_started_at_iso=tick_started_at_iso,
                tick_completed_at_iso=None,
                snapshot_loaded=True,
                events_fired=tuple(),
                events_dispatched=0,
                subscriptions_count=0,
                error_message=_format_error(exc),
            )

        # 4. For each event, for each subscription, dispatch.
        subscriptions = list(self._store.list_all())
        events_dispatched = 0
        for event in events:
            payload = _event_to_payload(event)
            for sub in subscriptions:
                try:
                    self._dispatch_fn(sub, payload)
                except Exception:
                    # Per-subscription dispatch failure must not abort the tick.
                    pass
                events_dispatched += 1

        # 5. Persist current snapshot atomically. Persist failure does NOT
        # mark the tick as failed for backoff purposes — events already
        # dispatched. We surface the persist error in error_message so an
        # operator can see it.
        persist_error: Optional[str] = None
        try:
            self._write_previous_snapshot(current_snapshot)
        except Exception as exc:  # noqa: BLE001
            persist_error = _format_error(exc)

        return NotificationLoopTickResult(
            tick_index=tick_index,
            tick_started_at_iso=tick_started_at_iso,
            tick_completed_at_iso=_utc_now_iso(),
            snapshot_loaded=True,
            events_fired=tuple(event.event_kind for event in events),
            events_dispatched=events_dispatched,
            subscriptions_count=len(subscriptions),
            error_message=persist_error,
        )

    # ------------------------------------------------------------------
    # Snapshot persistence
    # ------------------------------------------------------------------

    def _read_previous_snapshot(self) -> Optional[Mapping[str, Any]]:
        path = self._previous_snapshot_path
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, Mapping):
            return None
        return data

    def _write_previous_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        path = self._previous_snapshot_path
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(_to_jsonable(snapshot), fh, ensure_ascii=False, default=str)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # Backoff
    # ------------------------------------------------------------------

    def _compute_sleep_seconds(self, consecutive_failures: int) -> float:
        if consecutive_failures <= 0:
            return self._tick_interval_seconds
        multiplier = min(2 ** consecutive_failures, _BACKOFF_CAP_MULTIPLIER)
        return self._tick_interval_seconds * multiplier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def _format_error(exc: BaseException) -> str:
    name = type(exc).__name__
    text = str(exc).strip()
    if text:
        return f"{name}: {text}"
    tb = traceback.format_exception_only(type(exc), exc)
    return "".join(tb).strip() or name


def _event_to_payload(event: NotificationEvent) -> dict:
    """Render a :class:`NotificationEvent` as a dispatcher payload dict."""
    return {
        "event_kind": event.event_kind,
        "event_id": event.event_id,
        "title": event.title,
        "body": event.body,
        "severity": event.severity,
        "detected_at_iso": event.detected_at_iso,
        "payload": dict(event.payload),
    }


def _to_jsonable(value: Any) -> Any:
    """Best-effort recursive coercion to JSON-serialisable primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_jsonable(item) for item in value]
    return str(value)
