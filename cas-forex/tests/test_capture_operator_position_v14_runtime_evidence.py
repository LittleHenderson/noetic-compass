from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "capture_operator_position_v14_runtime_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("capture_operator_position_v14_runtime_evidence", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixtures():
    event_hash = "operator-event"
    decisions = []
    executions = []
    outcomes = []
    rows = [
        ("45945226", "SPX500", "close_full", "ref-close", -2.27),
        ("45945227", "XAUUSD", "trail_stop", "ref-trail", 1.00),
    ]
    for ticket, symbol, intent, action_ref, net_pnl in rows:
        decisions.append(
            {
                "position_key": f"ticket:{ticket}",
                "symbol": symbol,
                "decision": "SELECT",
                "intent": intent,
                "action_ref": action_ref,
                "growth_case": "NOT_APPLICABLE",
                "reason": "fixture",
            }
        )
        executions.append(
            {
                "status": "EXECUTED_RECONCILED",
                "broker_touched": True,
                "money_moved": False,
                "operator_position_edge_event_hash": event_hash,
                "execution_guard": {"status": "ACCEPT"},
                "broker_result": {"method": "close_position" if intent == "close_full" else "modify_position"},
                "terminal_receipt_status": "RECONCILED",
                "terminal_receipt": {"actual_remaining_volume": 0.0 if intent == "close_full" else None},
                "per_action_owner_confirmation_required": False,
                "selected_action": {
                    "broker_ticket": int(ticket),
                    "symbol": symbol,
                    "intent": intent,
                    "operator_action_ref": action_ref,
                    "requires_owner_confirmation": False,
                    "opened_at_iso": "2026-07-13T23:00:00+00:00",
                    "opened_at_source": "ORDER_ATTEMPT_BROKER_EXECUTION_RECEIPT",
                },
            }
        )
        outcomes.append(
            {
                "broker_ticket": ticket,
                "symbol": symbol,
                "direction": "LONG",
                "profile": "fixture_h1",
                "timeframe": "H1",
                "net_pnl": net_pnl,
            }
        )
    decision = {
        "prompt_version": "ai_operator_position_edge.v14",
        "status": "AI_OPERATOR_POSITION_DECIDED",
        "model_ok": True,
        "event_hash": event_hash,
        "model_response_normalization_count": 0,
        "operator_selected_count": 2,
        "operator_stand_down_count": 0,
        "decisions": decisions,
    }
    cycle = {
        "latest_cycle": {
            "status": "ACTIONS_EXECUTED",
            "operator_position_edge_prompt_version": "ai_operator_position_edge.v14",
            "per_action_owner_confirmation_required": False,
            "broker_touched": True,
            "terminal_effect_count": 2,
            "executions": executions,
        }
    }
    learning = {
        "status": "MT5_DEMO_LEARNING_BOUND",
        "broker_order_touched": False,
        "money_moved": False,
        "bound_trade_count": 40,
        "history_record_count": 48,
        "bound_outcomes": outcomes,
    }
    growth = {
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "event_hash": "growth-event",
        "account": {
            "account_mode": "demo",
            "server": "Hugosway-Demo",
            "currency": "USD",
            "current_balance_account_currency": 45041.59,
            "current_equity_account_currency": 45041.59,
        },
    }
    return decision, cycle, learning, growth


def test_build_evidence_preserves_natural_v14_decision_execution_and_outcomes():
    module = _load_module()
    decision, cycle, learning, growth = _fixtures()
    report = module.build_evidence(
        decision=decision,
        cycle_state=cycle,
        learning=learning,
        growth=growth,
        source_records={},
        generated_at="2026-07-13T23:30:00+00:00",
    )

    assert report["status"] == "PASS_NATURAL_V14_POSITION_MANAGEMENT_RECEIPT"
    assert report["operator_decision"]["event_hash"] == "operator-event"
    assert [row["intent"] for row in report["executions"]] == ["close_full", "trail_stop"]
    assert report["cycle_net_pnl"] == -1.27
    assert report["capture_controls"] == {
        "capture_order_send_called": False,
        "capture_broker_write_called": False,
        "capture_money_moved": False,
        "historical_runtime_broker_touched": True,
        "historical_runtime_money_moved": False,
    }
    assert len(report["event_hash"]) == 64


def test_build_evidence_rejects_unbound_or_noncanonical_execution():
    module = _load_module()
    decision, cycle, learning, growth = _fixtures()
    cycle["latest_cycle"]["executions"][0]["selected_action"]["operator_action_ref"] = "different-ref"

    with pytest.raises(ValueError, match="exact action_ref drifted"):
        module.build_evidence(
            decision=decision,
            cycle_state=cycle,
            learning=learning,
            growth=growth,
            source_records={},
        )
