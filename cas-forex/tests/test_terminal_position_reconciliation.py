"""Terminal position reconciliation coverage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import api.server as api_server
import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.agent_memory import build_agent_memory_report
from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.broker.mt4_mailbox_bridge import RECEIPT_SCHEMA
from cas_forex.terminal_bridge_supervisor import HEARTBEAT_SCHEMA, build_terminal_bridge_supervisor_report
from cas_forex.terminal_position_reconciliation import (
    build_terminal_position_reconciliation_report,
    load_latest_terminal_position_reconciliation_report,
)
from cas_forex.terminal_receipt_recovery_packet import (
    build_terminal_receipt_recovery_packet,
    run_terminal_receipt_archive_action,
)
from cas_forex.terminal_receipt_ingest import ingest_terminal_receipts


async def _asgi_get(path: str) -> tuple[int, dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(body.decode("utf-8"))


async def _asgi_post(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    payload = json.dumps(body).encode("utf-8")
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    response_body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(response_body.decode("utf-8"))


def _write_heartbeat(mailbox_dir: Path) -> None:
    payload = {
        "schema": HEARTBEAT_SCHEMA,
        "terminal": "MetaTrader 4",
        "terminal_build": "1400",
        "state": "TIMER",
        "account_id_hash": "acct-demo-hash",
        "server": "Demo-Server",
        "live_trading_allowed": False,
        "time": "2026.06.24 13:00:00",
    }
    path = mailbox_dir / "heartbeat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_receipt_with_open_position(mailbox_dir: Path, command: dict) -> None:
    command_payload = json.loads(Path(command["command_path"]).read_text(encoding="utf-8"))
    order = command_payload["order"]
    receipt_payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": "receipt-open-1",
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
        "broker_ticket": "123456",
        "filled_price": order["price"] or order["entry_price"] if "entry_price" in order else 0.899,
        "filled_volume": order["volume"],
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
            "open_positions": [
                {
                    "command_id": command["command_id"],
                    "receipt_id": "receipt-open-1",
                    "broker_ticket": "123456",
                    "symbol": order["symbol"],
                    "direction": order["direction"],
                    "lots": order["volume"],
                    "open_price": 0.899,
                    "stop_loss": order["stop_loss"],
                    "take_profit": order["take_profit"],
                }
            ],
        },
    }
    receipt_path = mailbox_dir / "receipts" / "receipt-open-1.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_payload), encoding="utf-8")


def test_terminal_position_reconciliation_reports_current_mt4_terminal_gap(tmp_path):
    report = build_terminal_position_reconciliation_report(
        terminal_bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING",
            "summary": {"heartbeat_status": "MISSING", "heartbeat_present": False, "live_trading_flag_visible": False},
            "account_snapshot": {"account_snapshot_present": False, "latest_account_snapshot": None},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "summary": {"pending_receipt_count": 0}, "receipt_records": []},
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "summary": {}, "history_records": [], "memory_updates": []},
        memory_report={"report_kind": "cas_forex_agent_memory_report", "summary": {}, "memory_records": []},
        mt4_history_export_verifier_report={
            "report_kind": "cas_forex_mt4_history_export_verifier_report",
            "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL",
            "summary": {"mailbox_ready": False},
        },
        output_dir=tmp_path / "reconciliation",
        write_report=False,
    )

    assert report["reconciliation_status"] == "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL"
    assert report["summary"]["account_snapshot_present"] is False
    assert "Install/open MT4" in report["next_action"]
    assert "does not by itself execute live broker orders" in report["claim_boundary"]


def test_terminal_position_reconciliation_matches_open_terminal_position(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=mailbox_dir)
    command = cycle["terminal_commands"][0]
    _write_heartbeat(mailbox_dir)
    _write_receipt_with_open_position(mailbox_dir, command)

    receipt_ingest = ingest_terminal_receipts(
        mailbox_dir=mailbox_dir,
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "receipt-ingest",
    )
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "memory",
    )
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    bridge = build_terminal_bridge_supervisor_report(
        mailbox_dir=mailbox_dir,
        history_source_paths=[history_dir],
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "bridge",
        now="2026-06-24T13:01:00+00:00",
        write_report=False,
    )

    report = build_terminal_position_reconciliation_report(
        terminal_bridge_report=bridge,
        receipt_ingest_report=receipt_ingest,
        history_ingest_report={
            "report_kind": "cas_forex_terminal_history_ingest",
            "ingest_status": "TERMINAL_HISTORY_EMPTY",
            "summary": {"history_record_count": 0, "memory_update_count": 0, "unmatched_history_count": 0},
            "history_records": [],
            "memory_updates": [],
        },
        memory_report=memory,
        mt4_history_export_verifier_report={
            "report_kind": "cas_forex_mt4_history_export_verifier_report",
            "verifier_status": "MT4_HISTORY_EXPORT_FILE_MISSING",
            "summary": {"mailbox_ready": True},
        },
        output_dir=tmp_path / "reconciliation",
    )

    assert report["reconciliation_status"] == "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS"
    assert report["summary"]["cas_open_position_count"] == 1
    assert report["summary"]["terminal_open_position_count"] == 1
    assert report["summary"]["reconciled_open_position_count"] == 1
    assert report["summary"]["unmatched_open_position_count"] == 0
    assert report["reconciled_open_positions"][0]["match_method"] == "command_id"

    latest = load_latest_terminal_position_reconciliation_report(tmp_path / "reconciliation")
    assert latest["reconciliation_status"] == "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS"


def test_terminal_position_reconciliation_flags_unmatched_open_memory(tmp_path):
    report = build_terminal_position_reconciliation_report(
        terminal_bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_READY",
            "summary": {"heartbeat_status": "FRESH", "heartbeat_present": True, "live_trading_flag_visible": False},
            "account_snapshot": {"account_snapshot_present": True, "latest_account_snapshot": {"balance": 5000.0, "equity": 5000.0}},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}, "receipt_records": []},
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "summary": {"unmatched_history_count": 0}, "history_records": [], "memory_updates": []},
        memory_report={
            "report_kind": "cas_forex_agent_memory_report",
            "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0},
            "memory_records": [
                {
                    "memory_id": "memory-1",
                    "decision_approved": True,
                    "command_id": "cmd-1",
                    "receipt_id": "receipt-1",
                    "broker_ticket": "ticket-1",
                    "symbol": "EUR/USD",
                    "direction": "LONG",
                    "outcome_label": "TERMINAL_ACKNOWLEDGED",
                    "condition_snapshot_open": {"symbol": "EUR/USD", "direction": "LONG", "lot_size": 0.1, "entry_price": 1.1},
                }
            ],
        },
        mt4_history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_EMPTY", "summary": {}},
        output_dir=tmp_path / "reconciliation",
        write_report=False,
    )

    assert report["reconciliation_status"] == "TERMINAL_POSITION_RECONCILIATION_MISMATCH"
    assert report["summary"]["unmatched_open_position_count"] == 1
    assert report["checks"][4]["status"] == "MISMATCH"


def test_terminal_receipt_recovery_packet_previews_pending_receipt_blocker(tmp_path):
    report = build_terminal_position_reconciliation_report(
        terminal_bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING",
            "summary": {"heartbeat_status": "MISSING", "heartbeat_present": False, "live_trading_flag_visible": False},
            "account_snapshot": {"account_snapshot_present": False, "latest_account_snapshot": None},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "summary": {"pending_receipt_count": 1, "receipt_mismatch_count": 0}, "receipt_records": []},
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "summary": {}, "history_records": [], "memory_updates": []},
        memory_report={
            "report_kind": "cas_forex_agent_memory_report",
            "summary": {"pending_receipt_count": 1, "receipt_mismatch_count": 0},
            "memory_records": [
                {
                    "memory_id": "memory-pending-1",
                    "decision_approved": True,
                    "command_id": "agent-micro-AUDCAD-20260624053115-20260624053115627453",
                    "broker_mode": "PAPER_MT4",
                    "symbol": "AUD/CAD",
                    "direction": "LONG",
                    "outcome_label": "AWAITING_TERMINAL_RECEIPT",
                    "learning_status": "WAITING_FOR_TERMINAL",
                    "condition_snapshot_open": {"symbol": "AUD/CAD", "direction": "LONG", "lot_size": 0.1, "entry_price": 0.9},
                }
            ],
        },
        mt4_history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {}},
        output_dir=tmp_path / "reconciliation",
        write_report=False,
    )
    event_log = tmp_path / "agent-events.jsonl"
    event_log.write_text(
        json.dumps(
            {
                "event_type": "TERMINAL_RECEIPT_PENDING",
                "created_at": "2026-06-24T05:31:15+00:00",
                "subject": "old pending receipt",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    packet = build_terminal_receipt_recovery_packet(
        reconciliation_report=report,
        event_log_path=event_log,
        legacy_snapshot_dir=tmp_path / "legacy-archive",
    )

    assert packet["report_kind"] == "cas_forex_terminal_receipt_recovery_packet"
    assert packet["status"] == "TERMINAL_RECEIPT_RECOVERY_ARCHIVE_PREVIEW_READY"
    assert packet["terminal_reconciliation_clean_for_live"] is False
    assert packet["broker_touched"] is False
    assert packet["journal_rewritten"] is False
    assert packet["pending_receipt_count"] == 1
    assert packet["pending_positions"][0]["classification_status"] == "LEGACY_MT4_MAILBOX_PENDING"
    assert packet["legacy_archive_preview"]["dry_run"] is True
    assert packet["legacy_archive_preview"]["pending_receipt_rows_archived"] == 1
    assert event_log.exists()


def test_terminal_receipt_archive_action_requires_owner_confirmation(tmp_path):
    event_log = tmp_path / "agent-events.jsonl"
    event_log.write_text(
        json.dumps(
            {
                "event_type": "TERMINAL_RECEIPT_PENDING",
                "created_at": "2000-01-01T00:00:00+00:00",
                "subject": "old pending receipt",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    action = run_terminal_receipt_archive_action(
        execute=True,
        confirm_owner_archive=False,
        event_log_path=event_log,
        legacy_snapshot_dir=tmp_path / "legacy-archive",
    )

    assert action["report_kind"] == "cas_forex_terminal_receipt_archive_action"
    assert action["status"] == "TERMINAL_RECEIPT_ARCHIVE_CONFIRM_REQUIRED"
    assert action["dry_run"] is True
    assert action["broker_touched"] is False
    assert action["journal_rewritten"] is False
    assert action["money_moved"] is False
    assert action["archive_result"]["pending_receipt_rows_archived"] == 1
    assert "TERMINAL_RECEIPT_PENDING" in event_log.read_text(encoding="utf-8")
    assert not any((tmp_path / "legacy-archive").glob("*.jsonl"))


def test_terminal_receipt_archive_action_route_previews_and_executes(monkeypatch, tmp_path):
    event_log = tmp_path / "agent-events.jsonl"
    event_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "TERMINAL_RECEIPT_PENDING",
                        "created_at": "2000-01-01T00:00:00+00:00",
                        "subject": "old pending receipt",
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "event_type": "KEEP_ME",
                        "created_at": "2000-01-01T00:00:00+00:00",
                        "subject": "ordinary row",
                    },
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    archive_dir = tmp_path / "legacy-archive"

    def archive_action(**kwargs: Any) -> dict[str, Any]:
        return run_terminal_receipt_archive_action(
            event_log_path=event_log,
            legacy_snapshot_dir=archive_dir,
            **kwargs,
        )

    monkeypatch.setattr(strategy_routes, "terminal_receipt_archive_action", archive_action)

    status, preview = asyncio.run(
        _asgi_post(
            "/api/forex/strategy/terminal-receipt-recovery-packet/archive-stale",
            {"execute": False, "confirm_owner_archive": False, "notes": "preview"},
        )
    )
    assert status == 200
    assert preview["status"] == "TERMINAL_RECEIPT_ARCHIVE_DRY_RUN"
    assert preview["dry_run"] is True
    assert preview["journal_rewritten"] is False
    assert preview["archive_result"]["pending_receipt_rows_archived"] == 1
    assert "TERMINAL_RECEIPT_PENDING" in event_log.read_text(encoding="utf-8")

    status, executed = asyncio.run(
        _asgi_post(
            "/api/forex/strategy/terminal-receipt-recovery-packet/archive-stale",
            {"execute": True, "confirm_owner_archive": True, "notes": "owner execute"},
        )
    )
    assert status == 200
    assert executed["status"] == "TERMINAL_RECEIPT_ARCHIVE_EXECUTED"
    assert executed["dry_run"] is False
    assert executed["broker_touched"] is False
    assert executed["journal_rewritten"] is True
    assert executed["money_moved"] is False
    rewritten = event_log.read_text(encoding="utf-8")
    assert "TERMINAL_RECEIPT_PENDING" not in rewritten
    assert "KEEP_ME" in rewritten
    assert len(list(archive_dir.glob("*.jsonl"))) == 1


def test_terminal_position_reconciliation_api_and_dashboard_surface(monkeypatch, tmp_path):
    report = build_terminal_position_reconciliation_report(
        terminal_bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING",
            "summary": {"heartbeat_status": "MISSING", "heartbeat_present": False},
            "account_snapshot": {},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "summary": {}, "receipt_records": []},
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "summary": {}, "history_records": [], "memory_updates": []},
        memory_report={"report_kind": "cas_forex_agent_memory_report", "summary": {}, "memory_records": []},
        mt4_history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {}},
        output_dir=tmp_path / "reconciliation",
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "terminal_position_reconciliation_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"terminalPositionReconciliation": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/terminal-position-reconciliation/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_terminal_position_reconciliation_report"
    assert body["reconciliation_status"] == "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["terminalPositionReconciliation"]["summary"]["account_snapshot_present"] is False


def test_terminal_receipt_recovery_packet_api_and_dashboard_surface(monkeypatch, tmp_path):
    packet = {
        "report_kind": "cas_forex_terminal_receipt_recovery_packet",
        "generated_at": "2026-06-30T00:00:00+00:00",
        "status": "TERMINAL_RECEIPT_RECOVERY_WAITING_FOR_TERMINAL",
        "terminal_reconciliation_clean_for_live": False,
        "broker_touched": False,
        "journal_rewritten": False,
        "receipt_ingest_attempted": False,
        "attempt_finalized": False,
        "pending_receipt_count": 28,
        "pending_receipt_count_by_lane": {"mt4_mailbox": 28},
        "cas_receipt_pending_open_count": 28,
        "unmatched_open_position_count": 28,
        "terminal_open_position_count": 0,
        "heartbeat_status": "MISSING",
        "account_snapshot_present": False,
        "pending_positions": [],
        "legacy_archive_preview": {"dry_run": True, "pending_receipt_rows_archived": 0},
        "missing_requirements": ["terminal_heartbeat_fresh", "terminal_receipts_clear"],
        "source_reconciliation": {},
        "operator_commands": {},
        "claim_boundary": "read-only packet",
        "next_action": "Open the terminal bridge.",
    }

    monkeypatch.setattr(strategy_routes, "terminal_receipt_recovery_packet_latest", lambda: packet)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"terminalReceiptRecoveryPacket": packet})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/terminal-receipt-recovery-packet/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_terminal_receipt_recovery_packet"
    assert body["journal_rewritten"] is False

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["terminalReceiptRecoveryPacket"]["pending_receipt_count"] == 28
