"""Tests for the execution guard -- the chokepoint that finally wires the
pre-execution risk gate into order dispatch.

Covers: config->caps mapping, PASS within caps, REJECT on a cap breach, that a
rejected order never reaches the bridge, and that a live-mode dispatch re-asserts
the owner live-trading authorization before placing anything.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cas_forex.execution_guard import (
    ExecutionBlocked,
    caps_from_config,
    evaluate,
    guard,
    guarded_place_order,
)


def _cfg(*, live_mode: bool = False) -> SimpleNamespace:
    """A minimal config stand-in with the fields caps_from_config reads."""
    return SimpleNamespace(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
    )


class _FakeBridge:
    """Records every place_order call so tests can assert dispatch happened
    (or, on a block, did not)."""

    def __init__(self) -> None:
        self.calls: list = []

    def place_order(self, order):
        self.calls.append(order)
        return {"status": "FILLED", "order": order}


class _Order:
    def __init__(self, symbol: str, direction: str, volume: float) -> None:
        self.symbol = symbol
        self.direction = direction
        self.volume = volume


# ---------------------------------------------------------------------------
# caps_from_config
# ---------------------------------------------------------------------------

def test_caps_from_config_ai_dials_drive_when_owner_has_not_overridden():
    # Owner directive 2026-07-03: with no explicit owner runtime override, the
    # AI operator's dials ARE the enforced caps (dial defaults: 15 open, 3 per
    # symbol, 2.0 total lots) — static config is only the last fallback.
    caps = caps_from_config(_cfg())
    assert caps.max_total_exposure_lots == 2.0
    assert caps.max_open_position_count == 15
    assert caps.max_positions_per_symbol == 3
    assert caps.max_drawdown_pct_from_equity_peak == 5.0
    # Dimensions nothing defines stay uncapped (None), rather than inventing
    # limits the operator never set.
    assert caps.max_concentration_pct is None
    assert caps.max_margin_utilization_pct is None
    assert caps.max_floating_loss_usd is None


def test_caps_from_config_owner_override_beats_ai_dial():
    from cas_forex.risk_control import (
        clear_risk_control_overrides,
        set_risk_control_overrides,
    )

    try:
        set_risk_control_overrides(max_concurrent_trades=7, max_total_exposure_lots=9.0)
        caps = caps_from_config(_cfg())
        assert caps.max_open_position_count == 7
        assert caps.max_total_exposure_lots == 9.0
        # The per-symbol dial still applies, held under the owner's open cap.
        assert caps.max_positions_per_symbol == 3
    finally:
        clear_risk_control_overrides()


def test_caps_from_config_follows_the_ai_dial(tmp_path):
    from cas_forex.ai_control_authority import (
        AiControlAuthority,
        get_authority,
        set_authority_for_tests,
    )

    try:
        set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
        control = get_authority().control
        control.adjust("max_concurrent_trades", 4)
        control.adjust("max_positions_per_symbol", 2)
        control.adjust("max_total_exposure_lots", 0.8)
        caps = caps_from_config(_cfg())
        assert caps.max_open_position_count == 4
        assert caps.max_positions_per_symbol == 2
        assert caps.max_total_exposure_lots == 0.8
    finally:
        set_authority_for_tests(None)


# ---------------------------------------------------------------------------
# evaluate (pure)
# ---------------------------------------------------------------------------

def test_evaluate_passes_within_caps():
    decision = evaluate(
        {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1}, config=_cfg()
    )
    assert decision.accepted
    assert decision.decision == "PASS"


def test_evaluate_rejects_total_exposure_breach():
    # 2.5 lots on an empty book exceeds the 2.0-lot total-exposure dial.
    decision = evaluate(
        {"symbol": "EURUSD", "direction": "BUY", "lots": 2.5}, config=_cfg()
    )
    assert not decision.accepted
    assert "max_total_exposure_lots" in decision.blocking_caps


def test_evaluate_rejects_missing_fields():
    decision = evaluate({"symbol": "EURUSD"}, config=_cfg())
    assert not decision.accepted
    assert "missing_required_fields" in decision.blocking_caps


# ---------------------------------------------------------------------------
# guard (raises)
# ---------------------------------------------------------------------------

def test_guard_raises_on_breach():
    with pytest.raises(ExecutionBlocked) as exc:
        guard({"symbol": "EURUSD", "direction": "BUY", "lots": 2.5}, config=_cfg())
    assert "max_total_exposure_lots" in exc.value.decision.blocking_caps


def test_guard_returns_decision_on_pass():
    decision = guard(
        {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1}, config=_cfg()
    )
    assert decision.accepted


# ---------------------------------------------------------------------------
# guarded_place_order (full chokepoint)
# ---------------------------------------------------------------------------

def test_guarded_place_order_dispatches_on_pass():
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 0.1)
    result = guarded_place_order(bridge, order, config=_cfg())
    assert len(bridge.calls) == 1
    assert result["status"] == "FILLED"


def test_guarded_place_order_blocks_and_does_not_touch_bridge():
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 2.5)  # breaches the total-exposure dial
    with pytest.raises(ExecutionBlocked):
        guarded_place_order(bridge, order, config=_cfg())
    assert bridge.calls == []  # the bridge must never be reached on a block


def test_guarded_place_order_live_mode_requires_authorization():
    # live_mode=True with no owner enable flags / creds -> the live-trading
    # gate is NOT LICENSED, so dispatch must raise before the bridge is hit.
    bridge = _FakeBridge()
    order = _Order("EURUSD", "BUY", 0.1)  # within risk caps; the block is the live gate
    with pytest.raises(PermissionError):
        guarded_place_order(bridge, order, config=_cfg(live_mode=True))
    assert bridge.calls == []
