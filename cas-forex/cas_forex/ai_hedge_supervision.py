"""Runtime AI Operator Edge/Hedge supervision report for CAS Forex.

This module is the auditable observation/recommendation stage of the AI Operator
Edge/Hedge runtime. The Operator is the adaptive trading edge engine;
hedge/protection is one of its jobs. Recommendations produced here are consumed
by the autonomous management cycle, which executes broker-bound actions through
execution_guard.py, fresh broker truth, risk gates, and owner controls.
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.movement_stream import build_movement_position_feed_truth
from cas_forex.operator_account_context import enrich_position_open_pnl
from cas_forex.spec_context import ai_hedge_intelligence_layer


REPORT_KIND = "cas_forex_ai_hedge_supervision"
DEFAULT_EMERGENCY_STOP_DISTANCE_PCT = 0.5
DEFAULT_EMERGENCY_STOP_MARKET_BUFFER_PCT = 0.05
DEFAULT_TAKE_PROFIT_REWARD_RISK = 2.0
DEFAULT_TAKE_PROFIT_EXTENSION_TRIGGER_FRACTION = 0.8
DEFAULT_TAKE_PROFIT_EXTENSION_FACTOR = 1.5
DEFAULT_TIME_STOP_HOURS = 72.0
CLAIM_BOUNDARY = (
    "AI Operator Edge/Hedge supervision is the observation and recommendation "
    "stage. Its governed intents feed the autonomous management executor; broker "
    "effects then pass through execution_guard.py, fresh broker truth, owner "
    "authority, terminal permissions, and durable receipts."
)


def build_ai_hedge_supervision_report(
    movement_stream: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a governed supervision report from the current movement stream."""

    movement = dict(movement_stream or _default_movement_stream())
    layer = ai_hedge_intelligence_layer()
    positions = [
        row for row in (movement.get("positions") or []) if isinstance(row, Mapping)
    ]
    static_symbols = [
        str(symbol) for symbol in (movement.get("static_fallback_symbols") or []) if symbol
    ]
    provider_symbols = [
        str(symbol) for symbol in (movement.get("provider_usable_symbols") or []) if symbol
    ]
    recommendations: list[dict[str, Any]] = []
    management_policy = _management_policy(movement)

    if static_symbols or movement.get("static_simulation_active"):
        recommendations.append(
            _recommendation(
                intent="stand_down",
                scope="market_data",
                symbol=",".join(static_symbols) or "UNKNOWN",
                urgency="HIGH",
                reason=(
                    "Static simulator fallback is active; trade management needs "
                    "fresh provider or MT5 prices before the AI Hedge layer can "
                    "supervise exits."
                ),
                gate_path="movement_stream -> price_source_truth -> no_broker_action",
                evidence_refs=["movement_stream.static_fallback_symbols"],
            )
        )

    for position in positions:
        recommendations.extend(
            _position_recommendations(position, policy=management_policy)
        )

    if not positions:
        recommendations.append(
            _recommendation(
                intent="skip",
                scope="account",
                symbol="ACCOUNT",
                urgency="LOW",
                reason="No open movement-stream positions are available for trade-management supervision.",
                gate_path="movement_stream -> no_open_positions",
                evidence_refs=["movement_stream.positions"],
            )
        )

    action_recommendations = [
        row for row in recommendations if row.get("intent") not in {"skip"}
    ]
    high_urgency = any(row.get("urgency") == "HIGH" for row in recommendations)
    status = (
        "ATTENTION"
        if high_urgency or static_symbols
        else "ACTIVE_RECOMMENDATIONS"
        if action_recommendations
        else "WATCHING"
    )
    position_feed_truth = _position_feed_truth(movement)
    source_health = _source_health(movement, position_feed_truth)
    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "layer_status": layer.get("status"),
        "thesis": layer.get("thesis"),
        "movement_stream_id": movement.get("stream_id"),
        "movement_timestamp": movement.get("timestamp"),
        "price_source_status": movement.get("price_source_status"),
        "price_source_label": movement.get("price_source_label"),
        "price_source_summary": movement.get("price_source_summary"),
        "price_source_warning": movement.get("price_source_warning"),
        "position_feed_label": position_feed_truth.get("position_feed_label"),
        "position_feed_detail": position_feed_truth.get("position_feed_detail"),
        "static_simulation_active": bool(movement.get("static_simulation_active")),
        "provider_usable_symbols": sorted(provider_symbols),
        "static_fallback_symbols": sorted(static_symbols),
        "position_count": len(positions),
        "recommendation_count": len(recommendations),
        "action_recommendation_count": len(action_recommendations),
        "high_urgency_count": sum(1 for row in recommendations if row.get("urgency") == "HIGH"),
        "source_health": source_health,
        "management_policy": management_policy,
        "positions": [
            _position_summary(row, policy=management_policy) for row in positions
        ],
        "recommendations": recommendations,
        "allowed_trade_intents": layer.get("allowed_trade_intents", []),
        "hard_boundaries": layer.get("hard_boundaries", []),
        "broker_bound_action_authorized": False,
        "orders_placed": False,
        "money_moved": False,
        "execution_required_path": [
            "order_dispatch.py",
            "execution_guard.py",
            "edge PASS",
            "broker truth",
            "risk gates",
            "mode separation",
            "owner controls",
        ],
        "next_action": _next_action(status, recommendations),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _default_movement_stream() -> Mapping[str, Any]:
    try:
        from api.data import movement_stream

        return movement_stream(use_provider_quotes=True)
    except Exception as exc:
        return {
            "report_kind": "cas_forex_movement_stream",
            "stream_id": "UNAVAILABLE",
            "timestamp": "",
            "positions": [],
            "price_source_status": "UNAVAILABLE",
            "price_source_label": "UNAVAILABLE",
            "price_source_summary": f"Movement stream unavailable: {type(exc).__name__}: {exc}",
            "position_feed_label": "NONE",
            "position_feed_detail": (
                "No broker or paper/demo movement snapshot is available because the "
                f"movement stream failed: {type(exc).__name__}: {exc}"
            ),
            "static_simulation_active": False,
            "provider_usable_symbols": [],
            "static_fallback_symbols": [],
        }


def _position_recommendations(
    position: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    position = enrich_position_open_pnl(position)
    symbol = str(position.get("symbol") or "UNKNOWN")
    resolved_policy = dict(policy or {})
    if bool(position.get("price_stale")):
        return [
            _recommendation(
                intent="stand_down",
                scope="position",
                symbol=symbol,
                urgency="HIGH",
                reason=(
                    str(position.get("stale_reason") or "")
                    or "Position has stale/static price source."
                ),
                gate_path="movement_stream -> stale_price_block -> no_broker_action",
                evidence_refs=[_position_ref(position), "position.price_stale"],
                position_id=str(position.get("row_id") or ""),
            )
        ]

    if _nonpositive_or_missing(position.get("stop_loss")):
        target = _emergency_stop_target(position, resolved_policy)
        if target is not None:
            return [
                _recommendation(
                    intent="set_stop_loss",
                    scope="position",
                    symbol=symbol,
                    urgency="HIGH",
                    reason=(
                        "Position has no broker stop; autonomously install a "
                        f"protective stop at {target} through the guarded management path."
                    ),
                    gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py -> broker bridge",
                    evidence_refs=[_position_ref(position), "position.stop_loss"],
                    position_id=str(position.get("row_id") or ""),
                    parameters={"stop_loss": target},
                )
            ]
        return [
            _recommendation(
                intent="stand_down",
                scope="position",
                symbol=symbol,
                urgency="HIGH",
                reason=(
                    "Position has no stop loss and its side/entry/current geometry "
                    "is insufficient to calculate a valid emergency protective stop."
                ),
                gate_path="position_protection -> invalid_geometry_block",
                evidence_refs=[_position_ref(position), "position.stop_loss"],
                position_id=str(position.get("row_id") or ""),
            )
        ]

    recs: list[dict[str, Any]] = []
    trailing_enabled = bool(resolved_policy.get("trailing_stop_enabled", True))
    trailing_fraction = _policy_float(
        resolved_policy,
        "trailing_lock_fraction",
        0.5,
        minimum=0.1,
    )
    time_stop_hours = _policy_float(
        resolved_policy,
        "time_stop_hours",
        DEFAULT_TIME_STOP_HOURS,
        minimum=0.0,
    )
    age_hours = _position_age_hours(position)
    if (
        time_stop_hours > 0
        and age_hours is not None
        and age_hours >= time_stop_hours
        and _position_not_profitable(position)
    ):
        return [
            _recommendation(
                intent="close_full",
                scope="position",
                symbol=symbol,
                urgency="HIGH",
                reason=(
                    f"Position is {age_hours:.1f} hours old, is not profitable, and "
                    f"exceeded the owner policy time stop of {time_stop_hours:.1f} hours."
                ),
                gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py -> broker close_position",
                evidence_refs=[_position_ref(position), "position.age_days", "management_policy.time_stop_hours"],
                position_id=str(position.get("row_id") or ""),
            )
        ]

    if _nonpositive_or_missing(position.get("take_profit")):
        target = _initial_take_profit_target(position, resolved_policy)
        if target is not None:
            recs.append(
                _recommendation(
                    intent="set_take_profit",
                    scope="position",
                    symbol=symbol,
                    urgency="MEDIUM",
                    reason=(
                        "Position has no broker take-profit; install the owner-policy "
                        f"profit target at {target}."
                    ),
                    gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py -> broker bridge",
                    evidence_refs=[_position_ref(position), "position.take_profit"],
                    position_id=str(position.get("row_id") or ""),
                    parameters={"take_profit": target},
                )
            )
    else:
        extension = _take_profit_extension_target(position, resolved_policy)
        if extension is not None:
            recs.append(
                _recommendation(
                    intent="modify_take_profit",
                    scope="position",
                    symbol=symbol,
                    urgency="LOW",
                    reason=(
                        "Position is principal-protected and near its current target; "
                        f"extend take-profit to {extension} under the owner policy."
                    ),
                    gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py -> broker bridge",
                    evidence_refs=[_position_ref(position), "position.take_profit", "position.stop_loss"],
                    position_id=str(position.get("row_id") or ""),
                    parameters={"take_profit": extension},
                )
            )

    r_multiple = _r_multiple(position, policy=resolved_policy)
    if r_multiple is None:
        if recs:
            return recs
        recs.append(
            _recommendation(
                intent="skip",
                scope="position",
                symbol=symbol,
                urgency="LOW",
                reason="Cannot compute R-multiple from entry/current/stop values.",
                gate_path="movement_stream -> insufficient_position_math",
                evidence_refs=[_position_ref(position)],
                position_id=str(position.get("row_id") or ""),
            )
        )
        return recs

    if r_multiple <= -1.0:
        return [
            _recommendation(
                intent="close_full",
                scope="position",
                symbol=symbol,
                urgency="HIGH",
                reason=(
                    f"Position is down {abs(r_multiple):.2f}R at the fresh exit price; "
                    "the original risk thesis is invalidated and remaining exposure should be closed."
                ),
                gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py -> broker close_position",
                evidence_refs=[_position_ref(position), "position.r_multiple"],
                position_id=str(position.get("row_id") or ""),
            )
        ]

    if r_multiple >= 2.0:
        recs.append(
            _recommendation(
                intent="close_partial",
                scope="position",
                symbol=symbol,
                urgency="MEDIUM",
                reason=f"Position is up {r_multiple:.2f}R; bank partial profit and protect the remainder if dispatch gates allow.",
                gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py",
                evidence_refs=[_position_ref(position), "position.r_multiple"],
                position_id=str(position.get("row_id") or ""),
            )
        )
        if trailing_enabled:
            recs.append(
                _recommendation(
                    intent="trail_stop",
                    scope="position",
                    symbol=symbol,
                    urgency="MEDIUM",
                    reason=(
                        f"Position is up {r_multiple:.2f}R; the enabled trailing policy "
                        f"may lock {trailing_fraction:.0%} of favorable movement through "
                        "the protected dispatch path."
                    ),
                    gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py",
                    evidence_refs=[
                        _position_ref(position),
                        "position.r_multiple",
                        "management_policy.trailing_stop_enabled",
                        "management_policy.trailing_lock_fraction",
                    ],
                    position_id=str(position.get("row_id") or ""),
                    parameters={"trailing_lock_fraction": trailing_fraction},
                )
            )
    elif r_multiple >= 1.0:
        if not _stop_at_or_beyond_breakeven(position):
            recs.append(
                _recommendation(
                    intent="move_stop_to_breakeven",
                    scope="position",
                    symbol=symbol,
                    urgency="MEDIUM",
                    reason=f"Position is up {r_multiple:.2f}R and stop is not at breakeven.",
                    gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py",
                    evidence_refs=[_position_ref(position), "position.r_multiple"],
                    position_id=str(position.get("row_id") or ""),
                )
            )
        else:
            if trailing_enabled:
                recs.append(
                    _recommendation(
                        intent="trail_stop",
                        scope="position",
                        symbol=symbol,
                        urgency="LOW",
                        reason=(
                            f"Position is up {r_multiple:.2f}R and already principal-protected; "
                            f"the enabled trailing policy may lock {trailing_fraction:.0%} of "
                            "favorable movement."
                        ),
                        gate_path="AI Hedge -> order_dispatch.py -> execution_guard.py",
                        evidence_refs=[
                            _position_ref(position),
                            "position.r_multiple",
                            "management_policy.trailing_stop_enabled",
                            "management_policy.trailing_lock_fraction",
                        ],
                        position_id=str(position.get("row_id") or ""),
                        parameters={"trailing_lock_fraction": trailing_fraction},
                    )
                )
            else:
                recs.append(
                    _recommendation(
                        intent="skip",
                        scope="position",
                        symbol=symbol,
                        urgency="LOW",
                        reason=(
                            f"Position is up {r_multiple:.2f}R and principal-protected, "
                            "but the owner-fenced trailing-stop dial is disabled."
                        ),
                        gate_path="AI control authority -> trailing_stop_enabled=0 -> watch",
                        evidence_refs=[
                            _position_ref(position),
                            "management_policy.trailing_stop_enabled",
                        ],
                        position_id=str(position.get("row_id") or ""),
                    )
                )
    elif r_multiple <= -0.75:
        recs.append(
            _recommendation(
                intent="reduce",
                scope="position",
                symbol=symbol,
                urgency="MEDIUM",
                reason=f"Position is down {abs(r_multiple):.2f}R; review reduction only through risk and execution gates.",
                gate_path="AI Hedge -> risk gates -> order_dispatch.py -> execution_guard.py",
                evidence_refs=[_position_ref(position), "position.r_multiple"],
                position_id=str(position.get("row_id") or ""),
            )
        )
    else:
        recs.append(
            _recommendation(
                intent="skip",
                scope="position",
                symbol=symbol,
                urgency="LOW",
                reason=f"Position is {r_multiple:.2f}R; no management change is justified by the runtime supervisor.",
                gate_path="movement_stream -> watch",
                evidence_refs=[_position_ref(position), "position.r_multiple"],
                position_id=str(position.get("row_id") or ""),
            )
        )
    return recs


def _recommendation(
    *,
    intent: str,
    scope: str,
    symbol: str,
    urgency: str,
    reason: str,
    gate_path: str,
    evidence_refs: list[str],
    position_id: str | None = None,
    parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "scope": scope,
        "symbol": symbol,
        "position_id": position_id,
        "urgency": urgency,
        "reason": reason,
        "gate_path": gate_path,
        "evidence_refs": evidence_refs,
        "parameters": dict(parameters or {}),
        "broker_bound_action_authorized": False,
        "orders_placed": False,
    }


def _position_summary(
    position: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    position = enrich_position_open_pnl(position)
    r_multiple, r_multiple_basis = _r_multiple_evidence(position, policy=policy)
    return {
        "position_id": position.get("row_id"),
        "symbol": position.get("symbol"),
        "side": position.get("side"),
        "lot_size": position.get("lot_size"),
        "open_price": position.get("open_price"),
        "current_price": position.get("current_price"),
        "stop_loss": position.get("stop_loss"),
        "original_stop_loss": position.get("original_stop_loss"),
        "take_profit": position.get("take_profit"),
        "floating_pnl_usd": position.get("floating_pnl_usd"),
        "floating_pnl_units": position.get("floating_pnl_units"),
        "position_price_pnl_usd": position.get("position_price_pnl_usd"),
        "swap_usd": position.get("swap_usd"),
        "commission_usd": position.get("commission_usd"),
        "net_open_pnl_after_reported_costs_usd": position.get(
            "net_open_pnl_after_reported_costs_usd"
        ),
        "open_pnl_basis": position.get("open_pnl_basis"),
        "r_multiple": round(r_multiple, 4) if r_multiple is not None else None,
        "r_multiple_basis": r_multiple_basis,
        "price_source": position.get("price_source"),
        "price_stale": bool(position.get("price_stale")),
        "stale_reason": position.get("stale_reason"),
        "position_source_label": position.get("position_source_label"),
        "age_days": position.get("age_days"),
        "opened_at_iso": position.get("opened_at_iso"),
        "opened_at_source": position.get("opened_at_source"),
        "broker_ticket": position.get("broker_ticket"),
    }


def _r_multiple(
    position: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
) -> float | None:
    return _r_multiple_evidence(position, policy=policy)[0]


def _r_multiple_evidence(
    position: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
) -> tuple[float | None, str]:
    try:
        entry = float(position.get("open_price"))
        current = float(position.get("current_price"))
        stop = float(position.get("stop_loss"))
    except (TypeError, ValueError):
        return None, "UNAVAILABLE_MISSING_ENTRY_CURRENT_OR_STOP"
    side = str(position.get("side") or "").upper()
    original_stop = _positive_float(position.get("original_stop_loss"))
    original_stop_is_adverse = bool(
        original_stop is not None
        and (
            (side in {"LONG", "BUY"} and original_stop < entry)
            or (side in {"SHORT", "SELL"} and original_stop > entry)
        )
    )
    if original_stop_is_adverse and original_stop is not None:
        risk = abs(entry - original_stop)
        risk_basis = "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT"
    else:
        risk = abs(entry - stop)
        risk_basis = "CURRENT_PROTECTIVE_STOP"
    stop_is_principal_protected = (
        (side in {"LONG", "BUY"} and stop >= entry)
        or (side in {"SHORT", "SELL"} and stop <= entry)
    )
    if stop_is_principal_protected and not original_stop_is_adverse:
        take_profit = _positive_float(position.get("take_profit"))
        favorable_target = bool(
            take_profit is not None
            and (
                (side in {"LONG", "BUY"} and take_profit > entry)
                or (side in {"SHORT", "SELL"} and take_profit < entry)
            )
        )
        if favorable_target and take_profit is not None:
            reward_risk = _policy_float(
                policy or {},
                "take_profit_reward_risk",
                DEFAULT_TAKE_PROFIT_REWARD_RISK,
                minimum=0.1,
            )
            risk = abs(take_profit - entry) / reward_risk
            risk_basis = "TAKE_PROFIT_POLICY_INFERENCE"
    if risk <= 0:
        return None, "UNAVAILABLE_NONPOSITIVE_RISK_DISTANCE"
    if side in {"LONG", "BUY"}:
        favorable = current - entry
    elif side in {"SHORT", "SELL"}:
        favorable = entry - current
    else:
        return None, "UNAVAILABLE_UNKNOWN_SIDE"
    return favorable / risk, risk_basis


def _management_policy(movement: Mapping[str, Any]) -> dict[str, Any]:
    supplied = movement.get("management_policy")
    policy = supplied if isinstance(supplied, Mapping) else {}
    return {
        "emergency_stop_distance_pct": _policy_float(
            policy,
            "emergency_stop_distance_pct",
            DEFAULT_EMERGENCY_STOP_DISTANCE_PCT,
            minimum=0.0001,
        ),
        "emergency_stop_market_buffer_pct": _policy_float(
            policy,
            "emergency_stop_market_buffer_pct",
            DEFAULT_EMERGENCY_STOP_MARKET_BUFFER_PCT,
            minimum=0.0001,
        ),
        "take_profit_reward_risk": _policy_float(
            policy,
            "take_profit_reward_risk",
            DEFAULT_TAKE_PROFIT_REWARD_RISK,
            minimum=0.1,
        ),
        "take_profit_extension_trigger_fraction": min(
            0.99,
            _policy_float(
                policy,
                "take_profit_extension_trigger_fraction",
                DEFAULT_TAKE_PROFIT_EXTENSION_TRIGGER_FRACTION,
                minimum=0.1,
            ),
        ),
        "take_profit_extension_factor": _policy_float(
            policy,
            "take_profit_extension_factor",
            DEFAULT_TAKE_PROFIT_EXTENSION_FACTOR,
            minimum=1.01,
        ),
        "time_stop_hours": _policy_float(
            policy,
            "time_stop_hours",
            DEFAULT_TIME_STOP_HOURS,
            minimum=0.0,
        ),
        "trailing_stop_enabled": _policy_bool(
            policy,
            "trailing_stop_enabled",
            True,
        ),
        "trailing_lock_fraction": min(
            0.9,
            _policy_float(
                policy,
                "trailing_lock_fraction",
                0.5,
                minimum=0.1,
            ),
        ),
    }


def _emergency_stop_target(
    position: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> float | None:
    entry = _positive_float(position.get("open_price"))
    current = _positive_float(position.get("current_price"))
    if entry is None or current is None:
        return None
    side = str(position.get("side") or "").upper()
    if side not in {"LONG", "BUY", "SHORT", "SELL"}:
        return None
    reward_risk = _policy_float(
        policy, "take_profit_reward_risk", DEFAULT_TAKE_PROFIT_REWARD_RISK, minimum=0.1
    )
    take_profit = _positive_float(position.get("take_profit"))
    favorable_tp = bool(
        take_profit is not None
        and ((side in {"LONG", "BUY"} and take_profit > entry) or (side in {"SHORT", "SELL"} and take_profit < entry))
    )
    if favorable_tp and take_profit is not None:
        risk_distance = abs(take_profit - entry) / reward_risk
    else:
        risk_distance = entry * _policy_float(
            policy,
            "emergency_stop_distance_pct",
            DEFAULT_EMERGENCY_STOP_DISTANCE_PCT,
            minimum=0.0001,
        ) / 100.0
    market_buffer = current * _policy_float(
        policy,
        "emergency_stop_market_buffer_pct",
        DEFAULT_EMERGENCY_STOP_MARKET_BUFFER_PCT,
        minimum=0.0001,
    ) / 100.0
    if risk_distance <= 0 or market_buffer <= 0:
        return None
    if side in {"LONG", "BUY"}:
        target = min(entry - risk_distance, current - market_buffer)
        if target <= 0 or target >= current:
            return None
    else:
        target = max(entry + risk_distance, current + market_buffer)
        if target <= current:
            return None
    return _round_like_position(target, position)


def _initial_take_profit_target(
    position: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> float | None:
    entry = _positive_float(position.get("open_price"))
    current = _positive_float(position.get("current_price"))
    stop = _positive_float(position.get("stop_loss"))
    if entry is None or current is None or stop is None:
        return None
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    side = str(position.get("side") or "").upper()
    reward_risk = _policy_float(
        policy, "take_profit_reward_risk", DEFAULT_TAKE_PROFIT_REWARD_RISK, minimum=0.1
    )
    buffer = current * _policy_float(
        policy,
        "emergency_stop_market_buffer_pct",
        DEFAULT_EMERGENCY_STOP_MARKET_BUFFER_PCT,
        minimum=0.0001,
    ) / 100.0
    if side in {"LONG", "BUY"}:
        target = max(entry + (risk * reward_risk), current + buffer)
    elif side in {"SHORT", "SELL"}:
        target = min(entry - (risk * reward_risk), current - buffer)
        if target <= 0:
            return None
    else:
        return None
    return _round_like_position(target, position)


def _take_profit_extension_target(
    position: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> float | None:
    if not _stop_at_or_beyond_breakeven(position):
        return None
    entry = _positive_float(position.get("open_price"))
    current = _positive_float(position.get("current_price"))
    take_profit = _positive_float(position.get("take_profit"))
    if entry is None or current is None or take_profit is None:
        return None
    side = str(position.get("side") or "").upper()
    if side in {"LONG", "BUY"}:
        distance = take_profit - entry
        progress = current - entry
    elif side in {"SHORT", "SELL"}:
        distance = entry - take_profit
        progress = entry - current
    else:
        return None
    if distance <= 0 or progress <= 0 or progress >= distance:
        return None
    trigger = _policy_float(
        policy,
        "take_profit_extension_trigger_fraction",
        DEFAULT_TAKE_PROFIT_EXTENSION_TRIGGER_FRACTION,
        minimum=0.1,
    )
    if progress / distance < min(trigger, 0.99):
        return None
    factor = _policy_float(
        policy,
        "take_profit_extension_factor",
        DEFAULT_TAKE_PROFIT_EXTENSION_FACTOR,
        minimum=1.01,
    )
    target = entry + (distance * factor) if side in {"LONG", "BUY"} else entry - (distance * factor)
    if target <= 0:
        return None
    return _round_like_position(target, position)


def _position_age_hours(position: Mapping[str, Any]) -> float | None:
    try:
        age_days = float(position.get("age_days"))
    except (TypeError, ValueError):
        return None
    return max(0.0, age_days * 24.0)


def _position_not_profitable(position: Mapping[str, Any]) -> bool:
    enriched = enrich_position_open_pnl(position)
    try:
        net_open_pnl = float(
            enriched.get("net_open_pnl_after_reported_costs_usd")
        )
    except (TypeError, ValueError):
        net_open_pnl = None
    if net_open_pnl is not None:
        return net_open_pnl <= 0.0
    entry = _positive_float(position.get("open_price"))
    current = _positive_float(position.get("current_price"))
    if entry is None or current is None:
        return False
    side = str(position.get("side") or "").upper()
    if side in {"LONG", "BUY"}:
        return current <= entry
    if side in {"SHORT", "SELL"}:
        return current >= entry
    return False


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


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


def _policy_bool(
    policy: Mapping[str, Any],
    key: str,
    default: bool,
) -> bool:
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


def _nonpositive_or_missing(value: Any) -> bool:
    try:
        return float(value) <= 0
    except (TypeError, ValueError):
        return True


def _stop_at_or_beyond_breakeven(position: Mapping[str, Any]) -> bool:
    try:
        entry = float(position.get("open_price"))
        stop = float(position.get("stop_loss"))
    except (TypeError, ValueError):
        return False
    side = str(position.get("side") or "").upper()
    if side in {"LONG", "BUY"}:
        return stop >= entry
    if side in {"SHORT", "SELL"}:
        return stop <= entry
    return False


def _position_feed_truth(movement: Mapping[str, Any]) -> dict[str, str | None]:
    position_feed_label = str(movement.get("position_feed_label") or "").strip() or None
    position_feed_detail = str(movement.get("position_feed_detail") or "").strip() or None
    if not (position_feed_label and position_feed_detail):
        derived = build_movement_position_feed_truth(
            positions=list(movement.get("positions") or []),
            quotes=list(movement.get("quotes") or []),
            price_source_status=str(movement.get("price_source_status") or "UNKNOWN"),
            market_data_provider_requested=bool(movement.get("market_data_provider_requested")),
            configured_market_data_provider=str(
                movement.get("configured_market_data_provider")
                or movement.get("market_data_provider")
                or movement.get("price_source_label")
                or ""
            ),
            provider_usable_symbols=movement.get("provider_usable_symbols"),
            static_fallback_symbols=movement.get("static_fallback_symbols"),
            mt5_fallback_symbols=movement.get("mt5_fallback_symbols"),
            provider_stale_symbols=movement.get("provider_stale_symbols"),
            provider_freshness_max_age_seconds=movement.get("provider_freshness_max_age_seconds"),
        )
        position_feed_label = position_feed_label or str(derived.get("position_feed_label") or "").strip() or None
        position_feed_detail = position_feed_detail or str(derived.get("position_feed_detail") or "").strip() or None
    return {
        "position_feed_label": position_feed_label,
        "position_feed_detail": position_feed_detail,
    }


def _source_health(
    movement: Mapping[str, Any],
    position_feed_truth: Mapping[str, Any],
) -> dict[str, Any]:
    status = str(movement.get("price_source_status") or "UNKNOWN")
    position_feed_detail = str(position_feed_truth.get("position_feed_detail") or "").strip() or None
    return {
        "price_source_status": status,
        "fresh_for_trade_management": status in {"PROVIDER_ACTIVE", "MIXED_PROVIDER_AND_STATIC_FALLBACK"}
        and not bool(movement.get("static_simulation_active")),
        "static_simulation_active": bool(movement.get("static_simulation_active")),
        "provider_usable_symbol_count": len(movement.get("provider_usable_symbols") or []),
        "static_fallback_symbol_count": len(movement.get("static_fallback_symbols") or []),
        "position_feed_label": position_feed_truth.get("position_feed_label"),
        "position_feed_detail": position_feed_detail,
        "detail": position_feed_detail,
        "summary": movement.get("price_source_summary"),
        "warning": movement.get("price_source_warning"),
    }


def _position_ref(position: Mapping[str, Any]) -> str:
    return f"movement_stream.position:{position.get('row_id') or position.get('symbol') or 'unknown'}"


def _next_action(status: str, recommendations: list[dict[str, Any]]) -> str:
    if status == "ATTENTION":
        return "Resolve high-urgency supervision blockers before treating AI Hedge trade-management recommendations as actionable."
    for row in recommendations:
        if row.get("intent") not in {"skip"}:
            return "Review the top AI Hedge recommendation, then route any broker-bound action through the protected dispatch path."
    return "Keep watching; no AI Hedge management action is justified by current movement telemetry."
