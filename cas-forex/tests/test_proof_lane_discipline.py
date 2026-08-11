"""Proof-lane discipline: only the proof may trade while the proof runs.

Every rule here maps to a specific June failure: the scalp lane traded 17+
symbols the proof never sanctioned, at 191 trades/day against a 3/day plan,
with 2,634 stop-less intents the risk gate silently passed.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cas_forex import execution_guard
from cas_forex.execution_guard import ExecutionBlocked
from cas_forex.proof_lane_discipline import (
    MAX_DISPATCHES_PER_UTC_DAY,
    evaluate_proof_lane,
    discipline_enabled,
)


def _armed(tmp_path: Path) -> Path:
    state = tmp_path / "discipline.json"
    state.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    return state


def _proof_intent(**over):
    intent = {
        "symbol": "NAS100",
        "decision_ref": "index-tsmom-126-d1-paper-proof-NAS100-20260811",
        "stop_loss": 28465.49,
    }
    intent.update(over)
    return intent


def test_disarmed_state_admits_everything(tmp_path):
    state = tmp_path / "discipline.json"  # never written -> disabled
    decision = evaluate_proof_lane({"symbol": "EUR/USD", "decision_ref": "waste-dir-x"}, state_path=state)
    assert decision.blocked is False
    assert discipline_enabled(state) is False


def test_armed_fence_blocks_off_plan_symbol(tmp_path):
    decision = evaluate_proof_lane(
        _proof_intent(symbol="EUR/USD"), state_path=_armed(tmp_path)
    )
    assert decision.blocked is True and decision.rule == "symbol_allowlist"


def test_armed_fence_blocks_non_proof_lineage(tmp_path):
    """The June signature: waste-dir-* scalp refs must not touch the bridge."""
    decision = evaluate_proof_lane(
        _proof_intent(decision_ref="waste-dir-20260702-nas100-m1"),
        state_path=_armed(tmp_path),
    )
    assert decision.blocked is True and decision.rule == "strategy_lineage"


def test_armed_fence_blocks_stopless_intent(tmp_path):
    decision = evaluate_proof_lane(
        _proof_intent(stop_loss=None), state_path=_armed(tmp_path)
    )
    assert decision.blocked is True and decision.rule == "no_stop_no_order"


def test_armed_fence_enforces_daily_ceiling_and_blocked_attempts_do_not_consume_it(tmp_path):
    state = _armed(tmp_path)
    for i in range(MAX_DISPATCHES_PER_UTC_DAY):
        assert evaluate_proof_lane(_proof_intent(), state_path=state).blocked is False, i
    fourth = evaluate_proof_lane(_proof_intent(), state_path=state)
    assert fourth.blocked is True and fourth.rule == "daily_dispatch_ceiling"
    # a blocked off-plan attempt must not have consumed capacity either
    (tmp_path / "second").mkdir(exist_ok=True)
    state2 = tmp_path / "second" / "discipline.json"
    state2.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    assert evaluate_proof_lane(_proof_intent(symbol="EUR/USD"), state_path=state2).blocked
    assert evaluate_proof_lane(_proof_intent(), state_path=state2).blocked is False, (
        "a blocked attempt must not consume the daily ceiling"
    )


def test_chokepoint_blocks_before_bridge_when_lane_blocks(monkeypatch):
    """guarded_place_order must consult the lane and never touch the bridge on
    a block - the same contract as the daily-loss pin."""
    from cas_forex import proof_lane_discipline

    calls = []

    class _Bridge:
        def will_execute_real_order(self):
            return False

        def place_order(self, order):
            calls.append(order)
            return SimpleNamespace(accepted=True)

    monkeypatch.setattr(
        execution_guard,
        "require_daily_realized_loss_ready",
        lambda **k: {"block_new_exposure": False},
    )
    monkeypatch.setattr(
        proof_lane_discipline,
        "evaluate_proof_lane",
        lambda intent, **k: proof_lane_discipline.LaneDecision(
            blocked=True, plain_english_reason="lane blocked (test)", rule="test"
        ),
    )
    with pytest.raises(ExecutionBlocked):
        execution_guard.guarded_place_order(
            _Bridge(),
            SimpleNamespace(order_id="x", decision_ref="waste-dir-x", symbol="EUR/USD"),
            config=SimpleNamespace(),
        )
    assert calls == [], "a lane-blocked dispatch must never touch the bridge"
