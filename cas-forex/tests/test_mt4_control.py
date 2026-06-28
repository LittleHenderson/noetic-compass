"""Owner MT4 mailbox control + EA-readable round-trip coverage."""

from __future__ import annotations

import json
import os

import pytest

from cas_forex.config import config
from cas_forex import mt4_control
from cas_forex.mt4_control import (
    clear_mt4_control_overrides,
    read_ea_heartbeat,
    resolve_mt4_control,
    set_mt4_control_overrides,
)
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest


@pytest.fixture(autouse=True)
def _reset_overrides():
    clear_mt4_control_overrides()
    yield
    clear_mt4_control_overrides()


def _order() -> BrokerOrderRequest:
    return BrokerOrderRequest(
        order_id="test-mt4-order",
        decision_ref="decision-1",
        symbol="EUR/USD",
        direction=Direction.LONG,
        volume=0.1,
        price=1.1,
        stop_loss=1.095,
        take_profit=1.11,
    )


def test_overrides_take_precedence_over_config(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "mt4_enabled", False)
    monkeypatch.setattr(config, "mt4_mailbox_dir", None)

    assert resolve_mt4_control().enabled is False

    ctrl = set_mt4_control_overrides(enabled=True, mailbox_dir=str(tmp_path / "mbox"))
    assert ctrl.enabled is True
    assert ctrl.mailbox_dir == str(tmp_path / "mbox")
    assert resolve_mt4_control().enabled is True

    clear_mt4_control_overrides()
    assert resolve_mt4_control().enabled is False


def test_empty_mailbox_dir_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        set_mt4_control_overrides(mailbox_dir="   ")


def test_heartbeat_absent_present_and_stale(tmp_path):
    assert read_ea_heartbeat(tmp_path)["present"] is False

    hb = tmp_path / "heartbeat.json"
    hb.write_text(json.dumps({"schema": "cas_forex_mt4_heartbeat.v1", "state": "TIMER", "server": "Demo"}), encoding="utf-8")
    fresh = read_ea_heartbeat(tmp_path)
    assert fresh["present"] is True
    assert fresh["fresh"] is True
    assert fresh["state"] == "TIMER"

    # Backdate the file well past the freshness window.
    old = mt4_control.HEARTBEAT_FRESH_SECONDS + 120
    past = hb.stat().st_mtime - old
    os.utime(hb, (past, past))
    stale = read_ea_heartbeat(tmp_path)
    assert stale["present"] is True
    assert stale["fresh"] is False


def test_execute_order_writes_ea_readable_command(monkeypatch, tmp_path):
    """The dispatch path must write commands/<id>.json the EA actually polls."""
    from cas_forex.broker.mt5_bridge import MT4EABridge

    mailbox = tmp_path / "mt4"
    monkeypatch.setattr(config, "paper_trading", True)
    monkeypatch.setattr(config, "live_mode", False)
    set_mt4_control_overrides(enabled=True, mailbox_dir=str(mailbox))

    bridge = MT4EABridge()
    outcome = bridge.execute_order(_order())

    assert outcome.broker_mode.value == "PAPER_MT4"
    # Legacy audit log still written...
    assert (mailbox / "orders.jsonl").exists()
    # ...and the EA-readable command file the EA polls.
    commands = list((mailbox / "commands").glob("*.json"))
    assert len(commands) == 1
    payload = json.loads(commands[0].read_text(encoding="utf-8"))
    assert payload["command_type"] == "PLACE_ORDER"
    assert payload["broker_mode"] == "PAPER_MT4"
    assert payload["live_money_authorized"] is False
