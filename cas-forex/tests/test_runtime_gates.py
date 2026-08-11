"""Security tests for the owner-controlled, fail-closed runtime gates.

These enforce the core requirement: real-money capabilities (live trading,
broker ACCEPT, auto-deposit, bank/card movement, payout automation) must never
be active without (1) the owner enable flag, (2) credentials, and (3) provider
config. They are authorizable, not permanently locked.
"""

import dataclasses

import pytest

from cas_forex import auto_halt, broker_reality, broker_truth_monitor, live_order_dry_run_review, live_pilot, live_recovery, runtime_gates


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
    payment_provider_environment: str = "live"
    payment_api_key: str = ""
    payment_provider_base_url: str = ""
    payment_provider_account_id: str = ""
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
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
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
    # Missing configured account identity -> denied.
    assert runtime_gates.is_authorized(
        "live_trading", dataclasses.replace(base, mt5_server="")
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


def test_live_trading_allows_terminal_held_password_after_exact_broker_truth(monkeypatch):
    _real_money_prereqs_ready(monkeypatch)
    cfg = dataclasses.replace(_fully_authorized_live(), mt5_password="")

    decision = runtime_gates.evaluate_live_trading(cfg)

    assert decision.authorized is True
    assert (
        "owner-approved MT5 account identity configured (mt5_login + mt5_server)"
        in decision.satisfied_requirements
    )
    assert any("password remains terminal-held" in item for item in decision.advisory_requirements)


def test_stale_broker_truth_blocks_live_dispatch(monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: False)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is False
    assert "continuous broker-truth monitor is fresh and live-connected" in decision.missing_requirements
    assert "continuous broker-truth monitor is fresh and live-connected" not in decision.advisory_requirements


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
    assert "owner delegates live-trading and money-movement authority" in boundary.lower()
    assert "autonomously act inside that delegated envelope" in boundary
    assert "paper-proof day count" in report["advisory_only_inputs"]
    assert "AI conviction score (not win probability) or agent recommendation" in report["advisory_only_inputs"]
    assert "AI confidence" not in " ".join(report["advisory_only_inputs"])
    assert report["owner_controls_are_final_authority"] is True
    assert report["metrics_and_ai_are_advisory_only"] is False
    assert report["metrics_and_ai_can_veto_owner_authority"] is False
    assert report["ai_autonomous_execution_authority"] == "OWNER_DELEGATED_WITHIN_GATES"
    assert report["per_order_confirmation_required"] is False
    assert "broker/feed/provider bridge is reachable for the requested action" in report["action_time_requirements"]


def test_live_trading_requires_risk_denominated_live_authority(monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: False)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is False
    assert "risk-denominated live authority is ACCEPT and available" in decision.missing_requirements


def test_live_trading_requires_recovery_clear(monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: False)

    decision = runtime_gates.evaluate_live_trading(_fully_authorized_live())

    assert decision.authorized is False
    assert "live crash/disconnect recovery review is CLEAR" in decision.missing_requirements


def test_live_trading_requires_owner_accepted_dry_run_review(monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
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
        payment_provider="simulated",
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
    cfg = FakeConfig(
        owner_enable_auto_deposit=True,
        payment_provider="simulated",
        payment_api_key="key",
    )
    assert runtime_gates.is_authorized("auto_deposit", cfg) is True
    bad = dataclasses.replace(cfg, payment_provider="")
    assert runtime_gates.is_authorized("auto_deposit", bad) is False


def test_bank_card_movement_requires_allowlisted_outflow_destination():
    cfg = FakeConfig(
        owner_enable_bank_card_movement=True,
        payment_provider="simulated",
        payment_api_key="key",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    assert runtime_gates.is_authorized("bank_card_movement", cfg) is True
    assert runtime_gates.is_authorized(
        "bank_card_movement", dataclasses.replace(cfg, payout_destination_id="")
    ) is False
    assert runtime_gates.is_authorized(
        "bank_card_movement", dataclasses.replace(cfg, payout_destination_allowlisted=False)
    ) is False


def test_money_movement_rejects_unsupported_provider_labels():
    cfg = FakeConfig(
        owner_enable_payout_automation=True,
        payment_provider="wise",
        payment_api_key="key",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    decision = runtime_gates.evaluate_payout_automation(cfg)
    assert decision.authorized is False
    assert "payment provider is supported by the runtime" in decision.missing_requirements


def test_real_provider_money_movement_requires_master_kill_clear(monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    payout_cfg = FakeConfig(
        owner_enable_payout_automation=True,
        payment_provider="broker_webhook",
        payment_api_key="key",
        payment_provider_base_url="https://funding.example.test",
        payment_provider_account_id="broker-account-1",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    deposit_cfg = FakeConfig(
        owner_enable_auto_deposit=True,
        payment_provider="broker_webhook",
        payment_api_key="key",
        payment_provider_base_url="https://funding.example.test",
        payment_provider_account_id="broker-account-1",
    )

    payout = runtime_gates.evaluate_payout_automation(payout_cfg)
    deposit = runtime_gates.evaluate_auto_deposit(deposit_cfg)

    assert payout.authorized is False
    assert deposit.authorized is False
    assert "master kill switch / auto-halt is CLEAR for real money movement" in payout.missing_requirements
    assert "master kill switch / auto-halt is CLEAR for real money movement" in deposit.missing_requirements


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
        payment_provider="broker_webhook",
        payment_api_key="key",
        payment_provider_base_url="https://funding.example.test",
        payment_provider_account_id="broker-account-1",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    report = runtime_gates.build_runtime_gates_report(cfg)
    assert report.all_real_money_authorized is True


def test_simulated_provider_keeps_all_real_money_authorized_false(monkeypatch):
    _real_money_prereqs_ready(monkeypatch)
    cfg = dataclasses.replace(
        _fully_authorized_live(),
        owner_enable_broker_accept=True,
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        payment_provider="simulated",
        payment_api_key="key",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )
    report = runtime_gates.build_runtime_gates_report(cfg)
    assert report.decisions["payout_automation"]["authorized"] is True
    assert report.all_real_money_authorized is False
    assert report.payment_provider_runtime["status"] == "SIMULATED_ONLY"
