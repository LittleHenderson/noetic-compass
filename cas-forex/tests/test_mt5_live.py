"""Tests for the read-only live MT5 account snapshot (cas_forex.mt5_live).

The real path attaches to a running terminal; these monkeypatch the bridge so the
snapshot shape, position mapping, and not-connected handling are covered without
a live terminal or any IPC.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import mt5_live as mt5_live_route
from cas_forex import mt5_live


@pytest.fixture(autouse=True)
def _reset_cache():
    mt5_live._bridge = None
    mt5_live._cache = None
    mt5_live._cache_expiry = 0.0
    yield
    mt5_live._bridge = None
    mt5_live._cache = None
    mt5_live._cache_expiry = 0.0


class _FakeMT5Module:
    def __init__(
        self,
        positions,
        *,
        terminal_trade_allowed=True,
        account_trade_allowed=True,
        account_trade_expert=True,
    ):
        self._positions = positions
        self._terminal_trade_allowed = terminal_trade_allowed
        self._account_trade_allowed = account_trade_allowed
        self._account_trade_expert = account_trade_expert

    def account_info(self):
        return SimpleNamespace(
            login=108941161, server="MetaQuotes-Demo", name="Demo", currency="USD",
            leverage=100, balance=100000.0, equity=100050.0, margin=81.0,
            margin_free=99919.0, profit=50.0, trade_allowed=self._account_trade_allowed,
            trade_expert=self._account_trade_expert, trade_mode=0,
        )

    def terminal_info(self):
        return SimpleNamespace(connected=True, trade_allowed=self._terminal_trade_allowed, tradeapi_disabled=False)

    def positions_get(self):
        return self._positions

    def symbol_info(self, symbol):
        if symbol == "US30":
            return SimpleNamespace(
                name="US30",
                point=0.01,
                digits=2,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                trade_contract_size=1.0,
                trade_tick_size=0.01,
                trade_tick_value=1.0,
                trade_tick_value_loss=1.0,
                trade_tick_value_profit=1.0,
                trade_stops_level=0,
                trade_freeze_level=0,
            )
        return None

    def symbols_get(self, pattern=None):
        _ = pattern
        return [SimpleNamespace(name="US30")]


class _FakeBridge:
    def __init__(
        self,
        connected=True,
        demo=True,
        positions=(),
        *,
        terminal_trade_allowed=True,
        account_trade_allowed=True,
        account_trade_expert=True,
    ):
        self._connected = connected
        self._demo = demo
        self._mt5 = _FakeMT5Module(
            list(positions),
            terminal_trade_allowed=terminal_trade_allowed,
            account_trade_allowed=account_trade_allowed,
            account_trade_expert=account_trade_expert,
        )

    def is_connected(self):
        return self._connected

    def connect(self):
        return self._connected

    def is_demo_account(self):
        return self._demo


def test_snapshot_when_connected_maps_account_and_positions(monkeypatch):
    pos = SimpleNamespace(ticket=1, type=0, symbol="EURUSD", volume=0.1, price_open=1.1,
                          price_current=1.105, sl=1.05, tp=1.2, profit=12.5, swap=0.0)
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[pos]))
    snap = mt5_live.get_mt5_account_snapshot(force=True)
    assert snap["connected"] is True
    assert snap["is_demo"] is True
    assert snap["account"]["login"] == 108941161
    assert snap["account"]["balance_usd"] == 100000.0
    assert snap["open_position_count"] == 1
    assert snap["algo_allowed"] is True
    assert snap["permission_state"]["status"] == "ORDER_SEND_READY_AT_TERMINAL"
    assert snap["permission_state"]["can_submit_order_send"] is True
    assert snap["position_protection"]["status"] == "ALL_POSITIONS_PROTECTED"
    assert snap["position_protection"]["unprotected_position_count"] == 0
    assert "read-only terminal mirror" in snap["claim_boundary"]
    assert "panel itself does not submit trade actions" in snap["claim_boundary"]
    assert "open, close, and manage trades" in snap["claim_boundary"]
    assert snap["mirror_scope"] == "account + open positions from the running MT5 terminal"
    assert snap["mirror_label"] == "TERMINAL MIRROR"
    assert snap["read_only_label"] == "READ-ONLY MIRROR"
    assert snap["writes_from_panel"] == "none from this panel"
    assert snap["observational_only"] is True
    assert "bridge/verifier path" in snap["execution_path_note"]
    assert "Terminal mirror" in snap["note"]
    assert "observational only" in snap["note"]
    assert "CAS AI and automation handle demo/paper trade actions" in snap["note"]
    p = snap["positions"][0]
    assert p["symbol"] == "EURUSD" and p["side"] == "LONG" and p["floating_pnl_usd"] == 12.5


def test_tick_report_treats_sunday_reopen_as_executable():
    now = datetime(2026, 7, 12, 22, 5, tzinfo=timezone.utc)

    class _TickMt5:
        SYMBOL_TRADE_MODE_DISABLED = 0

        @staticmethod
        def symbol_info_tick(symbol):
            _ = symbol
            tick_at = datetime(2026, 7, 12, 22, 4, 30, tzinfo=timezone.utc)
            return SimpleNamespace(time=tick_at.timestamp(), time_msc=0, bid=1.1, ask=1.2, last=0.0)

        @staticmethod
        def symbol_info(symbol):
            _ = symbol
            return SimpleNamespace(trade_mode=1)

    report = mt5_live._market_tick_report(_TickMt5(), "EURUSD", now=now)

    assert report["status"] == "FRESH"
    assert report["fresh"] is True
    assert report["market_open"] is True
    assert report["tick_age_seconds"] == 30.0


def test_snapshot_separates_fresh_account_read_from_stale_market_tick(monkeypatch):
    pos = SimpleNamespace(
        ticket=3,
        type=0,
        symbol="EURUSD",
        volume=0.1,
        price_open=1.1,
        price_current=1.105,
        sl=1.05,
        tp=1.2,
        profit=12.5,
        swap=0.0,
    )
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[pos]))
    monkeypatch.setattr(
        mt5_live,
        "_market_tick_report",
        lambda _mt5, symbol, now: {
            "symbol": symbol,
            "status": "STALE",
            "tick_observed_at": "2026-07-12T20:00:00+00:00",
            "tick_age_seconds": 7200.0,
            "fresh": False,
            "market_open": False,
            "week_schedule_open": True,
            "detail": "test stale tick",
        },
    )

    snap = mt5_live.get_mt5_account_snapshot(force=True)

    assert snap["snapshot_fresh"] is True
    assert snap["market_tick"]["status"] == "STALE_OR_PARTIAL"
    assert snap["market_tick"]["stale_or_unavailable_symbol_count"] == 1
    assert snap["market_tick"]["oldest_tick_age_seconds"] == 7200.0
    assert snap["positions"][0]["market_tick_status"] == "STALE"
    assert snap["positions"][0]["market_tick_fresh"] is False


def test_short_position_side(monkeypatch):
    pos = SimpleNamespace(ticket=2, type=1, symbol="US30", volume=0.2, price_open=40000.0,
                          price_current=39950.0, sl=0.0, tp=0.0, profit=-10.0, swap=0.0)
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[pos]))
    snap = mt5_live.get_mt5_account_snapshot(force=True)
    p = snap["positions"][0]
    assert p["side"] == "SHORT"
    assert p["stop_loss"] is None and p["take_profit"] is None  # 0.0 -> None
    assert snap["position_protection"]["status"] == "UNPROTECTED_POSITIONS"
    assert snap["position_protection"]["unprotected_positions"][0]["ticket"] == 2


def test_snapshot_exposes_broker_valued_position_risk_and_current_cap(monkeypatch):
    pos = SimpleNamespace(
        ticket=45944855,
        type=1,
        symbol="US30",
        volume=0.01,
        price_open=52_597.82,
        price_current=52_650.00,
        sl=52_734.75,
        tp=52_374.18,
        profit=-52.18,
        swap=0.0,
    )
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[pos]))
    monkeypatch.setattr(mt5_live, "_owner_risk_cap_pct", lambda: 0.1)

    snap = mt5_live.get_mt5_account_snapshot(force=True)

    risk = snap["positions"][0]
    assert risk["risk_at_stop_usd"] == 136.93
    assert risk["risk_at_stop_pct_equity"] == 0.1369
    assert risk["remaining_to_stop_drawdown_usd"] == 84.75
    assert risk["risk_cap_pct"] == 0.1
    assert risk["risk_cap_breached"] is True
    assert risk["risk_economics_source"] == "broker.trade_tick_value/trade_tick_size"
    assert risk["stop_risk"]["risk_basis"] == "ORIGINAL_ENTRY_TO_CURRENT_PROTECTIVE_STOP"
    assert snap["position_risk"]["status"] == "POSITION_RISK_CAP_BREACH"
    assert snap["position_risk"]["risk_cap_breach_count"] == 1
    assert snap["position_risk"]["risk_cap_breach_tickets"] == [45944855]


def test_snapshot_explains_terminal_algo_disabled(monkeypatch):
    monkeypatch.setattr(
        mt5_live,
        "_get_bridge",
        lambda: _FakeBridge(positions=[], terminal_trade_allowed=False),
    )

    snap = mt5_live.get_mt5_account_snapshot(force=True)

    assert snap["connected"] is True
    assert snap["algo_allowed"] is False
    assert snap["permission_state"]["status"] == "TERMINAL_ALGO_DISABLED"
    assert snap["permission_state"]["permission_label"] == "MT5 ORDER_SEND BLOCKED"
    assert "MT5 Algo Trading is off" in snap["permission_state"]["plain_english"]


def test_live_snapshot_keeps_real_execution_path_boundary(monkeypatch):
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(demo=False, positions=[]))

    snap = mt5_live.get_mt5_account_snapshot(force=True)

    assert snap["connected"] is True
    assert snap["is_demo"] is False
    assert "protected order-dispatch path" in snap["execution_path_note"]
    assert "read-only terminal mirror" in snap["claim_boundary"]


def test_permission_snapshot_returns_compact_diagnostics(monkeypatch):
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[]))

    diag = mt5_live.get_mt5_permission_snapshot(force=True)

    assert diag["report_kind"] == "cas_forex_mt5_permission_diagnostics"
    assert diag["connected"] is True
    assert diag["permission_state"]["status"] == "ORDER_SEND_READY_AT_TERMINAL"
    assert diag["permission_state"]["can_submit_order_send"] is True
    assert "positions" not in diag
    assert "does not call order_send" in diag["claim_boundary"]
    assert "does not submit trade actions" in diag["claim_boundary"]
    assert diag["mirror_label"] == "TERMINAL MIRROR"
    assert diag["read_only_label"] == "READ-ONLY MIRROR"
    assert diag["writes_from_panel"] == "none from this panel"
    assert diag["observational_only"] is True


def test_position_protection_snapshot_returns_compact_report(monkeypatch):
    pos = SimpleNamespace(ticket=2, type=1, symbol="US30", volume=0.2, price_open=40000.0,
                          price_current=39950.0, sl=0.0, tp=0.0, profit=-10.0, swap=0.0)
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[pos]))

    report = mt5_live.get_mt5_position_protection_snapshot(force=True)

    assert report["report_kind"] == "cas_forex_position_protection_report"
    assert report["status"] == "UNPROTECTED_POSITIONS"
    assert report["unprotected_position_count"] == 1
    assert report["requires_owner_attention"] is True
    assert report["mirror_label"] == "TERMINAL MIRROR"
    assert report["read_only_label"] == "READ-ONLY MIRROR"
    assert report["writes_from_panel"] == "none from this panel"
    assert report["observational_only"] is True


def test_permission_route_returns_diagnostics(monkeypatch):
    monkeypatch.setattr(
        mt5_live_route,
        "get_mt5_permission_snapshot",
        lambda force=False: {
            "report_kind": "cas_forex_mt5_permission_diagnostics",
            "connected": True,
            "force_seen": force,
            "permission_state": {"status": "ORDER_SEND_READY_AT_TERMINAL"},
        },
    )
    app = FastAPI()
    app.include_router(mt5_live_route.router, prefix="/api/forex/mt5")

    response = TestClient(app).get("/api/forex/mt5/permissions?force=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_kind"] == "cas_forex_mt5_permission_diagnostics"
    assert payload["force_seen"] is True


def test_position_protection_route_returns_report(monkeypatch):
    monkeypatch.setattr(
        mt5_live_route,
        "get_mt5_position_protection_snapshot",
        lambda force=False: {
            "report_kind": "cas_forex_position_protection_report",
            "status": "UNPROTECTED_POSITIONS",
            "force_seen": force,
            "requires_owner_attention": True,
            "unprotected_position_count": 1,
        },
    )
    app = FastAPI()
    app.include_router(mt5_live_route.router, prefix="/api/forex/mt5")

    response = TestClient(app).get("/api/forex/mt5/protection?force=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_kind"] == "cas_forex_position_protection_report"
    assert payload["force_seen"] is True


def test_snapshot_when_not_connected_is_graceful(monkeypatch):
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(connected=False))
    snap = mt5_live.get_mt5_account_snapshot(force=True)
    assert snap["connected"] is False
    assert snap["mirror_label"] == "TERMINAL MIRROR"
    assert snap["read_only_label"] == "READ-ONLY MIRROR"
    assert snap["writes_from_panel"] == "none from this panel"
    assert snap["observational_only"] is True
    assert "detail" in snap  # tells the owner what to do, never raises


def test_read_errors_are_caught(monkeypatch):
    class _Boom:
        def is_connected(self):
            raise RuntimeError("ipc boom")

    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _Boom())
    snap = mt5_live.get_mt5_account_snapshot(force=True)
    assert snap["connected"] is False
    assert "ipc boom" in snap["error"]


def test_cache_serves_without_re_reading(monkeypatch):
    calls = {"n": 0}

    def _bridge():
        calls["n"] += 1
        return _FakeBridge(positions=[])

    monkeypatch.setattr(mt5_live, "_get_bridge", _bridge)
    a = mt5_live.get_mt5_account_snapshot(force=True)
    assert a["cached"] is False
    b = mt5_live.get_mt5_account_snapshot()  # within TTL
    assert b["cached"] is True
    assert calls["n"] == 1  # only one actual read
