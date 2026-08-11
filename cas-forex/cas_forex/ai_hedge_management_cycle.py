"""Autonomous AI Edge/Hedge management cycle for open broker positions.

The handoff and executor already provide the deterministic management logic and
the guarded broker call. This module supplies the missing timed-cycle glue: it
reads fresh positions from the selected bridge, refreshes each position with a
current symbol-capable quote, chooses at most one action per position, and sends
the action through the existing execution guard and receipt reconciliation.

Completed one-shot actions and uncertain broker effects are persisted so a
restart or a fast loop cannot repeatedly partial-close or resend the same stop
change.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from cas_forex.ai_hedge_management import (
    build_ai_hedge_management_handoff,
    build_ai_operator_discretionary_management_options,
)
from cas_forex.ai_hedge_management_execution import (
    DEFAULT_AUDIT_PATH,
    run_ai_hedge_management_action,
)
from cas_forex.ai_operator_position_edge import (
    DEFAULT_AUDIT_PATH as DEFAULT_OPERATOR_POSITION_EDGE_AUDIT_PATH,
    DEFAULT_LATEST_PATH as DEFAULT_OPERATOR_POSITION_EDGE_LATEST_PATH,
    _position_origin_by_ticket,
    _action_ref_for_action,
    position_edge_enabled,
    review_management_actions_with_operator,
)
from cas_forex.ai_operator_scale_in import (
    DEFAULT_AUDIT_PATH as DEFAULT_OPERATOR_SCALE_IN_AUDIT_PATH,
    build_winning_scale_in_actions,
    run_operator_scale_in_action,
)
from cas_forex.pre_trade_money import (
    build_open_position_stop_risk,
    summarize_open_position_stop_risk,
)
from cas_forex.operator_account_context import (
    build_operator_account_context,
    enrich_position_open_pnl,
)
from cas_forex.time_utils import ensure_utc, utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "ai-hedge-management-cycle-state.json"
REPORT_KIND = "cas_forex_ai_hedge_management_cycle"
DEFAULT_ATTEMPT_COOLDOWN_SECONDS = 60
DEFAULT_MAX_ACTIONS_PER_CYCLE = 8
ONE_SHOT_INTENTS = {
    "close_partial",
    "close_full",
    "reduce",
    "move_stop_to_breakeven",
}
TRUTH_REARMABLE_INTENTS = {
    "set_stop_loss",
    "set_take_profit",
}
ACTION_PRIORITY = {
    "close_full": 0,
    "set_stop_loss": 1,
    "reduce": 2,
    "close_partial": 3,
    "move_stop_to_breakeven": 4,
    "set_take_profit": 5,
    "modify_take_profit": 6,
    "trail_stop": 7,
    "scale_in": 8,
}


def _bind_operator_selection_metadata(
    actions: Sequence[Mapping[str, Any]],
    report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind the exact model decision to every Operator-selected broker action."""

    decisions = {
        str(row.get("action_ref") or ""): dict(row)
        for row in (report.get("decisions") or [])
        if isinstance(row, Mapping)
        and str(row.get("decision") or "").upper() == "SELECT"
        and row.get("action_ref")
    }
    prepared: list[dict[str, Any]] = []
    for raw in actions:
        action = dict(raw)
        action_ref = _action_ref_for_action(action)
        decision = decisions.get(action_ref)
        if decision is not None:
            action.update(
                {
                    "operator_action_ref": action_ref,
                    "operator_event_hash": report.get("event_hash"),
                    "operator_prompt_version": report.get("prompt_version"),
                    "operator_decision_prompt_hash": report.get("model_prompt_hash"),
                    "operator_system_prompt_hash": report.get("system_prompt_hash"),
                    "operator_provider": report.get("provider"),
                    "operator_provider_label": report.get("provider_label"),
                    "operator_model_ref": report.get("model_ref"),
                    "operator_model_backend": report.get("model_backend"),
                    "operator_decision_context_hash": report.get("decision_context_hash"),
                    "operator_candidate_snapshot_hash": report.get("candidate_snapshot_hash"),
                    "operator_candidate_hash": action_ref,
                    "operator_action_set_hash": report.get("action_set_hash"),
                    "operator_decision": decision.get("decision"),
                    "operator_conviction": decision.get("conviction"),
                    "operator_reason": decision.get("reason"),
                    "operator_growth_case": decision.get("growth_case"),
                }
            )
        prepared.append(action)
    return prepared


POSITION_SCOPES = ("CAS_ONLY", "ALL_ACCOUNT")
TERMINAL_EFFECT_STATUSES = {
    "EXECUTED_RECONCILED",
    "EXECUTED_NOT_RECONCILED",
    "EXECUTED_RECONCILIATION_UNAVAILABLE",
}
PASSIVE_NO_CHANGE_BLOCK_CODES = {
    "STOP_ALREADY_PROTECTED",
    "TRAIL_WOULD_NOT_TIGHTEN",
    "TAKE_PROFIT_ALREADY_PRESENT",
}
CLAIM_BOUNDARY = (
    "The AI Edge/Hedge management cycle autonomously manages existing positions "
    "inside owner-delegated authority. It reads fresh broker/quote truth, chooses "
    "at most one action per position per cycle, and uses order_dispatch.py, "
    "execution_guard.py, and the selected broker bridge. It does not require "
    "per-action owner confirmation. It may add bounded exposure to an already-"
    "winning protected position when the Operator selects an exact broker-valid "
    "size. It cannot move money or bypass live/terminal/kill-switch/risk gates."
)

_state_lock = threading.RLock()


def run_ai_hedge_management_cycle(
    *,
    bridge: Any | None = None,
    config: Any = None,
    position_scope: str | None = None,
    execute: bool = True,
    state_path: Path | str = DEFAULT_STATE_PATH,
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
    quote_context_builder: Callable[..., Mapping[str, Any]] | None = None,
    post_execution_refresh: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    max_actions_per_cycle: int | None = None,
    attempt_cooldown_seconds: int | None = None,
    operator_provider: Any = None,
    operator_review_enabled: bool | None = None,
    operator_decision_context: Mapping[str, Any] | None = None,
    operator_audit_path: Path | str = DEFAULT_OPERATOR_POSITION_EDGE_AUDIT_PATH,
    operator_latest_path: Path | str = DEFAULT_OPERATOR_POSITION_EDGE_LATEST_PATH,
    scale_in_audit_path: Path | str = DEFAULT_OPERATOR_SCALE_IN_AUDIT_PATH,
) -> dict[str, Any]:
    """Run one autonomous management pass against current broker positions."""

    started = utc_now()
    resolved_bridge = bridge or _select_bridge(config)
    if resolved_bridge is None:
        return _finalize_cycle(
            started=started,
            status="BRIDGE_UNAVAILABLE",
            bridge=None,
            position_snapshot={},
            handoff={},
            executions=[],
            suppressed=[],
            state_path=state_path,
            state={},
            detail="No configured broker bridge is available for position management.",
        )

    position_snapshot = build_broker_position_management_snapshot(
        resolved_bridge,
        config=config,
        position_scope=position_scope,
        quote_context_builder=quote_context_builder,
    )
    positions = list(position_snapshot.get("positions") or [])
    if position_snapshot.get("status") == "BRIDGE_UNAVAILABLE":
        return _finalize_cycle(
            started=started,
            status="BRIDGE_UNAVAILABLE",
            bridge=resolved_bridge,
            position_snapshot=position_snapshot,
            handoff={},
            executions=[],
            suppressed=[],
            state_path=state_path,
            state=_load_state(state_path),
            detail=str(position_snapshot.get("detail") or "Broker positions are unavailable."),
        )

    state = _load_state(state_path)
    scale_in_units = state.setdefault("scale_in_units_by_parent", {})
    handoff = build_ai_hedge_management_handoff(movement_stream=position_snapshot)
    operator_review_active = position_edge_enabled(
        config,
        enabled=operator_review_enabled,
    )
    discretionary = (
        build_ai_operator_discretionary_management_options(
            position_snapshot,
            existing_actions=list(handoff.get("management_actions") or []),
        )
        if operator_review_active
        else {
            "report_kind": "cas_forex_ai_operator_discretionary_management_options",
            "status": "OPERATOR_POSITION_REVIEW_NOT_ENABLED",
            "position_count": len(positions),
            "recommendation_count": 0,
            "option_count": 0,
            "option_position_count": 0,
            "options": [],
            "blocked_option_count": 0,
            "blocked_options": [],
            "operator_selection_required": True,
            "model_failure_policy": "STAND_DOWN",
        }
    )
    scale_in = build_winning_scale_in_actions(
        position_snapshot,
        bridge=resolved_bridge,
        config=config,
        completed_units_by_parent=scale_in_units,
    )
    draft_actions = _ordered_actions(
        [
            *(handoff.get("management_actions") or []),
            *(discretionary.get("options") or []),
            *(scale_in.get("actions") or []),
        ]
    )
    non_entry_management_ready = any(
        str(row.get("intent") or "") != "scale_in" for row in draft_actions
    )
    handoff = {
        **handoff,
        "deterministic_handoff_status": handoff.get("status"),
        "status": (
            "READY_FOR_GUARDED_EXECUTION"
            if non_entry_management_ready
            else handoff.get("status")
        ),
        "ready_for_guarded_execution": non_entry_management_ready,
        "management_actions": draft_actions,
        "operator_discretionary": discretionary,
        "scale_in": scale_in,
        "scale_in_action_count": len(scale_in.get("actions") or []),
    }
    if not positions:
        return _finalize_cycle(
            started=started,
            status="WATCHING_NO_BROKER_POSITIONS",
            bridge=resolved_bridge,
            position_snapshot=position_snapshot,
            handoff=handoff,
            executions=[],
            suppressed=[],
            state_path=state_path,
            state=_load_state(state_path),
            detail="No open positions are present on the selected broker bridge.",
        )

    selected_actions, operator_position_edge = review_management_actions_with_operator(
        draft_actions,
        position_snapshot={
            **position_snapshot,
            "scale_in_readiness": scale_in,
        },
        bridge=resolved_bridge,
        config=config,
        provider=operator_provider,
        enabled=operator_review_enabled,
        decision_context=operator_decision_context,
        audit_path=operator_audit_path,
        latest_path=operator_latest_path,
    )
    actions = _ordered_actions(
        _bind_operator_selection_metadata(selected_actions, operator_position_edge)
    )

    records = state.setdefault("action_records", {})
    completed_once = state.setdefault("completed_once", {})
    cooldown = _positive_int(
        attempt_cooldown_seconds,
        getattr(config, "ai_hedge_management_attempt_cooldown_seconds", None),
        DEFAULT_ATTEMPT_COOLDOWN_SECONDS,
    )
    action_limit = _positive_int(
        max_actions_per_cycle,
        getattr(config, "ai_hedge_management_max_actions_per_cycle", None),
        DEFAULT_MAX_ACTIONS_PER_CYCLE,
    )
    now = utc_now()
    selected_tickets: set[str] = set()
    executions: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    for action in actions:
        ticket = str(action.get("broker_ticket") or "")
        if not ticket:
            suppressed.append(_suppressed(action, "MISSING_BROKER_TICKET"))
            continue
        if ticket in selected_tickets:
            suppressed.append(_suppressed(action, "ONE_ACTION_PER_POSITION_PER_CYCLE"))
            continue

        fingerprint = _action_fingerprint(action)
        once_key = _one_shot_key(action)
        reason = _suppression_reason(
            action,
            fingerprint=fingerprint,
            once_key=once_key,
            records=records,
            completed_once=completed_once,
            now=now,
            cooldown_seconds=cooldown,
        )
        if reason:
            suppressed.append(_suppressed(action, reason, fingerprint=fingerprint))
            continue
        if len(executions) >= action_limit:
            suppressed.append(_suppressed(action, "MAX_ACTIONS_PER_CYCLE_REACHED"))
            continue

        selected_tickets.add(ticket)
        if str(action.get("intent") or "") == "scale_in":
            if not execute:
                result = {
                    "report_kind": "cas_forex_ai_operator_scale_in_execution",
                    "status": "DRY_RUN",
                    "selected_action": dict(action),
                    "broker_touched": False,
                    "orders_placed": False,
                }
            else:
                result = run_operator_scale_in_action(
                    action,
                    operator_event_hash=str(operator_position_edge.get("event_hash") or ""),
                    bridge=resolved_bridge,
                    config=config,
                    audit_path=scale_in_audit_path,
                )
        else:
            result = run_ai_hedge_management_action(
                action_id=str(action.get("action_id") or "") or None,
                dry_run=not execute,
                confirm_owner_action=False,
                reason=(
                    "AI_OPERATOR_AUTONOMOUS_MANAGEMENT_CYCLE:"
                    f"{operator_position_edge.get('event_hash') or operator_position_edge.get('status') or 'NO_POSITION_EDGE_EVENT'}"
                ),
                bridge=resolved_bridge,
                audit_path=audit_path,
                handoff={
                    **handoff,
                    "management_actions": [dict(action)],
                    "management_action_count": 1,
                },
                config=config,
                post_execution_refresh=post_execution_refresh,
            )
        result = dict(result)
        result["action_fingerprint"] = fingerprint
        result["one_shot_key"] = once_key
        result["operator_position_edge_status"] = operator_position_edge.get("status")
        result["operator_position_edge_event_hash"] = operator_position_edge.get("event_hash")
        executions.append(result)
        _record_attempt(
            records,
            completed_once,
            action=action,
            fingerprint=fingerprint,
            once_key=once_key,
            result=result,
            attempted_at=now,
        )
        if (
            str(action.get("intent") or "") == "scale_in"
            and str(result.get("status") or "") in TERMINAL_EFFECT_STATUSES
        ):
            scale_in_units[ticket] = max(
                int(scale_in_units.get(ticket) or 0),
                int(action.get("scale_in_unit_index") or 0),
            )

    state["report_kind"] = "cas_forex_ai_hedge_management_cycle_state"
    state["updated_at_iso"] = utc_now().isoformat()
    state["claim_boundary"] = (
        "Durable duplicate suppression for autonomous position management. "
        "It records action effects and does not authorize a broker call."
    )
    _prune_state(state)

    if executions:
        executed_count = sum(
            1 for row in executions if str(row.get("status") or "") in TERMINAL_EFFECT_STATUSES
        )
        status = "ACTIONS_EXECUTED" if executed_count else "ACTIONS_ATTEMPTED"
        detail = (
            f"AI Edge/Hedge attempted {len(executions)} guarded management action(s); "
            f"{executed_count} reached a terminal-effect status."
        )
    elif actions and suppressed:
        status = "ACTIONS_SUPPRESSED"
        detail = "Current management drafts were duplicate, cooling down, or lower-priority actions for the same position."
    elif draft_actions and not actions and int(
        operator_position_edge.get("operator_deferred_count") or 0
    ) > 0:
        status = "AI_OPERATOR_REVIEW_DEFERRED"
        detail = (
            "Current broker-valid discretionary choices are waiting for the bounded "
            "Operator review interval; no model stand-down or broker action occurred."
        )
    elif draft_actions and not actions and int(
        operator_position_edge.get("operator_stand_down_count") or 0
    ) > 0:
        status = "AI_OPERATOR_STOOD_DOWN"
        detail = (
            "The AI Operator reviewed current broker-valid management drafts and "
            "stood down on every discretionary action."
        )
    elif handoff.get("blocked_action_count"):
        block_codes = {
            str(row.get("block_code") or "")
            for row in (handoff.get("blocked_actions") or [])
            if isinstance(row, Mapping)
        }
        quote_attempts = [
            row
            for row in (position_snapshot.get("quote_attempts") or [])
            if isinstance(row, Mapping)
        ]
        market_closed = bool(quote_attempts) and all(
            "market or symbol is closed" in str(row.get("detail") or "").lower()
            for row in quote_attempts
        )
        if market_closed:
            status = "WATCHING_MARKET_CLOSED"
            detail = (
                "Open broker positions remain protected by their broker-side stops and "
                "targets; the market is closed, so no fresh management action can execute."
            )
        elif block_codes and block_codes.issubset(PASSIVE_NO_CHANGE_BLOCK_CODES):
            status = "WATCHING_NO_ACTION"
            detail = "Fresh broker positions were reviewed; calculated management changes would not tighten or improve the current protection."
        else:
            status = "MANAGEMENT_BLOCKED"
            detail = "Current broker positions produced management recommendations, but fresh-price or position prerequisites blocked execution."
    else:
        status = "WATCHING_NO_ACTION"
        detail = "Fresh broker positions were reviewed; no management change is justified right now."

    return _finalize_cycle(
        started=started,
        status=status,
        bridge=resolved_bridge,
        position_snapshot=position_snapshot,
        handoff=handoff,
        executions=executions,
        suppressed=suppressed,
        state_path=state_path,
        state=state,
        detail=detail,
        operator_review=operator_position_edge,
    )


def build_broker_position_management_snapshot(
    bridge: Any,
    *,
    config: Any = None,
    position_scope: str | None = None,
    quote_context_builder: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Adapt current bridge positions into the AI Hedge movement contract."""

    generated = utc_now()
    if not _safe_bool_call(bridge, "is_connected", default=True):
        return {
            "report_kind": "cas_forex_broker_position_management_snapshot",
            "status": "BRIDGE_UNAVAILABLE",
            "timestamp": generated.isoformat(),
            "positions": [],
            "detail": "Selected broker bridge is not connected.",
        }
    resolved_scope = _normalize_position_scope(
        position_scope or getattr(config, "ai_hedge_position_scope", "CAS_ONLY")
    )
    try:
        raw_positions, position_method, account_position_count = _read_positions(
            bridge,
            scope=resolved_scope,
        )
    except Exception as exc:
        return {
            "report_kind": "cas_forex_broker_position_management_snapshot",
            "status": "BRIDGE_UNAVAILABLE",
            "timestamp": generated.isoformat(),
            "positions": [],
            "detail": f"{type(exc).__name__}: {exc}",
        }

    if quote_context_builder is not None:
        quote_builder = quote_context_builder
    else:
        prefer_mt5 = "MT5" in type(bridge).__name__.upper()
        quote_builder = lambda symbol, *, config=None: _default_quote_context_builder(
            symbol,
            config=config,
            prefer_mt5=prefer_mt5,
        )
    max_age = _quote_max_age_seconds(config)
    management_policy = _management_policy(config)
    risk_cap_pct = management_policy.get("max_risk_pct_per_trade")
    account_risk_snapshot = _bridge_account_risk_snapshot(bridge)
    position_origins = _position_origin_by_ticket()
    used_position_origins: dict[str, dict[str, Any]] = {}
    positions: list[dict[str, Any]] = []
    fresh_symbols: list[str] = []
    stale_symbols: list[str] = []
    quote_attempts: list[dict[str, Any]] = []
    quote_cache: dict[str, Mapping[str, Any]] = {}

    for raw in raw_positions:
        position = _normalize_position(raw, reference_time=generated)
        ticket = str(position.get("broker_ticket") or "").strip()
        origin = dict(position_origins.get(ticket) or {})
        if origin:
            used_position_origins[ticket] = origin
            for key in (
                "decision_ref",
                "order_id",
                "strategy",
                "strategy_id",
                "timeframe",
                "original_entry_price",
                "original_stop_loss",
                "original_take_profit",
                "original_volume",
                "admission_stop_risk_usd",
                "entry_sizing_ref",
                "entry_sizing_label",
                "entry_sizing_plan_hash",
                "entry_operator_event_hash",
            ):
                if origin.get(key) is not None:
                    position[key] = origin.get(key)
            origin_opened_at = origin.get("opened_at_iso")
            if origin_opened_at:
                position["opened_at_iso"] = origin_opened_at
                position["opened_at_source"] = origin.get("opened_at_source")
                position["age_days"] = _position_age_days(
                    str(origin_opened_at),
                    None,
                    reference_time=generated,
                )
        symbol = str(position.get("symbol") or "")
        if symbol not in quote_cache:
            try:
                quote_cache[symbol] = dict(quote_builder(symbol, config=config) or {})
            except TypeError:
                quote_cache[symbol] = dict(quote_builder(symbol) or {})
            except Exception as exc:
                quote_cache[symbol] = {"market_snapshot": None, "quote_error": f"{type(exc).__name__}: {exc}"}
        context = quote_cache[symbol]
        snapshot = context.get("market_snapshot") if isinstance(context, Mapping) else None
        usable, reason, age_seconds = _quote_usable(snapshot, max_age_seconds=max_age)
        if usable and isinstance(snapshot, Mapping):
            current = _exit_price(position.get("side"), snapshot)
            if current is None or current <= 0:
                usable = False
                reason = "fresh quote has no usable exit-side bid/ask"
            else:
                position["current_price"] = current
        position["price_stale"] = not usable
        position["stale_reason"] = None if usable else reason
        position["price_source"] = (
            str(context.get("quote_source") or snapshot.get("quote_source") or snapshot.get("source") or "broker_quote")
            if usable and isinstance(snapshot, Mapping)
            else "broker_quote_unavailable"
        )
        position["quote_age_seconds"] = age_seconds
        position["position_source_label"] = "BROKER_TERMINAL_TRUTH"
        stop_risk = build_open_position_stop_risk(
            symbol=symbol,
            direction=position.get("side"),
            lots=position.get("lot_size"),
            open_price=position.get("open_price"),
            current_price=position.get("current_price"),
            stop_loss=position.get("stop_loss"),
            take_profit=position.get("take_profit"),
            account_snapshot=account_risk_snapshot,
            bridge=bridge,
            config=config,
            risk_cap_pct=risk_cap_pct,
        )
        position["stop_risk"] = stop_risk
        for key in (
            "risk_at_stop_usd",
            "risk_at_stop_pct_equity",
            "remaining_to_stop_drawdown_usd",
            "remaining_to_stop_drawdown_pct_equity",
            "stop_locked_profit_usd",
            "risk_cap_pct",
            "risk_cap_breached",
            "risk_basis",
            "risk_economics_source",
        ):
            position[key] = stop_risk.get(key)
        positions.append(position)
        (fresh_symbols if usable else stale_symbols).append(symbol)
        quote_attempts.append(
            {
                "symbol": symbol,
                "usable": usable,
                "detail": None if usable else reason,
                "quote_source": context.get("quote_source") if isinstance(context, Mapping) else None,
                "quote_feed_label": context.get("quote_feed_label") if isinstance(context, Mapping) else None,
                "age_seconds": age_seconds,
            }
        )

    if positions and fresh_symbols:
        source_status = "PROVIDER_ACTIVE"
    elif positions:
        source_status = "UNAVAILABLE"
    else:
        source_status = "NO_OPEN_POSITIONS"
    stream_id = _snapshot_id(generated, bridge, positions)
    excluded_position_count = max(
        0,
        int(account_position_count or len(positions)) - len(positions),
    )
    position_risk = summarize_open_position_stop_risk(
        positions,
        risk_cap_pct=risk_cap_pct,
    )
    account_growth_context = build_operator_account_context(
        bridge,
        positions=positions,
        account_snapshot=account_risk_snapshot,
    )
    return {
        "report_kind": "cas_forex_broker_position_management_snapshot",
        "status": "FRESH" if not stale_symbols else "ATTENTION",
        "stream_id": stream_id,
        "timestamp": generated.isoformat(),
        "positions": positions,
        "position_entry_origins": used_position_origins,
        "position_count": len(positions),
        "account_position_count": int(account_position_count or len(positions)),
        "excluded_position_count": excluded_position_count,
        "position_scope": resolved_scope,
        "position_scope_label": (
            "CAS-tagged positions only"
            if resolved_scope == "CAS_ONLY"
            else "Every open position on the account"
        ),
        "price_source_status": source_status,
        "price_source_label": "FRESH BROKER / PROVIDER QUOTES" if fresh_symbols else "BROKER QUOTES UNAVAILABLE",
        "price_source_summary": (
            f"Read {len(positions)} broker position(s); {len(fresh_symbols)} have a fresh executable quote and "
            f"{len(stale_symbols)} are blocked from AI management."
        ),
        "position_feed_label": "BROKER TRUTH",
        "position_feed_detail": (
            f"Positions read directly through {type(bridge).__name__}.{position_method}; "
            f"owner scope is {resolved_scope}."
        ),
        "provider_usable_symbols": sorted(set(fresh_symbols)),
        "static_fallback_symbols": [],
        "static_simulation_active": False,
        "source_health": {
            "fresh_for_trade_management": bool(positions and fresh_symbols and not stale_symbols),
            "fresh_position_count": len(fresh_symbols),
            "stale_position_count": len(stale_symbols),
            "broker_ticket_position_count": sum(1 for row in positions if row.get("broker_ticket")),
            "account_position_count": int(account_position_count or len(positions)),
            "excluded_position_count": excluded_position_count,
        },
        "management_policy": management_policy,
        "position_risk": position_risk,
        "account_risk_snapshot": account_risk_snapshot,
        "account_growth_context": account_growth_context,
        "quote_attempts": quote_attempts,
        "bridge_class": type(bridge).__name__,
        "bridge_executes_real_orders": _safe_bool_call(bridge, "will_execute_real_order", default=False),
        "claim_boundary": (
            "This is fresh broker-position and quote truth for autonomous management. "
            "It does not itself call modify_position or close_position."
        ),
    }


def _select_bridge(config: Any) -> Any:
    from cas_forex.broker_control import select_bridge

    return select_bridge(config)


def _default_quote_context_builder(
    symbol: str,
    *,
    config: Any = None,
    prefer_mt5: bool = False,
) -> Mapping[str, Any]:
    from cas_forex.order_dispatch import build_dispatch_quote_context

    return build_dispatch_quote_context(
        symbol,
        config=config,
        prefer_mt5=prefer_mt5,
    )


def _read_positions(
    bridge: Any,
    *,
    scope: str,
) -> tuple[list[Mapping[str, Any]], str, int | None]:
    method = "get_open_positions" if scope == "CAS_ONLY" else "get_all_open_positions"
    fn = getattr(bridge, method, None)
    if not callable(fn):
        raise RuntimeError(
            f"{scope} position management requires bridge.{method}; scope cannot be proven"
        )
    rows = fn()
    if rows is None:
        raise RuntimeError(f"{method} returned no position collection")
    selected = [_mapping(row) for row in rows]
    account_position_count: int | None = len(selected)
    if scope == "CAS_ONLY":
        all_fn = getattr(bridge, "get_all_open_positions", None)
        if callable(all_fn):
            try:
                all_rows = all_fn()
                if all_rows is not None:
                    account_position_count = len(list(all_rows))
            except Exception:
                account_position_count = None
    return selected, method, account_position_count


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {
        key: getattr(value, key)
        for key in (
            "ticket", "symbol", "type", "side", "volume", "lots", "open_price",
            "price_open", "current_price", "price_current", "stop_loss", "sl",
            "take_profit", "tp", "profit", "swap", "commission", "comment",
            "time", "time_msc", "time_open_iso", "opened_at_iso", "age_days",
        )
        if hasattr(value, key)
    }


def _normalize_position(
    raw: Mapping[str, Any],
    *,
    reference_time: datetime,
) -> dict[str, Any]:
    ticket = raw.get("ticket", raw.get("broker_ticket", raw.get("position")))
    symbol = str(raw.get("symbol") or "").strip()
    side = _side(raw.get("side", raw.get("type")))
    opened_at_iso = _opened_at_iso(raw)
    age_days = _position_age_days(
        opened_at_iso,
        raw.get("age_days"),
        reference_time=reference_time,
    )
    return enrich_position_open_pnl({
        "row_id": f"broker:{ticket}" if ticket not in (None, "") else f"broker:{symbol}",
        "broker_ticket": ticket,
        "symbol": symbol,
        "side": side,
        "lot_size": _number(raw.get("volume", raw.get("lots", raw.get("lot_size")))),
        "open_price": _number(raw.get("open_price", raw.get("price_open"))),
        "current_price": _number(raw.get("current_price", raw.get("price_current"))),
        "stop_loss": _number(raw.get("stop_loss", raw.get("sl"))),
        "take_profit": _number(raw.get("take_profit", raw.get("tp"))),
        "floating_pnl_usd": _number(raw.get("profit")),
        "floating_pnl_units": _number(raw.get("profit")),
        "swap_usd": _number(raw.get("swap")),
        "commission_usd": _number(raw.get("commission")),
        "broker_comment": raw.get("comment"),
        "opened_at_iso": opened_at_iso,
        "age_days": age_days,
    })


def _side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG", "0"}:
        return "LONG"
    if text in {"SELL", "SHORT", "1"}:
        return "SHORT"
    return text or "UNKNOWN"


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_position_scope(value: Any) -> str:
    scope = str(value or "CAS_ONLY").strip().upper()
    return scope if scope in POSITION_SCOPES else "CAS_ONLY"


def _management_policy(config: Any) -> dict[str, Any]:
    control_values = _position_management_control_values(config)
    configured_risk_cap = _config_float(
        config,
        "max_risk_per_trade_pct",
        0.5,
        minimum=0.0001,
    )
    return {
        "emergency_stop_distance_pct": _config_float(
            config, "ai_hedge_emergency_stop_distance_pct", 0.5, minimum=0.0001
        ),
        "emergency_stop_market_buffer_pct": _config_float(
            config,
            "ai_hedge_emergency_stop_market_buffer_pct",
            0.05,
            minimum=0.0001,
        ),
        "take_profit_reward_risk": _config_float(
            config, "ai_hedge_take_profit_reward_risk", 2.0, minimum=0.1
        ),
        "take_profit_extension_trigger_fraction": min(
            0.99,
            _config_float(
                config,
                "ai_hedge_take_profit_extension_trigger_fraction",
                0.8,
                minimum=0.1,
            ),
        ),
        "take_profit_extension_factor": _config_float(
            config, "ai_hedge_take_profit_extension_factor", 1.5, minimum=1.01
        ),
        "time_stop_hours": _config_float(
            config, "ai_hedge_time_stop_hours", 72.0, minimum=0.0
        ),
        "trailing_stop_enabled": bool(
            int(_mapping_float(control_values, "trailing_stop_enabled", 1.0))
        ),
        "trailing_lock_fraction": min(
            0.9,
            max(
                0.1,
                _mapping_float(control_values, "trailing_lock_fraction", 0.5),
            ),
        ),
        "max_risk_pct_per_trade": max(
            0.0001,
            _mapping_float(
                control_values,
                "max_risk_pct_per_trade",
                configured_risk_cap,
            ),
        ),
    }


def _position_management_control_values(config: Any) -> Any:
    supplied = getattr(config, "ai_control_values", None)
    if isinstance(supplied, Mapping):
        return supplied
    try:
        from cas_forex.ai_control_authority import get_authority

        return get_authority().control
    except Exception:
        return {}


def _bridge_account_risk_snapshot(bridge: Any) -> dict[str, Any]:
    getter = getattr(bridge, "get_account_info", None)
    raw: Any = None
    if callable(getter):
        try:
            raw = getter()
        except Exception:
            raw = None
    if not isinstance(raw, Mapping):
        mt5 = getattr(bridge, "_mt5", None)
        account_getter = getattr(mt5, "account_info", None)
        if callable(account_getter):
            try:
                raw = account_getter()
            except Exception:
                raw = None
    if raw is None:
        return {}

    def value(*keys: str) -> Any:
        for key in keys:
            item = raw.get(key) if isinstance(raw, Mapping) else getattr(raw, key, None)
            if item is not None:
                return item
        return None

    balance = value("balance", "balance_usd")
    equity = value("equity", "equity_usd")
    floating = value("floating_pnl", "floating_pnl_usd", "profit")
    if floating is None:
        try:
            floating = float(equity) - float(balance)
        except (TypeError, ValueError):
            floating = None
    demo_checker = getattr(bridge, "is_demo_account", None)
    try:
        is_demo = bool(demo_checker()) if callable(demo_checker) else None
    except Exception:
        is_demo = None
    return {
        "login": value("login", "account_login") or getattr(bridge, "login", None),
        "server": value("server", "account_server") or getattr(bridge, "server", None),
        "currency": value("currency") or "USD",
        "is_demo": is_demo,
        "balance": value("balance", "balance_usd"),
        "equity": value("equity", "equity_usd"),
        "floating_pnl": floating,
        "margin": value("margin", "margin_used_usd"),
        "margin_free": value("margin_free", "free_margin", "free_margin_usd"),
        "leverage": value("leverage", "account_leverage"),
    }


def _mapping_float(
    values: Any,
    key: str,
    default: float,
) -> float:
    try:
        raw = values.get(key)
        return float(default if raw is None else raw)
    except (AttributeError, KeyError, TypeError, ValueError):
        return float(default)


def _config_float(
    config: Any,
    key: str,
    default: float,
    *,
    minimum: float,
) -> float:
    try:
        value = float(getattr(config, key, default))
    except (TypeError, ValueError):
        value = float(default)
    return max(float(minimum), value)


def _opened_at_iso(raw: Mapping[str, Any]) -> str | None:
    direct = raw.get("opened_at_iso") or raw.get("time_open_iso")
    if isinstance(direct, datetime):
        return ensure_utc(direct).isoformat()
    if direct not in (None, ""):
        try:
            return ensure_utc(
                datetime.fromisoformat(str(direct).replace("Z", "+00:00"))
            ).isoformat()
        except ValueError:
            pass
    timestamp = _number(raw.get("time_msc"))
    if timestamp is not None:
        timestamp /= 1000.0
    else:
        timestamp = _number(raw.get("time"))
    if timestamp is None or timestamp <= 0:
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _position_age_days(
    opened_at_iso: str | None,
    supplied_age_days: Any,
    *,
    reference_time: datetime,
) -> float | None:
    opened = _parse_iso(opened_at_iso)
    if opened is not None:
        return round(
            max(0.0, (ensure_utc(reference_time) - opened).total_seconds()) / 86_400.0,
            6,
        )
    try:
        supplied = float(supplied_age_days)
    except (TypeError, ValueError):
        return None
    return max(0.0, supplied)


def _quote_usable(snapshot: Any, *, max_age_seconds: float) -> tuple[bool, str | None, float | None]:
    if not isinstance(snapshot, Mapping):
        return False, "no symbol-capable provider/MT5 quote is available", None
    if bool(snapshot.get("synthetic_fallback")):
        return False, "quote is a synthetic fallback", _quote_age_seconds(snapshot)
    if not bool(snapshot.get("is_market_open")):
        return False, "quote reports the market or symbol is closed", _quote_age_seconds(snapshot)
    age = _quote_age_seconds(snapshot)
    if age is None:
        return False, "quote timestamp is missing or unparseable", None
    if age > max_age_seconds:
        return False, f"quote is stale ({age:.1f}s > {max_age_seconds:.1f}s)", age
    bid = _number(snapshot.get("bid"))
    ask = _number(snapshot.get("ask"))
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        return False, f"quote has invalid bid/ask (bid={bid}, ask={ask})", age
    return True, None, age


def _quote_age_seconds(snapshot: Mapping[str, Any]) -> float | None:
    value = snapshot.get("timestamp")
    if isinstance(value, datetime):
        parsed = ensure_utc(value)
    elif value not in (None, ""):
        try:
            parsed = ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
        except ValueError:
            return None
    else:
        return None
    return max(0.0, (ensure_utc(utc_now()) - parsed).total_seconds())


def _exit_price(side: Any, snapshot: Mapping[str, Any]) -> float | None:
    return _number(snapshot.get("bid" if str(side).upper() == "LONG" else "ask"))


def _quote_max_age_seconds(config: Any) -> float:
    try:
        return max(1.0, float(getattr(config, "dispatch_quote_max_age_seconds", 120) or 120))
    except (TypeError, ValueError):
        return 120.0


def _ordered_actions(values: Sequence[Any]) -> list[dict[str, Any]]:
    actions = [dict(row) for row in values if isinstance(row, Mapping)]
    return sorted(
        actions,
        key=lambda row: (
            ACTION_PRIORITY.get(str(row.get("intent") or ""), 99),
            str(row.get("broker_ticket") or ""),
            str(row.get("action_id") or ""),
        ),
    )


def _action_fingerprint(action: Mapping[str, Any]) -> str:
    body = {
        "ticket": str(action.get("broker_ticket") or ""),
        "intent": str(action.get("intent") or ""),
        "method": str(action.get("broker_method") or ""),
        "volume": _number(action.get("volume")),
        "previous_stop_loss": _number(action.get("previous_stop_loss")),
        "stop_loss": _number(action.get("stop_loss")),
        "previous_take_profit": _number(action.get("previous_take_profit")),
        "take_profit": _number(action.get("take_profit")),
        "scale_in_unit_index": action.get("scale_in_unit_index"),
        "sizing_ref": action.get("sizing_ref"),
        "order_id": (
            action.get("order_request", {}).get("order_id")
            if isinstance(action.get("order_request"), Mapping)
            else None
        ),
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:20]
    return f"ai-hedge-action:{digest}"


def _one_shot_key(action: Mapping[str, Any]) -> str | None:
    intent = str(action.get("intent") or "")
    if intent not in ONE_SHOT_INTENTS:
        return None
    return f"{action.get('broker_ticket')}:{intent}"


def _suppression_reason(
    action: Mapping[str, Any],
    *,
    fingerprint: str,
    once_key: str | None,
    records: Mapping[str, Any],
    completed_once: Mapping[str, Any],
    now: datetime,
    cooldown_seconds: int,
) -> str | None:
    if once_key and once_key in completed_once:
        return "ONE_SHOT_ACTION_ALREADY_COMPLETED"
    record = records.get(fingerprint)
    if not isinstance(record, Mapping):
        return None
    if bool(record.get("terminal_effect")):
        if (
            str(action.get("intent") or "") in TRUTH_REARMABLE_INTENTS
            and str(record.get("status") or "") == "EXECUTED_RECONCILED"
        ):
            return None
        return "EXACT_TERMINAL_EFFECT_ALREADY_RECORDED"
    if bool(record.get("uncertain_broker_effect")):
        return "UNCERTAIN_BROKER_EFFECT_REQUIRES_NEW_TRUTH"
    attempted = _parse_iso(record.get("attempted_at_iso"))
    if attempted is not None:
        age = max(0.0, (ensure_utc(now) - attempted).total_seconds())
        if age < cooldown_seconds:
            return "ACTION_ATTEMPT_COOLDOWN"
    return None


def _record_attempt(
    records: dict[str, Any],
    completed_once: dict[str, Any],
    *,
    action: Mapping[str, Any],
    fingerprint: str,
    once_key: str | None,
    result: Mapping[str, Any],
    attempted_at: datetime,
) -> None:
    status = str(result.get("status") or "UNKNOWN")
    terminal_effect = status in TERMINAL_EFFECT_STATUSES
    uncertain = status == "BRIDGE_ERROR"
    record = {
        "fingerprint": fingerprint,
        "action_id": action.get("action_id"),
        "broker_ticket": action.get("broker_ticket"),
        "intent": action.get("intent"),
        "status": status,
        "attempted_at_iso": ensure_utc(attempted_at).isoformat(),
        "terminal_effect": terminal_effect,
        "uncertain_broker_effect": uncertain,
        "audit_id": result.get("audit_id"),
        "terminal_receipt_status": result.get("terminal_receipt_status"),
    }
    records[fingerprint] = record
    if once_key and terminal_effect:
        completed_once[once_key] = dict(record)


def _suppressed(
    action: Mapping[str, Any],
    reason: str,
    *,
    fingerprint: str | None = None,
) -> dict[str, Any]:
    return {
        "action_id": action.get("action_id"),
        "broker_ticket": action.get("broker_ticket"),
        "symbol": action.get("symbol"),
        "intent": action.get("intent"),
        "action_fingerprint": fingerprint,
        "status": "SUPPRESSED",
        "reason": reason,
    }


def _finalize_cycle(
    *,
    started: datetime,
    status: str,
    bridge: Any,
    position_snapshot: Mapping[str, Any],
    handoff: Mapping[str, Any],
    executions: Sequence[Mapping[str, Any]],
    suppressed: Sequence[Mapping[str, Any]],
    state_path: Path | str,
    state: dict[str, Any],
    detail: str,
    operator_review: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    completed = utc_now()
    execution_rows = [dict(row) for row in executions]
    scale_in = (
        dict(handoff.get("scale_in") or {})
        if isinstance(handoff.get("scale_in"), Mapping)
        else {}
    )
    discretionary = (
        dict(handoff.get("operator_discretionary") or {})
        if isinstance(handoff.get("operator_discretionary"), Mapping)
        else {}
    )
    management_actions = [
        dict(row)
        for row in (handoff.get("management_actions") or [])
        if isinstance(row, Mapping)
    ]
    scale_in_blockers = [
        {
            "parent_broker_ticket": row.get("parent_broker_ticket"),
            "symbol": row.get("symbol"),
            "reason": row.get("reason"),
            "sizing_plan_hash": row.get("sizing_plan_hash"),
        }
        for row in (scale_in.get("blockers") or [])
        if isinstance(row, Mapping)
    ]
    payload = {
        "report_kind": REPORT_KIND,
        "status": status,
        "generated_at_iso": completed.isoformat(),
        "duration_ms": round((completed - started).total_seconds() * 1000.0, 3),
        "detail": detail,
        "position_snapshot_status": position_snapshot.get("status"),
        "position_count": int(position_snapshot.get("position_count") or len(position_snapshot.get("positions") or [])),
        "position_tickets": [
            str(row.get("broker_ticket") or row.get("ticket") or "")
            for row in (position_snapshot.get("positions") or [])
            if isinstance(row, Mapping) and (row.get("broker_ticket") or row.get("ticket"))
        ],
        "account_position_count": int(
            position_snapshot.get("account_position_count")
            or position_snapshot.get("position_count")
            or len(position_snapshot.get("positions") or [])
        ),
        "excluded_position_count": int(position_snapshot.get("excluded_position_count") or 0),
        "position_scope": position_snapshot.get("position_scope") or "CAS_ONLY",
        "position_scope_label": position_snapshot.get("position_scope_label") or "CAS-tagged positions only",
        "fresh_position_count": int((position_snapshot.get("source_health") or {}).get("fresh_position_count") or 0),
        "stale_position_count": int((position_snapshot.get("source_health") or {}).get("stale_position_count") or 0),
        "price_source_status": position_snapshot.get("price_source_status"),
        "price_source_label": position_snapshot.get("price_source_label"),
        "quote_attempts": [
            {
                "symbol": row.get("symbol"),
                "usable": row.get("usable"),
                "detail": row.get("detail"),
                "quote_source": row.get("quote_source"),
                "quote_feed_label": row.get("quote_feed_label"),
                "age_seconds": row.get("age_seconds"),
            }
            for row in (position_snapshot.get("quote_attempts") or [])
            if isinstance(row, Mapping)
        ],
        "handoff_status": handoff.get("status"),
        "draft_action_count": len(management_actions),
        "operator_discretionary_status": discretionary.get("status"),
        "operator_discretionary_option_count": int(
            discretionary.get("option_count")
            or len(discretionary.get("options") or [])
        ),
        "operator_discretionary_position_count": int(
            discretionary.get("option_position_count") or 0
        ),
        "operator_discretionary_blocked_option_count": int(
            discretionary.get("blocked_option_count") or 0
        ),
        "operator_discretionary_model_failure_policy": discretionary.get(
            "model_failure_policy"
        ),
        "scale_in_status": scale_in.get("status"),
        "scale_in_action_count": int(
            scale_in.get("action_count") or len(scale_in.get("actions") or [])
        ),
        "scale_in_parent_candidate_count": int(
            scale_in.get("parent_candidate_count") or 0
        ),
        "scale_in_blocker_count": len(scale_in_blockers),
        "scale_in_blockers": scale_in_blockers,
        "scale_in_max_compound_units": int(
            scale_in.get("max_compound_units") or 0
        ),
        "scale_in_minimum_profit_r": scale_in.get("minimum_profit_r"),
        "blocked_action_count": int(handoff.get("blocked_action_count") or 0),
        "blocked_actions": [
            {
                "block_code": row.get("block_code"),
                "symbol": row.get("symbol"),
                "broker_ticket": row.get("broker_ticket"),
                "intent": row.get("intent"),
                "reason": row.get("reason"),
                "source_reason": row.get("source_reason"),
            }
            for row in (handoff.get("blocked_actions") or [])
            if isinstance(row, Mapping)
        ],
        "attempted_action_count": len(execution_rows),
        "terminal_effect_count": sum(1 for row in execution_rows if str(row.get("status") or "") in TERMINAL_EFFECT_STATUSES),
        "suppressed_action_count": len(suppressed),
        "broker_touched": any(bool(row.get("broker_touched")) for row in execution_rows),
        "executions": execution_rows,
        "suppressed_actions": [dict(row) for row in suppressed],
        "operator_position_edge": dict(operator_review or {}),
        "operator_position_edge_status": (operator_review or {}).get("status"),
        "operator_position_edge_prompt_version": (operator_review or {}).get("prompt_version"),
        "operator_position_edge_provider": (operator_review or {}).get("provider"),
        "operator_position_edge_summary": (operator_review or {}).get("summary"),
        "operator_position_edge_selected_count": int(
            (operator_review or {}).get("selected_action_count") or 0
        ),
        "operator_position_edge_stand_down_count": int(
            (operator_review or {}).get("operator_stand_down_count") or 0
        ),
        "operator_position_edge_deferred_count": int(
            (operator_review or {}).get("operator_deferred_count") or 0
        ),
        "operator_position_edge_hard_policy_count": int(
            (operator_review or {}).get("hard_policy_selected_count") or 0
        ),
        "bridge_class": type(bridge).__name__ if bridge is not None else None,
        "bridge_connected": _safe_bool_call(bridge, "is_connected", default=False) if bridge is not None else False,
        "bridge_executes_real_orders": _safe_bool_call(bridge, "will_execute_real_order", default=False) if bridge is not None else False,
        "state_path": str(Path(state_path)),
        "per_action_owner_confirmation_required": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    # Watching can run every second. Persist only when an action was actually
    # attempted and the cooldown/effect ledger changed; idle telemetry already
    # lives in dispatch-loop memory and should not churn a OneDrive-backed file.
    persist_state = bool(execution_rows)
    payload["state_persisted"] = persist_state
    if persist_state:
        state["latest_cycle"] = payload
        _save_state(state_path, state)
    return payload


def _load_state(path: Path | str) -> dict[str, Any]:
    target = Path(path)
    with _state_lock:
        if not target.exists():
            return {}
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}


def _save_state(path: Path | str, state: Mapping[str, Any]) -> None:
    target = Path(path)
    with _state_lock:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(f"{target.suffix}.{os.getpid()}.{threading.get_ident()}.tmp")
        body = json.dumps(dict(state), indent=2, sort_keys=True, default=str)
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                tmp.write_text(body, encoding="utf-8")
                tmp.replace(target)
                return
            except OSError as exc:
                import time as _time

                last_error = exc
                _time.sleep(0.1 * (attempt + 1))
        if last_error is not None:
            raise last_error


def _prune_state(state: dict[str, Any], limit: int = 2000) -> None:
    for key in ("action_records", "completed_once"):
        records = state.get(key)
        if not isinstance(records, dict) or len(records) <= limit:
            continue
        ordered = sorted(
            records.items(),
            key=lambda item: str((item[1] or {}).get("attempted_at_iso") or ""),
            reverse=True,
        )
        state[key] = dict(ordered[:limit])


def _snapshot_id(generated: datetime, bridge: Any, positions: Sequence[Mapping[str, Any]]) -> str:
    body = {
        "generated": generated.isoformat(),
        "bridge": type(bridge).__name__,
        "tickets": [str(row.get("broker_ticket") or "") for row in positions],
    }
    return "broker-management:" + hashlib.sha256(
        json.dumps(body, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _parse_iso(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def _positive_int(*values: Any) -> int:
    for value in values:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return 1


def _safe_bool_call(obj: Any, method: str, *, default: bool) -> bool:
    fn = getattr(obj, method, None)
    if not callable(fn):
        return default
    try:
        return bool(fn())
    except Exception:
        return default
