"""MT4 terminal activation coverage for CAS Forex."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from api import data as api_data
from api.server import app
from cas_forex.mt4_terminal_activation import (
    build_mt4_terminal_activation_report,
    discover_mt4_terminal_roots,
    load_latest_mt4_terminal_activation_report,
)


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


def test_mt4_terminal_activation_reports_mt5_only_when_no_mt4_folder(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4")
    _make_mt5_terminal(tmp_path / "MetaQuotes" / "Terminal")

    report = build_mt4_terminal_activation_report(
        search_roots=[tmp_path / "MetaQuotes" / "Terminal"],
        ea_source_path=ea_source,
        output_dir=tmp_path / "activation",
    )

    assert report["activation_status"] == "MT4_ACTIVATION_NEEDS_MT4_TERMINAL"
    assert report["summary"]["mt5_only_candidate_count"] == 1
    assert report["selected_terminal"] is None
    assert "Only MT5-style terminal folders were found" in report["next_action"]
    assert "does not by itself execute live broker orders" in report["claim_boundary"]


def test_mt4_terminal_activation_discovers_mt4_and_needs_install(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")

    candidates = discover_mt4_terminal_roots(
        search_roots=[tmp_path / "MetaQuotes" / "Terminal"],
        source_path=ea_source,
    )
    report = build_mt4_terminal_activation_report(
        search_roots=[tmp_path / "MetaQuotes" / "Terminal"],
        ea_source_path=ea_source,
        output_dir=tmp_path / "activation",
        create_mailbox=False,
    )

    assert candidates[0]["terminal_data_dir"] == str(terminal)
    assert report["activation_status"] == "MT4_ACTIVATION_DISCOVERED_NEEDS_INSTALL"
    assert report["summary"]["mt4_candidate_count"] == 1
    assert report["selected_terminal"]["ea"]["target_exists"] is False
    assert "Rerun with --install" in report["next_action"]


def test_mt4_terminal_activation_installs_ea_and_mailbox(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4", "source-v1\n")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")

    report = build_mt4_terminal_activation_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        output_dir=tmp_path / "activation",
        install_ea=True,
    )

    target = terminal / "MQL4" / "Experts" / "CASForexBridgeEA.mq4"
    mailbox = terminal / "MQL4" / "Files" / "CASForexMailbox"
    assert target.read_text(encoding="utf-8") == "source-v1\n"
    assert (mailbox / "commands").is_dir()
    assert (mailbox / "receipts").is_dir()
    assert report["activation_status"] == "MT4_ACTIVATION_STAGED_NEEDS_TERMINAL_ATTACH"
    assert report["summary"]["ea_hash_matches"] is True
    assert report["summary"]["mailbox_ready"] is True
    assert report["path_alignment"]["recommended_env"]["CAS_FOREX_MT4_MAILBOX_DIR"] == str(mailbox)

    latest = load_latest_mt4_terminal_activation_report(tmp_path / "activation")
    assert latest["selected_terminal"]["ea"]["hash_matches"] is True


def test_mt4_terminal_activation_reports_heartbeat_present(tmp_path):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4", "source-v1\n")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")
    mailbox = terminal / "MQL4" / "Files" / "CASForexMailbox"
    report = build_mt4_terminal_activation_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        output_dir=tmp_path / "activation",
        install_ea=True,
    )
    heartbeat = {
        "schema": "cas_forex_mt4_heartbeat.v1",
        "terminal": "MetaTrader 4",
        "live_trading_allowed": False,
    }
    (mailbox / "heartbeat.json").write_text(json.dumps(heartbeat), encoding="utf-8")

    report = build_mt4_terminal_activation_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        output_dir=tmp_path / "activation",
    )

    assert report["activation_status"] == "MT4_ACTIVATION_HEARTBEAT_PRESENT"
    assert report["summary"]["heartbeat_present"] is True


def test_mt4_terminal_activation_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    ea_source = _write_ea_source(tmp_path / "repo" / "mt4" / "Experts" / "CASForexBridgeEA.mq4", "source-v1\n")
    terminal = _make_mt4_terminal(tmp_path / "MetaQuotes" / "Terminal")

    report = build_mt4_terminal_activation_report(
        terminal_data_dir=terminal,
        ea_source_path=ea_source,
        install_ea=True,
        write_report=False,
    )
    monkeypatch.setattr(api_data, "load_latest_mt4_terminal_activation_report", lambda: report)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt4-terminal-activation/latest"))
    assert status == 200
    assert body["activation_status"] == "MT4_ACTIVATION_STAGED_NEEDS_TERMINAL_ATTACH"
    assert body["summary"]["ea_hash_matches"] is True

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt4TerminalActivation"]["activation_status"] == "MT4_ACTIVATION_STAGED_NEEDS_TERMINAL_ATTACH"
