"""The WASTE-loop heartbeat: honest OFFLINE when idle, LIVE only on a fresh tick."""

from __future__ import annotations

import pytest

from cas_forex import loop_heartbeat as H


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
