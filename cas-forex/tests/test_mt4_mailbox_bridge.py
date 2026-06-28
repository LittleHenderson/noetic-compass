"""MT4 mailbox bridge contract coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cas_forex.broker.mt4_mailbox_bridge import (
    RECEIPT_SCHEMA,
    MT4MailboxBridge,
    build_mt4_mailbox_probe,
    hash_payload,
)
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerMode, BrokerOrderRequest


def _sample_order() -> BrokerOrderRequest:
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


def test_mt4_mailbox_probe_creates_paper_directories_and_ping(tmp_path):
    report = build_mt4_mailbox_probe(tmp_path)

    assert report["report_kind"] == "cas_forex_mt4_mailbox_probe"
    assert report["status"] == "MAILBOX_READY"
    assert report["broker_mode"] == "PAPER_MT4"
    assert report["live_money_authorized"] is False
    assert report["broker_accept_status"] == "NOT LICENSED"
    assert "does not place live orders" in report["claim_boundary"]
    assert (tmp_path / "commands").exists()
    assert (tmp_path / "receipts").exists()
    assert (tmp_path / "archive").exists()
    assert (tmp_path / "commands" / f"{report['ping_command']['command_id']}.json").exists()


def test_mt4_mailbox_bridge_writes_order_intent_with_hash(tmp_path):
    bridge = MT4MailboxBridge(tmp_path)
    command = bridge.write_order_intent(_sample_order())

    path = tmp_path / "commands" / f"{command['command_id']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert command["broker_mode"] == "PAPER_MT4"
    assert command["live_money_authorized"] is False
    assert payload["command_type"] == "PLACE_ORDER"
    assert payload["order"]["symbol"] == "EUR/USD"
    assert payload["raw_request_hash"] == command["raw_request_hash"]
    payload_without_hash = dict(payload)
    payload_without_hash.pop("raw_request_hash")
    assert hash_payload(payload_without_hash) == command["raw_request_hash"]


def test_mt4_mailbox_bridge_blocks_live_intent_without_explicit_authorization(tmp_path):
    bridge = MT4MailboxBridge(tmp_path)

    with pytest.raises(ValueError, match="LIVE_MT4"):
        bridge.write_order_intent(_sample_order(), broker_mode=BrokerMode.LIVE_MT4)


def test_mt4_mailbox_bridge_reads_valid_receipts(tmp_path):
    bridge = MT4MailboxBridge(tmp_path)
    command = bridge.write_order_intent(_sample_order())
    receipt_payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": "receipt-1",
        "command_id": command["command_id"],
        "status": "ACKNOWLEDGED",
        "created_at": "2026-06-24T00:00:00Z",
        "raw_response_hash": "abc123",
    }
    receipt_path = tmp_path / "receipts" / "receipt-1.json"
    receipt_path.write_text(json.dumps(receipt_payload), encoding="utf-8")

    receipts = bridge.read_receipts(command["command_id"])

    assert len(receipts) == 1
    assert receipts[0]["receipt_id"] == "receipt-1"
    assert receipts[0]["receipt_path"] == str(receipt_path)


def test_mt4_bridge_ea_contains_receipt_writer_contract():
    ea_path = Path(__file__).resolve().parents[1] / "mt4" / "Experts" / "CASForexBridgeEA.mq4"
    source = ea_path.read_text(encoding="utf-8")

    for required_function in [
        "ProcessCommandMailbox",
        "ProcessCommandFile",
        "HandlePlaceOrderCommand",
        "WriteReceipt",
        "JsonObject",
        "JsonRawValue",
        "AccountSnapshotJson",
    ]:
        assert required_function in source

    for required_field in [
        "cas_forex_mt4_mailbox_command.v1",
        "cas_forex_mt4_mailbox_receipt.v1",
        "raw_request_hash",
        "raw_response_hash",
        "terminal_name",
        "account_id_hash",
        "account_snapshot",
        "live_trading_allowed",
        "broker_ticket",
        "filled_price",
        "filled_volume",
        "slippage_pips",
    ]:
        assert required_field in source

    assert "OrderSend(" in source
    assert "LiveTradingAllowed" in source
    assert "PAPER_MT4" in source
    assert "LIVE_MT4" in source
