"""Tests for owner broker control — platform selection + paper loosen knobs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.broker_control import (
    PLATFORMS,
    build_broker_control_report,
    clear_broker_control_overrides,
    resolve_broker_control,
    select_bridge,
    set_broker_control_overrides,
)


@pytest.fixture(autouse=True)
def _clear_overrides():
    clear_broker_control_overrides()
    yield
    clear_broker_control_overrides()


def _cfg(**kw) -> SimpleNamespace:
    base = dict(
        broker_platform="auto",
        broker_max_spread_pips=5.0,
        broker_max_slippage_pips=3.0,
        broker_min_lot=0.01,
        broker_max_lot=1.0,
        broker_min_stop_distance_pips=5.0,
        mt5_treat_account_as_demo=False,
        movement_max_usd=None,
        mt5_login=0,
        paper_trading=True,
        live_mode=False,
        mt4_enabled=False,
        mt4_mailbox_dir=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_resolve_defaults_are_strict():
    ctrl = resolve_broker_control(_cfg())
    assert ctrl.platform == "auto"
    assert ctrl.loosened is False
    assert ctrl.max_spread_pips == 5.0


def test_set_overrides_platform_and_tolerances():
    ctrl = set_broker_control_overrides(platform="mt4", max_spread_pips=50.0, min_stop_distance_pips=0.0)
    assert ctrl.platform == "mt4"
    assert ctrl.max_spread_pips == 50.0
    assert ctrl.min_stop_distance_pips == 0.0
    assert ctrl.loosened is True


def test_invalid_platform_rejected():
    with pytest.raises(ValueError):
        set_broker_control_overrides(platform="bogus")


def test_strictness_loose_loosens_both_directions():
    ctrl = set_broker_control_overrides(strictness="loose")
    assert ctrl.strictness == "loose"
    assert ctrl.loosened is True
    assert ctrl.hardened is False
    assert ctrl.min_stop_distance_pips == 0.0
    assert ctrl.max_lot == 100.0


def test_strictness_strict_hardens():
    ctrl = set_broker_control_overrides(strictness="strict")
    assert ctrl.strictness == "strict"
    assert ctrl.hardened is True
    assert ctrl.loosened is False
    assert ctrl.min_stop_distance_pips == 10.0
    assert ctrl.max_lot == 0.5


def test_strictness_from_config():
    assert resolve_broker_control(_cfg(broker_strictness="strict")).strictness == "strict"
    assert resolve_broker_control(_cfg(broker_strictness="loose")).strictness == "loose"


def test_explicit_field_overrides_preset():
    ctrl = set_broker_control_overrides(strictness="loose", max_spread_pips=3.0)
    assert ctrl.max_spread_pips == 3.0  # explicit field wins over the preset
    assert ctrl.min_stop_distance_pips == 0.0  # rest of the loose preset stays


def test_invalid_strictness_rejected():
    with pytest.raises(ValueError):
        set_broker_control_overrides(strictness="bogus")


def test_select_bridge_simulated_applies_loosened_tolerances():
    set_broker_control_overrides(platform="simulated", max_spread_pips=99.0, max_lot=500.0)
    bridge = select_bridge(_cfg())
    assert isinstance(bridge, SimulatedBrokerBridge)
    assert bridge.max_spread_pips == 99.0
    assert bridge.max_lot == 500.0


def test_select_bridge_auto_defaults_to_simulator():
    bridge = select_bridge(_cfg())
    assert isinstance(bridge, SimulatedBrokerBridge)


def test_select_bridge_mt4_falls_back_to_sim_when_mt4_disabled():
    set_broker_control_overrides(platform="mt4")
    bridge = select_bridge(_cfg())
    # MT4 not enabled in config -> mailbox connect fails -> simulator fallback.
    assert isinstance(bridge, SimulatedBrokerBridge)


def test_treat_account_as_demo_reads_from_config():
    ctrl = resolve_broker_control(_cfg(mt5_treat_account_as_demo=True))
    assert ctrl.treat_mt5_account_as_demo is True


def test_real_money_loosen_not_settable_via_overrides():
    # treat_mt5_account_as_demo / movement cap are env-only; the override setter
    # does not accept them.
    with pytest.raises(TypeError):
        set_broker_control_overrides(treat_mt5_account_as_demo=True)


def test_report_lists_platforms_and_env_vars():
    report = build_broker_control_report(_cfg())
    assert set(report["platform_options"]) == set(PLATFORMS)
    assert report["env_vars"]["platform"] == "BROKER_PLATFORM"
    assert report["report_kind"] == "cas_forex_broker_control"
