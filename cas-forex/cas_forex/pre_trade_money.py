"""Owner-facing pre-trade money impact estimates.

The broker remains the source of truth for final margin, commission, spread,
swap, and fill price. This module gives CAS-side estimates before an order is
allowed to touch a bridge so the owner can inspect the approximate money impact
of the proposed exposure.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from cas_forex.instruments import (
    canonical_symbol,
    get_instrument,
    pip_value_per_lot,
    price_unit_size,
    resolve_broker_symbol,
    usd_notional,
)
from cas_forex.schemas.forecast import Direction


def _finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _positive_float(value: Any) -> float | None:
    out = _finite_float(value)
    return out if out is not None and out > 0 else None


def _nonnegative_float(value: Any) -> float | None:
    out = _finite_float(value)
    return out if out is not None and out >= 0 else None


def _account_value(account_snapshot: Mapping[str, Any] | None, *keys: str) -> float | None:
    if not isinstance(account_snapshot, Mapping):
        return None
    for key in keys:
        value = _finite_float(account_snapshot.get(key))
        if value is not None:
            return value
    return None


def _bridge_account_snapshot(bridge: Any) -> tuple[dict[str, Any], str | None]:
    """Read the freshest account values exposed by a broker bridge.

    MT5's bridge returns a mapping while broker-like test adapters sometimes
    expose the underlying ``account_info`` object directly. Zeroed snapshots
    are treated as unavailable because MT5 uses them when it is disconnected.
    """

    if bridge is None:
        return {}, None
    probe = getattr(bridge, "get_account_info", None)
    if callable(probe):
        try:
            info = probe() or {}
        except Exception:
            info = {}
        if isinstance(info, Mapping):
            equity = _positive_float(
                info.get("equity")
                if info.get("equity") is not None
                else info.get("equity_usd")
            )
            balance = _positive_float(
                info.get("balance")
                if info.get("balance") is not None
                else info.get("balance_usd")
            )
            if equity is not None or balance is not None:
                return dict(info), "bridge.get_account_info"

    api, available = _bridge_symbol_api(bridge)
    account_probe = getattr(api, "account_info", None) if available else None
    if not callable(account_probe):
        return {}, None
    try:
        info = account_probe()
    except Exception:
        info = None
    if info is None:
        return {}, None
    values = {
        "balance": getattr(info, "balance", None),
        "equity": getattr(info, "equity", None),
        "margin": getattr(info, "margin", None),
        "margin_free": getattr(info, "margin_free", None),
        "leverage": getattr(info, "leverage", None),
    }
    if _positive_float(values.get("equity")) is None and _positive_float(values.get("balance")) is None:
        return {}, None
    return values, "broker.account_info"


def _resolved_account_snapshot(
    account_snapshot: Mapping[str, Any] | None,
    bridge: Any,
) -> tuple[dict[str, Any], str | None]:
    """Fill from bridge truth while preserving an explicit caller snapshot."""

    caller_snapshot = dict(account_snapshot) if isinstance(account_snapshot, Mapping) else {}
    caller_equity = _positive_float(
        caller_snapshot.get("equity")
        if caller_snapshot.get("equity") is not None
        else caller_snapshot.get("equity_usd")
    )
    caller_balance = _positive_float(
        caller_snapshot.get("balance")
        if caller_snapshot.get("balance") is not None
        else caller_snapshot.get("balance_usd")
    )
    caller_leverage = _positive_float(
        caller_snapshot.get("leverage")
        if caller_snapshot.get("leverage") is not None
        else caller_snapshot.get("account_leverage")
    )
    caller_margin = _nonnegative_float(
        caller_snapshot.get("margin")
        if caller_snapshot.get("margin") is not None
        else caller_snapshot.get("margin_used_usd")
    )
    caller_free_margin = _nonnegative_float(
        caller_snapshot.get("margin_free")
        if caller_snapshot.get("margin_free") is not None
        else caller_snapshot.get("free_margin_usd")
    )
    if (
        (caller_equity is not None or caller_balance is not None)
        and caller_leverage is not None
        and caller_margin is not None
        and caller_free_margin is not None
    ):
        return caller_snapshot, "caller_snapshot"

    bridge_snapshot, bridge_source = _bridge_account_snapshot(bridge)
    resolved = dict(bridge_snapshot)
    if caller_snapshot:
        resolved.update(caller_snapshot)
    if bridge_source and caller_snapshot:
        return resolved, f"{bridge_source}+caller_snapshot"
    if bridge_source:
        return resolved, bridge_source
    if resolved:
        return resolved, "caller_snapshot"
    return resolved, None


def _entry_price(
    *,
    order_price: Any,
    proposed_intent: Mapping[str, Any] | None,
) -> tuple[float | None, str]:
    price = _positive_float(order_price)
    if price is not None:
        return price, "order.price"
    intent = proposed_intent if isinstance(proposed_intent, Mapping) else {}
    for key in ("entry_price", "entry", "current_price", "mid", "market_price", "price"):
        value = _positive_float(intent.get(key))
        if value is not None:
            return value, f"proposed_intent.{key}"
    return None, "unavailable_for_market_order"


def _direction_value(direction: Any) -> str:
    if isinstance(direction, Direction):
        return direction.value
    return str(direction or "").strip().upper()


def _order_type_value(value: Any, proposed_intent: Mapping[str, Any] | None) -> str:
    if value is not None:
        token = str(getattr(value, "value", value) or "").strip().upper()
        if token:
            return token
    if isinstance(proposed_intent, Mapping):
        token = str(proposed_intent.get("order_type") or "").strip().upper()
        if token:
            return token
    return "MARKET"


def _distance_units(symbol: str, left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    unit = price_unit_size(symbol)
    if unit <= 0:
        return None
    return abs(float(left) - float(right)) / unit


def _rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def _bridge_symbol_api(bridge: Any) -> tuple[Any, bool]:
    if bridge is None:
        return None, False
    mt5 = getattr(bridge, "_mt5", None)
    if mt5 is not None and callable(getattr(mt5, "symbol_info", None)):
        return mt5, True
    if callable(getattr(bridge, "symbol_info", None)):
        return bridge, True
    connect = getattr(bridge, "connect", None)
    if callable(connect):
        try:
            connect()
        except Exception:
            pass
    mt5 = getattr(bridge, "_mt5", None)
    if mt5 is not None and callable(getattr(mt5, "symbol_info", None)):
        return mt5, True
    if callable(getattr(bridge, "symbol_info", None)):
        return bridge, True
    return None, False


def _safe_symbol_info(api: Any, symbol: str | None) -> Any:
    if api is None or not symbol:
        return None
    try:
        return api.symbol_info(symbol)
    except Exception:
        return None


def _safe_symbol_tick(api: Any, symbol: str | None) -> Any:
    if api is None or not symbol:
        return None
    probe = getattr(api, "symbol_info_tick", None)
    if not callable(probe):
        return None
    try:
        return probe(symbol)
    except Exception:
        return None


def _contract_constraints(info: Any, *, canonical_symbol_value: str) -> dict[str, Any]:
    if info is None:
        return {}
    point = _positive_float(getattr(info, "point", None))
    unit = price_unit_size(canonical_symbol_value)
    if unit <= 0:
        unit = 0.0001
    stop_level_points = _positive_float(getattr(info, "trade_stops_level", None)) or 0.0
    freeze_level_points = _positive_float(getattr(info, "trade_freeze_level", None)) or 0.0
    min_stop_distance = None
    if point is not None:
        min_stop_distance = max(stop_level_points, freeze_level_points) * point / unit
    return {
        "min_lot": _positive_float(getattr(info, "volume_min", None)),
        "max_lot": _positive_float(getattr(info, "volume_max", None)),
        "lot_step": _positive_float(getattr(info, "volume_step", None)),
        "contract_size": _positive_float(getattr(info, "trade_contract_size", None)),
        "tick_size": _positive_float(getattr(info, "trade_tick_size", None)),
        "tick_value": _positive_float(getattr(info, "trade_tick_value", None)),
        "tick_value_loss": _positive_float(getattr(info, "trade_tick_value_loss", None)),
        "tick_value_profit": _positive_float(getattr(info, "trade_tick_value_profit", None)),
        "point": point,
        "digits": _finite_float(getattr(info, "digits", None)),
        "min_stop_distance_pips": min_stop_distance,
    }


def _broker_unit_values_per_lot(
    constraints: Mapping[str, Any],
    *,
    price_unit: float,
) -> tuple[float | None, float | None, str | None]:
    """Convert broker tick economics into CAS price-unit values.

    MT5 tick values are account-currency P/L for one ``trade_tick_size`` move
    at one lot. CAS index distances are measured in full index points, so a
    0.01 tick worth $1 becomes $100 per full point per lot.
    """

    tick_size = _positive_float(constraints.get("tick_size"))
    if tick_size is None or price_unit <= 0:
        return None, None, None
    generic = _positive_float(constraints.get("tick_value"))
    loss = _positive_float(constraints.get("tick_value_loss"))
    profit = _positive_float(constraints.get("tick_value_profit"))
    risk_ticks = [value for value in (generic, loss, profit) if value is not None]
    if not risk_ticks:
        return None, None, None
    multiplier = float(price_unit) / tick_size
    risk_value = max(risk_ticks) * multiplier
    reward_tick = profit or generic or loss
    reward_value = reward_tick * multiplier if reward_tick is not None else risk_value
    return risk_value, reward_value, "broker.trade_tick_value/trade_tick_size"


def _account_leverage(
    *,
    account_snapshot: Mapping[str, Any] | None,
    bridge: Any = None,
    api: Any = None,
) -> tuple[float | None, str | None]:
    leverage = _account_value(account_snapshot, "leverage", "account_leverage")
    if leverage is not None:
        return leverage, "account_snapshot.leverage"
    if bridge is not None:
        probe = getattr(bridge, "get_account_info", None)
        if callable(probe):
            try:
                info = probe() or {}
            except Exception:
                info = {}
            if isinstance(info, Mapping):
                leverage = _finite_float(info.get("leverage"))
                if leverage is not None:
                    return leverage, "bridge.get_account_info.leverage"
    if api is not None:
        probe = getattr(api, "account_info", None)
        if callable(probe):
            try:
                info = probe()
            except Exception:
                info = None
            leverage = _finite_float(getattr(info, "leverage", None))
            if leverage is not None:
                return leverage, "broker.account_info.leverage"
    return None, None


def _mt5_order_type(api: Any, *, direction: str, order_type: str) -> Any:
    direction_token = direction.strip().upper()
    order_type_token = order_type.strip().upper()
    token = {
        ("LONG", "MARKET"): "BUY",
        ("BUY", "MARKET"): "BUY",
        ("SHORT", "MARKET"): "SELL",
        ("SELL", "MARKET"): "SELL",
        ("LONG", "LIMIT"): "BUY_LIMIT",
        ("BUY", "LIMIT"): "BUY_LIMIT",
        ("SHORT", "LIMIT"): "SELL_LIMIT",
        ("SELL", "LIMIT"): "SELL_LIMIT",
        ("LONG", "STOP"): "BUY_STOP",
        ("BUY", "STOP"): "BUY_STOP",
        ("SHORT", "STOP"): "SELL_STOP",
        ("SELL", "STOP"): "SELL_STOP",
    }.get((direction_token, order_type_token))
    if token is None:
        return None
    attr = {
        ("LONG", "MARKET"): "ORDER_TYPE_BUY",
        ("BUY", "MARKET"): "ORDER_TYPE_BUY",
        ("SHORT", "MARKET"): "ORDER_TYPE_SELL",
        ("SELL", "MARKET"): "ORDER_TYPE_SELL",
        ("LONG", "LIMIT"): "ORDER_TYPE_BUY_LIMIT",
        ("BUY", "LIMIT"): "ORDER_TYPE_BUY_LIMIT",
        ("SHORT", "LIMIT"): "ORDER_TYPE_SELL_LIMIT",
        ("SELL", "LIMIT"): "ORDER_TYPE_SELL_LIMIT",
        ("LONG", "STOP"): "ORDER_TYPE_BUY_STOP",
        ("BUY", "STOP"): "ORDER_TYPE_BUY_STOP",
        ("SHORT", "STOP"): "ORDER_TYPE_SELL_STOP",
        ("SELL", "STOP"): "ORDER_TYPE_SELL_STOP",
    }.get((direction_token, order_type_token))
    if attr:
        value = getattr(api, attr, None)
        if value is not None:
            return value
    return token


def _broker_margin_context(
    *,
    canonical: str,
    direction: str,
    order_type: str,
    volume: float | None,
    entry: float | None,
    bridge: Any = None,
    account_snapshot: Mapping[str, Any] | None = None,
    config: Any = None,
) -> dict[str, Any]:
    context = {
        "selected_broker_symbol": None,
        "broker_symbol_resolution": None,
        "broker_contract_constraints": {},
        "entry_price": entry,
        "entry_price_source": None,
        "account_leverage": None,
        "account_leverage_source": None,
        "estimated_notional_usd": None,
        "estimated_margin_required_usd": None,
        "margin_source": None,
        "broker_contract_source": "CAS instrument defaults unless broker metadata overrides are added upstream.",
    }
    api, available = _bridge_symbol_api(bridge)
    if not available or api is None:
        return context

    overrides = getattr(config, "mt5_symbol_overrides", "") if config is not None else ""
    resolution = resolve_broker_symbol(canonical, broker=api, overrides=overrides, select=True)
    context["broker_symbol_resolution"] = resolution.as_dict()
    context["selected_broker_symbol"] = resolution.selected_symbol
    if resolution.status != "RESOLVED" or not resolution.selected_symbol:
        context["broker_contract_source"] = (
            resolution.detail
            or "Broker symbol metadata was available, but the symbol could not be resolved."
        )
        return context

    info = _safe_symbol_info(api, resolution.selected_symbol)
    constraints = _contract_constraints(info, canonical_symbol_value=canonical)
    context["broker_contract_constraints"] = constraints
    context["broker_contract_source"] = (
        f"Broker symbol metadata via {resolution.resolution_source or 'broker symbol discovery'}."
    )

    resolved_entry = entry
    entry_source = None
    if resolved_entry is None:
        tick = _safe_symbol_tick(api, resolution.selected_symbol)
        if tick is not None:
            if direction in {"LONG", "BUY"}:
                resolved_entry = _positive_float(getattr(tick, "ask", None))
                entry_source = "broker_symbol_tick.ask"
            else:
                resolved_entry = _positive_float(getattr(tick, "bid", None))
                entry_source = "broker_symbol_tick.bid"
    context["entry_price"] = resolved_entry
    context["entry_price_source"] = entry_source

    leverage, leverage_source = _account_leverage(
        account_snapshot=account_snapshot,
        bridge=bridge,
        api=api,
    )
    context["account_leverage"] = leverage
    context["account_leverage_source"] = leverage_source

    if volume is None or resolved_entry is None:
        return context

    order_type_const = _mt5_order_type(api, direction=direction, order_type=order_type)
    order_calc_margin = getattr(api, "order_calc_margin", None)
    margin_required = None
    if callable(order_calc_margin) and order_type_const is not None:
        try:
            margin_required = _nonnegative_float(
                order_calc_margin(order_type_const, resolution.selected_symbol, float(volume), float(resolved_entry))
            )
        except Exception:
            margin_required = None
    if margin_required is not None:
        context["estimated_margin_required_usd"] = margin_required
        context["margin_source"] = "broker.order_calc_margin"
        return context

    contract_size = constraints.get("contract_size")
    spec = get_instrument(canonical)
    if contract_size is None:
        contract_size = _positive_float(spec.contract_size)
    if contract_size is None or leverage is None or leverage <= 0:
        return context

    units = contract_size * float(volume)
    if spec.asset_class != "FX":
        notional = units * float(resolved_entry)
    elif canonical.startswith("USD/"):
        notional = units
    elif canonical.endswith("/USD"):
        notional = units * float(resolved_entry)
    else:
        notional = units * float(resolved_entry)
    context["estimated_notional_usd"] = notional
    context["estimated_margin_required_usd"] = notional / leverage
    context["margin_source"] = "broker.contract_size/account_leverage"
    return context


def build_pre_trade_money_estimate(
    *,
    symbol: str,
    direction: Any,
    lots: Any,
    price: Any,
    stop_loss: Any,
    take_profit: Any,
    proposed_intent: Mapping[str, Any] | None = None,
    account_snapshot: Mapping[str, Any] | None = None,
    bridge: Any = None,
    config: Any = None,
) -> dict[str, Any]:
    """Build a serializable pre-trade estimate for an order or raw intent."""

    assumptions: list[str] = [
        "Broker fill price, spread, commission, swap, and final margin are broker-side truth.",
    ]
    try:
        canonical = canonical_symbol(symbol)
        spec = get_instrument(canonical)
    except Exception as exc:
        return {
            "report_kind": "cas_forex_pre_trade_money_estimate",
            "status": "UNAVAILABLE",
            "symbol": str(symbol or ""),
            "direction": _direction_value(direction),
            "lots": _finite_float(lots),
            "detail": f"Unsupported symbol for money estimate: {exc}",
            "assumptions": assumptions,
            "claim_boundary": (
                "This is an estimate only. Broker receipts and account snapshots remain final truth."
            ),
        }

    volume = _positive_float(lots)
    resolved_account_snapshot, account_snapshot_source = _resolved_account_snapshot(
        account_snapshot,
        bridge,
    )
    entry, entry_source = _entry_price(order_price=price, proposed_intent=proposed_intent)
    sl = _positive_float(stop_loss)
    tp = _positive_float(take_profit)
    equity = _account_value(
        resolved_account_snapshot,
        "equity",
        "equity_usd",
        "account_equity",
        "account_equity_usd",
    )
    balance = _account_value(
        resolved_account_snapshot,
        "balance",
        "balance_usd",
        "account_balance",
        "account_balance_usd",
    )
    margin_used = _account_value(
        resolved_account_snapshot,
        "margin",
        "margin_used_usd",
        "account_margin",
    )
    free_margin = _account_value(
        resolved_account_snapshot,
        "free_margin",
        "margin_free",
        "free_margin_usd",
        "account_free_margin",
    )
    leverage = _account_value(resolved_account_snapshot, "leverage", "account_leverage")
    if leverage is None and config is not None:
        leverage = _positive_float(getattr(config, "leverage", None) or getattr(config, "account_leverage", None))
    leverage_source = "account_snapshot.leverage" if leverage is not None else None

    broker_context = _broker_margin_context(
        canonical=canonical,
        direction=_direction_value(direction),
        order_type=_order_type_value(None, proposed_intent),
        volume=volume,
        entry=entry,
        bridge=bridge,
        account_snapshot=resolved_account_snapshot,
        config=config,
    )
    if entry is None and broker_context.get("entry_price") is not None:
        entry = _positive_float(broker_context.get("entry_price"))
        entry_source = str(broker_context.get("entry_price_source") or entry_source)
    if broker_context.get("account_leverage") is not None:
        leverage = _positive_float(broker_context.get("account_leverage"))
        leverage_source = str(broker_context.get("account_leverage_source") or leverage_source)

    expected_loss = None
    expected_loss_source = None
    if isinstance(proposed_intent, Mapping):
        expected_loss = _positive_float(proposed_intent.get("expected_loss_usd"))
        if expected_loss is not None:
            expected_loss_source = "proposed_intent.expected_loss_usd"

    stop_units = _distance_units(canonical, entry, sl)
    tp_units = _distance_units(canonical, entry, tp)
    static_unit_value = pip_value_per_lot(canonical, entry or spec.default_mid)
    broker_risk_unit_value, broker_reward_unit_value, broker_unit_value_source = (
        _broker_unit_values_per_lot(
            broker_context.get("broker_contract_constraints") or {},
            price_unit=spec.price_unit,
        )
    )
    unit_value = broker_risk_unit_value or static_unit_value
    reward_unit_value = broker_reward_unit_value or unit_value
    unit_value_source = broker_unit_value_source or "cas_instrument_default"
    geometry_risk_usd = None
    if volume is not None and stop_units is not None:
        geometry_risk_usd = stop_units * unit_value * volume
    risk_candidates = [
        (expected_loss, expected_loss_source),
        (geometry_risk_usd, f"entry_to_stop_distance/{unit_value_source}"),
    ]
    risk_candidates = [(value, source) for value, source in risk_candidates if value is not None]
    risk_usd = max((value for value, _ in risk_candidates), default=None)
    risk_source = None
    if risk_usd is not None:
        winning_sources = [source for value, source in risk_candidates if value == risk_usd and source]
        risk_source = winning_sources[0] if len(risk_candidates) == 1 else (
            "conservative_max(" + ",".join(source or "unknown" for _, source in risk_candidates) + ")"
        )
    reward_usd = None
    if volume is not None and tp_units is not None:
        reward_usd = tp_units * reward_unit_value * volume
    notional = (
        _positive_float(broker_context.get("estimated_notional_usd"))
        if broker_context.get("estimated_notional_usd") is not None
        else (usd_notional(canonical, entry, volume) if entry is not None and volume is not None else None)
    )
    margin_required = _nonnegative_float(broker_context.get("estimated_margin_required_usd"))
    margin_source = broker_context.get("margin_source")
    if margin_required is None:
        margin_required = notional / leverage if notional is not None and leverage and leverage > 0 else None
        if margin_required is not None:
            margin_source = "generic_notional/account_leverage"
    margin_after = margin_used + margin_required if margin_used is not None and margin_required is not None else None
    free_after = free_margin - margin_required if free_margin is not None and margin_required is not None else None
    margin_utilization_after = (
        (margin_after / equity) * 100.0
        if margin_after is not None and equity is not None and equity > 0
        else None
    )
    risk_pct = (risk_usd / equity) * 100.0 if risk_usd is not None and equity is not None and equity > 0 else None
    reward_risk = reward_usd / risk_usd if reward_usd is not None and risk_usd and risk_usd > 0 else None

    spread_cost = None
    spread_source = None
    if isinstance(proposed_intent, Mapping):
        spread_units = _positive_float(
            proposed_intent.get("spread_units")
            or proposed_intent.get("spread_pips")
            or proposed_intent.get("spread")
        )
        if spread_units is not None and volume is not None:
            spread_cost = spread_units * unit_value * volume
            spread_source = "proposed_intent.spread_units"
    if spread_cost is None:
        assumptions.append("Spread cost is unavailable until a broker/feed spread is attached to the intent.")
    assumptions.append("Commission and swap are unknown until the broker returns execution/history data.")
    if entry is None:
        assumptions.append("Market order entry price was not supplied; stop-risk and margin estimates are unavailable.")
    if leverage is None:
        assumptions.append("Leverage was not supplied; margin-required estimate is unavailable.")

    status = "ESTIMATED"
    if entry is None or volume is None:
        status = "PARTIAL"
    if risk_usd is None and margin_required is None:
        status = "PARTIAL"

    return {
        "report_kind": "cas_forex_pre_trade_money_estimate",
        "status": status,
        "symbol": canonical,
        "direction": _direction_value(direction),
        "lots": _rounded(volume),
        "entry_price": _rounded(entry, spec.price_precision),
        "entry_price_source": entry_source,
        "stop_loss": _rounded(sl, spec.price_precision),
        "take_profit": _rounded(tp, spec.price_precision),
        "price_unit_name": spec.unit_name,
        "price_unit_size": spec.price_unit,
        "stop_distance_units": _rounded(stop_units),
        "take_profit_distance_units": _rounded(tp_units),
        "unit_value_per_lot_usd": _rounded(unit_value, 6),
        "unit_value_source": unit_value_source,
        "static_unit_value_per_lot_usd": _rounded(static_unit_value, 6),
        "broker_unit_value_per_lot_usd": _rounded(broker_risk_unit_value, 6),
        "geometry_risk_at_stop_usd": _rounded(geometry_risk_usd, 2),
        "risk_at_stop_usd": _rounded(risk_usd, 2),
        "risk_source": risk_source,
        "risk_at_stop_pct_equity": _rounded(risk_pct, 4),
        "reward_at_take_profit_usd": _rounded(reward_usd, 2),
        "reward_risk_ratio": _rounded(reward_risk, 4),
        "estimated_notional_usd": _rounded(notional, 2),
        "estimated_margin_required_usd": _rounded(margin_required, 2),
        "estimated_margin_after_usd": _rounded(margin_after, 2),
        "estimated_free_margin_after_usd": _rounded(free_after, 2),
        "estimated_margin_utilization_after_pct": _rounded(margin_utilization_after, 4),
        "account_equity_usd": _rounded(equity, 2),
        "account_balance_usd": _rounded(balance, 2),
        "account_margin_used_usd": _rounded(margin_used, 2),
        "account_free_margin_usd": _rounded(free_margin, 2),
        "account_leverage": _rounded(leverage, 2),
        "account_leverage_source": leverage_source,
        "account_snapshot_source": account_snapshot_source,
        "spread_cost_estimate_usd": _rounded(spread_cost, 2),
        "spread_cost_source": spread_source,
        "commission_estimate_usd": None,
        "swap_estimate_usd": None,
        "selected_broker_symbol": broker_context.get("selected_broker_symbol"),
        "broker_symbol_resolution": broker_context.get("broker_symbol_resolution"),
        "broker_contract_constraints": broker_context.get("broker_contract_constraints"),
        "margin_estimate_source": margin_source,
        "broker_contract_source": broker_context.get("broker_contract_source"),
        "assumptions": assumptions,
        "claim_boundary": (
            "This is a pre-trade estimate for owner inspection. It does not authorize execution; "
            "risk gates, owner live gates, and broker receipts remain authoritative."
        ),
    }


def build_open_position_stop_risk(
    *,
    symbol: str,
    direction: Any,
    lots: Any,
    open_price: Any,
    current_price: Any,
    stop_loss: Any,
    take_profit: Any,
    account_snapshot: Mapping[str, Any] | None = None,
    bridge: Any = None,
    config: Any = None,
    risk_cap_pct: Any = None,
) -> dict[str, Any]:
    """Value an open position's current protective stop with broker economics.

    The admission-cap comparison uses original entry versus the current broker
    stop. A separate remaining-to-stop number describes possible equity giveback
    from the current quote. Neither value predicts slippage or forces an exit.
    """

    estimate = build_pre_trade_money_estimate(
        symbol=symbol,
        direction=direction,
        lots=lots,
        price=open_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )
    direction_value = _direction_value(direction)
    entry = _positive_float(open_price)
    current = _positive_float(current_price)
    stop = _positive_float(stop_loss)
    volume = _positive_float(lots)
    unit_size = _positive_float(estimate.get("price_unit_size"))
    unit_value = _positive_float(estimate.get("unit_value_per_lot_usd"))
    equity = _positive_float(estimate.get("account_equity_usd"))
    cap_pct = _positive_float(risk_cap_pct)

    status = "UNAVAILABLE"
    entry_loss_usd = None
    entry_loss_pct = None
    remaining_drawdown_usd = None
    remaining_drawdown_pct = None
    locked_profit_usd = None
    cap_breached: bool | None = None

    if stop is None:
        status = "UNPROTECTED_NO_STOP"
    elif None not in (entry, volume, unit_size, unit_value):
        is_long = direction_value in {"LONG", "BUY"}
        is_short = direction_value in {"SHORT", "SELL"}
        if is_long or is_short:
            entry_loss_distance = max((entry - stop) if is_long else (stop - entry), 0.0)
            locked_profit_distance = max((stop - entry) if is_long else (entry - stop), 0.0)
            entry_loss_usd = entry_loss_distance / unit_size * unit_value * volume
            locked_profit_usd = locked_profit_distance / unit_size * unit_value * volume
            if current is not None:
                remaining_distance = max((current - stop) if is_long else (stop - current), 0.0)
                remaining_drawdown_usd = remaining_distance / unit_size * unit_value * volume
            if equity is not None:
                entry_loss_pct = entry_loss_usd / equity * 100.0
                if remaining_drawdown_usd is not None:
                    remaining_drawdown_pct = remaining_drawdown_usd / equity * 100.0
            if cap_pct is not None and entry_loss_pct is not None:
                cap_breached = entry_loss_pct > cap_pct + 1e-9
            if cap_breached:
                status = "POSITION_RISK_CAP_BREACH"
            elif locked_profit_usd and locked_profit_usd > 0:
                status = "PROFIT_LOCKED_BY_STOP"
            elif cap_pct is not None and entry_loss_pct is not None:
                status = "POSITION_RISK_WITHIN_CAP"
            else:
                status = "POSITION_RISK_ESTIMATED"

    return {
        "report_kind": "cas_forex_open_position_stop_risk",
        "status": status,
        "symbol": estimate.get("symbol") or str(symbol or ""),
        "direction": direction_value,
        "lots": _rounded(volume),
        "open_price": _rounded(entry, 8),
        "current_price": _rounded(current, 8),
        "stop_loss": _rounded(stop, 8),
        "risk_at_stop_usd": _rounded(entry_loss_usd, 2),
        "risk_at_stop_pct_equity": _rounded(entry_loss_pct, 4),
        "remaining_to_stop_drawdown_usd": _rounded(remaining_drawdown_usd, 2),
        "remaining_to_stop_drawdown_pct_equity": _rounded(remaining_drawdown_pct, 4),
        "stop_locked_profit_usd": _rounded(locked_profit_usd, 2),
        "risk_cap_pct": _rounded(cap_pct, 4),
        "risk_cap_breached": cap_breached,
        "risk_basis": "ORIGINAL_ENTRY_TO_CURRENT_PROTECTIVE_STOP",
        "risk_economics_source": estimate.get("unit_value_source"),
        "broker_unit_value_per_lot_usd": estimate.get("broker_unit_value_per_lot_usd"),
        "account_equity_usd": estimate.get("account_equity_usd"),
        "account_snapshot_source": estimate.get("account_snapshot_source"),
        "detail": (
            "Admission-risk telemetry compares original entry with the current protective stop. "
            "Remaining-to-stop drawdown compares the current quote with that stop."
        ),
        "claim_boundary": (
            "This is observational stop-risk telemetry, not a close instruction. Broker fill, "
            "gap, slippage, commission, and final account impact remain broker truth."
        ),
    }


def summarize_open_position_stop_risk(
    rows: list[Mapping[str, Any]],
    *,
    risk_cap_pct: Any = None,
) -> dict[str, Any]:
    """Aggregate already-enriched open-position stop-risk rows."""

    cap_pct = _positive_float(risk_cap_pct)
    breach_rows = [row for row in rows if row.get("risk_cap_breached") is True]
    unprotected_rows = [row for row in rows if not _positive_float(row.get("stop_loss"))]
    valued_rows = [row for row in rows if _nonnegative_float(row.get("risk_at_stop_usd")) is not None]
    total_risk = sum(float(row.get("risk_at_stop_usd") or 0.0) for row in valued_rows)
    total_remaining = sum(
        float(row.get("remaining_to_stop_drawdown_usd") or 0.0)
        for row in rows
        if _nonnegative_float(row.get("remaining_to_stop_drawdown_usd")) is not None
    )
    total_pct = sum(
        float(row.get("risk_at_stop_pct_equity") or 0.0)
        for row in valued_rows
        if _nonnegative_float(row.get("risk_at_stop_pct_equity")) is not None
    )
    if not rows:
        status = "NO_OPEN_POSITIONS"
    elif breach_rows:
        status = "POSITION_RISK_CAP_BREACH"
    elif unprotected_rows:
        status = "UNPROTECTED_POSITION_RISK_UNKNOWN"
    elif len(valued_rows) == len(rows) and cap_pct is not None:
        status = "POSITION_RISK_WITHIN_CAP"
    elif valued_rows:
        status = "POSITION_RISK_ESTIMATED"
    else:
        status = "POSITION_RISK_UNAVAILABLE"
    return {
        "report_kind": "cas_forex_open_position_risk_summary",
        "status": status,
        "open_position_count": len(rows),
        "valued_position_count": len(valued_rows),
        "unprotected_position_count": len(unprotected_rows),
        "risk_cap_breach_count": len(breach_rows),
        "risk_cap_breach_tickets": [
            row.get("ticket", row.get("broker_ticket")) for row in breach_rows
        ],
        "risk_cap_pct": _rounded(cap_pct, 4),
        "combined_entry_to_stop_risk_usd": _rounded(total_risk, 2),
        "combined_entry_to_stop_risk_pct_equity": _rounded(total_pct, 4),
        "combined_remaining_to_stop_drawdown_usd": _rounded(total_remaining, 2),
        "detail": (
            f"{len(breach_rows)} of {len(rows)} open position(s) exceed the current per-trade "
            "entry-risk cap. Existing positions are reported for Operator supervision; this "
            "summary does not add a retroactive forced-close rule."
            if breach_rows
            else "Open-position stop risk is valued with broker tick economics where available."
        ),
        "claim_boundary": (
            "This summary exposes current protective-stop evidence. It does not authorize, "
            "block, modify, or close an already-open position."
        ),
    }
