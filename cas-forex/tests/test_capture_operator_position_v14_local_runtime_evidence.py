from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.capture_operator_position_v14_local_runtime_evidence import build_evidence


def _fixtures():
    action_ref = "position-action-local-proof"
    event_hash = "operator-event-local-proof"
    decision = {
        "report_kind": "cas_forex_ai_operator_position_edge",
        "status": "AI_OPERATOR_POSITION_DECIDED",
        "prompt_version": "ai_operator_position_edge.v14",
        "model_ok": True,
        "provider": "local-fallback",
        "provider_label": "Local model (deepseek-r1:latest)",
        "model_ref": "deepseek-r1:latest",
        "model_backend": "ollama",
        "model_prompt_chars": 20000,
        "raw_response_chars": 500,
        "model_response_normalization_count": 0,
        "model_context_projection": {"full_context_retained_in_audit": True},
        "event_hash": event_hash,
        "decisions": [
            {
                "position_key": "ticket:45945233",
                "decision": "SELECT",
                "action_ref": action_ref,
                "intent": "close_full",
                "growth_case": "NOT_APPLICABLE",
                "reason": "Realize the current after-cost profit.",
            }
        ],
    }
    execution = {
        "status": "EXECUTED_RECONCILED",
        "broker_touched": True,
        "money_moved": False,
        "per_action_owner_confirmation_required": False,
        "execution_guard": {"status": "ACCEPT"},
        "broker_result": {"method": "close_position"},
        "terminal_receipt_status": "RECONCILED",
        "terminal_receipt": {"actual_remaining_volume": 0.0},
        "selected_action": {
            "broker_ticket": 45945233,
            "symbol": "XAUUSD",
            "intent": "close_full",
            "operator_action_ref": action_ref,
            "operator_event_hash": event_hash,
            "operator_growth_case": "NOT_APPLICABLE",
        },
    }
    outcome = {
        "broker_ticket": "45945233",
        "symbol": "XAU/USD",
        "direction": "SHORT",
        "profile": "live_candle_index-tsmom-126-d1_h1",
        "timeframe": "H1",
        "open_time": "2026-07-14T00:00:46+00:00",
        "close_time": "2026-07-14T00:21:20+00:00",
        "close_reason": "MT5_HISTORY_CLOSE:CAS_CLOSE",
        "gross_profit": 12.47,
        "commission": -0.05,
        "swap": 0.0,
        "net_pnl": 12.42,
        "admission_stop_risk_usd": 25.79,
        "realized_after_cost_r_multiple": 0.481582,
    }
    learning = {
        "status": "MT5_DEMO_LEARNING_BOUND",
        "bound_trade_count": 42,
        "history_record_count": 50,
        "broker_order_touched": False,
        "money_moved": False,
        "bound_outcomes": [outcome],
    }
    growth = {
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "event_hash": "growth-event",
        "account": {
            "account_mode": "demo",
            "server": "Hugosway-Demo",
            "currency": "USD",
            "current_balance_account_currency": 45053.91,
            "current_equity_account_currency": 45053.91,
        },
    }
    return decision, execution, learning, growth


def test_build_evidence_binds_local_decision_execution_and_after_cost_outcome():
    decision, execution, learning, growth = _fixtures()

    report = build_evidence(
        decision=decision,
        executions=[execution],
        learning=learning,
        growth=growth,
        source_records={},
        generated_at="2026-07-14T00:30:00+00:00",
    )

    assert report["status"] == "PASS_LOCAL_V14_POSITION_MANAGEMENT_RECEIPT"
    assert report["operator_decision"]["provider"] == "local-fallback"
    assert report["execution"]["execution_status"] == "EXECUTED_RECONCILED"
    assert report["execution"]["guard_status"] == "ACCEPT"
    assert report["execution"]["per_action_owner_confirmation_required"] is False
    assert report["bound_outcome"]["net_pnl"] == 12.42
    assert report["bound_outcome"]["realized_after_cost_r_multiple"] == 0.481582
    assert report["capture_controls"]["capture_broker_write_called"] is False
    assert len(report["event_hash"]) == 64


def test_build_evidence_rejects_nonlocal_or_unbound_execution():
    decision, execution, learning, growth = _fixtures()
    decision = deepcopy(decision)
    decision["provider"] = "frontier_anthropic"

    with pytest.raises(ValueError, match="local provider"):
        build_evidence(
            decision=decision,
            executions=[execution],
            learning=learning,
            growth=growth,
            source_records={},
        )
