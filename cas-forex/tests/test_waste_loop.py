"""Tests for the WASTE loop controller (cas_forex/waste_loop.py).

The load-bearing invariant under test is FAIL-CLOSED execution: there is NO code
path that reaches ``execute_fn`` without a fresh PASS decision carrying a non-empty
edge token. These tests use plain fakes for every injected stage so the loop runs
standalone, with no dependency on the other in-flight modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import pytest

from cas_forex.waste_loop import (
    AI_STAGES,
    CandidateSetup,
    CompoundDecision,
    EdgeTestDecision,
    WasteLoop,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
def _setup(direction: str = "LONG") -> CandidateSetup:
    return CandidateSetup(
        symbol="EURUSD",
        timeframe="H1",
        direction=direction,
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        signal_strength=0.7,
        regime="trend",
        decision_ref="dec-123",
    )


def _pass_edge(token: str = "tok-abc") -> EdgeTestDecision:
    return EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.71,
        null_p95=0.55,
        threshold=0.65,
        edge_token=token,
        evaluated_at="2026-06-28T00:00:00+00:00",
        reason="beats null and clears threshold",
    )


def _fail_edge(status: str = "NO_TRADE_NULL_FAILED", token: Optional[str] = None) -> EdgeTestDecision:
    return EdgeTestDecision(
        status=status,
        measured_win_prob=0.52,
        null_p95=0.58,
        threshold=0.65,
        edge_token=token,
        evaluated_at="2026-06-28T00:00:00+00:00",
        reason="did not beat null",
    )


class _Recorder:
    """Records that execute was called and with which token + lots."""

    def __init__(self) -> None:
        self.execute_calls: List[tuple[Any, float, str]] = []

    def execute(self, setup: CandidateSetup, lots: float, token: str) -> dict[str, Any]:
        self.execute_calls.append((setup, lots, token))
        return {"ticket": 42, "token": token}


def _build(
    *,
    strategize_returns: Optional[CandidateSetup],
    test_returns: Any,
    recorder: _Recorder,
    test_raises: bool = False,
    manage_fn: Any = None,
    paper_learning_fn: Any = None,
) -> WasteLoop:
    def watch_fn() -> dict[str, Any]:
        return {"bid": 1.10, "ask": 1.1001}

    def analyze_fn(state: Any) -> dict[str, Any]:
        return {"confidence": 0.8, "regime": "trend", "cell": "ok"}

    def strategize_fn(state: Any, analysis: Any) -> Optional[CandidateSetup]:
        return strategize_returns

    def test_fn(setup: CandidateSetup) -> EdgeTestDecision:
        if test_raises:
            raise RuntimeError("gate exploded")
        return test_returns

    def size_fn(setup: CandidateSetup) -> float:
        return 0.10

    return WasteLoop(
        watch_fn=watch_fn,
        analyze_fn=analyze_fn,
        strategize_fn=strategize_fn,
        test_fn=test_fn,
        size_fn=size_fn,
        execute_fn=recorder.execute,
        manage_fn=manage_fn,
        paper_learning_fn=paper_learning_fn,
    )


# ---------------------------------------------------------------------------
# PASS path
# ---------------------------------------------------------------------------
def test_pass_path_executes_once_with_token():
    rec = _Recorder()
    loop = _build(strategize_returns=_setup(), test_returns=_pass_edge("tok-XYZ"), recorder=rec)

    result = loop.tick()

    assert result["decision"] == "EXECUTE"
    assert result["stage_trace"][0] == "watch"
    assert result["stage_trace"] == ["watch", "analyze", "strategize", "test", "execute"]
    # execute called exactly once, with the gate's token threaded through.
    assert len(rec.execute_calls) == 1
    _, lots, token = rec.execute_calls[0]
    assert token == "tok-XYZ"
    assert lots == 0.10
    assert loop.current_stage() == "execute"


# ---------------------------------------------------------------------------
# Non-PASS: every failing status refuses execution
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "status",
    [
        "NO_TRADE_NULL_FAILED",
        "NO_TRADE_UNDERPOWERED",
        "NO_TRADE_STALE_DATA",
        "NO_TRADE_INSUFFICIENT_BARS",
    ],
)
def test_non_pass_status_never_executes(status):
    rec = _Recorder()
    loop = _build(strategize_returns=_setup(), test_returns=_fail_edge(status), recorder=rec)

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert result["stage_trace"][-1] == "no_trade"
    assert rec.execute_calls == []
    assert loop.current_stage() == "no_trade"


# ---------------------------------------------------------------------------
# THE CRITICAL PROOF: PASS-shaped status but empty / missing token => refused.
# This proves there is no path to execute_fn without a non-empty PASS token.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_token", [None, "", "   ".strip()])
def test_pass_status_with_empty_token_is_refused(bad_token):
    rec = _Recorder()
    # status is the magic word 'PASS' but the token is empty/missing.
    forged = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.99,
        null_p95=0.10,
        threshold=0.65,
        edge_token=bad_token,
        evaluated_at="2026-06-28T00:00:00+00:00",
        reason="looks passing but has no token",
    )
    loop = _build(strategize_returns=_setup(), test_returns=forged, recorder=rec)

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert result["stage_trace"][-1] == "no_trade"
    assert rec.execute_calls == [], "a PASS without a real token must NEVER reach execute_fn"


def test_test_fn_returning_none_is_refused():
    rec = _Recorder()
    loop = _build(strategize_returns=_setup(), test_returns=None, recorder=rec)

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert rec.execute_calls == []


# ---------------------------------------------------------------------------
# strategize None => no_trade, test gate never even runs
# ---------------------------------------------------------------------------
def test_strategize_none_ends_no_trade_without_testing():
    rec = _Recorder()
    test_called = {"hit": False}

    def watch_fn():
        return {}

    def analyze_fn(state):
        return {}

    def strategize_fn(state, analysis):
        return None

    def test_fn(setup):
        test_called["hit"] = True
        return _pass_edge()

    def size_fn(setup):
        return 0.10

    loop = WasteLoop(
        watch_fn=watch_fn,
        analyze_fn=analyze_fn,
        strategize_fn=strategize_fn,
        test_fn=test_fn,
        size_fn=size_fn,
        execute_fn=rec.execute,
    )

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert result["stage_trace"] == ["watch", "analyze", "strategize", "no_trade"]
    assert test_called["hit"] is False, "test gate must not run when there is no setup"
    assert rec.execute_calls == []


# ---------------------------------------------------------------------------
# Injected market_state bypasses watch_fn but still runs the full gate
# ---------------------------------------------------------------------------
def test_injected_market_state_used_and_still_gated():
    rec = _Recorder()
    watch_called = {"hit": False}

    def watch_fn():
        watch_called["hit"] = True
        return {"from": "watch"}

    def analyze_fn(state):
        assert state == {"from": "caller"}  # injected state flows through
        return {}

    def strategize_fn(state, analysis):
        return _setup()

    def test_fn(setup):
        return _fail_edge("NO_TRADE_NULL_FAILED")

    def size_fn(setup):
        return 0.1

    loop = WasteLoop(
        watch_fn=watch_fn,
        analyze_fn=analyze_fn,
        strategize_fn=strategize_fn,
        test_fn=test_fn,
        size_fn=size_fn,
        execute_fn=rec.execute,
    )

    result = loop.tick(market_state={"from": "caller"})

    assert watch_called["hit"] is False
    assert result["decision"] == "NO_TRADE"
    assert rec.execute_calls == []


# ---------------------------------------------------------------------------
# Internal faults => blocked, never execute
# ---------------------------------------------------------------------------
def test_test_fn_raising_ends_blocked_without_execute():
    rec = _Recorder()
    loop = _build(
        strategize_returns=_setup(), test_returns=_pass_edge(), recorder=rec, test_raises=True
    )

    result = loop.tick()

    assert result["decision"] == "BLOCKED"
    assert result["stage_trace"][-1] == "blocked"
    assert rec.execute_calls == []


def test_watch_fn_raising_ends_blocked():
    rec = _Recorder()

    def watch_fn():
        raise RuntimeError("feed down")

    loop = WasteLoop(
        watch_fn=watch_fn,
        analyze_fn=lambda s: {},
        strategize_fn=lambda s, a: _setup(),
        test_fn=lambda x: _pass_edge(),
        size_fn=lambda x: 0.1,
        execute_fn=rec.execute,
    )

    result = loop.tick()

    assert result["decision"] == "BLOCKED"
    assert result["stage_trace"] == ["watch", "blocked"]
    assert rec.execute_calls == []


# ---------------------------------------------------------------------------
# Compound / money-management step runs only after a real execute
# ---------------------------------------------------------------------------
def test_manage_fn_runs_after_execute_and_returns_compound_decision():
    rec = _Recorder()

    def manage_fn(**kwargs):
        # Sees the placed trade context; amplifies a confirmed edge.
        assert kwargs["edge"].status == "PASS"
        return CompoundDecision(action="ADD", add_units=1, reason="breakeven locked, edge fresh")

    loop = _build(
        strategize_returns=_setup(),
        test_returns=_pass_edge("tok-1"),
        recorder=rec,
        manage_fn=manage_fn,
    )

    result = loop.tick()

    assert result["decision"] == "EXECUTE"
    assert isinstance(result["compound"], CompoundDecision)
    assert result["compound"].action == "ADD"
    assert len(rec.execute_calls) == 1


def test_manage_fn_not_called_on_no_trade():
    rec = _Recorder()
    manage_called = {"hit": False}

    def manage_fn(**kwargs):
        manage_called["hit"] = True
        return CompoundDecision(action="HOLD", add_units=0, reason="x")

    loop = _build(
        strategize_returns=_setup(),
        test_returns=_fail_edge("NO_TRADE_UNDERPOWERED"),
        recorder=rec,
        manage_fn=manage_fn,
    )

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert manage_called["hit"] is False
    assert result["compound"] is None


# ---------------------------------------------------------------------------
# Stage vocabulary + UI heartbeat
# ---------------------------------------------------------------------------
def test_every_stage_in_trace_is_a_known_ai_stage():
    rec = _Recorder()
    loop = _build(strategize_returns=_setup(), test_returns=_pass_edge(), recorder=rec)
    result = loop.tick()
    for stage in result["stage_trace"]:
        assert stage in AI_STAGES


def test_initial_stage_is_idle():
    rec = _Recorder()
    loop = _build(strategize_returns=_setup(), test_returns=_pass_edge(), recorder=rec)
    assert loop.current_stage() == "idle"


# ---------------------------------------------------------------------------
# Paper LEARNING mode (owner decision 2026-07-01): on paper, the edge verdict is
# a label, not a blocker. Learning trades carry NO token — real money remains
# structurally impossible for them at the dispatch chokepoint.
# ---------------------------------------------------------------------------
def test_learning_mode_executes_non_pass_candidate_with_empty_token():
    rec = _Recorder()
    loop = _build(
        strategize_returns=_setup(),
        test_returns=_fail_edge(),
        recorder=rec,
        paper_learning_fn=lambda: True,
    )

    result = loop.tick()

    assert result["decision"] == "EXECUTE"
    assert result.get("learning_trade") is True
    # The edge verdict rides along as the training label.
    assert result["edge"].status == "NO_TRADE_NULL_FAILED"
    assert "LEARNING" in result["reason"]
    # Executed exactly once with an EMPTY token — never a fabricated PASS token.
    assert len(rec.execute_calls) == 1
    _, lots, token = rec.execute_calls[0]
    assert token == ""
    assert lots == 0.10
    assert result["stage_trace"][-1] == "execute"


def test_learning_mode_off_keeps_fail_closed_no_trade():
    rec = _Recorder()
    loop = _build(
        strategize_returns=_setup(),
        test_returns=_fail_edge(),
        recorder=rec,
        paper_learning_fn=lambda: False,
    )

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert rec.execute_calls == []


def test_learning_mode_error_reads_as_off_fail_closed():
    rec = _Recorder()

    def broken_gate() -> bool:
        raise RuntimeError("owner control unreadable")

    loop = _build(
        strategize_returns=_setup(),
        test_returns=_fail_edge(),
        recorder=rec,
        paper_learning_fn=broken_gate,
    )

    result = loop.tick()

    assert result["decision"] == "NO_TRADE"
    assert rec.execute_calls == []


def test_learning_mode_does_not_touch_pass_path_token():
    rec = _Recorder()
    loop = _build(
        strategize_returns=_setup(),
        test_returns=_pass_edge("tok-REAL"),
        recorder=rec,
        paper_learning_fn=lambda: True,
    )

    result = loop.tick()

    # A genuine PASS still executes through the token path, not the learning path.
    assert result["decision"] == "EXECUTE"
    assert result.get("learning_trade") is None
    assert rec.execute_calls[0][2] == "tok-REAL"


def test_learning_mode_never_invents_a_candidate():
    rec = _Recorder()
    loop = _build(
        strategize_returns=None,
        test_returns=_fail_edge(),
        recorder=rec,
        paper_learning_fn=lambda: True,
    )

    result = loop.tick()

    # No candidate => still NO_TRADE. Learning mode only unblocks execution of a
    # REAL candidate; it never fabricates one.
    assert result["decision"] == "NO_TRADE"
    assert rec.execute_calls == []
