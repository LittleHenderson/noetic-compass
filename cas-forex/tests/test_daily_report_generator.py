"""Unit tests for cas_forex.daily_report_generator.

The end-of-day report is OBSERVATIONAL only — these tests enforce both
the structural shape and the no-advisory-phrasing contract.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import pytest

from cas_forex.daily_report_generator import (
    DailyReport,
    DailySection,
    SECTION_NAMES,
    compose_daily_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _fixed_now() -> datetime:
    return datetime(2026, 6, 25, 23, 59, 0, tzinfo=timezone.utc)


def _empty_inputs() -> dict[str, Any]:
    return {
        "daily_rollup": None,
        "cycle_reports": None,
        "event_journal": None,
        "live_telemetry_snapshots": None,
        "risk_snapshots": None,
        "system_health_snapshots": None,
    }


def _cycle(
    *,
    cycle_id: str,
    decisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "cycle_id": cycle_id,
        "overseer_decisions": decisions or [],
    }


def _exec_decision(*, approved: bool = True, command_ready: bool = True, reasons=None):
    return {
        "approved": approved,
        "command_ready": command_ready,
        "decision": "APPROVE_ROUTE_INTENT" if approved else "REJECT_ROUTE_INTENT",
        "reasons": reasons or [],
    }


def _reject(*, reason: str = "live_trading currently not licensed"):
    return _exec_decision(approved=False, command_ready=False, reasons=[reason])


def _rich_inputs() -> dict[str, Any]:
    cycles = [
        _cycle(
            cycle_id="c-1",
            decisions=[
                _exec_decision(approved=True, command_ready=True),
                _reject(reason="live_trading currently not licensed"),
            ],
        ),
        _cycle(
            cycle_id="c-2",
            decisions=[_reject(reason="live_trading currently not licensed")],
        ),
        _cycle(
            cycle_id="c-3",
            decisions=[
                _reject(reason="live_trading currently not licensed"),
                _reject(reason="live_trading currently not licensed"),
                _reject(reason="live_trading currently not licensed"),
                _reject(reason="live_trading currently not licensed"),
                _reject(reason="live_trading currently not licensed"),
            ],
        ),
        _cycle(cycle_id="c-4", decisions=[]),
        _cycle(
            cycle_id="c-5",
            decisions=[
                _exec_decision(approved=True, command_ready=False),
            ],
        ),
    ]
    rollup = {
        "by_strategy": [
            {"key": "alpha_strategy", "closed_count": 3, "net_profit_loss_account": 25.5},
            {"key": "bravo_strategy", "closed_count": 1, "net_profit_loss_account": -2.05},
        ]
    }
    events = [
        {
            "event_type": "STRATEGY_PROMOTED",
            "created_at": "2026-06-25T01:00:00+00:00",
            "payload": {"strategy": "alpha_strategy"},
        },
        {
            "event_type": "STRATEGY_DEMOTED",
            "created_at": "2026-06-25T02:00:00+00:00",
            "payload": {"strategy": "charlie_strategy"},
        },
        {
            "event_type": "WALK_FORWARD_VERDICT",
            "created_at": "2026-06-25T03:00:00+00:00",
            "payload": {"verdict": "PASS"},
        },
        {
            "event_type": "AUTONOMOUS_LOOP_STALLED",
            "created_at": "2026-06-25T04:00:00+00:00",
            "payload": {},
        },
        {
            "event_type": "AUTONOMOUS_LOOP_STALLED",
            "created_at": "2026-06-25T04:30:00+00:00",
            "payload": {},
        },
        {
            "event_type": "AUTONOMOUS_LOOP_STALLED",
            "created_at": "2026-06-25T05:00:00+00:00",
            "payload": {},
        },
        {
            "event_type": "MT5_DISCONNECTED",
            "created_at": "2026-06-25T14:32:00+00:00",
            "payload": {},
        },
        {
            "event_type": "DISPATCH_FAILED",
            "created_at": "2026-06-25T16:00:00+00:00",
            "payload": {},
        },
        # 12 validator REJECT events to trip the >=10 hint.
        *(
            {
                "event_type": "VALIDATOR_REJECT",
                "created_at": f"2026-06-25T10:{i:02d}:00+00:00",
                "payload": {"gate": "live_trading"},
            }
            for i in range(12)
        ),
    ]
    live_snaps = [
        {"totals": {"open_position_count": 1, "total_floating_pnl": 12.5}},
        {"totals": {"open_position_count": 2, "total_floating_pnl": -8.0}},
    ]
    risk_snaps = [
        {
            "peak_concentration": 0.45,
            "peak_margin_utilization": 0.30,
            "max_floating_loss": -15.0,
            "max_floating_gain": 18.0,
        }
    ]
    system_snaps = [
        {
            "uvicorn_up": True,
            "autowake_up": True,
            "mt5_disconnected": False,
            "timestamp": "2026-06-25T00:30:00+00:00",
        },
        {
            "uvicorn_up": True,
            "autowake_up": False,
            "mt5_disconnected": True,
            "timestamp": "2026-06-25T14:32:00+00:00",
        },
    ]
    return {
        "daily_rollup": rollup,
        "cycle_reports": cycles,
        "event_journal": events,
        "live_telemetry_snapshots": live_snaps,
        "risk_snapshots": risk_snaps,
        "system_health_snapshots": system_snaps,
    }


def _compose(**overrides: Any) -> DailyReport:
    inputs = _empty_inputs()
    inputs.update(overrides)
    return compose_daily_report(
        report_date="2026-06-25",
        now=_fixed_now(),
        **inputs,
    )


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_empty_inputs_produce_no_activity_report():
    report = _compose()
    assert isinstance(report, DailyReport)
    assert report.report_date == "2026-06-25"
    assert "no activity" in report.overall_headline.lower()
    assert all(isinstance(s, DailySection) for s in report.sections)


def test_all_seven_sections_always_present_in_canonical_order():
    report = _compose(**_rich_inputs())
    assert tuple(s.section_name for s in report.sections) == SECTION_NAMES
    assert len(report.sections) == 7


def test_single_cycle_populates_cycles_section():
    report = _compose(
        cycle_reports=[
            _cycle(
                cycle_id="c-only",
                decisions=[_exec_decision(approved=True, command_ready=True)],
            )
        ],
    )
    cycles = next(s for s in report.sections if s.section_name == "cycles")
    assert cycles.metrics["total_cycles"] == 1
    assert cycles.metrics["executed"] == 1


def test_multiple_cycles_aggregate_correctly():
    report = _compose(**_rich_inputs())
    cycles = next(s for s in report.sections if s.section_name == "cycles")
    assert cycles.metrics["total_cycles"] == 5
    # c-1 has 1 approved+command_ready → executed.
    assert cycles.metrics["executed"] == 1
    # c-5 → approved_not_executed.
    assert cycles.metrics["approved_not_executed"] == 1
    # c-2 + c-3 → blocked.
    assert cycles.metrics["blocked"] == 2
    # c-4 → no_intent.
    assert cycles.metrics["no_intent"] == 1
    # c-3 had 5 blocked intents → notable event.
    assert any("5 blocked intents" in n for n in cycles.notable_events)


def test_decisions_section_top_blocking_reason():
    report = _compose(**_rich_inputs())
    decisions = next(s for s in report.sections if s.section_name == "decisions")
    assert decisions.metrics["total_decisions"] >= 8
    assert decisions.metrics["top_blocking_reason"] == (
        "live_trading currently not licensed"
    )


def test_executions_section_carries_pnl_and_top_strategies():
    report = _compose(**_rich_inputs())
    executions = next(s for s in report.sections if s.section_name == "executions")
    assert executions.metrics["total_executions"] == 4
    assert executions.metrics["net_pnl"] == pytest.approx(23.45)
    assert executions.metrics["top_winning_strategy"] == "alpha_strategy"
    assert executions.metrics["top_losing_strategy"] == "bravo_strategy"


def test_strategies_section_counts_promotions_demotions_and_verdicts():
    report = _compose(**_rich_inputs())
    strategies = next(s for s in report.sections if s.section_name == "strategies")
    assert strategies.metrics["promotions"] == 1
    assert strategies.metrics["demotions"] == 1
    assert strategies.metrics["walk_forward_verdicts"] == {"PASS": 1}


def test_risk_section_observes_concentration_and_floating_range():
    report = _compose(**_rich_inputs())
    risk = next(s for s in report.sections if s.section_name == "risk")
    assert risk.metrics["peak_concentration"] == pytest.approx(0.45)
    assert risk.metrics["peak_margin_utilization"] == pytest.approx(0.30)
    assert risk.metrics["max_floating_loss"] <= -15.0
    assert risk.metrics["max_floating_gain"] >= 18.0


def test_system_section_uptime_percentages_observed():
    report = _compose(**_rich_inputs())
    system = next(s for s in report.sections if s.section_name == "system")
    assert system.metrics["samples_observed"] == 2
    assert system.metrics["uvicorn_uptime_pct"] == pytest.approx(1.0)
    assert system.metrics["autowake_uptime_pct"] == pytest.approx(0.5)
    assert system.metrics["mt5_disconnect_events"] >= 1


def test_incidents_section_surfaces_loop_stalls_and_dispatch_failures():
    report = _compose(**_rich_inputs())
    incidents = next(s for s in report.sections if s.section_name == "incidents")
    assert incidents.metrics["loop_stalls"] == 3
    assert incidents.metrics["dispatch_failures"] == 1
    assert incidents.metrics["validator_rejects"] == 12
    assert any("Loop stall" in n for n in incidents.notable_events)


def test_diagnostic_hints_generated_when_conditions_met():
    report = _compose(**_rich_inputs())
    joined = " ".join(report.diagnostic_hints)
    assert "Loop stalled 3 time(s) today." in joined
    assert "MT5 disconnected" in joined
    assert "Validator REJECTed 12 intents today." in joined
    assert "Dispatch failures observed" in joined


def test_empty_inputs_give_no_diagnostic_hints():
    report = _compose()
    assert report.diagnostic_hints == ()


def test_overall_headline_template_matches_expected_shape():
    report = _compose(**_rich_inputs())
    assert report.overall_headline.startswith("2026-06-25:")
    assert "cycle(s)" in report.overall_headline
    assert "execution(s)" in report.overall_headline
    assert "blocked" in report.overall_headline


def test_dataclass_is_json_serializable():
    import json

    report = _compose(**_rich_inputs())
    text = json.dumps(asdict(report), default=str)
    assert isinstance(text, str) and len(text) > 0


def test_invalid_date_falls_back_to_injected_now_string():
    # The fallback date must be derived from the injected ``now`` (deterministic),
    # not from real wall-clock today.
    now = _fixed_now()
    report = compose_daily_report(report_date="", now=now)
    assert report.report_date == now.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Forbidden-advisory-phrase enforcement
# ---------------------------------------------------------------------------


FORBIDDEN_PHRASES = [
    "you should",
    "should have",
    "we recommend",
    "next time you should",
    "consider closing",
    "consider taking",
    "consider buying",
    "consider selling",
    "is a good",
    "would have been better",
]


def _collect_text(report: DailyReport) -> str:
    parts: list[str] = [
        report.overall_headline,
        report.plain_english_summary,
    ]
    for section in report.sections:
        parts.append(section.headline)
        parts.append(section.detail)
        parts.extend(section.notable_events)
    parts.extend(report.diagnostic_hints)
    return " \n ".join(parts).lower()


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_empty_report_never_contains_advisory_phrase(phrase: str):
    report = _compose()
    text = _collect_text(report)
    assert phrase not in text, f"advisory phrase {phrase!r} surfaced in empty report"


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_rich_report_never_contains_advisory_phrase(phrase: str):
    report = _compose(**_rich_inputs())
    text = _collect_text(report)
    assert phrase not in text, f"advisory phrase {phrase!r} surfaced in rich report"
