"""Tests for the one-screen stack-health composer.

Asserts the 6-check structure (uvicorn-api / autowake-supervisor /
mt5-terminal / autonomous-loop / readiness-gates / live-telemetry), the
overall-status rollup, plain-English summary content, ordered factual
remediation list, and a regression guard ensuring the summary +
next_actions never contain trade-advisory phrases.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping

import pytest

from cas_forex.stack_health_check import (
    CheckResult,
    StackHealthReport,
    compose_stack_health_report,
)


FORBIDDEN_ADVISORY_PHRASES: tuple[str, ...] = (
    "buy now",
    "should you trade",
    "good entry",
    "place a trade",
    "what should i do",
    "you should sell",
    "now is the time",
    "consider buying",
    "consider selling",
)


def _now() -> datetime:
    return datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Input fixture builders
# ---------------------------------------------------------------------------


def _healthy_system_health() -> dict[str, Any]:
    return {
        "overall_status": "healthy",
        "processes": [
            {"process_name": "uvicorn-api", "status_label": "alive"},
            {"process_name": "autowake-supervisor", "status_label": "alive"},
            {"process_name": "mt5-terminal", "status_label": "alive"},
        ],
    }


def _stale_autowake_system_health() -> dict[str, Any]:
    return {
        "overall_status": "degraded",
        "processes": [
            {"process_name": "uvicorn-api", "status_label": "alive"},
            {"process_name": "autowake-supervisor", "status_label": "stale"},
            {"process_name": "mt5-terminal", "status_label": "alive"},
        ],
    }


def _healthy_operator_briefing() -> dict[str, Any]:
    return {
        "loop_health_status": "running",
        "cycles_today": 4,
        "plain_english_briefing": "Loop running.",
    }


def _healthy_loop_health() -> dict[str, Any]:
    return {
        "overall_status": "running",
        "cycles_today": 4,
        "seconds_since_last_cycle": 60.0,
    }


def _stalled_loop_health() -> dict[str, Any]:
    return {
        "overall_status": "stalled",
        "cycles_today": 0,
        "seconds_since_last_cycle": 21600.0,
    }


def _never_started_loop_health() -> dict[str, Any]:
    return {
        "overall_status": "never_started",
        "cycles_today": 0,
        "seconds_since_last_cycle": None,
    }


def _healthy_mt5_probe() -> dict[str, Any]:
    return {
        "summary": {
            "terminal_connected": True,
            "broker_api_verified": True,
        }
    }


def _disconnected_mt5_probe() -> dict[str, Any]:
    return {
        "summary": {
            "terminal_connected": False,
            "broker_api_verified": False,
        }
    }


def _terminal_only_mt5_probe() -> dict[str, Any]:
    # Terminal up, but broker not verified -> DEGRADED.
    return {
        "summary": {
            "terminal_connected": True,
            "broker_api_verified": False,
        }
    }


def _healthy_readiness() -> dict[str, Any]:
    return {
        "checks_passed": 5,
        "checks_total": 5,
        "next_actions": [],
    }


def _partial_readiness() -> dict[str, Any]:
    return {
        "checks_passed": 3,
        "checks_total": 5,
        "next_actions": ["resolve gate X"],
    }


def _healthy_live_telemetry() -> dict[str, Any]:
    return {"as_of_iso": "2026-06-25T11:59:00+00:00", "open_positions": []}


# ---------------------------------------------------------------------------
# 1. All inputs None -> UNKNOWN
# ---------------------------------------------------------------------------


def test_all_inputs_none_yields_unknown() -> None:
    report = compose_stack_health_report(now=_now())
    assert report.overall_status == "UNKNOWN"
    assert report.unknown_count == 6
    assert report.ok_count == 0
    assert "unknown" in report.plain_english_summary.lower()


# ---------------------------------------------------------------------------
# 2. All inputs healthy -> OK
# ---------------------------------------------------------------------------


def test_all_inputs_healthy_yields_ok() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    assert report.overall_status == "OK"
    assert report.ok_count == 6
    assert report.degraded_count == 0
    assert report.missing_count == 0
    assert report.unknown_count == 0
    assert report.next_actions == ()


# ---------------------------------------------------------------------------
# 3. autowake-supervisor stale -> DEGRADED check
# ---------------------------------------------------------------------------


def test_autowake_stale_is_degraded() -> None:
    report = compose_stack_health_report(
        system_health=_stale_autowake_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    autowake_check = next(c for c in report.checks if c.name == "autowake-supervisor")
    assert autowake_check.status == "DEGRADED"
    assert report.overall_status == "DEGRADED"
    assert autowake_check.remediation is not None


# ---------------------------------------------------------------------------
# 4. mt5_probe disconnected -> MISSING
# ---------------------------------------------------------------------------


def test_mt5_disconnected_is_missing() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_disconnected_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    mt5_check = next(c for c in report.checks if c.name == "mt5-terminal")
    assert mt5_check.status == "MISSING"
    assert report.overall_status == "MISSING"
    assert mt5_check.remediation is not None


def test_mt5_terminal_only_is_degraded() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_terminal_only_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    mt5_check = next(c for c in report.checks if c.name == "mt5-terminal")
    assert mt5_check.status == "DEGRADED"
    assert report.overall_status == "DEGRADED"


def test_mt5_probe_status_broker_api_verified_is_ok() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe={"status": "BROKER_API_VERIFIED", "broker": "MT5"},
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    mt5_check = next(c for c in report.checks if c.name == "mt5-terminal")
    assert mt5_check.status == "OK"
    assert report.overall_status == "OK"


# ---------------------------------------------------------------------------
# 5. Autonomous loop "stalled" -> DEGRADED
# ---------------------------------------------------------------------------


def test_autonomous_loop_stalled_is_degraded() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_stalled_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    loop_check = next(c for c in report.checks if c.name == "autonomous-loop")
    assert loop_check.status == "DEGRADED"
    assert "stalled" in loop_check.headline.lower()
    assert report.overall_status == "DEGRADED"


# ---------------------------------------------------------------------------
# 6. Autonomous loop "never_started" -> MISSING
# ---------------------------------------------------------------------------


def test_autonomous_loop_never_started_is_missing() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_never_started_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    loop_check = next(c for c in report.checks if c.name == "autonomous-loop")
    assert loop_check.status == "MISSING"
    assert report.overall_status == "MISSING"


# ---------------------------------------------------------------------------
# 7. Readiness gates all open -> OK
# ---------------------------------------------------------------------------


def test_readiness_gates_all_open_is_ok() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    gates_check = next(c for c in report.checks if c.name == "readiness-gates")
    assert gates_check.status == "OK"
    # Caveat about paper/demo lane should appear in detail.
    assert "paper" in gates_check.detail.lower() or "demo" in gates_check.detail.lower()


# ---------------------------------------------------------------------------
# 8. Readiness gates partial -> DEGRADED with count
# ---------------------------------------------------------------------------


def test_readiness_gates_partial_is_degraded_with_count() -> None:
    report = compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_partial_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    gates_check = next(c for c in report.checks if c.name == "readiness-gates")
    assert gates_check.status == "DEGRADED"
    assert "3" in gates_check.headline or "3" in gates_check.detail
    assert "5" in gates_check.headline or "5" in gates_check.detail


# ---------------------------------------------------------------------------
# 9. overall MISSING when any check is MISSING
# ---------------------------------------------------------------------------


def test_overall_missing_when_any_missing() -> None:
    # Stalled loop AND disconnected MT5 -> overall MISSING (not DEGRADED).
    report = compose_stack_health_report(
        system_health=_stale_autowake_system_health(),  # DEGRADED
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_stalled_loop_health(),  # DEGRADED
        mt5_probe=_disconnected_mt5_probe(),  # MISSING
        readiness=_partial_readiness(),  # DEGRADED
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    assert report.overall_status == "MISSING"
    assert report.missing_count >= 1


# ---------------------------------------------------------------------------
# 10. next_actions ordered: MISSING first, then DEGRADED
# ---------------------------------------------------------------------------


def test_next_actions_missing_first_then_degraded() -> None:
    # uvicorn missing (no briefing), autowake stale (DEGRADED).
    report = compose_stack_health_report(
        system_health=_stale_autowake_system_health(),
        operator_briefing=None,  # uvicorn-api -> MISSING
        loop_health=_healthy_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )
    actions = report.next_actions
    assert len(actions) >= 2
    # uvicorn (MISSING) remediation must precede autowake (DEGRADED).
    uvicorn_idx = next(
        i for i, a in enumerate(actions) if "uvicorn" in a.lower()
    )
    autowake_idx = next(
        i for i, a in enumerate(actions) if "autowake" in a.lower()
    )
    assert uvicorn_idx < autowake_idx


# ---------------------------------------------------------------------------
# 11. Forbidden advisory phrases never appear (parametrized over 4 reports)
# ---------------------------------------------------------------------------


def _sample_report_healthy() -> StackHealthReport:
    return compose_stack_health_report(
        system_health=_healthy_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_healthy_loop_health(),
        mt5_probe=_healthy_mt5_probe(),
        readiness=_healthy_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )


def _sample_report_all_missing() -> StackHealthReport:
    return compose_stack_health_report(
        system_health={"processes": [{"process_name": "autowake-supervisor", "status_label": "missing"}]},
        operator_briefing=None,
        loop_health=_never_started_loop_health(),
        mt5_probe=_disconnected_mt5_probe(),
        readiness=None,
        live_telemetry=None,
        now=_now(),
    )


def _sample_report_mixed_degraded() -> StackHealthReport:
    return compose_stack_health_report(
        system_health=_stale_autowake_system_health(),
        operator_briefing=_healthy_operator_briefing(),
        loop_health=_stalled_loop_health(),
        mt5_probe=_terminal_only_mt5_probe(),
        readiness=_partial_readiness(),
        live_telemetry=_healthy_live_telemetry(),
        now=_now(),
    )


def _sample_report_all_none() -> StackHealthReport:
    return compose_stack_health_report(now=_now())


@pytest.mark.parametrize(
    "report_factory",
    [
        _sample_report_healthy,
        _sample_report_all_missing,
        _sample_report_mixed_degraded,
        _sample_report_all_none,
    ],
)
def test_no_forbidden_advisory_phrases(report_factory) -> None:
    report = report_factory()
    blob = " ".join(
        [report.plain_english_summary, *report.next_actions]
    ).lower()
    for phrase in FORBIDDEN_ADVISORY_PHRASES:
        assert phrase not in blob, (
            f"forbidden advisory phrase {phrase!r} present in: {blob!r}"
        )


# ---------------------------------------------------------------------------
# 12. CheckResult / StackHealthReport JSON-serializable via asdict
# ---------------------------------------------------------------------------


def test_report_is_json_serializable_via_asdict() -> None:
    import json

    report = _sample_report_mixed_degraded()
    payload = asdict(report)
    text = json.dumps(payload, default=str)
    assert text  # serialization succeeded
    # Round trip back through json.loads and recover the same overall.
    decoded = json.loads(text)
    assert decoded["overall_status"] == report.overall_status
    assert len(decoded["checks"]) == 6
    for check in decoded["checks"]:
        assert set(check.keys()) >= {
            "name",
            "status",
            "headline",
            "detail",
            "remediation",
        }
