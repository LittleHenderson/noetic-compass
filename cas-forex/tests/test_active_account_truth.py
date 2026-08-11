from __future__ import annotations

from datetime import datetime, timezone

from cas_forex.active_account_truth import build_active_account_truth
from cas_forex.mt5_account_growth import account_identity_hash


def _mt5_snapshot() -> dict:
    return {
        "connected": True,
        "is_demo": True,
        "cached": True,
        "snapshot_observed_at": "2026-07-11T10:00:00+00:00",
        "snapshot_age_seconds": 1.5,
        "snapshot_fresh": True,
        "account": {
            "login": 1000694,
            "server": "Hugosway-Demo",
            "currency": "USD",
            "leverage": 500,
            "balance_usd": 44757.89,
            "equity_usd": 44555.70,
            "floating_pnl_usd": -202.19,
            "margin_used_usd": 411.75,
            "free_margin_usd": 44143.95,
        },
        "positions": [
            {
                "ticket": 1,
                "symbol": "US30",
                "lots": 0.01,
                "stop_loss": 52734.75,
                "floating_pnl_usd": -97.57,
                "swap_usd": -7.60,
            },
            {
                "ticket": 2,
                "symbol": "NAS100",
                "lots": 0.02,
                "stop_loss": 29883.78,
                "floating_pnl_usd": -91.37,
                "swap_usd": -5.65,
            },
        ],
        "open_position_count": 2,
        "permission_state": {"can_submit_order_send": True},
        "position_protection": {
            "protected_position_count": 2,
            "unprotected_position_count": 0,
        },
        "position_risk": {
            "risk_cap_breach_count": 2,
            "risk_cap_pct": 0.1,
            "combined_entry_to_stop_risk_usd": 268.72,
            "combined_entry_to_stop_risk_pct_equity": 0.6031,
            "combined_remaining_to_stop_drawdown_usd": 79.78,
        },
    }


def _mt5_dispatch() -> dict:
    return {
        "running": True,
        "execution_active": True,
        "execution_lane": "PAPER",
        "mode": "PAPER_FALLBACK",
        "last_bridge_class": "MT5Bridge",
        "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        "last_management_status": "WATCHING_MARKET_CLOSED",
    }


def _simulator_health() -> dict:
    return {
        "status": "OBSERVING",
        "account": {
            "currency": "USD",
            "balance_usd": 5000.0,
            "equity_usd": 5000.0,
            "floating_pnl_usd": 0.0,
            "free_margin_usd": 5000.0,
        },
        "open_exposure": {
            "open_position_count": 0,
            "open_lots": 0.0,
            "unprotected_position_count": 0,
            "protective_order_coverage_pct": 100.0,
        },
        "source_health": {
            "static_simulation_active": True,
            "price_source_status": "STATIC_SIMULATION_FALLBACK",
        },
    }


def _account_growth(*, balance: float = 44757.89, login: int = 1000694) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "report_kind": "cas_forex_mt5_account_growth",
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "generated_at": "2026-07-11T13:00:00+00:00",
        "event_hash": "growth-event-1",
        "refresh_status": "FULL_HISTORY_REFRESHED",
        "period_realized_status": "RECONCILED_MT5_ACCOUNT_HISTORY",
        "period": {
            "utc_day": now.date().isoformat(),
            "utc_month": now.strftime("%Y-%m"),
        },
        "account": {
            "account_id_hash": account_identity_hash(login, "Hugosway-Demo"),
            "current_balance_account_currency": balance,
        },
        "baseline": {
            "status": "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY",
            "net_external_capital_flow_account_currency": 100000.0,
        },
        "realized_growth": {
            "cashflow_adjusted_all_time_account_currency": -55242.11,
            "today_account_currency": -12.34,
            "month_account_currency": -55242.11,
            "growth_pct_on_net_external_capital": -55.2421,
        },
        "reconciliation": {
            "ledger_ties_to_current_balance": True,
            "growth_components_tie": True,
            "ledger_balance_account_currency": balance,
            "balance_residual_account_currency": 0.0,
        },
    }


def test_active_mt5_demo_account_overrides_secondary_simulator_story():
    report = build_active_account_truth(
        mt5_snapshot=_mt5_snapshot(),
        dispatch_loop=_mt5_dispatch(),
        simulator_health=_simulator_health(),
        demo_learning={
            "status": "MT5_DEMO_LEARNING_BOUND",
            "learning_overall": {"trades": 4, "wins": 1, "losses": 3, "net_pnl": -6.77},
        },
    )

    assert report["status"] == "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
    assert report["authoritative_account_source"] == "mt5_account_snapshot"
    assert report["source_label"] == "MT5 DEMO"
    assert report["account"]["login"] == 1000694
    assert report["account"]["balance_usd"] == 44757.89
    assert report["account"]["position_price_pnl_usd"] == -188.94
    assert report["account"]["open_swap_usd"] == -13.25
    assert report["account"]["reported_open_components_usd"] == -202.19
    assert report["account"]["unattributed_open_pnl_usd"] == 0.0
    assert report["open_exposure"]["open_position_count"] == 2
    assert report["open_exposure"]["open_lots"] == 0.03
    assert report["open_exposure"]["risk_cap_breach_count"] == 2
    assert report["growth_measurement"]["cas_bound_closed_outcomes"]["net_pnl_usd"] == -6.77
    assert report["objective"]["north_star"] == "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH"
    assert report["objective"]["daily_or_monthly_target_is_trade_quota"] is False
    assert report["growth_measurement"]["current_balance_is_profit"] is False
    assert report["growth_measurement"]["open_pnl_decomposition"] == {
        "price_pnl_usd": -188.94,
        "swap_or_carry_usd": -13.25,
        "commission_usd": 0.0,
        "reported_components_usd": -202.19,
        "account_net_open_pnl_usd": -202.19,
        "unattributed_open_pnl_usd": 0.0,
        "interpretation": "NET_AFTER_REPORTED_OPEN_COSTS_NOT_REALIZED_PROFIT",
    }
    assert report["growth_measurement"]["realized_today_usd"] is None
    assert report["secondary_simulator"]["account"]["balance_usd"] == 5000.0
    assert report["secondary_simulator"]["authoritative_for_active_account"] is False
    codes = {row["code"] for row in report["conflicts"]}
    assert "SECONDARY_SIMULATOR_POSITION_COUNT_DIFFERS_FROM_MT5" in codes
    assert "SECONDARY_SIMULATOR_BALANCE_DIFFERS_FROM_MT5" in codes
    assert "STATIC_SIMULATION_IS_SECONDARY_DIAGNOSTIC" in codes


def test_connected_mt5_stays_owner_facing_when_dispatch_is_paused():
    dispatch = _mt5_dispatch()
    dispatch.update({"running": False, "execution_active": False})

    report = build_active_account_truth(
        mt5_snapshot=_mt5_snapshot(),
        dispatch_loop=dispatch,
        simulator_health=_simulator_health(),
    )

    assert report["status"] == "CONNECTED_MT5_DEMO_ACCOUNT_OBSERVATIONAL"
    assert report["authoritative_account_source"] == "mt5_account_snapshot"
    assert report["account"]["equity_usd"] == 44555.70


def test_active_mt5_uses_matching_cashflow_adjusted_growth_baseline():
    report = build_active_account_truth(
        mt5_snapshot=_mt5_snapshot(),
        dispatch_loop=_mt5_dispatch(),
        simulator_health=_simulator_health(),
        account_growth=_account_growth(),
    )

    growth = report["growth_measurement"]
    assert growth["balance_baseline_status"] == "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY"
    assert growth["cashflow_adjusted_realized_growth_usd"] == -55242.11
    assert growth["realized_today_usd"] == -12.34
    assert growth["realized_month_usd"] == -55242.11
    assert growth["net_external_capital_flow_usd"] == 100000.0
    assert growth["current_balance_is_profit"] is False
    assert growth["account_growth_reconciliation"]["reconciled"] is True


def test_active_mt5_rejects_growth_snapshot_from_other_account_or_balance():
    report = build_active_account_truth(
        mt5_snapshot=_mt5_snapshot(),
        dispatch_loop=_mt5_dispatch(),
        simulator_health=_simulator_health(),
        account_growth=_account_growth(login=2000000),
    )

    growth = report["growth_measurement"]
    assert growth["balance_baseline_status"] == "UNAVAILABLE_NO_RECONCILED_CASHFLOW_BASELINE"
    assert growth["cashflow_adjusted_realized_growth_usd"] is None
    assert growth["account_growth_reconciliation"]["account_matches"] is False
    assert "ACCOUNT_GROWTH_HISTORY_ACCOUNT_MISMATCH" in {
        row["code"] for row in report["conflicts"]
    }


def test_active_mt5_keeps_last_reconciled_growth_visible_while_balance_refreshes():
    report = build_active_account_truth(
        mt5_snapshot=_mt5_snapshot(),
        dispatch_loop=_mt5_dispatch(),
        simulator_health=_simulator_health(),
        account_growth=_account_growth(balance=44760.0),
    )

    growth = report["growth_measurement"]
    assert growth["cashflow_adjusted_realized_growth_usd"] is None
    assert growth["period_realized_status"] == "PENDING_BROKER_HISTORY_RECONCILIATION"
    assert growth["account_growth_reconciliation"]["reconciled"] is False
    assert growth["account_growth_reconciliation"]["last_reconciled_available"] is True
    assert growth["account_growth_reconciliation"]["pending_balance_delta_usd"] == -2.11
    assert growth["last_reconciled_growth"] == {
        "available": True,
        "classification": "LAST_RECONCILED_PENDING_CURRENT_BALANCE_CLASSIFICATION",
        "generated_at": "2026-07-11T13:00:00+00:00",
        "event_hash": "growth-event-1",
        "reconciled_balance_usd": 44760.0,
        "current_balance_usd": 44757.89,
        "pending_balance_delta_usd": -2.11,
        "cashflow_adjusted_realized_growth_usd": -55242.11,
        "realized_today_usd": -12.34,
        "realized_month_usd": -55242.11,
        "net_external_capital_flow_usd": 100000.0,
        "period_utc_day": datetime.now(timezone.utc).date().isoformat(),
        "current_utc_day": datetime.now(timezone.utc).date().isoformat(),
    }
    assert "ACCOUNT_GROWTH_HISTORY_REFRESH_PENDING" in {
        row["code"] for row in report["conflicts"]
    }


def test_active_simulator_lane_does_not_merge_connected_mt5_account():
    dispatch = {
        "running": True,
        "execution_active": True,
        "execution_lane": "PAPER",
        "last_bridge_class": "SimulatedBrokerBridge",
    }

    report = build_active_account_truth(
        mt5_snapshot=_mt5_snapshot(),
        dispatch_loop=dispatch,
        simulator_health=_simulator_health(),
    )

    assert report["status"] == "PRIMARY_SIMULATOR_ACCOUNT_ACTIVE"
    assert report["authoritative_account_source"] == "simulator_account"
    assert report["account"]["balance_usd"] == 5000.0
    assert report["secondary_simulator"]["authoritative_for_active_account"] is True


def test_missing_account_sources_remain_explicitly_unestablished():
    report = build_active_account_truth(
        mt5_snapshot={"connected": False},
        dispatch_loop={"running": False, "execution_active": False},
        simulator_health={},
    )

    assert report["status"] == "ACTIVE_ACCOUNT_NOT_ESTABLISHED"
    assert report["objective_account_established"] is False
    assert report["account"]["balance_usd"] is None
