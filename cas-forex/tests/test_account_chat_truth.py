from __future__ import annotations

from cas_forex.account_chat_truth import (
    asks_active_account_truth,
    compose_active_account_chat_reply,
    project_active_account_chat_truth,
)


def _active_report() -> dict:
    return {
        "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
        "objective_account_established": True,
        "authoritative_account_source": "mt5_account_snapshot",
        "account": {
            "login": 1000694,
            "server": "Hugosway-Demo",
            "currency": "USD",
            "is_demo": True,
            "balance_usd": 45080.90,
            "equity_usd": 45110.36,
            "floating_pnl_usd": 29.46,
            "position_price_pnl_usd": 32.71,
            "open_swap_usd": -3.25,
            "open_commission_usd": 0.0,
            "unattributed_open_pnl_usd": 0.0,
            "margin_used_usd": 200.12,
            "free_margin_usd": 44910.24,
        },
        "open_exposure": {
            "open_position_count": 6,
            "open_lots": 0.06,
            "protected_position_count": 6,
            "unprotected_position_count": 0,
        },
        "snapshot": {
            "observed_at": "2026-07-14T19:00:34+00:00",
            "age_seconds": 1.2,
            "fresh": True,
            "terminal_connected": True,
            "algo_order_send_ready": True,
        },
        "growth_measurement": {
            "balance_baseline_status": "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY",
            "cashflow_adjusted_realized_growth_usd": -54919.10,
            "realized_today_usd": 39.41,
            "realized_month_usd": -54918.97,
            "net_external_capital_flow_usd": 100000.0,
            "current_balance_is_profit": False,
            "account_growth_reconciliation": {"reconciled": True},
            "open_pnl_decomposition": {
                "price_pnl_usd": 32.71,
                "swap_or_carry_usd": -3.25,
                "commission_usd": 0.0,
                "account_net_open_pnl_usd": 29.46,
                "unattributed_open_pnl_usd": 0.0,
            },
        },
        "secondary_simulator": {
            "authoritative_for_active_account": False,
            "scope": "SEPARATE_PAPER_SIMULATOR_EVIDENCE",
            "account": {"balance_usd": 5000.0},
        },
    }


def test_account_truth_classifier_targets_current_metrics_without_stealing_compound_copy():
    assert asks_active_account_truth("What is our current account balance and equity?")
    assert asks_active_account_truth("Why hasn't the floating P&L changed?")
    assert asks_active_account_truth("How much have we made today?")
    assert not asks_active_account_truth("Explain balance-sheet accounting in general")
    assert not asks_active_account_truth("Should the Operator compound this winning trade?")


def test_projection_keeps_active_account_and_secondary_evidence_separate():
    projection = project_active_account_chat_truth(
        _active_report(),
        simulator_evidence={
            "scope": "PAPER_SIMULATOR_PERFORMANCE",
            "honest_paper_balance_usd": 3040.87,
            "balance_growth_net_pnl_usd": 1040.87,
        },
    )

    assert projection["account"]["login"] == 1000694
    assert projection["account"]["balance_usd"] == 45080.90
    assert projection["open_exposure"]["open_position_count"] == 6
    assert projection["growth_measurement"]["cashflow_adjusted_realized_growth_usd"] == -54919.10
    assert projection["growth_measurement"]["open_pnl_decomposition"] == {
        "price_pnl_usd": 32.71,
        "swap_or_carry_usd": -3.25,
        "commission_usd": 0.0,
        "account_net_open_pnl_usd": 29.46,
        "unattributed_open_pnl_usd": 0.0,
    }
    assert projection["secondary_evidence"]["simulator_ledger_balance_usd"] == 5000.0
    assert projection["secondary_evidence"]["performance_evidence_balance_usd"] == 3040.87
    assert projection["secondary_evidence"]["authoritative_for_active_account"] is False
    assert len(projection["evidence_fingerprint"]) == 64


def test_reply_reports_after_cost_growth_and_simulator_separation_exactly():
    projection = project_active_account_chat_truth(
        _active_report(),
        simulator_evidence={
            "scope": "PAPER_SIMULATOR_PERFORMANCE",
            "honest_paper_balance_usd": 3040.87,
            "balance_growth_net_pnl_usd": 1040.87,
        },
    )

    reply = compose_active_account_chat_reply(projection)

    assert "MT5 demo #1000694 on Hugosway-Demo" in reply
    assert "Balance $45,080.90; equity $45,110.36; open positions 6" in reply
    assert "Net open P&L after reported costs +$29.46" in reply
    assert "price P&L +$32.71" in reply
    assert "swap/carry -$3.25" in reply
    assert "commission $0.00" in reply
    assert "all time -$54,919.10, today +$39.41" in reply
    assert "External capital $100,000.00 is excluded from profit" in reply
    assert "simulator ledger balance $5,000.00" in reply
    assert "replay/performance balance $3,040.87 with net P&L +$1,040.87" in reply
    assert "Neither is added to the active MT5 account" in reply
    assert "This chat placed no order, changed no dial, and moved no money" in reply


def test_unavailable_projection_refuses_to_guess():
    reply = compose_active_account_chat_reply(project_active_account_chat_truth(None))
    assert "unavailable" in reply
    assert "will not guess" in reply


def test_pending_growth_reply_preserves_last_reconciled_values_without_guessing_delta():
    report = _active_report()
    report["growth_measurement"].update(
        {
            "balance_baseline_status": "PENDING_REFRESH_LAST_RECONCILED_BASELINE_AVAILABLE",
            "period_realized_status": "PENDING_BROKER_HISTORY_RECONCILIATION",
            "cashflow_adjusted_realized_growth_usd": None,
            "realized_today_usd": None,
            "realized_month_usd": None,
            "net_external_capital_flow_usd": None,
            "account_growth_reconciliation": {
                "reconciled": False,
                "truth_status": "PENDING_BROKER_HISTORY_RECONCILIATION",
            },
            "last_reconciled_growth": {
                "available": True,
                "generated_at": "2026-07-14T19:53:06+00:00",
                "pending_balance_delta_usd": -2.40,
                "cashflow_adjusted_realized_growth_usd": -54945.79,
                "realized_today_usd": 12.72,
                "realized_month_usd": -54945.66,
                "net_external_capital_flow_usd": 100000.0,
            },
        }
    )

    projection = project_active_account_chat_truth(report)
    reply = compose_active_account_chat_reply(projection)

    assert "Broker-history refresh pending" in reply
    assert "Last reconciled at 2026-07-14T19:53:06+00:00" in reply
    assert "all time -$54,945.79, today +$12.72" in reply
    assert "differs from that reconciled snapshot by -$2.40" in reply
    assert "not being guessed as trading profit, loss, deposit, or withdrawal" in reply
