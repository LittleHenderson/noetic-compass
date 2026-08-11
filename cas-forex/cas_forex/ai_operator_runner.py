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
from typing import Any, Dict, Mapping, Optional

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
    last_context_delivery: Dict[str, Any] = field(default_factory=dict)
    last_money_movement: Dict[str, Any] = field(default_factory=dict)


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
            "only. Operator intelligence steers owner-fenced dials and may originate "
            "autonomous intent; broker/provider side effects remain exclusively in "
            "the guarded dispatch, execution, and receipt paths."
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
    try:
        from cas_forex.autonomous_money_movement import (
            run_autonomous_verified_profit_sweep_cycle,
        )

        movement_cycle = run_autonomous_verified_profit_sweep_cycle(
            trigger="AI_OPERATOR_TICK",
        )
    except Exception as exc:
        movement_cycle = {
            "report_kind": "cas_forex_autonomous_money_movement_cycle",
            "status": "ERROR",
            "provider_touched": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
    with _lock:
        _state.last_tick_iso = utc_now().isoformat()
        _state.last_summary = tick.summary
        _state.last_provider = tick.provider or ""
        _state.last_ok = tick.ok
        _state.ticks_run += 1
        _state.last_context_delivery = dict(tick.context_delivery)
        _state.last_money_movement = dict(movement_cycle)
        if not tick.ok:
            _state.last_error = tick.error or ""
        else:
            _state.last_error = ""
    payload = tick.to_dict()
    payload["autonomous_money_movement"] = movement_cycle
    return payload


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


def _autonomous_money_movement_status() -> Dict[str, Any]:
    try:
        from cas_forex.autonomous_money_movement import autonomous_money_movement_status

        return autonomous_money_movement_status()
    except Exception as exc:
        return {
            "report_kind": "cas_forex_autonomous_money_movement_status",
            "status": "UNAVAILABLE",
            "autonomous_enabled": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }


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
            pass
        else:
            _state.stop_event.clear()
            _state.started_at_iso = utc_now().isoformat()
            _state.thread = threading.Thread(target=_run, name="cas-ai-operator", daemon=True)
            _state.thread.start()
    return runner_status_fast()


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
    return runner_status_fast()


def set_desired_runner_state(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    *,
    desired_running: bool,
) -> Dict[str, Any]:
    with _lock:
        interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds)))
        _state.interval = interval
        _save_control_state(desired_running=desired_running)
    return runner_status_fast()


def _state_snapshot_locked() -> Dict[str, Any]:
    return {
        "thread": _state.thread,
        "interval": int(_state.interval),
        "started_at_iso": _state.started_at_iso,
        "last_tick_iso": _state.last_tick_iso,
        "last_summary": _state.last_summary,
        "last_provider": _state.last_provider,
        "last_ok": _state.last_ok,
        "ticks_run": int(_state.ticks_run),
        "last_error": _state.last_error,
        "last_context_delivery": dict(_state.last_context_delivery),
        "last_money_movement": dict(_state.last_money_movement),
    }


def _operational_state(running: bool, dispatch_runtime: Dict[str, Any]) -> str:
    dispatch_running = bool(dispatch_runtime.get("running"))
    dispatch_active = bool(dispatch_runtime.get("execution_active"))
    dispatch_blocked = str(dispatch_runtime.get("status") or "") == "LIVE_BLOCKED"
    dispatch_paper_fallback = bool(dispatch_runtime.get("paper_fallback_active"))
    if not running:
        return "OFF"
    if dispatch_blocked:
        return "WATCHING_EXECUTION_BLOCKED"
    if dispatch_active and dispatch_paper_fallback:
        return "WATCHING_PAPER_EXECUTING_LIVE_PENDING"
    if dispatch_active:
        return "WATCHING_AND_EXECUTING"
    if dispatch_running:
        return "WATCHING_EXECUTION_IDLE"
    return "WATCHING_EXECUTION_LOOP_OFF"


def _build_status(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build the rich evidence packet without holding the scheduler lock."""

    thread = snapshot.get("thread")
    running = bool(thread and thread.is_alive())
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
    professional_readiness: Dict[str, Any] = {}
    try:
        from cas_forex.ai_operator import _professional_readiness_context

        professional_readiness = _professional_readiness_context()
    except Exception:
        professional_readiness = {}
    dispatch_runtime: Dict[str, Any] = {}
    try:
        from cas_forex.dispatch_loop import loop_status

        dispatch_runtime = loop_status()
    except Exception:
        dispatch_runtime = {}
    active_account_objective: Dict[str, Any] = {}
    try:
        from cas_forex.ai_operator import (
            _active_account_objective_context,
            _compact_mt5_snapshot,
        )
        from cas_forex.mt5_account_growth import load_mt5_account_growth
        from cas_forex.mt5_live import get_mt5_account_snapshot

        active_account_objective = _active_account_objective_context(
            live_mt5=_compact_mt5_snapshot(get_mt5_account_snapshot(force=False)),
            dispatch_loop=dispatch_runtime,
            simulator_performance=profit_and_balance,
            account_growth=load_mt5_account_growth(),
        )
    except Exception:
        active_account_objective = {}
    lessons: list = []
    lessons_total = 0
    try:
        from cas_forex.operator_lessons import lessons_count, list_lessons

        lessons = list_lessons(limit=8)
        lessons_total = lessons_count()
    except Exception:
        lessons, lessons_total = [], 0
    dispatch_running = bool(dispatch_runtime.get("running"))
    dispatch_active = bool(dispatch_runtime.get("execution_active"))
    dispatch_paper_fallback = bool(dispatch_runtime.get("paper_fallback_active"))
    operational_state = _operational_state(running, dispatch_runtime)
    return {
        "report_kind": REPORT_KIND,
        "running": running,
        "operational_state": operational_state,
        "desired_running": bool(control.get("desired_running", running)),
        "interval_seconds": snapshot.get("interval"),
        "durable_control_state_path": str(_CONTROL_STATE_PATH),
        "started_at_iso": snapshot.get("started_at_iso") or None,
        "last_tick_iso": snapshot.get("last_tick_iso") or None,
        "last_summary": snapshot.get("last_summary") or None,
        "last_provider": snapshot.get("last_provider") or None,
        "last_ok": snapshot.get("last_ok"),
        "ticks_run": snapshot.get("ticks_run"),
        "last_error": snapshot.get("last_error") or None,
        "last_context_delivery": dict(snapshot.get("last_context_delivery") or {})
        if snapshot.get("last_context_delivery")
        else (
            dict(operator_recent[0].get("context_delivery") or {})
            if operator_recent and isinstance(operator_recent[0], dict)
            else {}
        ),
        "model_provider": provider_status,
        "recent_actions": operator_recent,
        "active_account_objective": active_account_objective,
        "profit_and_balance": profit_and_balance,
        "professional_readiness": professional_readiness,
        "execution_runtime": {
            "status": dispatch_runtime.get("status"),
            "running": dispatch_running,
            "execution_active": dispatch_active,
            "execution_lane": dispatch_runtime.get("execution_lane"),
            "paper_learning_active": dispatch_runtime.get("paper_learning_active"),
            "paper_fallback_active": dispatch_runtime.get("paper_fallback_active"),
            "paper_fallback_available": dispatch_runtime.get("paper_fallback_available"),
            "live_execution_active": dispatch_runtime.get("live_execution_active"),
            "live_execution_authorized": dispatch_runtime.get("live_execution_authorized"),
            "live_execution_status": dispatch_runtime.get("live_execution_status"),
            "requested_mode": dispatch_runtime.get("requested_mode"),
            "mode": dispatch_runtime.get("mode"),
            "last_run_iso": dispatch_runtime.get("last_run_iso"),
            "last_summary": dispatch_runtime.get("last_summary"),
            "last_error": dispatch_runtime.get("last_error"),
            "last_blocking_detail": dispatch_runtime.get("last_blocking_detail"),
            "live_blocking_detail": dispatch_runtime.get("live_blocking_detail"),
            "last_bridge_class": dispatch_runtime.get("last_bridge_class"),
            "last_bridge_selection_status": dispatch_runtime.get(
                "last_bridge_selection_status"
            ),
            "last_bridge_selection_detail": dispatch_runtime.get(
                "last_bridge_selection_detail"
            ),
            "cycles_run": dispatch_runtime.get("cycles_run"),
            "cycles_idle": dispatch_runtime.get("cycles_idle"),
            "last_entry_timeframe_scan": dict(
                dispatch_runtime.get("last_entry_timeframe_scan") or {}
            ),
            "active_entry_timeframes": list(
                dispatch_runtime.get("active_entry_timeframes") or []
            ),
            "last_entry_timeframe": dispatch_runtime.get("last_entry_timeframe"),
            "last_entry_lane": dispatch_runtime.get("last_entry_lane"),
            "last_entry_risk_feasibility": dict(
                dispatch_runtime.get("last_entry_risk_feasibility") or {}
            ),
            "last_entry_risk_feasibility_status": dispatch_runtime.get(
                "last_entry_risk_feasibility_status"
            ),
            "last_entry_risk_candidate_count": dispatch_runtime.get(
                "last_entry_risk_candidate_count"
            ),
            "last_entry_risk_feasible_count": dispatch_runtime.get(
                "last_entry_risk_feasible_count"
            ),
            "last_entry_risk_blocked_count": dispatch_runtime.get(
                "last_entry_risk_blocked_count"
            ),
            "last_entry_risk_unknown_count": dispatch_runtime.get(
                "last_entry_risk_unknown_count"
            ),
            "last_entry_risk_operator_candidate_count": dispatch_runtime.get(
                "last_entry_risk_operator_candidate_count"
            ),
            "last_entry_capacity_pressure": dict(
                dispatch_runtime.get("last_entry_capacity_pressure") or {}
            ),
            "last_entry_capacity_pressure_status": dispatch_runtime.get(
                "last_entry_capacity_pressure_status"
            ),
            "last_symbol_targeting": dict(
                dispatch_runtime.get("last_symbol_targeting") or {}
            ),
            "last_symbol_targeting_status": dispatch_runtime.get(
                "last_symbol_targeting_status"
            ),
            "last_effective_entry_symbols": list(
                dispatch_runtime.get("last_effective_entry_symbols") or []
            ),
            "last_eligible_entry_symbols": list(
                dispatch_runtime.get("last_eligible_entry_symbols") or []
            ),
            "last_saturated_entry_symbols": list(
                dispatch_runtime.get("last_saturated_entry_symbols") or []
            ),
            "control_revision": dispatch_runtime.get("control_revision"),
            "control_updated_at": dispatch_runtime.get("control_updated_at"),
            "control_updated_by": dispatch_runtime.get("control_updated_by"),
            "control_change_reason": dispatch_runtime.get("control_change_reason"),
            "control_event_hash": dispatch_runtime.get("control_event_hash"),
            "management_cycles_run": dispatch_runtime.get("management_cycles_run"),
            "last_management_status": dispatch_runtime.get("last_management_status"),
            "last_management_detail": dispatch_runtime.get("last_management_detail"),
            "last_management_action_count": dispatch_runtime.get("last_management_action_count"),
            "last_management_terminal_effect_count": dispatch_runtime.get(
                "last_management_terminal_effect_count"
            ),
            "last_management_broker_touched": dispatch_runtime.get(
                "last_management_broker_touched"
            ),
            "last_management_account_position_count": dispatch_runtime.get(
                "last_management_account_position_count"
            ),
            "last_management_excluded_position_count": dispatch_runtime.get(
                "last_management_excluded_position_count"
            ),
            "last_management_primary_position_count": dispatch_runtime.get(
                "last_management_primary_position_count"
            ),
            "last_management_simulator_handoff_position_count": dispatch_runtime.get(
                "last_management_simulator_handoff_position_count"
            ),
            "last_management_sources": list(
                dispatch_runtime.get("last_management_sources") or []
            ),
            "operator_position_edge_prompt_version": dispatch_runtime.get(
                "operator_position_edge_prompt_version"
            ),
            "last_operator_position_edge": dict(
                dispatch_runtime.get("last_operator_position_edge") or {}
            ),
            "last_operator_position_edge_status": dispatch_runtime.get(
                "last_operator_position_edge_status"
            ),
            "last_operator_position_edge_at": dispatch_runtime.get(
                "last_operator_position_edge_at"
            ),
            "last_operator_position_edge_provider": dispatch_runtime.get(
                "last_operator_position_edge_provider"
            ),
            "last_operator_position_edge_summary": dispatch_runtime.get(
                "last_operator_position_edge_summary"
            ),
            "last_operator_position_edge_candidate_count": dispatch_runtime.get(
                "last_operator_position_edge_candidate_count"
            ),
            "last_operator_position_edge_selected_count": dispatch_runtime.get(
                "last_operator_position_edge_selected_count"
            ),
            "last_operator_position_edge_stand_down_count": dispatch_runtime.get(
                "last_operator_position_edge_stand_down_count"
            ),
            "last_operator_position_edge_hard_policy_count": dispatch_runtime.get(
                "last_operator_position_edge_hard_policy_count"
            ),
            "last_mt5_demo_learning_sync_status": dispatch_runtime.get(
                "last_mt5_demo_learning_sync_status"
            ),
            "last_mt5_demo_learning_sync_at": dispatch_runtime.get(
                "last_mt5_demo_learning_sync_at"
            ),
            "last_mt5_demo_learning_sync_error": dispatch_runtime.get(
                "last_mt5_demo_learning_sync_error"
            ),
            "last_mt5_demo_learning_history_count": dispatch_runtime.get(
                "last_mt5_demo_learning_history_count"
            ),
            "last_mt5_demo_learning_bound_trade_count": dispatch_runtime.get(
                "last_mt5_demo_learning_bound_trade_count"
            ),
            "last_mt5_demo_learning_group_learning_ready": dispatch_runtime.get(
                "last_mt5_demo_learning_group_learning_ready"
            ),
            "last_mt5_demo_learning_overall_sample_ready": dispatch_runtime.get(
                "last_mt5_demo_learning_overall_sample_ready"
            ),
            "last_mt5_demo_learning_ready_group_count": dispatch_runtime.get(
                "last_mt5_demo_learning_ready_group_count"
            ),
            "last_mt5_demo_learning_min_samples_per_group": dispatch_runtime.get(
                "last_mt5_demo_learning_min_samples_per_group"
            ),
            "operator_trade_edge_prompt_version": dispatch_runtime.get(
                "operator_trade_edge_prompt_version"
            ),
            "last_operator_trade_edge": dict(
                dispatch_runtime.get("last_operator_trade_edge") or {}
            ),
            "last_operator_trade_edge_status": dispatch_runtime.get(
                "last_operator_trade_edge_status"
            ),
            "last_operator_trade_edge_at": dispatch_runtime.get(
                "last_operator_trade_edge_at"
            ),
            "last_operator_trade_edge_provider": dispatch_runtime.get(
                "last_operator_trade_edge_provider"
            ),
            "last_operator_trade_edge_summary": dispatch_runtime.get(
                "last_operator_trade_edge_summary"
            ),
            "last_operator_trade_edge_candidate_count": dispatch_runtime.get(
                "last_operator_trade_edge_candidate_count"
            ),
            "last_operator_trade_edge_approved_count": dispatch_runtime.get(
                "last_operator_trade_edge_approved_count"
            ),
            "last_operator_trade_edge_stand_down_count": dispatch_runtime.get(
                "last_operator_trade_edge_stand_down_count"
            ),
        },
        "autonomous_money_movement": dict(snapshot.get("last_money_movement") or {})
        if snapshot.get("last_money_movement")
        else _autonomous_money_movement_status(),
        "recent_lessons": lessons,
        "lessons_total": lessons_total,
        "objective": "Grow realized net profit and the account balance (paper now; real needs owner go-live).",
        "claim_boundary": (
            "The AI Operator is the trading edge. Its model tick steers owner-fenced "
            "controls, while autonomous entries and position management execute only "
            "through the guarded dispatch/execution runtime shown here. A running "
            "model scheduler does not by itself prove that execution is active."
        ),
    }


def runner_status() -> Dict[str, Any]:
    with _lock:
        snapshot = _state_snapshot_locked()
    return _build_status(snapshot)


def runner_status_fast(
    dispatch_runtime: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the polling shell without broker, ledger, or readiness rebuilds."""

    with _lock:
        snapshot = _state_snapshot_locked()
    thread = snapshot.get("thread")
    running = bool(thread and thread.is_alive())
    control = _load_control_state()
    dispatch_snapshot = dict(dispatch_runtime or {})
    return {
        "report_kind": REPORT_KIND,
        "running": running,
        "operational_state": _operational_state(running, dispatch_snapshot),
        "desired_running": bool(control.get("desired_running", running)),
        "interval_seconds": snapshot.get("interval"),
        "durable_control_state_path": str(_CONTROL_STATE_PATH),
        "started_at_iso": snapshot.get("started_at_iso") or None,
        "last_tick_iso": snapshot.get("last_tick_iso") or None,
        "last_summary": snapshot.get("last_summary") or None,
        "last_provider": snapshot.get("last_provider") or None,
        "last_ok": snapshot.get("last_ok"),
        "ticks_run": snapshot.get("ticks_run"),
        "last_error": snapshot.get("last_error") or None,
        "last_context_delivery": dict(snapshot.get("last_context_delivery") or {}),
        "model_provider": {},
        "recent_actions": [],
        "active_account_objective": {"status": "CACHE_WARMING"},
        "profit_and_balance": {"status": "CACHE_WARMING"},
        "professional_readiness": {"status": "CACHE_WARMING"},
        "execution_runtime": dispatch_snapshot,
        "autonomous_money_movement": dict(snapshot.get("last_money_movement") or {}),
        "recent_lessons": [],
        "lessons_total": 0,
        "objective": "Grow realized net profit and the account balance (paper now; real needs owner go-live).",
        "claim_boundary": (
            "This fast shell reports scheduler and execution-loop truth while the "
            "rich Operator evidence packet refreshes in the background."
        ),
    }


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
