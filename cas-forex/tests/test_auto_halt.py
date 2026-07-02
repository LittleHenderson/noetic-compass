from __future__ import annotations

import dataclasses

import pytest

from cas_forex import auto_halt, runtime_gates


def _live_ledger(*, drawdown_pct=0.0, deals=None, realized_pnl=0.0):
    return {
        "mode": "LIVE_ACCOUNT_LEDGER",
        "live_money_authorized": True,
        "summary": {
            "drawdown_pct": drawdown_pct,
            "realized_pnl_usd": realized_pnl,
            "deal_count": len(deals or []),
        },
        "deals": deals or [],
        "cashflow_events": [],
    }


def _paper_ledger(*, realized_pnl=0.0, deal_count=1):
    return {
        "mode": "PAPER_DEMO_ACCOUNT_LEDGER",
        "live_money_authorized": False,
        "summary": {"realized_pnl_usd": realized_pnl, "deal_count": deal_count},
        "deals": [],
        "cashflow_events": [],
    }


@dataclasses.dataclass
class GateConfig:
    owner_enable_live_trading: bool = True
    live_trading_licensed: bool = True
    mt5_login: int = 123
    mt5_password: str = "secret"
    mt5_server: str = "Broker-Live"
    live_mode: bool = True
    prefer_mt5: bool = True
    mt5_path: str = ""
    personal_account_ack: bool = True
    no_pooled_capital_ack: bool = True
    account_type: str = "personal"
    selected_broker_id: str = "hugosway"
    broker_name: str = "HUGOSWAY"


def test_auto_halt_persists_drawdown_trip_and_blocks_runtime_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")

    report = auto_halt.build_auto_halt_report(
        live_account_ledger=_live_ledger(drawdown_pct=12.5),
        settings=auto_halt.AutoHaltSettings(max_account_drawdown_pct=10.0),
        persist=True,
    )

    assert report["status"] == auto_halt.STATUS_ACTIVE
    assert "max_account_drawdown_pct" in report["triggered_checks"]
    assert auto_halt.is_auto_halt_active() is True

    decision = runtime_gates.evaluate_live_trading(GateConfig())
    assert decision.authorized is False
    assert "auto-halt circuit breaker is CLEAR" in decision.missing_requirements


def test_auto_halt_trips_on_consecutive_live_losses(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    deals = [
        {"timestamp": "2026-06-30T10:00:00Z", "net_pnl_usd": 50.0},
        {"timestamp": "2026-06-30T11:00:00Z", "net_pnl_usd": -10.0},
        {"timestamp": "2026-06-30T12:00:00Z", "net_pnl_usd": -20.0},
        {"timestamp": "2026-06-30T13:00:00Z", "net_pnl_usd": -30.0},
    ]

    report = auto_halt.build_auto_halt_report(
        live_account_ledger=_live_ledger(deals=deals, realized_pnl=-10.0),
        settings=auto_halt.AutoHaltSettings(max_consecutive_losses=3),
        persist=True,
    )

    assert report["status"] == auto_halt.STATUS_ACTIVE
    assert "max_consecutive_losses" in report["triggered_checks"]


def test_auto_halt_trips_on_live_vs_paper_divergence(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")

    report = auto_halt.build_auto_halt_report(
        live_account_ledger=_live_ledger(realized_pnl=600.0, deals=[{"timestamp": "2026-06-30T10:00:00Z", "net_pnl_usd": 600.0}]),
        paper_account_ledger=_paper_ledger(realized_pnl=1000.0, deal_count=1),
        settings=auto_halt.AutoHaltSettings(max_live_paper_divergence_pct=25.0),
        persist=True,
    )

    assert report["status"] == auto_halt.STATUS_ACTIVE
    assert "live_vs_paper_divergence_pct" in report["triggered_checks"]


def test_auto_halt_trips_on_broker_truth_reconciliation_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")

    report = auto_halt.build_auto_halt_report(
        live_account_ledger=_live_ledger(realized_pnl=100.0, deals=[{"timestamp": "2026-06-30T10:00:00Z", "net_pnl_usd": 100.0}]),
        paper_account_ledger=_paper_ledger(realized_pnl=100.0, deal_count=1),
        reconciliation_report={"overall_status": "RECONCILIATION_FAILED"},
        persist=True,
    )

    assert report["status"] == auto_halt.STATUS_ACTIVE
    assert "broker_truth_reconciliation" in report["triggered_checks"]


def test_auto_halt_clear_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    auto_halt.activate_auto_halt(["TEST"], [{"check_id": "TEST"}])

    with pytest.raises(ValueError, match="confirm_clear"):
        auto_halt.clear_auto_halt(confirm_clear=False)

    state = auto_halt.clear_auto_halt(confirm_clear=True, reason="TEST_CLEAR")
    assert state["active"] is False
    assert state["force_paper_mode"] is False
    assert auto_halt.is_auto_halt_active() is False
