"""Terminal bridge supervisor coverage for CAS Forex."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.broker.mt4_mailbox_bridge import RECEIPT_SCHEMA
from cas_forex.terminal_bridge_supervisor import (
    HEARTBEAT_SCHEMA,
    build_terminal_bridge_supervisor_report,
    load_latest_terminal_bridge_supervisor_report,
)


def _write_heartbeat(mailbox_dir: Path, *, live: bool = False, time: str = "2026.06.24 13:00:00") -> Path:
    payload = {
        "schema": HEARTBEAT_SCHEMA,
        "terminal": "MetaTrader 4",
        "terminal_build": "1400",
        "state": "TIMER",
        "account_id_hash": "acct-demo-hash",
        "server": "Demo-Server",
        "live_trading_allowed": live,
        "time": time,
    }
    path = mailbox_dir / "heartbeat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_receipt(mailbox_dir: Path, command: dict, *, receipt_id: str = "receipt-1") -> Path:
    payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "command_id": command["command_id"],
        "status": "ACKNOWLEDGED",
        "created_at": "2026-06-24T13:00:10+00:00",
        "raw_request_hash": command["raw_request_hash"],
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
            "equity": 5002.0,
            "margin": 100.0,
            "margin_free": 4902.0,
            "currency": "USD",
            "leverage": 500,
        },
    }
    path = mailbox_dir / "receipts" / f"{receipt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_terminal_bridge_supervisor_reports_missing_heartbeat(tmp_path):
    report = build_terminal_bridge_supervisor_report(
        mailbox_dir=tmp_path / "mailbox",
        history_source_paths=[tmp_path / "history"],
        event_log_path=tmp_path / "events.jsonl",
        output_dir=tmp_path / "supervisor",
        now="2026-06-24T13:01:00+00:00",
    )

    assert report["supervisor_status"] == "TERMINAL_BRIDGE_HEARTBEAT_MISSING"
    assert report["summary"]["heartbeat_present"] is False
    assert any(alert["alert_id"] == "heartbeat_missing" for alert in report["alerts"])
    assert "does not by itself execute live broker orders" in report["claim_boundary"]


def test_terminal_bridge_supervisor_reports_fresh_heartbeat_and_pending_receipts(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=mailbox_dir)
    _write_heartbeat(mailbox_dir)

    report = build_terminal_bridge_supervisor_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[tmp_path / "history"],
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "supervisor",
        now="2026-06-24T13:01:00+00:00",
    )

    assert report["supervisor_status"] == "TERMINAL_BRIDGE_READY_PENDING_RECEIPTS"
    assert report["summary"]["heartbeat_status"] == "FRESH"
    assert report["summary"]["command_file_count"] == 1
    assert report["summary"]["pending_command_receipt_count"] == 1
    assert report["event_journal"]["pending_receipt_count"] == 1
    assert any(alert["alert_id"] == "pending_command_receipts" for alert in report["alerts"])


def test_terminal_bridge_supervisor_sees_receipt_account_snapshot_and_history(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=mailbox_dir)
    _write_heartbeat(mailbox_dir)
    _write_receipt(mailbox_dir, cycle["terminal_commands"][0])
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "closed-history.json").write_text("[]", encoding="utf-8")

    report = build_terminal_bridge_supervisor_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[history_dir],
        event_log_path=tmp_path / "no-events.jsonl",
        output_dir=tmp_path / "supervisor",
        now="2026-06-24T13:01:00+00:00",
    )

    assert report["supervisor_status"] == "TERMINAL_BRIDGE_READY"
    assert report["summary"]["receipt_file_count"] == 1
    assert report["summary"]["pending_command_receipt_count"] == 0
    assert report["summary"]["account_snapshot_present"] is True
    assert report["account_snapshot"]["latest_account_snapshot"]["equity"] == 5002.0
    assert report["summary"]["history_file_count"] == 1

    latest = load_latest_terminal_bridge_supervisor_report(tmp_path / "supervisor")
    assert latest["summary"]["account_snapshot_present"] is True


def test_terminal_bridge_supervisor_surfaces_live_flag(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    (mailbox_dir / "commands").mkdir(parents=True)
    (mailbox_dir / "receipts").mkdir(parents=True)
    _write_heartbeat(mailbox_dir, live=True)

    report = build_terminal_bridge_supervisor_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[tmp_path / "history"],
        event_log_path=tmp_path / "events.jsonl",
        output_dir=tmp_path / "supervisor",
        now="2026-06-24T13:01:00+00:00",
    )

    assert report["supervisor_status"] == "TERMINAL_BRIDGE_LIVE_FLAG_VISIBLE"
    assert report["summary"]["live_trading_flag_visible"] is True
    assert any(alert["alert_id"] == "live_trading_flag_visible" for alert in report["alerts"])
