"""Tests for CAS Forex core schemas."""

import pytest
from datetime import datetime

from cas_forex.schemas.forecast import (
    ForecastProposal,
    Direction,
    ModelSource,
    SUPPORTED_SYMBOLS,
)
from cas_forex.schemas.decision import (
    CASDecision,
    GateResult,
    Verdict,
    GateStatus,
)
from cas_forex.schemas.risk import RiskAssessment
from cas_forex.schemas.order import (
    BrokerOrderRequest,
    OrderOutcome,
    OrderType,
    OrderStatus,
)
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.sweep import (
    ProfitSweepPolicy,
    SweepTransaction,
    SweepMode,
    SweepStatus,
)
from cas_forex.schemas.market import MarketSnapshot


class TestForecastProposal:
    def test_valid_long_proposal(self):
        p = ForecastProposal(
            proposal_id="test-001",
            symbol="EUR/USD",
            direction=Direction.LONG,
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0950,
            confidence=0.75,
            model_source=ModelSource.ENSEMBLE,
        )
        assert p.proposal_id == "test-001"
        assert p.direction == Direction.LONG
        assert p.stop_loss < p.entry_price < p.take_profit

    def test_valid_short_proposal(self):
        p = ForecastProposal(
            proposal_id="test-002",
            symbol="GBP/USD",
            direction=Direction.SHORT,
            entry_price=1.2650,
            stop_loss=1.2700,
            take_profit=1.2550,
            confidence=0.80,
            model_source=ModelSource.TIMEGPT,
        )
        assert p.direction == Direction.SHORT
        assert p.stop_loss > p.entry_price > p.take_profit

    def test_rejects_unsupported_symbol(self):
        with pytest.raises(ValueError, match="Unsupported symbol"):
            ForecastProposal(
                proposal_id="bad-001",
                symbol="BTC/USD",
                direction=Direction.LONG,
                entry_price=50000,
                stop_loss=49000,
                take_profit=52000,
                confidence=0.5,
                model_source=ModelSource.TECHNICAL,
            )

    def test_rejects_long_with_stop_loss_above_entry(self):
        with pytest.raises(ValueError, match="LONG stop_loss"):
            ForecastProposal(
                proposal_id="bad-002",
                symbol="EUR/USD",
                direction=Direction.LONG,
                entry_price=1.0850,
                stop_loss=1.0900,  # above entry
                take_profit=1.0950,
                confidence=0.5,
                model_source=ModelSource.TECHNICAL,
            )

    def test_rejects_short_with_stop_loss_below_entry(self):
        with pytest.raises(ValueError, match="SHORT stop_loss"):
            ForecastProposal(
                proposal_id="bad-003",
                symbol="EUR/USD",
                direction=Direction.SHORT,
                entry_price=1.0850,
                stop_loss=1.0800,  # below entry
                take_profit=1.0750,
                confidence=0.5,
                model_source=ModelSource.TECHNICAL,
            )

    def test_rejects_negative_entry_price(self):
        with pytest.raises(ValueError):
            ForecastProposal(
                proposal_id="bad-004",
                symbol="EUR/USD",
                direction=Direction.LONG,
                entry_price=-1.0,
                stop_loss=0.9,
                take_profit=1.1,
                confidence=0.5,
                model_source=ModelSource.TECHNICAL,
            )

    def test_confidence_bounds(self):
        with pytest.raises(ValueError):
            ForecastProposal(
                proposal_id="bad-005",
                symbol="EUR/USD",
                direction=Direction.LONG,
                entry_price=1.0850,
                stop_loss=1.0800,
                take_profit=1.0950,
                confidence=1.5,
                model_source=ModelSource.TECHNICAL,
            )

    def test_all_supported_symbols(self):
        for sym in SUPPORTED_SYMBOLS:
            p = ForecastProposal(
                proposal_id=f"test-{sym.replace('/', '')}",
                symbol=sym,
                direction=Direction.LONG,
                entry_price=1.0,
                stop_loss=0.9,
                take_profit=1.1,
                confidence=0.5,
                model_source=ModelSource.TECHNICAL,
            )
            assert p.symbol == sym


class TestCASDecision:
    def test_accepted_decision(self):
        d = CASDecision(
            decision_id="dec-001",
            proposal_ref="test-001",
            symbol="EUR/USD",
            verdict=Verdict.ACCEPT,
            gate_results=[
                GateResult(gate_name="market", status=GateStatus.PASS, reason="ok"),
                GateResult(gate_name="risk", status=GateStatus.PASS, reason="ok"),
            ],
        )
        assert d.is_accepted
        assert not d.is_suppressed
        assert not d.requires_human

    def test_suppressed_decision(self):
        d = CASDecision(
            decision_id="dec-002",
            proposal_ref="test-002",
            symbol="EUR/USD",
            verdict=Verdict.SUPPRESS,
            gate_results=[
                GateResult(gate_name="market", status=GateStatus.PASS, reason="ok"),
                GateResult(
                    gate_name="risk",
                    status=GateStatus.FAIL,
                    reason="Daily drawdown breached",
                ),
            ],
            overriding_gate="risk",
        )
        assert d.is_suppressed
        assert not d.is_accepted

    def test_flag_for_human_review(self):
        d = CASDecision(
            decision_id="dec-003",
            proposal_ref="test-003",
            symbol="EUR/USD",
            verdict=Verdict.FLAG_FOR_HUMAN_REVIEW,
            gate_results=[
                GateResult(
                    gate_name="macro",
                    status=GateStatus.UNDETERMINED,
                    reason="Close to FOMC blackout boundary",
                ),
            ],
        )
        assert d.requires_human


class TestRiskAssessment:
    def test_drawdown_breach_detection(self):
        ra = RiskAssessment(
            assessment_id="risk-001",
            account_balance=10000,
            account_equity=9800,
            margin_free=9000,
            daily_drawdown_pct=2.5,
            weekly_drawdown_pct=3.0,
            proposed_position_size_lots=0.05,
            open_positions_count=1,
            risk_score=0.7,
        )
        assert ra.daily_drawdown_breached
        assert not ra.weekly_drawdown_breached

    def test_position_size_exceeded(self):
        ra = RiskAssessment(
            assessment_id="risk-002",
            account_balance=10000,
            account_equity=10000,
            margin_free=9500,
            proposed_position_size_lots=0.5,
            max_position_size_lots=0.1,
            open_positions_count=0,
            risk_score=0.3,
        )
        assert ra.position_size_exceeded

    def test_exposure_exceeded(self):
        ra = RiskAssessment(
            assessment_id="risk-003",
            account_balance=10000,
            account_equity=10000,
            margin_free=9000,
            proposed_position_size_lots=0.1,
            total_exposure_lots=0.45,
            max_total_exposure_lots=0.5,
            open_positions_count=2,
            risk_score=0.5,
        )
        assert ra.exposure_exceeded


class TestBrokerOrderRequest:
    def test_market_buy_order(self):
        order = BrokerOrderRequest(
            order_id="ord-001",
            decision_ref="dec-001",
            symbol="EUR/USD",
            order_type=OrderType.MARKET,
            direction=Direction.LONG,
            volume=0.05,
            stop_loss=1.0800,
            take_profit=1.0950,
        )
        mt5 = order.to_mt5_request()
        assert mt5["symbol"] == "EURUSD"
        assert mt5["volume"] == 0.05

    def test_market_sell_order(self):
        order = BrokerOrderRequest(
            order_id="ord-002",
            decision_ref="dec-002",
            symbol="GBP/USD",
            order_type=OrderType.MARKET,
            direction=Direction.SHORT,
            volume=0.1,
            stop_loss=1.2700,
            take_profit=1.2550,
        )
        mt5 = order.to_mt5_request()
        assert "SELL" in mt5["order_type"]


class TestForexEvidencePacket:
    def test_hash_integrity(self):
        packet = ForexEvidencePacket(
            packet_id="pkt-001",
            trace_id="trace-001",
            status=PacketStatus.PROPOSED,
        )
        packet.proposal = {"symbol": "EUR/USD", "direction": "LONG"}
        packet.finalize()
        assert packet.packet_hash_sha256 is not None
        assert packet.verify_hash()

    def test_hash_tamper_detection(self):
        packet = ForexEvidencePacket(
            packet_id="pkt-002",
            trace_id="trace-002",
            status=PacketStatus.PROPOSED,
        )
        packet.proposal = {"symbol": "EUR/USD"}
        packet.finalize()
        # Tamper
        packet.proposal = {"symbol": "GBP/USD"}
        assert not packet.verify_hash()

    def test_full_lifecycle_packet(self):
        packet = ForexEvidencePacket(
            packet_id="pkt-003",
            trace_id="trace-003",
            status=PacketStatus.CLOSED_WIN,
        )
        packet.proposal = {"proposal_id": "p-1", "symbol": "EUR/USD"}
        packet.market_snapshot = {"bid": 1.0850, "ask": 1.0852}
        packet.cas_decision = {"verdict": "ACCEPT"}
        packet.risk_assessment = {"risk_score": 0.2}
        packet.order_request = {"volume": 0.05}
        packet.order_outcome = {"status": "EXECUTED", "broker_ticket": 12345}
        packet.close_outcome = {"profit_pips": 25.0}
        packet.profit_loss_account = 125.0
        packet.profit_loss_pips = 25.0
        packet.finalize()
        assert packet.verify_hash()
        assert packet.finalized_at is not None


class TestProfitSweepPolicy:
    def test_allocation_sum(self):
        policy = ProfitSweepPolicy(
            mode=SweepMode.AUTO,
            reinvest_pct=50,
            savings_pct=40,
            tax_reserve_pct=10,
        )
        assert policy.allocation_sum == 100.0


class TestMarketSnapshot:
    def test_mid_price(self):
        snap = MarketSnapshot(
            symbol="EUR/USD",
            bid=1.0850,
            ask=1.0852,
        )
        assert snap.mid == 1.0851

    def test_rejects_invalid_symbol(self):
        with pytest.raises(ValueError, match="Unsupported symbol"):
            MarketSnapshot(symbol="INVALID", bid=1.0, ask=1.0)
