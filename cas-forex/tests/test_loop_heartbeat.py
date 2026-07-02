"""The WASTE-loop heartbeat: honest OFFLINE when idle, LIVE only on a fresh tick."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.routes import loop_stage
from cas_forex import loop_heartbeat as H
from cas_forex import waste_runner


@pytest.fixture(autouse=True)
def _clean():
    H.reset()
    yield
    H.reset()


def test_offline_when_never_ticked():
    s = H.snapshot()
    assert s["running"] is False
    assert s["stage"] == "idle"
    assert s["updated_at"] is None


def test_running_after_record():
    H.record("test", detail="vs the null gate", symbol="EUR/USD")
    s = H.snapshot()
    assert s["running"] is True
    assert s["stage"] == "test"
    assert s["detail"] == "vs the null gate"
    assert s["symbol"] == "EUR/USD"
    assert s["stage_trace"] == ["test"]


def test_records_compact_stage_trace():
    H.record("watch")
    H.record("analyze")
    H.record("strategize")
    H.record("strategize")
    H.record("no_trade")

    s = H.snapshot()

    assert s["running"] is True
    assert s["stage"] == "no_trade"
    assert s["stage_trace"] == ["watch", "analyze", "strategize", "no_trade"]


def test_collapses_to_idle_when_stale():
    H.record("execute")
    # A tiny staleness window forces the beat to read as offline.
    s = H.snapshot(stale_after_s=-1.0)
    assert s["running"] is False
    assert s["stage"] == "idle"          # stage masked to idle when not running
    assert s["detail"] is None
    assert s["updated_at"] is not None   # the raw timestamp is still reported


def test_unknown_stage_collapses_to_idle():
    H.record("nonsense-stage")
    assert H.snapshot()["stage"] == "idle"


def test_stage_route_reads_isolated_worker_when_api_heartbeat_is_empty(monkeypatch):
    """An API restart clears process-local heartbeat memory; the worker is durable."""

    def fake_runner_status():
        return {
            "running": True,
            "current_stage": "no_trade",
            "last_decision": "NO_TRADE",
            "last_run_iso": datetime.now(timezone.utc).isoformat(),
            "cycles_run": 12,
            "mode": "PAPER",
            "worker_isolated": True,
            "supervisor": {
                "active_lease_is_fresh": True,
                "active_lease": {"interval_seconds": 5},
            },
            "external_worker": {
                "running": True,
                "config": {"interval_seconds": 5},
            },
            "durable_cycle": {
                "stage_trace": ["watch", "analyze", "strategize", "test", "no_trade"],
                "candidate": {"symbol": "US30"},
            },
        }

    monkeypatch.setattr(waste_runner, "runner_status", fake_runner_status)
    local = H.snapshot()

    stage = loop_stage._runner_backed_snapshot(local)

    assert stage["running"] is True
    assert stage["stage"] == "no_trade"
    assert stage["source"] == "waste_runner_status"
    assert stage["worker_isolated"] is True
    assert stage["symbol"] == "US30"
    assert stage["stage_trace"] == [
        "watch",
        "analyze",
        "strategize",
        "test",
        "execute",
        "no_trade",
    ]


def test_stage_route_accepts_fresh_supervisor_when_worker_record_is_unconfigured(monkeypatch):
    """A fresh durable lease is enough when the worker registry row is missing."""

    def fake_runner_status():
        return {
            "running": True,
            "current_stage": "no_trade",
            "last_decision": "NO_TRADE",
            "last_run_iso": datetime.now(timezone.utc).isoformat(),
            "cycles_run": 17,
            "mode": "PAPER",
            "worker_isolated": True,
            "supervisor": {
                "active_lease_is_fresh": True,
                "active_lease": {"interval_seconds": 60},
            },
            "external_worker": {
                "configured": False,
                "running": False,
                "config": None,
            },
            "durable_cycle": {
                "stage_trace": ["watch", "analyze", "strategize", "no_trade"],
                "candidate": {"symbol": "NAS100"},
            },
        }

    monkeypatch.setattr(waste_runner, "runner_status", fake_runner_status)
    stage = loop_stage._runner_backed_snapshot(H.snapshot())

    assert stage["running"] is True
    assert stage["stage"] == "no_trade"
    assert stage["source"] == "waste_runner_status"
    assert stage["symbol"] == "NAS100"
    assert stage["stage_trace"] == [
        "watch",
        "analyze",
        "strategize",
        "test",
        "execute",
        "no_trade",
    ]


def test_stage_route_expands_local_no_trade_trace_for_full_waste_indicator():
    H.record("watch")
    H.record("analyze")
    H.record("strategize")
    H.record("no_trade")

    stage = loop_stage._loop_stage_payload()

    assert stage["stage"] == "no_trade"
    assert stage["stage_trace"] == [
        "watch",
        "analyze",
        "strategize",
        "test",
        "execute",
        "no_trade",
    ]


def test_stage_route_cache_does_not_block_cold_first_paint(monkeypatch):
    """The dashboard heartbeat must not wait on isolated-runner inspection."""

    captured: dict[str, object] = {}
    local = H.snapshot()

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(loop_stage, "cache_first_payload", fake_cache_first_payload)

    stage = loop_stage._cached_runner_backed_snapshot(local)

    assert captured == {
        "key": "waste_loop_stage_runner",
        "ttl_seconds": 1.5,
        "block_on_cold": False,
    }
    assert stage["running"] is False
    assert stage["stage"] == "idle"
