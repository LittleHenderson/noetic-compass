"""Long-running launcher for the CAS Forex notification dispatcher loop.

Wires real ``time.monotonic`` / ``time.sleep`` into
``cas_forex.notification_dispatcher_loop.NotificationDispatcherLoop`` and
installs a SIGINT/SIGTERM handler that flips a ``threading.Event`` so the
loop exits between ticks instead of mid-evaluation.

The loop itself is in ``cas_forex.notification_dispatcher_loop`` so it can
be unit-tested with injected clocks, sleepers, and dispatch transports.
Heavy imports (operator briefing inputs, push notification store) happen
inside ``main`` so importing this script as a module stays cheap.

Dispatch-backend gap:
    Real Web Push delivery requires the ``pywebpush`` package, which is
    intentionally NOT a dependency of this repo today. The launcher's
    default dispatch closure calls
    ``cas_forex.push_notifications.dispatch_test_push`` with no
    transport, so every dispatch returns the documented stub failure
    (``"dispatch backend not installed (pywebpush)"``). When pywebpush
    is installed, this launcher will gain a transport closure that
    actually delivers the payload.

Operator usage::

    py -3.12 scripts/run_notification_dispatcher.py \\
        --tick-interval-seconds 60 \\
        --summary-only

Run in its own window like the autowake supervisor.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREVIOUS_SNAPSHOT_PATH = (
    REPO_ROOT / "evidence_runs" / "push_subscriptions" / "previous_state_snapshot.json"
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tick-interval-seconds",
        type=float,
        default=60.0,
        help="Base cadence between dispatcher ticks (default: 60s).",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Optional cap on total ticks before the loop exits.",
    )
    parser.add_argument(
        "--max-total-duration-seconds",
        type=float,
        default=None,
        help="Optional wall-clock cap (monotonic) before the loop exits.",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=10,
        help="Stop after this many consecutive tick failures (default: 10).",
    )
    parser.add_argument(
        "--previous-snapshot-path",
        type=Path,
        default=DEFAULT_PREVIOUS_SNAPSHOT_PATH,
        help="JSON file to persist last-seen state across ticks/restarts.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Log only a compact per-tick summary instead of the full tick result.",
    )
    return parser


def _install_shutdown_handler() -> threading.Event:
    """Install SIGINT/SIGTERM handlers that flip a shutdown event."""

    event = threading.Event()

    def _handler(signum, _frame):  # type: ignore[no-untyped-def]
        event.set()

    signal.signal(signal.SIGINT, _handler)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _handler)
        except (ValueError, OSError):  # pragma: no cover — best-effort on Windows
            pass
    return event


def _build_state_loader():
    """Return a zero-arg loader that builds the live state snapshot dict.

    Reuses the disk patterns already proven by the operator_briefing
    route: loop health, latest cycle, live telemetry, MT5 probe,
    readiness. Each underlying loader is wrapped so a missing or
    unreadable artifact becomes ``None`` for that input.
    """

    sys.path.insert(0, str(REPO_ROOT))

    def load_state_snapshot() -> dict[str, Any]:
        # Local imports keep the launcher schema cheap to import.
        from cas_forex.operator_briefing import load_operator_briefing_inputs

        try:
            briefing_inputs = load_operator_briefing_inputs(REPO_ROOT)
        except Exception:
            briefing_inputs = {}

        # The detect_all suite reads:
        #   * latest_cycle_report (for TRADE_EXECUTED)
        #   * latest_decision     (for TRADE_BLOCKED)
        #   * loop_health         (for LOOP_STALLED / LOOP_RESUMED)
        #   * mt5_probe           (for MT5_DISCONNECTED)
        #   * readiness           (for READINESS_GATE_FLIPPED)
        latest_cycle_report: Mapping[str, Any] | None = None
        try:
            from cas_forex.autonomous_loop_health import load_loop_health_inputs

            loop_inputs = load_loop_health_inputs(REPO_ROOT)
            cycle = loop_inputs.get("latest_cycle_report")
            if isinstance(cycle, Mapping):
                latest_cycle_report = dict(cycle)
        except Exception:
            latest_cycle_report = None

        return {
            "latest_cycle_report": latest_cycle_report,
            "latest_decision": briefing_inputs.get("latest_decision"),
            "loop_health": briefing_inputs.get("loop_health"),
            "mt5_probe": briefing_inputs.get("mt5_probe"),
            "readiness": briefing_inputs.get("readiness"),
        }

    return load_state_snapshot


def _build_dispatch_fn():
    """Return the production dispatch closure.

    Calls :func:`cas_forex.push_notifications.dispatch_test_push` with no
    transport. Until ``pywebpush`` is installed and a VAPID-signed
    transport closure is wired here, every dispatch returns the
    documented stub failure (``"dispatch backend not installed
    (pywebpush)")``. This is the production gap.
    """

    from cas_forex.push_notifications import (
        PushDispatchResult,
        PushSubscription,
        dispatch_test_push,
    )

    def dispatch_fn(subscription: PushSubscription, payload: dict) -> PushDispatchResult:
        return dispatch_test_push(subscription=subscription, payload=payload, transport=None)

    return dispatch_fn


def _log_tick(summary_only: bool):
    from cas_forex.notification_dispatcher_loop import NotificationLoopTickResult

    def on_tick(result: NotificationLoopTickResult) -> None:
        if summary_only:
            payload = {
                "tick_index": result.tick_index,
                "tick_started_at": result.tick_started_at_iso,
                "snapshot_loaded": result.snapshot_loaded,
                "events_fired_count": len(result.events_fired),
                "events_dispatched": result.events_dispatched,
                "subscriptions_count": result.subscriptions_count,
                "error_message": result.error_message,
            }
        else:
            payload = {
                "tick_index": result.tick_index,
                "tick_started_at": result.tick_started_at_iso,
                "tick_completed_at": result.tick_completed_at_iso,
                "snapshot_loaded": result.snapshot_loaded,
                "events_fired": list(result.events_fired),
                "events_dispatched": result.events_dispatched,
                "subscriptions_count": result.subscriptions_count,
                "error_message": result.error_message,
            }
        print(json.dumps(payload, default=str, ensure_ascii=False))

    return on_tick


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT))
    from cas_forex.notification_dispatcher_loop import NotificationDispatcherLoop
    from cas_forex.push_notifications import PushSubscriptionStore

    shutdown_event = _install_shutdown_handler()
    load_state_snapshot = _build_state_loader()
    dispatch_fn = _build_dispatch_fn()
    on_tick = _log_tick(summary_only=args.summary_only)
    store = PushSubscriptionStore()

    loop = NotificationDispatcherLoop(
        load_state_snapshot=load_state_snapshot,
        store=store,
        dispatch_fn=dispatch_fn,
        previous_snapshot_path=args.previous_snapshot_path,
        tick_interval_seconds=args.tick_interval_seconds,
        max_ticks=args.max_ticks,
        max_consecutive_failures=args.max_consecutive_failures,
        max_total_duration_seconds=args.max_total_duration_seconds,
        clock=time.monotonic,
        sleeper=time.sleep,
        on_tick=on_tick,
        shutdown_event=shutdown_event,
    )

    summary = loop.run()
    print(
        json.dumps(
            {
                "stopped_reason": summary.stopped_reason,
                "total_ticks": summary.total_ticks,
                "events_fired_total": summary.events_fired_total,
                "events_dispatched_total": summary.events_dispatched_total,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
