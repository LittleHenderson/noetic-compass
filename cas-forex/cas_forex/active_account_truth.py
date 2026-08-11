"""Resolve one authoritative account story for owner and Operator surfaces.

The connected MT5 account and the durable simulator ledger are different
accounts.  This module selects the account governed by the active execution
lane and keeps the other source as explicitly secondary evidence so a cockpit
cannot add, merge, or accidentally swap their balances and positions.
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.mt5_account_growth import classify_mt5_account_growth_snapshot
from cas_forex.time_utils import utc_now


REPORT_KIND = "cas_forex_active_account_truth"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _integer(value: Any) -> int:
    number = _number(value)
    return int(number) if number is not None else 0


def _different(left: Any, right: Any, *, tolerance: float = 0.005) -> bool:
    left_number = _number(left)
    right_number = _number(right)
    if left_number is None or right_number is None:
        return False
    return abs(left_number - right_number) > tolerance


def build_active_account_truth(
    *,
    mt5_snapshot: Mapping[str, Any] | None,
    dispatch_loop: Mapping[str, Any] | None,
    simulator_health: Mapping[str, Any] | None = None,
    demo_learning: Mapping[str, Any] | None = None,
    account_growth: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the current account without merging unrelated ledgers."""

    mt5 = _mapping(mt5_snapshot)
    loop = _mapping(dispatch_loop)
    health = _mapping(simulator_health)
    learning = _mapping(demo_learning)
    growth = _mapping(account_growth)
    mt5_account = _mapping(mt5.get("account"))
    simulator_account = _mapping(health.get("account"))
    simulator_daily = _mapping(health.get("daily"))
    simulator_exposure = _mapping(health.get("open_exposure"))
    simulator_source = _mapping(health.get("source_health"))

    bridge = str(loop.get("last_bridge_class") or "")
    lane = str(loop.get("execution_lane") or "")
    execution_active = bool(loop.get("running") and loop.get("execution_active"))
    mt5_connected = bool(mt5.get("connected") and mt5_account)
    mt5_lane_active = bool(execution_active and "MT5" in bridge.upper() and mt5_connected)
    simulator_lane_active = bool(execution_active and "SIMULAT" in bridge.upper())

    if mt5_lane_active or (mt5_connected and not simulator_lane_active):
        authoritative_source = "mt5_account_snapshot"
        is_demo = bool(mt5.get("is_demo"))
        source_label = "MT5 DEMO" if is_demo else "MT5 LIVE"
        status = (
            "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
            if mt5_lane_active and is_demo
            else "PRIMARY_MT5_LIVE_ACCOUNT_ACTIVE"
            if mt5_lane_active
            else "CONNECTED_MT5_DEMO_ACCOUNT_OBSERVATIONAL"
            if is_demo
            else "CONNECTED_MT5_LIVE_ACCOUNT_OBSERVATIONAL"
        )
        account = {
            "login": mt5_account.get("login"),
            "server": mt5_account.get("server"),
            "name": mt5_account.get("name"),
            "currency": mt5_account.get("currency") or "USD",
            "leverage": mt5_account.get("leverage"),
            "is_demo": is_demo,
            "mode": "DEMO" if is_demo else "LIVE",
            "balance_usd": mt5_account.get("balance_usd"),
            "equity_usd": mt5_account.get("equity_usd"),
            "floating_pnl_usd": mt5_account.get("floating_pnl_usd"),
            "margin_used_usd": mt5_account.get("margin_used_usd"),
            "free_margin_usd": mt5_account.get("free_margin_usd"),
        }
        positions = _rows(mt5.get("positions"))
        position_price_pnl = round(
            sum(_number(row.get("floating_pnl_usd")) or 0.0 for row in positions),
            2,
        )
        open_swap = round(sum(_number(row.get("swap_usd")) or 0.0 for row in positions), 2)
        open_commission = round(
            sum(_number(row.get("commission_usd")) or 0.0 for row in positions),
            2,
        )
        reported_open_components = round(position_price_pnl + open_swap + open_commission, 2)
        account_open_pnl = _number(account.get("floating_pnl_usd"))
        account.update(
            {
                "position_price_pnl_usd": position_price_pnl,
                "open_swap_usd": open_swap,
                "open_commission_usd": open_commission,
                "reported_open_components_usd": reported_open_components,
                "unattributed_open_pnl_usd": (
                    round(account_open_pnl - reported_open_components, 2)
                    if account_open_pnl is not None
                    else None
                ),
            }
        )
        protection = _mapping(mt5.get("position_protection"))
        position_risk = _mapping(mt5.get("position_risk"))
        open_exposure = {
            "open_position_count": _integer(mt5.get("open_position_count")),
            "open_lots": round(sum(_number(row.get("lots")) or 0.0 for row in positions), 4),
            "protected_position_count": _integer(protection.get("protected_position_count")),
            "unprotected_position_count": _integer(protection.get("unprotected_position_count")),
            "protective_order_coverage_pct": (
                100.0
                if positions and not _integer(protection.get("unprotected_position_count"))
                else 0.0
                if positions
                else 100.0
            ),
            "risk_cap_breach_count": _integer(position_risk.get("risk_cap_breach_count")),
            "risk_cap_pct": position_risk.get("risk_cap_pct"),
            "entry_to_stop_risk_usd": position_risk.get("combined_entry_to_stop_risk_usd"),
            "entry_to_stop_risk_pct_equity": position_risk.get("combined_entry_to_stop_risk_pct_equity"),
            "remaining_to_stop_drawdown_usd": position_risk.get("combined_remaining_to_stop_drawdown_usd"),
        }
        account_source_detail = (
            "Connected MT5 demo account and broker positions are authoritative for the active PAPER MT5 lane."
            if mt5_lane_active and is_demo
            else "Connected MT5 account is the current owner-facing account snapshot; execution is not active on that MT5 lane."
            if not mt5_lane_active
            else "Connected MT5 live account and broker positions are authoritative for the active LIVE MT5 lane."
        )
    else:
        authoritative_source = "simulator_account"
        source_label = "SIMULATOR"
        status = "PRIMARY_SIMULATOR_ACCOUNT_ACTIVE" if simulator_lane_active else "ACTIVE_ACCOUNT_NOT_ESTABLISHED"
        account = {
            "login": None,
            "server": None,
            "name": None,
            "currency": simulator_account.get("currency") or "USD",
            "leverage": None,
            "is_demo": True,
            "mode": "PAPER_SIMULATOR",
            "balance_usd": simulator_account.get("balance_usd"),
            "equity_usd": simulator_account.get("equity_usd"),
            "floating_pnl_usd": simulator_account.get("floating_pnl_usd"),
            "margin_used_usd": simulator_account.get("margin_used_usd"),
            "free_margin_usd": simulator_account.get("free_margin_usd"),
            "position_price_pnl_usd": simulator_account.get("floating_pnl_usd"),
            "open_swap_usd": None,
            "open_commission_usd": None,
            "reported_open_components_usd": simulator_account.get("floating_pnl_usd"),
            "unattributed_open_pnl_usd": None,
        }
        positions = []
        protection = {}
        position_risk = {}
        open_exposure = {
            "open_position_count": _integer(simulator_exposure.get("open_position_count")),
            "open_lots": _number(simulator_exposure.get("open_lots")),
            "protected_position_count": _integer(simulator_exposure.get("protected_position_count")),
            "unprotected_position_count": _integer(simulator_exposure.get("unprotected_position_count")),
            "protective_order_coverage_pct": simulator_exposure.get("protective_order_coverage_pct"),
            "risk_cap_breach_count": None,
            "risk_cap_pct": None,
            "entry_to_stop_risk_usd": simulator_exposure.get("open_risk_estimate_usd"),
            "entry_to_stop_risk_pct_equity": None,
            "remaining_to_stop_drawdown_usd": None,
        }
        account_source_detail = (
            "The active execution lane uses the durable paper simulator. A connected MT5 account, if present, is not merged into this ledger."
            if simulator_lane_active
            else "No active execution account is established; simulator evidence is shown only as a fallback observation."
        )

    learning_overall = _mapping(learning.get("learning_overall"))
    growth_account = _mapping(growth.get("account"))
    growth_baseline = _mapping(growth.get("baseline"))
    growth_realized = _mapping(growth.get("realized_growth"))
    growth_reconciliation = _mapping(growth.get("reconciliation"))
    active_account_is_demo = bool(account.get("is_demo"))
    learning_applies = bool(
        authoritative_source == "mt5_account_snapshot" and active_account_is_demo
    )
    simulator_count = _integer(simulator_exposure.get("open_position_count"))
    growth_state = classify_mt5_account_growth_snapshot(
        growth,
        login=account.get("login"),
        server=account.get("server"),
        current_balance=account.get("balance_usd"),
    )
    growth_account_matches = bool(
        authoritative_source == "mt5_account_snapshot"
        and growth_state.get("account_matches")
    )
    growth_balance_matches = bool(
        authoritative_source == "mt5_account_snapshot"
        and growth_state.get("balance_matches")
    )
    growth_reconciled = bool(
        authoritative_source == "mt5_account_snapshot"
        and growth_state.get("reconciled")
    )
    last_reconciled_available = bool(
        authoritative_source == "mt5_account_snapshot"
        and growth_state.get("last_reconciled_available")
    )
    conflicts: list[dict[str, str]] = []
    if authoritative_source == "mt5_account_snapshot":
        conflicts.append(
            {
                "code": "SECONDARY_SIMULATOR_NOT_ACTIVE_ACCOUNT",
                "detail": "The simulator ledger is separate evidence and must not replace or be added to the connected MT5 account.",
            }
        )
        if simulator_count != _integer(open_exposure.get("open_position_count")):
            conflicts.append(
                {
                    "code": "SECONDARY_SIMULATOR_POSITION_COUNT_DIFFERS_FROM_MT5",
                    "detail": (
                        f"MT5 reports {_integer(open_exposure.get('open_position_count'))} open position(s); "
                        f"the separate simulator ledger reports {simulator_count}."
                    ),
                }
            )
        if _different(simulator_account.get("balance_usd"), account.get("balance_usd")):
            conflicts.append(
                {
                    "code": "SECONDARY_SIMULATOR_BALANCE_DIFFERS_FROM_MT5",
                    "detail": "The simulator and MT5 balances belong to different accounts and must be labeled separately.",
                }
            )
        if bool(simulator_source.get("static_simulation_active")):
            conflicts.append(
                {
                    "code": "STATIC_SIMULATION_IS_SECONDARY_DIAGNOSTIC",
                    "detail": "Static simulator pricing cannot overrule the current MT5 account or broker-position snapshot.",
                }
            )
        if growth and not growth_account_matches:
            conflicts.append(
                {
                    "code": "ACCOUNT_GROWTH_HISTORY_ACCOUNT_MISMATCH",
                    "detail": (
                        "The saved MT5 growth ledger belongs to a different or "
                        "unverifiable account and cannot establish this account's baseline."
                    ),
                }
            )
        elif growth_account_matches and not growth_balance_matches:
            conflicts.append(
                {
                    "code": "ACCOUNT_GROWTH_HISTORY_REFRESH_PENDING",
                    "detail": (
                        "The saved MT5 growth ledger is valid for this account, but the "
                        "broker balance moved. Last-reconciled values remain visible with "
                        "the unclassified balance delta until deal history refreshes."
                    ),
                }
            )

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "objective_account_established": status != "ACTIVE_ACCOUNT_NOT_ESTABLISHED",
        "authoritative_account_source": authoritative_source,
        "source_label": source_label,
        "source_detail": account_source_detail,
        "account": account,
        "open_exposure": open_exposure,
        "positions": positions,
        "position_protection": protection,
        "position_risk": position_risk,
        "execution": {
            "running": bool(loop.get("running")),
            "execution_active": bool(loop.get("execution_active")),
            "execution_lane": lane or None,
            "mode": loop.get("mode"),
            "bridge_class": bridge or None,
            "bridge_status": loop.get("last_bridge_selection_status"),
            "management_status": loop.get("last_management_status"),
            "management_detail": loop.get("last_management_detail"),
        },
        "snapshot": {
            "observed_at": mt5.get("snapshot_observed_at"),
            "age_seconds": mt5.get("snapshot_age_seconds"),
            "fresh": mt5.get("snapshot_fresh"),
            "cached": mt5.get("cached"),
            "terminal_connected": bool(mt5.get("connected")),
            "algo_order_send_ready": bool(_mapping(mt5.get("permission_state")).get("can_submit_order_send")),
        },
        "objective": {
            "north_star": "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH",
            "measurement_basis": (
                "Realized net account growth after spread, commission, swap, slippage, and losses, "
                "inside the owner's delegated authority."
            ),
            "daily_or_monthly_target_is_trade_quota": False,
            "target_deficit_can_manufacture_edge": False,
        },
        "growth_measurement": {
            "current_balance_usd": account.get("balance_usd"),
            "current_equity_usd": account.get("equity_usd"),
            "floating_pnl_usd": account.get("floating_pnl_usd"),
            "open_pnl_decomposition": {
                "price_pnl_usd": account.get("position_price_pnl_usd"),
                "swap_or_carry_usd": account.get("open_swap_usd"),
                "commission_usd": account.get("open_commission_usd"),
                "reported_components_usd": account.get(
                    "reported_open_components_usd"
                ),
                "account_net_open_pnl_usd": account.get("floating_pnl_usd"),
                "unattributed_open_pnl_usd": account.get(
                    "unattributed_open_pnl_usd"
                ),
                "interpretation": "NET_AFTER_REPORTED_OPEN_COSTS_NOT_REALIZED_PROFIT",
            },
            "current_balance_is_profit": False,
            "balance_baseline_status": (
                growth_baseline.get("status")
                if growth_reconciled
                else "PENDING_REFRESH_LAST_RECONCILED_BASELINE_AVAILABLE"
                if last_reconciled_available
                else "UNAVAILABLE_NO_RECONCILED_CASHFLOW_BASELINE"
            ),
            "period_realized_status": (
                growth.get("period_realized_status")
                if growth_reconciled
                else "PENDING_BROKER_HISTORY_RECONCILIATION"
                if last_reconciled_available
                else "SIMULATOR_DAILY_REALIZED_AVAILABLE"
                if authoritative_source == "simulator_account"
                and _number(simulator_daily.get("realized_pnl_usd")) is not None
                else "UNAVAILABLE_NO_PERIOD_RECONCILIATION"
            ),
            "realized_today_usd": (
                growth_realized.get("today_account_currency")
                if growth_reconciled
                else simulator_daily.get("realized_pnl_usd")
                if authoritative_source == "simulator_account"
                else None
            ),
            "realized_month_usd": (
                growth_realized.get("month_account_currency")
                if growth_reconciled
                else None
            ),
            "cashflow_adjusted_realized_growth_usd": (
                growth_realized.get("cashflow_adjusted_all_time_account_currency")
                if growth_reconciled
                else None
            ),
            "growth_pct_on_net_external_capital": (
                growth_realized.get("growth_pct_on_net_external_capital")
                if growth_reconciled
                else None
            ),
            "net_external_capital_flow_usd": (
                growth_baseline.get("net_external_capital_flow_account_currency")
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
                "ledger_balance_usd": (
                    growth_reconciliation.get("ledger_balance_account_currency")
                    if growth_account_matches
                    else None
                ),
                "balance_residual_usd": (
                    growth_reconciliation.get("balance_residual_account_currency")
                    if growth_account_matches
                    else None
                ),
            },
            "last_reconciled_growth": {
                "available": last_reconciled_available,
                "classification": (
                    "CURRENT_EXACT"
                    if growth_reconciled
                    else "LAST_RECONCILED_PENDING_CURRENT_BALANCE_CLASSIFICATION"
                    if last_reconciled_available
                    else "UNAVAILABLE"
                ),
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
                    growth_realized.get(
                        "cashflow_adjusted_all_time_account_currency"
                    )
                    if last_reconciled_available
                    else None
                ),
                "realized_today_usd": (
                    growth_realized.get("today_account_currency")
                    if last_reconciled_available
                    and growth_state.get("period_current")
                    else None
                ),
                "realized_month_usd": (
                    growth_realized.get("month_account_currency")
                    if last_reconciled_available
                    and growth_state.get("month_current")
                    else None
                ),
                "net_external_capital_flow_usd": (
                    growth_baseline.get(
                        "net_external_capital_flow_account_currency"
                    )
                    if last_reconciled_available
                    else None
                ),
                "period_utc_day": growth_state.get("period_utc_day"),
                "current_utc_day": growth_state.get("current_utc_day"),
            },
            "cas_bound_closed_outcomes": {
                "status": (
                    learning.get("status")
                    if learning_applies
                    else "UNAVAILABLE_FOR_SELECTED_ACCOUNT"
                ),
                "trades": learning_overall.get("trades") if learning_applies else None,
                "wins": learning_overall.get("wins") if learning_applies else None,
                "losses": learning_overall.get("losses") if learning_applies else None,
                "net_pnl_usd": learning_overall.get("net_pnl") if learning_applies else None,
                "scope": (
                    "CAS_BOUND_MT5_DEMO_OUTCOMES_ONLY"
                    if learning_applies
                    else "NOT_BOUND_TO_SELECTED_ACCOUNT"
                ),
            },
        },
        "secondary_simulator": {
            "authoritative_for_active_account": authoritative_source == "simulator_account",
            "status": health.get("status"),
            "account": simulator_account,
            "open_exposure": simulator_exposure,
            "source_health": simulator_source,
            "scope": "SEPARATE_PAPER_SIMULATOR_EVIDENCE",
        },
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "presentation_rules": [
            "Show account, balance, equity, floating P&L, and open positions from authoritative_account_source.",
            "Never add simulator P&L to MT5 P&L or call simulator balance the MT5 balance.",
            "Keep secondary simulator evidence visible only with an explicit non-authoritative label.",
            "A current balance snapshot is not realized profit without a reconciled cashflow baseline.",
            "Deposits, withdrawals, credits, and bonuses are capital flow, not trading profit.",
            "Use cashflow_adjusted_realized_growth_usd only when account and balance reconciliation are true.",
        ],
        "claim_boundary": (
            "Active account truth resolves source precedence for owner and Operator insight. "
            "It does not place or modify orders, move money, invent a profit baseline, "
            "authorize live trading, or weaken any execution gate. A realized-growth "
            "baseline is exposed only when broker deal history ties to current balance."
        ),
    }


__all__ = ["REPORT_KIND", "build_active_account_truth"]
