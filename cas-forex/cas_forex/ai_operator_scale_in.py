"""Autonomous AI Operator scale-ins for already-winning broker positions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from cas_forex.instruments import canonical_or_normalized_symbol

from cas_forex.operator_sizing import build_operator_sizing_plan
from cas_forex.operator_account_context import (
    enrich_position_open_pnl,
    position_is_net_winning_after_reported_costs,
)
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "ai-operator-scale-in-execution-audit.jsonl"
REPORT_KIND = "cas_forex_ai_operator_scale_in"
CLAIM_BOUNDARY = (
    "The scale-in lane creates exact broker-grid add choices only for a fresh, "
    "protected parent position that is net winning after reported carry and costs. "
    "The AI Operator selects one "
    "choice and a short-lived one-shot authorization is consumed through "
    "order_dispatch.py and execution_guard.py. No per-add human confirmation is "
    "required inside the owner envelope; final risk, margin, broker-truth, live, "
    "kill-switch, idempotency, and receipt checks remain authoritative."
)


def build_winning_scale_in_actions(
    position_snapshot: Mapping[str, Any],
    *,
    bridge: Any,
    config: Any = None,
    completed_units_by_parent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one exact add action per available size choice for each winner."""

    enabled = bool(getattr(config, "ai_scale_in_enabled", True))
    maximum_units = _effective_compound_unit_cap(config)
    minimum_r = _config_float(config, "ai_scale_in_min_profit_r", 0.5, minimum=0.0)
    completed = dict(completed_units_by_parent or {})
    actions: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    if not enabled or maximum_units <= 0:
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "status": "SCALE_IN_DISABLED",
            "actions": [],
            "action_count": 0,
            "blockers": [],
            "max_compound_units": maximum_units,
            "claim_boundary": CLAIM_BOUNDARY,
        }

    for position in position_snapshot.get("positions") or []:
        if not isinstance(position, Mapping):
            continue
        parent = enrich_position_open_pnl(position)
        ticket = str(parent.get("broker_ticket") or "").strip()
        symbol = str(parent.get("symbol") or "").strip()
        side = _direction(parent.get("side"))
        r_multiple, r_multiple_basis = _position_r_multiple_evidence(parent)
        reason = _scale_in_block_reason(parent, minimum_r=minimum_r)
        current_units = _int(completed.get(ticket), 0)
        if current_units >= maximum_units:
            reason = f"compound-unit cap reached ({current_units} / {maximum_units})"
        if reason:
            distance_to_threshold = max(0.0, minimum_r - r_multiple)
            blockers.append(
                {
                    "parent_broker_ticket": ticket or None,
                    "symbol": symbol,
                    "reason": reason,
                    "reason_code": _scale_in_block_code(reason),
                    "current_r": round(r_multiple, 4),
                    "minimum_profit_r": minimum_r,
                    "distance_to_threshold_r": round(distance_to_threshold, 4),
                    "r_multiple_basis": r_multiple_basis,
                    "net_open_pnl_after_reported_costs_usd": _number(
                        parent.get("net_open_pnl_after_reported_costs_usd")
                    ),
                    "original_stop_loss": _number(parent.get("original_stop_loss")),
                    "current_stop_loss": _number(parent.get("stop_loss")),
                }
            )
            continue

        current = _number(parent.get("current_price"))
        stop = _number(parent.get("stop_loss"))
        target = _number(parent.get("take_profit"))
        seed = _broker_min_lot(bridge, symbol)
        proposed = {
            "symbol": symbol,
            "direction": side,
            "entry_price": current,
            "stop_loss": stop,
            "take_profit": target,
            "lots": seed,
            "ai_action": "AI_OPERATOR_SCALE_IN",
            "is_compound_add": True,
            "parent_broker_ticket": ticket,
        }
        plan = build_operator_sizing_plan(
            symbol=symbol,
            direction=side,
            entry_price=current,
            stop_loss=stop,
            take_profit=target,
            seed_lots=seed,
            bridge=bridge,
            config=config,
            proposed_intent=proposed,
            account_snapshot=position_snapshot.get("account_risk_snapshot"),
            purpose="SCALE_IN",
            parent_position=parent,
            compound_slot_allowance=maximum_units,
        )
        if not plan.get("options"):
            blockers.append(
                {
                    "parent_broker_ticket": ticket,
                    "symbol": symbol,
                    "reason": "; ".join(plan.get("blockers") or ["no compliant add size"]),
                    "sizing_plan_hash": plan.get("plan_hash"),
                }
            )
            continue

        unit_index = current_units + 1
        quote_key = str(parent.get("quote_timestamp") or position_snapshot.get("timestamp") or "")
        for option in plan.get("options") or []:
            if not isinstance(option, Mapping):
                continue
            sizing_ref = str(option.get("sizing_ref") or "")
            lots = float(option.get("lots") or 0.0)
            identity = _hash(
                {
                    "ticket": ticket,
                    "unit_index": unit_index,
                    "sizing_ref": sizing_ref,
                    "quote_key": quote_key,
                    "current": current,
                    "stop": stop,
                    "target": target,
                }
            )[:18]
            decision_ref = f"ai-scale-in:{ticket}:{unit_index}:{identity}"
            order = BrokerOrderRequest(
                order_id=f"scale-{ticket}-{unit_index}-{identity}",
                decision_ref=decision_ref,
                symbol=symbol,
                order_type=OrderType.MARKET,
                direction=Direction.LONG if side == "LONG" else Direction.SHORT,
                volume=lots,
                price=0.0,
                stop_loss=float(stop),
                take_profit=float(target),
                comment=f"CAS_SCALE:{ticket}"[:31],
                magic_number=20260711,
            )
            actions.append(
                {
                    "action_id": f"ai-scale-in:{ticket}:{unit_index}:{sizing_ref}",
                    "intent": "scale_in",
                    "broker_method": "execute_order",
                    "broker_ticket": ticket,
                    "position_id": parent.get("row_id") or f"broker:{ticket}",
                    "symbol": symbol,
                    "side": side,
                    "urgency": "MEDIUM",
                    "reason": (
                        f"Parent is net winning after reported costs at {r_multiple:.2f}R with fresh protected "
                        f"geometry; Operator may add {lots:g} lots using {option.get('label')}."
                    ),
                    "risk_effect": "bounded_winner_scale_in",
                    "r_multiple": r_multiple,
                    "r_multiple_basis": r_multiple_basis,
                    "minimum_profit_r": minimum_r,
                    "distance_to_threshold_r": 0.0,
                    "floating_pnl_usd": _number(parent.get("floating_pnl_usd")),
                    "position_price_pnl_usd": _number(
                        parent.get("position_price_pnl_usd")
                    ),
                    "swap_usd": _number(parent.get("swap_usd")),
                    "commission_usd": _number(parent.get("commission_usd")),
                    "net_open_pnl_after_reported_costs_usd": _number(
                        parent.get("net_open_pnl_after_reported_costs_usd")
                    ),
                    "open_pnl_basis": parent.get("open_pnl_basis"),
                    "open_price": _number(parent.get("open_price")),
                    "current_price": current,
                    "previous_stop_loss": stop,
                    "stop_loss": stop,
                    "previous_take_profit": target,
                    "take_profit": target,
                    "original_volume": _number(parent.get("lot_size")),
                    "volume": lots,
                    "expected_remaining_volume": _number(parent.get("lot_size")),
                    "scale_in_unit_index": unit_index,
                    "max_compound_units": maximum_units,
                    "compound_slot_allowance": maximum_units,
                    "compound_slot_policy": {
                        "base_max_positions_per_symbol": plan.get("cap_snapshot", {}).get(
                            "max_positions_per_symbol"
                        ),
                        "authorized_compound_slot_allowance": maximum_units,
                        "effective_max_positions_per_symbol": plan.get(
                            "effective_max_positions_per_symbol"
                        ),
                        "ordinary_entry_cap_unchanged": True,
                    },
                    "parent_broker_ticket": ticket,
                    "parent_position": parent,
                    "sizing_ref": sizing_ref,
                    "sizing_label": option.get("label"),
                    "sizing_plan_hash": plan.get("plan_hash"),
                    "risk_at_stop_usd": option.get("risk_at_stop_usd"),
                    "risk_at_stop_pct_equity": option.get("risk_at_stop_pct_equity"),
                    "estimated_margin_required_usd": option.get(
                        "estimated_margin_required_usd"
                    ),
                    "order_request": order.model_dump(mode="json"),
                    "quote_timestamp": quote_key,
                    "operator_authorization_required": True,
                    "per_action_owner_confirmation_required": False,
                    "evidence_refs": [
                        f"broker-position:{ticket}",
                        f"sizing-plan:{plan.get('plan_hash')}",
                    ],
                }
            )

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": "SCALE_IN_OPTIONS_READY" if actions else "NO_SCALE_IN_CANDIDATE",
        "action_count": len(actions),
        "parent_candidate_count": len({row["parent_broker_ticket"] for row in actions}),
        "actions": actions,
        "blockers": blockers,
        "threshold_waiting_parent_count": sum(
            1
            for row in blockers
            if row.get("reason_code") == "BELOW_SCALE_IN_THRESHOLD"
        ),
        "max_compound_units": maximum_units,
        "minimum_profit_r": minimum_r,
        "per_action_owner_confirmation_required": False,
        "daily_profit_target_used_for_sizing": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run_operator_scale_in_action(
    action: Mapping[str, Any],
    *,
    operator_event_hash: str,
    bridge: Any,
    config: Any = None,
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
) -> dict[str, Any]:
    """Authorize and dispatch one exact Operator-selected add order."""

    from cas_forex import operator_scale_in_authorization
    from cas_forex.order_dispatch import dispatch_order

    generated_at = utc_now().isoformat()
    base = {
        "report_kind": "cas_forex_ai_operator_scale_in_execution",
        "generated_at": generated_at,
        "action_id": action.get("action_id"),
        "parent_broker_ticket": action.get("parent_broker_ticket"),
        "sizing_ref": action.get("sizing_ref"),
        "sizing_plan_hash": action.get("sizing_plan_hash"),
        "operator_event_hash": operator_event_hash,
        "operator_decision_provenance": {
            key: action.get(key)
            for key in (
                "operator_action_ref",
                "operator_prompt_version",
                "operator_decision_prompt_hash",
                "operator_system_prompt_hash",
                "operator_provider",
                "operator_provider_label",
                "operator_model_ref",
                "operator_model_backend",
                "operator_decision_context_hash",
                "operator_candidate_snapshot_hash",
                "operator_candidate_hash",
                "operator_action_set_hash",
                "operator_decision",
                "operator_conviction",
                "operator_reason",
                "operator_growth_case",
            )
            if action.get(key) is not None
        },
        "per_action_owner_confirmation_required": False,
        "compound_slot_policy": dict(action.get("compound_slot_policy") or {}),
        "broker_touched": False,
        "orders_placed": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    try:
        order = BrokerOrderRequest(**dict(action.get("order_request") or {}))
        parent = _current_parent(bridge, str(action.get("parent_broker_ticket") or ""))
        if parent is None:
            raise PermissionError("scale-in parent position is no longer open")
        if not _position_is_winning(parent):
            raise PermissionError(
                "scale-in parent position is no longer net winning after reported carry and costs"
            )
        before_volume = _symbol_side_volume(bridge, order.symbol, _direction(order.direction))
        authorization = operator_scale_in_authorization.authorize(
            order,
            parent_position=parent,
            operator_event_hash=str(operator_event_hash or ""),
            sizing_plan_hash=str(action.get("sizing_plan_hash") or ""),
            sizing_ref=str(action.get("sizing_ref") or ""),
            bridge=bridge,
            config=config,
        )
        proposed = {
            "symbol": order.symbol,
            "direction": _direction(order.direction),
            "lots": float(order.volume),
            "entry_price": _number(action.get("current_price")),
            "stop_loss": float(order.stop_loss),
            "take_profit": float(order.take_profit),
            "strategy_id": "ai-operator-winning-scale-in",
            "ai_action": "AI_OPERATOR_SCALE_IN",
            "is_compound_add": True,
            "parent_broker_ticket": str(action.get("parent_broker_ticket") or ""),
            "scale_in_unit_index": action.get("scale_in_unit_index"),
            "compound_slot_allowance": action.get("compound_slot_allowance"),
            "operator_event_hash": str(operator_event_hash or ""),
            "sizing_plan_hash": str(action.get("sizing_plan_hash") or ""),
            "sizing_ref": str(action.get("sizing_ref") or ""),
            "estimated_margin_required_usd": action.get("estimated_margin_required_usd"),
            "risk_at_stop_usd": action.get("risk_at_stop_usd"),
            "risk_at_stop_pct_equity": action.get("risk_at_stop_pct_equity"),
        }
        proposed.update(
            {
                key: action.get(key)
                for key in (
                    "operator_action_ref",
                    "operator_prompt_version",
                    "operator_decision_prompt_hash",
                    "operator_system_prompt_hash",
                    "operator_provider",
                    "operator_provider_label",
                    "operator_model_ref",
                    "operator_model_backend",
                    "operator_decision_context_hash",
                    "operator_candidate_snapshot_hash",
                    "operator_candidate_hash",
                    "operator_action_set_hash",
                    "operator_decision",
                    "operator_conviction",
                    "operator_reason",
                    "operator_growth_case",
                    "growth_evidence_state",
                )
                if action.get(key) is not None
            }
        )
        result = dispatch_order(
            order,
            bridge,
            proposed_intent=proposed,
            strategy_id="ai-operator-winning-scale-in",
            ai_action="AI_OPERATOR_SCALE_IN",
            config=config,
            audit_source="ai_operator_scale_in",
        )
        after_volume = _symbol_side_volume(bridge, order.symbol, _direction(order.direction))
        receipt = {
            "status": (
                "RECONCILED"
                if result.executed and after_volume + 1e-9 >= before_volume + float(order.volume)
                else "NOT_RECONCILED" if result.executed else "NOT_REQUESTED"
            ),
            "symbol": order.symbol,
            "side": _direction(order.direction),
            "before_volume": before_volume,
            "expected_after_volume": round(before_volume + float(order.volume), 8),
            "actual_after_volume": after_volume,
        }
        if result.executed and receipt["status"] == "RECONCILED":
            status = "EXECUTED_RECONCILED"
        elif result.executed:
            status = "EXECUTED_NOT_RECONCILED"
        else:
            status = str(result.status or "BLOCKED")
        payload = {
            **base,
            "status": status,
            "broker_touched": bool(result.dispatched_to_bridge),
            "orders_placed": bool(result.executed),
            "authorization": authorization,
            "dispatch_result": result.to_dict(),
            "terminal_receipt": receipt,
            "terminal_receipt_status": receipt["status"],
        }
    except Exception as exc:
        payload = {
            **base,
            "status": "SCALE_IN_BLOCKED",
            "error_type": type(exc).__name__,
            "detail": str(exc),
            "terminal_receipt_status": "NOT_REQUESTED",
        }
    payload["audit_id"] = "scale-in-" + _hash(payload)[:24]
    _append_audit(payload, audit_path)
    return payload


def _scale_in_block_reason(position: Mapping[str, Any], *, minimum_r: float) -> str | None:
    if not str(position.get("broker_ticket") or "").strip():
        return "broker ticket is missing"
    if bool(position.get("price_stale")):
        return str(position.get("stale_reason") or "current quote is stale")
    if not _position_is_winning(position):
        return "parent position is not net winning after reported carry and costs"
    r_multiple, r_basis = _position_r_multiple_evidence(position)
    if r_basis == "UNAVAILABLE_NO_ORIGINAL_OR_ADVERSE_STOP":
        return "original entry-risk geometry is unavailable after the stop protected principal"
    if r_multiple + 1e-9 < minimum_r:
        return f"winner has not reached the {minimum_r:.2f}R scale-in threshold"
    side = _direction(position.get("side"))
    current = _number(position.get("current_price"))
    stop = _number(position.get("stop_loss"))
    target = _number(position.get("take_profit"))
    if None in (current, stop, target):
        return "fresh current price, stop loss, and take profit are required"
    if side == "LONG" and not (float(stop) < float(current) < float(target)):
        return "LONG add geometry requires stop < current < take profit"
    if side == "SHORT" and not (float(target) < float(current) < float(stop)):
        return "SHORT add geometry requires take profit < current < stop"
    return None


def _position_r_multiple(position: Mapping[str, Any]) -> float:
    return _position_r_multiple_evidence(position)[0]


def _position_r_multiple_evidence(position: Mapping[str, Any]) -> tuple[float, str]:
    side = _direction(position.get("side"))
    opened = _number(position.get("open_price"))
    current = _number(position.get("current_price"))
    if None in (opened, current):
        return 0.0, "UNAVAILABLE_MISSING_ENTRY_OR_CURRENT"
    favorable = float(current) - float(opened) if side == "LONG" else float(opened) - float(current)
    if favorable <= 0:
        return 0.0, "NOT_FAVORABLE"
    original_stop = _number(position.get("original_stop_loss"))
    current_stop = _number(position.get("stop_loss"))
    if original_stop is not None and (
        (side == "LONG" and float(original_stop) < float(opened))
        or (side == "SHORT" and float(original_stop) > float(opened))
    ):
        risk_distance = abs(float(opened) - float(original_stop))
        basis = "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT"
    elif current_stop is not None and (
        (side == "LONG" and float(current_stop) < float(opened))
        or (side == "SHORT" and float(current_stop) > float(opened))
    ):
        risk_distance = abs(float(opened) - float(current_stop))
        basis = "CURRENT_ADVERSE_STOP_FALLBACK"
    else:
        return 0.0, "UNAVAILABLE_NO_ORIGINAL_OR_ADVERSE_STOP"
    return round(favorable / max(risk_distance, 1e-12), 4), basis


def _scale_in_block_code(reason: Any) -> str:
    text = str(reason or "").lower()
    if "has not reached" in text and "scale-in threshold" in text:
        return "BELOW_SCALE_IN_THRESHOLD"
    if "entry-risk geometry" in text:
        return "ORIGINAL_RISK_GEOMETRY_UNAVAILABLE"
    if "not net winning" in text:
        return "NOT_NET_WINNING_AFTER_COSTS"
    if "compound-unit cap" in text:
        return "COMPOUND_UNIT_CAP_REACHED"
    if "quote is stale" in text or "current quote" in text:
        return "STALE_QUOTE"
    if "geometry" in text:
        return "INVALID_ADD_GEOMETRY"
    return "OTHER_SCALE_IN_BLOCKER"


def _current_parent(bridge: Any, ticket: str) -> dict[str, Any] | None:
    for row in _positions(bridge):
        current = str(row.get("broker_ticket") or row.get("ticket") or row.get("position") or "")
        if current == str(ticket):
            return row
    return None


def _position_is_winning(position: Mapping[str, Any]) -> bool:
    return position_is_net_winning_after_reported_costs(position)


def _symbol_side_volume(bridge: Any, symbol: str, side: str) -> float:
    total = 0.0
    target = _symbol_key(symbol)
    for row in _positions(bridge):
        if _symbol_key(row.get("symbol")) != target:
            continue
        if _direction(row.get("side") or row.get("direction") or row.get("type")) != side:
            continue
        total += _number(row.get("volume") or row.get("lots") or row.get("lot_size")) or 0.0
    return round(total, 8)


def _positions(bridge: Any) -> list[dict[str, Any]]:
    for name in ("get_open_positions_all", "get_open_positions"):
        getter = getattr(bridge, name, None)
        if not callable(getter):
            continue
        try:
            return [_mapping(row) for row in list(getter() or [])]
        except Exception:
            continue
    return []


def _broker_min_lot(bridge: Any, symbol: str) -> float:
    getter = getattr(bridge, "symbol_info", None)
    if callable(getter):
        try:
            info = getter(symbol)
            value = info.get("volume_min") if isinstance(info, Mapping) else getattr(info, "volume_min", None)
            parsed = _number(value)
            if parsed is not None and parsed > 0:
                return parsed
        except Exception:
            pass
    return 0.01


def _control_int(key: str, *, default: int) -> int:
    try:
        from cas_forex.ai_control_authority import get_authority

        return max(0, int(get_authority().control.get(key)))
    except Exception:
        return int(default)


def _effective_compound_unit_cap(config: Any) -> int:
    """Use the strictest compound cap shared by planning and final dispatch."""

    authority_cap = _control_int("max_compound_units", default=4)
    try:
        from cas_forex.execution_guard import caps_from_config

        dispatch_cap = max(0, int(caps_from_config(config).max_compound_units or 0))
    except Exception:
        dispatch_cap = authority_cap
    return min(authority_cap, dispatch_cap)


def _config_float(config: Any, key: str, default: float, *, minimum: float) -> float:
    try:
        value = float(getattr(config, key, default))
    except (TypeError, ValueError):
        value = float(default)
    return max(minimum, value)


def _direction(value: Any) -> str:
    raw = getattr(value, "value", value)
    text = str(raw or "").strip().upper()
    if text in {"BUY", "LONG", "0"}:
        return "LONG"
    if text in {"SELL", "SHORT", "1"}:
        return "SHORT"
    return text


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {
        key: getattr(value, key)
        for key in (
            "broker_ticket",
            "ticket",
            "position",
            "symbol",
            "side",
            "direction",
            "type",
            "volume",
            "lots",
            "lot_size",
            "open_price",
            "price_open",
            "current_price",
            "price_current",
            "stop_loss",
            "sl",
            "take_profit",
            "tp",
            "floating_pnl_usd",
            "profit",
            "position_price_pnl_usd",
            "swap_usd",
            "swap",
            "commission_usd",
            "commission",
            "net_open_pnl_after_reported_costs_usd",
            "comment",
        )
        if hasattr(value, key)
    }


def _symbol_key(value: Any) -> str:
    return canonical_or_normalized_symbol(value)


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _append_audit(payload: Mapping[str, Any], path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True, default=str) + "\n")


__all__ = [
    "CLAIM_BOUNDARY",
    "build_winning_scale_in_actions",
    "run_operator_scale_in_action",
]
