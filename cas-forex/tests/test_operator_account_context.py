from __future__ import annotations

from datetime import datetime, timezone

from cas_forex.operator_account_context import (
    build_operator_account_context,
    enrich_position_open_pnl,
    position_is_net_winning_after_reported_costs,
)
from cas_forex.mt5_account_growth import account_identity_hash


class _Bridge:
    login = 1000694
    server = "Hugosway-Demo"

    def is_demo_account(self):
        return True

    def get_account_info(self):
        return {
            "balance": 5000.0,
            "equity": 4999.0,
            "margin": 25.0,
            "margin_free": 4974.0,
            "leverage": 500,
        }


def test_position_price_winner_is_net_loser_after_reported_carry():
    position = {
        "ticket": 7001,
        "symbol": "US30",
        "type": "BUY",
        "profit": 1.25,
        "swap": -2.25,
        "commission": 0.0,
    }

    enriched = enrich_position_open_pnl(position)

    assert enriched["position_price_pnl_usd"] == 1.25
    assert enriched["swap_usd"] == -2.25
    assert enriched["commission_usd"] == 0.0
    assert enriched["net_open_pnl_after_reported_costs_usd"] == -1.0
    assert position_is_net_winning_after_reported_costs(position) is False


def test_operator_account_context_reconciles_position_costs_to_account_net():
    positions = [
        {"ticket": 7001, "profit": 1.25, "swap": -2.25},
        {"ticket": 7002, "profit": 3.0, "swap": -3.0},
    ]

    context = build_operator_account_context(_Bridge(), positions=positions)

    assert context["north_star"] == "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH"
    assert context["login"] == 1000694
    assert context["mode"] == "DEMO"
    assert context["balance"] == 5000.0
    assert context["equity"] == 4999.0
    assert context["position_price_pnl_usd"] == 4.25
    assert context["open_swap_usd"] == -5.25
    assert context["reported_open_components_usd"] == -1.0
    assert context["account_net_open_pnl_usd"] == -1.0
    assert context["unattributed_open_pnl_usd"] == 0.0
    assert context["current_balance_is_profit"] is False
    assert context["target_deficit_may_manufacture_trade_or_size"] is False


def test_operator_account_context_includes_only_matching_reconciled_growth():
    growth = {
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "generated_at": "2026-07-11T13:00:00+00:00",
        "event_hash": "growth-event-1",
        "refresh_status": "FULL_HISTORY_REFRESHED",
        "period_realized_status": "RECONCILED_MT5_ACCOUNT_HISTORY",
        "period": {"utc_day": "2026-07-11", "utc_month": "2026-07"},
        "account": {
            "account_id_hash": account_identity_hash(1000694, "Hugosway-Demo"),
            "current_balance_account_currency": 5000.0,
        },
        "baseline": {
            "status": "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY",
            "net_external_capital_flow_account_currency": 6000.0,
        },
        "realized_growth": {
            "cashflow_adjusted_all_time_account_currency": -1000.0,
            "today_account_currency": 25.0,
            "month_account_currency": -1000.0,
            "growth_pct_on_net_external_capital": -16.6667,
        },
        "reconciliation": {
            "ledger_ties_to_current_balance": True,
            "growth_components_tie": True,
        },
    }

    context = build_operator_account_context(
        _Bridge(),
        positions=[],
        growth_snapshot=growth,
        observed_at=datetime(2026, 7, 11, 13, 5, tzinfo=timezone.utc),
    )

    assert context["balance_baseline_status"] == "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY"
    assert context["cashflow_adjusted_realized_growth_usd"] == -1000.0
    assert context["realized_today_usd"] == 25.0
    assert context["net_external_capital_flow_usd"] == 6000.0
    assert context["account_growth_reconciliation"]["reconciled"] is True
    assert context["account_growth_reconciliation"]["period_current"] is True


def test_operator_account_context_withholds_previous_utc_day_realized_value():
    growth = {
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "generated_at": "2026-07-11T23:59:00+00:00",
        "period": {"timezone": "UTC", "utc_day": "2026-07-11"},
        "account": {
            "account_id_hash": account_identity_hash(1000694, "Hugosway-Demo"),
            "current_balance_account_currency": 5000.0,
        },
        "baseline": {
            "status": "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY",
        },
        "realized_growth": {"today_account_currency": -50.0},
        "reconciliation": {
            "ledger_ties_to_current_balance": True,
            "growth_components_tie": True,
        },
    }

    context = build_operator_account_context(
        _Bridge(),
        positions=[],
        growth_snapshot=growth,
        observed_at=datetime(2026, 7, 12, 0, 1, tzinfo=timezone.utc),
    )

    assert context["realized_today_usd"] is None
    assert context["account_growth_reconciliation"]["reconciled"] is False
    assert context["account_growth_reconciliation"]["period_utc_day"] == "2026-07-11"
    assert context["account_growth_reconciliation"]["current_utc_day"] == "2026-07-12"
    assert context["account_growth_reconciliation"]["period_current"] is False
