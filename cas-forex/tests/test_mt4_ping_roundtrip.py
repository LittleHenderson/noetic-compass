"""MT4 ping roundtrip coverage for CAS Forex."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from api import data as api_data
from api.server import app
from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge
from cas_forex.mt4_ping_roundtrip import (
    build_mt4_ping_roundtrip_report,
    load_latest_mt4_ping_roundtrip_report,
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


def _activation_without_mailbox() -> dict[str, Any]:
    return {
        "activation_status": "MT4_ACTIVATION_NEEDS_MT4_TERMINAL",
        "path_alignment": {"recommended_cas_mailbox_dir": None},
        "selected_terminal": None,
        "report_path": "activation.json",
    }


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


def test_mt4_ping_roundtrip_needs_activated_mailbox(tmp_path):
    report = build_mt4_ping_roundtrip_report(
        activation_report=_activation_without_mailbox(),
        output_dir=tmp_path / "roundtrip",
    )

    assert report["roundtrip_status"] == "MT4_PING_NEEDS_ACTIVATED_MAILBOX"
    assert report["mailbox_dir"] is None
    assert report["summary"]["ping_written"] is False
    assert "does not place live broker orders" in report["claim_boundary"]


def test_mt4_ping_roundtrip_writes_ping_and_waits_for_terminal(tmp_path):
    mailbox = tmp_path / "terminal" / "MQL4" / "Files" / "CASForexMailbox"

    report = build_mt4_ping_roundtrip_report(
        mailbox_dir=mailbox,
        output_dir=tmp_path / "roundtrip",
        wait_seconds=0,
    )

    command_path = Path(report["command"]["command_path"])
    assert report["roundtrip_status"] == "MT4_PING_WRITTEN_WAITING_FOR_TERMINAL"
    assert command_path.exists()
    assert report["summary"]["ping_written"] is True
    assert report["summary"]["heartbeat_present"] is False
    assert report["summary"]["receipt_present"] is False


def test_mt4_ping_roundtrip_acknowledges_existing_ping(tmp_path):
    mailbox = tmp_path / "terminal" / "MQL4" / "Files" / "CASForexMailbox"
    bridge = MT4MailboxBridge(mailbox_dir=mailbox)
    command = bridge.write_ping()
    _write_heartbeat(mailbox)
    _write_receipt(mailbox, command)

    report = build_mt4_ping_roundtrip_report(
        mailbox_dir=mailbox,
        output_dir=tmp_path / "roundtrip",
        existing_command_id=command["command_id"],
        write_ping=False,
        wait_seconds=0,
    )

    assert report["roundtrip_status"] == "MT4_PING_ROUNDTRIP_ACKNOWLEDGED"
    assert report["summary"]["raw_request_hash_match"] is True
    assert report["summary"]["heartbeat_present"] is True
    assert report["summary"]["receipt_status"] == "ACKNOWLEDGED"

    latest = load_latest_mt4_ping_roundtrip_report(tmp_path / "roundtrip")
    assert latest["roundtrip_status"] == "MT4_PING_ROUNDTRIP_ACKNOWLEDGED"


def test_mt4_ping_roundtrip_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    mailbox = tmp_path / "terminal" / "MQL4" / "Files" / "CASForexMailbox"
    report = build_mt4_ping_roundtrip_report(
        mailbox_dir=mailbox,
        output_dir=tmp_path / "roundtrip",
        wait_seconds=0,
        write_report=False,
    )
    monkeypatch.setattr(api_data, "load_latest_mt4_ping_roundtrip_report", lambda: report)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt4-ping-roundtrip/latest"))
    assert status == 200
    assert body["roundtrip_status"] == "MT4_PING_WRITTEN_WAITING_FOR_TERMINAL"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt4PingRoundtrip"]["roundtrip_status"] == "MT4_PING_WRITTEN_WAITING_FOR_TERMINAL"
