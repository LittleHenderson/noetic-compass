"""Tests for the owner-controlled paper dispatch loop scheduler.

The loop runs the gated dispatch cycle on a timer in a background thread. These
tests monkeypatch the (heavy, real) cycle with a fast fake so they exercise the
start/stop/status state machine without doing real dispatch work or sleeping for
the full interval.
"""

import time

import pytest

from cas_forex import dispatch_loop


class _FakeReport:
    mode = "PAPER"
    intent_count = 2
    executed_count = 1
    blocked_count = 0
    rejected_count = 1


class _FakeCycle:
    dispatch_report = _FakeReport()


@pytest.fixture(autouse=True)
def _clean_loop(monkeypatch):
    import cas_forex.agent_dispatch as ad

    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", lambda **kw: _FakeCycle())
    monkeypatch.setattr(ad, "write_agent_dispatch_cycle_report", lambda cycle: {})
    dispatch_loop.stop_loop()
    dispatch_loop._state.cycles_run = 0
    dispatch_loop._state.last_summary = ""
    dispatch_loop._state.last_error = ""
    yield
    dispatch_loop.stop_loop()


def _wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_loop_starts_runs_a_cycle_and_stops():
    assert dispatch_loop.loop_status()["running"] is False
    started = dispatch_loop.start_loop(10)
    assert started["running"] is True
    # The loop runs a cycle immediately, before waiting the interval.
    assert _wait_for(lambda: dispatch_loop.loop_status()["cycles_run"] >= 1)
    status = dispatch_loop.loop_status()
    assert "mode=PAPER" in (status["last_summary"] or "")
    assert status["last_error"] is None
    stopped = dispatch_loop.stop_loop()
    assert stopped["running"] is False


def test_start_is_idempotent():
    dispatch_loop.start_loop(15)
    again = dispatch_loop.start_loop(15)
    # Still one running loop (no second thread); interval reflected.
    assert again["running"] is True
    assert again["interval_seconds"] == 15
    dispatch_loop.stop_loop()


def test_interval_is_clamped():
    s = dispatch_loop.start_loop(1)  # below MIN
    assert s["interval_seconds"] == dispatch_loop.MIN_INTERVAL_SECONDS
    dispatch_loop.stop_loop()
    s2 = dispatch_loop.start_loop(99999)  # above MAX
    assert s2["interval_seconds"] == dispatch_loop.MAX_INTERVAL_SECONDS
    dispatch_loop.stop_loop()


def test_one_bad_cycle_does_not_kill_the_loop(monkeypatch):
    import cas_forex.agent_dispatch as ad

    def _boom(**kw):
        raise RuntimeError("simulated cycle failure")

    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _boom)
    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: dispatch_loop.loop_status()["last_error"] is not None)
    # Loop is still running despite the cycle error.
    assert dispatch_loop.loop_status()["running"] is True
    assert "simulated cycle failure" in dispatch_loop.loop_status()["last_error"]
    dispatch_loop.stop_loop()
