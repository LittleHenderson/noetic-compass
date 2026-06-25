"""Pure tests for cas_forex.operator_briefing.compose_operator_briefing.

The composer must:
* Never fabricate counts/timestamps when inputs are missing.
* Always produce a plain-English briefing that is OBSERVATIONAL — never
  advisory. The 7 forbidden phrases below are explicitly checked.
* Cap diagnostic hints at 5, merging loop-health hints with readiness
  hints in that order.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from cas_forex.operator_briefing import (
    OperatorBriefing,
    compose_operator_briefing,
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
        "data_freshness": {"source": "movement_stream", "stale": False, "last_update_iso": _NOW.isoformat()},
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
    assert briefing.mt5_terminal_connected is False
    assert briefing.mt5_broker_api_verified is False
    assert briefing.readiness_gates_open == 0
    assert briefing.readiness_gates_total == 0
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
    assert briefing.mt5_terminal_connected is True
    assert briefing.mt5_broker_api_verified is True
    assert briefing.readiness_gates_open == 7
    assert briefing.readiness_gates_total == 12
    assert briefing.autowake_present is True
    assert briefing.autowake_next_due_iso == "2026-06-24T13:00:00+00:00"


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
    assert "2 active position" in briefing.plain_english_briefing


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
