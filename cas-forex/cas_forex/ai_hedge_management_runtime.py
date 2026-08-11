"""Broker-backed AI Hedge supervision for API and cockpit surfaces."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from cas_forex.ai_hedge_management import build_ai_hedge_management_handoff
from cas_forex.ai_hedge_management_cycle import (
    build_broker_position_management_snapshot,
)
from cas_forex.ai_hedge_supervision import build_ai_hedge_supervision_report
from cas_forex.dispatch_loop import resolve_active_management_runtime


def prepare_current_ai_hedge_management(
    *,
    runtime_context: Mapping[str, Any] | None = None,
    quote_context_builder: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build current supervision and drafts from the scheduler's active bridge."""

    context = dict(runtime_context or resolve_active_management_runtime())
    bridge = context.get("bridge")
    config = context.get("runtime_config")
    if str(context.get("status") or "") != "READY" or bridge is None:
        blocked = _blocked_handoff(context)
        return {
            "status": str(context.get("status") or "BRIDGE_UNAVAILABLE"),
            "context": context,
            "bridge": None,
            "config": config,
            "position_snapshot": {},
            "supervision": _blocked_supervision(context),
            "handoff": blocked,
        }

    snapshot = build_broker_position_management_snapshot(
        bridge,
        config=config,
        position_scope=str(context.get("position_scope") or "CAS_ONLY"),
        quote_context_builder=quote_context_builder,
    )
    supervision = build_ai_hedge_supervision_report(snapshot)
    handoff = build_ai_hedge_management_handoff(supervision)
    runtime_fields = _runtime_fields(context, bridge, snapshot)
    supervision = {**supervision, **runtime_fields}
    handoff = {**handoff, **runtime_fields}
    return {
        "status": "READY",
        "context": context,
        "bridge": bridge,
        "config": config,
        "position_snapshot": snapshot,
        "supervision": supervision,
        "handoff": handoff,
    }


def build_current_ai_hedge_supervision_report() -> dict[str, Any]:
    return dict(prepare_current_ai_hedge_management()["supervision"])


def build_current_ai_hedge_management_handoff() -> dict[str, Any]:
    return dict(prepare_current_ai_hedge_management()["handoff"])


def _runtime_fields(
    context: Mapping[str, Any],
    bridge: Any,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    selection = (
        dict(context.get("bridge_selection") or {})
        if isinstance(context.get("bridge_selection"), Mapping)
        else {}
    )
    health = (
        dict(snapshot.get("source_health") or {})
        if isinstance(snapshot.get("source_health"), Mapping)
        else {}
    )
    return {
        "runtime_truth_source": "ACTIVE_DISPATCH_MANAGEMENT_LANE",
        "runtime_mode": context.get("effective_mode"),
        "execution_lane": context.get("execution_lane"),
        "position_scope": context.get("position_scope"),
        "bridge_class": type(bridge).__name__,
        "bridge_selection_status": selection.get("status"),
        "bridge_selection_detail": selection.get("detail"),
        "account_position_count": int(
            snapshot.get("account_position_count")
            or snapshot.get("position_count")
            or 0
        ),
        "fresh_position_count": int(health.get("fresh_position_count") or 0),
        "stale_position_count": int(health.get("stale_position_count") or 0),
        "static_simulation_active": bool(snapshot.get("static_simulation_active")),
    }


def _blocked_handoff(context: Mapping[str, Any]) -> dict[str, Any]:
    status = str(context.get("status") or "BRIDGE_UNAVAILABLE")
    detail = str(context.get("detail") or "Active management bridge is unavailable.")
    return {
        "report_kind": "cas_forex_ai_hedge_management_handoff",
        "status": status,
        "runtime_truth_source": "ACTIVE_DISPATCH_MANAGEMENT_LANE",
        "runtime_mode": context.get("effective_mode"),
        "execution_lane": context.get("execution_lane"),
        "position_scope": context.get("position_scope"),
        "position_count": 0,
        "management_action_count": 0,
        "blocked_action_count": 1,
        "management_actions": [],
        "blocked_actions": [
            {
                "status": "BLOCKED",
                "block_code": status,
                "intent": "stand_down",
                "symbol": "UNKNOWN",
                "reason": detail,
                "broker_bound_action_authorized": False,
                "broker_touched": False,
                "orders_placed": False,
            }
        ],
        "dry_run_only": False,
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "detail": detail,
        "claim_boundary": (
            "The active management lane could not be resolved, so no broker "
            "draft or effect is available."
        ),
    }


def _blocked_supervision(context: Mapping[str, Any]) -> dict[str, Any]:
    status = str(context.get("status") or "BRIDGE_UNAVAILABLE")
    detail = str(context.get("detail") or "Active management bridge is unavailable.")
    return {
        "report_kind": "cas_forex_ai_hedge_supervision",
        "status": status,
        "runtime_truth_source": "ACTIVE_DISPATCH_MANAGEMENT_LANE",
        "runtime_mode": context.get("effective_mode"),
        "execution_lane": context.get("execution_lane"),
        "position_scope": context.get("position_scope"),
        "position_count": 0,
        "positions": [],
        "recommendations": [],
        "detail": detail,
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "claim_boundary": (
            "The active management lane could not be resolved, so supervision "
            "stands down without a broker effect."
        ),
    }
