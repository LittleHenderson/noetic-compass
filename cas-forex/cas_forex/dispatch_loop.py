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

# The owner drives — the interval can be anything from 1 second up to a day.
# (Very low intervals hammer the market-data feed + CPU; that's the owner's call,
# surfaced as an honest note in the UI, not blocked.)
MIN_INTERVAL_SECONDS = 1
DEFAULT_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 86_400


# Session names the owner can target. Overlap-inclusive (a cycle during the
# 12:00-16:00 UTC London/NY overlap counts as BOTH London and New York).
SESSION_NAMES = ("Asian", "London", "New York")


def active_sessions(now: Any = None) -> set[str]:
    """Which trading sessions are active at ``now`` (UTC)."""
    if now is None:
        from cas_forex.time_utils import utc_now

        now = utc_now()
    h = now.hour
    active = set()
    if h < 8 or h >= 21:
        active.add("Asian")
    if 8 <= h < 16:
        active.add("London")
    if 12 <= h < 21:
        active.add("New York")
    return active


class _LoopState:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.interval = DEFAULT_INTERVAL_SECONDS
        # Targeting (empty list / None => no restriction = everything).
        self.symbols: list[str] = []
        self.sessions: list[str] = []
        self.cycles_run = 0
        self.cycles_idle = 0
        self.last_run_iso: str = ""
        self.last_summary: str = ""
        self.last_error: str = ""
        self.started_at_iso: str = ""


_state = _LoopState()
_lock = threading.Lock()


def _run(interval: int) -> None:
    from cas_forex.agent_dispatch import (
        collect_route_intents,
        run_agent_dispatch_cycle,
        write_agent_dispatch_cycle_report,
    )
    from cas_forex.time_utils import utc_now

    while not _state.stop_event.is_set():
        try:
            # Session gate: if the owner restricted sessions and none is active now,
            # idle this cycle (no dispatch) rather than trading off-session.
            if _state.sessions and not (active_sessions() & set(_state.sessions)):
                _state.cycles_idle += 1
                _state.last_run_iso = utc_now().isoformat()
                _state.last_summary = (
                    f"idle — outside target sessions {_state.sessions} "
                    f"(active now: {sorted(active_sessions()) or ['none']})"
                )
            else:
                # Symbol targeting: collect the cycle's intents and keep only the
                # owner's chosen symbols before dispatching.
                intents = collect_route_intents()
                if _state.symbols:
                    intents = [i for i in intents if i.symbol in _state.symbols]
                cycle = run_agent_dispatch_cycle(intents=intents, enforce_receipt_gates=True)
                try:
                    write_agent_dispatch_cycle_report(cycle)
                except Exception:  # artifact write is best-effort; never break the loop
                    pass
                rep = cycle.dispatch_report
                _state.cycles_run += 1
                _state.last_run_iso = utc_now().isoformat()
                target = ""
                if _state.symbols:
                    target = f" symbols={_state.symbols}"
                _state.last_summary = (
                    f"mode={rep.mode} intents={rep.intent_count} executed={rep.executed_count} "
                    f"blocked={rep.blocked_count} rejected={rep.rejected_count}{target}"
                )
            _state.last_error = ""
        except Exception as exc:  # one bad cycle must never kill the loop thread
            _state.last_error = f"{type(exc).__name__}: {exc}"
        # Sleep the CURRENT interval (re-read each cycle so the owner can change it
        # live without restarting), but wake immediately if stop was requested.
        _state.stop_event.wait(max(MIN_INTERVAL_SECONDS, _state.interval))


def start_loop(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    symbols: Optional[list[str]] = None,
    sessions: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Start the paper dispatch loop if not already running. Idempotent.

    ``interval_seconds``, ``symbols`` (restrict dispatch to these), and
    ``sessions`` (only dispatch during these) all update live — re-calling while
    the loop runs applies the new targeting on the next cycle without a restart.
    Pass ``None`` to leave a field unchanged; pass ``[]`` to clear a restriction.
    """
    from cas_forex.time_utils import utc_now

    with _lock:
        interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds)))
        _state.interval = interval
        if symbols is not None:
            _state.symbols = [str(s) for s in symbols]
        if sessions is not None:
            _state.sessions = [s for s in (str(x) for x in sessions) if s in SESSION_NAMES]
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
        "symbols": list(_state.symbols),
        "sessions": list(_state.sessions),
        "active_sessions": sorted(active_sessions()),
        "cycles_run": _state.cycles_run,
        "cycles_idle": _state.cycles_idle,
        "last_run_iso": _state.last_run_iso or None,
        "last_summary": _state.last_summary or None,
        "last_error": _state.last_error or None,
        "started_at_iso": _state.started_at_iso or None,
        "mode": _effective_mode(),
        "note": (
            "Runs the same gated dispatch cycle as the manual button on a timer. "
            "Paper-safe by default; it reaches a live broker only when live trading "
            "is owner-authorized and the bridge allows it. Empty symbols/sessions = "
            "no restriction (trade everything, any session)."
        ),
    }


def loop_status() -> dict[str, Any]:
    """Current loop status (running, interval, cycles run, last result, mode)."""
    with _lock:
        return _status_locked()
