"""MT5 terminal API verifier coverage."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import api.server as api_server
import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.mt5_terminal_api_verifier import (
    build_mt5_terminal_api_verifier_report,
    load_latest_mt5_terminal_api_verifier_report,
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


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def __init__(self, *, connected: bool = True):
        self.connected = connected
        self.initialize_calls: list[dict[str, Any]] = []

    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        self.connected = True
        return True

    def terminal_info(self):
        return SimpleNamespace(
            connected=self.connected,
            name="MetaTrader 5",
            company="Hugosway-Demo",
            path=r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
            data_path=r"C:\Users\wakil\AppData\Roaming\MetaQuotes\Terminal\TEST",
            commondata_path=r"C:\Users\wakil\AppData\Roaming\MetaQuotes\Terminal\Common",
            trade_allowed=True,
            dlls_allowed=True,
            build=3900,
        )

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            server="Hugosway-Demo",
            company="Hugosway-Demo",
            trade_mode=self.ACCOUNT_TRADE_MODE_DEMO,
            currency="USD",
            leverage=500,
            balance=100000.0,
            equity=100000.0,
            margin=0.0,
            margin_free=100000.0,
        )

    def positions_get(self):
        return []

    def history_orders_get(self, _start, _end):
        return []

    def history_deals_get(self, _start, _end):
        return []


def test_mt5_terminal_api_verifier_reports_broker_api_verified(tmp_path):
    report = build_mt5_terminal_api_verifier_report(
        mt5_path=r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
        trading_date="2026-06-24",
        output_dir=tmp_path / "mt5-api",
        mt5_module=FakeMT5(),
    )

    assert report["verifier_status"] == "MT5_API_VERIFIER_BROKER_API_VERIFIED"
    assert report["summary"]["terminal_connected"] is True
    assert report["summary"]["account_snapshot_present"] is True
    assert report["summary"]["broker_mode"] == "PAPER_MT5"
    assert report["summary"]["open_positions_reconciled"] is True
    assert "does not place live broker orders" in report["claim_boundary"]

    latest = load_latest_mt5_terminal_api_verifier_report(tmp_path / "mt5-api")
    assert latest["verifier_status"] == "MT5_API_VERIFIER_BROKER_API_VERIFIED"


class FakeLiveMT5(FakeMT5):
    def account_info(self):
        return SimpleNamespace(
            login=123456,
            server="Hugosway-Live",
            company="Hugosway",
            trade_mode=1,
            currency="USD",
            leverage=500,
            balance=100000.0,
            equity=100000.0,
            margin=0.0,
            margin_free=100000.0,
        )


def test_mt5_terminal_api_verifier_blocks_non_demo_account(tmp_path):
    report = build_mt5_terminal_api_verifier_report(
        trading_date="2026-06-24",
        output_dir=tmp_path / "mt5-api",
        mt5_module=FakeLiveMT5(),
        write_report=False,
    )

    assert report["verifier_status"] == "MT5_API_VERIFIER_BLOCKED"
    assert report["summary"]["probe_status"] == "BLOCKED"


def test_mt5_terminal_api_verifier_api_and_dashboard_surface(monkeypatch, tmp_path):
    report = build_mt5_terminal_api_verifier_report(
        trading_date="2026-06-24",
        output_dir=tmp_path / "mt5-api",
        mt5_module=FakeMT5(),
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "mt5_terminal_api_verifier_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"mt5TerminalApiVerifier": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt5-terminal-api-verifier/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_mt5_terminal_api_verifier_report"
    assert body["verifier_status"] == "MT5_API_VERIFIER_BROKER_API_VERIFIED"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt5TerminalApiVerifier"]["summary"]["account_snapshot_present"] is True
