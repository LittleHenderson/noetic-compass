from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from api.routes import assistant
from api.routes import live_telemetry as live_telemetry_route
from cas_forex import ai_operator, broker_truth_monitor
from cas_forex.active_account_truth import build_active_account_truth
from cas_forex.broker_truth_monitor_supervisor import BrokerTruthMonitorSupervisorStore
from cas_forex.config import config as runtime_config
from cas_forex.operator_briefing import compose_operator_briefing
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
_NOW = datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _trusted_mt5_identity(monkeypatch):
    monkeypatch.setattr(runtime_config, "mt5_login", 123)
    monkeypatch.setattr(runtime_config, "mt5_server", "Broker-Live")


def _live_mt5_unprotected_snapshot() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt5_live_account",
        "connected": True,
        "is_demo": False,
        "account": {"login": 123, "server": "Broker-Live"},
        "open_position_count": 1,
        "position_protection": {
            "report_kind": "cas_forex_position_protection_report",
            "status": "UNPROTECTED_POSITIONS",
            "connected": True,
            "open_position_count": 1,
            "protected_position_count": 0,
            "unprotected_position_count": 1,
            "requires_owner_attention": True,
            "detail": "1 broker-visible live position has no stop-loss protection.",
            "unprotected_positions": [
                {
                    "ticket": 22,
                    "symbol": "US30",
                    "side": "LONG",
                    "lots": 0.1,
                    "open_price": 52000.0,
                    "current_price": 52100.0,
                    "stop_loss": None,
                    "take_profit": 53000.0,
                    "floating_pnl_usd": 25.0,
                }
            ],
        },
    }


def _terminal_open_positions_reconciled() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_terminal_position_reconciliation_report",
        "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS",
        "summary": {
            "terminal_open_position_count": 1,
            "unmatched_open_position_count": 0,
            "terminal_unattributed_open_position_count": 0,
            "terminal_memory_gap_open_position_count": 0,
            "cas_memory_only_open_position_count": 0,
            "cas_receipt_pending_open_position_count": 0,
            "pending_receipt_count": 0,
            "receipt_mismatch_count": 0,
            "account_snapshot_present": True,
        },
        "classified_unmatched_open_positions": [],
    }


def _isolated_supervisor_store(tmp_path: Path) -> BrokerTruthMonitorSupervisorStore:
    return BrokerTruthMonitorSupervisorStore(
        tmp_path / "broker-truth-monitor-supervisor.json",
        tmp_path / "broker-truth-monitor-supervisor-audit.jsonl",
        lease_seconds=60,
    )


def _broker_truth_fast_status_from_one_unprotected_live_position(tmp_path: Path, monkeypatch) -> dict[str, Any]:
    activated: dict[str, Any] = {}

    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    monkeypatch.setattr(broker_truth_monitor, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(
        broker_truth_monitor,
        "activate_auto_halt",
        lambda reasons, checks: activated.update({"reasons": list(reasons), "checks": list(checks)}),
    )
    monkeypatch.setattr(
        broker_truth_monitor,
        "emit_critical_notification",
        lambda event, source: {"ok": True, "source": source, "event": event},
    )
    broker_truth_monitor.set_monitor_supervisor_for_tests(
        _isolated_supervisor_store(tmp_path),
        owner_id="cross-surface-owner",
    )
    try:
        report = broker_truth_monitor.run_broker_truth_check(
            mt5_snapshot=_live_mt5_unprotected_snapshot(),
            terminal_reconciliation_report=_terminal_open_positions_reconciled(),
            state_path=tmp_path / "broker-truth.json",
            write_state=True,
            write_report=False,
        )
        status = broker_truth_monitor.monitor_fast_status()
    finally:
        broker_truth_monitor.set_monitor_supervisor_for_tests(None)
        with broker_truth_monitor._lock:  # noqa: SLF001 - isolate monitor singleton after this regression.
            broker_truth_monitor._state.last_report = None  # noqa: SLF001

    assert activated["reasons"] == ["live_position_stop_loss_protection"]
    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["auto_halt_latched_from_monitor"] is True
    assert report["monitor_auto_halt_reason_ids"] == ["live_position_stop_loss_protection"]
    assert status["ready_for_live"] is False
    return status


def test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces(tmp_path, monkeypatch):
    fast_status = _broker_truth_fast_status_from_one_unprotected_live_position(tmp_path, monkeypatch)
    latest_report = fast_status["latest_report"]

    # 1. Broker-truth monitor fast status: the source evidence and compact API agree.
    assert fast_status["monitor_status"] == "BROKER_TRUTH_RECONCILIATION_FAILED"
    assert latest_report["auto_halt_latched_from_monitor"] is True
    assert latest_report["monitor_auto_halt_reason_ids"] == ["live_position_stop_loss_protection"]
    assert latest_report["position_protection_status"] == "UNPROTECTED_POSITIONS"
    assert latest_report["position_protection_unprotected_position_count"] == 1
    assert latest_report["position_protection_detail"] == "1 broker-visible live position has no stop-loss protection."

    # 2. Live gate summary UI contract: the same fields drive the top-line readiness card.
    live_gate_source = (REPO_ROOT / "ui" / "src" / "components" / "LiveReadinessSummaryPanel.tsx").read_text(encoding="utf-8")
    assert "BROKER TRUTH PAPER FORCE" in live_gate_source
    assert "monitor_auto_halt_reason_ids" in live_gate_source
    assert "position_protection_unprotected_position_count" in live_gate_source
    assert "Broker Truth Enforcement" in live_gate_source
    assert "Stop-Loss Protection" in live_gate_source

    # 3. Operator briefing: structured one-call briefing receives and explains the same condition.
    briefing = compose_operator_briefing(
        broker_truth_monitor=fast_status,
        now=_NOW,
    )
    assert briefing.broker_truth_monitor_status == "BROKER_TRUTH_RECONCILIATION_FAILED"
    assert briefing.broker_truth_paper_force_latched is True
    assert briefing.broker_truth_halt_reason_labels == ("Stop-Loss Protection",)
    assert briefing.broker_truth_position_protection_label == "UNPROTECTED POSITIONS"
    assert briefing.broker_truth_unprotected_position_count == 1
    assert "Broker truth monitor is forcing paper mode; reasons: Stop-Loss Protection." in briefing.plain_english_briefing

    briefing_card_source = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBriefingCard.tsx").read_text(encoding="utf-8")
    assert "Broker truth enforcement" in briefing_card_source
    assert "Paper-force is latched by broker truth" in briefing_card_source
    assert "broker_truth_halt_reason_summary" in briefing_card_source
    assert "broker_truth_unprotected_position_count" in briefing_card_source

    # 4. Operator chat: the local answer uses the same compact monitor payload.
    operator_context = {
        "broker_truth_monitor": ai_operator._compact_broker_truth_monitor(fast_status),  # noqa: SLF001
    }
    operator_reply = ai_operator._local_chat_reply(  # noqa: SLF001
        "why is broker truth paper force active?",
        operator_context,
        model_attempted=False,
    )
    assert "Broker truth monitor: status=BROKER_TRUTH_RECONCILIATION_FAILED" in operator_reply
    assert "paper_force_latched=True" in operator_reply
    assert "reasons=Stop-Loss Protection" in operator_reply
    assert "position_protection=UNPROTECTED POSITIONS" in operator_reply
    assert "unprotected_positions=1" in operator_reply

    # 5. Assistant live-state prompt: AI-backed assistant replies receive the same truth block.
    monkeypatch.setattr(
        ai_operator,
        "_operator_briefing_context",
        lambda: {"available": True, **asdict(briefing)},
    )
    assistant_block = assistant._live_state_block()  # noqa: SLF001
    assert "broker truth briefing:" in assistant_block
    assert "status=BROKER_TRUTH_RECONCILIATION_FAILED" in assistant_block
    assert "paper_force_latched=true" in assistant_block
    assert "halt_reasons=Stop-Loss Protection" in assistant_block
    assert "position_protection=UNPROTECTED POSITIONS" in assistant_block
    assert "unprotected_positions=1" in assistant_block
    assert "broker truth protection detail: 1 broker-visible live position has no stop-loss protection." in assistant_block


def test_current_mt5_demo_account_outranks_stale_and_secondary_sources_across_cockpit(monkeypatch):
    observed_at = utc_now().isoformat()
    snapshot = {
        "connected": True,
        "is_demo": True,
        "snapshot_observed_at": observed_at,
        "snapshot_age_seconds": 1.0,
        "snapshot_fresh": True,
        "cached": True,
        "account": {
            "login": 1000694,
            "server": "Hugosway-Demo",
            "currency": "USD",
            "balance_usd": 44757.89,
            "equity_usd": 44555.70,
            "floating_pnl_usd": -202.19,
            "margin_used_usd": 411.75,
            "free_margin_usd": 44143.95,
        },
        "positions": [
            {
                "ticket": 101,
                "symbol": "US30",
                "side": "SHORT",
                "lots": 0.01,
                "open_price": 52925.15,
                "current_price": 53022.72,
                "stop_loss": 53234.75,
                "take_profit": 51000.0,
                "floating_pnl_usd": -97.57,
                "swap_usd": -7.60,
            },
            {
                "ticket": 102,
                "symbol": "NAS100",
                "side": "SHORT",
                "lots": 0.01,
                "open_price": 29173.02,
                "current_price": 29264.39,
                "stop_loss": 29469.0,
                "take_profit": 28500.0,
                "floating_pnl_usd": -91.37,
                "swap_usd": -5.65,
            },
        ],
        "open_position_count": 2,
        "permission_state": {"can_submit_order_send": True},
        "position_protection": {
            "protected_position_count": 2,
            "unprotected_position_count": 0,
        },
        "position_risk": {"risk_cap_breach_count": 2, "risk_cap_pct": 0.1},
    }
    dispatch = {
        "running": True,
        "execution_active": True,
        "execution_lane": "PAPER",
        "last_bridge_class": "MT5Bridge",
    }
    simulator = {
        "account": {"balance_usd": 5000.0, "equity_usd": 5000.0},
        "open_exposure": {"open_position_count": 0},
        "source_health": {"static_simulation_active": True},
    }

    active = build_active_account_truth(
        mt5_snapshot=snapshot,
        dispatch_loop=dispatch,
        simulator_health=simulator,
        demo_learning={
            "status": "MT5_DEMO_LEARNING_BOUND",
            "learning_overall": {"trades": 4, "wins": 1, "losses": 3, "net_pnl": -6.77},
        },
    )
    monkeypatch.setattr(live_telemetry_route, "get_mt5_account_snapshot", lambda: snapshot)
    telemetry = live_telemetry_route.collect_live_telemetry()
    briefing = compose_operator_briefing(live_telemetry=telemetry, now=utc_now())
    operator_objective = ai_operator._active_account_objective_context(  # noqa: SLF001
        live_mt5=snapshot,
        dispatch_loop=dispatch,
        simulator_performance={
            "honest_paper_balance_usd": 5000.0,
            "balance_growth_net_pnl_usd": 0.0,
        },
        demo_learning={
            "status": "MT5_DEMO_LEARNING_BOUND",
            "learning_overall": {"trades": 4, "wins": 1, "losses": 3, "net_pnl": -6.77},
        },
    )

    assert active["authoritative_account_source"] == "mt5_account_snapshot"
    assert active["account"]["login"] == 1000694
    assert active["account"]["balance_usd"] == 44757.89
    assert active["open_exposure"]["open_position_count"] == 2
    assert active["secondary_simulator"]["account"]["balance_usd"] == 5000.0
    assert active["secondary_simulator"]["authoritative_for_active_account"] is False

    assert telemetry["telemetry_source"] == "mt5_demo_account_snapshot"
    assert telemetry["position_feed_label"] == "MT5 DEMO"
    assert telemetry["totals"]["open_position_count"] == 2
    assert telemetry["movement_source_truth"]["account_login"] == 1000694
    assert telemetry["totals"]["gross_floating_pnl"] == -188.94
    assert telemetry["totals"]["total_swap"] == -13.25
    assert telemetry["totals"]["total_open_pnl_after_costs"] == -202.19

    assert briefing.live_telemetry_source == "mt5_demo_account_snapshot"
    assert briefing.live_position_feed_label == "MT5 DEMO"
    assert briefing.open_position_count == 2
    assert briefing.broker_truth_open_position_count == 2
    assert briefing.broker_truth_mt5_connected is True
    assert briefing.broker_truth_mt5_is_demo is True
    assert "2 active MT5 demo broker position(s)" in briefing.plain_english_briefing
    assert "No active MT5 broker positions" not in briefing.plain_english_briefing
    assert briefing.total_floating_pnl == -202.19

    assert operator_objective["status"] == "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
    assert operator_objective["current_account"]["login"] == 1000694
    assert operator_objective["current_account"]["open_position_count"] == 2
    assert operator_objective["growth_measurement"]["open_pnl_decomposition"]["price_pnl_usd"] == -188.94
    assert operator_objective["growth_measurement"]["open_pnl_decomposition"]["swap_or_carry_usd"] == -13.25
    assert operator_objective["secondary_simulator_performance"]["authoritative_for_active_account"] is False
