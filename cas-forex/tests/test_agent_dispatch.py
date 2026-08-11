"""Tests for wiring real agent signals into the gated dispatch loop.

Covers: a real RouteIntent (built by the micro-scalp policy) flowing through the
overseer into the gated paper dispatch; overseer-rejected intents recorded but
not dispatched; live-gate block; and the end-to-end run_agent_dispatch_cycle.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import json

import pytest

from cas_forex.agent_dispatch import (
    AgentDispatchCycle,
    _filter_current_market_valid_intents,
    _intent_proposed_dispatch_context,
    collect_route_intents,
    dispatch_route_intents,
    entry_risk_feasibility_status,
    entry_timeframe_scan_status,
    load_latest_agent_dispatch_cycle_report,
    reset_entry_risk_feasibility_for_testing,
    reset_entry_timeframe_rotation_for_testing,
    run_agent_dispatch_cycle,
    write_agent_dispatch_cycle_report,
)
from cas_forex.agent_state import RouteIntent
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision, _now_iso, mint_token
from cas_forex.order_attempt_audit import OrderAttemptAuditStore
from cas_forex.order_dispatch import (
    STATUS_BLOCKED_EDGE_AUTHORIZATION,
    STATUS_BLOCKED_RISK,
    STATUS_OVERSEER_REJECTED,
)
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.time_utils import utc_now


@pytest.fixture(autouse=True)
def _isolate_default_order_attempt_audit(tmp_path, monkeypatch):
    import cas_forex.order_attempt_audit as order_attempt_audit

    monkeypatch.setattr(order_attempt_audit, "DEFAULT_STATE_PATH", tmp_path / "default-order-attempts.json")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_AUDIT_PATH", tmp_path / "default-order-attempts-audit.jsonl")


def _cfg(*, live_mode: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
    )


def _order(symbol: str = "EUR/USD", volume: float = 0.1) -> BrokerOrderRequest:
    return BrokerOrderRequest(
        order_id=f"agent-{symbol.replace('/', '')}-1",
        decision_ref="micro_scalp_agent:test",
        symbol=symbol,
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=volume,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_MICRO_SCALP",
    )


def test_dispatch_context_preserves_entry_timeframe_for_learning_join():
    intent = _route_intent()

    context = _intent_proposed_dispatch_context(intent, None)

    assert context["timeframe"] == intent.timeframe
    assert context["strategy_id"] == intent.strategy_setting
    assert context["route_intent_id"] == intent.intent_id


def test_dispatch_context_preserves_actual_operator_model_and_sizing_provenance():
    intent = replace(
        _route_intent(volume=0.02),
        _runtime_context={
            "setup": SimpleNamespace(regime="directional_pressure"),
            "operator_sizing_selection": {
                "sizing_ref": "size-press-002",
                "label": "PRESS_EDGE",
                "lots": 0.02,
                "sizing_plan_hash": "plan-hash",
                "operator_event_hash": "operator-event-hash",
                "operator_prompt_version": "ai_operator_trade_edge.v11",
                "operator_decision_prompt_hash": "decision-prompt-hash",
                "operator_system_prompt_hash": "system-prompt-hash",
                "operator_provider": "local-fallback",
                "operator_provider_label": "Local model (deepseek-r1:latest)",
                "operator_model_ref": "deepseek-r1:latest",
                "operator_model_backend": "ollama",
                "operator_decision_context_hash": "context-hash",
                "operator_candidate_snapshot_hash": "candidate-snapshot-hash",
                "operator_candidate_hash": "candidate-hash",
                "operator_decision": "APPROVE",
                "operator_conviction": "HIGH",
                "operator_reason": "Exact after-cost evidence supports the bounded size.",
                "growth_evidence_state": "EXACT_GROUP_RISK_NORMALIZED_EDGE",
                "regime_identity_available": True,
                "regime_comparable_outcome_count": 8,
                "all_regimes_growth_evidence_state": (
                    "EXACT_GROUP_POSITIVE_SAMPLE_READY"
                ),
                "sizing_options_offered": [
                    {
                        "sizing_ref": "size-probe-001",
                        "label": "PROBE",
                        "lots": 0.01,
                    },
                    {
                        "sizing_ref": "size-press-002",
                        "label": "PRESS_EDGE",
                        "lots": 0.02,
                    },
                ],
                "sizing_option_count": 2,
                "max_executable_lots": 0.02,
                "sizing_limiting_source": "max_risk_per_trade_pct",
            }
        },
    )

    context = _intent_proposed_dispatch_context(intent, None)

    assert context["lots"] == 0.02
    assert context["sizing_ref"] == "size-press-002"
    assert context["sizing_label"] == "PRESS_EDGE"
    assert context["operator_model_ref"] == "deepseek-r1:latest"
    assert context["operator_provider"] == "local-fallback"
    assert context["operator_prompt_version"] == "ai_operator_trade_edge.v11"
    assert context["operator_candidate_hash"] == "candidate-hash"
    assert context["operator_event_hash"] == "operator-event-hash"
    assert context["market_regime"] == "directional_pressure"
    assert context["market_regime_source"] == "candidate_setup.regime"
    assert context["regime_identity_available"] is True
    assert context["regime_comparable_outcome_count"] == 8
    assert context["sizing_option_count"] == 2
    assert context["max_executable_lots"] == 0.02
    assert context["sizing_limiting_source"] == "max_risk_per_trade_pct"
    assert context["sizing_options_offered"][1]["sizing_ref"] == "size-press-002"


def _route_intent(
    *,
    symbol: str = "EUR/USD",
    volume: float = 0.1,
    confidence: float = 0.7,
    evidence_score: float = 2.0,
    evidence_refs=("ref-1",),
    intent_id: str = "intent-1",
) -> RouteIntent:
    order = _order(symbol=symbol, volume=volume)
    return RouteIntent(
        intent_id=intent_id,
        agent_id="micro_scalp_agent",
        action="OPEN_MICRO_SCALP",
        symbol=symbol,
        timeframe="M5",
        strategy_setting="range_scalper_12_80",
        direction=Direction.LONG.value,
        confidence=confidence,
        evidence_score=evidence_score,
        lot_size=volume,
        entry_price=1.10,
        stop_loss=1.0900,
        take_profit=1.1100,
        reason="test route intent",
        evidence_refs=list(evidence_refs),
        order_request=order.model_dump(mode="json"),
    )


class _IndexRiskBridge:
    def symbol_info(self, symbol):
        if symbol != "US30":
            return None
        return SimpleNamespace(
            point=0.01,
            digits=2,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_contract_size=1.0,
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            trade_tick_value_loss=1.0,
            trade_tick_value_profit=1.0,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbols_get(self, pattern=None):
        return [SimpleNamespace(name="US30")]

    def get_account_info(self):
        return {
            "balance": 44_757.89,
            "equity": 44_555.70,
            "margin": 411.75,
            "margin_free": 44_143.95,
            "leverage": 500,
        }

    def get_open_positions(self):
        return []

    def will_execute_real_order(self):
        return False


def _index_risk_intent(*, stop_loss: float = 52_734.75) -> RouteIntent:
    entry = 52_597.82
    order = BrokerOrderRequest(
        order_id="agent-us30-risk-preflight",
        decision_ref="live-candle-us30-risk-preflight",
        symbol="US30",
        order_type=OrderType.MARKET,
        direction=Direction.SHORT,
        volume=0.01,
        price=0.0,
        stop_loss=stop_loss,
        take_profit=52_374.18,
        comment="CAS_RISK_PREFLIGHT",
    )
    return RouteIntent(
        intent_id="intent-us30-risk-preflight",
        agent_id="live_candle_agent",
        action="OPEN_LIVE_CANDLE_LEARNING",
        symbol="US30",
        timeframe="H1",
        strategy_setting="live_candle_index-tsmom_h1",
        direction=Direction.SHORT.value,
        confidence=0.75,
        evidence_score=2.0,
        lot_size=0.01,
        entry_price=entry,
        stop_loss=stop_loss,
        take_profit=52_374.18,
        reason="fresh completed H1 candidate",
        evidence_refs=["completed-candle:H1", "broker-quote:fresh"],
        order_request=order.model_dump(mode="json"),
        learning_trade=True,
        market_quote_context={
            "quote_source": "mt5",
            "market_snapshot": {
                "symbol": "US30",
                "bid": entry,
                "ask": entry + 1.0,
                "spread": 1.0,
                "timestamp": utc_now().isoformat(),
            },
        },
    )


class _CapturingOperatorProvider:
    def __init__(self, decision: str = "STAND_DOWN") -> None:
        self.decision = decision
        self.calls: list[str] = []

    def generate(self, prompt, system=None, **kwargs):
        self.calls.append(prompt)
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "candidate_decisions": [
                        {
                            "intent_id": "intent-us30-risk-preflight",
                            "decision": self.decision,
                            "conviction": "LOW",
                            "reason": "Test decision after deterministic risk feasibility.",
                        }
                    ],
                    "summary": "Test Operator response.",
                }
            ),
            "provider": "claude",
            "provider_label": "Claude (test)",
            "paid": True,
            "failover": False,
            "error": None,
        }


def test_real_route_intent_dispatches_through_overseer_and_gate():
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    assert isinstance(cycle, AgentDispatchCycle)
    assert cycle.approved_count == 1
    report = cycle.dispatch_report
    assert report.intent_count == 1
    assert report.executed_count == 1
    assert report.mode == "PAPER"
    # The dispatched order produced a paper ledger event.
    events = cycle.ledger_events()
    assert len(events) == 1
    assert events[0].event_type == "paper_order_intent"
    assert events[0].external_money_movement is False


def test_broker_minimum_lot_risk_blocks_before_operator_model_call(tmp_path, monkeypatch):
    from cas_forex import execution_guard

    reset_entry_risk_feasibility_for_testing()
    monkeypatch.setattr(
        execution_guard,
        "caps_from_config",
        lambda config=None: SimpleNamespace(max_risk_per_trade_pct=0.1),
    )
    provider = _CapturingOperatorProvider(decision="APPROVE")
    state_path = tmp_path / "entry-risk-feasibility.json"

    cycle = run_agent_dispatch_cycle(
        intents=[_index_risk_intent()],
        bridge=_IndexRiskBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
        operator_trade_edge_enabled=True,
        operator_trade_edge_provider=provider,
        operator_trade_edge_audit_path=tmp_path / "operator-edge.jsonl",
        operator_trade_edge_latest_path=tmp_path / "operator-edge-latest.json",
        entry_risk_feasibility_path=state_path,
    )

    assert provider.calls == []
    assert cycle.overseer_decisions[0].approved is False
    assert cycle.overseer_decisions[0].decision == "RISK_PREFLIGHT_REJECTED"
    assert cycle.dispatch_report.results[0].status == STATUS_BLOCKED_RISK
    assert cycle.dispatch_report.blocked_count == 1
    report = cycle.entry_risk_feasibility_report
    assert report["status"] == "ALL_CANDIDATES_BLOCKED_BEFORE_OPERATOR"
    assert report["operator_candidate_count"] == 0
    candidate = report["candidates"][0]
    assert candidate["status"] == "BLOCKED_AT_BROKER_MIN_LOT"
    assert candidate["risk_at_stop_usd"] == 136.93
    assert candidate["risk_at_stop_pct_equity"] == 0.3073
    assert candidate["broker_min_lot"] == 0.01
    assert candidate["max_feasible_lots"] == 0.0
    assert "no compliant lot exists" in candidate["reason"]
    assert state_path.exists()
    assert entry_risk_feasibility_status()["status"] == report["status"]


def test_risk_feasible_candidate_reaches_operator(tmp_path, monkeypatch):
    from cas_forex import execution_guard

    monkeypatch.setattr(
        execution_guard,
        "caps_from_config",
        lambda config=None: SimpleNamespace(max_risk_per_trade_pct=0.1),
    )
    provider = _CapturingOperatorProvider(decision="STAND_DOWN")

    cycle = run_agent_dispatch_cycle(
        intents=[_index_risk_intent(stop_loss=52_617.82)],
        bridge=_IndexRiskBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
        operator_trade_edge_enabled=True,
        operator_trade_edge_provider=provider,
        operator_trade_edge_audit_path=tmp_path / "operator-edge.jsonl",
        operator_trade_edge_latest_path=tmp_path / "operator-edge-latest.json",
        entry_risk_feasibility_path=tmp_path / "entry-risk-feasibility.json",
    )

    assert len(provider.calls) == 1
    report = cycle.entry_risk_feasibility_report
    assert report["status"] == "ALL_CANDIDATES_RISK_FEASIBLE"
    assert report["feasible_count"] == 1
    assert report["operator_candidate_count"] == 1
    assert report["candidates"][0]["risk_at_stop_usd"] == 20.0
    assert report["candidates"][0]["risk_at_stop_pct_equity"] == 0.0449
    assert cycle.overseer_decisions[0].decision == "AI_OPERATOR_STAND_DOWN"


def test_overseer_rejected_intent_is_recorded_not_dispatched():
    bridge = SimulatedBrokerBridge()
    # evidence_score below the overseer's 1.0 route threshold -> rejected.
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent(evidence_score=0.0)],
        bridge=bridge,
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    assert cycle.approved_count == 0
    results = cycle.dispatch_report.results
    assert len(results) == 1
    assert results[0].status == STATUS_OVERSEER_REJECTED
    assert results[0].dispatched_to_bridge is False
    # Nothing reached the broker.
    assert bridge.get_open_positions() == []


def test_live_mode_blocks_approved_intent_without_fresh_edge_pass(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "agent-live-gate-order-attempts.json",
        tmp_path / "agent-live-gate-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=bridge,
        config=_cfg(live_mode=True),
        enforce_receipt_gates=False,
        audit_store=store,
    )
    assert cycle.approved_count == 1  # overseer approves
    result = cycle.dispatch_report.results[0]
    # Real dispatch requires its one-shot edge authorization before later live gates.
    assert result.status == STATUS_BLOCKED_EDGE_AUTHORIZATION
    assert result.dispatched_to_bridge is False
    assert bridge.get_open_positions() == []


def test_dispatch_route_intents_mixed_batch():
    bridge = SimulatedBrokerBridge()
    from cas_forex.agent_overseer import review_route_intents

    intents = [
        _route_intent(intent_id="ok", symbol="EUR/USD"),
        _route_intent(intent_id="bad", symbol="USD/JPY", evidence_score=0.0),
    ]
    decisions = review_route_intents(intents, enforce_receipt_gates=False)
    report = dispatch_route_intents(intents, decisions, bridge=bridge, config=_cfg())

    assert report.intent_count == 2
    assert report.executed_count == 1
    statuses = {r.status for r in report.results}
    assert STATUS_OVERSEER_REJECTED in statuses


def test_duplicate_intent_id_not_silently_dropped():
    # SF-1 regression: positional pairing represents every intent exactly once,
    # even when two intents share an intent_id (the old id-keyed dict dropped one).
    bridge = SimulatedBrokerBridge()
    from cas_forex.agent_overseer import review_route_intents

    intents = [
        _route_intent(intent_id="dup", symbol="EUR/USD"),
        _route_intent(intent_id="dup", symbol="USD/JPY"),
    ]
    decisions = review_route_intents(intents, enforce_receipt_gates=False)
    report = dispatch_route_intents(intents, decisions, bridge=bridge, config=_cfg())

    # Both intents are represented; none dropped from the report.
    assert report.intent_count == 2
    symbols = sorted(r.symbol for r in report.results)
    assert symbols == ["EUR/USD", "USD/JPY"]


def test_cycle_serializes_to_dict():
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    payload = cycle.to_dict()
    assert payload["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert payload["route_intent_count"] == 1
    assert payload["dispatch_report"]["report_kind"] == "cas_forex_order_dispatch"
    assert "Operator selects one" in payload["claim_boundary"]
    assert "final action-time risk guard" in payload["claim_boundary"]


def test_write_cycle_report_persists_json(tmp_path):
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    paths = write_agent_dispatch_cycle_report(cycle, output_dir=tmp_path)
    assert paths["json"].exists()
    assert paths["latest"].exists()
    loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert loaded["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert loaded["dispatch_report"]["executed_count"] == 1
    assert load_latest_agent_dispatch_cycle_report(output_dir=tmp_path) == loaded


def test_stale_market_geometry_route_is_filtered_before_dispatch(tmp_path):
    class _Connector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=0.9805,
                ask=0.9807,
                is_market_open=True,
                timestamp=utc_now().isoformat(),
            )

    stale = _route_intent(symbol="AUD/CAD")
    kept = _filter_current_market_valid_intents(
        [stale],
        connector=_Connector(),
        report_path=tmp_path / "agent-route-filter.json",
    )

    assert kept == []
    report = json.loads((tmp_path / "agent-route-filter.json").read_text(encoding="utf-8"))
    assert report["status"] == "FILTERED_STALE_MARKET_GEOMETRY"
    assert report["filtered_count"] == 1
    assert "LONG market route is stale" in report["filtered"][0]["reason"]


def test_historical_replay_template_is_not_mistaken_for_current_direction(tmp_path):
    class _Connector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=0.9805,
                ask=0.9807,
                is_market_open=True,
                timestamp=utc_now().isoformat(),
            )

    template = _route_intent(symbol="AUD/CAD")
    template = template.__class__(
        **{
            **template.to_dict(),
            "market_geometry_policy": "REPLAY_TEMPLATE_REQUIRES_CURRENT_DIRECTION",
        }
    )
    report_path = tmp_path / "agent-route-filter.json"
    kept = _filter_current_market_valid_intents(
        [template],
        connector=_Connector(),
        report_path=report_path,
    )

    assert kept == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "FILTERED_REPLAY_TEMPLATE_UNBOUND"
    assert "not a current directional entry" in report["filtered"][0]["reason"]


def test_valid_route_carries_quote_into_dispatch_checks_and_money_estimate(tmp_path):
    class _Connector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.0999,
                ask=1.1001,
                spread=2.0,
                is_market_open=True,
                synthetic_fallback=False,
                timestamp=utc_now().isoformat(),
            )

    kept = _filter_current_market_valid_intents(
        [_route_intent(symbol="EUR/USD", volume=0.01)],
        connector=_Connector(),
        report_path=tmp_path / "agent-route-filter.json",
    )

    assert len(kept) == 1
    assert kept[0].market_quote_context["market_snapshot"]["ask"] == 1.1001

    cycle = run_agent_dispatch_cycle(
        intents=kept,
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    result = cycle.dispatch_report.results[0]
    assert result.executed is True
    assert result.market_availability["status"] == "PASSED"
    assert result.execution_quality["status"] == "PASSED"
    assert result.order_constraints["status"] == "PASSED"
    assert result.pre_trade_estimate["entry_price"] == 1.1001
    assert result.pre_trade_estimate["entry_price_source"] == "proposed_intent.entry_price"
    assert result.pre_trade_estimate["spread_cost_estimate_usd"] is not None
    assert result.outcome is not None
    assert abs(float(result.outcome.filled_price) - 1.100102) < 1e-8


def test_pass_ready_route_registers_and_consumes_edge_before_paper_dispatch(tmp_path):
    from cas_forex import edge_authorization
    from cas_forex.edge_authorization import EdgeNotAuthorized

    edge_authorization.reset()
    base = _route_intent(intent_id="pass-ready", symbol="EUR/USD")
    setup = CandidateSetup(
        symbol="EUR/USD",
        timeframe="M5",
        direction="LONG",
        entry=1.10,
        stop_loss=1.09,
        take_profit=1.11,
        signal_strength=0.8,
        regime="trend",
        decision_ref=base.order_request["decision_ref"],
    )
    evaluated_at = _now_iso()
    edge = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.7,
        null_p95=0.01,
        threshold=0.6,
        edge_token=mint_token(setup, evaluated_at),
        evaluated_at=evaluated_at,
        reason="fresh test edge",
    )
    intent = base.__class__(
        **{
            **base.to_dict(),
            "edge_authorization_ready": True,
            "edge_label": {
                "status": "PASS",
                "has_edge_token": True,
            },
            "_runtime_context": {
                "source_kind": "test_pass_route",
                "setup": setup,
                "edge": edge,
            },
        }
    )
    store = OrderAttemptAuditStore(
        tmp_path / "pass-order-attempts.json",
        tmp_path / "pass-order-attempts-audit.jsonl",
    )

    cycle = run_agent_dispatch_cycle(
        intents=[intent],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
        audit_store=store,
    )

    assert cycle.dispatch_report.executed_count == 1
    assert edge_authorization.is_required(setup.decision_ref) is True
    with pytest.raises(EdgeNotAuthorized, match="already consumed"):
        edge_authorization.require(
            BrokerOrderRequest(**intent.order_request),
            is_real=False,
            config=_cfg(),
            bridge=SimulatedBrokerBridge(),
            volume=0.1,
            order_type=OrderType.MARKET,
            price=0.0,
            strategy_id=intent.strategy_setting,
            proposed_intent={
                "symbol": "EUR/USD",
                "direction": "LONG",
                "lots": 0.1,
            },
        )
    edge_authorization.reset()


def test_live_candle_learning_dispatch_records_waste_outcome_join_context(tmp_path):
    from cas_forex.waste_cycle_audit import WasteCycleAuditStore

    base = _route_intent(intent_id="learning-route", symbol="EUR/USD")
    decision_ref = str(base.order_request["decision_ref"])
    setup = CandidateSetup(
        symbol="EUR/USD",
        timeframe="M5",
        direction="LONG",
        entry=1.10,
        stop_loss=1.09,
        take_profit=1.11,
        signal_strength=0.8,
        regime="trend",
        decision_ref=decision_ref,
    )
    edge = EdgeTestDecision(
        status="NO_TRADE_NULL_FAILED",
        measured_win_prob=0.6,
        null_p95=0.02,
        threshold=0.6,
        edge_token=None,
        evaluated_at=_now_iso(),
        reason="paper label",
    )
    intent = base.__class__(
        **{
            **base.to_dict(),
            "agent_id": "live_candle_agent",
            "action": "OPEN_LIVE_CANDLE_LEARNING",
            "learning_trade": True,
            "edge_label": {"status": edge.status, "has_edge_token": False},
            "_runtime_context": {
                "source_kind": "live_candle_route",
                "setup": setup,
                "edge": edge,
                "watch_state": {"symbol": "EUR/USD", "broker_grade_market_truth": True},
                "analysis": {"hypothesis": {"direction": "LONG", "confidence": 0.8}},
                "learning_trade": True,
            },
        }
    )
    cycle_store = WasteCycleAuditStore(
        tmp_path / "waste-state.json",
        tmp_path / "waste-audit.jsonl",
    )

    cycle = run_agent_dispatch_cycle(
        intents=[intent],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
        audit_store=OrderAttemptAuditStore(
            tmp_path / "learning-attempts.json",
            tmp_path / "learning-attempts-audit.jsonl",
        ),
        waste_cycle_audit_store=cycle_store,
    )

    assert cycle.dispatch_report.executed_count == 1
    latest = cycle_store.latest_cycle()
    assert latest["decision"] == "EXECUTE"
    assert latest["learning_trade"] is True
    assert latest["source"] == "agent_dispatch.live_candle_route"
    assert latest["candidate"]["decision_ref"] == decision_ref
    assert latest["edge"]["status"] == "NO_TRADE_NULL_FAILED"
    assert latest["execute_result"]["executed"] is True


def test_route_without_usable_quote_is_filtered_before_overseer_or_bridge(tmp_path):
    class _Connector:
        def fetch_snapshot(self, symbol):
            raise RuntimeError(f"quote feed unavailable for {symbol}")

    kept = _filter_current_market_valid_intents(
        [_route_intent(symbol="EUR/USD")],
        connector=_Connector(),
        report_path=tmp_path / "agent-route-filter.json",
    )

    assert kept == []
    report = json.loads((tmp_path / "agent-route-filter.json").read_text(encoding="utf-8"))
    assert report["status"] == "FILTERED_NO_USABLE_MARKET_QUOTE"
    assert report["filter_status_counts"] == {"FILTERED_NO_USABLE_MARKET_QUOTE": 1}
    assert "quote feed unavailable" in report["filtered"][0]["reason"]


def test_closed_or_stale_quote_is_not_treated_as_permission_to_dispatch(tmp_path):
    class _ClosedConnector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.0999,
                ask=1.1001,
                spread=2.0,
                is_market_open=False,
                synthetic_fallback=False,
                timestamp=utc_now().isoformat(),
            )

    closed_report_path = tmp_path / "closed-agent-route-filter.json"
    assert _filter_current_market_valid_intents(
        [_route_intent(symbol="EUR/USD")],
        connector=_ClosedConnector(),
        report_path=closed_report_path,
    ) == []
    closed_report = json.loads(closed_report_path.read_text(encoding="utf-8"))
    assert closed_report["status"] == "FILTERED_MARKET_CLOSED"

    class _StaleConnector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.0999,
                ask=1.1001,
                spread=2.0,
                is_market_open=True,
                synthetic_fallback=False,
                timestamp=(utc_now() - timedelta(seconds=121)).isoformat(),
            )

    stale_report_path = tmp_path / "stale-agent-route-filter.json"
    assert _filter_current_market_valid_intents(
        [_route_intent(symbol="EUR/USD")],
        connector=_StaleConnector(),
        report_path=stale_report_path,
    ) == []
    stale_report = json.loads(stale_report_path.read_text(encoding="utf-8"))
    assert stale_report["status"] == "FILTERED_STALE_MARKET_QUOTE"
    assert "121" in stale_report["filtered"][0]["reason"]


def test_materially_future_quote_is_blocked_before_dispatch(tmp_path):
    class _FutureConnector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.0999,
                ask=1.1001,
                spread=2.0,
                is_market_open=True,
                synthetic_fallback=False,
                timestamp=(utc_now() + timedelta(minutes=5)).isoformat(),
            )

    report_path = tmp_path / "future-agent-route-filter.json"
    assert _filter_current_market_valid_intents(
        [_route_intent(symbol="EUR/USD")],
        connector=_FutureConnector(),
        report_path=report_path,
    ) == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "FILTERED_FUTURE_MARKET_QUOTE"
    assert "ahead of the host clock" in report["filtered"][0]["reason"]


def test_entry_timeframe_rotation_scans_micro_and_intraday_lanes(tmp_path, monkeypatch):
    import cas_forex.live_candle_route_policy as live_policy

    reset_entry_timeframe_rotation_for_testing()
    selected: list[str] = []

    def build(**kwargs):
        selected.append(str(kwargs["timeframe"]))
        return []

    monkeypatch.setattr(live_policy, "build_live_candle_route_intents", build)
    monkeypatch.setattr(
        live_policy,
        "live_candle_route_invocation_status",
        lambda **kwargs: {
            "status": "FULL_SCAN_COMPLETED",
            "fresh_market_scan_performed": True,
            "timeframe": kwargs["timeframe"],
            "attempt_count": 1,
            "entry_stage_summary": {"status": "NO_EDGE_TEST_CANDIDATE"},
        },
    )
    scan_path = tmp_path / "entry-timeframe-scan.json"
    common = {
        "replay_results": {"replay_verdict": "NO_REPLAY_LEAD"},
        "replay_candidates": {"candidates": []},
        "include_live_candle": True,
        "active_timeframes": ["M1", "M5", "H1"],
        "entry_timeframe_scan_path": scan_path,
        "allowed_symbols": ["EUR/USD"],
        "config": SimpleNamespace(live_mode=False, paper_trading=True),
    }

    for _ in range(4):
        assert collect_route_intents(**common) == []

    assert selected == ["M1", "M5", "H1", "M1"]
    status = entry_timeframe_scan_status()
    assert status["status"] == "SCAN_COMPLETED"
    assert status["fresh_market_scan_performed"] is True
    assert status["route_scan_status"] == "FULL_SCAN_COMPLETED"
    assert status["market_attempt_count"] == 1
    assert status["selected_timeframe"] == "M1"
    assert status["entry_lane"] == "MICRO_SCALP"
    assert status["active_timeframes"] == ["M1", "M5", "H1"]
    saved = json.loads(scan_path.read_text(encoding="utf-8"))
    assert saved["selected_timeframe"] == "M1"
    assert saved["fresh_intent_count"] == 0


def test_entry_timeframe_scan_labels_cache_throttle_without_claiming_full_scan(
    tmp_path, monkeypatch
):
    import cas_forex.live_candle_route_policy as live_policy

    reset_entry_timeframe_rotation_for_testing()
    monkeypatch.setattr(live_policy, "build_live_candle_route_intents", lambda **_kwargs: [])
    monkeypatch.setattr(
        live_policy,
        "live_candle_route_invocation_status",
        lambda **_kwargs: {
            "status": "SCAN_THROTTLED_CACHE",
            "fresh_market_scan_performed": False,
            "cache_remaining_seconds": 31.5,
            "last_full_scan": {"status": "FULL_SCAN_COMPLETED"},
        },
    )

    scan_path = tmp_path / "entry-timeframe-scan.json"
    collect_route_intents(
        replay_results={},
        replay_candidates={},
        include_live_candle=True,
        active_timeframes=["M1"],
        entry_timeframe_scan_path=scan_path,
        allowed_symbols=["EUR/USD"],
        config=SimpleNamespace(live_mode=False, paper_trading=True),
    )

    status = entry_timeframe_scan_status()
    assert status["status"] == "SCAN_THROTTLED_CACHE"
    assert status["fresh_market_scan_performed"] is False
    assert status["cache_remaining_seconds"] == 31.5
    assert status["last_full_scan"]["status"] == "FULL_SCAN_COMPLETED"
