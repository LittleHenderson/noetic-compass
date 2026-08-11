"""Pure tests for cas_forex.operator_briefing.compose_operator_briefing.

The composer must:
* Never fabricate counts/timestamps when inputs are missing.
* Always produce a plain-English briefing that is OBSERVATIONAL — never
  advisory. The 7 forbidden phrases below are explicitly checked.
* Cap diagnostic hints at 5, merging loop-health hints with readiness
  hints in that order.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import pytest

from cas_forex.operator_briefing import (
    OperatorBriefing,
    compose_operator_briefing,
    refresh_operator_briefing_live_telemetry,
)


_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


FORBIDDEN_PHRASES = (
    "buy now",
    "should you trade",
    "good entry",
    "place a trade",
    "what should i do",
    "you should sell",
    "now is the time",
)


def _full_loop_health() -> dict[str, Any]:
    return {
        "overall_status": "running",
        "last_cycle_at_iso": "2026-06-24T11:55:00+00:00",
        "seconds_since_last_cycle": 300.0,
        "cycles_today": 3,
        "decisions_today": 5,
        "executions_today": 2,
        "blocked_today": 1,
        "autowake_present": True,
        "autowake_next_due_iso": "2026-06-24T13:00:00+00:00",
        "plain_english_summary": "Loop is running.",
        "diagnostic_hints": ["Loop hint A", "Loop hint B"],
    }


def _full_latest_decision() -> dict[str, Any]:
    return {
        "cycle_id": "cycle-abc-123",
        "overall_status": "executed",
        "plain_english_summary": (
            "In cycle cycle-abc-123, the agent chose strategy ff_default and the "
            "intent was executed on the paper terminal."
        ),
        "chain": (),
        "next_action_hint": None,
    }


def _full_live_telemetry() -> dict[str, Any]:
    return {
        "as_of_iso": _NOW.isoformat(),
        "open_positions": [
            {"symbol": "EURUSD", "floating_pnl": 12.50},
            {"symbol": "USDJPY", "floating_pnl": -3.25},
        ],
        "totals": {"open_position_count": 2, "total_floating_pnl": 9.25},
        "data_freshness": {
            "source": "movement_stream",
            "stale": False,
            "last_update_iso": _NOW.isoformat(),
            "movement_source": {
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
            },
        },
    }


def _current_mt5_demo_telemetry() -> dict[str, Any]:
    return {
        "as_of_iso": "2026-07-11T10:00:02+00:00",
        "open_positions": [
            {
                "symbol": "US30",
                "floating_pnl": -97.57,
                "broker_ticket": "101",
                "position_source_label": "MT5_DEMO_BROKER",
                "price_source": "mt5_demo_account_snapshot",
            },
            {
                "symbol": "NAS100",
                "floating_pnl": -91.37,
                "broker_ticket": "102",
                "position_source_label": "MT5_DEMO_BROKER",
                "price_source": "mt5_demo_account_snapshot",
            },
        ],
        "totals": {"open_position_count": 2, "total_floating_pnl": -188.94},
        "telemetry_source": "mt5_demo_account_snapshot",
        "position_feed_label": "MT5 DEMO",
        "position_feed_detail": "Current MT5 demo broker positions.",
        "position_protection": {
            "status": "ALL_POSITIONS_PROTECTED",
            "open_position_count": 2,
            "protected_position_count": 2,
            "unprotected_position_count": 0,
            "detail": "Every open position has a broker-side stop loss.",
        },
        "movement_source_truth": {
            "telemetry_source": "mt5_demo_account_snapshot",
            "position_feed_label": "MT5 DEMO",
            "position_feed_detail": "Current MT5 demo broker positions.",
            "account_mode": "DEMO",
            "account_login": 1000694,
        },
        "data_freshness": {
            "source": "mt5_demo_account_snapshot",
            "stale": False,
            "last_update_iso": "2026-07-11T10:00:00+00:00",
            "account_mode": "DEMO",
        },
    }


def _full_mt5_probe() -> dict[str, Any]:
    return {
        "summary": {
            "terminal_connected": True,
            "broker_api_verified": True,
        },
    }


def _full_readiness() -> dict[str, Any]:
    return {
        "checks_total": 12,
        "checks_passed": 7,
        "next_actions": ["Readiness action X", "Readiness action Y"],
        "checks": [],
    }


def _blocked_public_launch_gate() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_public_launch_gate",
        "launch_gate_status": "BLOCK_PUBLIC_LAUNCH",
        "public_launch_status": "BLOCKED",
        "live_money_production_status": "BLOCKED",
        "pass_count": 4,
        "block_count": 4,
        "hard_blockers": [
            "Counsel legal review is missing or incomplete; draft disclosures are not public-launch approval.",
            "External uptime/error tracking/off-screen alert destinations are not fully configured.",
        ],
        "gates": [],
    }


def _broker_truth_monitor_paper_force() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status_fast",
        "status": "RUNNING",
        "running": True,
        "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
        "ready_for_live": False,
        "latest_report": {
            "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
            "overall_status": "RECONCILIATION_FAILED",
            "mt5_connected": True,
            "mt5_is_demo": False,
            "mt5_open_position_count": 2,
            "auto_halt_latched_from_monitor": True,
            "monitor_auto_halt_reason_ids": [
                "live_position_stop_loss_protection",
                "terminal_position_reconciliation",
            ],
            "position_protection_status": "UNPROTECTED_POSITIONS",
            "position_protection_open_position_count": 2,
            "position_protection_unprotected_position_count": 2,
            "position_protection_requires_owner_attention": True,
            "position_protection_detail": "2 broker-visible live positions have no stop-loss protection.",
            "next_action": "Keep paper force active until broker truth clears.",
        },
    }


# ---------------------------------------------------------------------------
# 1. All inputs None
# ---------------------------------------------------------------------------


def test_all_inputs_none_yields_unknown_briefing():
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert isinstance(briefing, OperatorBriefing)
    assert briefing.loop_health_status == "unknown"
    assert briefing.cycles_today == 0
    assert briefing.decisions_today == 0
    assert briefing.executions_today == 0
    assert briefing.blocked_today == 0
    assert briefing.latest_decision_summary is None
    assert briefing.latest_decision_cycle_id is None
    assert briefing.latest_decision_overall_status is None
    assert briefing.open_position_count == 0
    assert briefing.total_floating_pnl == 0.0
    assert briefing.live_telemetry_source == "none"
    assert briefing.live_telemetry_stale is True
    assert briefing.live_telemetry_last_update_iso is None
    assert briefing.live_price_source_status is None
    assert briefing.live_position_feed_label == "NONE"
    assert briefing.live_movement_source_truth is not None
    assert briefing.live_movement_source_truth["movement_stream_present"] is False
    assert briefing.live_movement_source_truth["position_feed_label"] == "NONE"
    assert "No broker or paper/demo movement snapshot" in briefing.live_position_feed_detail
    assert briefing.mt5_terminal_connected is False
    assert briefing.mt5_broker_api_verified is False
    assert briefing.readiness_gates_open == 0
    assert briefing.readiness_gates_total == 0
    assert briefing.public_launch_gate_status == "unknown"
    assert briefing.public_launch_status == "unknown"
    assert briefing.live_money_production_status == "unknown"
    assert briefing.public_launch_gate_block_count == 0
    assert briefing.public_launch_gate_blockers == ()
    assert briefing.broker_truth_monitor_status == "unavailable"
    assert briefing.broker_truth_ready_for_live is False
    assert briefing.broker_truth_paper_force_latched is False
    assert briefing.broker_truth_halt_reason_ids == ()
    assert briefing.broker_truth_halt_reason_summary == "none"
    assert briefing.broker_truth_position_protection_label == "PROTECTION UNAVAILABLE"
    assert briefing.broker_truth_unprotected_position_count == 0
    assert briefing.broker_truth_position_protection_detail is None
    assert briefing.autowake_present is False
    assert briefing.autowake_next_due_iso is None
    assert briefing.diagnostic_hints == ()
    # Plain English mentions unknown loop and missing decision.
    text = briefing.plain_english_briefing.lower()
    assert "unknown" in text
    assert "no recent agent decision" in text
    assert "no active positions" in text


# ---------------------------------------------------------------------------
# 2. Full happy-path
# ---------------------------------------------------------------------------


def test_full_happy_path_populates_all_fields():
    briefing = compose_operator_briefing(
        loop_health=_full_loop_health(),
        latest_decision=_full_latest_decision(),
        live_telemetry=_full_live_telemetry(),
        mt5_probe=_full_mt5_probe(),
        readiness=_full_readiness(),
        public_launch_gate=_blocked_public_launch_gate(),
        broker_truth_monitor=_broker_truth_monitor_paper_force(),
        now=_NOW,
    )
    assert briefing.generated_at_iso == _NOW.isoformat()
    assert briefing.loop_health_status == "running"
    assert briefing.cycles_today == 3
    assert briefing.decisions_today == 5
    assert briefing.executions_today == 2
    assert briefing.blocked_today == 1
    assert briefing.latest_decision_cycle_id == "cycle-abc-123"
    assert briefing.latest_decision_overall_status == "executed"
    assert briefing.open_position_count == 2
    assert briefing.total_floating_pnl == pytest.approx(9.25)
    assert briefing.live_telemetry_source == "movement_stream"
    assert briefing.live_telemetry_stale is False
    assert briefing.live_telemetry_last_update_iso == _NOW.isoformat()
    assert briefing.live_price_source_status == "STATIC_SIMULATION_FALLBACK"
    assert briefing.live_position_feed_label == "SIM PROOF"
    assert briefing.live_movement_source_truth is not None
    assert briefing.live_movement_source_truth["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert briefing.live_movement_source_truth["position_feed_label"] == "SIM PROOF"
    assert briefing.live_movement_source_truth["open_position_count"] == 2
    assert "not live MT5 terminal positions" in briefing.live_position_feed_detail
    assert briefing.mt5_terminal_connected is True
    assert briefing.mt5_broker_api_verified is True
    assert briefing.readiness_gates_open == 7
    assert briefing.readiness_gates_total == 12
    assert briefing.public_launch_gate_status == "BLOCK_PUBLIC_LAUNCH"
    assert briefing.public_launch_status == "BLOCKED"
    assert briefing.live_money_production_status == "BLOCKED"
    assert briefing.public_launch_gate_pass_count == 4
    assert briefing.public_launch_gate_block_count == 4
    assert briefing.broker_truth_monitor_status == "BROKER_TRUTH_RECONCILIATION_FAILED"
    assert briefing.broker_truth_ready_for_live is False
    assert briefing.broker_truth_paper_force_latched is True
    assert briefing.broker_truth_halt_reason_ids == (
        "live_position_stop_loss_protection",
        "terminal_position_reconciliation",
    )
    assert briefing.broker_truth_halt_reason_labels == (
        "Stop-Loss Protection",
        "Terminal Reconciliation",
    )
    assert briefing.broker_truth_halt_reason_summary == "Stop-Loss Protection, Terminal Reconciliation"
    assert briefing.broker_truth_position_protection_label == "UNPROTECTED POSITIONS"
    assert briefing.broker_truth_unprotected_position_count == 2
    assert briefing.broker_truth_position_protection_detail == "2 broker-visible live positions have no stop-loss protection."
    assert "Broker truth monitor is forcing paper mode" in briefing.plain_english_briefing
    assert "Stop-Loss Protection" in briefing.plain_english_briefing
    assert briefing.autowake_present is True
    assert briefing.autowake_next_due_iso == "2026-06-24T13:00:00+00:00"


def test_live_telemetry_prefers_top_level_movement_source_truth_when_nested_summary_is_partial():
    detail = (
        "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
        "Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry "
        "until usable provider or MT5 quotes arrive."
    )
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry={
            "as_of_iso": _NOW.isoformat(),
            "open_positions": [
                {
                    "symbol": "NAS100",
                    "floating_pnl": 0.0,
                    "position_source_label": "PAPER_SIM_STATIC",
                    "price_source": "paper_route_snapshot:static_simulation",
                    "price_stale": True,
                }
            ],
            "totals": {"open_position_count": 1, "total_floating_pnl": 0.0},
            "position_feed_label": "SIM PROOF",
            "position_feed_detail": detail,
            "movement_source_truth": {
                "movement_stream_present": True,
                "telemetry_source": "movement_stream",
                "telemetry_stale": False,
                "telemetry_last_update_iso": _NOW.isoformat(),
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "price_source_label": "STATIC SIM",
                "price_source_summary": "Static simulation only.",
                "position_feed_label": "SIM PROOF",
                "position_feed_detail": detail,
                "static_simulation_active": True,
                "open_position_count": 1,
                "static_position_count": 1,
                "static_quote_count": 1,
                "closed_market_symbols": ["NAS100"],
                "closed_market_quote_count": 1,
                "unsupported_provider_symbols": ["NAS100"],
                "detail": detail,
                "local_detail": detail,
            },
            "data_freshness": {
                "source": "movement_stream",
                "stale": False,
                "last_update_iso": _NOW.isoformat(),
                "movement_source": {
                    "price_source_status": "STATIC_SIMULATION_FALLBACK",
                },
            },
        },
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert briefing.live_movement_source_truth is not None
    assert briefing.live_movement_source_truth["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert briefing.live_movement_source_truth["static_quote_count"] == 1
    assert briefing.live_movement_source_truth["closed_market_symbols"] == ["NAS100"]
    assert briefing.live_movement_source_truth["unsupported_provider_symbols"] == ["NAS100"]
    assert briefing.live_movement_source_truth["detail"] == detail


# ---------------------------------------------------------------------------
# 3. Loop health "running" + 3 cycles + 5 decisions reflected
# ---------------------------------------------------------------------------


def test_loop_health_counts_reflected_in_briefing():
    briefing = compose_operator_briefing(
        loop_health=_full_loop_health(),
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert briefing.loop_health_status == "running"
    assert briefing.cycles_today == 3
    assert briefing.decisions_today == 5
    assert "running" in briefing.plain_english_briefing.lower()
    assert "3 cycle" in briefing.plain_english_briefing


# ---------------------------------------------------------------------------
# 4. Latest decision summary copied through unchanged
# ---------------------------------------------------------------------------


def test_latest_decision_summary_passes_through_verbatim():
    latest = _full_latest_decision()
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=latest,
        live_telemetry=None,
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert briefing.latest_decision_summary == latest["plain_english_summary"]
    # And the briefing surfaces it.
    assert latest["plain_english_summary"] in briefing.plain_english_briefing


# ---------------------------------------------------------------------------
# 5. Live telemetry with 2 positions and floating PnL aggregated
# ---------------------------------------------------------------------------


def test_live_telemetry_positions_and_pnl_aggregated():
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=_full_live_telemetry(),
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert briefing.open_position_count == 2
    assert briefing.total_floating_pnl == pytest.approx(9.25)
    assert "2 active paper/demo simulator proof row" in briefing.plain_english_briefing
    assert "Source is static simulation" in briefing.plain_english_briefing


def test_live_telemetry_prefers_canonical_position_feed_detail_when_present():
    detail = (
        "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
        "Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry "
        "until usable provider or MT5 quotes arrive. Requested provider: Yahoo. Static fallback symbols: NAS100. "
        "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)."
    )
    telemetry = {
        "open_positions": [
            {"symbol": "NAS100", "floating_pnl": 0.0},
        ],
        "totals": {"open_position_count": 1, "total_floating_pnl": 0.0},
        "position_feed_label": "SIM PROOF",
        "position_feed_detail": detail,
        "data_freshness": {
            "source": "movement_stream",
            "stale": False,
            "last_update_iso": _NOW.isoformat(),
            "movement_source": {
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "position_feed_label": "SIM PROOF",
                "position_feed_detail": "older nested detail that should not win",
            },
        },
    }

    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=telemetry,
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )

    assert briefing.live_position_feed_label == "SIM PROOF"
    assert briefing.live_position_feed_detail == detail
    assert briefing.live_movement_source_truth is not None
    assert briefing.live_movement_source_truth["position_feed_detail"] == detail
    assert briefing.live_movement_source_truth["detail"] == detail
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in briefing.live_position_feed_detail


def test_live_telemetry_without_totals_falls_back_to_positions_list():
    telemetry = {
        "open_positions": [
            {"symbol": "EURUSD", "floating_pnl": 10.0},
            {"symbol": "GBPUSD", "floating_pnl": -2.5},
        ],
    }
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=telemetry,
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert briefing.open_position_count == 2
    assert briefing.total_floating_pnl == pytest.approx(7.5)
    assert briefing.live_telemetry_source == "unknown"
    assert briefing.live_position_feed_label == "UNKNOWN"


# ---------------------------------------------------------------------------
# 6. MT5 probe verified → flags True
# ---------------------------------------------------------------------------


def test_mt5_probe_verified_sets_flags_true():
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=_full_mt5_probe(),
        readiness=None,
        now=_NOW,
    )
    assert briefing.mt5_terminal_connected is True
    assert briefing.mt5_broker_api_verified is True


def test_mt5_probe_unverified_keeps_flags_false():
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe={"summary": {"terminal_connected": False, "broker_api_verified": False}},
        readiness=None,
        now=_NOW,
    )
    assert briefing.mt5_terminal_connected is False
    assert briefing.mt5_broker_api_verified is False


# ---------------------------------------------------------------------------
# 7. Readiness checks_passed/total reflected
# ---------------------------------------------------------------------------


def test_readiness_counts_reflected():
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=_full_readiness(),
        now=_NOW,
    )
    assert briefing.readiness_gates_open == 7
    assert briefing.readiness_gates_total == 12
    assert "7/12" in briefing.plain_english_briefing


def test_public_launch_gate_reflected_without_advice():
    briefing = compose_operator_briefing(
        loop_health=_full_loop_health(),
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=_full_readiness(),
        public_launch_gate=_blocked_public_launch_gate(),
        now=_NOW,
    )

    assert briefing.public_launch_gate_status == "BLOCK_PUBLIC_LAUNCH"
    assert briefing.public_launch_status == "BLOCKED"
    assert briefing.live_money_production_status == "BLOCKED"
    assert briefing.public_launch_gate_block_count == 4
    assert "Public launch gate is BLOCK_PUBLIC_LAUNCH" in briefing.plain_english_briefing
    assert "4 blocker" in briefing.plain_english_briefing
    assert any("Counsel legal review is missing" in hint for hint in briefing.diagnostic_hints)


# ---------------------------------------------------------------------------
# 8. Forbidden advisory phrases NEVER appear in plain_english_briefing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_plain_english_briefing_never_contains_forbidden_phrase_empty(phrase: str):
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=None,
        now=_NOW,
    )
    assert phrase not in briefing.plain_english_briefing.lower(), (
        f"forbidden advisory phrase in empty briefing: {phrase!r}"
    )


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_plain_english_briefing_never_contains_forbidden_phrase_full(phrase: str):
    briefing = compose_operator_briefing(
        loop_health=_full_loop_health(),
        latest_decision=_full_latest_decision(),
        live_telemetry=_full_live_telemetry(),
        mt5_probe=_full_mt5_probe(),
        readiness=_full_readiness(),
        now=_NOW,
    )
    assert phrase not in briefing.plain_english_briefing.lower(), (
        f"forbidden advisory phrase in full briefing: {phrase!r}"
    )


# ---------------------------------------------------------------------------
# 9. diagnostic_hints capped at 5; merged from loop + readiness
# ---------------------------------------------------------------------------


def test_diagnostic_hints_capped_at_five_merging_loop_and_readiness():
    loop = dict(_full_loop_health())
    loop["diagnostic_hints"] = ["loop-1", "loop-2", "loop-3"]
    readiness = {
        "checks_total": 5,
        "checks_passed": 3,
        "next_actions": ["ready-1", "ready-2", "ready-3", "ready-4"],
    }
    briefing = compose_operator_briefing(
        loop_health=loop,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=readiness,
        now=_NOW,
    )
    # Loop hints come first; cap at 5 total.
    assert briefing.diagnostic_hints == (
        "loop-1",
        "loop-2",
        "loop-3",
        "ready-1",
        "ready-2",
    )
    assert len(briefing.diagnostic_hints) == 5


def test_diagnostic_hints_dedupe_and_handle_empty_sources():
    loop = dict(_full_loop_health())
    loop["diagnostic_hints"] = ["same-hint"]
    readiness = {
        "checks_total": 2,
        "checks_passed": 1,
        "next_actions": ["same-hint", "fresh-hint"],
    }
    briefing = compose_operator_briefing(
        loop_health=loop,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=readiness,
        now=_NOW,
    )
    assert briefing.diagnostic_hints == ("same-hint", "fresh-hint")


def test_readiness_blocked_check_next_action_promoted_to_hint():
    readiness = {
        "checks_total": 3,
        "checks_passed": 1,
        "next_actions": [],
        "checks": [
            {"status": "OPEN", "blocks_live": True, "next_action": "open-action-1"},
            {"status": "PASSED", "blocks_live": True, "next_action": "should-not-appear"},
        ],
    }
    briefing = compose_operator_briefing(
        loop_health=None,
        latest_decision=None,
        live_telemetry=None,
        mt5_probe=None,
        readiness=readiness,
        now=_NOW,
    )
    assert "open-action-1" in briefing.diagnostic_hints
    assert "should-not-appear" not in briefing.diagnostic_hints


def test_current_mt5_demo_snapshot_is_named_and_counted_as_broker_truth():
    briefing = compose_operator_briefing(
        live_telemetry=_current_mt5_demo_telemetry(),
        mt5_probe={"connected": True, "broker_api_verified": True},
        now=_NOW,
    )

    assert briefing.live_telemetry_source == "mt5_demo_account_snapshot"
    assert briefing.live_position_feed_label == "MT5 DEMO"
    assert briefing.open_position_count == 2
    assert briefing.broker_truth_open_position_count == 2
    assert briefing.broker_truth_mt5_connected is True
    assert briefing.broker_truth_mt5_is_demo is True
    assert briefing.broker_truth_position_protection_status == "ALL_POSITIONS_PROTECTED"
    assert briefing.broker_truth_position_protection_label == "PROTECTION CLEAR"
    assert briefing.total_floating_pnl == -188.94
    assert briefing.live_movement_source_truth["account_login"] == 1000694
    assert "2 active MT5 demo broker position(s)" in briefing.plain_english_briefing
    assert "No active MT5 broker positions" not in briefing.plain_english_briefing


def test_cached_briefing_position_story_is_replaced_by_current_mt5_truth():
    stale = compose_operator_briefing(
        live_telemetry={
            "totals": {"open_position_count": 0, "total_floating_pnl": 0.0},
            "data_freshness": {
                "source": "mt5_terminal_api_verifier",
                "stale": True,
                "last_update_iso": "2026-06-30T10:00:00+00:00",
            },
        },
        broker_truth_monitor={
            "monitor_status": "BROKER_TRUTH_MONITOR_OK",
            "ready_for_live": False,
            "latest_report": {
                "mt5_connected": True,
                "mt5_is_demo": True,
                "mt5_open_position_count": 4,
                "position_protection_status": "UNPROTECTED_POSITIONS",
                "position_protection_unprotected_position_count": 1,
                "position_protection_detail": "Stale protection report.",
            },
        },
        now=_NOW,
    )

    assert stale.broker_truth_open_position_count == 4

    refreshed = refresh_operator_briefing_live_telemetry(
        asdict(stale),
        _current_mt5_demo_telemetry(),
    )

    assert refreshed["open_position_count"] == 2
    assert refreshed["broker_truth_open_position_count"] == 2
    assert refreshed["broker_truth_mt5_connected"] is True
    assert refreshed["broker_truth_mt5_is_demo"] is True
    assert refreshed["broker_truth_position_protection_status"] == "ALL_POSITIONS_PROTECTED"
    assert refreshed["broker_truth_unprotected_position_count"] == 0
    assert refreshed["live_telemetry_source"] == "mt5_demo_account_snapshot"
    assert refreshed["live_position_feed_label"] == "MT5 DEMO"
    assert "2 active MT5 demo broker position(s)" in refreshed["plain_english_briefing"]
    assert "No active MT5 broker positions" not in refreshed["plain_english_briefing"]
    assert "2026-06-30T10:00:00+00:00" not in refreshed["plain_english_briefing"]
