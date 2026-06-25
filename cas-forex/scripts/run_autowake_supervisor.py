"""Long-running supervisor that wakes the CAS Forex session autowake runner.

This script wires real ``time.monotonic`` / ``time.sleep`` into
``cas_forex.autowake_supervisor.AutowakeSupervisor`` and installs a
SIGINT/SIGTERM handler that flips a ``threading.Event`` so the supervisor
exits between ticks instead of mid-evaluation.

The supervisor itself is in ``cas_forex.autowake_supervisor`` so it can be
unit-tested with injected clocks/sleepers. Heavy imports (the session
autowake runner, agent state) happen inside ``main`` so importing this
script as a module stays cheap and the launcher schema is testable in
isolation.
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tick-interval-seconds",
        type=float,
        default=300.0,
        help="Base cadence between session autowake ticks (default: 300s).",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Optional cap on total ticks before the supervisor exits.",
    )
    parser.add_argument(
        "--max-total-duration-seconds",
        type=float,
        default=None,
        help="Optional wall-clock cap (monotonic) before the supervisor exits.",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=5,
        help="Stop after this many consecutive tick failures (default: 5).",
    )
    parser.add_argument(
        "--execute-cycle",
        action="store_true",
        help="Pass --execute-cycle through to each session autowake tick.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Log only the autowake summary block per tick instead of the full report.",
    )
    return parser


def _install_shutdown_handler() -> threading.Event:
    """Install SIGINT/SIGTERM handlers that flip a shutdown event."""

    event = threading.Event()

    def _handler(signum, _frame):  # type: ignore[no-untyped-def]
        event.set()

    signal.signal(signal.SIGINT, _handler)
    # SIGTERM is POSIX-only; on Windows it may not be defined.
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _handler)
        except (ValueError, OSError):  # pragma: no cover — best-effort on Windows
            pass
    return event


def _build_tick(execute_cycle: bool):
    """Return a tick callable that runs one session autowake evaluation."""

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from cas_forex.session_autowake_runner import build_session_autowake_report

    def tick() -> Mapping[str, Any]:
        return build_session_autowake_report(execute_cycle=execute_cycle)

    return tick


def _log_tick(summary_only: bool):
    from cas_forex.autowake_supervisor import SupervisorTickResult

    def on_tick(result: SupervisorTickResult) -> None:
        if not result.succeeded:
            payload = {
                "tick_index": result.tick_index,
                "started_at": result.started_at_iso,
                "succeeded": False,
                "error_message": result.error_message,
            }
        else:
            report = result.payload or {}
            if summary_only:
                payload = {
                    "tick_index": result.tick_index,
                    "started_at": result.started_at_iso,
                    "completed_at": result.completed_at_iso,
                    "autowake_status": report.get("autowake_status"),
                    "summary": report.get("summary"),
                    "next_action": report.get("next_action"),
                }
            else:
                payload = {
                    "tick_index": result.tick_index,
                    "started_at": result.started_at_iso,
                    "completed_at": result.completed_at_iso,
                    "report": dict(report),
                }
        print(json.dumps(payload, default=str, ensure_ascii=False))

    return on_tick


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from cas_forex.autowake_supervisor import AutowakeSupervisor

    shutdown_event = _install_shutdown_handler()
    tick = _build_tick(execute_cycle=args.execute_cycle)
    on_tick = _log_tick(summary_only=args.summary_only)

    supervisor = AutowakeSupervisor(
        tick=tick,
        tick_interval_seconds=args.tick_interval_seconds,
        max_ticks=args.max_ticks,
        max_consecutive_failures=args.max_consecutive_failures,
        max_total_duration_seconds=args.max_total_duration_seconds,
        clock=time.monotonic,
        sleeper=time.sleep,
        on_tick=on_tick,
        shutdown_event=shutdown_event,
    )

    summary = supervisor.run()
    print(
        json.dumps(
            {
                "stopped_reason": summary.stopped_reason,
                "total_ticks": summary.total_ticks,
                "successful_ticks": summary.successful_ticks,
                "failed_ticks": summary.failed_ticks,
                "consecutive_failures_at_stop": summary.consecutive_failures_at_stop,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
