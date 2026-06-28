"""Broker-synced paper-risk apply coverage."""

from __future__ import annotations

from api.data import PLAN_ID, apply_broker_synced_risk_review


def test_apply_broker_synced_risk_review_appends_once_to_temp_chain(tmp_path):
    first = apply_broker_synced_risk_review(confirm_apply=True, output_dir=tmp_path)

    assert first["report_kind"] == "cas_forex_broker_synced_risk_apply"
    assert first["mode"] == "BROKER_SYNCED_PAPER_RISK_APPLY"
    assert first["sync_to_broker_snapshot"] is True
    assert first["broker_snapshot_initial_investment_usd"] > 0
    assert first["account_equity"] == first["broker_snapshot_initial_investment_usd"]
    assert first["would_append_evidence"] is True
    assert first["evidence_appended"] is True
    assert first["already_applied"] is False
    assert first["append_receipt"]
    assert first["paper_risk_summary"]["review_count"] == 1
    assert first["paper_risk_summary"]["chain_verified"] is True
    assert first["live_money_authorized"] is False
    assert first["payment_movement_authorized"] is False
    assert first["deployment_status"] == "NOT LICENSED"
    assert first["broker_accept_status"] == "NOT LICENSED"
    assert first["payment_transfer_status"] == "NOT LICENSED"
    assert (tmp_path / f"{PLAN_ID}-paper-risk.jsonl").exists()
    assert (tmp_path / f"{PLAN_ID}-paper-risk-status.json").exists()

    second = apply_broker_synced_risk_review(confirm_apply=True, output_dir=tmp_path)

    assert second["evidence_appended"] is False
    assert second["already_applied"] is True
    assert second["append_receipt"] is None
    assert second["paper_risk_summary"]["review_count"] == 1
