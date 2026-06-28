"""Coverage for MT5 process guard (worker spec, guard integration, timeout handling)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex import agent_state as agent_state_module
from cas_forex.mt5_process_guard import (
    DEFAULT_MT5_TIMEOUT_SECONDS,
    MT5WorkerSpec,
    _worker_execute_demo_order,
    _worker_get_deal_history,
    _worker_get_account_snapshot,
    _worker_get_open_positions,
    _worker_close_single_position,
    run_mt5_operation_safe,
)
from cas_forex.agent_state import (
    TERMINAL_LANE_MT5_DEMO,
    _run_mt5_execution_via_guard,
    _run_mt5_deal_history_via_guard,
    run_agent_workflow_cycle,
)
from cas_forex.schemas.order import BrokerOrderRequest


# ---------------------------------------------------------------------------
# Worker spec
# ---------------------------------------------------------------------------


def test_worker_spec_serializes_cleanly():
    spec = MT5WorkerSpec(operation="get_account_snapshot", mt5_path="C:\\mt5\\terminal64.exe")
    d = json.loads(json.dumps(spec.__dict__))
    assert d["operation"] == "get_account_snapshot"
    assert d["mt5_path"] == "C:\\mt5\\terminal64.exe"
    assert "schema" in d
    assert "timestamp" in d


def test_worker_spec_timestamp_default():
    spec = MT5WorkerSpec(operation="test", mt5_path="/fake/path")
    assert spec.timestamp > 0


# ---------------------------------------------------------------------------
# Fake MT5 for worker-level unit tests
# ---------------------------------------------------------------------------


class _DealRow:
    """Fake MT5 deal row that supports _asdict() like namedtuple."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def _asdict(self):
        return dict(self.__dict__)


class _FakeMT5Worker:
    """Minimal fake MT5 for unit-testing worker operation functions."""

    def __init__(self):
        # order attributes
        self.ORDER_TYPE_BUY = 0
        self.ORDER_TYPE_SELL = 1
        self.TRADE_ACTION_DEAL = 1
        self.ORDER_TIME_GTC = 0
        self.ORDER_FILLING_FOK = 0
        self.ORDER_FILLING_IOC = 1
        self.TRADE_RETCODE_DONE = 10009
        self.TRADE_RETCODE_REJECT = 10006
        self.SYMBOL_FILLING_FOK = 1
        self.SYMBOL_FILLING_IOC = 2
        self.POSITION_TYPE_BUY = 0
        self.POSITION_TYPE_SELL = 1

        # captured state
        self.sent_order = None
        self.sent_close = None
        self.close_success = True

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=1.1340, ask=1.1341)

    def symbol_info(self, symbol):
        return SimpleNamespace(digits=5, filling_mode=self.SYMBOL_FILLING_FOK | self.SYMBOL_FILLING_IOC)

    def order_check(self, request):
        return SimpleNamespace(retcode=0, comment="OK")

    def order_send(self, request):
        self.sent_order = request
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            order=45938644,
            price=1.1341,
            comment="",
        )

    def positions_get(self, ticket=None):
        if ticket is None:
            return ()
        return (SimpleNamespace(
            ticket=ticket,
            symbol="EUR/USD",
            type=self.POSITION_TYPE_BUY,
            volume=0.01,
            price_open=1.1340,
            sl=0.0,
            tp=0.0,
            price_current=1.1341,
            profit=0.01,
            comment="CAS_FOREX_DEMO",
        ),)

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            server="Hugosway-Demo",
            balance=100000.0,
            equity=100000.0,
            margin=0.0,
            margin_free=100000.0,
            trade_mode=0,
        )

    def terminal_info(self):
        return SimpleNamespace(
            connected=True,
            trade_allowed=True,
        )

    def last_error(self):
        return (0, "")

    def shutdown(self):
        pass

    def history_deals_get(self, date_from, date_to):
        return (
            _DealRow(
                ticket=500001,
                position_id=45938644,
                order=45938644,
                time=1719230000,
                type=0,
                entry=0,
                symbol="EUR/USD",
                volume=0.01,
                price=1.13489,
                commission=-0.05,
                swap=0.0,
                profit=0.0,
                comment="CAS_FOREX_DEMO",
            ),
            _DealRow(
                ticket=500002,
                position_id=45938644,
                order=45938644,
                time=1719230060,
                type=1,
                entry=1,
                symbol="EUR/USD",
                volume=0.01,
                price=1.13481,
                commission=0.0,
                swap=0.0,
                profit=-0.08,
                comment="CAS_FOREX_DEMO_CLOSE",
            ),
        )


# ---------------------------------------------------------------------------
# Worker operation unit tests
# ---------------------------------------------------------------------------


def test_worker_execute_demo_order_buy():
    mt5 = _FakeMT5Worker()
    result = _worker_execute_demo_order(mt5, {
        "symbol": "EUR/USD",
        "direction": "LONG",
        "volume": 0.01,
        "stop_loss": 1.1300,
        "take_profit": 1.1400,
        "close_after_send": False,
    })
    assert result["execution_status"] == "ORDER_EXECUTED"
    assert result["broker_ticket"] == 45938644
    assert result["filled_price"] == 1.1341
    assert not result["close_attempted"]
    assert not result["close_success"]
    assert result["order_check"]["order_check_status"] == "ORDER_CHECK_OK"
    assert mt5.sent_order is not None
    assert mt5.sent_order["symbol"] == "EUR/USD"


def test_worker_execute_demo_order_sell_with_close():
    mt5 = _FakeMT5Worker()
    result = _worker_execute_demo_order(mt5, {
        "symbol": "EUR/USD",
        "direction": "SHORT",
        "volume": 0.01,
        "stop_loss": None,
        "take_profit": None,
        "close_after_send": True,
    })
    assert result["execution_status"] == "ORDER_EXECUTED"
    assert result["close_attempted"] is True
    assert result["close_success"] is True


def test_worker_get_deal_history_by_ticket():
    mt5 = _FakeMT5Worker()
    result = _worker_get_deal_history(mt5, {"ticket": 45938644, "future_minutes": 120})
    assert result["raw_deal_count"] == 2
    assert result["ticket_filter"] == "45938644"
    assert len(result["deals"]) == 2


def test_worker_get_account_snapshot():
    mt5 = _FakeMT5Worker()
    result = _worker_get_account_snapshot(mt5, {})
    assert result.get("is_demo") is True
    assert "balance" in result
    assert "server" in result


def test_worker_get_open_positions():
    mt5 = _FakeMT5Worker()
    result = _worker_get_open_positions(mt5, {})
    # Fake returns no open positions by default (empty tuple)
    assert result["position_count"] == 0


def test_worker_close_single_position_success():
    mt5 = _FakeMT5Worker()
    success = _worker_close_single_position(mt5, 45938644)
    assert success is True


def test_worker_close_single_position_no_position():
    mt5 = _FakeMT5Worker()
    mt5.positions_get = lambda ticket: None
    success = _worker_close_single_position(mt5, 999999)
    assert success is False


# ---------------------------------------------------------------------------
# Process guard integration: run_mt5_operation_safe with invalid path
# ---------------------------------------------------------------------------


def test_guard_handles_timeout_on_nonexistent_mt5(tmp_path):
    """Guard should return failure (init error or timeout) for nonexistent MT5 path."""
    result = run_mt5_operation_safe(
        mt5_path="C:\\NONEXISTENT\\terminal64.exe",
        operation="get_account_snapshot",
        params={},
        timeout_seconds=5,
    )
    assert result.get("success") is False
    assert result.get("error") in {"MT5_WORKER_FAILED", "MT5_TIMEOUT", "MT5_IMPORT_ERROR", "MT5_INIT_FAILED"}


# ---------------------------------------------------------------------------
# Guard-based execution report helpers (unit tests)
# ---------------------------------------------------------------------------


def test_run_mt5_execution_via_guard_success(tmp_path):
    """_run_mt5_execution_via_guard builds correct report from guard result via mock."""
    with mock.patch("cas_forex.mt5_process_guard.run_mt5_operation_safe") as mock_safe:
        mock_safe.return_value = {
            "success": True,
            "result": {
                "execution_status": "ORDER_EXECUTED",
                "broker_ticket": 987654,
                "filled_price": 1.1350,
                "close_attempted": True,
                "close_success": True,
                "raw_request_hash": "abc123",
                "order_check": {"order_check_status": "ORDER_CHECK_OK"},
            },
        }

        from cas_forex.agent_state import RouteIntent
        intent = RouteIntent(
            intent_id="test-intent-1",
            agent_id="test-agent",
            action="PLACE_ORDER",
            symbol="EUR/USD",
            timeframe="M1",
            strategy_setting="default",
            direction="LONG",
            confidence=0.8,
            evidence_score=0.9,
            lot_size=0.01,
            entry_price=1.1350,
            stop_loss=1.1300,
            take_profit=1.1400,
            reason="test",
        )
        order = BrokerOrderRequest(
            order_id="test-order-1",
            decision_ref="decision-ref-1",
            symbol="EUR/USD",
            direction="LONG",
            volume=0.01,
            stop_loss=1.1300,
            take_profit=1.1400,
        )

        report = _run_mt5_execution_via_guard(
            mt5_path=r"C:\mt5\terminal64.exe",
            intent=intent,
            order=order,
            close_after_send=True,
            timeout_seconds=120,
            output_dir=str(tmp_path),
        )

        assert report["verifier_status"] == "MT5_PAPER_EXECUTION_DEMO_ORDER_EXECUTED"
        assert report["summary"]["execution_status"] == "ORDER_EXECUTED"
        assert report["summary"]["broker_ticket"] == 987654
        assert report["summary"]["close_success"] is True
        assert report["execution_controls"]["process_guard_used"] is True


def test_run_mt5_execution_via_guard_failure(tmp_path):
    """_run_mt5_execution_via_guard handles guard failure gracefully."""
    with mock.patch("cas_forex.mt5_process_guard.run_mt5_operation_safe") as mock_safe:
        mock_safe.return_value = {
            "success": False,
            "error": "MT5_TIMEOUT",
            "message": "MT5 operation timed out after 60s",
        }

        from cas_forex.agent_state import RouteIntent
        intent = RouteIntent(
            intent_id="test-intent-2",
            agent_id="test-agent",
            action="PLACE_ORDER",
            symbol="EUR/USD",
            timeframe="M1",
            strategy_setting="default",
            direction="LONG",
            confidence=0.8,
            evidence_score=0.9,
            lot_size=0.01,
            entry_price=1.1350,
            stop_loss=None,
            take_profit=None,
            reason="test",
        )
        order = BrokerOrderRequest(
            order_id="test-order-2",
            decision_ref="decision-ref-2",
            symbol="EUR/USD",
            direction="LONG",
            volume=0.01,
            stop_loss=1.1300,
            take_profit=1.1400,
        )

        report = _run_mt5_execution_via_guard(
            mt5_path=r"C:\mt5\terminal64.exe",
            intent=intent,
            order=order,
            close_after_send=True,
            timeout_seconds=60,
            output_dir=str(tmp_path),
        )

        assert report["verifier_status"] == "MT5_PAPER_EXECUTION_ORDER_REJECTED"
        assert report["summary"]["execution_status"] == "ORDER_REJECTED"
        assert report["summary"]["execution_error_message"] == "MT5 operation timed out after 60s"
        assert report["execution_controls"]["process_guard_used"] is True


def test_run_mt5_deal_history_via_guard(tmp_path):
    """_run_mt5_deal_history_via_guard builds correct report from guard deal data."""
    with mock.patch("cas_forex.mt5_process_guard.run_mt5_operation_safe") as mock_safe:
        mock_safe.return_value = {
            "success": True,
            "result": {
                "deals": [
                    {"entry": 0, "profit": 0.0, "commission": -0.05, "swap": 0.0},
                    {"entry": 1, "profit": -0.08, "commission": 0.0, "swap": 0.0},
                ],
            },
        }

        report = _run_mt5_deal_history_via_guard(
            mt5_path=r"C:\mt5\terminal64.exe",
            ticket="987654",
            future_minutes=120,
            timeout_seconds=120,
            memory_report={},
            export_dir=tmp_path / "exports",
            terminal_history_dir=tmp_path / "history",
        )

        assert report["ingest_status"] == "MT5_DEAL_HISTORY_INGEST_VIA_PROCESS_GUARD"
        assert report["summary"]["raw_deal_count"] == 2
        assert report["summary"]["closed_position_count"] == 1
        assert report["summary"]["net_profit_loss_account"] == -0.08
        assert report["summary"]["total_commission"] == -0.05
        assert report["guard_success"] is True


# ---------------------------------------------------------------------------
# No-regression: guard flag OFF preserves existing path
# ---------------------------------------------------------------------------


def test_agent_cycle_with_guard_flag_off_uses_direct_path(tmp_path):
    """When mt5_use_process_guard=False, cycle uses the normal MT5 path."""
    report = run_agent_workflow_cycle(
        output_dir=tmp_path / "cycles",
        terminal_lane=TERMINAL_LANE_MT5_DEMO,
        mt5_use_process_guard=False,
        mt5_path=None,
        write_terminal_commands=False,
        trigger_source="TEST",
    )
    assert report["execution_mode"] == "PAPER_MT5_DEMO_AGENT_LOOP"
    assert report["summary"]["terminal_command_count"] >= 0
