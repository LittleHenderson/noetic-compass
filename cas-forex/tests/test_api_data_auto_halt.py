from __future__ import annotations

from api import data as data_module


def test_auto_halt_status_threads_mt5_position_protection_snapshot(monkeypatch):
    seen: dict[str, object] = {}

    monkeypatch.setattr(data_module, "live_broker_account_ledger", lambda: {"mode": "LIVE_ACCOUNT_LEDGER"})
    monkeypatch.setattr(data_module, "account_ledger", lambda: {"mode": "PAPER_DEMO_ACCOUNT_LEDGER"})
    monkeypatch.setattr(
        data_module,
        "latest_broker_truth_reconciliation_report",
        lambda: {"overall_status": "RECONCILED"},
    )

    def _fake_position_protection(force: bool = False):
        seen["force"] = force
        return {"status": "ALL_POSITIONS_PROTECTED", "unprotected_position_count": 0}

    def _fake_build_auto_halt_report(**kwargs):
        seen["kwargs"] = kwargs
        return {"report_kind": "cas_forex_auto_halt", "status": "AUTO_HALT_CLEAR"}

    monkeypatch.setattr(data_module, "get_mt5_position_protection_snapshot", _fake_position_protection)
    monkeypatch.setattr(data_module, "build_auto_halt_report", _fake_build_auto_halt_report)

    report = data_module.auto_halt_status(persist=True)

    assert report["report_kind"] == "cas_forex_auto_halt"
    assert seen["force"] is True
    forwarded = seen["kwargs"]
    assert isinstance(forwarded, dict)
    assert forwarded["position_protection_report"]["status"] == "ALL_POSITIONS_PROTECTED"
    assert forwarded["persist"] is True
