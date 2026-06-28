"""Terminal receipt ingest coverage for CAS Forex agent workflows."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.agent_message_bus import AgentEventStore
from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.broker.mt4_mailbox_bridge import RECEIPT_SCHEMA
from cas_forex.terminal_receipt_ingest import (
    ingest_terminal_receipts,
    load_latest_terminal_receipt_ingest_report,
)


def _write_receipt(
    mailbox_dir: Path,
    command: dict,
    *,
    receipt_id: str = "receipt-1",
    raw_request_hash: str | None = None,
) -> Path:
    receipt_payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "command_id": command["command_id"],
        "status": "ACKNOWLEDGED",
        "created_at": "2026-06-24T00:00:00Z",
        "raw_request_hash": raw_request_hash or command["raw_request_hash"],
        "raw_response_hash": "response-hash-1",
        "terminal_name": "MetaTrader 4",
        "terminal_build": "1400",
        "account_id_hash": "acct-demo-hash",
        "server": "Demo-Server",
        "broker_mode": "PAPER_MT4",
        "live_mode": False,
        "live_trading_allowed": False,
        "broker_ticket": 123456,
        "filled_price": 1.01234,
        "filled_volume": 0.9,
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
    receipt_path.write_text(json.dumps(receipt_payload), encoding="utf-8")
    return receipt_path


def test_terminal_receipt_ingest_verifies_reconciles_and_allows_next_cycle(tmp_path):
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

    summary = ingest["summary"]
    assert summary["receipt_count"] == 1
    assert summary["new_receipt_count"] == 1
    assert summary["verified_receipt_count"] == 1
    assert summary["reconciled_receipt_count"] == 1
    assert summary["next_cycle_allowed_count"] == 1
    assert summary["pending_receipt_count"] == 0

    store = AgentEventStore(report["event_journal"]["event_log_path"])
    event_types = {event["event_type"] for event in store.read_events(limit=1000)}
    assert "TERMINAL_RECEIPT_RECEIVED" in event_types
    assert "TERMINAL_RECEIPT_RECONCILED" in event_types
    assert "NEXT_CYCLE_ALLOWED" in event_types
    assert store.summary()["pending_receipt_count"] == 0

    latest = load_latest_terminal_receipt_ingest_report(tmp_path / "receipt-ingest")
    assert latest["summary"]["verified_receipt_count"] == 1


def test_terminal_receipt_ingest_locks_mismatched_receipt_hash(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    report = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    command = report["terminal_commands"][0]
    _write_receipt(mailbox_dir, command, receipt_id="receipt-bad", raw_request_hash="wrong-hash")

    ingest = ingest_terminal_receipts(
        mailbox_dir=mailbox_dir,
        event_log_path=report["event_journal"]["event_log_path"],
        output_dir=tmp_path / "receipt-ingest",
    )

    record = ingest["receipt_records"][0]
    assert record["lifecycle_status"] == "RECEIPT_MISMATCH"
    assert record["reconcile_status"] == "TERMINAL_LOCKED_FOR_SYMBOL"
    assert "raw_request_hash does not match" in " ".join(record["reasons"])
    assert ingest["summary"]["receipt_mismatch_count"] == 1
    assert ingest["summary"]["next_cycle_allowed_count"] == 0

    store = AgentEventStore(report["event_journal"]["event_log_path"])
    event_types = {event["event_type"] for event in store.read_events(limit=1000)}
    assert "TERMINAL_RECEIPT_MISMATCH" in event_types


def test_terminal_receipt_ingest_is_idempotent_by_receipt_id(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    report = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    command = report["terminal_commands"][0]
    _write_receipt(mailbox_dir, command)

    first = ingest_terminal_receipts(
        mailbox_dir=mailbox_dir,
        event_log_path=report["event_journal"]["event_log_path"],
        output_dir=tmp_path / "receipt-ingest",
    )
    second = ingest_terminal_receipts(
        mailbox_dir=mailbox_dir,
        event_log_path=report["event_journal"]["event_log_path"],
        output_dir=tmp_path / "receipt-ingest",
    )

    assert first["summary"]["new_receipt_count"] == 1
    assert second["summary"]["new_receipt_count"] == 0
    assert second["summary"]["skipped_already_ingested_count"] == 1


def test_workflow_cycle_waits_for_receipt_then_allows_next_same_symbol_route(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"

    first = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    assert first["summary"]["terminal_command_count"] == 1
    first_command = first["terminal_commands"][0]

    blocked = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    assert blocked["summary"]["terminal_command_count"] == 0
    assert blocked["summary"]["approved_intent_count"] == 0
    assert "awaiting terminal receipt/reconciliation" in " ".join(
        reason
        for decision in blocked["overseer_decisions"]
        for reason in decision["reasons"]
    )

    _write_receipt(mailbox_dir, first_command, receipt_id="receipt-cycle-allow")
    ingest = ingest_terminal_receipts(
        mailbox_dir=mailbox_dir,
        event_log_path=first["event_journal"]["event_log_path"],
        output_dir=tmp_path / "receipt-ingest",
    )
    assert ingest["summary"]["next_cycle_allowed_count"] == 1

    allowed = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    assert allowed["summary"]["terminal_command_count"] == 1
    assert allowed["summary"]["approved_intent_count"] == 1
    assert "receipt lifecycle allows next same-symbol cycle" in " ".join(
        reason
        for decision in allowed["overseer_decisions"]
        for reason in decision["reasons"]
    )
