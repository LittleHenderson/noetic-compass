from cas_forex.authority_boundary import (
    AUTHORIZED,
    NOT_LICENSED,
    OPEN,
    assert_authority_boundary,
    build_authority_boundary_report,
)


def test_authority_boundary_defaults_pending_owner_enable():
    """With no owner config, every real-money capability is pending owner enable
    (fail-closed) and nothing is reported active."""
    report = build_authority_boundary_report(
        [
            {"lead_id": "index_tsmom_126_d1", "deployment_status": "NOT LICENSED"},
            {"lead_id": "range_scalper_filtered_fx_d1", "deployment_status": "NOT LICENSED"},
        ]
    )

    assert report.live_trading_status == NOT_LICENSED
    assert report.broker_accept_status == NOT_LICENSED
    assert report.auto_deposit_status == NOT_LICENSED
    assert report.debit_card_bank_movement_status == NOT_LICENSED
    assert report.payout_automation_status == NOT_LICENSED
    assert report.trading_edge_status == OPEN
    assert report.can_place_live_orders is False
    assert report.can_create_broker_accept is False
    assert report.can_move_money is False
    assert report.can_automate_payouts is False
    assert report.ledger_deployment_status_counts == {"NOT LICENSED": 2}
    assert "Trading edge remains OPEN" in report.claim_boundary
    # The boundary must list concrete, owner-actionable missing requirements -
    # proving this is a path to authorize, not a permanent ban.
    assert report.blockers
    assert any("owner live-trading switches are ON" in b for b in report.blockers)

    assert_authority_boundary(report)


def test_not_licensed_is_current_status_not_permanent():
    """The pending status is explicitly the current safety status, not 'never'."""
    assert NOT_LICENSED == "CURRENTLY NOT LICENSED"
    assert AUTHORIZED == "AUTHORIZED"


def test_authority_boundary_runtime_lock_reflects_live_gate(monkeypatch):
    from cas_forex import auto_halt, broker_reality, broker_truth_monitor, live_order_dry_run_review, live_pilot, live_recovery
    from cas_forex.config import config

    # Default: live trading not authorized -> runtime lock holds.
    monkeypatch.setattr(config, "owner_enable_live_trading", False)
    locked = build_authority_boundary_report()
    assert locked.live_execution_runtime_locked is True
    assert locked.live_trading_status == NOT_LICENSED

    # Owner fully authorizes live trading -> runtime unlocks and status flips to
    # AUTHORIZED. This proves NOT LICENSED was a current state, not permanent.
    monkeypatch.setattr(config, "owner_enable_live_trading", True)
    monkeypatch.setattr(config, "live_trading_licensed", True)
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "prefer_mt5", True)
    monkeypatch.setattr(config, "mt5_login", 123)
    monkeypatch.setattr(config, "mt5_password", "secret")
    monkeypatch.setattr(config, "mt5_server", "Broker-Live")
    monkeypatch.setattr(config, "personal_account_ack", True)
    monkeypatch.setattr(config, "no_pooled_capital_ack", True)
    monkeypatch.setattr(config, "account_type", "personal")
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)

    unlocked = build_authority_boundary_report()
    assert unlocked.live_execution_runtime_locked is False
    assert unlocked.live_trading_status == AUTHORIZED
    assert unlocked.can_place_live_orders is True
    # assert_authority_boundary checks consistency against the live gates.
    assert_authority_boundary(unlocked)


def test_assert_authority_boundary_rejects_unbacked_active_claim(monkeypatch):
    import dataclasses

    from cas_forex.config import config
    import pytest

    # Force everything pending, then forge a report that claims live trading is
    # active. The consistency check must reject it.
    monkeypatch.setattr(config, "owner_enable_live_trading", False)
    forged = dataclasses.replace(
        build_authority_boundary_report(),
        live_trading_status=AUTHORIZED,
        can_place_live_orders=True,
    )
    with pytest.raises(ValueError):
        assert_authority_boundary(forged)
