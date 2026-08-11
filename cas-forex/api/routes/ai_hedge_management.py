"""HTTP routes for AI Operator Edge/Hedge management execution."""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from api import data as data_module
from api.live_money_cache import LIVE_MONEY_GATE_CACHE_KEYS, invalidate_live_money_gate_caches
from api.route_cache import store_cache_payload
from cas_forex.ai_hedge_management_execution import (
    latest_ai_hedge_management_execution,
    run_ai_hedge_management_action,
)
from cas_forex.ai_hedge_management_runtime import (
    build_current_ai_hedge_management_handoff,
    prepare_current_ai_hedge_management,
)
from cas_forex.broker_truth_monitor import monitor_fast_status, run_broker_truth_check
from cas_forex.time_utils import utc_now

from .live_telemetry import collect_live_telemetry


router = APIRouter()
AI_HEDGE_MANAGEMENT_CONFIRM_PHRASE = "CONFIRM AI EDGE MANAGEMENT"  # Legacy UI compatibility only.
POST_EXECUTION_REFRESH_EXTRA_CACHE_KEYS = (
    "live_telemetry",
    "broker_truth_monitor_fast_status",
    "auto_halt_status",
)


class AiHedgeManagementExecuteRequest(BaseModel):
    action_id: str = Field(default="", max_length=240)
    reason: str = Field(default="AI_OPERATOR_EDGE_MANAGEMENT", max_length=300)


def _confirm_required(
    *,
    action_id: str,
    dry_run: bool,
    confirm_owner_action: bool,
    confirm_phrase: str,
) -> dict[str, Any] | None:
    _ = (action_id, dry_run, confirm_owner_action, confirm_phrase)
    return None


@router.get("/handoff")
async def get_ai_hedge_management_handoff() -> dict[str, Any]:
    """Return current AI Operator Edge/Hedge management drafts."""
    return await run_in_threadpool(build_current_ai_hedge_management_handoff)


@router.get("/latest")
async def get_ai_hedge_management_latest() -> dict[str, Any]:
    """Return latest AI Operator Edge/Hedge management execution audit row."""
    return latest_ai_hedge_management_execution()


@router.post("/execute")
async def execute_ai_hedge_management_action(
    body: AiHedgeManagementExecuteRequest,
    dry_run: bool = Query(default=True),
    confirm_owner_action: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Dry-run or execute one current AI Operator Edge/Hedge management draft.

    Per-action owner confirmation is not required inside the armed delegated
    authority envelope; execution still passes through execution_guard.py and
    the configured broker bridge. ``confirm_*`` query params are retained for
    backward-compatible clients and ignored by the gate.
    """
    pending = _confirm_required(
        action_id=body.action_id,
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        confirm_phrase=confirm_phrase,
    )
    if pending is not None:
        return pending
    return await run_in_threadpool(
        _run_current_ai_hedge_management_action,
        body.action_id or None,
        dry_run,
        confirm_owner_action,
        body.reason,
    )


def _run_current_ai_hedge_management_action(
    action_id: str | None,
    dry_run: bool,
    confirm_owner_action: bool,
    reason: str,
) -> dict[str, Any]:
    prepared = prepare_current_ai_hedge_management()
    return run_ai_hedge_management_action(
        action_id=action_id,
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        reason=reason,
        bridge=prepared.get("bridge"),
        handoff=prepared.get("handoff"),
        config=prepared.get("config"),
        post_execution_refresh=_post_execution_broker_truth_refresh,
    )


def _post_execution_broker_truth_refresh(execution_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Refresh broker/account read models after a broker-touching AI action."""

    started = utc_now()
    invalidated_keys = list(LIVE_MONEY_GATE_CACHE_KEYS + POST_EXECUTION_REFRESH_EXTRA_CACHE_KEYS)
    invalidate_live_money_gate_caches(*POST_EXECUTION_REFRESH_EXTRA_CACHE_KEYS)

    reports: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []

    _refresh_packet(
        reports=reports,
        errors=errors,
        label="broker_truth_check",
        cache_key=None,
        builder=run_broker_truth_check,
    )
    _refresh_packet(
        reports=reports,
        errors=errors,
        label="broker_truth_monitor_fast_status",
        cache_key="broker_truth_monitor_fast_status",
        builder=monitor_fast_status,
    )
    _refresh_packet(
        reports=reports,
        errors=errors,
        label="live_telemetry",
        cache_key="live_telemetry",
        builder=collect_live_telemetry,
    )
    _refresh_packet(
        reports=reports,
        errors=errors,
        label="account_reconciliation",
        cache_key="account_reconciliation:False",
        builder=lambda: data_module.account_reconciliation(sync_to_broker=False),
    )
    _refresh_packet(
        reports=reports,
        errors=errors,
        label="account_reconciliation_broker_sync_preview",
        cache_key="account_reconciliation:True",
        builder=lambda: data_module.account_reconciliation(sync_to_broker=True),
    )
    _refresh_packet(
        reports=reports,
        errors=errors,
        label="movement_snapshot_provider",
        cache_key="movement_snapshot:True",
        builder=lambda: data_module.movement_stream(use_provider_quotes=True),
    )

    completed = utc_now()
    status = "REFRESH_RAN" if not errors else "REFRESH_PARTIAL" if reports else "REFRESH_FAILED"
    return {
        "report_kind": "cas_forex_ai_hedge_management_post_execution_refresh",
        "status": status,
        "started_at_iso": started.isoformat(),
        "completed_at_iso": completed.isoformat(),
        "duration_ms": round((completed - started).total_seconds() * 1000, 3),
        "cache_invalidated": True,
        "invalidated_cache_keys": invalidated_keys,
        "refreshed_packets": reports,
        "errors": errors,
        "error_count": len(errors),
        "execution_status": execution_payload.get("status"),
        "execution_audit_id": execution_payload.get("audit_id"),
        "selected_action_id": execution_payload.get("selected_action_id"),
        "broker_state_may_have_changed": True,
        "claim_boundary": (
            "Post-execution refresh is read-only evidence rebuilding after a guarded AI broker action. "
            "It does not open trades, move money, or bypass order_dispatch.py/execution_guard.py."
        ),
    }


def _refresh_packet(
    *,
    reports: dict[str, Any],
    errors: list[dict[str, Any]],
    label: str,
    cache_key: str | None,
    builder: Callable[[], Mapping[str, Any]],
) -> None:
    started = time.perf_counter()
    try:
        payload = builder()
        if not isinstance(payload, Mapping):
            raise TypeError(f"{label} returned {type(payload).__name__}, not a mapping")
        if cache_key:
            store_cache_payload(cache_key, payload)
        reports[label] = _compact_refresh_payload(
            payload,
            cache_key=cache_key,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )
    except Exception as exc:
        errors.append(
            {
                "packet": label,
                "cache_key": cache_key,
                "error_type": type(exc).__name__,
                "detail": str(exc),
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )


def _compact_refresh_payload(
    payload: Mapping[str, Any],
    *,
    cache_key: str | None,
    duration_ms: float,
) -> dict[str, Any]:
    totals = payload.get("totals") if isinstance(payload.get("totals"), Mapping) else {}
    latest_report = payload.get("latest_report") if isinstance(payload.get("latest_report"), Mapping) else {}
    return {
        "report_kind": payload.get("report_kind"),
        "status": payload.get("status"),
        "overall_status": payload.get("overall_status"),
        "monitor_status": payload.get("monitor_status") or latest_report.get("monitor_status"),
        "ready_for_live": payload.get("ready_for_live"),
        "telemetry_source": payload.get("telemetry_source"),
        "telemetry_stale": payload.get("telemetry_stale"),
        "position_feed_label": payload.get("position_feed_label"),
        "open_position_count": (
            totals.get("open_position_count")
            if "open_position_count" in totals
            else payload.get("mt5_open_position_count")
            or latest_report.get("mt5_open_position_count")
            or payload.get("position_count")
        ),
        "total_floating_pnl": totals.get("total_floating_pnl"),
        "broker_mode": payload.get("broker_mode"),
        "broker_receipt_validation_status": payload.get("broker_receipt_validation_status"),
        "sync_to_broker_snapshot": payload.get("sync_to_broker_snapshot"),
        "cache_key": cache_key,
        "cache_seeded": bool(cache_key),
        "duration_ms": duration_ms,
    }
