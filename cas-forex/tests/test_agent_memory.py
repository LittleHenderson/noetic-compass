"""Agent outcome-memory coverage."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.agent_memory import build_agent_memory_report, load_latest_agent_memory_report
from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.broker.mt4_mailbox_bridge import RECEIPT_SCHEMA
from cas_forex.terminal_receipt_ingest import ingest_terminal_receipts


def _write_receipt(mailbox_dir: Path, command: dict, *, receipt_id: str = "receipt-memory-1") -> Path:
    payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "command_id": command["command_id"],
        "status": "ACKNOWLEDGED",
        "created_at": "2026-06-24T00:00:00Z",
        "raw_request_hash": command["raw_request_hash"],
        "raw_response_hash": "memory-response-hash",
        "terminal_name": "MetaTrader 4",
        "terminal_build": "1400",
        "account_id_hash": "acct-demo-hash",
        "server": "Demo-Server",
        "broker_mode": "PAPER_MT4",
        "live_mode": False,
        "live_trading_allowed": False,
        "broker_ticket": 123456,
        "filled_price": 1.01234,
        "filled_volume": 0.1,
        "slippage_pips": 0.1,
        "commission": 0.0,
        "swap": 0.0,
        "account_snapshot": {
            "balance": 5000.0,
            "equity": 5000.0,
            "margin": 100.0,
            "margin_free": 4900.0,
            "currency": "USD",
            "leverage": 500,
        },
    }
    receipt_path = mailbox_dir / "receipts" / f"{receipt_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")
    return receipt_path


def test_agent_memory_writes_pending_and_rejected_route_rows(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    report = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)

    memory = build_agent_memory_report(
        event_log_path=report["event_journal"]["event_log_path"],
        output_dir=tmp_path / "agent-memory",
    )

    summary = memory["summary"]
    labels = {record["outcome_label"] for record in memory["memory_records"]}
    assert summary["memory_record_count"] == 2
    assert summary["command_joined_count"] == 1
    assert summary["receipt_joined_count"] == 0
    assert "AWAITING_TERMINAL_RECEIPT" in labels
    assert "ROUTE_REJECTED" in labels

    latest = load_latest_agent_memory_report(tmp_path / "agent-memory")
    assert latest["summary"]["memory_record_count"] == 2


def test_agent_memory_joins_verified_terminal_receipt(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    report = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    command = report["terminal_commands"][0]
    _write_receipt(mailbox_dir, command)
    ingest = ingest_terminal_receipts(
        mailbox_dir=mailbox_dir,
        event_log_path=report["event_journal"]["event_log_path"],
        output_dir=tmp_path / "receipt-ingest",
    )
    assert ingest["summary"]["verified_receipt_count"] == 1

    memory = build_agent_memory_report(
        event_log_path=report["event_journal"]["event_log_path"],
        output_dir=tmp_path / "agent-memory",
    )
    receipt_records = [record for record in memory["memory_records"] if record["receipt_id"]]

    assert memory["summary"]["receipt_joined_count"] == 1
    assert receipt_records[0]["outcome_label"] == "TERMINAL_ACKNOWLEDGED"
    assert receipt_records[0]["learning_status"] == "READY_FOR_RESEARCH"
    assert receipt_records[0]["condition_snapshot_close"]["account_snapshot"]["balance"] == 5000.0
