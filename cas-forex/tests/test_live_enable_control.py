"""Tests for the owner live-enable control: in-app toggles that satisfy the
live-trading runtime gate without editing .env.

The contract: with no overrides set the module is a true no-op (runtime_gates
behaves exactly as before); setting the six flags ON drives
``evaluate_live_trading`` toward AUTHORIZED via the resolved-config wrapper; and
the report always lists exactly what is still missing.
"""

import dataclasses

import pytest

from cas_forex import live_enable_control, runtime_gates


@dataclasses.dataclass
class FakeConfig:
    owner_enable_live_trading: bool = False
    live_trading_licensed: bool = False
    mt5_login: int = 123
    mt5_password: str = "secret"
    mt5_server: str = "Broker-Live"
    live_mode: bool = False
    prefer_mt5: bool = False
    mt5_path: str = ""
    personal_account_ack: bool = False
    no_pooled_capital_ack: bool = False
    account_type: str = "personal"
    selected_broker_id: str = "hugosway"
    broker_name: str = "HUGOSWAY"


@pytest.fixture(autouse=True)
def _clear_overrides():
    live_enable_control.clear_live_enable_overrides()
    yield
    live_enable_control.clear_live_enable_overrides()


def test_no_overrides_is_a_true_noop():
    cfg = FakeConfig()
    # apply_live_enable_overrides returns the same object when nothing is set.
    assert live_enable_control.apply_live_enable_overrides(cfg) is cfg


def test_resolve_reflects_overrides_over_config():
    cfg = FakeConfig(live_mode=False)
    live_enable_control.set_live_enable_overrides(live_mode=True)
    resolved = live_enable_control.resolve_live_enable(cfg)
    assert resolved["live_mode"] is True
    # Untouched flag still reads from config.
    assert resolved["owner_enable_live_trading"] is False


def test_toggles_drive_live_trading_to_authorized():
    cfg = FakeConfig()
    # Creds + broker already present in FakeConfig; the gate is blocked only on
    # the six toggleable flags. Flip them all on.
    assert runtime_gates.is_authorized("live_trading", cfg) is False
    live_enable_control.set_live_enable_overrides(
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        live_mode=True,
        prefer_mt5=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
    )
    assert runtime_gates.is_authorized("live_trading", cfg) is True


def test_partial_toggles_keep_gate_closed_and_report_missing():
    cfg = FakeConfig()
    live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
    report = live_enable_control.build_live_enable_report(cfg)
    assert report["live_authorized"] is False
    assert report["still_missing"]  # names exactly what is left


def test_reset_clears_overrides():
    cfg = FakeConfig()
    live_enable_control.set_live_enable_overrides(live_mode=True)
    assert live_enable_control.resolve_live_enable(cfg)["live_mode"] is True
    live_enable_control.clear_live_enable_overrides()
    assert live_enable_control.resolve_live_enable(cfg)["live_mode"] is False


def test_unknown_flag_rejected():
    with pytest.raises(ValueError):
        live_enable_control.set_live_enable_overrides(not_a_real_flag=True)


def test_report_shape_has_flags_and_caveats():
    report = live_enable_control.build_live_enable_report(FakeConfig())
    keys = {f["key"] for f in report["flags"]}
    assert keys == set(live_enable_control.LIVE_ENABLE_KEYS)
    assert report["caveats"]
    assert report["report_kind"] == "cas_forex_live_enable"
