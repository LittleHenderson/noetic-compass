"""Account health and performance metrics for CAS Forex.

This module projects the account ledger into the numbers a trading operator
actually needs: balance, equity, drawdown, open exposure, protection coverage,
closed-trade win/loss, profit factor, and expectancy. It is read-only and does
not authorize or place trades.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from cas_forex.movement_stream import build_movement_position_feed_truth
from cas_forex.movement_stream import build_movement_price_source_summary


CLAIM_BOUNDARY = (
    "Account health is a read-only projection over the account ledger. It can "
    "summarize balance, equity, P&L, drawdown, exposure, protective-order "
    "coverage, and closed-trade performance, but it does not generate signals, "
    "place orders, close positions, authorize live trading, or move money."
)


def build_account_health_report(
    account_ledger: Mapping[str, Any],
    *,
    movement_stream: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = _mapping(account_ledger.get("summary"))
    positions = _rows(account_ledger.get("positions"))
    orders = _rows(account_ledger.get("orders"))
    deals = _rows(account_ledger.get("deals"))
    events = _rows(account_ledger.get("cashflow_events"))

    account = _account_metrics(summary)
    closed = _closed_trade_metrics(deals)
    exposure = _open_exposure_metrics(positions, orders, summary)
    source_health = _source_health_metrics(positions, movement_stream=movement_stream)
    daily = _daily_metrics(events, as_of_date=str(account_ledger.get("as_of_date") or ""))
    data_quality = _data_quality(account_ledger, positions, orders, deals)
    status, blockers = _health_status(account, exposure, source_health)

    return {
        "report_kind": "cas_forex_account_health",
        "generated_from": {
            "source_report_kind": account_ledger.get("report_kind"),
            "mode": account_ledger.get("mode"),
            "plan_id": account_ledger.get("plan_id"),
            "lead_id": account_ledger.get("lead_id"),
            "as_of_date": account_ledger.get("as_of_date"),
            "live_money_authorized": bool(account_ledger.get("live_money_authorized", False)),
        },
        "status": status,
        "blockers": blockers,
        "account": account,
        "daily": daily,
        "closed_trade_performance": closed,
        "open_exposure": exposure,
        "source_health": source_health,
        "data_quality": data_quality,
        "decision_metrics": {
            "balance_usd": account["balance_usd"],
            "equity_usd": account["equity_usd"],
            "free_margin_usd": account["free_margin_usd"],
            "realized_pnl_usd": account["realized_pnl_usd"],
            "floating_pnl_usd": account["floating_pnl_usd"],
            "drawdown_pct": account["drawdown_pct"],
            "closed_trade_count": closed["closed_trade_count"],
            "win_rate_pct": closed["win_rate_pct"],
            "profit_factor": closed["profit_factor"],
            "expectancy_usd": closed["expectancy_usd"],
            "open_position_count": exposure["open_position_count"],
            "open_lots": exposure["open_lots"],
            "unprotected_position_count": exposure["unprotected_position_count"],
            "protective_order_coverage_pct": exposure["protective_order_coverage_pct"],
            "stale_price_position_count": source_health["stale_price_position_count"],
            "static_simulator_position_count": source_health["static_simulator_position_count"],
            "broker_ticket_position_count": source_health["broker_ticket_position_count"],
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _account_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    balance = _money(summary.get("balance_usd"))
    equity = _money(summary.get("equity_usd"))
    margin = _money(summary.get("margin_used_usd"))
    free_margin = _money(summary.get("free_margin_usd"))
    initial = _money(summary.get("initial_investment_usd"))
    margin_utilization = _pct((margin / equity) * 100.0) if equity > 0 else None
    return {
        "mode": summary.get("mode"),
        "currency": summary.get("currency", "USD"),
        "initial_investment_usd": initial,
        "balance_usd": balance,
        "equity_usd": equity,
        "free_margin_usd": free_margin,
        "margin_used_usd": margin,
        "margin_utilization_pct": margin_utilization,
        "realized_pnl_usd": _money(summary.get("realized_pnl_usd")),
        "floating_pnl_usd": _money(summary.get("floating_pnl_usd")),
        "swap_usd": _money(summary.get("swap_usd")),
        "commission_usd": _money(summary.get("commission_usd")),
        "broker_fees_usd": _money(summary.get("broker_fees_usd")),
        "drawdown_usd": _money(summary.get("drawdown_usd")),
        "drawdown_pct": _pct(summary.get("drawdown_pct")),
        "return_on_initial_pct": _pct(((equity - initial) / initial) * 100.0) if initial > 0 else None,
    }


def _closed_trade_metrics(deals: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    closed = [row for row in deals if _is_closed_trade(row)]
    pnls = [_money(row.get("net_pnl_usd")) for row in closed]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    flats = [value for value in pnls if value == 0]
    gross_profit = _money(sum(wins))
    gross_loss = _money(abs(sum(losses)))
    net = _money(sum(pnls))
    count = len(closed)
    profit_factor = None if gross_loss == 0 else _round(gross_profit / gross_loss, 4)
    if gross_loss == 0 and gross_profit > 0:
        profit_factor_state = "NO_CLOSED_LOSSES"
    elif gross_profit == 0 and gross_loss > 0:
        profit_factor_state = "NO_CLOSED_PROFITS"
    elif count == 0:
        profit_factor_state = "NO_CLOSED_TRADES"
    else:
        profit_factor_state = "CALCULATED"
    r_values = [_r_multiple(row) for row in closed]
    r_values = [value for value in r_values if value is not None]
    by_symbol: dict[str, dict[str, Any]] = {}
    symbol_rows: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in closed:
        symbol_rows[str(row.get("symbol") or "UNKNOWN")].append(row)
    for symbol, rows in sorted(symbol_rows.items()):
        values = [_money(row.get("net_pnl_usd")) for row in rows]
        symbol_wins = [value for value in values if value > 0]
        symbol_losses = [value for value in values if value < 0]
        by_symbol[symbol] = {
            "closed_trade_count": len(rows),
            "net_pnl_usd": _money(sum(values)),
            "win_rate_pct": _pct((len(symbol_wins) / len(rows)) * 100.0) if rows else None,
            "profit_factor": None if not symbol_losses else _round(sum(symbol_wins) / abs(sum(symbol_losses)), 4),
        }
    return {
        "closed_trade_count": count,
        "winning_trade_count": len(wins),
        "losing_trade_count": len(losses),
        "breakeven_trade_count": len(flats),
        "win_rate_pct": _pct((len(wins) / count) * 100.0) if count else None,
        "gross_profit_usd": gross_profit,
        "gross_loss_usd": gross_loss,
        "net_pnl_usd": net,
        "profit_factor": profit_factor,
        "profit_factor_state": profit_factor_state,
        "average_win_usd": _money(sum(wins) / len(wins)) if wins else None,
        "average_loss_usd": _money(sum(losses) / len(losses)) if losses else None,
        "expectancy_usd": _money(net / count) if count else None,
        "average_r_multiple": _round(sum(r_values) / len(r_values), 4) if r_values else None,
        "r_multiple_count": len(r_values),
        "by_symbol": by_symbol,
    }


def _open_exposure_metrics(
    positions: Sequence[Mapping[str, Any]],
    orders: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    exposure_by_symbol: dict[str, float] = defaultdict(float)
    exposure_by_direction: dict[str, float] = defaultdict(float)
    protected = 0
    unprotected: list[dict[str, Any]] = []
    risk_price_lots = 0.0
    open_lots = 0.0
    for row in positions:
        symbol = str(row.get("symbol") or "UNKNOWN")
        side = str(row.get("side") or "UNKNOWN").upper()
        lots = _float(row.get("lot_size"))
        open_lots += lots
        exposure_by_symbol[symbol] += lots
        exposure_by_direction[side] += lots
        stop_loss = _nullable_float(row.get("stop_loss"))
        open_price = _nullable_float(row.get("open_price"))
        if stop_loss is None or stop_loss <= 0:
            unprotected.append(_position_ref(row, reason="missing_stop_loss"))
            continue
        protected += 1
        if open_price is not None and open_price > 0:
            risk_price_lots += abs(open_price - stop_loss) * lots

    open_count = len(positions)
    planned_risk = _money(summary.get("planned_risk_usd"))
    top_symbols = sorted(
        ({"symbol": symbol, "lots": _round(lots, 4)} for symbol, lots in exposure_by_symbol.items()),
        key=lambda item: float(item["lots"]),
        reverse=True,
    )
    return {
        "open_position_count": open_count,
        "pending_order_count": len(orders),
        "open_lots": _round(open_lots, 4),
        "exposure_by_symbol_lots": {key: _round(value, 4) for key, value in sorted(exposure_by_symbol.items())},
        "exposure_by_direction_lots": {key: _round(value, 4) for key, value in sorted(exposure_by_direction.items())},
        "top_symbol_exposures": top_symbols[:5],
        "protected_position_count": protected,
        "unprotected_position_count": len(unprotected),
        "unprotected_positions": unprotected,
        "protective_order_coverage_pct": _pct((protected / open_count) * 100.0) if open_count else 100.0,
        "open_risk_estimate_usd": planned_risk if planned_risk > 0 else None,
        "open_risk_estimate_source": "ledger.summary.planned_risk_usd" if planned_risk > 0 else "unavailable",
        "open_risk_price_lots": _round(risk_price_lots, 6),
    }


def _source_health_metrics(
    positions: Sequence[Mapping[str, Any]],
    *,
    movement_stream: Mapping[str, Any] | None,
) -> dict[str, Any]:
    movement_positions = _movement_positions_by_key(movement_stream)
    label_counts: dict[str, int] = defaultdict(int)
    stale_rows: list[dict[str, Any]] = []
    static_rows: list[dict[str, Any]] = []
    provider_priced = 0
    broker_ticket_count = 0

    for row in positions:
        key = _position_key(row)
        movement_row = movement_positions.get(key) or {}
        broker_ticket = row.get("broker_ticket") or movement_row.get("broker_ticket")
        label = str(
            movement_row.get("position_source_label")
            or ("BROKER_TICKET_LEDGER_ONLY" if broker_ticket else "LEDGER_SIMULATOR")
        )
        price_source = str(movement_row.get("price_source") or "")
        price_stale = bool(movement_row.get("price_stale", False))
        label_counts[label] += 1
        if broker_ticket:
            broker_ticket_count += 1
        if label == "PAPER_SIM_PROVIDER_PRICED" or price_source.startswith(("provider_snapshot:", "operator_quote_override")):
            provider_priced += 1
        if label == "PAPER_SIM_STATIC" or price_source.startswith("paper_route_snapshot"):
            static_rows.append(_source_ref(row, movement_row, reason="static_simulator_price"))
        if price_stale:
            stale_rows.append(_source_ref(row, movement_row, reason=str(movement_row.get("stale_reason") or "stale_price")))

    open_count = len(positions)
    simulator_count = max(0, open_count - broker_ticket_count)
    static_count = len(static_rows)
    stale_count = len(stale_rows)
    movement_present = isinstance(movement_stream, Mapping) and bool(movement_stream)
    canonical_truth = (
        movement_stream.get("movement_source_truth")
        if movement_present and isinstance(movement_stream.get("movement_source_truth"), Mapping)
        else {}
    )
    source_payload = canonical_truth if isinstance(canonical_truth, Mapping) and canonical_truth else movement_stream if movement_present else {}
    price_status = (
        str(source_payload.get("price_source_status") or "UNKNOWN")
        if movement_present
        else "LEDGER_ONLY"
    )
    if open_count == 0:
        local_detail = "No open positions are present in the account ledger."
    elif stale_count or static_count:
        local_detail = (
            f"{stale_count or static_count} open position row(s) are static or stale simulator telemetry; "
            "floating P&L may remain unchanged until provider/MT5 prices are usable."
        )
    elif broker_ticket_count == open_count:
        local_detail = "All open positions carry broker tickets in the ledger."
    elif provider_priced:
        local_detail = "Simulator rows are being repriced by provider/operator quotes."
    else:
        local_detail = "Open position source is ledger-only simulator telemetry."
    configured_provider = (
        str(
            source_payload.get("configured_market_data_provider")
            or source_payload.get("market_data_provider")
            or ""
        ).strip()
        if movement_present
        else ""
    )
    mt5_fallback_symbols = _string_list(source_payload.get("mt5_fallback_symbols") if movement_present else None)
    provider_stale_symbols = _string_list(source_payload.get("provider_stale_symbols") if movement_present else None)
    provider_errors = source_payload.get("provider_errors") if movement_present else None
    provider_error_count = int(source_payload.get("provider_error_count") or 0) if movement_present else 0
    if provider_error_count <= 0 and isinstance(provider_errors, Mapping):
        provider_error_count = len(provider_errors)
    price_source_label = (
        str(source_payload.get("price_source_label") or "").strip()
        if movement_present
        else ""
    )
    price_source_summary = (
        str(source_payload.get("price_source_summary") or "").strip()
        if movement_present
        else ""
    )
    price_source_warning = (
        str(source_payload.get("price_source_warning") or "").strip()
        if movement_present
        else ""
    )
    static_simulation_active = bool(
        (source_payload.get("static_simulation_active") if movement_present else False)
        or static_count
    )
    position_feed_label = (
        str(source_payload.get("position_feed_label") or "").strip()
        if movement_present
        else ""
    )
    position_feed_detail = (
        str(source_payload.get("position_feed_detail") or "").strip()
        if movement_present
        else ""
    )
    if not (price_source_label and price_source_summary):
        derived = build_movement_price_source_summary(
            price_source_status=price_status,
            market_data_provider_requested=bool(movement_stream.get("market_data_provider_requested")) if movement_present else False,
            configured_market_data_provider=configured_provider or None,
            provider_usable_symbols=_string_list(movement_stream.get("provider_usable_symbols") if movement_present else None),
            static_fallback_symbols=_string_list(movement_stream.get("static_fallback_symbols") if movement_present else None),
            mt5_fallback_symbols=mt5_fallback_symbols,
            provider_stale_symbols=provider_stale_symbols,
            provider_freshness_max_age_seconds=movement_stream.get("provider_freshness_max_age_seconds") if movement_present else None,
        )
        price_source_label = price_source_label or str(derived.get("price_source_label") or "")
        price_source_summary = price_source_summary or str(derived.get("price_source_summary") or "")
        price_source_warning = price_source_warning or str(derived.get("price_source_warning") or "")
        static_simulation_active = bool(derived.get("static_simulation_active")) or static_simulation_active
    if movement_present and not (position_feed_label and position_feed_detail):
        derived_feed = build_movement_position_feed_truth(
            positions=_rows(movement_stream.get("positions")),
            quotes=_rows(movement_stream.get("quotes")),
            price_source_status=price_status,
            market_data_provider_requested=bool(movement_stream.get("market_data_provider_requested")),
            configured_market_data_provider=configured_provider or None,
            provider_usable_symbols=_string_list(movement_stream.get("provider_usable_symbols")),
            static_fallback_symbols=_string_list(movement_stream.get("static_fallback_symbols")),
            mt5_fallback_symbols=mt5_fallback_symbols,
            provider_stale_symbols=provider_stale_symbols,
            provider_freshness_max_age_seconds=movement_stream.get("provider_freshness_max_age_seconds"),
        )
        position_feed_label = position_feed_label or str(derived_feed.get("position_feed_label") or "")
        position_feed_detail = position_feed_detail or str(derived_feed.get("position_feed_detail") or "")
    detail = position_feed_detail or local_detail

    return {
        "movement_stream_present": movement_present,
        "price_source_status": price_status,
        "price_source_label": price_source_label or None,
        "price_source_summary": price_source_summary or None,
        "price_source_warning": price_source_warning or None,
        "position_feed_label": position_feed_label or None,
        "position_feed_detail": position_feed_detail or None,
        "static_simulation_active": static_simulation_active,
        "open_position_count": open_count,
        "broker_ticket_position_count": broker_ticket_count,
        "simulator_position_count": simulator_count,
        "provider_priced_simulator_position_count": provider_priced,
        "static_simulator_position_count": static_count,
        "stale_price_position_count": stale_count,
        "source_label_counts": dict(sorted(label_counts.items())),
        "configured_market_data_provider": configured_provider or None,
        "provider_usable_symbols": _string_list(source_payload.get("provider_usable_symbols") if movement_present else None),
        "static_fallback_symbols": _string_list(source_payload.get("static_fallback_symbols") if movement_present else None),
        "mt5_fallback_symbols": mt5_fallback_symbols,
        "provider_stale_symbols": provider_stale_symbols,
        "closed_market_symbols": _string_list(source_payload.get("closed_market_symbols") if movement_present else None),
        "closed_market_quote_count": int(source_payload.get("closed_market_quote_count") or 0) if movement_present else 0,
        "unsupported_provider_symbols": _string_list(source_payload.get("unsupported_provider_symbols") if movement_present else None),
        "provider_freshness_max_age_seconds": source_payload.get("provider_freshness_max_age_seconds") if movement_present else None,
        "snapshot_age_seconds_by_symbol": (
            dict(source_payload.get("snapshot_age_seconds_by_symbol") or {})
            if movement_present and isinstance(source_payload.get("snapshot_age_seconds_by_symbol"), Mapping)
            else {}
        ),
        "provider_error_count": provider_error_count,
        "static_quote_count": int(source_payload.get("static_quote_count") or 0) if movement_present else 0,
        "stale_positions": stale_rows[:10],
        "static_positions": static_rows[:10],
        "attention_required": bool(stale_count or static_count),
        "detail": detail,
        "local_detail": local_detail,
    }


def _daily_metrics(events: Sequence[Mapping[str, Any]], *, as_of_date: str) -> dict[str, Any]:
    target_date = str(as_of_date or "")
    if not target_date:
        dates = sorted({_date_part(row.get("timestamp")) for row in events if _date_part(row.get("timestamp"))})
        target_date = dates[-1] if dates else ""
    realized_event_types = {"realized_profit", "realized_loss"}
    todays = [
        row
        for row in events
        if _date_part(row.get("timestamp")) == target_date and str(row.get("event_type") or "") in realized_event_types
    ]
    return {
        "as_of_date": target_date,
        "realized_pnl_usd": _money(sum(_float(row.get("balance_delta_usd")) for row in todays)),
        "realized_trade_event_count": len(todays),
    }


def _data_quality(
    account_ledger: Mapping[str, Any],
    positions: Sequence[Mapping[str, Any]],
    orders: Sequence[Mapping[str, Any]],
    deals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    open_count = len(positions)
    stop_visible = sum(1 for row in positions if _nullable_float(row.get("stop_loss")) not in (None, 0.0))
    return {
        "ledger_present": bool(account_ledger),
        "summary_present": isinstance(account_ledger.get("summary"), Mapping),
        "closed_deals_present": bool(deals),
        "open_positions_present": bool(positions),
        "pending_orders_present": bool(orders),
        "stop_loss_visibility_pct": _pct((stop_visible / open_count) * 100.0) if open_count else 100.0,
        "notes": [
            "Profit factor and win rate require closed trade rows.",
            "Open risk in USD uses ledger planned_risk_usd when broker-grade per-position risk is unavailable.",
        ],
    }


def _health_status(
    account: Mapping[str, Any],
    exposure: Mapping[str, Any],
    source_health: Mapping[str, Any],
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if int(exposure.get("unprotected_position_count") or 0) > 0:
        blockers.append("One or more open positions has no visible stop loss.")
    if int(source_health.get("stale_price_position_count") or 0) > 0:
        blockers.append("One or more open positions is priced by stale/static simulator telemetry.")
    margin_utilization = account.get("margin_utilization_pct")
    if isinstance(margin_utilization, (int, float)) and margin_utilization >= 80.0:
        blockers.append(f"Margin utilization is high at {margin_utilization:.2f}%.")
    if _float(account.get("free_margin_usd")) <= 0 and _float(account.get("margin_used_usd")) > 0:
        blockers.append("Free margin is zero while margin is in use.")
    return ("ATTENTION" if blockers else "OBSERVING"), blockers


def _is_closed_trade(row: Mapping[str, Any]) -> bool:
    tab = str(row.get("tab") or "").upper()
    status = str(row.get("status") or "").upper()
    return tab == "DEALS" or "CLOSED" in status or _nullable_float(row.get("close_or_current_price")) is not None


def _r_multiple(row: Mapping[str, Any]) -> float | None:
    open_price = _nullable_float(row.get("open_price"))
    close_price = _nullable_float(row.get("close_or_current_price"))
    stop_loss = _nullable_float(row.get("stop_loss"))
    if open_price is None or close_price is None or stop_loss is None:
        return None
    risk = abs(open_price - stop_loss)
    if risk <= 0:
        return None
    side = str(row.get("side") or "").upper()
    if side in {"SHORT", "SELL"}:
        movement = open_price - close_price
    else:
        movement = close_price - open_price
    return _round(movement / risk, 4)


def _position_ref(row: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "row_id": row.get("row_id"),
        "symbol": row.get("symbol"),
        "side": row.get("side"),
        "lot_size": _float(row.get("lot_size")),
        "broker_ticket": row.get("broker_ticket"),
        "simulator_ticket": row.get("simulator_ticket"),
        "reason": reason,
    }


def _source_ref(row: Mapping[str, Any], movement_row: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "row_id": row.get("row_id") or movement_row.get("row_id"),
        "symbol": row.get("symbol") or movement_row.get("symbol"),
        "side": row.get("side") or movement_row.get("side"),
        "lot_size": _float(row.get("lot_size") or movement_row.get("lot_size")),
        "broker_ticket": row.get("broker_ticket") or movement_row.get("broker_ticket"),
        "simulator_ticket": row.get("simulator_ticket") or movement_row.get("simulator_ticket"),
        "price_source": movement_row.get("price_source"),
        "position_source_label": movement_row.get("position_source_label"),
        "stale_reason": movement_row.get("stale_reason"),
        "reason": reason,
    }


def _movement_positions_by_key(movement_stream: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    positions = movement_stream.get("positions") if isinstance(movement_stream, Mapping) else None
    if not isinstance(positions, list):
        return {}
    out: dict[str, Mapping[str, Any]] = {}
    for row in positions:
        if not isinstance(row, Mapping):
            continue
        key = _position_key(row)
        if key:
            out[key] = row
    return out


def _position_key(row: Mapping[str, Any]) -> str:
    for key in ("row_id", "broker_ticket", "simulator_ticket"):
        value = row.get(key)
        if value:
            return f"{key}:{value}"
    return "|".join(
        str(row.get(key) or "")
        for key in ("symbol", "side", "lot_size", "open_price")
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _nullable_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> float:
    return round(_float(value), 2)


def _round(value: Any, places: int) -> float:
    return round(_float(value), places)


def _pct(value: Any) -> float:
    return round(_float(value), 4)


def _date_part(value: Any) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else ""
