"""USD/JPY pip math regressions."""

from types import SimpleNamespace

import pytest

from cas_forex.backtest.engine import BacktestEngine, TradeRecord
import cas_forex.broker.mt5_bridge as mt5_module
from cas_forex.broker.mt5_bridge import MT5Bridge
from cas_forex.forecast.integrity import ForecastIntegrityGate
from cas_forex.instruments import (
    broker_symbol,
    pip_value_per_lot,
    usd_notional,
    yahoo_ticker,
)
from cas_forex.schemas.decision import CASDecision, Verdict
from cas_forex.schemas.forecast import Direction, ForecastProposal, ModelSource
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.schemas.order import BrokerOrderRequest


def _jpy_proposal():
    return ForecastProposal(
        proposal_id="jpy-prop",
        symbol="USD/JPY",
        direction=Direction.LONG,
        entry_price=150.00,
        stop_loss=149.50,
        take_profit=151.00,
        confidence=0.8,
        model_source=ModelSource.TECHNICAL,
        rationale="test",
    )


def test_mt5_bridge_reports_usdjpy_slippage_in_jpy_pips():
    class FakeMT5:
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_REJECT = 10006
        TRADE_RETCODE_CANCEL = 10007
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TYPE_BUY_LIMIT = 2
        ORDER_TYPE_SELL_LIMIT = 3
        ORDER_TYPE_BUY_STOP = 4
        ORDER_TYPE_SELL_STOP = 5
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def order_send(self, request):
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_DONE,
                order=123,
                price=150.01,
                commission=0.0,
                comment="done",
            )

    order = BrokerOrderRequest(
        order_id="jpy-order",
        decision_ref="d-1",
        symbol="USD/JPY",
        direction=Direction.LONG,
        volume=0.05,
        price=150.00,
        stop_loss=149.50,
        take_profit=151.00,
    )
    bridge = MT5Bridge()
    bridge._mt5 = FakeMT5()
    bridge._connected = True

    outcome = bridge.execute_order(order)

    assert outcome.slippage_pips == pytest.approx(1.0)


def test_mt5_bridge_compares_abnormal_slippage_points_as_pips():
    class FakeMT5:
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_REJECT = 10006
        TRADE_RETCODE_CANCEL = 10007
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TYPE_BUY_LIMIT = 2
        ORDER_TYPE_SELL_LIMIT = 3
        ORDER_TYPE_BUY_STOP = 4
        ORDER_TYPE_SELL_STOP = 5
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def symbol_info(self, symbol):
            return SimpleNamespace(point=0.00001)

        def order_send(self, request):
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_DONE,
                order=123,
                price=1.10040,
                commission=0.0,
                comment="done",
            )

    order = BrokerOrderRequest(
        order_id="eur-slip",
        decision_ref="d-1",
        symbol="EUR/USD",
        direction=Direction.LONG,
        volume=0.05,
        price=1.10000,
        stop_loss=1.09500,
        take_profit=1.11000,
        slippage=30,
    )
    bridge = MT5Bridge()
    bridge._mt5 = FakeMT5()
    bridge._connected = True

    outcome = bridge.execute_order(order)

    assert outcome.slippage_pips == pytest.approx(4.0)
    assert outcome.is_abnormal_slippage is True


def test_get_bridge_attempts_mt5_connect_before_simulated_fallback(monkeypatch):
    class FakeBridge:
        def __init__(self):
            self.connect_called = False

        def connect(self):
            self.connect_called = True
            return True

        def is_connected(self):
            return self.connect_called

    fake = FakeBridge()
    monkeypatch.setattr(mt5_module.config, "live_mode", False)
    monkeypatch.setattr(mt5_module.config, "paper_trading", True)
    monkeypatch.setattr(mt5_module.config, "mt5_login", 123)
    monkeypatch.setattr(mt5_module, "MT5Bridge", lambda: fake)

    assert mt5_module.get_bridge() is fake
    assert fake.connect_called is True


def test_get_bridge_live_mode_refuses_disconnected_mt5(monkeypatch):
    class FakeBridge:
        def __init__(self):
            self.connect_called = False

        def connect(self):
            self.connect_called = True
            return False

    fake = FakeBridge()
    monkeypatch.setattr(mt5_module.config, "live_mode", True)
    monkeypatch.setattr(mt5_module.config, "paper_trading", False)
    monkeypatch.setattr(mt5_module.config, "mt5_login", 123)
    monkeypatch.setattr(mt5_module.config, "mt5_password", "secret")
    monkeypatch.setattr(mt5_module.config, "mt5_server", "Broker-Live")
    monkeypatch.setattr(mt5_module.config, "prefer_mt5", True)
    monkeypatch.setattr(mt5_module.config, "owner_enable_live_trading", True)
    monkeypatch.setattr(mt5_module.config, "live_trading_licensed", True)
    monkeypatch.setattr(mt5_module.config, "personal_account_ack", True)
    monkeypatch.setattr(mt5_module.config, "no_pooled_capital_ack", True)
    monkeypatch.setattr(mt5_module.config, "account_type", "personal")
    monkeypatch.setattr(mt5_module, "MT5Bridge", lambda: fake)

    with pytest.raises(ConnectionError, match="refusing live fallback"):
        mt5_module.get_bridge()
    assert fake.connect_called is True


def test_get_bridge_live_mode_blocked_when_not_licensed(monkeypatch):
    """Owner-controlled gate: live trading stays unauthorized without the owner
    enable flag, even when acks/credentials are present.

    Account-type and source-of-funds acks alone must not authorize live
    execution; the explicit owner enable flag must also be on. This proves the
    reported status is enforced at the real broker path - and that it is a
    fail-closed default, not a value that can be active without owner enablement.
    """

    def _boom():  # pragma: no cover - must never be constructed
        raise AssertionError("MT5Bridge must not be built while NOT LICENSED")

    monkeypatch.setattr(mt5_module.config, "live_mode", True)
    monkeypatch.setattr(mt5_module.config, "paper_trading", False)
    monkeypatch.setattr(mt5_module.config, "mt5_login", 123)
    monkeypatch.setattr(mt5_module.config, "mt5_password", "secret")
    monkeypatch.setattr(mt5_module.config, "mt5_server", "Broker-Live")
    monkeypatch.setattr(mt5_module.config, "prefer_mt5", True)
    monkeypatch.setattr(mt5_module.config, "owner_enable_live_trading", False)
    monkeypatch.setattr(mt5_module.config, "live_trading_licensed", False)
    monkeypatch.setattr(mt5_module.config, "personal_account_ack", True)
    monkeypatch.setattr(mt5_module.config, "no_pooled_capital_ack", True)
    monkeypatch.setattr(mt5_module.config, "account_type", "personal")
    monkeypatch.setattr(mt5_module, "MT5Bridge", _boom)

    with pytest.raises(PermissionError, match="NOT LICENSED"):
        mt5_module.get_bridge()


def test_backtest_books_usdjpy_profit_pips_and_account_value():
    proposal = _jpy_proposal()
    decision = CASDecision(
        decision_id="d-1",
        proposal_ref=proposal.proposal_id,
        symbol="USD/JPY",
        verdict=Verdict.ACCEPT,
    )
    engine = BacktestEngine(position_size_lots=0.05, spread_pips=1.0)
    trade = TradeRecord(proposal, decision)
    trade.entry_price = 150.00
    engine.open_positions.append(trade)

    engine._close_trade(
        trade,
        {"close": 150.20, "timestamp": "2026-06-17T00:00:00"},
        lot_pips=0.10,
        forced=True,
    )

    assert trade.profit_pips == pytest.approx(19.0)
    expected_pip_value = (100000 * 0.01) / 150.20
    assert trade.profit_account == pytest.approx(19.0 * expected_pip_value * 0.05)


def test_index_symbol_uses_point_value_not_fx_units():
    proposal = ForecastProposal(
        proposal_id="nas-prop",
        symbol="NAS100",
        direction=Direction.LONG,
        entry_price=19000.0,
        stop_loss=18900.0,
        take_profit=19200.0,
        confidence=0.8,
        model_source=ModelSource.TECHNICAL,
    )
    decision = CASDecision(
        decision_id="d-nas",
        proposal_ref=proposal.proposal_id,
        symbol="NAS100",
        verdict=Verdict.ACCEPT,
    )
    engine = BacktestEngine(position_size_lots=0.5, spread_pips=1.0)
    trade = TradeRecord(proposal, decision)
    trade.entry_price = 19000.0
    engine.open_positions.append(trade)

    engine._close_trade(
        trade,
        {"close": 19100.0, "timestamp": "2026-06-17T00:00:00"},
        lot_pips=0.10,
        forced=True,
    )

    assert proposal.risk_pips == pytest.approx(100.0)
    assert proposal.reward_pips == pytest.approx(200.0)
    assert trade.profit_pips == pytest.approx(99.0)
    assert trade.profit_account == pytest.approx(49.5)
    assert pip_value_per_lot("NAS100", 19100.0) == pytest.approx(1.0)
    assert usd_notional("NAS100", 19100.0, 0.5) == pytest.approx(9550.0)


def test_gold_symbol_uses_contract_point_value():
    proposal = ForecastProposal(
        proposal_id="xau-prop",
        symbol="XAU/USD",
        direction=Direction.LONG,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        confidence=0.8,
        model_source=ModelSource.TECHNICAL,
    )
    decision = CASDecision(
        decision_id="d-xau",
        proposal_ref=proposal.proposal_id,
        symbol="XAU/USD",
        verdict=Verdict.ACCEPT,
    )
    engine = BacktestEngine(position_size_lots=0.1, spread_pips=0.5)
    trade = TradeRecord(proposal, decision)
    trade.entry_price = 2300.0
    engine.open_positions.append(trade)

    engine._close_trade(
        trade,
        {"close": 2310.0, "timestamp": "2026-06-17T00:00:00"},
        lot_pips=0.10,
        forced=True,
    )

    assert proposal.risk_pips == pytest.approx(10.0)
    assert proposal.reward_pips == pytest.approx(20.0)
    assert trade.profit_pips == pytest.approx(9.5)
    assert trade.profit_account == pytest.approx(95.0)
    assert pip_value_per_lot("XAU/USD", 2310.0) == pytest.approx(100.0)
    assert usd_notional("XAU/USD", 2310.0, 0.1) == pytest.approx(23100.0)


def test_non_fx_symbol_mappings_are_explicit():
    assert yahoo_ticker("NAS100") == "^NDX"
    assert yahoo_ticker("US30") == "^DJI"
    assert yahoo_ticker("XAU/USD") == "GC=F"
    assert broker_symbol("XAU/USD") == "XAUUSD"


def test_integrity_uses_symbol_aware_spread_and_atr_pips():
    proposal = _jpy_proposal()
    snapshot = MarketSnapshot(
        symbol="USD/JPY",
        bid=150.00,
        ask=150.02,
        spread=2.0,
        session="LONDON",
    )

    vals = ForecastIntegrityGate._collect_evidence_values(
        proposal,
        snapshot,
        candles=[],
        atr=None,
        baselines={},
    )
    assert 0.02 in vals

    limiting, impact = ForecastIntegrityGate()._find_limiting_reagent(
        proposal,
        snapshot,
        atr=0.20,
        lacunarity_voids=[],
    )
    assert limiting is None
    assert impact == 0.0
