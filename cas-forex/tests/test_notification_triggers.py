"""Tests for the pure notification observer primitives.

These tests cover each detector's positive and negative branches plus
the OBSERVATIONAL invariant: a parametrized list of trade-advisory
phrases is checked against the title + body of every event every
detector can produce, and none must appear.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cas_forex.notification_triggers import (
    EVENT_LOOP_RESUMED,
    EVENT_LOOP_STALLED,
    EVENT_MT5_DISCONNECTED,
    EVENT_READINESS_GATE_FLIPPED,
    EVENT_TRADE_BLOCKED,
    EVENT_TRADE_EXECUTED,
    NotificationEvent,
    SEVERITY_ALERT,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    detect_all,
    detect_loop_resumed,
    detect_loop_stalled,
    detect_mt5_disconnected,
    detect_readiness_gate_flipped,
    detect_trade_blocked,
    detect_trade_executed,
)


# Trade-advisory phrases that MUST NEVER appear in any event's title or
# body. These are the substrings that turn an instrument-panel readout
# into a trade recommendation; the architectural commitment is that
# notifications never carry them, full stop.
FORBIDDEN_PHRASES = [
    "buy now",
    "should you trade",
    "good entry",
    "place a trade",
    "what should i do",
    "you should sell",
    "you should buy",
    "now is the time",
    "consider buying",
    "consider selling",
    "is a buy",
    "is a sell",
    "we recommend",
    "recommended trade",
]


FIXED_NOW = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# detect_trade_executed
# ---------------------------------------------------------------------------


def test_detect_trade_executed_fires_on_verified_fill():
    cycle = {
        "cycle_id": "cycle-abc",
        "symbol": "EURUSD",
        "side": "buy",
        "lots": 0.01,
        "broker_ticket": 12345,
        "receipt_verified": True,
    }
    event = detect_trade_executed(latest_cycle_report=cycle, now=FIXED_NOW)
    assert event is not None
    assert event.event_kind == EVENT_TRADE_EXECUTED
    assert event.severity == SEVERITY_INFO
    assert event.payload["broker_ticket"] == "12345"
    assert event.payload["symbol"] == "EURUSD"
    # event_id is deterministic
    again = detect_trade_executed(latest_cycle_report=cycle, now=FIXED_NOW)
    assert again is not None
    assert again.event_id == event.event_id


def test_detect_trade_executed_returns_none_when_unverified_or_no_ticket():
    # no ticket
    assert (
        detect_trade_executed(
            latest_cycle_report={"cycle_id": "c1", "receipt_verified": True},
            now=FIXED_NOW,
        )
        is None
    )
    # ticket but not verified
    assert (
        detect_trade_executed(
            latest_cycle_report={
                "cycle_id": "c1",
                "broker_ticket": 7,
                "receipt_verified": False,
            },
            now=FIXED_NOW,
        )
        is None
    )
    # missing input
    assert detect_trade_executed(latest_cycle_report=None, now=FIXED_NOW) is None


def test_detect_trade_executed_dedupes_against_previous_cycle():
    cycle = {
        "cycle_id": "cycle-abc",
        "symbol": "EURUSD",
        "side": "buy",
        "lots": 0.01,
        "broker_ticket": 12345,
        "receipt_verified": True,
    }
    # same cycle id + ticket already observed last tick -> no event
    assert (
        detect_trade_executed(
            latest_cycle_report=cycle,
            previous_cycle_report=cycle,
            now=FIXED_NOW,
        )
        is None
    )


# ---------------------------------------------------------------------------
# detect_trade_blocked
# ---------------------------------------------------------------------------


def test_detect_trade_blocked_fires_with_gate_name():
    decision = {
        "decision_id": "dec-9",
        "overall_status": "blocked",
        "blocking_gate": "pcba_readiness",
        "symbol": "USDJPY",
        "reason": "live trading not authorized",
    }
    event = detect_trade_blocked(latest_decision=decision, now=FIXED_NOW)
    assert event is not None
    assert event.event_kind == EVENT_TRADE_BLOCKED
    assert event.severity == SEVERITY_WARNING
    assert "pcba_readiness" in event.title
    assert event.payload["blocking_gate"] == "pcba_readiness"


def test_detect_trade_blocked_falls_back_to_failed_gates():
    decision = {
        "decision_id": "dec-10",
        "overall_status": "blocked",
        "failed_gates": ["mt5_bridge", "ccb"],
        "symbol": "EURUSD",
    }
    event = detect_trade_blocked(latest_decision=decision, now=FIXED_NOW)
    assert event is not None
    assert event.payload["blocking_gate"] == "mt5_bridge"


def test_detect_trade_blocked_returns_none_when_not_blocked():
    assert (
        detect_trade_blocked(
            latest_decision={"decision_id": "x", "overall_status": "approved"},
            now=FIXED_NOW,
        )
        is None
    )
    assert detect_trade_blocked(latest_decision=None, now=FIXED_NOW) is None


# ---------------------------------------------------------------------------
# detect_loop_stalled / detect_loop_resumed
# ---------------------------------------------------------------------------


def test_detect_loop_stalled_fires_on_transition_from_running():
    health = {
        "status": "stalled",
        "last_cycle_at": "2026-06-25T11:55:00+00:00",
        "seconds_since_last_cycle": 300,
    }
    event = detect_loop_stalled(
        loop_health=health, previous_status="running", now=FIXED_NOW
    )
    assert event is not None
    assert event.event_kind == EVENT_LOOP_STALLED
    assert event.severity == SEVERITY_ALERT
    assert event.payload["previous_status"] == "running"


def test_detect_loop_stalled_does_not_fire_when_already_stalled():
    health = {"status": "stalled"}
    # no transition -> no event
    assert (
        detect_loop_stalled(
            loop_health=health, previous_status="stalled", now=FIXED_NOW
        )
        is None
    )
    # current not stalled -> no event
    assert (
        detect_loop_stalled(
            loop_health={"status": "running"},
            previous_status="running",
            now=FIXED_NOW,
        )
        is None
    )


def test_detect_loop_resumed_fires_from_stalled_or_unknown():
    health = {"status": "running", "last_cycle_at": "2026-06-25T12:00:00+00:00"}
    from_stalled = detect_loop_resumed(
        loop_health=health, previous_status="stalled", now=FIXED_NOW
    )
    from_unknown = detect_loop_resumed(
        loop_health=health, previous_status="unknown", now=FIXED_NOW
    )
    assert from_stalled is not None
    assert from_unknown is not None
    assert from_stalled.event_kind == EVENT_LOOP_RESUMED
    assert from_stalled.severity == SEVERITY_INFO
    # no transition from running -> no event
    assert (
        detect_loop_resumed(
            loop_health=health, previous_status="running", now=FIXED_NOW
        )
        is None
    )


# ---------------------------------------------------------------------------
# detect_mt5_disconnected
# ---------------------------------------------------------------------------


def test_detect_mt5_disconnected_fires_on_transition_to_disconnected():
    probe = {
        "connected": False,
        "account": "live-1234567",
        "last_error": "terminal closed",
    }
    event = detect_mt5_disconnected(
        mt5_probe=probe, previous_connected=True, now=FIXED_NOW
    )
    assert event is not None
    assert event.event_kind == EVENT_MT5_DISCONNECTED
    assert event.severity == SEVERITY_ALERT
    assert event.payload["account"] == "live-1234567"


def test_detect_mt5_disconnected_does_not_fire_without_transition():
    # already disconnected -> no event
    assert (
        detect_mt5_disconnected(
            mt5_probe={"connected": False},
            previous_connected=False,
            now=FIXED_NOW,
        )
        is None
    )
    # currently connected -> no event
    assert (
        detect_mt5_disconnected(
            mt5_probe={"connected": True},
            previous_connected=True,
            now=FIXED_NOW,
        )
        is None
    )
    # missing input -> no event
    assert detect_mt5_disconnected(mt5_probe=None, previous_connected=True) is None


# ---------------------------------------------------------------------------
# detect_readiness_gate_flipped
# ---------------------------------------------------------------------------


def test_detect_readiness_gate_flipped_fires_on_authorization_diff():
    readiness = {"authorized": ["paper_trading", "live_trading_read"]}
    event = detect_readiness_gate_flipped(
        readiness=readiness,
        previous_authorized_set=frozenset({"paper_trading"}),
        now=FIXED_NOW,
    )
    assert event is not None
    assert event.event_kind == EVENT_READINESS_GATE_FLIPPED
    assert "live_trading_read" in event.payload["newly_authorized"]
    assert event.payload["newly_revoked"] == []


def test_detect_readiness_gate_flipped_does_not_fire_without_baseline_or_diff():
    # no baseline yet -> no event
    assert (
        detect_readiness_gate_flipped(
            readiness={"authorized": ["paper_trading"]},
            previous_authorized_set=None,
            now=FIXED_NOW,
        )
        is None
    )
    # baseline matches current -> no event
    assert (
        detect_readiness_gate_flipped(
            readiness={"authorized": ["paper_trading"]},
            previous_authorized_set=frozenset({"paper_trading"}),
            now=FIXED_NOW,
        )
        is None
    )


# ---------------------------------------------------------------------------
# detect_all integration
# ---------------------------------------------------------------------------


def test_detect_all_returns_multiple_events_in_deterministic_order():
    snapshot = {
        "latest_cycle_report": {
            "cycle_id": "cycle-42",
            "symbol": "EURUSD",
            "side": "buy",
            "lots": 0.01,
            "broker_ticket": 999,
            "receipt_verified": True,
        },
        "latest_decision": {
            "decision_id": "dec-1",
            "overall_status": "blocked",
            "blocking_gate": "pcba",
            "symbol": "USDJPY",
        },
        "loop_health": {"status": "stalled", "seconds_since_last_cycle": 600},
        "mt5_probe": {"connected": False, "account": "live-1"},
        "readiness": {"authorized": ["paper_trading", "live_trading_read"]},
    }
    previous = {
        "previous_loop_status": "running",
        "previous_mt5_connected": True,
        "previous_authorized_set": frozenset({"paper_trading"}),
    }
    events = detect_all(state_snapshot=snapshot, previous_snapshot=previous, now=FIXED_NOW)
    kinds = [e.event_kind for e in events]
    # expected detectors fired in module-defined order
    assert kinds == [
        EVENT_TRADE_EXECUTED,
        EVENT_TRADE_BLOCKED,
        EVENT_LOOP_STALLED,
        EVENT_MT5_DISCONNECTED,
        EVENT_READINESS_GATE_FLIPPED,
    ]
    # all event ids unique
    assert len(set(e.event_id for e in events)) == len(events)


def test_detect_all_empty_when_no_signals():
    assert detect_all(state_snapshot={}, previous_snapshot=None, now=FIXED_NOW) == tuple()


# ---------------------------------------------------------------------------
# Observational invariant — NO advisory language anywhere
# ---------------------------------------------------------------------------


def _all_sample_events() -> list[NotificationEvent]:
    """Build at least one event from each detector for invariant checking."""
    samples: list[NotificationEvent] = []

    samples.append(
        detect_trade_executed(
            latest_cycle_report={
                "cycle_id": "cycle-1",
                "symbol": "EURUSD",
                "side": "buy",
                "lots": 0.05,
                "broker_ticket": 111,
                "receipt_verified": True,
            },
            now=FIXED_NOW,
        )
    )
    samples.append(
        detect_trade_executed(
            latest_cycle_report={
                "cycle_id": "cycle-2",
                "symbol": "USDJPY",
                "side": "sell",
                "lots": 0.10,
                "broker_ticket": 222,
                "receipt_verified": True,
            },
            now=FIXED_NOW,
        )
    )
    samples.append(
        detect_trade_blocked(
            latest_decision={
                "decision_id": "dec-1",
                "overall_status": "blocked",
                "blocking_gate": "pcba_readiness",
                "symbol": "EURUSD",
                "reason": "live trading not authorized",
            },
            now=FIXED_NOW,
        )
    )
    samples.append(
        detect_loop_stalled(
            loop_health={
                "status": "stalled",
                "last_cycle_at": "2026-06-25T11:55:00+00:00",
                "seconds_since_last_cycle": 600,
            },
            previous_status="running",
            now=FIXED_NOW,
        )
    )
    samples.append(
        detect_loop_resumed(
            loop_health={
                "status": "running",
                "last_cycle_at": "2026-06-25T12:00:00+00:00",
            },
            previous_status="stalled",
            now=FIXED_NOW,
        )
    )
    samples.append(
        detect_mt5_disconnected(
            mt5_probe={
                "connected": False,
                "account": "live-1234567",
                "last_error": "terminal closed",
            },
            previous_connected=True,
            now=FIXED_NOW,
        )
    )
    samples.append(
        detect_readiness_gate_flipped(
            readiness={"authorized": ["paper_trading", "live_trading_read"]},
            previous_authorized_set=frozenset({"paper_trading"}),
            now=FIXED_NOW,
        )
    )
    # filter Nones in case any sample fails to fire
    return [s for s in samples if s is not None]


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_no_advisory_phrases_in_any_event(phrase: str):
    events = _all_sample_events()
    assert events, "expected at least one sample event from each detector"
    for event in events:
        haystack = f"{event.title}\n{event.body}".lower()
        assert (
            phrase not in haystack
        ), f"event {event.event_kind} contained forbidden advisory phrase {phrase!r}"


def test_sample_events_cover_every_detector():
    """Belt-and-braces: the invariant test is only meaningful if our
    sample set actually exercises every detector."""
    events = _all_sample_events()
    kinds = {e.event_kind for e in events}
    assert kinds == {
        EVENT_TRADE_EXECUTED,
        EVENT_TRADE_BLOCKED,
        EVENT_LOOP_STALLED,
        EVENT_LOOP_RESUMED,
        EVENT_MT5_DISCONNECTED,
        EVENT_READINESS_GATE_FLIPPED,
    }
