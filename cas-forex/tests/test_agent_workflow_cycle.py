"""CAS Forex agent workflow execution-cycle coverage."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import api.server as api_server
import api.routes.strategy as strategy_routes
import pytest
from api.server import app
from cas_forex.agent_state import TERMINAL_LANE_MT5_DEMO, run_agent_workflow_cycle
from cas_forex.micro_scalp_policy import build_micro_scalp_intents


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


class FakeMT5AgentWorkflow:
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
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self):
        self.ticket = 987654
        self.sent_requests: list[dict[str, Any]] = []
        self.closed_tickets: list[int] = []

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

    def positions_get(self, ticket=None):
        if ticket:
            request = self.sent_requests[0] if self.sent_requests else {"symbol": "AUDCAD", "volume": 0.01, "price": 1.1002, "comment": "CAS"}
            return [
                SimpleNamespace(
                    ticket=ticket,
                    symbol=request["symbol"],
                    type=self.POSITION_TYPE_BUY,
                    volume=request["volume"],
                    price_open=request["price"],
                    price_current=request["price"] - 0.0001,
                    profit=-0.12,
                    swap=0.0,
                    comment=request.get("comment", "CAS"),
                    magic=request.get("magic", 20260624),
                )
            ]
        return []

    def history_orders_get(self, _start, _end):
        return []

    def history_deals_get(self, _start, _end, group="*"):
        request = self.sent_requests[0] if self.sent_requests else {"symbol": "AUDCAD", "volume": 0.01, "price": 1.1002, "comment": "CAS"}
        base = int(datetime(2026, 6, 24, 16, 1, tzinfo=timezone.utc).timestamp())
        return [
            SimpleNamespace(
                ticket=900001,
                order=self.ticket,
                time=base,
                time_msc=base * 1000,
                type=self.DEAL_TYPE_BUY,
                entry=self.DEAL_ENTRY_IN,
                magic=request.get("magic", 20260624),
                position_id=self.ticket,
                reason=3,
                volume=request["volume"],
                price=request["price"],
                commission=0.0,
                swap=0.0,
                profit=0.0,
                fee=0.0,
                symbol=request["symbol"],
                comment=request.get("comment", "CAS"),
                external_id="",
            ),
            SimpleNamespace(
                ticket=900002,
                order=self.ticket + 1,
                time=base + 12,
                time_msc=(base + 12) * 1000,
                type=self.DEAL_TYPE_SELL,
                entry=self.DEAL_ENTRY_OUT,
                magic=request.get("magic", 20260624),
                position_id=self.ticket,
                reason=3,
                volume=request["volume"],
                price=request["price"] - 0.0001,
                commission=-0.01,
                swap=0.0,
                profit=-0.12,
                fee=0.0,
                symbol=request["symbol"],
                comment="CAS_CLOSE",
                external_id="",
            ),
        ]

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(bid=1.1000, ask=1.1002)

    def symbol_info(self, _symbol):
        return SimpleNamespace(filling_mode=1)

    def order_check(self, request):
        return SimpleNamespace(retcode=0, comment="check ok", request_id=1, margin=1.0)

    def order_send(self, request):
        if "position" in request:
            self.closed_tickets.append(int(request["position"]))
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=int(request["position"]), price=request["price"], comment="closed")
        self.sent_requests.append(dict(request))
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=self.ticket, price=request["price"], comment="filled")


def test_micro_scalp_policy_builds_mt4_ready_route_intent():
    intents = build_micro_scalp_intents(
        {
            "replay_verdict": "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW",
            "condition_summary": {
                "top_condition_cells": [
                    {
                        "symbol": "AUD/CAD",
                        "timeframe": "M5",
                        "setting": "range_scalper_12_80",
                        "score": 5.0378,
                        "win_rate": 0.9722,
                    }
                ]
            },
            "report_path": "replay.json",
        },
        {
            "report_path": "candidates.json",
            "candidates": [
                {
                    "cas_symbol": "AUD/CAD",
                    "timeframe": "M5",
                    "risk_shape": {"lot_size": 0.9, "stop_loss": 29, "take_profit": 5},
                }
            ],
        },
    )

    assert len(intents) == 1
    intent = intents[0]
    assert intent.agent_id == "micro_scalp_agent"
    assert intent.action == "OPEN_MICRO_SCALP"
    assert intent.symbol == "AUD/CAD"
    assert intent.order_request is not None
    assert intent.order_request["symbol"] == "AUD/CAD"
    assert intent.order_request["volume"] == 0.9


def test_overseer_approves_first_same_symbol_route_and_rejects_duplicate(tmp_path):
    report = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    decisions = report["overseer_decisions"]

    assert report["summary"]["route_intent_count"] == 2
    assert report["summary"]["approved_intent_count"] == 1
    assert report["summary"]["rejected_intent_count"] == 1
    assert decisions[0]["decision"] == "APPROVE_ROUTE_INTENT"
    assert decisions[1]["decision"] == "REJECT_ROUTE_INTENT"
    assert "same-symbol route already approved" in " ".join(decisions[1]["reasons"])


def test_agent_cycle_writes_paper_mt4_command_and_state(tmp_path):
    report = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")

    assert report["report_kind"] == "cas_forex_agent_workflow_cycle"
    assert report["execution_mode"] == "PAPER_MT4_COMMAND_INTENT"
    assert report["summary"]["terminal_command_count"] == 1
    assert "do not by themselves execute live broker orders" in report["claim_boundary"]
    assert "order_dispatch.py" in report["claim_boundary"]
    assert report["live_execution_boundary"]["live_trading_status"] == "OWNER_ARMING_REQUIRED"
    command_path = Path(report["terminal_commands"][0]["command_path"])
    assert command_path.exists()
    command = json.loads(command_path.read_text(encoding="utf-8"))
    assert command["command_type"] == "PLACE_ORDER"
    assert command["broker_mode"] == "PAPER_MT4"
    assert command["live_money_authorized"] is False
    assert Path(report["state_path"]).exists()
    assert Path(report["event_journal"]["event_log_path"]).exists()
    assert report["event_journal"]["pending_receipt_count"] >= 1


def test_agent_cycle_can_execute_mt5_demo_and_join_deal_history(tmp_path):
    fake = FakeMT5AgentWorkflow()
    report = run_agent_workflow_cycle(
        output_dir=tmp_path / "cycles",
        mailbox_dir=tmp_path / "mailbox",
        terminal_lane=TERMINAL_LANE_MT5_DEMO,
        execute_mt5_demo_order=True,
        confirm_mt5_demo_order=True,
        mt5_module=fake,
        mt5_execution_output_dir=tmp_path / "mt5-exec",
        mt5_deal_history_output_dir=tmp_path / "mt5-deals",
        terminal_history_output_dir=tmp_path / "terminal-history-ingest",
        terminal_history_export_dir=tmp_path / "terminal-history-exports",
        agent_memory_output_dir=tmp_path / "agent-memory",
    )

    loop = report["mt5_execution_loop"]
    command = report["terminal_commands"][0]
    receipt = command["terminal_receipt"]

    assert report["execution_mode"] == "PAPER_MT5_DEMO_AGENT_LOOP"
    assert report["summary"]["terminal_lane"] == TERMINAL_LANE_MT5_DEMO
    assert report["summary"]["terminal_command_count"] == 1
    assert report["event_journal"]["pending_receipt_count"] == 0
    assert report["event_journal"]["event_type_counts"]["NEXT_CYCLE_ALLOWED"] == 1
    assert report["event_journal"]["status_counts"]["NEXT_CYCLE_ALLOWED"] == 1
    assert command["broker_mode"] == "PAPER_MT5"
    assert command["command_status"] == "MT5_DEMO_ORDER_EXECUTED"
    assert receipt["lifecycle_status"] == "RECEIPT_VERIFIED"
    assert receipt["broker_ticket"] == fake.ticket
    assert fake.closed_tickets == [fake.ticket]
    assert loop["loop_status"] == "MT5_DEMO_EXECUTION_DEAL_HISTORY_JOINED"
    assert loop["deal_history_ingest"]["ingest_status"] == "MT5_DEAL_HISTORY_JOINED_TO_MEMORY"
    assert loop["deal_history_ingest"]["summary"]["memory_update_count"] == 1
    assert loop["post_deal_memory"]["summary"]["terminal_history_joined_count"] == 1
    assert loop["post_deal_memory"]["summary"]["net_profit_loss_account"] == pytest.approx(-0.13)
    assert report["summary"]["mt5_deal_history_memory_update_count"] == 1
    assert report["summary"]["mt5_net_profit_loss_account"] == pytest.approx(-0.13)


def test_agent_cycle_route_and_dashboard_surface_latest_cycle(monkeypatch, tmp_path):
    report = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    monkeypatch.setattr(strategy_routes, "agent_workflow_cycle", lambda: report)
    monkeypatch.setattr(
        api_server,
        "dashboard_state",
        lambda: {
            "agentWorkflowCycle": report,
            "agentMessageBus": report["event_journal"],
        },
    )

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/agent-workflow-cycle/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_agent_workflow_cycle"
    assert body["summary"]["approved_intent_count"] >= 1
    assert body["summary"]["terminal_command_count"] >= 1

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "agentWorkflowCycle" in dashboard
    assert "agentMessageBus" in dashboard
    assert dashboard["agentWorkflowCycle"]["execution_mode"] == "PAPER_MT4_COMMAND_INTENT"
    assert dashboard["agentMessageBus"]["event_count"] >= dashboard["agentWorkflowCycle"]["summary"]["event_count"]
