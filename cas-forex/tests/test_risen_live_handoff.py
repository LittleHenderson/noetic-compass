from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from cas_forex import risen_live_handoff


REPO_ROOT = Path(__file__).resolve().parents[1]


def _truth(*, exact=True, reconciled=True):
    return {
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_account": 101321 if exact else 1000694,
        "mt5_account_server": "Risen-Trade" if exact else "Hugosway-Demo",
        "mt5_expected_account": 101321,
        "mt5_expected_server": "Risen-Trade",
        "mt5_account_identity_matches_config": exact,
        "overall_status": "RECONCILED" if reconciled else "RECONCILIATION_FAILED",
    }


def _patch_downstream(monkeypatch, *, broker_clear=True, recovery_clear=True):
    monkeypatch.setattr(
        risen_live_handoff,
        "monitor_status",
        lambda: {"running": False, "ready_for_live": broker_clear},
    )
    monkeypatch.setattr(
        risen_live_handoff,
        "build_broker_truth_recovery_packet",
        lambda **kwargs: {
            "broker_truth_clear_for_live_recovery": broker_clear,
            "next_action": "resolve broker truth",
        },
    )
    monkeypatch.setattr(
        risen_live_handoff,
        "build_live_recovery_report",
        lambda **kwargs: {
            "recovery_clear_for_live": recovery_clear,
            "requires_recovery_review": False,
            "evidence_ready_for_owner_accept": recovery_clear,
            "next_action": "resolve recovery",
        },
    )
    monkeypatch.setattr(
        risen_live_handoff,
        "build_broker_reality_review",
        lambda: {"review_status": "OPEN", "next_action": "accept broker terms"},
    )
    monkeypatch.setattr(
        risen_live_handoff,
        "build_live_order_dry_run_review",
        lambda **kwargs: {
            "dry_run_review_clear_for_live": False,
            "next_action": "run dry run",
        },
    )
    monkeypatch.setattr(
        risen_live_handoff,
        "build_runtime_gates_report",
        lambda: SimpleNamespace(
            to_dict=lambda: {"decisions": {"live_trading": {"authorized": False}}}
        ),
    )


def test_wrong_account_never_starts_monitor_or_applies_recovery(monkeypatch):
    monkeypatch.setattr(
        risen_live_handoff,
        "run_broker_truth_check",
        lambda **kwargs: _truth(exact=False),
    )
    started = []
    monkeypatch.setattr(
        risen_live_handoff,
        "start_broker_truth_monitor_worker",
        lambda **kwargs: started.append(kwargs),
    )

    report = risen_live_handoff.run_risen_live_handoff()

    assert report["status"] == risen_live_handoff.STATUS_WAITING_ACCOUNT
    assert report["exact_live_account"] is False
    assert report["broker_touched"] is False
    assert report["order_attempted"] is False
    assert started == []


def test_exact_account_starts_monitor_but_dirty_truth_cannot_clear_recovery(monkeypatch):
    monkeypatch.setattr(
        risen_live_handoff,
        "run_broker_truth_check",
        lambda **kwargs: _truth(exact=True, reconciled=False),
    )
    _patch_downstream(monkeypatch, broker_clear=False, recovery_clear=False)
    monkeypatch.setattr(
        risen_live_handoff,
        "start_broker_truth_monitor_worker",
        lambda **kwargs: {"running": True, "status": "RUNNING"},
    )
    monkeypatch.setattr(risen_live_handoff, "is_auto_halt_active", lambda: True)
    clear_calls = []
    monkeypatch.setattr(
        risen_live_handoff,
        "clear_auto_halt",
        lambda **kwargs: clear_calls.append(kwargs),
    )

    report = risen_live_handoff.run_risen_live_handoff()

    assert report["status"] == risen_live_handoff.STATUS_RECONCILIATION_BLOCKED
    assert report["monitor_worker"]["running"] is True
    assert clear_calls == []
    assert report["recovery_actions"] == []


def test_clean_truth_applies_standing_recovery_but_never_accepts_broker_terms(monkeypatch):
    monkeypatch.setattr(
        risen_live_handoff,
        "run_broker_truth_check",
        lambda **kwargs: _truth(exact=True, reconciled=True),
    )
    _patch_downstream(monkeypatch, broker_clear=True, recovery_clear=True)
    monkeypatch.setattr(
        risen_live_handoff,
        "start_broker_truth_monitor_worker",
        lambda **kwargs: {"running": True, "status": "RUNNING"},
    )
    monkeypatch.setattr(risen_live_handoff, "is_auto_halt_active", lambda: True)
    monkeypatch.setattr(
        risen_live_handoff,
        "clear_auto_halt",
        lambda **kwargs: {"active": False, "cleared_at": "now"},
    )

    report = risen_live_handoff.run_risen_live_handoff()

    assert report["status"] == risen_live_handoff.STATUS_OWNER_GATES_OPEN
    assert report["recovery_actions"] == [
        {"action": "auto_halt_clear", "applied": True, "cleared_at": "now"}
    ]
    assert report["broker_review"]["review_status"] == "OPEN"
    assert "accept broker terms" in report["next_actions"]
    assert report["broker_touched"] is False
    assert report["money_moved"] is False


def test_handoff_script_is_directly_runnable_from_repo_root():
    completed = subprocess.run(
        [sys.executable, "scripts/run_risen_live_handoff.py", "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Verify the configured Risen live account" in completed.stdout
