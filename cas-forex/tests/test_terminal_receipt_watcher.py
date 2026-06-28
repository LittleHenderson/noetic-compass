"""Terminal receipt watcher coverage for CAS Forex."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.broker.mt4_mailbox_bridge import RECEIPT_SCHEMA
from cas_forex.terminal_receipt_watcher import (
    build_terminal_receipt_watcher_report,
    load_latest_terminal_receipt_watcher_report,
)


def _write_receipt(mailbox_dir: Path, command: dict, *, receipt_id: str = "receipt-1") -> Path:
    payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "command_id": command["command_id"],
        "status": "ACKNOWLEDGED",
        "created_at": "2026-06-24T00:00:00Z",
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
            "equity": 5000.0,
            "margin": 100.0,
            "margin_free": 4900.0,
            "currency": "USD",
            "leverage": 500,
        },
    }
    path = mailbox_dir / "receipts" / f"{receipt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_terminal_receipt_watcher_idles_without_terminal_files(tmp_path):
    report = build_terminal_receipt_watcher_report(
        mailbox_dir=tmp_path / "mailbox",
        history_source_paths=[tmp_path / "history"],
        event_log_path=tmp_path / "events.jsonl",
        output_dir=tmp_path / "watcher",
    )

    assert report["watch_status"] == "WATCHER_IDLE_NO_TERMINAL_FILES"
    assert report["summary"]["terminal_file_count"] == 0
    assert report["summary"]["chain_step_count"] == 0
    assert report["file_changes"]["change_counts"]["NEW"] == 0


def test_terminal_receipt_watcher_runs_chain_for_new_receipt_then_idles(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=mailbox_dir)
    _write_receipt(mailbox_dir, cycle["terminal_commands"][0])

    first = build_terminal_receipt_watcher_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[tmp_path / "history"],
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "watcher",
        chain_output_root=tmp_path / "chain",
        now="2026-06-24T13:00:00+00:00",
    )

    assert first["watch_status"] == "WATCHER_CHAIN_RAN"
    assert first["summary"]["receipt_file_count"] == 1
    assert first["summary"]["changed_file_count"] == 1
    assert first["summary"]["chain_step_complete_count"] == 8
    assert first["summary"]["chain_step_failed_count"] == 0
    assert first["chain_reports"]["terminal_receipt_ingest"]["summary"]["verified_receipt_count"] == 1
    assert first["chain_reports"]["agent_memory"]["summary"]["receipt_joined_count"] == 1
    assert first["chain_reports"]["session_autowake"]["status"] == "SESSION_AUTOWAKE_READY"

    latest = load_latest_terminal_receipt_watcher_report(tmp_path / "watcher")
    assert latest["summary"]["latest_completed_step"] == "session_autowake"

    second = build_terminal_receipt_watcher_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[tmp_path / "history"],
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "watcher",
        chain_output_root=tmp_path / "chain",
        previous_report=first,
        now="2026-06-24T13:00:00+00:00",
    )

    assert second["watch_status"] == "WATCHER_IDLE_NO_CHANGES"
    assert second["summary"]["changed_file_count"] == 0
    assert second["summary"]["chain_step_count"] == 0


def test_terminal_receipt_watcher_can_detect_change_without_running_chain(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    receipt_path = mailbox_dir / "receipts" / "receipt-placeholder.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text('{"receipt_id": "placeholder"}', encoding="utf-8")

    report = build_terminal_receipt_watcher_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[tmp_path / "history"],
        event_log_path=tmp_path / "events.jsonl",
        output_dir=tmp_path / "watcher",
        run_chain=False,
    )

    assert report["watch_status"] == "WATCHER_CHANGE_DETECTED_NO_CHAIN_RUN"
    assert report["summary"]["changed_file_count"] == 1
    assert report["summary"]["chain_step_count"] == 0
