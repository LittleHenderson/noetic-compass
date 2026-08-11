"""HTTP route for the single-call operator briefing.

Thin wrapper around `cas_forex.operator_briefing`. Uses the module's
own ``load_operator_briefing_inputs(repo_root)`` helper for disk I/O,
then runs the pure composer, then JSON-encodes the result.

The route exists so the LLM cockpit bot can answer "what is going on
right now?" with a single capability call instead of chaining loop
health + latest decision + live telemetry + MT5 probe + readiness.
The briefing is OBSERVATIONAL only — it never advises trades.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable

from fastapi import APIRouter

from . import autonomous_loop as autonomous_loop_route
from ..route_cache import run_serial_refresh
from cas_forex.operator_briefing import (
    OperatorBriefing,
    compose_operator_briefing,
    load_operator_briefing_inputs,
    refresh_operator_briefing_live_telemetry,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]
_CACHE_TTL_SECONDS = 120.0
_CACHE_LOCK = threading.RLock()
_CACHE_PAYLOAD: dict[str, Any] | None = None
_CACHE_BUILT_AT = 0.0
_CACHE_BUILDING = False
_CACHE_ERROR: str | None = None


def _default_loader() -> dict[str, Any]:
    return load_operator_briefing_inputs(REPO_ROOT)


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader
    _clear_cache()


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader
    _clear_cache()


def _briefing_to_payload(b: OperatorBriefing) -> dict[str, Any]:
    return asdict(b)


def _clear_cache() -> None:
    global _CACHE_PAYLOAD, _CACHE_BUILT_AT, _CACHE_BUILDING, _CACHE_ERROR
    with _CACHE_LOCK:
        _CACHE_PAYLOAD = None
        _CACHE_BUILT_AT = 0.0
        _CACHE_BUILDING = False
        _CACHE_ERROR = None


def _under_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _compose_payload() -> dict[str, Any]:
    inputs = _LOADER()
    return _briefing_to_payload(compose_operator_briefing(**inputs))


def _runtime_loop_status() -> dict[str, Any] | None:
    return autonomous_loop_route._runtime_loop_status()


def _runtime_backed_briefing_payload(payload: dict[str, Any]) -> dict[str, Any]:
    runtime = _runtime_loop_status()
    if not runtime or not runtime.get("running"):
        return payload

    out = dict(payload)
    out["loop_health_status"] = "running"
    out["cycles_today"] = max(int(out.get("cycles_today") or 0), int(runtime.get("cycles_run") or 0))
    out["runtime_loop"] = {
        "source": runtime.get("source"),
        "running": True,
        "mode": runtime.get("mode") or "PAPER",
        "stage": runtime.get("stage"),
        "cycles_run": runtime.get("cycles_run"),
        "last_run_iso": runtime.get("last_run_iso"),
        "status": runtime.get("status"),
        "claim_boundary": (
            "Runtime loop evidence is observational. It does not authorize live "
            "trading, broker ACCEPT, deposits, withdrawals, bank/card movement, "
            "payouts, or LICENSED status."
        ),
    }
    out["diagnostic_hints"] = tuple(
        hint
        for hint in (out.get("diagnostic_hints") or ())
        if "most recent cycle" not in str(hint).lower()
        and "autowake" not in str(hint).lower()
    )

    mode = runtime.get("mode") or "PAPER"
    source = str(runtime.get("source") or "runtime loop").replace("_", " ")
    stage = runtime.get("stage")
    stage_text = f", stage {stage}" if stage else ""
    runtime_sentence = (
        f"Autonomous loop runtime is running from {source} in {mode} mode{stage_text}; "
        f"{runtime.get('cycles_run') or 0} runtime cycle(s) observed."
    )
    briefing = str(out.get("plain_english_briefing") or "").strip()
    if briefing:
        if ". " in briefing:
            briefing = briefing.split(". ", 1)[1]
        else:
            briefing = ""
    briefing = _drop_stale_loop_hint_sentence(briefing)
    out["plain_english_briefing"] = " ".join(part for part in (runtime_sentence, briefing) if part)
    return out


def _drop_stale_loop_hint_sentence(briefing: str) -> str:
    marker = "Top diagnostic hint:"
    if marker not in briefing:
        return briefing
    before, after = briefing.split(marker, 1)
    lower_hint = after.lower()
    if "most recent cycle" in lower_hint or "autowake" in lower_hint:
        return before.strip()
    return briefing


def _with_cache_meta(payload: dict[str, Any], status: str, built_at: float | None) -> dict[str, Any]:
    out = _runtime_backed_briefing_payload(payload)
    try:
        from .live_telemetry import collect_live_telemetry

        out = refresh_operator_briefing_live_telemetry(out, collect_live_telemetry())
    except Exception:
        # Keep the last coherent cached briefing if the fast telemetry mirror is
        # temporarily unavailable; its stale/source fields remain explicit.
        pass
    out["cache_status"] = status
    out["cache_ttl_seconds"] = _CACHE_TTL_SECONDS
    out["cache_built_at_epoch"] = built_at
    return out


def _warming_payload(status: str = "warming") -> dict[str, Any]:
    return {
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
        "loop_health_status": "unknown",
        "cycles_today": 0,
        "decisions_today": 0,
        "executions_today": 0,
        "blocked_today": 0,
        "latest_decision_summary": None,
        "latest_decision_cycle_id": None,
        "latest_decision_overall_status": None,
        "open_position_count": 0,
        "total_floating_pnl": 0.0,
        "live_telemetry_source": "none",
        "live_telemetry_stale": True,
        "live_telemetry_last_update_iso": None,
        "live_price_source_status": None,
        "live_position_feed_label": "NONE",
        "live_position_feed_detail": "No broker or paper/demo movement snapshot is reporting positions right now.",
        "live_movement_source_truth": {
            "movement_stream_present": False,
            "telemetry_source": "none",
            "telemetry_stale": True,
            "telemetry_last_update_iso": None,
            "price_source_status": None,
            "price_source_label": None,
            "price_source_summary": None,
            "price_source_warning": None,
            "position_feed_label": "NONE",
            "position_feed_detail": "No broker or paper/demo movement snapshot is reporting positions right now.",
            "static_simulation_active": False,
            "open_position_count": 0,
            "broker_ticket_position_count": 0,
            "simulator_position_count": 0,
            "provider_priced_simulator_position_count": 0,
            "static_simulator_position_count": 0,
            "stale_price_position_count": 0,
            "static_position_count": 0,
            "source_label_counts": {},
            "configured_market_data_provider": None,
            "provider_usable_symbols": [],
            "static_fallback_symbols": [],
            "mt5_fallback_symbols": [],
            "provider_stale_symbols": [],
            "provider_freshness_max_age_seconds": None,
            "provider_error_count": 0,
            "attention_required": False,
            "detail": "No broker or paper/demo movement snapshot is reporting positions right now.",
            "local_detail": "No broker or paper/demo movement snapshot is reporting positions right now.",
        },
        "mt5_terminal_connected": False,
        "mt5_broker_api_verified": False,
        "readiness_gates_open": 0,
        "readiness_gates_total": 0,
        "public_launch_gate_status": "unknown",
        "public_launch_status": "unknown",
        "live_money_production_status": "unknown",
        "public_launch_gate_pass_count": 0,
        "public_launch_gate_block_count": 0,
        "public_launch_gate_blockers": (),
        "broker_truth_monitor_status": "unavailable",
        "broker_truth_ready_for_live": False,
        "broker_truth_paper_force_latched": False,
        "broker_truth_halt_reason_ids": (),
        "broker_truth_halt_reason_labels": (),
        "broker_truth_halt_reason_summary": "none",
        "broker_truth_position_protection_status": "POSITION_PROTECTION_UNAVAILABLE",
        "broker_truth_position_protection_label": "PROTECTION UNAVAILABLE",
        "broker_truth_unprotected_position_count": 0,
        "broker_truth_position_protection_detail": None,
        "broker_truth_mt5_connected": None,
        "broker_truth_mt5_is_demo": None,
        "broker_truth_open_position_count": 0,
        "autowake_present": False,
        "autowake_next_due_iso": None,
        "plain_english_briefing": (
            "Operator briefing is warming cached diagnostics. The API answered "
            "immediately, and the heavier evidence read is running in the background."
        ),
        "diagnostic_hints": ("Wait for the operator briefing cache to warm.",),
        "cache_status": status,
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "cache_built_at_epoch": None,
        "cache_error": _CACHE_ERROR,
    }


def _refresh_cache_worker() -> None:
    global _CACHE_PAYLOAD, _CACHE_BUILT_AT, _CACHE_BUILDING, _CACHE_ERROR
    try:
        payload = run_serial_refresh(_compose_payload)
        with _CACHE_LOCK:
            _CACHE_PAYLOAD = payload
            _CACHE_BUILT_AT = time.time()
            _CACHE_ERROR = None
    except Exception as exc:  # pragma: no cover - defensive runtime guard.
        with _CACHE_LOCK:
            _CACHE_ERROR = f"{type(exc).__name__}: {exc}"
    finally:
        with _CACHE_LOCK:
            _CACHE_BUILDING = False


def _ensure_background_refresh() -> bool:
    global _CACHE_BUILDING
    with _CACHE_LOCK:
        if _CACHE_BUILDING:
            return False
        _CACHE_BUILDING = True
    thread = threading.Timer(0.2, _refresh_cache_worker)
    thread.name = "cas-forex-operator-briefing-cache"
    thread.daemon = True
    thread.start()
    return True


def start_operator_briefing_cache_refresh() -> bool:
    """Start the read-only operator briefing cache warmup."""
    return _ensure_background_refresh()


@router.get("")
@router.get("/")
async def get_operator_briefing() -> dict[str, Any]:
    """Return the single-call operator briefing.

    Aggregates loop health, latest decision summary, open positions,
    MT5 connection state, and readiness gate counts into one
    observational snapshot. Returns 200 even when all inputs are
    missing (briefing reports ``loop_health_status: "unknown"``).
    """
    if _under_pytest():
        return _runtime_backed_briefing_payload(_compose_payload())

    now = time.time()
    with _CACHE_LOCK:
        payload = _CACHE_PAYLOAD
        built_at = _CACHE_BUILT_AT
        building = _CACHE_BUILDING
        fresh = payload is not None and (now - built_at) <= _CACHE_TTL_SECONDS

    if fresh and payload is not None:
        return _with_cache_meta(payload, "fresh", built_at)

    if not building:
        _ensure_background_refresh()

    if payload is not None:
        return _with_cache_meta(payload, "refreshing", built_at)

    return _with_cache_meta(_warming_payload(), "warming", None)
