from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import api.server as api_server
import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.mt5_paper_execution_verifier import (
    build_mt5_paper_execution_verifier_report,
    load_latest_mt5_paper_execution_verifier_report,
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


class FakeMT5PaperExecution:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_REJECT = 10006
    TRADE_RETCODE_CANCEL = 10007
    TRADE_RETCODE_CLIENT_DISABLES_AT = 10027
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1

    def __init__(self, *, demo: bool = True, autotrading_disabled: bool = False):
        self.demo = demo
        self.autotrading_disabled = autotrading_disabled
        self.sent_requests: list[dict] = []
        self.closed_tickets: list[int] = []

    def initialize(self, **_kwargs):
        return True

    def terminal_info(self):
        return SimpleNamespace(
            connected=True,
            name="MetaTrader 5",
            path=r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal",
            data_path=r"C:\Users\wakil\AppData\Roaming\MetaQuotes\Terminal\TEST",
            trade_allowed=not self.autotrading_disabled,
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
            balance=100000.0,
            equity=100000.0,
            margin=0.0,
            margin_free=100000.0,
        )

    def positions_get(self, ticket=None):
        if ticket:
            return [
                SimpleNamespace(
                    ticket=ticket,
                    symbol="EURUSD",
                    type=self.POSITION_TYPE_BUY,
                    volume=0.01,
                    price_open=1.1002,
                    price_current=1.1004,
                    profit=0.2,
                    swap=0.0,
                    comment="CAS_MT5_VERIFY",
                    magic=20260601,
                )
            ]
        return []

    def history_orders_get(self, _start, _end):
        return []

    def history_deals_get(self, _start, _end):
        return []

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(bid=1.1000, ask=1.1002)

    def symbol_info(self, _symbol):
        return SimpleNamespace(filling_mode=1)

    def order_check(self, request):
        return SimpleNamespace(retcode=0, comment="check ok", request_id=1, margin=1.0)

    def order_send(self, request):
        self.sent_requests.append(dict(request))
        if self.autotrading_disabled:
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_CLIENT_DISABLES_AT,
                order=0,
                deal=0,
                price=0.0,
                comment="AutoTrading disabled by client",
            )
        if "position" in request:
            self.closed_tickets.append(int(request["position"]))
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=int(request["position"]), price=request["price"], comment="closed")
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=987654, price=request["price"], comment="filled")


def test_mt5_paper_execution_verifier_dry_run_builds_request(tmp_path):
    fake = FakeMT5PaperExecution()
    report = build_mt5_paper_execution_verifier_report(
        mt5_module=fake,
        output_dir=tmp_path / "mt5-paper-exec",
    )

    assert report["verifier_status"] == "MT5_PAPER_EXECUTION_DRY_RUN_READY"
    assert report["summary"]["mt5_api_verified"] is True
    assert report["summary"]["order_request_built"] is True
    assert report["summary"]["order_check_status"] == "ORDER_CHECK_OK"
    assert report["summary"]["execution_attempted"] is False
    assert report["mt5_request"]["type_filling"] == fake.ORDER_FILLING_FOK
    assert fake.sent_requests == []

    latest = load_latest_mt5_paper_execution_verifier_report(tmp_path / "mt5-paper-exec")
    assert latest["verifier_status"] == "MT5_PAPER_EXECUTION_DRY_RUN_READY"


def test_mt5_paper_execution_verifier_requires_confirm_for_send(tmp_path):
    fake = FakeMT5PaperExecution()
    report = build_mt5_paper_execution_verifier_report(
        mt5_module=fake,
        execute_demo_order=True,
        confirm_demo_order=False,
        output_dir=tmp_path / "mt5-paper-exec",
        write_report=False,
    )

    assert report["verifier_status"] == "MT5_PAPER_EXECUTION_SEND_NOT_CONFIRMED"
    assert report["summary"]["execution_attempted"] is False
    assert fake.sent_requests == []


def test_mt5_paper_execution_verifier_can_execute_and_close_demo_order(tmp_path):
    fake = FakeMT5PaperExecution()
    report = build_mt5_paper_execution_verifier_report(
        mt5_module=fake,
        execute_demo_order=True,
        confirm_demo_order=True,
        output_dir=tmp_path / "mt5-paper-exec",
        write_report=False,
    )

    assert report["verifier_status"] == "MT5_PAPER_EXECUTION_DEMO_ORDER_EXECUTED"
    assert report["summary"]["execution_attempted"] is True
    assert report["summary"]["execution_status"] == "ORDER_EXECUTED"
    assert report["summary"]["close_attempted"] is True
    assert report["summary"]["close_success"] is True
    assert fake.closed_tickets == [987654]


def test_mt5_paper_execution_verifier_reports_autotrading_disabled(tmp_path):
    fake = FakeMT5PaperExecution(autotrading_disabled=True)
    report = build_mt5_paper_execution_verifier_report(
        mt5_module=fake,
        execute_demo_order=True,
        confirm_demo_order=True,
        output_dir=tmp_path / "mt5-paper-exec",
        write_report=False,
    )

    assert report["verifier_status"] == "MT5_PAPER_EXECUTION_DEMO_ORDER_REJECTED"
    assert report["summary"]["terminal_trade_allowed"] is False
    assert report["summary"]["execution_status"] == "ORDER_REJECTED"
    # The send may be pre-blocked by mt5_permissions before the broker request
    # (newer, more fail-closed) or rejected by the terminal with the broker's
    # own comment. Both convey the same fact: Algo Trading is off.
    error_message = report["summary"]["execution_error_message"]
    assert (
        "AutoTrading disabled by client" in error_message
        or "Algo Trading is off" in error_message
    ), error_message
    # The request that WAS built is hashed; a broker response that never
    # happened is not. When the send is pre-blocked, raw_response_hash must be
    # honestly absent - hashing a nonexistent response would be fake evidence.
    assert report["summary"]["raw_request_hash"]
    if "blocked before broker request" in error_message:
        assert report["summary"]["raw_response_hash"] is None
    else:
        assert report["summary"]["raw_response_hash"]
    assert "AutoTrading disabled by client" in report["next_action"]


def test_mt5_paper_execution_verifier_blocks_non_demo_account(tmp_path):
    report = build_mt5_paper_execution_verifier_report(
        mt5_module=FakeMT5PaperExecution(demo=False),
        output_dir=tmp_path / "mt5-paper-exec",
        write_report=False,
    )

    assert report["verifier_status"] in {
        "MT5_PAPER_EXECUTION_BLOCKED_BY_API_VERIFIER",
        "MT5_PAPER_EXECUTION_BLOCKED_NON_DEMO_ACCOUNT",
    }


def test_mt5_paper_execution_verifier_api_and_dashboard_surface(monkeypatch, tmp_path):
    report = build_mt5_paper_execution_verifier_report(
        mt5_module=FakeMT5PaperExecution(),
        output_dir=tmp_path / "mt5-paper-exec",
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "mt5_paper_execution_verifier_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"mt5PaperExecutionVerifier": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt5-paper-execution-verifier/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_mt5_paper_execution_verifier_report"
    assert body["verifier_status"] == "MT5_PAPER_EXECUTION_DRY_RUN_READY"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt5PaperExecutionVerifier"]["summary"]["order_request_built"] is True
