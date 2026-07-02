from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import live_recovery as route_module
from cas_forex import live_recovery
from cas_forex.time_utils import utc_now


def _pilot(*, trades: int = 1):
    return {
        "owner_pilot_status": "ACCEPT",
        "live_trade_count": trades,
        "last_live_order_at": utc_now().isoformat() if trades else None,
    }


def _clean_live_truth():
    return {
        "report_kind": "cas_forex_broker_truth_monitor",
        "generated_at": utc_now().isoformat(),
        "overall_status": "RECONCILED",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_open_position_count": 0,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }


def _clean_order_attempts():
    return {
        "report_kind": "cas_forex_order_attempt_audit",
        "attempt_count": 0,
        "real_attempt_count": 0,
        "unresolved_attempt_count": 0,
        "unresolved_real_attempt_count": 0,
        "latest_attempt": None,
        "has_unresolved_real_attempt": False,
    }


def _unresolved_real_order_attempts():
    return {
        "report_kind": "cas_forex_order_attempt_audit",
        "attempt_count": 1,
        "real_attempt_count": 1,
        "unresolved_attempt_count": 1,
        "unresolved_real_attempt_count": 1,
        "has_unresolved_real_attempt": True,
        "latest_attempt": {
            "attempt_id": "attempt-live-crash-1",
            "status": "ATTEMPT_STARTED",
            "mode": "LIVE",
            "is_real_attempt": True,
            "result_finalized": False,
            "order_id": "live-crash-1",
            "decision_ref": "live-crash-ref-1",
        },
    }


def _synthetic_test_like_unresolved_attempts():
    return {
        "report_kind": "cas_forex_order_attempt_audit",
        "attempt_count": 2,
        "real_attempt_count": 2,
        "unresolved_attempt_count": 2,
        "unresolved_real_attempt_count": 2,
        "has_unresolved_real_attempt": True,
        "unresolved_real_attempts": [
            {
                "attempt_id": "order-attempt-fake-1",
                "status": "ATTEMPT_STARTED",
                "mode": "LIVE",
                "bridge_name": "_FakeRealBridge",
                "order_id": "compound-add-1",
                "decision_ref": "compound-add-ref-1",
                "source": "order_dispatch",
                "symbol": "EUR/USD",
                "direction": "LONG",
                "volume": 0.01,
                "is_real_attempt": True,
                "result_finalized": False,
            },
            {
                "attempt_id": "order-attempt-fake-2",
                "status": "ATTEMPT_STARTED",
                "mode": "LIVE",
                "bridge_name": "_FakeRealBridge",
                "order_id": "waste-add-dref-test-1-2",
                "decision_ref": "dref-test-1:compound-add:2",
                "source": "waste_compound_add_handoff",
                "symbol": "EUR/USD",
                "direction": "LONG",
                "volume": 0.01,
                "is_real_attempt": True,
                "result_finalized": False,
            },
        ],
        "latest_attempt": None,
    }


def test_recovery_clear_when_no_prior_live_activity(tmp_path, monkeypatch):
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "recovery.json")
    report = live_recovery.build_live_recovery_report(
        broker_truth_report={},
        live_pilot_policy=_pilot(trades=0),
        order_attempt_status=_clean_order_attempts(),
    )

    assert report["requires_recovery_review"] is False
    assert report["recovery_clear_for_live"] is True
    assert report["recovery_status"] == live_recovery.STATUS_CLEAR


def test_prior_live_activity_requires_fresh_broker_truth(tmp_path, monkeypatch):
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "recovery.json")
    report = live_recovery.build_live_recovery_report(
        broker_truth_report={},
        live_pilot_policy=_pilot(trades=1),
        order_attempt_status=_clean_order_attempts(),
    )

    assert report["requires_recovery_review"] is True
    assert report["recovery_clear_for_live"] is False
    assert "broker_truth_present" in report["missing_requirements"]


def test_accept_recovery_review_for_current_clean_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "recovery.json")
    monkeypatch.setattr(live_recovery, "DEFAULT_AUDIT_PATH", tmp_path / "audit.jsonl")
    truth = _clean_live_truth()
    pilot = _pilot(trades=1)

    accepted = live_recovery.accept_live_recovery_review(
        notes="Owner reviewed fresh live truth after restart.",
        confirm_owner_accept=True,
        broker_truth_report=truth,
        live_pilot_policy=pilot,
        order_attempt_status=_clean_order_attempts(),
    )

    assert accepted["owner_recovery_status"] == live_recovery.STATUS_ACCEPT
    assert accepted["recovery_clear_for_live"] is True
    assert accepted["accepted_fingerprint"] == accepted["current_fingerprint"]
    assert (tmp_path / "audit.jsonl").exists()

    changed = live_recovery.build_live_recovery_report(
        broker_truth_report={**truth, "terminal_unmatched_open_position_count": 1},
        live_pilot_policy=pilot,
        order_attempt_status=_clean_order_attempts(),
    )
    assert changed["recovery_clear_for_live"] is False


def test_unresolved_real_order_attempt_blocks_live_recovery_until_reconciled(tmp_path, monkeypatch):
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "recovery.json")
    truth = _clean_live_truth()
    attempts = _unresolved_real_order_attempts()

    report = live_recovery.build_live_recovery_report(
        broker_truth_report=truth,
        live_pilot_policy=_pilot(trades=0),
        order_attempt_status=attempts,
    )

    assert report["requires_recovery_review"] is True
    assert report["recovery_clear_for_live"] is False
    assert "unresolved_real_order_attempts_clear" in report["missing_requirements"]
    assert report["order_attempt_summary"]["has_unresolved_real_attempt"] is True
    assert report["order_attempt_summary"]["unresolved_real_attempt_count"] == 1
    assert report["order_attempt_summary"]["unknown_unresolved_attempt_count"] == 1
    assert report["order_attempt_summary"]["broker_review_required_unresolved_attempt_count"] == 1

    with pytest.raises(live_recovery.LiveRecoveryError):
        live_recovery.accept_live_recovery_review(
            notes="Owner cannot clear unresolved real order attempt by assertion.",
            confirm_owner_accept=True,
            broker_truth_report=truth,
            live_pilot_policy=_pilot(trades=0),
            order_attempt_status=attempts,
        )


def test_synthetic_test_like_unresolved_attempts_do_not_block_live_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "recovery.json")
    truth = _clean_live_truth()
    attempts = _synthetic_test_like_unresolved_attempts()

    report = live_recovery.build_live_recovery_report(
        broker_truth_report=truth,
        live_pilot_policy=_pilot(trades=0),
        order_attempt_status=attempts,
    )

    assert report["requires_recovery_review"] is False
    assert report["recovery_clear_for_live"] is True
    assert "unresolved_real_order_attempts_clear" not in report["missing_requirements"]
    summary = report["order_attempt_summary"]
    assert summary["unresolved_real_attempt_count"] == 2
    assert summary["synthetic_test_like_unresolved_attempt_count"] == 2
    assert summary["broker_review_required_unresolved_attempt_count"] == 0
    assert summary["has_unresolved_real_attempt"] is False


def test_route_rejects_accept_without_ready_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "recovery.json")
    monkeypatch.setattr(live_recovery, "_order_attempt_status", _clean_order_attempts)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-recovery")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-recovery/accept?confirm_owner_accept=true",
        json={"notes": "trying too early"},
    )

    assert response.status_code == 400
