"""Always-on scheduler for the CAS Forex AI operator.

Mirrors the proof auto-runner: an owner on/off switch, a durable desired-state
file so the loop survives API restarts, and a background thread that ticks the
:class:`~cas_forex.ai_operator.AIOperator` on the owner-set interval. Each tick
asks the ACTIVE model (Claude, or the free local fallback when tokens run out)
for dial adjustments and applies them through the owner-fenced control surface.

Cost-aware by design: the default interval is 30 minutes and the operator only
consumes paid tokens while Claude is the active provider with budget remaining.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTROL_STATE_PATH = REPO_ROOT / "runtime" / "ai-operator-runner-control.json"
_CONTROL_STATE_PATH = DEFAULT_CONTROL_STATE_PATH

DEFAULT_INTERVAL_SECONDS = 1800
MIN_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 86_400
INITIAL_DELAY_SECONDS = 20

REPORT_KIND = "cas_forex_ai_operator_runner"


@dataclass
class _RunnerState:
    thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    interval: int = DEFAULT_INTERVAL_SECONDS
    started_at_iso: str = ""
    last_tick_iso: str = ""
    last_summary: str = ""
    last_provider: str = ""
    last_ok: Optional[bool] = None
    ticks_run: int = 0
    last_error: str = ""


_state = _RunnerState()
_lock = threading.RLock()


def set_control_state_path_for_tests(path: Optional[Path]) -> None:
    global _CONTROL_STATE_PATH
    _CONTROL_STATE_PATH = Path(path) if path is not None else DEFAULT_CONTROL_STATE_PATH


def _load_control_state() -> Dict[str, Any]:
    if not _CONTROL_STATE_PATH.exists():
        return {}
    try:
        return json.loads(_CONTROL_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_control_state(*, desired_running: bool) -> None:
    payload = {
        "report_kind": "cas_forex_ai_operator_runner_control",
        "desired_running": bool(desired_running),
        "interval_seconds": int(_state.interval),
        "claim_boundary": (
            "AI operator runner control records the owner-desired scheduler state "
            "only. The operator adjusts owner-fenced AI dials; it never authorizes "
            "live trading, broker ACCEPT, orders, deposits, withdrawals, payouts, "
            "or LICENSED status."
        ),
    }
    _CONTROL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CONTROL_STATE_PATH.with_suffix(
        f"{_CONTROL_STATE_PATH.suffix}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    payload_json = json.dumps(payload, indent=2, sort_keys=True)
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            tmp.write_text(payload_json, encoding="utf-8")
            tmp.replace(_CONTROL_STATE_PATH)
            return
        except OSError as exc:  # transient OneDrive/AV lock
            import time as _time

            last_error = exc
            _time.sleep(0.2 * (attempt + 1))
    if last_error is not None:
        raise last_error


def run_operator_tick_now() -> Dict[str, Any]:
    """Run one operator tick synchronously (the manual-button path)."""
    from cas_forex.ai_operator import AIOperator

    tick = AIOperator().tick()
    with _lock:
        _state.last_tick_iso = utc_now().isoformat()
        _state.last_summary = tick.summary
        _state.last_provider = tick.provider or ""
        _state.last_ok = tick.ok
        _state.ticks_run += 1
        if not tick.ok:
            _state.last_error = tick.error or ""
        else:
            _state.last_error = ""
    return tick.to_dict()


def _run() -> None:
    if _state.stop_event.wait(min(INITIAL_DELAY_SECONDS, max(MIN_INTERVAL_SECONDS, int(_state.interval)))):
        return
    while not _state.stop_event.is_set():
        try:
            run_operator_tick_now()
        except Exception as exc:  # one bad tick must never kill the runner thread
            with _lock:
                _state.last_error = f"{type(exc).__name__}: {exc}"
        _state.stop_event.wait(max(MIN_INTERVAL_SECONDS, _state.interval))


def start_runner(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    *,
    persist_desired: bool = True,
) -> Dict[str, Any]:
    """Start the always-on operator loop if not already running. Idempotent."""
    with _lock:
        interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds)))
        _state.interval = interval
        if persist_desired:
            _save_control_state(desired_running=True)
        if _state.thread and _state.thread.is_alive():
            return _status_locked()
        _state.stop_event.clear()
        _state.started_at_iso = utc_now().isoformat()
        _state.thread = threading.Thread(target=_run, name="cas-ai-operator", daemon=True)
        _state.thread.start()
        return _status_locked()


def stop_runner(*, persist_desired: bool = True) -> Dict[str, Any]:
    with _lock:
        _state.stop_event.set()
        thread = _state.thread
    if thread and thread.is_alive():
        thread.join(timeout=3.0)
    with _lock:
        _state.thread = None
        if persist_desired:
            _save_control_state(desired_running=False)
        return _status_locked()


def set_desired_runner_state(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    *,
    desired_running: bool,
) -> Dict[str, Any]:
    with _lock:
        interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds)))
        _state.interval = interval
        _save_control_state(desired_running=desired_running)
        return _status_locked()


def _status_locked() -> Dict[str, Any]:
    running = bool(_state.thread and _state.thread.is_alive())
    control = _load_control_state()
    provider_status: Dict[str, Any] = {}
    operator_recent: list = []
    try:
        from cas_forex.model_provider import get_model_provider

        provider_status = get_model_provider().status()
    except Exception:
        provider_status = {}
    try:
        from cas_forex.ai_operator import AIOperator

        operator_recent = AIOperator().recent_actions(limit=10)
    except Exception:
        operator_recent = []
    profit_and_balance: Dict[str, Any] = {}
    try:
        from cas_forex.ai_operator import _profit_and_balance

        profit_and_balance = _profit_and_balance()
    except Exception:
        profit_and_balance = {}
    return {
        "report_kind": REPORT_KIND,
        "running": running,
        "desired_running": bool(control.get("desired_running", running)),
        "interval_seconds": _state.interval,
        "durable_control_state_path": str(_CONTROL_STATE_PATH),
        "started_at_iso": _state.started_at_iso or None,
        "last_tick_iso": _state.last_tick_iso or None,
        "last_summary": _state.last_summary or None,
        "last_provider": _state.last_provider or None,
        "last_ok": _state.last_ok,
        "ticks_run": _state.ticks_run,
        "last_error": _state.last_error or None,
        "model_provider": provider_status,
        "recent_actions": operator_recent,
        "profit_and_balance": profit_and_balance,
        "objective": "Grow realized net profit and the account balance (paper now; real needs owner go-live).",
        "claim_boundary": (
            "The AI operator steers the trading engine by tuning owner-fenced "
            "dials toward profit; it never places trades, moves money, or "
            "authorizes live trading itself."
        ),
    }


def runner_status() -> Dict[str, Any]:
    with _lock:
        return _status_locked()


def control_state() -> Dict[str, Any]:
    control = _load_control_state()
    return {
        "report_kind": "cas_forex_ai_operator_runner_control",
        "desired_running": bool(control.get("desired_running", False)),
        "interval_seconds": int(control.get("interval_seconds") or DEFAULT_INTERVAL_SECONDS),
        "durable_control_state_path": str(_CONTROL_STATE_PATH),
    }


def restore_desired_state_on_startup() -> Dict[str, Any]:
    """Called at API startup: re-arm the loop if the owner had it on."""
    control = _load_control_state()
    if bool(control.get("desired_running", False)):
        return start_runner(
            int(control.get("interval_seconds") or DEFAULT_INTERVAL_SECONDS),
            persist_desired=False,
        )
    return runner_status()
