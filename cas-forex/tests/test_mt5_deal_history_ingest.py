from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import pytest

import api.server as api_server
import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.mt5_deal_history_ingest import (
    build_mt5_deal_history_ingest_report,
    load_latest_mt5_deal_history_ingest_report,
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


class FakeMT5DealHistory:
    ACCOUNT_TRADE_MODE_DEMO = 0
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self, *, demo: bool = True, empty: bool = False):
        self.demo = demo
        self.empty = empty

    def initialize(self, **_kwargs):
        return True

    def terminal_info(self):
        return SimpleNamespace(
            connected=True,
            name="MetaTrader 5",
            path=r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal",
            data_path=r"C:\Users\wakil\AppData\Roaming\MetaQuotes\Terminal\TEST",
            trade_allowed=True,
            build=3900,
        )

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            server="Hugosway-Demo" if self.demo else "Hugosway-Live",
            company="Hugosway-Demo" if self.demo else "Hugosway",
            trade_mode=self.ACCOUNT_TRADE_MODE_DEMO if self.demo else 1,
            currency="USD",
            leverage=500,
            balance=99999.87,
            equity=99999.87,
            margin=0.0,
            margin_free=99999.87,
        )

    def history_deals_get(self, _start, _end):
        if self.empty:
            return []
        base = int(datetime(2026, 6, 24, 16, 1, tzinfo=timezone.utc).timestamp())
        return [
            SimpleNamespace(
                ticket=900001,
                order=45938644,
                time=base,
                time_msc=base * 1000,
                type=self.DEAL_TYPE_BUY,
                entry=self.DEAL_ENTRY_IN,
                magic=20260601,
                position_id=45938644,
                reason=3,
                volume=0.01,
                price=1.13489,
                commission=0.0,
                swap=0.0,
                profit=0.0,
                fee=0.0,
                symbol="EURUSD",
                comment="CAS_MT5_VERIFY",
                external_id="",
            ),
            SimpleNamespace(
                ticket=900002,
                order=45938645,
                time=base + 12,
                time_msc=(base + 12) * 1000,
                type=self.DEAL_TYPE_SELL,
                entry=self.DEAL_ENTRY_OUT,
                magic=20260601,
                position_id=45938644,
                reason=3,
                volume=0.01,
                price=1.13476,
                commission=-0.01,
                swap=0.0,
                profit=-0.12,
                fee=0.0,
                symbol="EURUSD",
                comment="CAS_CLOSE",
                external_id="",
            ),
        ]


def test_mt5_deal_history_ingest_exports_and_joins_memory(tmp_path):
    memory_report = {
        "summary": {"memory_record_count": 1, "pending_receipt_count": 0},
        "memory_records": [
            {
                "memory_id": "memory-ticket-45938644",
                "broker_ticket": "45938644",
                "symbol": "EUR/USD",
                "direction": "LONG",
                "timeframe": "M1",
                "condition_snapshot_open": {
                    "lot_size": 0.01,
                    "entry_price": 1.13489,
                    "stop_loss": 1.13289,
                },
            }
        ],
    }
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(),
        ticket="45938644",
        memory_report=memory_report,
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "MT5_DEAL_HISTORY_JOINED_TO_MEMORY"
    assert report["summary"]["raw_deal_count"] == 2
    assert report["summary"]["closed_position_count"] == 1
    assert report["summary"]["memory_update_count"] == 1
    assert report["summary"]["net_profit_loss_account"] == pytest.approx(-0.13)
    assert report["history_records"][0]["ticket"] == "45938644"
    assert report["history_records"][0]["direction"] == "buy"
    assert report["history_records"][0]["commission"] == pytest.approx(-0.01)

    latest = load_latest_mt5_deal_history_ingest_report(tmp_path / "mt5-deal-history")
    assert latest["summary"]["memory_update_count"] == 1
    assert latest["terminal_history_ingest"]["summary"]["memory_update_count"] == 1


def test_mt5_deal_history_ingest_reports_empty_demo_history(tmp_path):
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(empty=True),
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "MT5_DEAL_HISTORY_EMPTY"
    assert report["summary"]["raw_deal_count"] == 0
    assert report["summary"]["closed_position_count"] == 0


def test_mt5_deal_history_ingest_blocks_non_demo_account(tmp_path):
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(demo=False),
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "MT5_DEAL_HISTORY_BLOCKED_NON_DEMO_ACCOUNT"
    assert report["summary"]["demo_account_confirmed"] is False


def test_mt5_live_deal_history_requires_explicit_confirmation(tmp_path):
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(demo=False),
        account_mode="live",
        confirm_live_history=False,
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "MT5_DEAL_HISTORY_LIVE_CONFIRM_REQUIRED"
    assert report["account_mode"] == "live"
    assert report["summary"]["live_account_confirmed"] is True
    assert report["summary"]["raw_deal_count"] == 0


def test_mt5_live_deal_history_blocks_demo_account(tmp_path):
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(demo=True),
        account_mode="live",
        confirm_live_history=True,
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "MT5_DEAL_HISTORY_BLOCKED_DEMO_ACCOUNT_FOR_LIVE"
    assert report["summary"]["demo_account_confirmed"] is True
    assert report["summary"]["raw_deal_count"] == 0


def test_mt5_live_deal_history_exports_live_rows_when_confirmed(tmp_path):
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(demo=False),
        account_mode="live",
        confirm_live_history=True,
        memory_report={"summary": {"memory_record_count": 0, "pending_receipt_count": 0}, "memory_records": []},
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "MT5_LIVE_DEAL_HISTORY_EXPORTED_UNMATCHED"
    assert report["summary"]["live_account_confirmed"] is True
    assert report["summary"]["raw_deal_count"] == 2
    assert report["summary"]["net_profit_loss_account"] == pytest.approx(-0.13)
    assert report["history_records"][0]["broker_mode"] == "LIVE_MT5"
    assert report["terminal_history_ingest"]["summary"]["history_record_count"] == 1


def test_mt5_deal_history_ingest_api_and_dashboard_surface(monkeypatch, tmp_path):
    report = build_mt5_deal_history_ingest_report(
        mt5_module=FakeMT5DealHistory(empty=True),
        output_dir=tmp_path / "mt5-deal-history",
        export_dir=tmp_path / "terminal-history-exports",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "mt5_deal_history_ingest_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"mt5DealHistoryIngest": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt5-deal-history-ingest/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_mt5_deal_history_ingest_report"
    assert body["ingest_status"] == "MT5_DEAL_HISTORY_EMPTY"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt5DealHistoryIngest"]["summary"]["raw_deal_count"] == 0
