"""Tests for BrokerBridge.modify_position — the breakeven principal-lock primitive.

modify_position moves an OPEN, already-authorized position's stop-loss (toward
breakeven) and optionally its take-profit. It is RISK-REDUCING: it opens no new
exposure, so it needs no edge PASS token. A LIVE modify must still pass the owner
live-trading authorization, exactly like execute_order / close_position.

Covered here:
  * SimulatedBrokerBridge.modify_position moves the in-memory SL (and TP).
  * An unknown ticket is REJECTED, not crashed.
  * The MT5 LIVE path requires owner live-trading authorization (REJECTED when
    the gate is not authorized; the broker order_send is never reached).
  * The MT4 mailbox path writes a paper-only MODIFY_SL command (never live money).
"""

from cas_forex.broker.mt5_bridge import (
    MT5Bridge,
    SimulatedBrokerBridge,
)
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import (
    BrokerMode,
    BrokerOrderRequest,
    OrderStatus,
    OrderType,
)


def _order(symbol: str = "EUR/USD", volume: float = 0.1) -> BrokerOrderRequest:
    return BrokerOrderRequest(
        order_id=f"be-{symbol.replace('/', '')}-1",
        decision_ref="breakeven:test",
        symbol=symbol,
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=volume,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_BREAKEVEN_TEST",
    )


def test_simulated_modify_moves_stop_loss():
    bridge = SimulatedBrokerBridge()
    fill = bridge.execute_order(_order())
    assert fill.status == OrderStatus.EXECUTED
    ticket = fill.broker_ticket
    assert ticket is not None

    # Move SL to entry (breakeven principal-lock).
    new_sl = 1.1000
    outcome = bridge.modify_position(ticket, stop_loss=new_sl)

    assert outcome.status == OrderStatus.EXECUTED
    assert outcome.broker_ticket == ticket
    assert outcome.is_real_broker is False
    assert outcome.broker_mode == BrokerMode.SIMULATED
    # The in-memory open position now carries the locked stop.
    assert bridge._positions[ticket]["stop_loss"] == new_sl
    # TP untouched when take_profit is omitted.
    assert "take_profit" not in bridge._positions[ticket]


def test_simulated_modify_can_also_set_take_profit():
    bridge = SimulatedBrokerBridge()
    ticket = bridge.execute_order(_order()).broker_ticket

    outcome = bridge.modify_position(ticket, stop_loss=1.1000, take_profit=1.1200)

    assert outcome.status == OrderStatus.EXECUTED
    assert bridge._positions[ticket]["stop_loss"] == 1.1000
    assert bridge._positions[ticket]["take_profit"] == 1.1200


def test_simulated_modify_unknown_ticket_is_rejected_not_crash():
    bridge = SimulatedBrokerBridge()
    outcome = bridge.modify_position(99999999, stop_loss=1.1000)

    assert outcome.status == OrderStatus.REJECTED
    assert outcome.is_real_broker is False
    assert "No open position" in (outcome.error_message or "")


class _FakeMT5Position:
    def __init__(self, ticket, symbol="EURUSD"):
        self.ticket = ticket
        self.symbol = symbol
        self.tp = 1.1100
        self.magic = 20260601


class _FakeMT5Module:
    """Minimal MT5 stub so we can assert the LIVE gate runs BEFORE order_send."""

    TRADE_ACTION_SLTP = 7
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010

    def __init__(self):
        self.order_send_called = False

    def positions_get(self, ticket=None):
        return (_FakeMT5Position(ticket or 1),)

    def order_send(self, request):
        self.order_send_called = True

        class _R:
            retcode = 10009
            comment = "ok"

        return _R()


def _live_mt5_bridge(fake_mt5):
    """A connected, LIVE (non-demo) MT5 bridge wired to the fake module."""
    bridge = MT5Bridge.__new__(MT5Bridge)
    bridge.login = 12345
    bridge.password = "x"
    bridge.server = "LiveServer"
    bridge.prefer_mt5 = True
    bridge._mt5 = fake_mt5
    bridge._connected = True
    bridge.is_connected = lambda: True
    bridge.is_demo_account = lambda: False  # LIVE account
    return bridge


def test_mt5_live_modify_requires_authorization(monkeypatch):
    """A LIVE modify with an unauthorized owner gate is REJECTED and never
    reaches the broker order_send — the gate is fail-closed."""
    from cas_forex import runtime_gates

    def _deny(capability, config=None):
        raise PermissionError("live_trading not authorized in test")

    monkeypatch.setattr(runtime_gates, "require_authorized", _deny)

    fake = _FakeMT5Module()
    bridge = _live_mt5_bridge(fake)

    outcome = bridge.modify_position(1, stop_loss=1.1000)

    assert outcome.status == OrderStatus.REJECTED
    assert "Live-trading gate not authorized" in (outcome.error_message or "")
    # Fail-closed: no broker modify was attempted.
    assert fake.order_send_called is False


def test_mt5_live_modify_executes_when_authorized(monkeypatch):
    """With the owner gate authorized, the LIVE modify reaches order_send and
    reports EXECUTED. (Authorization is the only thing gating a risk-reducing
    modify — it amplifies/protects an existing authorized position.)"""
    from cas_forex import runtime_gates

    monkeypatch.setattr(runtime_gates, "require_authorized", lambda *a, **k: None)

    fake = _FakeMT5Module()
    bridge = _live_mt5_bridge(fake)

    outcome = bridge.modify_position(1, stop_loss=1.1000)

    assert outcome.status == OrderStatus.EXECUTED
    assert outcome.is_real_broker is True
    assert fake.order_send_called is True


def test_mt5_demo_modify_skips_live_gate(monkeypatch):
    """A connected DEMO account is paper — the live gate does not apply, so a
    modify executes even if live authorization would be denied."""
    from cas_forex import runtime_gates

    def _deny(capability, config=None):
        raise PermissionError("would block if it were consulted")

    monkeypatch.setattr(runtime_gates, "require_authorized", _deny)

    fake = _FakeMT5Module()
    bridge = _live_mt5_bridge(fake)
    bridge.is_demo_account = lambda: True  # paper account

    outcome = bridge.modify_position(1, stop_loss=1.1000)

    assert outcome.status == OrderStatus.EXECUTED
    assert fake.order_send_called is True


def test_mt4_mailbox_modify_writes_paper_command(tmp_path):
    """The MT4 mailbox MODIFY_SL command is paper/demo-only and never live."""
    from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge

    bridge = MT4MailboxBridge(mailbox_dir=tmp_path)
    command = bridge.write_modify_intent(4242, stop_loss=1.1000, take_profit=1.1200)

    assert command["command_type"] == "MODIFY_SL"
    assert command["broker_mode"] == BrokerMode.PAPER_MT4.value
    assert command["live_money_authorized"] is False
    import json

    written = json.loads(
        (tmp_path / "commands" / f"{command['command_id']}.json").read_text("utf-8")
    )
    assert written["ticket"] == 4242
    assert written["stop_loss"] == 1.1000
    assert written["take_profit"] == 1.1200
    assert written["command_type"] == "MODIFY_SL"
