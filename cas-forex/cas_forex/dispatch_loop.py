"""Owner-controlled paper dispatch loop — runs the gated dispatch cycle on a timer.

The dispatch engine existed (``agent_dispatch.run_agent_dispatch_cycle``) but
nothing ran it on a schedule, so even with green gates the bot never acted on its
own — it only fired when the owner hit a button. This module is that missing
scheduler: a background daemon thread that runs the SAME gated cycle every N
seconds.

Paper-safe by design: it calls the exact gated cycle the manual button calls, so
it can only ever reach a live broker when the owner has authorized live trading
(and the broker bridge re-checks at order time, fail-closed). By default that
means paper/demo dispatch — the loop running does not move the live gate.

Owner-controlled: nothing starts this automatically. The owner starts/stops it and
sets the interval from the app. A single global loop (single-owner cockpit);
state resets on restart.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

MIN_INTERVAL_SECONDS = 10
DEFAULT_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 3600


class _LoopState:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.interval = DEFAULT_INTERVAL_SECONDS
        self.cycles_run = 0
        self.last_run_iso: str = ""
        self.last_summary: str = ""
        self.last_error: str = ""
        self.started_at_iso: str = ""


_state = _LoopState()
_lock = threading.Lock()


def _run(interval: int) -> None:
    from cas_forex.agent_dispatch import (
        run_agent_dispatch_cycle,
        write_agent_dispatch_cycle_report,
    )
    from cas_forex.time_utils import utc_now

    while not _state.stop_event.is_set():
        try:
            cycle = run_agent_dispatch_cycle(enforce_receipt_gates=True)
            try:
                write_agent_dispatch_cycle_report(cycle)
            except Exception:  # artifact write is best-effort; never break the loop
                pass
            rep = cycle.dispatch_report
            _state.cycles_run += 1
            _state.last_run_iso = utc_now().isoformat()
            _state.last_summary = (
                f"mode={rep.mode} intents={rep.intent_count} executed={rep.executed_count} "
                f"blocked={rep.blocked_count} rejected={rep.rejected_count}"
            )
            _state.last_error = ""
        except Exception as exc:  # one bad cycle must never kill the loop thread
            _state.last_error = f"{type(exc).__name__}: {exc}"
        # Sleep the interval, but wake immediately if stop was requested.
        _state.stop_event.wait(interval)


def start_loop(interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> dict[str, Any]:
    """Start the paper dispatch loop if not already running. Idempotent."""
    from cas_forex.time_utils import utc_now

    with _lock:
        interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds)))
        _state.interval = interval
        if _state.thread and _state.thread.is_alive():
            return _status_locked()
        _state.stop_event.clear()
        _state.started_at_iso = utc_now().isoformat()
        _state.thread = threading.Thread(
            target=_run, args=(interval,), name="cas-paper-dispatch-loop", daemon=True
        )
        _state.thread.start()
        return _status_locked()


def stop_loop() -> dict[str, Any]:
    """Stop the loop and wait briefly for the current cycle to wind down."""
    with _lock:
        _state.stop_event.set()
        thread = _state.thread
    if thread and thread.is_alive():
        thread.join(timeout=3.0)
    with _lock:
        _state.thread = None
        return _status_locked()


def _effective_mode() -> str:
    try:
        from cas_forex import runtime_gates
        from cas_forex.config import config

        if getattr(config, "live_mode", False) and runtime_gates.is_authorized("live_trading"):
            return "LIVE"
    except Exception:  # pragma: no cover - defensive
        pass
    return "PAPER"


def _status_locked() -> dict[str, Any]:
    running = bool(_state.thread and _state.thread.is_alive())
    return {
        "report_kind": "cas_forex_dispatch_loop",
        "running": running,
        "interval_seconds": _state.interval,
        "cycles_run": _state.cycles_run,
        "last_run_iso": _state.last_run_iso or None,
        "last_summary": _state.last_summary or None,
        "last_error": _state.last_error or None,
        "started_at_iso": _state.started_at_iso or None,
        "mode": _effective_mode(),
        "note": (
            "Runs the same gated dispatch cycle as the manual button on a timer. "
            "Paper-safe by default; it reaches a live broker only when live trading "
            "is owner-authorized and the bridge allows it."
        ),
    }


def loop_status() -> dict[str, Any]:
    """Current loop status (running, interval, cycles run, last result, mode)."""
    with _lock:
        return _status_locked()
