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


def test_authorization_report_covers_all_five_capabilities():
    report = live_enable_control.build_authorization_report(FakeConfig())
    caps = [c["capability"] for c in report["capabilities"]]
    assert caps == [
        "live_trading",
        "broker_accept",
        "auto_deposit",
        "bank_card_movement",
        "payout_automation",
    ]
    # Every capability carries its own toggles + gate readout.
    for c in report["capabilities"]:
        assert c["toggles"]
        assert "authorized" in c and "missing_requirements" in c


def test_payout_automation_authorizes_via_toggles_and_provider():
    cfg = FakeConfig()
    assert runtime_gates.is_authorized("payout_automation", cfg) is False
    live_enable_control.set_live_enable_overrides(
        owner_enable_payout_automation=True,
        payment_provider="wise",
        payment_api_key="secret-xyz",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    assert runtime_gates.is_authorized("payout_automation", cfg) is True


def test_payment_api_key_is_never_returned_in_report():
    live_enable_control.set_live_enable_overrides(payment_api_key="super-secret-123")
    report = live_enable_control.build_authorization_report(FakeConfig())
    assert "super-secret-123" not in str(report)
    assert report["provider"]["payment_api_key_set"] is True


def test_string_provider_keys_not_coerced_to_bool():
    live_enable_control.set_live_enable_overrides(payment_provider="stripe")
    cfg = live_enable_control.apply_live_enable_overrides(FakeConfig())
    assert cfg.payment_provider == "stripe"
