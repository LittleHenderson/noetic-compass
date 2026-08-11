"""Shared active broker-account and after-cost position truth for AI decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from cas_forex.mt5_account_growth import (
    classify_mt5_account_growth_snapshot,
    load_mt5_account_growth,
)

REPORT_KIND = "cas_forex_operator_active_account_context"
NORTH_STAR = "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH"


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {}


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_number(source: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key not in source:
            continue
        value = _number(source.get(key))
        if value is not None:
            return value
    return None


def _first_value(source: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in source and source.get(key) is not None:
            return source.get(key)
    return None


def enrich_position_open_pnl(position: Mapping[str, Any]) -> dict[str, Any]:
    """Return one position with explicit price, cost, and net-open P&L fields."""

    row = dict(position)
    price_pnl = _first_number(
        row,
        "position_price_pnl_usd",
        "floating_pnl_usd",
        "floating_pnl",
        "profit",
    )
    swap = _first_number(row, "swap_usd", "swap")
    commission = _first_number(row, "commission_usd", "commission")
    explicit_net = _first_number(
        row,
        "net_open_pnl_after_reported_costs_usd",
        "net_open_pnl_usd",
    )
    swap_reported = any(
        key in row and row.get(key) is not None for key in ("swap_usd", "swap")
    )
    commission_reported = any(
        key in row and row.get(key) is not None
        for key in ("commission_usd", "commission")
    )
    reported_swap = float(swap or 0.0)
    reported_commission = float(commission or 0.0)
    net_open_pnl = (
        explicit_net
        if explicit_net is not None
        else (
            round(float(price_pnl) + reported_swap + reported_commission, 2)
            if price_pnl is not None
            else None
        )
    )
    row.update(
        {
            "position_price_pnl_usd": (
                round(float(price_pnl), 2) if price_pnl is not None else None
            ),
            "swap_usd": round(reported_swap, 2) if price_pnl is not None else None,
            "commission_usd": (
                round(reported_commission, 2) if price_pnl is not None else None
            ),
            "net_open_pnl_after_reported_costs_usd": (
                round(float(net_open_pnl), 2) if net_open_pnl is not None else None
            ),
            "swap_reported": swap_reported,
            "commission_reported": commission_reported,
            "open_pnl_basis": "PRICE_PLUS_REPORTED_SWAP_AND_COMMISSION",
        }
    )
    return row


def position_is_net_winning_after_reported_costs(
    position: Mapping[str, Any],
) -> bool:
    """A compound winner must be positive after every currently reported cost."""

    enriched = enrich_position_open_pnl(position)
    net_open_pnl = _number(
        enriched.get("net_open_pnl_after_reported_costs_usd")
    )
    if net_open_pnl is not None:
        return net_open_pnl > 0.0

    side = str(
        _first_value(enriched, "side", "direction", "type") or ""
    ).strip().upper()
    opened = _first_number(enriched, "open_price", "price_open", "entry_price")
    current = _first_number(enriched, "current_price", "price_current")
    if opened is None or current is None:
        return False
    if side in {"BUY", "LONG", "0"}:
        return current > opened
    if side in {"SELL", "SHORT", "1"}:
        return current < opened
    return False


def build_operator_account_context(
    bridge: Any,
    *,
    positions: Sequence[Mapping[str, Any]] | None = None,
    account_snapshot: Mapping[str, Any] | None = None,
    growth_snapshot: Mapping[str, Any] | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Build one broker-facing account scoreboard for immediate AI decisions."""

    raw_account = dict(account_snapshot or {})
    if not raw_account:
        getter = getattr(bridge, "get_account_info", None)
        if callable(getter):
            try:
                raw_account = _mapping(getter())
            except Exception:
                raw_account = {}

    raw_positions: list[dict[str, Any]] = []
    if positions is not None:
        raw_positions = [dict(row) for row in positions if isinstance(row, Mapping)]
    else:
        for name in ("get_all_open_positions", "get_open_positions"):
            getter = getattr(bridge, name, None)
            if not callable(getter):
                continue
            try:
                raw_positions = [_mapping(row) for row in list(getter() or [])]
            except Exception:
                raw_positions = []
            break

    enriched_positions = [enrich_position_open_pnl(row) for row in raw_positions]
    position_rows_with_pnl = [
        row
        for row in enriched_positions
        if _number(row.get("position_price_pnl_usd")) is not None
    ]
    position_price_pnl = round(
        sum(float(row.get("position_price_pnl_usd") or 0.0) for row in position_rows_with_pnl),
        2,
    )
    open_swap = round(
        sum(float(row.get("swap_usd") or 0.0) for row in position_rows_with_pnl),
        2,
    )
    open_commission = round(
        sum(float(row.get("commission_usd") or 0.0) for row in position_rows_with_pnl),
        2,
    )
    reported_components = round(position_price_pnl + open_swap + open_commission, 2)

    balance = _first_number(raw_account, "balance", "balance_usd")
    equity = _first_number(raw_account, "equity", "equity_usd")
    account_net_open_pnl = _first_number(
        raw_account,
        "account_net_open_pnl_usd",
        "floating_pnl",
        "floating_pnl_usd",
        "profit",
    )
    if account_net_open_pnl is None and balance is not None and equity is not None:
        account_net_open_pnl = round(equity - balance, 2)
    if account_net_open_pnl is None and position_rows_with_pnl:
        account_net_open_pnl = reported_components

    is_demo: bool | None = None
    if isinstance(raw_account.get("is_demo"), bool):
        is_demo = bool(raw_account.get("is_demo"))
    else:
        checker = getattr(bridge, "is_demo_account", None)
        if callable(checker):
            try:
                is_demo = bool(checker())
            except Exception:
                is_demo = None
    login = _first_value(raw_account, "login", "account_login") or getattr(
        bridge, "login", None
    )
    server = _first_value(raw_account, "server", "account_server") or getattr(
        bridge, "server", None
    )
    growth = dict(growth_snapshot or {})
    if growth_snapshot is None:
        growth = load_mt5_account_growth()
    growth_baseline = _mapping(growth.get("baseline"))
    growth_realized = _mapping(growth.get("realized_growth"))
    growth_state = classify_mt5_account_growth_snapshot(
        growth,
        login=login,
        server=server,
        current_balance=balance,
        observed_at=observed_at,
    )
    current_utc_day = str(growth_state.get("current_utc_day") or "")
    growth_period_utc_day = str(growth_state.get("period_utc_day") or "")
    growth_period_current = bool(growth_state.get("period_current"))
    growth_account_matches = bool(growth_state.get("account_matches"))
    growth_balance_matches = bool(growth_state.get("balance_matches"))
    growth_reconciled = bool(growth_state.get("reconciled"))
    last_reconciled_available = bool(
        growth_state.get("last_reconciled_available")
    )
    margin = _first_number(raw_account, "margin", "margin_used_usd")
    margin_free = _first_number(
        raw_account,
        "margin_free",
        "free_margin",
        "free_margin_usd",
    )
    residual = (
        round(float(account_net_open_pnl) - reported_components, 2)
        if account_net_open_pnl is not None and position_rows_with_pnl
        else None
    )

    return {
        "report_kind": REPORT_KIND,
        "north_star": NORTH_STAR,
        "measurement_basis": (
            "Sustainable realized net account growth after spread, commission, "
            "swap, slippage, and losses, inside owner-delegated authority."
        ),
        "authoritative_source": "BROKER_BRIDGE_ACCOUNT_AND_POSITIONS",
        "login": login,
        "server": server,
        "currency": _first_value(raw_account, "currency") or "USD",
        "is_demo": is_demo,
        "mode": "DEMO" if is_demo is True else "LIVE" if is_demo is False else "UNKNOWN",
        "balance": balance,
        "equity": equity,
        "margin": margin,
        "margin_free": margin_free,
        "leverage": _first_value(raw_account, "leverage", "account_leverage"),
        "floating_pnl": account_net_open_pnl,
        "account_net_open_pnl_usd": account_net_open_pnl,
        "open_position_count": len(enriched_positions),
        "position_price_pnl_usd": position_price_pnl if position_rows_with_pnl else None,
        "open_swap_usd": open_swap if position_rows_with_pnl else None,
        "open_commission_usd": open_commission if position_rows_with_pnl else None,
        "reported_open_components_usd": (
            reported_components if position_rows_with_pnl else None
        ),
        "unattributed_open_pnl_usd": residual,
        "balance_baseline_status": (
            growth_baseline.get("status")
            if growth_reconciled
            else "PENDING_REFRESH_LAST_RECONCILED_BASELINE_AVAILABLE"
            if last_reconciled_available
            else "UNAVAILABLE_NO_RECONCILED_CASHFLOW_BASELINE"
        ),
        "current_balance_is_profit": False,
        "period_realized_status": (
            growth.get("period_realized_status")
            if growth_reconciled
            else "PENDING_BROKER_HISTORY_RECONCILIATION"
            if last_reconciled_available
            else "UNAVAILABLE_NO_PERIOD_RECONCILIATION"
        ),
        "cashflow_adjusted_realized_growth_usd": (
            growth_realized.get("cashflow_adjusted_all_time_account_currency")
            if growth_reconciled
            else None
        ),
        "realized_today_usd": (
            growth_realized.get("today_account_currency")
            if growth_reconciled
            else None
        ),
        "realized_month_usd": (
            growth_realized.get("month_account_currency")
            if growth_reconciled
            else None
        ),
        "net_external_capital_flow_usd": (
            growth_baseline.get("net_external_capital_flow_account_currency")
            if growth_reconciled
            else None
        ),
        "growth_pct_on_net_external_capital": (
            growth_realized.get("growth_pct_on_net_external_capital")
            if growth_reconciled
            else None
        ),
        "account_growth_reconciliation": {
            "status": growth.get("status") if growth else "UNAVAILABLE",
            "truth_status": growth_state.get("status"),
            "account_matches": growth_account_matches,
            "balance_matches": growth_balance_matches,
            "reconciled": growth_reconciled,
            "last_reconciled_available": last_reconciled_available,
            "pending_balance_delta_usd": growth_state.get(
                "pending_balance_delta_account_currency"
            ),
            "event_hash": growth.get("event_hash"),
            "generated_at": growth.get("generated_at"),
            "refresh_status": growth.get("refresh_status"),
            "refresh_reason": growth.get("refresh_reason"),
            "period_utc_day": growth_period_utc_day,
            "current_utc_day": current_utc_day,
            "period_current": growth_period_current,
        },
        "last_reconciled_growth": {
            "available": last_reconciled_available,
            "generated_at": growth.get("generated_at"),
            "event_hash": growth.get("event_hash"),
            "reconciled_balance_usd": growth_state.get(
                "saved_balance_account_currency"
            ),
            "current_balance_usd": growth_state.get(
                "current_balance_account_currency"
            ),
            "pending_balance_delta_usd": growth_state.get(
                "pending_balance_delta_account_currency"
            ),
            "cashflow_adjusted_realized_growth_usd": (
                growth_realized.get("cashflow_adjusted_all_time_account_currency")
                if last_reconciled_available
                else None
            ),
            "realized_today_usd": (
                growth_realized.get("today_account_currency")
                if last_reconciled_available and growth_period_current
                else None
            ),
            "realized_month_usd": (
                growth_realized.get("month_account_currency")
                if last_reconciled_available and growth_state.get("month_current")
                else None
            ),
            "net_external_capital_flow_usd": (
                growth_baseline.get("net_external_capital_flow_account_currency")
                if last_reconciled_available
                else None
            ),
        },
        "daily_target_is_trade_quota": False,
        "target_deficit_may_manufacture_trade_or_size": False,
        "open_pnl_interpretation": "UNREALIZED_NET_AFTER_REPORTED_OPEN_COSTS",
        "realized_growth_interpretation": (
            "CASHFLOW_ADJUSTED_BROKER_BALANCE_GROWTH"
            if growth_reconciled
            else "LAST_RECONCILED_VALUES_WITH_PENDING_UNCLASSIFIED_BALANCE_DELTA"
            if last_reconciled_available
            else "UNAVAILABLE_UNTIL_BROKER_HISTORY_RECONCILES"
        ),
    }


__all__ = [
    "NORTH_STAR",
    "REPORT_KIND",
    "build_operator_account_context",
    "enrich_position_open_pnl",
    "position_is_net_winning_after_reported_costs",
]
