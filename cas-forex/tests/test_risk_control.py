"""Tests for owner risk control — set any concurrent count / loss cap, or none."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cas_forex.execution_guard import caps_from_config, evaluate
from cas_forex.risk_control import (
    clear_risk_control_overrides,
    resolve_risk_control,
    set_risk_control_overrides,
)


@pytest.fixture(autouse=True)
def _clear():
    clear_risk_control_overrides()
    yield
    clear_risk_control_overrides()


def _cfg(**kw) -> SimpleNamespace:
    base = dict(
        max_open_positions=5,
        max_total_exposure_lots=0.5,
        max_weekly_drawdown_pct=5.0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_resolve_defaults_from_config():
    rc = resolve_risk_control(_cfg())
    assert rc.max_concurrent_trades == 5
    assert rc.max_total_exposure_lots == 0.5
    assert rc.max_drawdown_pct == 5.0
    assert rc.max_loss_cap_usd is None  # no config attr -> no cap


def test_set_cap_then_unlimited():
    set_risk_control_overrides(max_concurrent_trades=50)
    assert resolve_risk_control(_cfg()).max_concurrent_trades == 50
    set_risk_control_overrides(max_concurrent_trades=None)  # unlimited
    assert resolve_risk_control(_cfg()).max_concurrent_trades is None


def test_negative_cap_rejected():
    with pytest.raises(ValueError):
        set_risk_control_overrides(max_loss_cap_usd=-1)


def test_caps_from_config_reflects_overrides():
    set_risk_control_overrides(max_concurrent_trades=42, max_total_exposure_lots=None)
    caps = caps_from_config(_cfg())
    assert caps.max_open_position_count == 42
    assert caps.max_positions_per_symbol == 42
    assert caps.max_total_exposure_lots is None  # unlimited


def test_no_overrides_preserves_prior_behavior():
    # With nothing set, caps mirror the old config-only mapping exactly.
    caps = caps_from_config(_cfg())
    assert caps.max_total_exposure_lots == 0.5
    assert caps.max_open_position_count == 5
    assert caps.max_drawdown_pct_from_equity_peak == 5.0
    assert caps.max_floating_loss_usd is None


def test_unlimited_lets_oversized_order_pass_the_gate():
    # 5 lots on an empty book breaches the default 0.5-lot cap...
    blocked = evaluate({"symbol": "EUR/USD", "direction": "BUY", "lots": 5.0}, config=_cfg())
    assert not blocked.accepted
    assert "max_total_exposure_lots" in blocked.blocking_caps

    # ...but with the owner removing the exposure cap, it passes.
    set_risk_control_overrides(max_total_exposure_lots=None)
    allowed = evaluate({"symbol": "EUR/USD", "direction": "BUY", "lots": 5.0}, config=_cfg())
    assert allowed.accepted


def test_higher_concurrent_cap_allows_more_positions():
    # Default cap is 5 open positions; raising it is reflected immediately.
    set_risk_control_overrides(max_concurrent_trades=100)
    caps = caps_from_config(_cfg())
    assert caps.max_open_position_count == 100
