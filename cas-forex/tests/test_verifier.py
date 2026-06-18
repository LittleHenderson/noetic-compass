"""Tests for CAS Forex Verifier gates."""
import pytest
from datetime import datetime, timedelta

from cas_forex.schemas.forecast import ForecastProposal, Direction, ModelSource
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.schemas.risk import RiskAssessment
from cas_forex.schemas.decision import Verdict, GateStatus
from cas_forex.schemas.order import BrokerOrderRequest
from cas_forex.verifier.market_gate import MarketGate
from cas_forex.verifier.macro_gate import MacroGate
from cas_forex.verifier.risk_gate import RiskGate
from cas_forex.verifier.execution_gate import ExecutionGate
from cas_forex.verifier.auditor import CASForexAuditor


def _make_proposal(symbol="EUR/USD", direction=Direction.LONG, entry=1.0850, sl=1.0800, tp=1.0950, confidence=0.8):
    return ForecastProposal(
        proposal_id="prop-001",
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        confidence=confidence,
        model_source=ModelSource.ENSEMBLE,
    )


def _make_snapshot(symbol="EUR/USD", bid=1.0848, ask=1.0852, spread=0.4, high=1.0860, low=1.0840,
                   session="LONDON", is_open=True, timestamp=datetime(2026, 6, 16, 10, 0, 0)):
    return MarketSnapshot(
        symbol=symbol,
        timestamp=timestamp,
        bid=bid,
        ask=ask,
        spread=spread,
        high=high,
        low=low,
        session=session,
        is_market_open=is_open,
    )


def _make_risk(daily_dd=0.5, weekly_dd=1.0, pos_size=0.05, risk_per_trade=0.25,
               open_pos=2, total_exposure=0.15, margin_level=500.0):
    return RiskAssessment(
        assessment_id="ra-001",
        account_balance=10000.0,
        account_equity=9950.0,
        margin_used=1990.0,
        margin_free=7960.0,
        margin_level_pct=margin_level,
        daily_drawdown_pct=daily_dd,
        weekly_drawdown_pct=weekly_dd,
        proposed_position_size_lots=pos_size,
        risk_per_trade_pct=risk_per_trade,
        open_positions_count=open_pos,
        total_exposure_lots=total_exposure,
        risk_score=0.3,
    )


class TestMarketGate:
    def test_pass_normal_conditions(self):
        gate = MarketGate()
        snap = _make_snapshot()
        result = gate.evaluate(snap, Direction.LONG, 1.0850)
        assert result.status == GateStatus.PASS
        assert "spread_pips" in result.evidence

    def test_fail_market_closed(self):
        gate = MarketGate()
        snap = _make_snapshot(is_open=False)
        result = gate.evaluate(snap, Direction.LONG, 1.0850)
        assert result.status == GateStatus.FAIL

    def test_fail_wide_spread(self):
        gate = MarketGate(max_spread_pips=2.0)
        snap = _make_snapshot(spread=5.0)
        result = gate.evaluate(snap, Direction.LONG, 1.0850)
        assert result.status == GateStatus.FAIL

    def test_pass_spread_within_bounds(self):
        gate = MarketGate(max_spread_pips=3.0)
        snap = _make_snapshot(spread=1.5)
        result = gate.evaluate(snap, Direction.LONG, 1.0850)
        assert result.status == GateStatus.PASS

    def test_high_atr_undetermined(self):
        gate = MarketGate(max_atr_multiple=2.0)
        snap = _make_snapshot(high=1.0900, low=1.0800)  # 100 pip range
        result = gate.evaluate(snap, Direction.LONG, 1.0850, atr_14=0.0020)  # 20 pip ATR
        # range=0.01, atr=0.002, ratio=5.0 > 2.0 max
        assert result.status == GateStatus.FAIL


class TestMacroGate:
    def test_pass_normal_time(self):
        gate = MacroGate()
        # A Tuesday at 10:00 UTC — no events
        dt = datetime(2026, 6, 16, 10, 0, 0)  # Tuesday
        result = gate.evaluate(dt)
        assert result.status == GateStatus.PASS

    def test_fail_nfp_blackout(self):
        gate = MacroGate()
        # First Friday of June 2026 is June 5
        dt = datetime(2026, 6, 5, 12, 30, 0)  # NFP release time
        result = gate.evaluate(dt)
        assert result.status == GateStatus.FAIL
        assert "NFP" in result.reason

    def test_pass_outside_nfp_blackout(self):
        gate = MacroGate()
        # First Friday but 3 hours before
        dt = datetime(2026, 6, 5, 9, 0, 0)
        result = gate.evaluate(dt)
        # 9:00 UTC, NFP at 12:30 UTC, blackout starts 60 min before = 11:30
        assert result.status == GateStatus.PASS

    def test_fail_fomc_blackout(self):
        gate = MacroGate()
        # June 2026 FOMC — Jun 16-17 meeting, decision Jun 17 at 18:00 UTC (14:00 EDT)
        dt = datetime(2026, 6, 17, 18, 0, 0)
        result = gate.evaluate(dt)
        assert result.status == GateStatus.FAIL


class TestRiskGate:
    def test_pass_normal_risk(self):
        gate = RiskGate()
        risk = _make_risk()
        result = gate.evaluate(risk)
        assert result.status == GateStatus.PASS

    def test_fail_daily_drawdown_breach(self):
        gate = RiskGate()
        risk = _make_risk(daily_dd=3.0)
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL
        assert "LIVE_LOCKED" in result.reason
        assert result.evidence["locks_triggered"] is True

    def test_fail_weekly_drawdown_breach(self):
        gate = RiskGate()
        risk = _make_risk(weekly_dd=6.0)
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL
        assert "LIVE_LOCKED" in result.reason

    def test_fail_position_size_exceeded(self):
        gate = RiskGate()
        risk = _make_risk(pos_size=0.5)
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL

    def test_fail_open_positions_exceeded(self):
        gate = RiskGate()
        risk = _make_risk(open_pos=5)
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL

    def test_fail_margin_level_low(self):
        gate = RiskGate()
        risk = _make_risk(margin_level=150)
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL

    def test_fail_risk_per_trade_default_half_percent(self):
        gate = RiskGate()
        risk = _make_risk(risk_per_trade=0.6)
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL
        assert "Risk/trade" in result.reason

    def test_fail_correlated_exposure_cap(self):
        gate = RiskGate()
        risk = _make_risk(pos_size=0.05)
        risk.correlated_exposure_lots = 0.18
        risk.max_correlated_exposure_lots = 0.2
        result = gate.evaluate(risk)
        assert result.status == GateStatus.FAIL
        assert "Correlated exposure" in result.reason


class TestExecutionGate:
    def test_pass_valid_order(self):
        gate = ExecutionGate()
        order = BrokerOrderRequest(
            order_id="ord-001",
            decision_ref="dec-001",
            symbol="EUR/USD",
            direction=Direction.LONG,
            volume=0.05,
            stop_loss=1.0800,
            take_profit=1.0950,
        )
        result = gate.evaluate(order, current_price=1.0850)
        assert result.status == GateStatus.PASS

    def test_fail_duplicate_order(self):
        gate = ExecutionGate()
        order1 = BrokerOrderRequest(
            order_id="ord-001", decision_ref="dec-001", symbol="EUR/USD",
            direction=Direction.LONG, volume=0.05, stop_loss=1.0800, take_profit=1.0950,
        )
        order2 = BrokerOrderRequest(
            order_id="ord-002", decision_ref="dec-002", symbol="EUR/USD",
            direction=Direction.LONG, volume=0.05, stop_loss=1.0800, take_profit=1.0950,
        )
        gate.evaluate(order1, current_price=1.0850)  # First passes
        result = gate.evaluate(order2, current_price=1.0850)  # Duplicate fails
        assert result.status == GateStatus.FAIL
        assert result.evidence["duplicate_detected"] is True

    def test_fail_slippage_exceeded(self):
        gate = ExecutionGate(max_slippage_points=10)
        order = BrokerOrderRequest(
            order_id="ord-001", decision_ref="dec-001", symbol="EUR/USD",
            direction=Direction.LONG, volume=0.05, stop_loss=1.0800, take_profit=1.0950,
            price=1.0900, slippage=50,
        )
        result = gate.evaluate(order, current_price=1.0850)
        assert result.status == GateStatus.FAIL

    def test_fail_tight_stop_loss(self):
        gate = ExecutionGate(min_stop_distance_pips=10)
        order = BrokerOrderRequest(
            order_id="ord-001", decision_ref="dec-001", symbol="EUR/USD",
            direction=Direction.LONG, volume=0.05, stop_loss=1.0845, take_profit=1.0950,
        )
        result = gate.evaluate(order, current_price=1.0850)
        # sl distance = 1.0850 - 1.0845 = 0.0005 = 5 pips < 10 min
        assert result.status == GateStatus.FAIL


class TestCASForexAuditor:
    def test_full_accept_flow(self):
        auditor = CASForexAuditor()
        proposal = _make_proposal()
        snapshot = _make_snapshot()
        risk = _make_risk()

        decision = auditor.evaluate(proposal, snapshot, risk)
        assert decision.verdict == Verdict.ACCEPT
        assert decision.is_accepted
        assert len(decision.gate_results) == 5  # compiler + risk + macro + market + execution
        assert all(g.status == GateStatus.PASS for g in decision.gate_results)

    def test_risk_lock_suppresses(self):
        auditor = CASForexAuditor()
        proposal = _make_proposal()
        snapshot = _make_snapshot()
        risk = _make_risk(daily_dd=3.0)

        decision = auditor.evaluate(proposal, snapshot, risk)
        assert decision.verdict == Verdict.SUPPRESS
        assert decision.overriding_gate == "risk"
        assert "LIVE_LOCKED" in decision.summary

    def test_market_closed_suppresses(self):
        auditor = CASForexAuditor()
        proposal = _make_proposal()
        snapshot = _make_snapshot(is_open=False)
        risk = _make_risk()

        decision = auditor.evaluate(proposal, snapshot, risk)
        assert decision.verdict == Verdict.SUPPRESS

    def test_build_order_from_proposal(self):
        auditor = CASForexAuditor()
        proposal = _make_proposal()
        risk = _make_risk()

        order = auditor.build_order(proposal, risk, decision_ref="dec-ref")
        assert order.symbol == "EUR/USD"
        assert order.direction == Direction.LONG
        assert order.volume == 0.05
        assert order.decision_ref == "dec-ref"
