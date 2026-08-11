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

import json

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


def test_simulated_partial_close_reduces_volume_instead_of_flattening_position():
    bridge = SimulatedBrokerBridge()
    ticket = bridge.execute_order(_order(volume=0.04)).broker_ticket
    assert ticket is not None

    assert bridge.close_position(ticket, volume=0.02) is True

    positions = bridge.get_open_positions()
    assert len(positions) == 1
    assert positions[0]["ticket"] == ticket
    assert positions[0]["volume"] == 0.02


def test_simulated_ticket_is_stable_across_bridge_recreation():
    order = _order()

    first = SimulatedBrokerBridge().execute_order(order)
    second = SimulatedBrokerBridge().execute_order(order)

    assert first.broker_ticket == second.broker_ticket
    assert first.broker_ticket != 100000


def test_simulated_bridge_rejects_duplicate_order_id():
    bridge = SimulatedBrokerBridge()
    order = _order()

    first = bridge.execute_order(order)
    duplicate = bridge.execute_order(order)

    assert first.status == OrderStatus.EXECUTED
    assert duplicate.status == OrderStatus.REJECTED
    assert duplicate.is_duplicate is True
    assert duplicate.broker_ticket == first.broker_ticket


def test_simulated_different_orders_receive_different_tickets():
    bridge = SimulatedBrokerBridge()
    first = bridge.execute_order(_order())
    second_order = _order().model_copy(update={"order_id": "be-EURUSD-2"})
    second = bridge.execute_order(second_order)

    assert first.broker_ticket != second.broker_ticket


def test_simulated_paper_state_survives_bridge_recreation(tmp_path):
    state = tmp_path / "simulated-broker-state.json"
    first_bridge = SimulatedBrokerBridge(state_path=state)
    fill = first_bridge.execute_order(_order(volume=0.04))
    assert fill.broker_ticket is not None

    restored = SimulatedBrokerBridge(state_path=state)
    positions = restored.get_open_positions()

    assert len(positions) == 1
    assert positions[0]["ticket"] == fill.broker_ticket
    assert positions[0]["volume"] == 0.04

    restored.modify_position(fill.broker_ticket, stop_loss=1.1000, take_profit=1.1200)
    after_modify = SimulatedBrokerBridge(state_path=state).get_open_positions()[0]
    assert after_modify["stop_loss"] == 1.1000
    assert after_modify["take_profit"] == 1.1200

    assert SimulatedBrokerBridge(state_path=state).close_position(fill.broker_ticket) is True
    assert SimulatedBrokerBridge(state_path=state).get_open_positions() == []


def test_simulated_paper_state_reconciles_closed_outcome_ticket(tmp_path):
    state = tmp_path / "simulated-broker-state.json"
    ledger = tmp_path / "paper-outcomes.json"
    bridge = SimulatedBrokerBridge(
        state_path=state,
        closed_ticket_ledger_path=ledger,
    )
    fill = bridge.execute_order(_order())
    ledger.write_text(
        json.dumps({"history_records": [{"broker_ticket": str(fill.broker_ticket)}]}),
        encoding="utf-8",
    )

    restored = SimulatedBrokerBridge(
        state_path=state,
        closed_ticket_ledger_path=ledger,
    )

    assert restored.get_open_positions() == []
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["open_position_count"] == 0


def test_simulated_paper_position_can_be_voided_without_fabricated_pnl(tmp_path):
    state = tmp_path / "simulated-broker-state.json"
    bridge = SimulatedBrokerBridge(state_path=state)
    fill = bridge.execute_order(_order())

    assert bridge.void_position(
        fill.broker_ticket,
        reason="forming_candle_reemission_bug",
        evidence={"incident": "test"},
    ) is True

    restored = SimulatedBrokerBridge(state_path=state)
    assert restored.get_open_positions() == []
    voids = restored.get_void_events()
    assert len(voids) == 1
    assert voids[0]["broker_ticket"] == str(fill.broker_ticket)
    assert voids[0]["reason"] == "forming_candle_reemission_bug"
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["close_events"] == []
    assert payload["void_event_count"] == 1
    assert payload["balance"] == 10000.0


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
    assert outcome.is_demo_account is False
    assert outcome.broker_mode == BrokerMode.LIVE_MT5
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
    assert outcome.is_real_broker is True
    assert outcome.is_demo_account is True
    assert outcome.broker_mode == BrokerMode.PAPER_MT5
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
