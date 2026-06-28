"""Tests for the read-only live MT5 account snapshot (cas_forex.mt5_live).

The real path attaches to a running terminal; these monkeypatch the bridge so the
snapshot shape, position mapping, and not-connected handling are covered without
a live terminal or any IPC.
"""

from types import SimpleNamespace

import pytest

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
    def __init__(self, positions):
        self._positions = positions

    def account_info(self):
        return SimpleNamespace(
            login=108941161, server="MetaQuotes-Demo", name="Demo", currency="USD",
            leverage=100, balance=100000.0, equity=100050.0, margin=81.0,
            margin_free=99919.0, profit=50.0,
        )

    def terminal_info(self):
        return SimpleNamespace(connected=True, trade_allowed=True)

    def positions_get(self):
        return self._positions


class _FakeBridge:
    def __init__(self, connected=True, demo=True, positions=()):
        self._connected = connected
        self._demo = demo
        self._mt5 = _FakeMT5Module(list(positions))

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
    p = snap["positions"][0]
    assert p["symbol"] == "EURUSD" and p["side"] == "LONG" and p["floating_pnl_usd"] == 12.5


def test_short_position_side(monkeypatch):
    pos = SimpleNamespace(ticket=2, type=1, symbol="US30", volume=0.2, price_open=40000.0,
                          price_current=39950.0, sl=0.0, tp=0.0, profit=-10.0, swap=0.0)
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(positions=[pos]))
    snap = mt5_live.get_mt5_account_snapshot(force=True)
    p = snap["positions"][0]
    assert p["side"] == "SHORT"
    assert p["stop_loss"] is None and p["take_profit"] is None  # 0.0 -> None


def test_snapshot_when_not_connected_is_graceful(monkeypatch):
    monkeypatch.setattr(mt5_live, "_get_bridge", lambda: _FakeBridge(connected=False))
    snap = mt5_live.get_mt5_account_snapshot(force=True)
    assert snap["connected"] is False
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
