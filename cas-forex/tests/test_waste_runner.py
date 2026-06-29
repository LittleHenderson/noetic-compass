"""Tests for the WASTE-loop runner — proves it is fail-closed and paper-safe.

The runner ticks ``WasteLoop`` and stamps the live heartbeat per stage. These
tests use fakes (a controllable ``test`` gate via monkeypatch, an injected
``strategize`` and ``dispatch`` sink) to prove the load-bearing invariants:

  * a tick records a heartbeat stage (the indicator pulses with the real stage);
  * a NON-PASS test => NO execution + the tick ends at ``no_trade``;
  * a PASS => ``edge_authorization.authorize`` is called AND dispatch is called;
  * daily-CAP-reached => no candidate => no new trades that day;
  * the runner CANNOT execute without a PASS (fail-closed, by construction).
"""

from __future__ import annotations

import pytest

from cas_forex import edge_authorization, loop_heartbeat, waste_runner
from cas_forex.ai_objective import ProfitObjective
from cas_forex.edge_gate import EdgeTestDecision, mint_token
from cas_forex.waste_loop import CandidateSetup


def _setup() -> CandidateSetup:
    return CandidateSetup(
        symbol="EUR/USD",
        timeframe="H1",
        direction="LONG",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        signal_strength=0.8,
        regime="trend",
        decision_ref="dref-test-1",
    )


def _pass_decision(setup: CandidateSetup) -> EdgeTestDecision:
    """A genuine PASS whose token is a valid HMAC over the gate setup, so
    ``edge_authorization.authorize`` accepts it."""
    from cas_forex.waste_runner import _to_gate_setup

    gate_setup = _to_gate_setup(setup)
    evaluated_at = "2026-06-29T00:00:00+00:00"
    token = mint_token(gate_setup, evaluated_at)
    return EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.72,
        null_p95=0.01,
        threshold=0.65,
        edge_token=token,
        evaluated_at=evaluated_at,
        reason="edge confirmed (test fixture)",
    )


def _no_trade_decision() -> EdgeTestDecision:
    return EdgeTestDecision(
        status="NO_TRADE_NULL_FAILED",
        measured_win_prob=0.40,
        null_p95=0.02,
        threshold=0.65,
        edge_token=None,
        evaluated_at="2026-06-29T00:00:00+00:00",
        reason="did not beat null",
    )


@pytest.fixture(autouse=True)
def _clean_state():
    loop_heartbeat.reset()
    edge_authorization.reset()
    yield
    loop_heartbeat.reset()
    edge_authorization.reset()


# ---------------------------------------------------------------------------
# 1. A tick records a heartbeat stage.
# ---------------------------------------------------------------------------
def test_tick_records_heartbeat_stage():
    runner = waste_runner.WasteRunner(strategize_fn=lambda s, a: None)
    runner.tick_once()
    snap = loop_heartbeat.snapshot()
    # The indicator is live and pulsing with a real stage (default => no_trade).
    assert snap["running"] is True
    assert snap["stage"] in waste_runner.loop_heartbeat.VALID_STAGES
    assert snap["stage"] == "no_trade"


# ---------------------------------------------------------------------------
# 2. A NON-PASS test => NO execution + stage no_trade.
# ---------------------------------------------------------------------------
def test_non_pass_test_means_no_execution(monkeypatch):
    dispatched: list = []
    authorized: list = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs)
        return {"status": "EXECUTED"}

    monkeypatch.setattr(
        edge_authorization, "authorize", lambda *a, **k: authorized.append((a, k))
    )

    runner = waste_runner.WasteRunner(
        strategize_fn=lambda s, a: _setup(),
        dispatch_fn=fake_dispatch,
    )
    # Force the gate to a non-PASS verdict.
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _no_trade_decision()
    )

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []        # the bridge was never touched
    assert authorized == []        # nothing was authorized
    assert loop_heartbeat.snapshot()["stage"] == "no_trade"


# ---------------------------------------------------------------------------
# 3. A PASS => authorize + dispatch are both called.
# ---------------------------------------------------------------------------
def test_pass_authorizes_and_dispatches(monkeypatch):
    dispatched: list = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs)
        return {"status": "EXECUTED", "broker_ticket": 555, "fill_price": 1.1000}

    setup = _setup()
    runner = waste_runner.WasteRunner(
        strategize_fn=lambda s, a: setup,
        dispatch_fn=fake_dispatch,
    )
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _pass_decision(setup)
    )

    result = runner.tick_once()

    assert result["decision"] == "EXECUTE"
    # dispatch was called exactly once, on the PASS branch.
    assert len(dispatched) == 1
    assert dispatched[0]["setup"].decision_ref == "dref-test-1"
    assert isinstance(dispatched[0]["token"], str) and dispatched[0]["token"]
    # The PASS was registered for the dispatch chokepoint to verify (fail-closed twice).
    assert edge_authorization.is_required("dref-test-1") is True
    assert loop_heartbeat.snapshot()["stage"] == "execute"  # tick settled on execute


# ---------------------------------------------------------------------------
# 4. Daily-CAP-reached => no new trades that day.
# ---------------------------------------------------------------------------
def test_daily_cap_reached_blocks_new_trades(monkeypatch):
    dispatched: list = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs)
        return {"status": "EXECUTED"}

    setup = _setup()
    objective = ProfitObjective(daily_max_target=3500.0)
    runner = waste_runner.WasteRunner(
        strategize_fn=lambda s, a: setup,           # would propose a candidate...
        dispatch_fn=fake_dispatch,
        objective=objective,
        today_realized_fn=lambda: 4000.0,           # ...but the cap is already hit.
    )
    # Even a PASS-able gate must not be reached: strategize returns None first.
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _pass_decision(setup)
    )

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []
    assert loop_heartbeat.snapshot()["stage"] == "no_trade"


# ---------------------------------------------------------------------------
# 5. Fail-closed by construction: the runner cannot execute without a PASS even
#    when strategize hands a full candidate and the gate underpowers/refuses.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "status",
    ["NO_TRADE_NULL_FAILED", "NO_TRADE_UNDERPOWERED", "NO_TRADE_INSUFFICIENT_BARS"],
)
def test_cannot_execute_without_pass(monkeypatch, status):
    dispatched: list = []

    setup = _setup()
    runner = waste_runner.WasteRunner(
        strategize_fn=lambda s, a: setup,
        dispatch_fn=lambda **k: dispatched.append(k),
    )
    refused = EdgeTestDecision(
        status=status,
        measured_win_prob=0.0,
        null_p95=0.0,
        threshold=0.65,
        edge_token=None,
        evaluated_at="2026-06-29T00:00:00+00:00",
        reason=status,
    )
    monkeypatch.setattr(waste_runner, "evaluate_candidate", lambda *a, **k: refused)

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []
    assert edge_authorization.is_required("dref-test-1") is False


# ---------------------------------------------------------------------------
# 6. A PASS with an EMPTY token is NOT a license to execute (token is the key).
# ---------------------------------------------------------------------------
def test_pass_with_empty_token_does_not_execute(monkeypatch):
    dispatched: list = []
    setup = _setup()
    runner = waste_runner.WasteRunner(
        strategize_fn=lambda s, a: setup,
        dispatch_fn=lambda **k: dispatched.append(k),
    )
    bad_pass = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.9,
        null_p95=0.0,
        threshold=0.65,
        edge_token="",          # empty token => not a real authorization
        evaluated_at="2026-06-29T00:00:00+00:00",
        reason="malformed PASS",
    )
    monkeypatch.setattr(waste_runner, "evaluate_candidate", lambda *a, **k: bad_pass)

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []
