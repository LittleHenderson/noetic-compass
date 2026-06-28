"""Owner-controlled daily proof auto-runner.

The 30-trading-day paper proof used to advance only by a command-line step the
non-technical owner could not run, so it stalled. This module is the missing
in-app advance: a background daemon thread that, once per trading day, runs the
same daily paper-proof bundle (broker-verified receipt + decision + risk) so the
proof accumulates on its own. The owner turns it on/off from the app.

Paper-only and safe: ``run_daily_paper_bundle`` refuses live mode, and the run
is idempotent (``skip_existing``) so a day already broker-verified is never
re-appended. If the demo terminal is down when a day is due, the runner records
the miss and retries on the next check rather than burning the day.

A single global runner (single-owner cockpit). State resets on restart.
"""

from __future__ import annotations

import threading
from datetime import date
from typing import Any, Dict, Optional

# How often the runner wakes to check whether today's proof day still needs
# recording. It only ever ACTS once per trading day; this is just the retry
# cadence when the demo terminal is temporarily unavailable.
MIN_CHECK_INTERVAL_SECONDS = 60
DEFAULT_CHECK_INTERVAL_SECONDS = 1800  # 30 minutes
MAX_CHECK_INTERVAL_SECONDS = 86_400


class _RunnerState:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.check_interval = DEFAULT_CHECK_INTERVAL_SECONDS
        self.last_check_iso: str = ""
        self.last_run_iso: str = ""
        self.last_recorded_date: str = ""
        self.last_status: str = ""
        self.last_detail: str = ""
        self.last_error: str = ""
        self.days_recorded = 0
        self.started_at_iso: str = ""


_state = _RunnerState()
_lock = threading.Lock()


def _plan_and_dir():
    from cas_forex.paper_proof import (
        build_index_tsmom_126_paper_proof_plan,
        index_tsmom_126_proof_dir,
    )

    return build_index_tsmom_126_paper_proof_plan(), index_tsmom_126_proof_dir()


def run_proof_day_now(trading_date: Optional[date] = None) -> Dict[str, Any]:
    """Record one proof day (today or a given date). The manual-button path.

    Returns a status payload. ``APPENDED`` = a new broker-verified day was added;
    ``SKIPPED_EXISTING`` = today is already verified; ``UNAVAILABLE``/``BLOCKED``
    = the demo terminal was not reachable/demo (retry later); ``WEEKEND`` /
    ``LIVE_BLOCKED`` = not a paper trading day.
    """

    from cas_forex.config import config
    from cas_forex.paper_daily_bundle import run_daily_paper_bundle
    from cas_forex.time_utils import utc_now

    if config.live_mode or not config.paper_trading:
        return {
            "report_kind": "cas_forex_proof_run",
            "status": "LIVE_BLOCKED",
            "detail": "Proof runs are paper-only (need paper_trading=True and live_mode=False).",
        }

    day = trading_date or utc_now().date()
    if day.weekday() >= 5:
        return {
            "report_kind": "cas_forex_proof_run",
            "status": "WEEKEND",
            "date": day.isoformat(),
            "detail": "Markets are closed; proof days are weekdays only.",
        }

    plan, out_dir = _plan_and_dir()
    bundle = run_daily_paper_bundle(
        plan,
        out_dir,
        trading_date=day,
        append_records=True,
        collect_mt5_receipt=True,
        skip_existing=True,
    )
    receipt_step = next(
        (step for step in bundle.steps if step.name == "mt5_demo_receipt"),
        None,
    )
    status = receipt_step.status if receipt_step else "UNKNOWN"
    detail = receipt_step.detail if receipt_step else "No receipt step ran."
    reasons = list(getattr(receipt_step, "reasons", []) or []) if receipt_step else []
    return {
        "report_kind": "cas_forex_proof_run",
        "status": status,
        "date": day.isoformat(),
        "detail": detail,
        "reasons": reasons,
        "latest_proof": bundle.latest_proof,
    }


def _run() -> None:
    from cas_forex.time_utils import utc_now

    while not _state.stop_event.is_set():
        try:
            now = utc_now()
            day = now.date()
            _state.last_check_iso = now.isoformat()
            if day.weekday() < 5 and _state.last_recorded_date != day.isoformat():
                result = run_proof_day_now(day)
                _state.last_run_iso = utc_now().isoformat()
                _state.last_status = str(result.get("status"))
                _state.last_detail = str(result.get("detail") or "")
                if result.get("status") in {"APPENDED", "SKIPPED_EXISTING"}:
                    # Today's proof day is secured — don't try again until tomorrow.
                    if result.get("status") == "APPENDED":
                        _state.days_recorded += 1
                    _state.last_recorded_date = day.isoformat()
                # UNAVAILABLE / BLOCKED / WEEKEND: leave last_recorded_date unset so
                # we retry on the next check once the demo terminal is back.
            _state.last_error = ""
        except Exception as exc:  # one bad check must never kill the runner thread
            _state.last_error = f"{type(exc).__name__}: {exc}"
        _state.stop_event.wait(max(MIN_CHECK_INTERVAL_SECONDS, _state.check_interval))


def start_runner(check_interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS) -> Dict[str, Any]:
    """Start the daily proof auto-runner if not already running. Idempotent."""

    from cas_forex.time_utils import utc_now

    with _lock:
        interval = max(
            MIN_CHECK_INTERVAL_SECONDS,
            min(MAX_CHECK_INTERVAL_SECONDS, int(check_interval_seconds)),
        )
        _state.check_interval = interval
        if _state.thread and _state.thread.is_alive():
            return _status_locked()
        _state.stop_event.clear()
        _state.started_at_iso = utc_now().isoformat()
        _state.thread = threading.Thread(target=_run, name="cas-proof-auto-runner", daemon=True)
        _state.thread.start()
        return _status_locked()


def stop_runner() -> Dict[str, Any]:
    """Stop the auto-runner; the current check winds down on its own."""

    with _lock:
        _state.stop_event.set()
        thread = _state.thread
    if thread and thread.is_alive():
        thread.join(timeout=3.0)
    with _lock:
        _state.thread = None
        return _status_locked()


def _status_locked() -> Dict[str, Any]:
    running = bool(_state.thread and _state.thread.is_alive())
    return {
        "report_kind": "cas_forex_proof_runner",
        "running": running,
        "check_interval_seconds": _state.check_interval,
        "last_check_iso": _state.last_check_iso or None,
        "last_run_iso": _state.last_run_iso or None,
        "last_recorded_date": _state.last_recorded_date or None,
        "last_status": _state.last_status or None,
        "last_detail": _state.last_detail or None,
        "last_error": _state.last_error or None,
        "days_recorded_this_session": _state.days_recorded,
        "started_at_iso": _state.started_at_iso or None,
        "note": (
            "Records one broker-verified proof day per trading day. Paper-only; "
            "idempotent (a day already verified is not re-recorded). If the demo "
            "terminal is down when a day is due, it retries on the next check."
        ),
    }


def runner_status() -> Dict[str, Any]:
    """Current auto-runner status."""
    with _lock:
        return _status_locked()
