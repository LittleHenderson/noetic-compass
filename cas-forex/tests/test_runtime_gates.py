"""Security tests for the owner-controlled, fail-closed runtime gates.

These enforce the core requirement: real-money capabilities (live trading,
broker ACCEPT, auto-deposit, bank/card movement, payout automation) must never
be active without (1) the owner enable flag, (2) credentials, and (3) provider
config. They are authorizable, not permanently locked.
"""

import dataclasses

import pytest

from cas_forex import broker_reality, broker_truth_monitor, live_order_dry_run_review, live_pilot, live_recovery, runtime_gates


@dataclasses.dataclass
class FakeConfig:
    owner_enable_live_trading: bool = False
    live_trading_licensed: bool = False
    owner_enable_broker_accept: bool = False
    owner_enable_auto_deposit: bool = False
    owner_enable_bank_card_movement: bool = False
    owner_enable_payout_automation: bool = False
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    live_mode: bool = False
    prefer_mt5: bool = False
    mt5_path: str = ""
    personal_account_ack: bool = False
    no_pooled_capital_ack: bool = False
    account_type: str = "personal"
    selected_broker_id: str = "hugosway"
    broker_name: str = "HUGOSWAY"
    payment_provider: str = ""
    payment_api_key: str = ""
    payout_destination_id: str = ""
    payout_destination_allowlisted: bool = False


def _fully_authorized_live() -> FakeConfig:
    return FakeConfig(
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        mt5_login=123,
        mt5_password="secret",
        mt5_server="Broker-Live",
        live_mode=True,
        prefer_mt5=True,
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        account_type="personal",
    )


def test_default_config_denies_every_real_money_capability():
    cfg = FakeConfig()
    report = runtime_gates.build_runtime_gates_report(cfg)
    assert report.all_real_money_authorized is False
    for cap in runtime_gates.CAPABILITIES:
        dec = runtime_gates.evaluate_capability(cap, cfg)
        assert dec.authorized is False
        assert dec.status == runtime_gates.PENDING_OWNER_ENABLE
        assert dec.missing_requirements  # tells owner exactly what to provide
        assert dec.next_action


def _real_money_prereqs_ready(monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)


def test_live_trading_requires_all_three_pillars(monkeypatch):
    _real_money_prereqs_ready(monkeypatch)
    base = _fully_authorized_live()
    assert runtime_gates.is_authorized("live_trading", base) is True

    # Missing owner flag -> denied.
    assert runtime_gates.is_authorized(
        "live_trading", dataclasses.replace(base, owner_enable_live_trading=False)
    ) is False
    # Missing credentials -> denied.
    assert runtime_gates.is_authorized(
        "live_trading", dataclasses.replace(base, mt5_password="")
    ) is False
    # Missing broker config -> denied.
    assert runtime_gates.is_authorized(
        "live_trading", dataclasses.replace(base, live_mode=False)
    ) is False
    # Missing acknowledgments -> denied.
    assert runtime_gates.is_authorized(
        "live_trading", dataclasses.replace(base, personal_account_ack=False)
    ) is False
    # Pooled account -> denied.
    assert runtime_gates.is_authorized(
        "live_trading", dataclasses.replace(base, account_type="pooled")
    ) is False


def test_broker_truth_freshness_is_advisory_not_owner_veto(monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: False)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is True
    assert "continuous broker-truth monitor is fresh and live-connected" in decision.advisory_requirements
    assert "continuous broker-truth monitor is fresh and live-connected" not in decision.missing_requirements


def test_owner_authority_is_not_vetoed_by_metrics_or_ai_scores(monkeypatch):
    _real_money_prereqs_ready(monkeypatch)
    cfg = _fully_authorized_live()
    # These dynamic fields represent dashboard/proof/AI metrics that may advise
    # the owner, but must not become hidden vetoes over live authority.
    cfg.paper_trading_days = 0
    cfg.multi_symbol_evidence_months = 0
    cfg.ai_confidence_score = 0.0
    cfg.strategy_win_rate = 0.0
    cfg.monthly_profit_pace_usd = -999.0

    decision = runtime_gates.evaluate_live_trading(cfg)
    report = runtime_gates.build_runtime_gates_report(cfg).to_dict()

    assert decision.authorized is True
    assert decision.missing_requirements == ()
    boundary = report["owner_authority_boundary"]
    assert "owner is the live-trading authority" in boundary
    assert "advisory only" in boundary
    assert "paper-proof day count" in report["advisory_only_inputs"]
    assert report["owner_controls_are_final_authority"] is True
    assert report["metrics_and_ai_can_veto_owner_authority"] is False
    assert "broker/feed/provider bridge is reachable for the requested action" in report["action_time_requirements"]


def test_live_trading_requires_small_controlled_pilot(monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: False)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is False
    assert "small-controlled live pilot is ACCEPT and has remaining capacity" in decision.missing_requirements


def test_live_trading_requires_recovery_clear(monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: False)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is False
    assert "live crash/disconnect recovery review is CLEAR" in decision.missing_requirements


def test_live_trading_requires_owner_accepted_dry_run_review(monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: False)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is False
    assert "owner ACCEPTED latest passing live-order dry run against fresh broker truth" in decision.missing_requirements


def test_broker_accept_requires_live_trading_and_flag(monkeypatch):
    _real_money_prereqs_ready(monkeypatch)
    base = _fully_authorized_live()
    # Live authorized but broker-accept flag off -> denied.
    assert runtime_gates.is_authorized("broker_accept", base) is False
    enabled = dataclasses.replace(base, owner_enable_broker_accept=True)
    assert runtime_gates.is_authorized("broker_accept", enabled) is True
    # Flag on but live trading not authorized -> still denied.
    no_live = dataclasses.replace(
        FakeConfig(), owner_enable_broker_accept=True
    )
    assert runtime_gates.is_authorized("broker_accept", no_live) is False


def test_payout_automation_requires_provider_creds_and_allowlist(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    cfg = FakeConfig(
        owner_enable_payout_automation=True,
        payment_provider="wise",
        payment_api_key="key",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    assert runtime_gates.is_authorized("payout_automation", cfg) is True
    # Drop the allowlist -> denied.
    assert runtime_gates.is_authorized(
        "payout_automation", dataclasses.replace(cfg, payout_destination_allowlisted=False)
    ) is False
    # Drop credentials -> denied.
    assert runtime_gates.is_authorized(
        "payout_automation", dataclasses.replace(cfg, payment_api_key="")
    ) is False


def test_money_movement_requires_flag_provider_and_creds():
    for cap, flag in (
        ("auto_deposit", "owner_enable_auto_deposit"),
        ("bank_card_movement", "owner_enable_bank_card_movement"),
    ):
        cfg = FakeConfig(payment_provider="wise", payment_api_key="key")
        setattr(cfg, flag, True)
        assert runtime_gates.is_authorized(cap, cfg) is True
        # No provider -> denied.
        bad = dataclasses.replace(cfg, payment_provider="")
        assert runtime_gates.is_authorized(cap, bad) is False


def test_require_authorized_raises_with_actionable_message():
    with pytest.raises(PermissionError) as exc:
        runtime_gates.require_authorized("payout_automation", FakeConfig())
    msg = str(exc.value)
    assert "CURRENTLY NOT LICENSED" in msg
    assert "Missing:" in msg
    assert "Next:" in msg


def test_full_authorization_reports_all_authorized(monkeypatch):
    _real_money_prereqs_ready(monkeypatch)
    cfg = _fully_authorized_live()
    cfg = dataclasses.replace(
        cfg,
        owner_enable_broker_accept=True,
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        payment_provider="wise",
        payment_api_key="key",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    report = runtime_gates.build_runtime_gates_report(cfg)
    assert report.all_real_money_authorized is True
