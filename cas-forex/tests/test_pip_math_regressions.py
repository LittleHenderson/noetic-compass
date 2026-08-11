"""USD/JPY pip math regressions."""

import sys
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
from cas_forex.schemas.order import BrokerOrderRequest, OrderStatus


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

        ACCOUNT_TRADE_MODE_DEMO = 0

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def account_info(self):
            return SimpleNamespace(server="MetaQuotes-Demo", company="MetaQuotes Demo", trade_mode=0)

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

        ACCOUNT_TRADE_MODE_DEMO = 0

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def account_info(self):
            return SimpleNamespace(server="MetaQuotes-Demo", company="MetaQuotes Demo", trade_mode=0)

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


def test_mt5_bridge_widens_market_stops_to_symbol_stop_level_for_indices():
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
        ACCOUNT_TRADE_MODE_DEMO = 0

        def __init__(self):
            self.sent = []

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def account_info(self):
            return SimpleNamespace(server="Hugosway-Demo", company="Hugo's Way", trade_mode=0)

        def symbol_info_tick(self, symbol):
            return SimpleNamespace(bid=38999.0, ask=39000.0)

        def symbol_info(self, symbol):
            return SimpleNamespace(
                point=1.0,
                digits=2,
                trade_stops_level=200,
                trade_freeze_level=0,
                filling_mode=2,
            )

        def order_send(self, request):
            self.sent.append(dict(request))
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_DONE,
                order=321,
                price=request["price"],
                commission=0.0,
                comment="done",
            )

    order = BrokerOrderRequest(
        order_id="us30-tight-stops",
        decision_ref="d-1",
        symbol="US30",
        direction=Direction.LONG,
        volume=0.01,
        price=0.0,
        stop_loss=38950.0,
        take_profit=39100.0,
    )
    fake = FakeMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    outcome = bridge.execute_order(order)

    assert outcome.status == OrderStatus.EXECUTED
    assert len(fake.sent) == 1
    sent = fake.sent[0]
    assert sent["price"] == 39000.0
    assert sent["price"] - sent["sl"] >= 201.0
    assert sent["tp"] - sent["price"] >= 201.0
    assert outcome.raw_request_snapshot["symbol"] == "US30"
    assert outcome.raw_request_snapshot["sl"] == sent["sl"]


def test_mt5_bridge_rejects_market_order_when_live_price_crossed_take_profit():
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
        ACCOUNT_TRADE_MODE_DEMO = 0

        def __init__(self):
            self.sent = []

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def account_info(self):
            return SimpleNamespace(server="Hugosway-Demo", company="Hugo's Way", trade_mode=0)

        def symbol_info_tick(self, symbol):
            return SimpleNamespace(bid=0.98040, ask=0.98057)

        def symbol_info(self, symbol):
            return SimpleNamespace(
                point=0.00001,
                digits=5,
                trade_stops_level=0,
                trade_freeze_level=0,
                filling_mode=1,
            )

        def order_send(self, request):
            self.sent.append(dict(request))
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_DONE,
                order=321,
                price=request["price"],
                commission=0.0,
                comment="done",
            )

    order = BrokerOrderRequest(
        order_id="audcad-stale",
        decision_ref="d-1",
        symbol="AUD/CAD",
        direction=Direction.LONG,
        volume=0.1,
        price=0.0,
        stop_loss=0.8971,
        take_profit=0.9005,
    )
    fake = FakeMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    outcome = bridge.execute_order(order)

    assert outcome.status == OrderStatus.REJECTED
    assert "market price invalidates order geometry" in (outcome.error_message or "")
    assert outcome.is_real_broker is False
    assert fake.sent == []
    assert outcome.raw_request_snapshot is None


def test_mt5_bridge_live_account_requires_gate_before_order_send():
    # GB-1 bridge-level hardening: a connected LIVE (non-demo) account must not
    # reach order_send without the owner live-trading gate, even with live_mode
    # off and even for a caller that bypasses the execution guard.
    sent: list = []

    class FakeLiveMT5:
        ACCOUNT_TRADE_MODE_DEMO = 0
        TRADE_RETCODE_DONE = 10009
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

        def account_info(self):
            # trade_mode=2 (REAL), server has no "demo" -> live account.
            return SimpleNamespace(server="HugosWay-Live", company="Hugo's Way", trade_mode=2)

        def order_send(self, request):
            sent.append(request)
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=1, price=150.0, commission=0.0, comment="done")

    order = BrokerOrderRequest(
        order_id="live-1",
        decision_ref="d-1",
        symbol="USD/JPY",
        direction=Direction.LONG,
        volume=0.05,
        price=150.00,
        stop_loss=149.50,
        take_profit=151.00,
    )
    bridge = MT5Bridge()
    bridge._mt5 = FakeLiveMT5()
    bridge._connected = True

    outcome = bridge.execute_order(order)

    assert outcome.status == OrderStatus.REJECTED
    assert "Live-trading gate not authorized" in (outcome.error_message or "")
    assert sent == []  # order_send must never be reached for an ungated live account


class _FakeLiveMT5:
    """A connected LIVE (non-demo) MT5 whose server label happens to contain 'demo'."""

    ACCOUNT_TRADE_MODE_DEMO = 0  # real=2, demo=0
    TRADE_RETCODE_DONE = 10009
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    POSITION_TYPE_BUY = 0

    def __init__(self):
        self.sent: list = []

    def terminal_info(self):
        return SimpleNamespace(connected=True)

    def account_info(self):
        # trade_mode=2 (REAL) but server contains the substring 'demo'.
        return SimpleNamespace(server="LiveDemo-Server", company="DemoTech Markets", trade_mode=2)

    def order_send(self, request):
        self.sent.append(request)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=1, price=150.0, commission=0.0, comment="done")

    def positions_get(self, ticket=None):
        return [SimpleNamespace(symbol="USD/JPY", type=self.POSITION_TYPE_BUY, volume=0.05, ticket=ticket or 1)]

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=150.0, ask=150.02)

    def symbol_info(self, symbol):
        return SimpleNamespace(point=0.001, filling_mode=1)


def _jpy_order():
    return BrokerOrderRequest(
        order_id="jpy-live",
        decision_ref="d-1",
        symbol="USD/JPY",
        direction=Direction.LONG,
        volume=0.05,
        price=150.00,
        stop_loss=149.50,
        take_profit=151.00,
    )


def test_mt5_bridge_blocks_terminal_algo_off_before_order_send():
    class FakeDemoMT5:
        ACCOUNT_TRADE_MODE_DEMO = 0

        def __init__(self):
            self.sent: list = []

        def terminal_info(self):
            return SimpleNamespace(connected=True, trade_allowed=False, tradeapi_disabled=False)

        def account_info(self):
            return SimpleNamespace(
                server="MetaQuotes-Demo",
                company="MetaQuotes Demo",
                trade_mode=0,
                trade_allowed=True,
                trade_expert=True,
            )

        def order_send(self, request):
            self.sent.append(request)
            raise AssertionError("order_send must not run when MT5 Algo Trading is off")

    fake = FakeDemoMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    outcome = bridge.execute_order(_jpy_order())

    assert outcome.status == OrderStatus.REJECTED
    assert "MT5 Algo Trading is off" in (outcome.error_message or "")
    assert outcome.is_real_broker is False
    assert fake.sent == []


def test_live_account_with_demo_in_server_name_is_still_gated():
    # Regression: a broker-controlled server/company string containing 'demo'
    # must NOT downgrade a real (trade_mode=2) account to paper and skip the gate.
    fake = _FakeLiveMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    assert bridge.is_demo_account() is False
    outcome = bridge.execute_order(_jpy_order())
    assert outcome.status == OrderStatus.REJECTED
    assert fake.sent == []  # order_send never reached


def test_owner_override_treat_account_as_demo_allows_fill(monkeypatch):
    # The explicit owner loosen: declare the account paper -> no live gate.
    from cas_forex.config import config as global_config

    monkeypatch.setattr(global_config, "mt5_treat_account_as_demo", True)
    fake = _FakeLiveMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    assert bridge.is_demo_account() is True
    outcome = bridge.execute_order(_jpy_order())
    assert outcome.status == OrderStatus.EXECUTED
    assert len(fake.sent) == 1


def test_close_position_is_gated_on_live_account():
    # close_position is a real order_send too -> gated the same as execute_order.
    fake = _FakeLiveMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    assert bridge.close_position(1) is False
    assert fake.sent == []  # the close order_send must be refused


def test_close_position_allowed_when_owner_declares_demo(monkeypatch):
    from cas_forex.config import config as global_config

    monkeypatch.setattr(global_config, "mt5_treat_account_as_demo", True)
    fake = _FakeLiveMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True

    assert bridge.close_position(1) is True
    assert len(fake.sent) == 1


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


def test_mt5_bridge_initialize_uses_configured_terminal_path_without_empty_credentials(monkeypatch):
    class FakeMT5:
        def __init__(self):
            self.initialize_calls = []

        def initialize(self, **kwargs):
            self.initialize_calls.append(kwargs)
            return True

        def terminal_info(self):
            return SimpleNamespace(connected=True)

    fake = FakeMT5()
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    monkeypatch.setattr(mt5_module.config, "mt5_path", r"C:\Program Files\Broker\terminal64.exe")
    monkeypatch.setattr(mt5_module.config, "mt5_login", 0)
    monkeypatch.setattr(mt5_module.config, "mt5_password", "")
    monkeypatch.setattr(mt5_module.config, "mt5_server", "")

    bridge = MT5Bridge()

    assert bridge.connect() is True
    assert fake.initialize_calls == [
        {"timeout": mt5_module.MT5_INIT_TIMEOUT_MS, "path": r"C:\Program Files\Broker\terminal64.exe"}
    ]


def test_mt5_bridge_initialize_auto_uses_known_terminal_path(tmp_path, monkeypatch):
    class FakeMT5:
        def __init__(self):
            self.initialize_calls = []
            self._account = SimpleNamespace(login=123456)

        def initialize(self, **kwargs):
            self.initialize_calls.append(kwargs)
            return True

        def account_info(self):
            return self._account

        def terminal_info(self):
            return SimpleNamespace(connected=True)

    terminal = tmp_path / "Hugosway PRO5 Terminal" / "terminal64.exe"
    terminal.parent.mkdir()
    terminal.write_text("fake terminal", encoding="utf-8")
    fake = FakeMT5()
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    monkeypatch.setattr(mt5_module.config, "mt5_path", None)
    monkeypatch.setattr(mt5_module.config, "mt5_login", 123456)
    monkeypatch.setattr(mt5_module.config, "mt5_password", "secret")
    monkeypatch.setattr(mt5_module.config, "mt5_server", "Broker-Demo")
    monkeypatch.setattr(mt5_module, "COMMON_MT5_TERMINAL_PATHS", (str(terminal),))

    bridge = MT5Bridge()

    assert bridge.mt5_path == str(terminal)
    assert bridge.connect() is True
    assert fake.initialize_calls == [
        {"timeout": mt5_module.MT5_INIT_TIMEOUT_MS, "path": str(terminal)}
    ]


class _FakeMT5Attach:
    """Records initialize() calls; reports a configurable attached account."""

    def __init__(self, attached_login):
        self.initialize_calls = []
        self.shutdown_calls = 0
        self._attached_login = attached_login

    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        return True

    def account_info(self):
        return SimpleNamespace(login=self._attached_login)

    def terminal_info(self):
        return SimpleNamespace(connected=True)

    def shutdown(self):
        self.shutdown_calls += 1


def _set_mt5_config(monkeypatch):
    monkeypatch.setattr(mt5_module.config, "mt5_path", r"C:\Program Files\Broker\terminal64.exe")
    monkeypatch.setattr(mt5_module.config, "mt5_login", 123456)
    monkeypatch.setattr(mt5_module.config, "mt5_password", "secret")
    monkeypatch.setattr(mt5_module.config, "mt5_server", "Broker-Demo")


def test_mt5_bridge_attaches_without_relogin_when_account_matches(monkeypatch):
    # Terminal already logged into the configured account -> attach only (a bare
    # initialize with path), never re-login with credentials (a re-login into an
    # already-logged-in terminal fails with "IPC send failed").
    fake = _FakeMT5Attach(attached_login=123456)
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    _set_mt5_config(monkeypatch)

    bridge = MT5Bridge()
    t = mt5_module.MT5_INIT_TIMEOUT_MS
    assert bridge.connect() is True
    assert fake.initialize_calls == [{"timeout": t, "path": r"C:\Program Files\Broker\terminal64.exe"}]
    assert fake.shutdown_calls == 0


def test_mt5_bridge_relogins_with_credentials_on_account_mismatch(monkeypatch):
    # Terminal logged into a DIFFERENT account -> attach, then re-login with creds.
    fake = _FakeMT5Attach(attached_login=999999)
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    _set_mt5_config(monkeypatch)

    bridge = MT5Bridge()
    t = mt5_module.MT5_INIT_TIMEOUT_MS
    assert bridge.connect() is True
    assert fake.initialize_calls == [
        {"timeout": t, "path": r"C:\Program Files\Broker\terminal64.exe"},
        {
            "timeout": t,
            "path": r"C:\Program Files\Broker\terminal64.exe",
            "login": 123456,
            "password": "secret",
            "server": "Broker-Demo",
        },
    ]
    assert fake.shutdown_calls == 1


def test_get_bridge_live_mode_refuses_disconnected_mt5(monkeypatch):
    from cas_forex import runtime_gates

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
    monkeypatch.setattr(runtime_gates, "require_authorized", lambda *args, **kwargs: None)

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
    assert yahoo_ticker("SPX500") == "^GSPC"
    assert yahoo_ticker("XAU/USD") == "GC=F"
    assert broker_symbol("SPX500") == "SPX500"
    assert broker_symbol("XAU/USD") == "XAUUSD"


def test_forex_fury_crosses_have_explicit_yahoo_and_broker_mappings():
    assert yahoo_ticker("AUD/CAD") == "AUDCAD=X"
    assert yahoo_ticker("GBP/AUD") == "GBPAUD=X"
    assert broker_symbol("AUD/CAD") == "AUDCAD"
    assert broker_symbol("GBP/AUD") == "GBPAUD"
    assert pip_value_per_lot("AUD/CAD", 0.9) == pytest.approx(10.0)
    assert pip_value_per_lot("GBP/AUD", 1.92) == pytest.approx(10.0)


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
