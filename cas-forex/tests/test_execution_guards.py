"""Regression tests for broker-order and execution geometry guards."""

from datetime import datetime

import pytest

from cas_forex.schemas.forecast import Direction, ModelSource
from cas_forex.schemas.forecast import ForecastProposal
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.schemas.risk import RiskAssessment
from cas_forex.schemas.decision import GateStatus, Verdict
from cas_forex.verifier.auditor import CASForexAuditor
from cas_forex.verifier.execution_gate import ExecutionGate


def _risk():
    return RiskAssessment(
        assessment_id="r-1",
        account_balance=10000,
        account_equity=10000,
        margin_free=9000,
        proposed_position_size_lots=0.05,
        open_positions_count=0,
    )


def test_forecast_proposal_rejects_bad_take_profit_side():
    with pytest.raises(ValueError, match="LONG take_profit"):
        ForecastProposal(
            proposal_id="bad-long-tp",
            symbol="EUR/USD",
            direction=Direction.LONG,
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0840,
            confidence=0.8,
            model_source=ModelSource.TECHNICAL,
        )
    with pytest.raises(ValueError, match="SHORT take_profit"):
        ForecastProposal(
            proposal_id="bad-short-tp",
            symbol="EUR/USD",
            direction=Direction.SHORT,
            entry_price=1.0850,
            stop_loss=1.0900,
            take_profit=1.0860,
            confidence=0.8,
            model_source=ModelSource.TECHNICAL,
        )


def test_pending_orders_require_explicit_price():
    with pytest.raises(ValueError, match="requires explicit price"):
        BrokerOrderRequest(
            order_id="limit-no-price",
            decision_ref="d-1",
            symbol="EUR/USD",
            order_type=OrderType.LIMIT,
            direction=Direction.LONG,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.1000,
        )


def test_execution_gate_rejects_market_order_without_effective_price():
    order = BrokerOrderRequest(
        order_id="missing-price",
        decision_ref="d-1",
        symbol="EUR/USD",
        direction=Direction.SHORT,
        volume=0.1,
        stop_loss=1.1000,
        take_profit=1.0900,
    )
    result = ExecutionGate(min_stop_distance_pips=0).evaluate(order)
    assert result.status == GateStatus.FAIL
    assert "Current price required" in result.reason


def test_execution_gate_rejects_tp_on_wrong_side_of_current_price():
    long_order = BrokerOrderRequest(
        order_id="bad-long",
        decision_ref="d-1",
        symbol="EUR/USD",
        direction=Direction.LONG,
        volume=0.1,
        stop_loss=1.0700,
        take_profit=1.0800,
    )
    short_order = BrokerOrderRequest(
        order_id="bad-short",
        decision_ref="d-1",
        symbol="EUR/USD",
        direction=Direction.SHORT,
        volume=0.1,
        stop_loss=1.1000,
        take_profit=1.0900,
    )

    assert ExecutionGate().evaluate(long_order, current_price=1.0850).status == GateStatus.FAIL
    assert ExecutionGate().evaluate(short_order, current_price=1.0850).status == GateStatus.FAIL


def test_auditor_suppresses_when_current_price_crosses_take_profit():
    proposal = ForecastProposal(
        proposal_id="p-1",
        symbol="EUR/USD",
        direction=Direction.LONG,
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        confidence=0.8,
        model_source=ModelSource.ENSEMBLE,
    )
    snapshot = MarketSnapshot(
        symbol="EUR/USD",
        timestamp=datetime(2026, 6, 16, 10, 0, 0),
        bid=1.0848,
        ask=1.0852,
        spread=0.4,
        session="LONDON",
        is_market_open=True,
    )

    decision = CASForexAuditor().evaluate(
        proposal,
        snapshot,
        _risk(),
        current_price=1.1000,
    )

    assert decision.verdict == Verdict.SUPPRESS
    assert decision.overriding_gate == "execution"
