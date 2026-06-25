"""Pure observers for operator-facing notification events.

This module turns parsed cockpit state into :class:`NotificationEvent`
records that a downstream dispatcher (``push_notifications``) can ship to
subscribed devices.

Framing note (observational, never advisory):
    Every event describes what the SYSTEM DID — a trade executed, a loop
    stalled, a runtime gate flipped. Titles and bodies MUST NEVER contain
    trade-advisory language ("you should buy", "good entry", "now is the
    time", "is a buy", etc.). CAS is the operator's instrument panel, not
    a trade picker. A regression test enumerates forbidden phrases and
    asserts none appear in any event's title or body.

Design constraints:
    * Pure functions only. No disk I/O. No network. No clocks beyond the
      caller-supplied ``now``.
    * Each detector returns 0 or 1 :class:`NotificationEvent`. Missing
      or malformed input always yields ``None`` rather than raising.
    * ``event_id`` is deterministic from kind + key fields so a downstream
      deduper can recognise repeats across cycles.
    * Wiring this module into the live agent cycle is a separate slice;
      this module ships the chassis only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


# ---------------------------------------------------------------------------
# Event data shape
# ---------------------------------------------------------------------------


SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ALERT = "alert"

EVENT_TRADE_EXECUTED = "TRADE_EXECUTED"
EVENT_TRADE_BLOCKED = "TRADE_BLOCKED"
EVENT_LOOP_STALLED = "LOOP_STALLED"
EVENT_LOOP_RESUMED = "LOOP_RESUMED"
EVENT_PCBA_BLOCKED = "PCBA_BLOCKED"
EVENT_STRATEGY_PROMOTED = "STRATEGY_PROMOTED"
EVENT_STRATEGY_DEMOTED = "STRATEGY_DEMOTED"
EVENT_MT5_DISCONNECTED = "MT5_DISCONNECTED"
EVENT_READINESS_GATE_FLIPPED = "READINESS_GATE_FLIPPED"
EVENT_MISSED_DECISION_QUORUM = "MISSED_DECISION_QUORUM"


@dataclass(frozen=True)
class NotificationEvent:
    """An observation worth surfacing to the operator.

    Attributes:
        event_kind: One of the ``EVENT_*`` constants in this module.
        event_id: Deterministic short hash derived from kind + load-bearing
            fields. Two snapshots describing the same observation produce
            the same ``event_id``, so the dispatcher can dedupe.
        title: One-line observational headline, plain text.
        body: Two-to-three-sentence observational summary, plain text.
            Never advisory.
        severity: ``"info"`` | ``"warning"`` | ``"alert"``.
        detected_at_iso: UTC ISO-8601 timestamp the detector fired.
        payload: Structured fields the client UI can render without
            re-parsing the title/body text.
    """

    event_kind: str
    event_id: str
    title: str
    body: str
    severity: str
    detected_at_iso: str
    payload: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow_iso(now: Optional[datetime] = None) -> str:
    moment = now if now is not None else datetime.now(tz=timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.replace(microsecond=0).isoformat()


def _event_id(kind: str, *parts: Any) -> str:
    """Deterministic 16-hex-char event id derived from kind + key fields."""
    raw = "|".join([kind] + [str(p) for p in parts])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Detector: TRADE_EXECUTED
# ---------------------------------------------------------------------------


def detect_trade_executed(
    *,
    latest_cycle_report: Optional[Mapping[str, Any]],
    previous_cycle_report: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Optional[NotificationEvent]:
    """Detect when a cycle EXECUTED a trade.

    A cycle counts as having executed when (a) the cycle dict carries a
    truthy ``broker_ticket`` (real broker fill) and (b) ``receipt_verified``
    is truthy. ``previous_cycle_report`` deduplicates: if the same
    ``cycle_id`` was already observed and already had an executed trade,
    this returns ``None``.
    """
    if not isinstance(latest_cycle_report, Mapping):
        return None

    cycle_id = _safe_str(latest_cycle_report.get("cycle_id"))
    if not cycle_id:
        return None

    broker_ticket = latest_cycle_report.get("broker_ticket")
    receipt_verified = bool(latest_cycle_report.get("receipt_verified"))
    if not broker_ticket or not receipt_verified:
        return None

    # Dedupe against previous snapshot — same cycle, same outcome.
    if isinstance(previous_cycle_report, Mapping):
        prev_id = _safe_str(previous_cycle_report.get("cycle_id"))
        prev_ticket = previous_cycle_report.get("broker_ticket")
        if prev_id == cycle_id and prev_ticket == broker_ticket:
            return None

    side = _safe_str(latest_cycle_report.get("side"), "?").upper()
    symbol = _safe_str(latest_cycle_report.get("symbol"), "?").upper()
    lots = latest_cycle_report.get("lots", "?")
    ticket_str = _safe_str(broker_ticket)

    detected_at = _utcnow_iso(now)
    title = f"Trade executed: {side} {symbol} {lots} lots"
    body = (
        f"Cycle {cycle_id} executed a {side} {symbol} order for {lots} lots; "
        f"broker ticket {ticket_str}. Receipt verified."
    )

    return NotificationEvent(
        event_kind=EVENT_TRADE_EXECUTED,
        event_id=_event_id(EVENT_TRADE_EXECUTED, cycle_id, ticket_str),
        title=title,
        body=body,
        severity=SEVERITY_INFO,
        detected_at_iso=detected_at,
        payload={
            "cycle_id": cycle_id,
            "symbol": symbol,
            "side": side,
            "lots": lots,
            "broker_ticket": ticket_str,
        },
    )


# ---------------------------------------------------------------------------
# Detector: TRADE_BLOCKED
# ---------------------------------------------------------------------------


def detect_trade_blocked(
    *,
    latest_decision: Optional[Mapping[str, Any]],
    now: Optional[datetime] = None,
) -> Optional[NotificationEvent]:
    """Detect when the latest decision was blocked by a gate.

    Fires when ``overall_status`` is ``"blocked"``. The blocking gate's
    name is included in the title when the decision exposes it as
    ``blocking_gate`` or as the first entry of ``failed_gates``.
    """
    if not isinstance(latest_decision, Mapping):
        return None

    status = _safe_str(latest_decision.get("overall_status")).lower()
    if status != "blocked":
        return None

    decision_id = _safe_str(latest_decision.get("decision_id"))
    if not decision_id:
        return None

    blocking_gate = latest_decision.get("blocking_gate")
    if not blocking_gate:
        failed_gates = latest_decision.get("failed_gates")
        if isinstance(failed_gates, (list, tuple)) and failed_gates:
            blocking_gate = failed_gates[0]
    gate_name = _safe_str(blocking_gate, "unknown gate")

    symbol = _safe_str(latest_decision.get("symbol"), "?").upper()
    reason = _safe_str(latest_decision.get("reason"), "no reason recorded")

    detected_at = _utcnow_iso(now)
    title = f"Trade blocked by {gate_name}"
    body = (
        f"Decision {decision_id} on {symbol} was blocked by gate "
        f"{gate_name}. Recorded reason: {reason}."
    )

    return NotificationEvent(
        event_kind=EVENT_TRADE_BLOCKED,
        event_id=_event_id(EVENT_TRADE_BLOCKED, decision_id, gate_name),
        title=title,
        body=body,
        severity=SEVERITY_WARNING,
        detected_at_iso=detected_at,
        payload={
            "decision_id": decision_id,
            "symbol": symbol,
            "blocking_gate": gate_name,
            "reason": reason,
        },
    )


# ---------------------------------------------------------------------------
# Detector: LOOP_STALLED
# ---------------------------------------------------------------------------


def detect_loop_stalled(
    *,
    loop_health: Optional[Mapping[str, Any]],
    previous_status: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[NotificationEvent]:
    """Detect when loop transitioned from ``"running"`` to ``"stalled"``."""
    if not isinstance(loop_health, Mapping):
        return None

    current = _safe_str(loop_health.get("status")).lower()
    if current != "stalled":
        return None
    prior = _safe_str(previous_status).lower() if previous_status is not None else ""
    if prior != "running":
        return None

    seconds_since = loop_health.get("seconds_since_last_cycle")
    last_cycle_at = _safe_str(loop_health.get("last_cycle_at"), "unknown")

    detected_at = _utcnow_iso(now)
    title = "Autonomous loop stalled"
    body = (
        "The autonomous trading loop stopped advancing. Last cycle observed at "
        f"{last_cycle_at}; {seconds_since}s since last heartbeat."
    )

    return NotificationEvent(
        event_kind=EVENT_LOOP_STALLED,
        event_id=_event_id(EVENT_LOOP_STALLED, last_cycle_at, seconds_since),
        title=title,
        body=body,
        severity=SEVERITY_ALERT,
        detected_at_iso=detected_at,
        payload={
            "previous_status": prior,
            "current_status": current,
            "last_cycle_at": last_cycle_at,
            "seconds_since_last_cycle": seconds_since,
        },
    )


# ---------------------------------------------------------------------------
# Detector: LOOP_RESUMED
# ---------------------------------------------------------------------------


def detect_loop_resumed(
    *,
    loop_health: Optional[Mapping[str, Any]],
    previous_status: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[NotificationEvent]:
    """Detect when loop transitioned from stalled/unknown to running."""
    if not isinstance(loop_health, Mapping):
        return None

    current = _safe_str(loop_health.get("status")).lower()
    if current != "running":
        return None
    prior = _safe_str(previous_status).lower() if previous_status is not None else ""
    if prior not in {"stalled", "unknown"}:
        return None

    last_cycle_at = _safe_str(loop_health.get("last_cycle_at"), "unknown")

    detected_at = _utcnow_iso(now)
    title = "Autonomous loop resumed"
    body = (
        "The autonomous trading loop is advancing again after being "
        f"{prior}. Most recent cycle observed at {last_cycle_at}."
    )

    return NotificationEvent(
        event_kind=EVENT_LOOP_RESUMED,
        event_id=_event_id(EVENT_LOOP_RESUMED, last_cycle_at, prior),
        title=title,
        body=body,
        severity=SEVERITY_INFO,
        detected_at_iso=detected_at,
        payload={
            "previous_status": prior,
            "current_status": current,
            "last_cycle_at": last_cycle_at,
        },
    )


# ---------------------------------------------------------------------------
# Detector: MT5_DISCONNECTED
# ---------------------------------------------------------------------------


def detect_mt5_disconnected(
    *,
    mt5_probe: Optional[Mapping[str, Any]],
    previous_connected: Optional[bool] = None,
    now: Optional[datetime] = None,
) -> Optional[NotificationEvent]:
    """Detect when MT5 connection transitioned from connected to disconnected."""
    if not isinstance(mt5_probe, Mapping):
        return None

    connected_value = mt5_probe.get("connected")
    if connected_value is None:
        return None
    currently_connected = bool(connected_value)
    if currently_connected:
        return None
    if previous_connected is not True:
        return None

    account = _safe_str(mt5_probe.get("account"), "unknown account")
    error = _safe_str(mt5_probe.get("last_error"), "no error message recorded")

    detected_at = _utcnow_iso(now)
    title = "MT5 broker connection lost"
    body = (
        f"The MT5 broker bridge for account {account} is no longer connected. "
        f"Last reported error: {error}."
    )

    return NotificationEvent(
        event_kind=EVENT_MT5_DISCONNECTED,
        event_id=_event_id(EVENT_MT5_DISCONNECTED, account, detected_at),
        title=title,
        body=body,
        severity=SEVERITY_ALERT,
        detected_at_iso=detected_at,
        payload={
            "account": account,
            "previous_connected": True,
            "currently_connected": False,
            "last_error": error,
        },
    )


# ---------------------------------------------------------------------------
# Detector: READINESS_GATE_FLIPPED
# ---------------------------------------------------------------------------


def detect_readiness_gate_flipped(
    *,
    readiness: Optional[Mapping[str, Any]],
    previous_authorized_set: Optional[frozenset[str]] = None,
    now: Optional[datetime] = None,
) -> Optional[NotificationEvent]:
    """Detect runtime gates that flipped authorization since last check.

    ``readiness`` is expected to expose either an ``authorized`` list or
    an ``authorized_capabilities`` list of capability names. The detector
    compares it against ``previous_authorized_set`` and fires when any
    name was added or removed. If ``previous_authorized_set`` is None,
    no event fires (first observation establishes baseline).
    """
    if not isinstance(readiness, Mapping):
        return None
    if previous_authorized_set is None:
        return None

    authorized_raw = readiness.get("authorized")
    if authorized_raw is None:
        authorized_raw = readiness.get("authorized_capabilities")
    if not isinstance(authorized_raw, (list, tuple, set, frozenset)):
        return None

    current_set = frozenset(_safe_str(item) for item in authorized_raw if _safe_str(item))
    if current_set == previous_authorized_set:
        return None

    newly_authorized = sorted(current_set - previous_authorized_set)
    newly_revoked = sorted(previous_authorized_set - current_set)
    if not newly_authorized and not newly_revoked:
        return None

    detected_at = _utcnow_iso(now)
    parts: list[str] = []
    if newly_authorized:
        parts.append(f"authorized: {', '.join(newly_authorized)}")
    if newly_revoked:
        parts.append(f"revoked: {', '.join(newly_revoked)}")
    summary = "; ".join(parts)

    title = "Runtime readiness gate changed"
    body = (
        "Runtime readiness changed since the last observation. "
        f"Differences observed — {summary}."
    )

    return NotificationEvent(
        event_kind=EVENT_READINESS_GATE_FLIPPED,
        event_id=_event_id(
            EVENT_READINESS_GATE_FLIPPED,
            ",".join(newly_authorized),
            ",".join(newly_revoked),
        ),
        title=title,
        body=body,
        severity=SEVERITY_INFO,
        detected_at_iso=detected_at,
        payload={
            "newly_authorized": newly_authorized,
            "newly_revoked": newly_revoked,
            "current_authorized": sorted(current_set),
        },
    )


# ---------------------------------------------------------------------------
# detect_all — orchestrator
# ---------------------------------------------------------------------------


def detect_all(
    *,
    state_snapshot: Mapping[str, Any],
    previous_snapshot: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> tuple[NotificationEvent, ...]:
    """Run all detectors against a single state snapshot.

    ``state_snapshot`` is a dict with keys matching the kwargs of the
    individual detectors:

    * ``latest_cycle_report`` -> :func:`detect_trade_executed`
    * ``latest_decision``     -> :func:`detect_trade_blocked`
    * ``loop_health``         -> :func:`detect_loop_stalled` /
                                 :func:`detect_loop_resumed`
    * ``mt5_probe``           -> :func:`detect_mt5_disconnected`
    * ``readiness``           -> :func:`detect_readiness_gate_flipped`

    ``previous_snapshot`` carries the corresponding previous values plus
    bookkeeping keys ``previous_loop_status``, ``previous_mt5_connected``,
    and ``previous_authorized_set`` that the trigger system maintains
    across calls.

    Returns the fired events in a deterministic order — detector ordering
    by definition, with at most one event per detector.
    """
    if not isinstance(state_snapshot, Mapping):
        return tuple()

    previous = previous_snapshot if isinstance(previous_snapshot, Mapping) else {}

    results: list[NotificationEvent] = []

    executed = detect_trade_executed(
        latest_cycle_report=state_snapshot.get("latest_cycle_report"),
        previous_cycle_report=previous.get("latest_cycle_report"),
        now=now,
    )
    if executed is not None:
        results.append(executed)

    blocked = detect_trade_blocked(
        latest_decision=state_snapshot.get("latest_decision"),
        now=now,
    )
    if blocked is not None:
        results.append(blocked)

    stalled = detect_loop_stalled(
        loop_health=state_snapshot.get("loop_health"),
        previous_status=previous.get("previous_loop_status"),
        now=now,
    )
    if stalled is not None:
        results.append(stalled)

    resumed = detect_loop_resumed(
        loop_health=state_snapshot.get("loop_health"),
        previous_status=previous.get("previous_loop_status"),
        now=now,
    )
    if resumed is not None:
        results.append(resumed)

    disconnected = detect_mt5_disconnected(
        mt5_probe=state_snapshot.get("mt5_probe"),
        previous_connected=previous.get("previous_mt5_connected"),
        now=now,
    )
    if disconnected is not None:
        results.append(disconnected)

    prev_auth = previous.get("previous_authorized_set")
    if isinstance(prev_auth, (list, tuple, set, frozenset)):
        prev_auth = frozenset(_safe_str(item) for item in prev_auth if _safe_str(item))
    flipped = detect_readiness_gate_flipped(
        readiness=state_snapshot.get("readiness"),
        previous_authorized_set=prev_auth if isinstance(prev_auth, frozenset) else None,
        now=now,
    )
    if flipped is not None:
        results.append(flipped)

    return tuple(results)


__all__ = [
    "EVENT_LOOP_RESUMED",
    "EVENT_LOOP_STALLED",
    "EVENT_MISSED_DECISION_QUORUM",
    "EVENT_MT5_DISCONNECTED",
    "EVENT_PCBA_BLOCKED",
    "EVENT_READINESS_GATE_FLIPPED",
    "EVENT_STRATEGY_DEMOTED",
    "EVENT_STRATEGY_PROMOTED",
    "EVENT_TRADE_BLOCKED",
    "EVENT_TRADE_EXECUTED",
    "NotificationEvent",
    "SEVERITY_ALERT",
    "SEVERITY_INFO",
    "SEVERITY_WARNING",
    "detect_all",
    "detect_loop_resumed",
    "detect_loop_stalled",
    "detect_mt5_disconnected",
    "detect_readiness_gate_flipped",
    "detect_trade_blocked",
    "detect_trade_executed",
]
