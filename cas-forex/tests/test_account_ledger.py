import pytest

from cas_forex.account_ledger import (
    AccountLedgerEvent,
    assert_account_ledger_boundary,
    build_account_ledger_from_paper_review,
    build_paper_account_ledger,
)


def _risk_review(account_equity=5000.0):
    return {
        "plan_id": "plan-1",
        "lead_id": "lead-1",
        "strategy_setting": "setting-1",
        "date": "2026-06-23",
        "review_id": "review-1",
        "account_equity": account_equity,
        "route_action": "ROUTE_PAPER_SIGNAL",
        "total_planned_risk_usd": 25.30,
        "sizing": [
            {
                "symbol": "US30",
                "direction": "LONG",
                "entry_price": 51745.87,
                "stop_loss": 50485.56,
                "take_profit": 58047.44,
                "sized_lots": 0.01,
                "proposal_id": "proposal-us30",
                "attempt_status": "PAPER_ATTEMPT_ALLOWED",
            }
        ],
    }


def _decision():
    return {
        "plan_id": "plan-1",
        "lead_id": "lead-1",
        "strategy_setting": "setting-1",
        "date": "2026-06-23",
        "route_action": "ROUTE_PAPER_SIGNAL",
        "symbol_decisions": [{"symbol": "US30", "action": "ROUTE_PAPER_SIGNAL"}],
    }


def test_paper_account_ledger_accepts_any_positive_initial_investment():
    ledger = build_paper_account_ledger(
        initial_investment_usd=1234.56,
        plan_id="plan-1",
        lead_id="lead-1",
        strategy_setting="setting-1",
        as_of_date="2026-06-23",
        planned_risk_usd=12.34,
    )

    assert ledger.summary.initial_investment_usd == 1234.56
    assert ledger.summary.deposit_usd == 1234.56
    assert ledger.summary.balance_usd == 1234.56
    assert ledger.summary.equity_usd == 1234.56
    assert ledger.summary.free_margin_usd == 1234.56
    assert ledger.cashflow_events[0].ledger_id.startswith("ledger-")
    assert ledger.supported_history_tabs == ("Positions", "Orders", "Deals")
    assert ledger.supported_time_filters == ("Seconds", "Minutes", "Hour", "Day", "Week", "Month", "Custom")
    assert ledger.live_money_authorized is False
    assert ledger.payment_movement_authorized is False
    assert_account_ledger_boundary(ledger)


@pytest.mark.parametrize("amount", [0, -1])
def test_paper_account_ledger_rejects_non_positive_initial_investment(amount):
    with pytest.raises(ValueError, match="initial_investment_usd must be positive"):
        build_paper_account_ledger(
            initial_investment_usd=amount,
            plan_id="plan-1",
            lead_id="lead-1",
            strategy_setting="setting-1",
            as_of_date="2026-06-23",
        )


def test_paper_account_ledger_rejects_external_money_movement_claims():
    bad = AccountLedgerEvent(
        ledger_id="ledger-bad",
        event_type="deposit",
        timestamp="2026-06-23T00:00:00Z",
        amount_usd=100,
        balance_delta_usd=100,
        equity_delta_usd=100,
        external_money_movement=True,
    )
    with pytest.raises(ValueError, match="external money movement"):
        build_paper_account_ledger(
            initial_investment_usd=5000,
            plan_id="plan-1",
            lead_id="lead-1",
            strategy_setting="setting-1",
            as_of_date="2026-06-23",
            cashflow_events=(bad,),
        )


def test_build_account_ledger_from_risk_review_populates_terminal_rows_and_recalc_flag():
    ledger = build_account_ledger_from_paper_review(
        _risk_review(account_equity=5000.0),
        initial_investment_usd=2500.0,
        decision=_decision(),
        evidence_refs=("risk.json", "decision.json"),
    )

    assert ledger.summary.initial_investment_usd == 2500.0
    assert ledger.summary.risk_review_account_equity_usd == 5000.0
    assert ledger.summary.requires_new_risk_review_for_selected_investment is True
    assert ledger.summary.planned_risk_usd == 25.30
    assert ledger.summary.planned_risk_pct_of_selected_equity == 1.012
    assert len(ledger.positions) == 1
    assert len(ledger.orders) == 1
    assert len(ledger.deals) == 0
    row = ledger.positions[0]
    assert row.symbol == "US30"
    assert row.lot_size == 0.01
    assert row.broker_ticket is None
    assert row.simulator_ticket.startswith("sim-")
    assert row.evidence_packet_id == "review-1"
    assert any(event.event_type == "paper_order_intent" for event in ledger.cashflow_events)
    assert_account_ledger_boundary(ledger)
