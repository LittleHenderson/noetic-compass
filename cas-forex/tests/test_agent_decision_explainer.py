"""Tests for cas_forex.agent_decision_explainer.

The explainer walks the CAS Forex agent's past decision into a structured
explanation the LLM cockpit bot can surface. It must NEVER fabricate, NEVER
read from disk, and NEVER recommend a future trade.
"""

from __future__ import annotations

import pytest

from cas_forex.agent_decision_explainer import (
    AgentDecisionExplanation,
    DecisionChainStep,
    explain_latest_agent_decision,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_intent(
    *,
    intent_id: str = "intent-001",
    strategy_setting: str = "micro_scalp_v3",
    symbol: str = "EURUSD",
    timeframe: str = "M1",
    direction: str = "BUY",
    entry: float = 1.0850,
    stop_loss: float = 1.0830,
    take_profit: float = 1.0890,
    lot_size: float = 0.01,
    confidence: float = 0.72,
    reason: str = "M1 momentum lead matched live regime cluster.",
) -> dict:
    return {
        "intent_id": intent_id,
        "agent_id": "micro_scalp_agent",
        "action": direction,
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy_setting": strategy_setting,
        "direction": direction,
        "confidence": confidence,
        "evidence_score": 0.66,
        "lot_size": lot_size,
        "entry_price": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reason": reason,
        "evidence_refs": ["forex_fury_replay::r-001"],
        "order_request": {"symbol": symbol, "volume": lot_size},
        "status": "PROPOSED",
    }


def _make_decision(
    *,
    intent_id: str = "intent-001",
    approved: bool = True,
    decision: str = "APPROVE",
    reasons: list[str] | None = None,
) -> dict:
    return {
        "decision_id": f"dec-{intent_id}",
        "intent_id": intent_id,
        "agent_id": "overseer_agent",
        "decision": decision,
        "approved": approved,
        "reasons": reasons or ["No conflicting position; risk under cap."],
        "command_ready": approved,
        "timestamp": "2026-06-24T10:00:00+00:00",
    }


def _make_terminal_command(
    *,
    intent_id: str = "intent-001",
    broker_ticket: str = "PAPER-MT5-12345",
    status: str = "EXECUTED",
    filled_price: float = 1.0851,
) -> dict:
    return {
        "command_id": "cmd-001",
        "command_type": "PLACE_ORDER",
        "broker_mode": "PAPER_MT5",
        "command_status": "MT5_DEMO_ORDER_EXECUTED",
        "intent_id": intent_id,
        "agent_id": "micro_scalp_agent",
        "symbol": "EURUSD",
        "timeframe": "M1",
        "terminal_receipt": {
            "receipt_id": f"mt5-receipt-{broker_ticket}",
            "command_id": "cmd-001",
            "intent_id": intent_id,
            "agent_id": "micro_scalp_agent",
            "broker_mode": "PAPER_MT5",
            "status": status,
            "lifecycle_status": "RECEIPT_VERIFIED",
            "broker_ticket": broker_ticket,
            "filled_price": filled_price,
            "filled_volume": 0.01,
        },
    }


def _make_cycle_report(
    *,
    intents: list[dict] | None = None,
    decisions: list[dict] | None = None,
    terminal_commands: list[dict] | None = None,
    cycle_id: str = "agent-cycle-abc123",
) -> dict:
    intents = intents if intents is not None else [_make_intent()]
    decisions = decisions if decisions is not None else [_make_decision()]
    terminal_commands = terminal_commands or []
    return {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": cycle_id,
        "created_at": "2026-06-24T10:00:00+00:00",
        "trigger_source": "TEST",
        "summary": {"route_intent_count": len(intents)},
        "agent_heartbeats": [],
        "route_intents": intents,
        "overseer_decisions": decisions,
        "terminal_commands": terminal_commands,
        "memory_snapshots": [],
        "claim_boundary": "Agent workflow cycles do not by themselves execute live broker orders.",
    }


def _make_strategy_dev_queue() -> dict:
    return {
        "work_items": [
            {
                "item_id": "strategy-dev-micro-scalp-aaaa",
                "item_type": "STRATEGY_REPLAY_REQUEST",
                "strategy_setting": "micro_scalp_v3",
                "symbols": ["EURUSD"],
                "timeframes": ["M1"],
                "family": "micro_scalp_v3",
                "hypothesis": "M1 momentum bursts in the London open carry edge after spread filter.",
                "plain_english_goal": "Confirm the M1 micro-scalp lead before scaling lot size.",
            }
        ]
    }


def _make_walk_forward_report(
    *,
    verdict: str = "PASS",
    score: float = 0.62,
    sample_size: int = 240,
) -> dict:
    return {
        "summary": {
            "verdict": verdict,
            "score": score,
            "sample_size": sample_size,
            "sharpe": 1.4,
            "win_rate": 0.58,
        }
    }


def _make_memory_report_with_pnl(
    *,
    intent_id: str = "intent-001",
    pnl: float = 4.25,
) -> dict:
    return {
        "memory_records": [
            {
                "memory_id": "mem-001",
                "intent_id": intent_id,
                "outcome_label": "TRADE_CLOSED_PROFIT",
                "profit_loss_account": pnl,
                "evidence_refs": [f"intent::{intent_id}"],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_inputs_returns_no_recent_decision():
    """Test 1: No inputs at all → overall_status='no_recent_decision'."""
    result = explain_latest_agent_decision()
    assert isinstance(result, AgentDecisionExplanation)
    assert result.cycle_id is None
    assert result.overall_status == "no_recent_decision"
    assert len(result.chain) == 5
    assert all(isinstance(step, DecisionChainStep) for step in result.chain)
    # All five steps missing.
    assert {step.status for step in result.chain} == {"missing"}
    # Plain English must explain why.
    summary = result.plain_english_summary.lower()
    assert "no recent" in summary or "no agent" in summary or "run an agent cycle" in summary
    assert result.next_action_hint is not None
    assert "agent" in result.next_action_hint.lower()


def test_executed_trade_walks_full_chain():
    """Test 2: Cycle with executed trade → all five chain steps found, overall_status='executed'."""
    cycle = _make_cycle_report(terminal_commands=[_make_terminal_command()])
    memory = _make_memory_report_with_pnl()
    strategy_q = _make_strategy_dev_queue()
    walk_forward = _make_walk_forward_report()

    result = explain_latest_agent_decision(
        agent_cycle_report=cycle,
        agent_memory_report=memory,
        strategy_dev_queue_report=strategy_q,
        walk_forward_report=walk_forward,
    )

    assert result.overall_status == "executed"
    assert result.cycle_id == "agent-cycle-abc123"
    step_names = [s.name for s in result.chain]
    assert step_names == [
        "strategy_lead",
        "walk_forward_evidence",
        "pcba_gate_verdict",
        "cycle_decision",
        "execution_outcome",
    ]
    # Strategy + walk-forward + cycle + execution must be found.
    assert result.chain[0].status == "found"
    assert result.chain[1].status == "found"
    assert result.chain[3].status == "found"
    assert result.chain[4].status == "found"
    # PCBA step is found (no PCBA-block reason and overseer approved).
    assert result.chain[2].status == "found"
    # Execution step references the broker ticket.
    exec_evidence = " ".join(result.chain[4].evidence)
    assert "PAPER-MT5-12345" in exec_evidence
    assert "close_pnl_account=4.25" in exec_evidence
    # Strategy step quotes the hypothesis.
    strategy_evidence = " ".join(result.chain[0].evidence)
    assert "micro_scalp_v3" in strategy_evidence
    assert "hypothesis" in strategy_evidence.lower()


def test_approved_intent_without_receipt_is_approved_not_executed():
    """Test 3: Approved intent but no terminal receipt → 'approved_not_executed'."""
    cycle = _make_cycle_report(terminal_commands=[])
    result = explain_latest_agent_decision(
        agent_cycle_report=cycle,
        walk_forward_report=_make_walk_forward_report(),
        strategy_dev_queue_report=_make_strategy_dev_queue(),
    )
    assert result.overall_status == "approved_not_executed"
    exec_step = result.chain[4]
    assert exec_step.status == "found"
    assert "no execution receipt" in exec_step.headline.lower() or "approved" in exec_step.headline.lower()


def test_pcba_block_marks_pcba_step_blocked_with_reason_in_detail():
    """Test 4: Cycle blocked by PCBA gate → step 3 status='blocked' with PCBA reason."""
    intent = _make_intent()
    decision = _make_decision(
        approved=False,
        decision="REJECT",
        reasons=[
            "PCBA gate: live trading remains NOT_LICENSED until pcba_semantics_review_signed lands.",
        ],
    )
    cycle = _make_cycle_report(intents=[intent], decisions=[decision], terminal_commands=[])
    pcba_report = {
        "verdict": "BLOCKED",
        "reason": "live_trading_permission_path remains NOT_LICENSED",
    }

    result = explain_latest_agent_decision(
        agent_cycle_report=cycle,
        pcba_report=pcba_report,
        walk_forward_report=_make_walk_forward_report(),
        strategy_dev_queue_report=_make_strategy_dev_queue(),
    )

    pcba_step = result.chain[2]
    assert pcba_step.name == "pcba_gate_verdict"
    assert pcba_step.status == "blocked"
    assert "live_trading_permission_path" in pcba_step.detail or "NOT_LICENSED" in pcba_step.detail
    assert result.overall_status == "blocked"
    assert result.next_action_hint is not None
    assert "pcba" in result.next_action_hint.lower()


def test_missing_walk_forward_sets_step_missing_with_hint():
    """Test 5: Missing walk-forward input → step 2 status='missing' with hint."""
    cycle = _make_cycle_report(terminal_commands=[_make_terminal_command()])
    result = explain_latest_agent_decision(
        agent_cycle_report=cycle,
        strategy_dev_queue_report=_make_strategy_dev_queue(),
        # walk_forward_report omitted intentionally.
    )

    wf_step = result.chain[1]
    assert wf_step.name == "walk_forward_evidence"
    assert wf_step.status == "missing"
    assert "walk_forward" in wf_step.detail or "walk-forward" in wf_step.detail.lower()
    # The detail must name the input that would unlock it.
    assert (
        "walk_forward_report" in wf_step.detail
        or "daily learning rollup" in wf_step.detail.lower()
    )


def test_plain_english_summary_never_recommends_a_future_trade():
    """Test 6: plain_english_summary never references future-trade advice.

    This explainer describes a PAST decision. It must not say 'buy now',
    'should you trade', 'what should I do', or otherwise advise a future
    market action.
    """
    # Build a variety of scenarios and assert the forbidden phrases never appear.
    scenarios: list[AgentDecisionExplanation] = [
        explain_latest_agent_decision(),
        explain_latest_agent_decision(
            agent_cycle_report=_make_cycle_report(terminal_commands=[_make_terminal_command()]),
            agent_memory_report=_make_memory_report_with_pnl(),
            strategy_dev_queue_report=_make_strategy_dev_queue(),
            walk_forward_report=_make_walk_forward_report(),
        ),
        explain_latest_agent_decision(
            agent_cycle_report=_make_cycle_report(
                intents=[_make_intent()],
                decisions=[
                    _make_decision(
                        approved=False,
                        decision="REJECT",
                        reasons=["PCBA gate blocks live trading."],
                    )
                ],
                terminal_commands=[],
            ),
            pcba_report={"verdict": "BLOCKED", "reason": "not licensed"},
        ),
        explain_latest_agent_decision(
            agent_cycle_report=_make_cycle_report(terminal_commands=[]),
            strategy_dev_queue_report=_make_strategy_dev_queue(),
        ),
    ]

    forbidden = [
        "buy now",
        "sell now",
        "should you trade",
        "what should i do",
        "what should i trade",
        "you should buy",
        "you should sell",
        "recommend buying",
        "recommend selling",
        "place a trade",
    ]
    for result in scenarios:
        summary_lower = result.plain_english_summary.lower()
        for phrase in forbidden:
            assert phrase not in summary_lower, (
                f"Forbidden future-trade advice phrase '{phrase}' found in summary: "
                f"{result.plain_english_summary!r}"
            )


# ---------------------------------------------------------------------------
# A few extra invariants worth pinning down
# ---------------------------------------------------------------------------


def test_chain_is_immutable_tuple_of_dataclasses():
    """Chain must be a tuple of frozen DecisionChainStep instances."""
    result = explain_latest_agent_decision()
    assert isinstance(result.chain, tuple)
    for step in result.chain:
        assert isinstance(step, DecisionChainStep)
        # frozen dataclass → setattr raises FrozenInstanceError (subclass of AttributeError)
        with pytest.raises(Exception):
            step.headline = "mutated"  # type: ignore[misc]


def test_explanation_is_frozen_dataclass():
    """Outer explanation dataclass is frozen too."""
    result = explain_latest_agent_decision()
    with pytest.raises(Exception):
        result.cycle_id = "mutated"  # type: ignore[misc]
