"""Guarded AI Operator Edge/Hedge trade-management handoff.

AI Operator Edge/Hedge supervision explains what should be considered. This
module converts those recommendations into deterministic broker-action
drafts for the guarded management execution path. It does not call the broker
bridge or touch MT4/MT5 by itself; execution is handled downstream by
execution_guard.py and the configured broker bridge. Per-action owner
confirmation is not required inside armed delegated authority.
"""

from __future__ import annotations

from math import floor
from typing import Any, Mapping

from cas_forex.ai_hedge_supervision import build_ai_hedge_supervision_report
from cas_forex.operator_account_context import enrich_position_open_pnl


REPORT_KIND = "cas_forex_ai_hedge_management_handoff"
CLAIM_BOUNDARY = (
    "AI Operator Edge/Hedge management handoff translates supervision "
    "recommendations into broker-action drafts for guarded execution. The "
    "handoff does not call broker bridges by itself; autonomous execution may "
    "continue without per-action owner confirmation only through order_dispatch.py, "
    "execution_guard.py, fresh broker truth, owner-delegated authority, and the "
    "configured bridge."
)
ACTIONABLE_INTENTS = {
    "set_stop_loss",
    "set_take_profit",
    "modify_take_profit",
    "move_stop_to_breakeven",
    "trail_stop",
    "close_partial",
    "close_full",
    "reduce",
}
DEFAULT_MIN_LOT = 0.01
DEFAULT_LOT_STEP = 0.01
TRAIL_LOCK_FRACTION = 0.50


def build_ai_hedge_management_handoff(
    supervision_report: Mapping[str, Any] | None = None,
    *,
    movement_stream: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a dry-run broker-action handoff from AI Hedge recommendations."""

    supervision = dict(
        supervision_report
        if supervision_report is not None
        else build_ai_hedge_supervision_report(movement_stream)
    )
    positions = [
        dict(row) for row in (supervision.get("positions") or []) if isinstance(row, Mapping)
    ]
    recommendations = [
        dict(row)
        for row in (supervision.get("recommendations") or [])
        if isinstance(row, Mapping)
    ]
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for recommendation in recommendations:
        intent = str(recommendation.get("intent") or "")
        if intent == "stand_down" and str(recommendation.get("urgency") or "").upper() == "HIGH":
            position = _match_position(recommendation, positions)
            blocked.append(
                _blocked_action(
                    recommendation,
                    position,
                    *_stand_down_blocker(recommendation),
                )
            )
            continue
        if intent not in ACTIONABLE_INTENTS:
            skipped.append(_skipped_recommendation(recommendation))
            continue
        position = _match_position(recommendation, positions)
        if position is None:
            blocked.append(
                _blocked_action(
                    recommendation,
                    None,
                    "POSITION_NOT_FOUND",
                    "No movement-stream position matched this AI Hedge recommendation.",
                )
            )
            continue
        problem = _position_blocker(supervision, position, intent=intent)
        if problem is not None:
            blocked.append(_blocked_action(recommendation, position, problem[0], problem[1]))
            continue
        if intent == "set_stop_loss":
            result = _build_emergency_stop_action(recommendation, position)
        elif intent == "set_take_profit":
            result = _build_take_profit_action(
                recommendation,
                position,
                modifying=False,
            )
        elif intent == "modify_take_profit":
            result = _build_take_profit_action(
                recommendation,
                position,
                modifying=True,
            )
        elif intent == "move_stop_to_breakeven":
            result = _build_breakeven_action(recommendation, position)
        elif intent == "trail_stop":
            result = _build_trailing_stop_action(recommendation, position)
        elif intent in {"close_partial", "reduce"}:
            result = _build_partial_close_action(recommendation, position)
        elif intent == "close_full":
            result = _build_full_close_action(recommendation, position)
        else:
            result = (
                None,
                _blocked_action(
                    recommendation,
                    position,
                    "UNSUPPORTED_INTENT",
                    f"AI Hedge management handoff does not support intent {intent}.",
                ),
            )
        action, block = result
        if action is not None:
            actions.append(action)
        elif block is not None:
            blocked.append(block)

    status = _status(supervision, actions, blocked, skipped)
    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "supervision_status": supervision.get("status"),
        "movement_stream_id": supervision.get("movement_stream_id"),
        "movement_timestamp": supervision.get("movement_timestamp"),
        "price_source_status": supervision.get("price_source_status"),
        "price_source_label": supervision.get("price_source_label"),
        "static_simulation_active": bool(supervision.get("static_simulation_active")),
        "source_health": supervision.get("source_health") or {},
        "position_count": len(positions),
        "recommendation_count": len(recommendations),
        "actionable_recommendation_count": sum(
            1 for row in recommendations if row.get("intent") in ACTIONABLE_INTENTS
        ),
        "management_action_count": len(actions),
        "blocked_action_count": len(blocked),
        "skipped_recommendation_count": len(skipped),
        "ready_for_owner_review": False,
        "ready_for_guarded_execution": bool(actions),
        "dry_run_only": False,
        "broker_bound_action_authorized": False,
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "management_actions": actions,
        "blocked_actions": blocked,
        "skipped_recommendations": skipped[:8],
        "execution_required_path": [
            "AI Hedge management handoff",
            "fresh broker truth refresh",
            "order_dispatch.py management chokepoint",
            "execution_guard.py management review",
            "broker bridge modify_position or close_position",
            "terminal receipt and audit reconciliation",
        ],
        "next_action": _next_action(actions, blocked, skipped),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def build_ai_operator_discretionary_management_options(
    movement_stream: Mapping[str, Any],
    *,
    existing_actions: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Offer exact broker-valid management choices to the active Operator.

    The deterministic supervisor still supplies mandatory protection and urgent
    invalidation actions. This menu closes the autonomy gap between those fixed
    triggers: every fresh manageable position can be held or managed by the
    Operator using immutable drafts. These drafts are never policy fallbacks;
    they require an explicit Operator selection.
    """

    supervision = dict(build_ai_hedge_supervision_report(movement_stream))
    positions = [
        dict(row)
        for row in (supervision.get("positions") or [])
        if isinstance(row, Mapping)
    ]
    policy = (
        dict(supervision.get("management_policy") or {})
        if isinstance(supervision.get("management_policy"), Mapping)
        else {}
    )
    existing = {
        (str(row.get("broker_ticket") or ""), str(row.get("intent") or ""))
        for row in (existing_actions or [])
        if isinstance(row, Mapping)
    }
    recommendations: list[dict[str, Any]] = []

    for position in positions:
        enriched = enrich_position_open_pnl(position)
        ticket = str(enriched.get("broker_ticket") or "")
        symbol = str(enriched.get("symbol") or "UNKNOWN")
        position_id = str(enriched.get("row_id") or "")
        net_open = _float_or_none(
            enriched.get("net_open_pnl_after_reported_costs_usd")
        )
        is_net_winner = net_open is not None and net_open > 0.0
        evidence_refs = [
            (
                "movement_stream.position:"
                f"{enriched.get('row_id') or enriched.get('symbol') or 'unknown'}"
            ),
            "position.net_open_pnl_after_reported_costs_usd",
            "position.stop_loss",
            "position.take_profit",
        ]

        def add_option(
            intent: str,
            reason: str,
            *,
            parameters: Mapping[str, Any] | None = None,
        ) -> None:
            if (ticket, intent) in existing:
                return
            recommendations.append(
                {
                    "intent": intent,
                    "scope": "position",
                    "symbol": symbol,
                    "position_id": position_id,
                    "broker_ticket": enriched.get("broker_ticket"),
                    "urgency": "LOW",
                    "reason": reason,
                    "gate_path": (
                        "AI Operator discretionary review -> order_dispatch.py -> "
                        "execution_guard.py -> broker bridge"
                    ),
                    "evidence_refs": list(evidence_refs),
                    "parameters": dict(parameters or {}),
                    "broker_bound_action_authorized": False,
                    "orders_placed": False,
                }
            )

        add_option(
            "close_full",
            (
                f"Operator discretionary realization option: close the full position and "
                f"attempt to realize the currently reported net open P&L of ${net_open:.2f}."
                if is_net_winner
                else "Operator discretionary risk-reduction option: close the full position if current evidence invalidates the hold thesis."
            ),
            parameters={
                "close_basis": (
                    "REALIZATION_ONLY_NO_INVALIDATION_EVIDENCE"
                    if is_net_winner
                    else "RISK_REDUCTION_REQUIRES_THESIS_REVIEW"
                ),
                "thesis_invalidation_evidence_supplied": False,
            },
        )

        volume = _float_or_none(enriched.get("lot_size"))
        if volume is not None and volume >= (DEFAULT_MIN_LOT + DEFAULT_LOT_STEP):
            add_option(
                "close_partial" if is_net_winner else "reduce",
                (
                    "Operator discretionary profit-banking option: realize part of a net winner while retaining reduced exposure."
                    if is_net_winner
                    else "Operator discretionary exposure-reduction option: reduce a position whose current evidence no longer supports full size."
                ),
            )

        if is_net_winner and not _stop_at_or_beyond_breakeven(enriched):
            add_option(
                "move_stop_to_breakeven",
                "Operator discretionary principal-protection option for a position that is net winning after reported costs.",
            )

        if is_net_winner and _policy_bool(policy, "trailing_stop_enabled", True):
            trailing_fraction = min(
                0.9,
                _policy_float(
                    policy,
                    "trailing_lock_fraction",
                    TRAIL_LOCK_FRACTION,
                    minimum=0.1,
                ),
            )
            add_option(
                "trail_stop",
                "Operator discretionary profit-protection option: tighten the stop without crossing the fresh exit price.",
                parameters={"trailing_lock_fraction": trailing_fraction},
            )

    option_handoff = build_ai_hedge_management_handoff(
        {
            **supervision,
            "recommendations": recommendations,
        }
    )
    options = [
        {
            **dict(row),
            "operator_discretionary_option": True,
            "operator_selection_required": True,
            "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        }
        for row in (option_handoff.get("management_actions") or [])
        if isinstance(row, Mapping)
    ]
    return {
        "report_kind": "cas_forex_ai_operator_discretionary_management_options",
        "status": (
            "OPERATOR_DISCRETIONARY_OPTIONS_READY"
            if options
            else "NO_OPERATOR_DISCRETIONARY_OPTIONS"
        ),
        "position_count": len(positions),
        "recommendation_count": len(recommendations),
        "option_count": len(options),
        "option_position_count": len(
            {str(row.get("broker_ticket") or "") for row in options}
        ),
        "options": options,
        "blocked_option_count": int(option_handoff.get("blocked_action_count") or 0),
        "blocked_options": list(option_handoff.get("blocked_actions") or []),
        "operator_selection_required": True,
        "model_failure_policy": "STAND_DOWN",
        "claim_boundary": (
            "These are immutable broker-action choices for the active AI Operator. "
            "No option is selected by construction, no provider failure may select "
            "one, and every selected option still passes fresh broker truth, order "
            "dispatch, execution guard, terminal, idempotency, and receipt checks."
        ),
    }


def _match_position(
    recommendation: Mapping[str, Any],
    positions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    position_id = str(recommendation.get("position_id") or "")
    broker_ticket = str(recommendation.get("broker_ticket") or "")
    symbol = str(recommendation.get("symbol") or "")
    if broker_ticket:
        for position in positions:
            if str(position.get("broker_ticket") or "") == broker_ticket:
                return position
    if position_id:
        for position in positions:
            if position_id in {
                str(position.get("position_id") or ""),
                str(position.get("row_id") or ""),
            }:
                return position
    if symbol:
        for position in positions:
            if str(position.get("symbol") or "") == symbol:
                return position
    return None


def _position_blocker(
    supervision: Mapping[str, Any],
    position: Mapping[str, Any],
    *,
    intent: str,
) -> tuple[str, str] | None:
    if not _position_has_fresh_price(supervision, position):
        return (
            "STALE_OR_STATIC_PRICE_SOURCE",
            "Broker-management proposals require a fresh provider or MT5 price for this position.",
        )
    if _parse_ticket(position.get("broker_ticket")) is None:
        return (
            "MISSING_BROKER_TICKET",
            "A broker ticket is required before close/modify proposals can target an existing position.",
        )
    entry = _float_or_none(position.get("open_price"))
    if entry is None or entry <= 0:
        return ("MISSING_ENTRY_PRICE", "The position has no usable open price.")
    current = _float_or_none(position.get("current_price"))
    if current is None or current <= 0:
        return ("MISSING_CURRENT_PRICE", "The position has no usable current price.")
    side = str(position.get("side") or "").upper()
    if side not in {"LONG", "BUY", "SHORT", "SELL"}:
        return ("UNKNOWN_SIDE", "The position side is missing or unsupported.")
    stop = _float_or_none(position.get("stop_loss"))
    if intent != "set_stop_loss" and (stop is None or stop <= 0):
        return (
            "MISSING_STOP_LOSS",
            "A non-emergency management action requires an existing positive broker stop.",
        )
    return None


def _position_has_fresh_price(
    supervision: Mapping[str, Any],
    position: Mapping[str, Any],
) -> bool:
    if bool(position.get("price_stale")):
        return False
    source = str(position.get("price_source") or "").lower()
    label = str(position.get("position_source_label") or "").lower()
    if "static" in source or "static" in label:
        return False
    status = str(supervision.get("price_source_status") or "").upper()
    if status in {"PROVIDER_ACTIVE", "MIXED_PROVIDER_AND_STATIC_FALLBACK"}:
        return True
    source_health = (
        supervision.get("source_health")
        if isinstance(supervision.get("source_health"), Mapping)
        else {}
    )
    return bool(source_health.get("fresh_for_trade_management"))


def _build_emergency_stop_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    current = _float_or_none(position.get("current_price"))
    target = _recommendation_number(recommendation, "stop_loss")
    assert current is not None
    side = str(position.get("side") or "").upper()
    if target is None or target <= 0:
        return None, _blocked_action(
            recommendation,
            position,
            "INVALID_EMERGENCY_STOP_TARGET",
            "Emergency stop recommendation did not carry a positive stop target.",
        )
    if side in {"LONG", "BUY"} and target >= current:
        return None, _blocked_action(
            recommendation,
            position,
            "INVALID_EMERGENCY_STOP_GEOMETRY",
            "A long emergency stop must remain below the fresh exit price.",
        )
    if side in {"SHORT", "SELL"} and target <= current:
        return None, _blocked_action(
            recommendation,
            position,
            "INVALID_EMERGENCY_STOP_GEOMETRY",
            "A short emergency stop must remain above the fresh exit price.",
        )
    return _modify_action(
        recommendation,
        position,
        stop_loss=_round_like_position(target, position),
        risk_effect="emergency_protective_stop",
    ), None


def _build_take_profit_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
    *,
    modifying: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    target = _recommendation_number(recommendation, "take_profit")
    current = _float_or_none(position.get("current_price"))
    entry = _float_or_none(position.get("open_price"))
    stop = _float_or_none(position.get("stop_loss"))
    previous = _float_or_none(position.get("take_profit"))
    assert current is not None and entry is not None and stop is not None
    side = str(position.get("side") or "").upper()
    if target is None or target <= 0:
        return None, _blocked_action(
            recommendation,
            position,
            "INVALID_TAKE_PROFIT_TARGET",
            "Take-profit recommendation did not carry a positive target.",
        )
    if side in {"LONG", "BUY"}:
        valid_geometry = target > current and target > entry
        improves = previous is None or previous <= 0 or target > previous
        principal_protected = stop >= entry
    else:
        valid_geometry = target < current and target < entry
        improves = previous is None or previous <= 0 or target < previous
        principal_protected = stop <= entry
    if not valid_geometry:
        return None, _blocked_action(
            recommendation,
            position,
            "INVALID_TAKE_PROFIT_GEOMETRY",
            "Take-profit target must remain beyond the fresh exit price in the profitable direction.",
        )
    if modifying and (previous is None or previous <= 0):
        return None, _blocked_action(
            recommendation,
            position,
            "TAKE_PROFIT_NOT_PRESENT",
            "Explicit take-profit modification requires an existing broker target.",
        )
    if modifying and (not improves or not principal_protected):
        return None, _blocked_action(
            recommendation,
            position,
            "TAKE_PROFIT_EXTENSION_NOT_PROTECTED",
            "A target extension must improve reward while the stop already protects principal.",
        )
    if not modifying and previous is not None and previous > 0:
        return None, _blocked_action(
            recommendation,
            position,
            "TAKE_PROFIT_ALREADY_PRESENT",
            "Set-take-profit is only valid when no broker target is currently present.",
        )
    ticket = _parse_ticket(position.get("broker_ticket"))
    assert ticket is not None
    rounded_target = _round_like_position(target, position)
    risk_effect = (
        "profit_extension_after_principal_lock"
        if modifying
        else "bounded_profit_target"
    )
    return {
        **_base_action(recommendation, position),
        "broker_method": "modify_position",
        "broker_ticket": ticket,
        "volume": None,
        "stop_loss": stop,
        "take_profit": rounded_target,
        "risk_effect": risk_effect,
        "draft_call": {
            "method": "bridge.modify_position",
            "ticket": ticket,
            "stop_loss": stop,
            "take_profit": rounded_target,
        },
    }, None


def _build_breakeven_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    entry = _float_or_none(position.get("open_price"))
    current = _float_or_none(position.get("current_price"))
    stop = _float_or_none(position.get("stop_loss"))
    assert entry is not None and current is not None and stop is not None
    side = str(position.get("side") or "").upper()
    if side in {"LONG", "BUY"}:
        if current <= entry:
            return None, _blocked_action(
                recommendation,
                position,
                "NOT_IN_PROFIT",
                "A long stop cannot be moved to breakeven unless current price is above entry.",
            )
        if stop >= entry:
            return None, _blocked_action(
                recommendation,
                position,
                "STOP_ALREADY_PROTECTED",
                "The long stop is already at or beyond breakeven.",
            )
    else:
        if current >= entry:
            return None, _blocked_action(
                recommendation,
                position,
                "NOT_IN_PROFIT",
                "A short stop cannot be moved to breakeven unless current price is below entry.",
            )
        if stop <= entry:
            return None, _blocked_action(
                recommendation,
                position,
                "STOP_ALREADY_PROTECTED",
                "The short stop is already at or beyond breakeven.",
            )
    return _modify_action(
        recommendation,
        position,
        stop_loss=_round_like_position(entry, position),
        risk_effect="principal_lock",
    ), None


def _build_trailing_stop_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    entry = _float_or_none(position.get("open_price"))
    current = _float_or_none(position.get("current_price"))
    stop = _float_or_none(position.get("stop_loss"))
    assert entry is not None and current is not None and stop is not None
    lock_fraction = _recommendation_number(recommendation, "trailing_lock_fraction")
    if lock_fraction is None:
        lock_fraction = TRAIL_LOCK_FRACTION
    lock_fraction = min(0.9, max(0.1, float(lock_fraction)))
    side = str(position.get("side") or "").upper()
    if side in {"LONG", "BUY"}:
        favorable = current - entry
        candidate = entry + (favorable * lock_fraction)
        if favorable <= 0 or candidate <= stop or candidate >= current:
            return None, _blocked_action(
                recommendation,
                position,
                "TRAIL_WOULD_NOT_TIGHTEN",
                "The calculated long trailing stop would not tighten risk without crossing current price.",
            )
    else:
        favorable = entry - current
        candidate = entry - (favorable * lock_fraction)
        if favorable <= 0 or candidate >= stop or candidate <= current:
            return None, _blocked_action(
                recommendation,
                position,
                "TRAIL_WOULD_NOT_TIGHTEN",
                "The calculated short trailing stop would not tighten risk without crossing current price.",
            )
    return _modify_action(
        recommendation,
        position,
        stop_loss=_round_like_position(candidate, position),
        risk_effect="risk_reducing_trail",
    ), None


def _build_partial_close_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    lot_size = _float_or_none(position.get("lot_size"))
    if lot_size is None or lot_size <= 0:
        return None, _blocked_action(
            recommendation,
            position,
            "MISSING_VOLUME",
            "A close/reduce proposal requires a positive lot size.",
        )
    volume = _round_volume_down(lot_size / 2.0)
    if volume < DEFAULT_MIN_LOT or volume >= lot_size:
        return None, _blocked_action(
            recommendation,
            position,
            "VOLUME_TOO_SMALL_FOR_PARTIAL_CLOSE",
            "The position is too small for a safe partial close draft at the default 0.01 lot step.",
        )
    return _close_action(recommendation, position, volume=volume), None


def _build_full_close_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    lot_size = _float_or_none(position.get("lot_size"))
    if lot_size is None or lot_size <= 0:
        return None, _blocked_action(
            recommendation,
            position,
            "MISSING_VOLUME",
            "A full-close action requires a positive current position volume.",
        )
    return _close_action(
        recommendation,
        position,
        volume=None,
        full_close=True,
    ), None


def _modify_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
    *,
    stop_loss: float,
    risk_effect: str,
) -> dict[str, Any]:
    ticket = _parse_ticket(position.get("broker_ticket"))
    assert ticket is not None
    take_profit = _float_or_none(position.get("take_profit"))
    return {
        **_base_action(recommendation, position),
        "broker_method": "modify_position",
        "broker_ticket": ticket,
        "volume": None,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_effect": risk_effect,
        "draft_call": {
            "method": "bridge.modify_position",
            "ticket": ticket,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        },
    }


def _close_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
    *,
    volume: float | None,
    full_close: bool = False,
) -> dict[str, Any]:
    ticket = _parse_ticket(position.get("broker_ticket"))
    assert ticket is not None
    lot_size = _float_or_none(position.get("lot_size"))
    expected_remaining = 0.0 if full_close else None
    if not full_close and lot_size is not None and volume is not None:
        expected_remaining = max(0.0, round(float(lot_size) - float(volume), 2))
    return {
        **_base_action(recommendation, position),
        "broker_method": "close_position",
        "broker_ticket": ticket,
        "volume": volume,
        "original_volume": lot_size,
        "expected_remaining_volume": expected_remaining,
        "stop_loss": None,
        "take_profit": None,
        "risk_effect": (
            "exposure_reducing_full_close"
            if full_close
            else "exposure_reducing_partial_close"
        ),
        "draft_call": {
            "method": "bridge.close_position",
            "ticket": ticket,
            "volume": volume,
        },
    }


def _base_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any],
) -> dict[str, Any]:
    intent = str(recommendation.get("intent") or "unknown")
    position_id = str(position.get("position_id") or recommendation.get("position_id") or "")
    symbol = str(position.get("symbol") or recommendation.get("symbol") or "UNKNOWN")
    action_id = f"ai-hedge-management:{position_id or symbol}:{intent}"
    return {
        "action_id": action_id,
        "status": "READY_FOR_GUARDED_EXECUTION",
        "intent": intent,
        "symbol": symbol,
        "position_id": position_id or None,
        "side": position.get("side"),
        "open_price": _float_or_none(position.get("open_price")),
        "current_price": _float_or_none(position.get("current_price")),
        "previous_stop_loss": _float_or_none(position.get("stop_loss")),
        "original_stop_loss": _float_or_none(position.get("original_stop_loss")),
        "previous_take_profit": _float_or_none(position.get("take_profit")),
        "original_volume": _float_or_none(position.get("lot_size")),
        "r_multiple": position.get("r_multiple"),
        "r_multiple_basis": position.get("r_multiple_basis"),
        "floating_pnl_usd": _float_or_none(position.get("floating_pnl_usd")),
        "position_price_pnl_usd": _float_or_none(
            position.get("position_price_pnl_usd")
        ),
        "swap_usd": _float_or_none(position.get("swap_usd")),
        "commission_usd": _float_or_none(position.get("commission_usd")),
        "net_open_pnl_after_reported_costs_usd": _float_or_none(
            position.get("net_open_pnl_after_reported_costs_usd")
        ),
        "open_pnl_basis": position.get("open_pnl_basis"),
        "opened_at_iso": position.get("opened_at_iso"),
        "opened_at_source": position.get("opened_at_source"),
        "age_days": position.get("age_days"),
        "reason": recommendation.get("reason"),
        "urgency": recommendation.get("urgency"),
        "evidence_refs": list(recommendation.get("evidence_refs") or []),
        "decision_parameters": dict(recommendation.get("parameters") or {}),
        "requires_owner_confirmation": False,
        "requires_fresh_broker_truth": True,
        "requires_execution_guard": True,
        "dry_run_only": False,
        "broker_bound_action_authorized": False,
        "broker_touched": False,
        "orders_placed": False,
        "gate_path": (
            "AI Hedge management handoff -> fresh broker truth -> order_dispatch.py -> "
            "execution_guard.py management review -> broker bridge"
        ),
    }


def _blocked_action(
    recommendation: Mapping[str, Any],
    position: Mapping[str, Any] | None,
    code: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "block_code": code,
        "intent": recommendation.get("intent"),
        "symbol": (position or recommendation).get("symbol"),
        "position_id": (position or recommendation).get("position_id"),
        "broker_ticket": (position or {}).get("broker_ticket"),
        "reason": reason,
        "source_reason": recommendation.get("reason"),
        "gate_path": "AI Hedge management handoff -> fail closed",
        "broker_bound_action_authorized": False,
        "broker_touched": False,
        "orders_placed": False,
    }


def _stand_down_blocker(recommendation: Mapping[str, Any]) -> tuple[str, str]:
    reason = str(recommendation.get("reason") or "")
    low = reason.lower()
    if "static" in low or "stale" in low or "price" in low:
        return (
            "STALE_OR_STATIC_PRICE_SOURCE",
            "AI Operator Edge/Hedge stand-down is active because price source truth is not fresh enough for broker management.",
        )
    if "no stop" in low or "stop loss" in low:
        return (
            "MISSING_STOP_LOSS",
            "AI Operator Edge/Hedge stand-down is active because the position is not proven protected by stop-loss telemetry.",
        )
    return (
        "HIGH_URGENCY_STAND_DOWN",
        "AI Operator Edge/Hedge stand-down is active, so broker-management drafting is blocked.",
    )


def _skipped_recommendation(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intent": recommendation.get("intent"),
        "scope": recommendation.get("scope"),
        "symbol": recommendation.get("symbol"),
        "urgency": recommendation.get("urgency"),
        "reason": recommendation.get("reason"),
    }


def _status(
    supervision: Mapping[str, Any],
    actions: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> str:
    if str(supervision.get("status") or "").upper() == "WARMING":
        return "WARMING"
    if actions:
        return "READY_FOR_GUARDED_EXECUTION"
    if blocked:
        return "BLOCKED"
    if skipped:
        return "NO_ACTIONABLE_MANAGEMENT"
    return "WARMING"


def _next_action(
    actions: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> str:
    if actions:
        return (
            "Drafted management action is ready for guarded execution. Execution "
            "still needs fresh broker truth, execution-guard approval, owner-delegated "
            "authority, and a broker bridge call."
        )
    if blocked:
        return "Resolve the first blocked management handoff before any broker action can be drafted."
    if skipped:
        return "Keep watching; current AI Hedge recommendations do not require a broker-management action."
    return "Wait for AI Hedge supervision to refresh."


def _parse_ticket(value: Any) -> int | None:
    try:
        ticket = int(str(value))
    except (TypeError, ValueError):
        return None
    if ticket <= 0:
        return None
    return ticket


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stop_at_or_beyond_breakeven(position: Mapping[str, Any]) -> bool:
    entry = _float_or_none(position.get("open_price"))
    stop = _float_or_none(position.get("stop_loss"))
    if entry is None or stop is None:
        return False
    side = str(position.get("side") or "").upper()
    if side in {"LONG", "BUY"}:
        return stop >= entry
    if side in {"SHORT", "SELL"}:
        return stop <= entry
    return False


def _policy_bool(policy: Mapping[str, Any], key: str, default: bool) -> bool:
    raw = policy.get(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(int(raw))
    token = str(raw or "").strip().lower()
    if token in {"1", "true", "yes", "on", "enabled"}:
        return True
    if token in {"0", "false", "no", "off", "disabled"}:
        return False
    return bool(default)


def _policy_float(
    policy: Mapping[str, Any],
    key: str,
    default: float,
    *,
    minimum: float,
) -> float:
    try:
        value = float(policy.get(key, default))
    except (TypeError, ValueError):
        value = float(default)
    return max(float(minimum), value)


def _recommendation_number(recommendation: Mapping[str, Any], key: str) -> float | None:
    parameters = recommendation.get("parameters")
    if not isinstance(parameters, Mapping):
        return None
    return _float_or_none(parameters.get(key))


def _round_volume_down(value: float) -> float:
    units = floor((value + 1e-12) / DEFAULT_LOT_STEP)
    return round(units * DEFAULT_LOT_STEP, 2)


def _round_like_position(value: float, position: Mapping[str, Any]) -> float:
    decimals = 2
    for key in ("open_price", "current_price", "stop_loss", "take_profit"):
        raw = position.get(key)
        if raw in (None, ""):
            continue
        text = str(raw)
        if "." in text:
            decimals = max(decimals, min(5, len(text.split(".", 1)[1].rstrip("0"))))
    return round(float(value), decimals)
