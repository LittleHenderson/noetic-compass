"""MT4 terminal session verifier coverage for CAS Forex."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from api import data as api_data
from api.server import app
from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge
from cas_forex.mt4_terminal_session_verifier import (
    build_mt4_terminal_session_verifier_report,
    load_latest_mt4_terminal_session_verifier_report,
)


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


def _write_ea_source(path: Path, body: str = "input string MailboxRoot = \"CASForexMailbox\";\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _make_mt4_terminal(root: Path, name: str = "ABCDEF0123456789ABCDEF0123456789") -> Path:
    terminal = root / name
    (terminal / "MQL4" / "Experts").mkdir(parents=True)
    (terminal / "MQL4" / "Files").mkdir(parents=True)
    return terminal


def _make_mt5_terminal(root: Path, name: str = "FEDCBA9876543210FEDCBA9876543210") -> Path:
    terminal = root / name
    (terminal / "MQL5" / "Experts" / "Advisors").mkdir(parents=True)
    return terminal


def _write_heartbeat(mailbox: Path) -> None:
    (mailbox / "heartbeat.json").write_text(
        json.dumps(
            {
                "schema": "cas_forex_mt4_heartbeat.v1",
                "terminal": "MetaTrader 4",
                "terminal_build": "1340",
                "state": "TIMER",
                "account_id_hash": "acct-hash",
                "server": "Demo",
                "live_trading_allowed": False,
                "time": "2026.06.24 12:00:00",
            }
        ),
        encoding="utf-8",
    )


def _write_receipt(mailbox: Path, command: dict[str, Any]) -> None:
    receipt = {
        "schema": "cas_forex_mt4_mailbox_receipt.v1",
        "receipt_id": f"receipt-{command['command_id']}",
        "command_id": command["command_id"],
        "status": "ACKNOWLEDGED",
        "created_at": "2026.06.24 12:00:01",
        "raw_request_hash": command["raw_request_hash"],
        "terminal_name": "MetaTrader 4",
        "terminal_build": "1340",
        "account_id_hash": "acct-hash",
        "server": "Demo",
        "broker_mode": command["broker_mode"],
        "live_mode": False,
        "live_trading_allowed": False,
        "broker_ticket": 0,
        "filled_price": 0.0,
        "filled_volume": 0.0,
        "slippage_pips": 0.0,
        "commission": 0.0,
        "swap": 0.0,
        "error_code": 0,
        "message": "ping acknowledged",
        "account_snapshot": {"balance": 5000.0, "equity": 5000.0, "currency": "USD"},
        "raw_response_hash": "mql4-test-response",
    }
    (mailbox / "receipts" / f"receipt-{command['command_id']}.json").write_text(
        json.dumps(receipt),
        encoding="utf-8",
    )


def test_mt4_terminal_session_verifier_needs_mt4_terminal(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4")
    _make_mt5_terminal(tmp_path / "MetaQuotes" / "Terminal")

    report = build_mt4_terminal_session_verifier_report(
        search_roots=[tmp_path / "MetaQuotes" / "Terminal"],
        ea_source_path=ea_source,
        output_dir=tmp_path / "session",
        child_output_root=tmp_path / "evidence",
    )

    assert report["session_status"] == "MT4_SESSION_NEEDS_MT4_TERMINAL"
    assert report["summary"]["mt4_candidate_count"] == 0
    assert report["summary"]["mt5_only_candidate_count"] == 1
    assert report["summary"]["ping_written"] is False
    assert {step["status"] for step in report["step_results"]} == {"COMPLETE", "SKIPPED"}
    assert "does not place live broker orders" in report["claim_boundary"]


def test_mt4_terminal_session_verifier_stages_ping_and_waits_for_terminal(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4", "source-v1\n")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")

    report = build_mt4_terminal_session_verifier_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        install_ea=True,
        output_dir=tmp_path / "session",
        child_output_root=tmp_path / "evidence",
        run_refresh_chain=False,
    )

    assert report["session_status"] == "MT4_SESSION_PING_WRITTEN_WAITING_FOR_TERMINAL"
    assert report["summary"]["mailbox_ready"] is True
    assert report["summary"]["ping_written"] is True
    assert report["summary"]["heartbeat_present"] is False
    assert str(terminal / "MQL4" / "Files" / "CASForexMailbox" / "history") in report["history_source_paths"]
    assert Path(report["child_reports"]["mt4_ping_roundtrip"]["summary"]["command_path"]).exists()


def test_mt4_terminal_session_verifier_acknowledged_roundtrip_runs_refresh_chain(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4", "source-v1\n")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")
    mailbox = terminal / "MQL4" / "Files" / "CASForexMailbox"
    bridge = MT4MailboxBridge(mailbox_dir=mailbox)
    command = bridge.write_ping()
    _write_heartbeat(mailbox)
    _write_receipt(mailbox, command)
    event_log = tmp_path / "events.jsonl"
    event_log.write_text("", encoding="utf-8")

    report = build_mt4_terminal_session_verifier_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        install_ea=True,
        output_dir=tmp_path / "session",
        child_output_root=tmp_path / "evidence",
        chain_output_root=tmp_path / "chain",
        event_log_path=event_log,
        existing_command_id=command["command_id"],
        write_ping=False,
        run_refresh_chain=True,
        force_refresh_chain=True,
    )

    assert report["session_status"] == "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN"
    assert report["summary"]["heartbeat_present"] is True
    assert report["summary"]["receipt_present"] is True
    assert report["summary"]["receipt_status"] == "ACKNOWLEDGED"
    assert report["summary"]["refresh_chain_complete"] is True
    assert report["summary"]["chain_step_count"] >= 7

    latest = load_latest_mt4_terminal_session_verifier_report(tmp_path / "session")
    assert latest["session_status"] == "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN"


def test_mt4_terminal_session_verifier_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4", "source-v1\n")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")
    report = build_mt4_terminal_session_verifier_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        install_ea=True,
        output_dir=tmp_path / "session",
        child_output_root=tmp_path / "evidence",
        run_refresh_chain=False,
        write_report=False,
    )
    monkeypatch.setattr(api_data, "load_latest_mt4_terminal_session_verifier_report", lambda: report)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt4-terminal-session-verifier/latest"))
    assert status == 200
    assert body["session_status"] == "MT4_SESSION_PING_WRITTEN_WAITING_FOR_TERMINAL"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt4TerminalSessionVerifier"]["session_status"] == "MT4_SESSION_PING_WRITTEN_WAITING_FOR_TERMINAL"
