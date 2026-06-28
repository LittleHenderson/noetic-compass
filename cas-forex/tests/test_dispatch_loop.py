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

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", lambda **kw: _FakeCycle())
    monkeypatch.setattr(ad, "write_agent_dispatch_cycle_report", lambda cycle: {})
    dispatch_loop.stop_loop()
    dispatch_loop._state.cycles_run = 0
    dispatch_loop._state.cycles_idle = 0
    dispatch_loop._state.symbols = []
    dispatch_loop._state.sessions = []
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
    s = dispatch_loop.start_loop(0)  # below MIN -> clamped up to MIN (1)
    assert s["interval_seconds"] == dispatch_loop.MIN_INTERVAL_SECONDS
    dispatch_loop.stop_loop()
    s2 = dispatch_loop.start_loop(9_999_999)  # above MAX -> clamped down to MAX
    assert s2["interval_seconds"] == dispatch_loop.MAX_INTERVAL_SECONDS
    dispatch_loop.stop_loop()


def test_owner_can_set_sub_60s_interval():
    # The owner drives: anything from 1s up is honored, including below the old 60s/10s floors.
    for want in (1, 3, 5, 30):
        s = dispatch_loop.start_loop(want)
        assert s["interval_seconds"] == want
        dispatch_loop.stop_loop()


def test_interval_change_while_running_is_applied_live():
    dispatch_loop.start_loop(45)
    assert dispatch_loop.loop_status()["interval_seconds"] == 45
    # Re-calling start while running updates the interval without spawning a 2nd loop.
    again = dispatch_loop.start_loop(3)
    assert again["running"] is True
    assert again["interval_seconds"] == 3
    dispatch_loop.stop_loop()


def test_active_sessions_by_hour():
    import datetime as _dt

    def at(h):
        return _dt.datetime(2026, 6, 24, h, 0, tzinfo=_dt.timezone.utc)

    assert dispatch_loop.active_sessions(at(3)) == {"Asian"}
    assert dispatch_loop.active_sessions(at(9)) == {"London"}
    assert dispatch_loop.active_sessions(at(14)) == {"London", "New York"}  # overlap
    assert dispatch_loop.active_sessions(at(18)) == {"New York"}
    assert dispatch_loop.active_sessions(at(23)) == {"Asian"}


def test_symbol_targeting_filters_dispatched_intents(monkeypatch):
    import cas_forex.agent_dispatch as ad

    class _I:
        def __init__(self, symbol):
            self.symbol = symbol

    captured = {}

    def _capture_cycle(**kw):
        captured["intents"] = list(kw.get("intents") or [])
        return _FakeCycle()

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [_I("EUR/USD"), _I("US30"), _I("NAS100")])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _capture_cycle)

    dispatch_loop.start_loop(10, symbols=["US30"])
    assert _wait_for(lambda: "intents" in captured)
    assert [i.symbol for i in captured["intents"]] == ["US30"]
    dispatch_loop.stop_loop()


def test_session_targeting_idles_outside_target_sessions(monkeypatch):
    import cas_forex.agent_dispatch as ad

    called = {"dispatch": 0}

    def _count(**kw):
        called["dispatch"] += 1
        return _FakeCycle()

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _count)
    # Pretend it's the Asian session, but the owner targets London only.
    monkeypatch.setattr(dispatch_loop, "active_sessions", lambda now=None: {"Asian"})

    dispatch_loop.start_loop(10, sessions=["London"])
    assert _wait_for(lambda: dispatch_loop.loop_status()["cycles_idle"] >= 1)
    assert called["dispatch"] == 0  # never dispatched off-session
    assert "idle — outside target sessions" in (dispatch_loop.loop_status()["last_summary"] or "")
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
