"""Tests for cas_forex.autonomous_loop_health.summarize_autonomous_loop_health.

These tests are pure: they pass dicts directly to the summariser. No disk
access; the helper :func:`load_loop_health_inputs` is not exercised here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cas_forex.autonomous_loop_health import (
    AutonomousLoopHealth,
    summarize_autonomous_loop_health,
)


NOW = datetime(2026, 6, 24, 18, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


# --- Test 1: All inputs None -> "unknown" ------------------------------------


def test_all_inputs_none_returns_unknown() -> None:
    result = summarize_autonomous_loop_health(now=NOW)

    assert isinstance(result, AutonomousLoopHealth)
    assert result.overall_status == "unknown"
    assert result.last_cycle_at_iso is None
    assert result.seconds_since_last_cycle is None
    assert result.cycles_today == 0
    assert result.decisions_today == 0
    assert result.executions_today == 0
    assert result.blocked_today == 0
    assert result.autowake_present is False
    assert result.autowake_next_due_iso is None
    assert "unknown" in result.plain_english_summary.lower()
    assert result.diagnostic_hints  # non-empty: tells caller what to provide


# --- Test 2: No cycle reports -> "never_started" -----------------------------


def test_no_cycle_reports_returns_never_started() -> None:
    autowake = {
        "summary": {"next_due_at": _iso(NOW + timedelta(minutes=30))},
        "event_evaluations": [],
    }

    result = summarize_autonomous_loop_health(
        autowake_report=autowake,
        latest_cycle_report=None,
        recent_event_journal=[],
        daily_rollup=None,
        now=NOW,
    )

    assert result.overall_status == "never_started"
    assert result.last_cycle_at_iso is None
    assert result.seconds_since_last_cycle is None
    assert result.autowake_present is True
    assert any("cycle" in hint.lower() for hint in result.diagnostic_hints)


# --- Test 3: Cycle within threshold -> "running" + correct seconds -----------


def test_cycle_within_threshold_returns_running() -> None:
    cycle_at = NOW - timedelta(minutes=10)
    cycle_report = {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": "agent-cycle-abc",
        "created_at": _iso(cycle_at),
        "summary": {
            "approved_intent_count": 3,
            "rejected_intent_count": 1,
            "terminal_command_count": 2,
        },
    }

    result = summarize_autonomous_loop_health(
        latest_cycle_report=cycle_report,
        now=NOW,
        running_threshold_minutes=60,
    )

    assert result.overall_status == "running"
    assert result.last_cycle_at_iso == _iso(cycle_at)
    assert result.seconds_since_last_cycle == pytest.approx(600.0, rel=1e-3)
    assert result.cycles_today == 1
    assert result.decisions_today == 4  # 3 approved + 1 rejected
    assert result.executions_today == 2
    assert result.blocked_today == 1
    assert result.diagnostic_hints == ()  # empty when running


# --- Test 4: Cycle older than threshold + no future autowake -> "stalled" ----


def test_old_cycle_no_future_autowake_returns_stalled() -> None:
    cycle_at = NOW - timedelta(hours=4)
    cycle_report = {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": "agent-cycle-stale",
        "created_at": _iso(cycle_at),
        "summary": {
            "approved_intent_count": 0,
            "rejected_intent_count": 0,
            "terminal_command_count": 0,
        },
    }
    autowake = {
        # next-due is in the PAST -> equivalent to no future fire scheduled
        "summary": {"next_due_at": _iso(NOW - timedelta(minutes=30))},
        "event_evaluations": [],
    }

    result = summarize_autonomous_loop_health(
        autowake_report=autowake,
        latest_cycle_report=cycle_report,
        now=NOW,
        running_threshold_minutes=60,
    )

    assert result.overall_status == "stalled"
    assert result.seconds_since_last_cycle == pytest.approx(4 * 3600, rel=1e-3)
    assert any("stalled" in hint.lower() or "restart" in hint.lower() for hint in result.diagnostic_hints)


# --- Test 5: Old cycle BUT autowake_next_due in the future -> still "running"


def test_old_cycle_with_future_autowake_still_running() -> None:
    cycle_at = NOW - timedelta(hours=3)
    cycle_report = {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": "agent-cycle-paced",
        "created_at": _iso(cycle_at),
        "summary": {
            "approved_intent_count": 0,
            "rejected_intent_count": 0,
            "terminal_command_count": 0,
        },
    }
    future_due = NOW + timedelta(minutes=15)
    autowake = {
        "summary": {"next_due_at": _iso(future_due)},
        "event_evaluations": [],
    }

    result = summarize_autonomous_loop_health(
        autowake_report=autowake,
        latest_cycle_report=cycle_report,
        now=NOW,
        running_threshold_minutes=60,
    )

    assert result.overall_status == "running"
    assert result.autowake_next_due_iso == _iso(future_due)
    # When running, diagnostic_hints is empty.
    assert result.diagnostic_hints == ()


# --- Test 6: Multiple cycles today aggregation -------------------------------


def test_cycles_today_aggregated_from_event_journal() -> None:
    cycle_at = NOW - timedelta(minutes=5)
    events = [
        {
            "event_type": "AGENT_CYCLE_STARTED",
            "event_at": _iso(NOW - timedelta(hours=6)),
            "cycle_id": "agent-cycle-1",
        },
        {
            "event_type": "AGENT_CYCLE_STARTED",
            "event_at": _iso(NOW - timedelta(hours=3)),
            "cycle_id": "agent-cycle-2",
        },
        {
            "event_type": "AGENT_CYCLE_STARTED",
            "event_at": _iso(NOW - timedelta(minutes=5)),
            "cycle_id": "agent-cycle-3",
        },
        # Duplicate cycle_id should not double-count
        {
            "event_type": "AGENT_CYCLE_STARTED",
            "event_at": _iso(NOW - timedelta(minutes=7)),
            "cycle_id": "agent-cycle-3",
        },
        # Yesterday's cycle: should not be counted
        {
            "event_type": "AGENT_CYCLE_STARTED",
            "event_at": _iso(NOW - timedelta(days=1, hours=2)),
            "cycle_id": "agent-cycle-old",
        },
        # Route intents to feed decisions_today
        {
            "event_type": "ROUTE_INTENT_CREATED",
            "event_at": _iso(NOW - timedelta(minutes=10)),
            "status": "PENDING",
        },
        {
            "event_type": "ROUTE_INTENT_CREATED",
            "event_at": _iso(NOW - timedelta(minutes=8)),
            "status": "PENDING",
        },
    ]
    cycle_report = {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": "agent-cycle-3",
        "created_at": _iso(cycle_at),
        "summary": {
            "approved_intent_count": 2,
            "rejected_intent_count": 0,
            "terminal_command_count": 1,
        },
    }

    result = summarize_autonomous_loop_health(
        latest_cycle_report=cycle_report,
        recent_event_journal=events,
        now=NOW,
    )

    assert result.overall_status == "running"
    assert result.cycles_today == 3  # three distinct cycle_ids today
    assert result.decisions_today == 2  # two ROUTE_INTENT_CREATED today
    assert result.last_cycle_at_iso == _iso(cycle_at)


# --- Test 7: plain_english_summary must NOT include trade-advisory language --


@pytest.mark.parametrize(
    "scenario",
    [
        "unknown",
        "never_started",
        "running",
        "stalled",
    ],
)
def test_plain_english_summary_never_contains_trade_advisory(scenario: str) -> None:
    if scenario == "unknown":
        result = summarize_autonomous_loop_health(now=NOW)
    elif scenario == "never_started":
        result = summarize_autonomous_loop_health(
            autowake_report={"summary": {}, "event_evaluations": []},
            now=NOW,
        )
    elif scenario == "running":
        result = summarize_autonomous_loop_health(
            latest_cycle_report={
                "report_kind": "cas_forex_agent_workflow_cycle",
                "cycle_id": "agent-cycle-x",
                "created_at": _iso(NOW - timedelta(minutes=2)),
                "summary": {
                    "approved_intent_count": 5,
                    "rejected_intent_count": 0,
                    "terminal_command_count": 5,
                },
            },
            now=NOW,
        )
    else:  # stalled
        result = summarize_autonomous_loop_health(
            latest_cycle_report={
                "report_kind": "cas_forex_agent_workflow_cycle",
                "cycle_id": "agent-cycle-stale",
                "created_at": _iso(NOW - timedelta(hours=8)),
                "summary": {
                    "approved_intent_count": 0,
                    "rejected_intent_count": 0,
                    "terminal_command_count": 0,
                },
            },
            now=NOW,
        )

    summary = result.plain_english_summary.lower()
    forbidden_phrases = [
        "buy now",
        "sell now",
        "should you trade",
        "good entry",
        "good time to trade",
        "you should buy",
        "you should sell",
        "open a trade",
        "place a trade",
        "trade recommendation",
        "trade signal",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in summary, (
            f"plain_english_summary leaked trade-advisory phrase {phrase!r}: "
            f"{result.plain_english_summary!r}"
        )


# --- Extra: decision/blocked aggregation from daily_rollup fallback ---------


def test_decisions_and_blocked_fallback_to_daily_rollup() -> None:
    cycle_at = NOW - timedelta(minutes=15)
    cycle_report = {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": "agent-cycle-q",
        "created_at": _iso(cycle_at),
        # No summary counts to force fallback.
        "summary": {},
    }
    daily_rollup = {
        "summary": {
            "approved_count": 7,
            "rejected_count": 4,
        }
    }

    result = summarize_autonomous_loop_health(
        latest_cycle_report=cycle_report,
        recent_event_journal=[],
        daily_rollup=daily_rollup,
        now=NOW,
    )

    assert result.overall_status == "running"
    assert result.decisions_today == 11
    assert result.blocked_today == 4
