"""Tests for the owner live-enable control: in-app toggles that satisfy the
live-trading runtime gate without editing .env.

The contract: with no overrides set the module is a true no-op (runtime_gates
behaves exactly as before); setting the six flags ON drives
``evaluate_live_trading`` toward AUTHORIZED via the resolved-config wrapper; and
the report always lists exactly what is still missing.
"""

import dataclasses
import asyncio

import pytest

from cas_forex import broker_reality, broker_truth_monitor, live_enable_control, live_order_dry_run_review, live_pilot, live_recovery, runtime_gates
from api import live_money_cache
from api.routes import live_enable as live_enable_route
from api.routes.live_enable import AuthorizationUpdate


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
def _clear_overrides(tmp_path):
    path = tmp_path / "live-enable-overrides.json"
    live_enable_control.set_live_enable_override_store_for_tests(path)
    live_enable_control.clear_live_enable_overrides()
    yield path
    live_enable_control.clear_live_enable_overrides()
    live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


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


def test_toggles_drive_live_trading_to_authorized(monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)
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
    model = report["owner_authority_model"]
    assert model["authority"] == "OWNER"
    assert model["owner_controls_are_final_authority"] is True
    assert model["metrics_and_ai_can_veto_owner_authority"] is False
    assert "owner switches" in model["authority_controls"]
    assert model["technical_action_time_checks_still_required"] is True


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
    assert report["owner_authority_model"]["authority"] == "OWNER"
    assert report["owner_authority_model"]["metrics_and_ai_can_veto_owner_authority"] is False


def test_authorization_update_accepts_core_live_owner_flags():
    body = AuthorizationUpdate(
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        live_mode=True,
        prefer_mt5=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
    )

    assert body.personal_account_ack is True
    assert body.no_pooled_capital_ack is True
    assert body.live_mode is True
    assert body.prefer_mt5 is True


def test_authorization_route_invalidates_dependent_route_caches(monkeypatch):
    captured: dict[str, object] = {}

    def fake_set_live_enable_overrides(**flags):
        captured["flags"] = flags

    def fake_build_authorization_report():
        return {"report_kind": "cas_forex_authorization", "provider": {"payment_provider": "wise"}}

    def fake_invalidate_live_money_gate_caches(*keys: str):
        captured["invalidated"] = keys

    monkeypatch.setattr(live_enable_route, "set_live_enable_overrides", fake_set_live_enable_overrides)
    monkeypatch.setattr(live_enable_route, "build_authorization_report", fake_build_authorization_report)
    monkeypatch.setattr(live_enable_route, "invalidate_live_money_gate_caches", fake_invalidate_live_money_gate_caches)

    body = AuthorizationUpdate(payment_provider="wise", payout_destination_id="dest-1")
    report = asyncio.run(live_enable_route.post_authorization(body))

    assert report["report_kind"] == "cas_forex_authorization"
    assert captured["flags"] == {"payment_provider": "wise", "payout_destination_id": "dest-1"}
    assert captured["invalidated"] == ()


def test_live_enable_get_routes_are_cache_first_fail_closed(monkeypatch):
    captured: list[dict[str, object]] = []

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.append(
            {
                "key": key,
                "builder": builder.__name__,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(live_enable_route, "cache_first_payload", fake_cache_first_payload)

    state = asyncio.run(live_enable_route.get_live_enable())
    auth = asyncio.run(live_enable_route.get_authorization())

    assert state["report_kind"] == "cas_forex_live_enable"
    assert state["live_authorized"] is False
    assert auth["report_kind"] == "cas_forex_authorization"
    assert auth["all_real_money_authorized"] is False
    assert captured == [
        {
            "key": "live_enable_state_report",
            "builder": "build_live_enable_report",
            "ttl_seconds": 30.0,
            "block_on_cold": False,
        },
        {
            "key": "live_enable_authorization_report",
            "builder": "build_authorization_report",
            "ttl_seconds": 30.0,
            "block_on_cold": False,
        },
    ]


def test_live_money_gate_invalidation_includes_live_enable_cache_keys(monkeypatch):
    captured: dict[str, tuple[str, ...]] = {}

    def fake_invalidate_cache(*keys):
        captured["keys"] = keys

    monkeypatch.setattr(live_money_cache, "invalidate_cache", fake_invalidate_cache)

    live_money_cache.invalidate_live_money_gate_caches()

    assert "live_enable_authorization_report" in captured["keys"]
    assert "live_enable_state_report" in captured["keys"]


def test_default_authorization_report_cache_invalidates_on_owner_update(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("CAS_FOREX_LIVE_ENABLE_REPORT_CACHE_TTL_SECONDS", "60")
    calls = {"count": 0}

    class FakeRuntimeReport:
        all_real_money_authorized = False
        summary = "fake runtime gates"

        @property
        def decisions(self):
            calls["count"] += 1
            return {
                cap: {
                    "capability": cap,
                    "authorized": False,
                    "status": "CURRENTLY NOT LICENSED",
                    "missing_requirements": ["test"],
                    "satisfied_requirements": [],
                    "next_action": "test",
                }
                for cap in runtime_gates.CAPABILITIES
            }

    monkeypatch.setattr(runtime_gates, "build_runtime_gates_report", lambda config=None: FakeRuntimeReport())
    live_enable_control.build_authorization_report()
    live_enable_control.build_authorization_report()
    assert calls["count"] == 1

    live_enable_control.set_live_enable_overrides(payment_provider="wise")
    live_enable_control.build_authorization_report()
    assert calls["count"] == 2


def test_payout_automation_authorizes_via_toggles_and_provider(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
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


def test_authorization_overrides_persist_and_reload_after_restart(_clear_overrides, monkeypatch):
    path = _clear_overrides
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    live_enable_control.set_live_enable_overrides(
        owner_enable_payout_automation=True,
        payment_provider="wise",
        payment_api_key="secret-xyz",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )

    assert path.exists()
    assert "secret-xyz" in path.read_text(encoding="utf-8")

    # Simulate a fresh API process: memory is cleared, then the persisted file
    # reloads into the runtime-gate path.
    live_enable_control.set_live_enable_override_store_for_tests(path)
    report = live_enable_control.build_authorization_report(FakeConfig())

    assert report["provider"]["payment_provider"] == "wise"
    assert report["provider"]["payment_api_key_set"] is True
    assert report["provider"]["payout_destination_id"] == "dest-1"
    assert report["provider"]["payout_destination_allowlisted"] is True
    assert report["override_state_path"] == str(path)
    assert report["persisted"] is True
    assert "secret-xyz" not in str(report)
    assert runtime_gates.is_authorized("payout_automation", FakeConfig()) is True


def test_clear_overrides_removes_persisted_runtime_file(_clear_overrides):
    path = _clear_overrides
    live_enable_control.set_live_enable_overrides(payment_provider="stripe")
    assert path.exists()

    live_enable_control.clear_live_enable_overrides()

    assert not path.exists()
    cfg = FakeConfig()
    assert live_enable_control.apply_live_enable_overrides(cfg) is cfg
    assert live_enable_control.resolve_live_enable(cfg)["live_mode"] is False
