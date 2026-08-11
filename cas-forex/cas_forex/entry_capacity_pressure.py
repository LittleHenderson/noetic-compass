"""Durable evidence that entry candidates are starving at a position-count cap.

This module observes deterministic entry preflight reports.  It never changes a
dial or authorizes an order.  Its job is to distinguish one ordinary cap block
from repeated, cross-market capacity starvation while the account is using only
a small fraction of its separate exposure envelope.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "entry-capacity-pressure.json"
REPORT_KIND = "cas_forex_entry_capacity_pressure"
WINDOW_SECONDS = 3600
MIN_CAP_BLOCK_EVENTS = 3
MIN_DISTINCT_SYMBOLS = 2
MAX_LOW_EXPOSURE_UTILIZATION_PCT = 25.0
MAX_RETAINED_EVENTS = 120

_lock = threading.RLock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(
        f"{path.suffix}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    tmp.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _authority_snapshot() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        from cas_forex.ai_control_authority import get_authority

        snapshot = dict(get_authority().snapshot() or {})
    except Exception:
        return {}, {}
    surface = snapshot.get("control_surface")
    surface = surface if isinstance(surface, Mapping) else {}
    values = surface.get("values")
    bounds = surface.get("bounds")
    return (
        dict(values) if isinstance(values, Mapping) else {},
        dict(bounds) if isinstance(bounds, Mapping) else {},
    )


def _owner_override_keys() -> set[str]:
    try:
        from cas_forex.risk_control import explicit_override_keys

        return {str(value) for value in explicit_override_keys()}
    except Exception:
        return set()


def _candidate_event(
    row: Mapping[str, Any],
    *,
    generated_at: str,
    mode: str,
) -> dict[str, Any] | None:
    plan = row.get("operator_sizing_plan")
    plan = plan if isinstance(plan, Mapping) else {}
    blockers = [
        str(value).strip()
        for value in (plan.get("blockers") or [])
        if str(value or "").strip()
    ]
    if not blockers:
        reason = str(row.get("reason") or "").strip()
        if reason:
            blockers = [reason]
    normalized = [value.lower() for value in blockers]
    cap_only = bool(normalized) and all(
        "open-position cap" in value or "open position cap" in value
        for value in normalized
    )
    if not cap_only:
        return None

    portfolio = plan.get("portfolio_snapshot")
    portfolio = portfolio if isinstance(portfolio, Mapping) else {}
    caps = plan.get("cap_snapshot")
    caps = caps if isinstance(caps, Mapping) else {}
    identity_payload = {
        "generated_at": generated_at,
        "intent_id": row.get("intent_id"),
        "symbol": row.get("symbol"),
        "timeframe": row.get("timeframe"),
        "direction": row.get("direction"),
    }
    identity = str(row.get("intent_id") or "").strip() or hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return {
        "event_id": identity,
        "generated_at": generated_at,
        "mode": str(mode or "UNKNOWN").upper(),
        "intent_id": row.get("intent_id"),
        "symbol": row.get("symbol"),
        "timeframe": row.get("timeframe"),
        "direction": row.get("direction"),
        "entry_lane": row.get("entry_lane"),
        "candidate_status": row.get("status"),
        "blockers": blockers,
        "open_position_count": _integer(portfolio.get("open_position_count")),
        "max_open_position_count": _integer(caps.get("max_open_position_count")),
        "total_exposure_lots": _number(portfolio.get("total_exposure_lots")),
        "max_total_exposure_lots": _number(caps.get("max_total_exposure_lots")),
        "minimum_lot_risk_usd": _number(row.get("minimum_lot_risk_usd")),
        "minimum_lot_risk_pct_equity": _number(
            row.get("minimum_lot_risk_pct_equity")
        ),
        "max_feasible_lots_before_position_cap": _number(
            row.get("max_feasible_lots")
        ),
        "broker_min_lot": _number(row.get("broker_min_lot")),
    }


def _candidate_sizing_snapshot(row: Mapping[str, Any]) -> dict[str, Any]:
    plan = row.get("operator_sizing_plan")
    plan = plan if isinstance(plan, Mapping) else {}
    portfolio = plan.get("portfolio_snapshot")
    portfolio = portfolio if isinstance(portfolio, Mapping) else {}
    caps = plan.get("cap_snapshot")
    caps = caps if isinstance(caps, Mapping) else {}
    if not portfolio and not caps:
        return {}
    return {
        "open_position_count": _integer(portfolio.get("open_position_count")),
        "max_open_position_count": _integer(caps.get("max_open_position_count")),
        "total_exposure_lots": _number(portfolio.get("total_exposure_lots")),
        "max_total_exposure_lots": _number(caps.get("max_total_exposure_lots")),
    }


def _bound_value(bounds: Mapping[str, Any], key: str, fallback: int) -> int:
    raw = bounds.get(key)
    raw = raw if isinstance(raw, Mapping) else {}
    value = _integer(raw.get("max"))
    return value if value is not None else fallback


def record_entry_capacity_observation(
    entry_risk_report: Mapping[str, Any] | None,
    *,
    mode: str,
    state_path: Path | str = DEFAULT_STATE_PATH,
    now: datetime | None = None,
    control_values: Mapping[str, Any] | None = None,
    control_bounds: Mapping[str, Any] | None = None,
    explicit_owner_override_keys: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Record one cycle and return bounded capacity-pressure evidence."""

    timestamp = (now or _utc_now()).astimezone(timezone.utc)
    report = dict(entry_risk_report or {})
    generated_at = str(report.get("generated_at") or timestamp.isoformat())
    target = Path(state_path)
    with _lock:
        previous = _load(target)
        events_by_id = {
            str(row.get("event_id") or ""): dict(row)
            for row in (previous.get("events") or [])
            if isinstance(row, Mapping) and str(row.get("event_id") or "")
        }
        current_cycle_snapshot: dict[str, Any] = {}
        current_cycle_cap_events: list[dict[str, Any]] = []
        for raw in report.get("candidates") or []:
            if not isinstance(raw, Mapping):
                continue
            sizing_snapshot = _candidate_sizing_snapshot(raw)
            if sizing_snapshot:
                current_cycle_snapshot = sizing_snapshot
            event = _candidate_event(raw, generated_at=generated_at, mode=mode)
            if event is not None:
                events_by_id[str(event["event_id"])] = event
                current_cycle_cap_events.append(event)

        cutoff = timestamp - timedelta(seconds=WINDOW_SECONDS)
        events = [
            row
            for row in events_by_id.values()
            if (_parse_time(row.get("generated_at")) or timestamp) >= cutoff
        ]
        events.sort(key=lambda row: str(row.get("generated_at") or ""))
        events = events[-MAX_RETAINED_EVENTS:]

        resolved_values, resolved_bounds = _authority_snapshot()
        values = dict(control_values or resolved_values)
        bounds = dict(control_bounds or resolved_bounds)
        override_keys = {
            str(value)
            for value in (
                explicit_owner_override_keys
                if explicit_owner_override_keys is not None
                else _owner_override_keys()
            )
        }
        current_cap = _integer(values.get("max_concurrent_trades"))
        if current_cap is None and events:
            current_cap = _integer(events[-1].get("max_open_position_count"))
        matching_events = [
            row
            for row in events
            if current_cap is None
            or _integer(row.get("max_open_position_count")) == current_cap
        ]
        current_cycle_matches_cap = bool(
            current_cycle_snapshot
            and (
                current_cap is None
                or _integer(
                    current_cycle_snapshot.get("max_open_position_count")
                )
                == current_cap
            )
        )
        latest = (
            current_cycle_snapshot
            if current_cycle_matches_cap
            else matching_events[-1]
            if matching_events
            else {}
        )
        open_count = _integer(latest.get("open_position_count"))
        total_exposure = _number(latest.get("total_exposure_lots"))
        max_exposure = _number(latest.get("max_total_exposure_lots"))
        if max_exposure is None:
            max_exposure = _number(values.get("max_total_exposure_lots"))
        exposure_utilization_pct = (
            round(100.0 * float(total_exposure) / float(max_exposure), 6)
            if total_exposure is not None and max_exposure not in (None, 0.0)
            else None
        )
        symbols = sorted(
            {str(row.get("symbol")) for row in matching_events if row.get("symbol")}
        )
        timeframes = sorted(
            {
                str(row.get("timeframe"))
                for row in matching_events
                if row.get("timeframe")
            }
        )
        owner_override = "max_concurrent_trades" in override_keys
        low_exposure = (
            exposure_utilization_pct is not None
            and exposure_utilization_pct <= MAX_LOW_EXPOSURE_UTILIZATION_PCT
        )
        cap_full = (
            current_cap is not None
            and open_count is not None
            and open_count >= current_cap
        )
        repeated = len(matching_events) >= MIN_CAP_BLOCK_EVENTS
        cross_market = len(symbols) >= MIN_DISTINCT_SYMBOLS
        owner_max = _bound_value(bounds, "max_concurrent_trades", 50)
        proposed_cap = (
            min(owner_max, current_cap + 1) if current_cap is not None else None
        )
        review_allowed = bool(
            repeated
            and cross_market
            and cap_full
            and low_exposure
            and not owner_override
            and proposed_cap is not None
            and current_cap is not None
            and proposed_cap > current_cap
        )
        if review_allowed:
            status = "POSITION_CAPACITY_STARVATION"
        elif (
            current_cycle_matches_cap
            and not current_cycle_cap_events
            and matching_events
        ):
            status = "POSITION_CAPACITY_PRESSURE_CLEARED"
        elif matching_events:
            status = "POSITION_CAPACITY_PRESSURE_OBSERVED"
        else:
            status = "NO_POSITION_CAPACITY_PRESSURE"

        blockers: list[str] = []
        if matching_events and not repeated:
            blockers.append(
                f"need at least {MIN_CAP_BLOCK_EVENTS} fresh cap-blocked candidates"
            )
        if matching_events and not cross_market:
            blockers.append(
                f"need candidates from at least {MIN_DISTINCT_SYMBOLS} symbols"
            )
        if matching_events and not cap_full:
            blockers.append("current open-position count is no longer at the cap")
        if matching_events and not low_exposure:
            blockers.append(
                "total exposure is not low enough for an autonomous one-slot review"
            )
        if owner_override:
            blockers.append("an explicit owner max_concurrent_trades override is active")
        if proposed_cap is not None and current_cap is not None and proposed_cap <= current_cap:
            blockers.append("the current cap already reaches the owner envelope")

        substantive = {
            "status": status,
            "mode": str(mode or "UNKNOWN").upper(),
            "window_seconds": WINDOW_SECONDS,
            "cap_block_event_count": len(matching_events),
            "distinct_symbol_count": len(symbols),
            "symbols": symbols,
            "timeframes": timeframes,
            "current_open_position_count": open_count,
            "current_max_open_position_count": current_cap,
            "current_total_exposure_lots": total_exposure,
            "current_max_total_exposure_lots": max_exposure,
            "exposure_utilization_pct": exposure_utilization_pct,
            "low_exposure_threshold_pct": MAX_LOW_EXPOSURE_UTILIZATION_PCT,
            "explicit_owner_override_active": owner_override,
            "autonomous_one_slot_review_allowed": review_allowed,
            "recommended_review_cap": proposed_cap if review_allowed else None,
            "review_blockers": blockers,
            "current_cycle_candidate_count": len(report.get("candidates") or []),
            "current_cycle_cap_only_block_count": len(current_cycle_cap_events),
            "current_cycle_sizing_snapshot": current_cycle_snapshot,
            "latest_blocked_candidate": {
                key: latest.get(key)
                for key in (
                    "generated_at",
                    "intent_id",
                    "symbol",
                    "timeframe",
                    "direction",
                    "entry_lane",
                    "minimum_lot_risk_usd",
                    "minimum_lot_risk_pct_equity",
                    "max_feasible_lots_before_position_cap",
                    "broker_min_lot",
                )
                if key in latest
            },
        }
        event_hash = hashlib.sha256(
            json.dumps(substantive, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        payload = {
            "report_kind": REPORT_KIND,
            "generated_at": timestamp.isoformat(),
            **substantive,
            "event_hash": event_hash,
            "events": events,
            "broker_order_touched": False,
            "orders_placed": False,
            "money_moved": False,
            "claim_boundary": (
                "Capacity-pressure evidence may focus an autonomous Operator dial "
                "review. It cannot change a cap, approve an entry, close a position, "
                "touch a broker, or move money. Any cap change remains an explicit "
                "Operator decision inside the owner envelope, and every later order "
                "must pass fresh edge, sizing, risk, and execution guards."
            ),
        }
        _write(target, payload)
        return payload


def load_entry_capacity_pressure(
    state_path: Path | str = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Load the latest bounded capacity-pressure snapshot."""

    payload = _load(Path(state_path))
    if payload:
        return payload
    return {
        "report_kind": REPORT_KIND,
        "generated_at": None,
        "status": "NO_POSITION_CAPACITY_PRESSURE",
        "cap_block_event_count": 0,
        "distinct_symbol_count": 0,
        "symbols": [],
        "timeframes": [],
        "autonomous_one_slot_review_allowed": False,
        "recommended_review_cap": None,
        "events": [],
        "broker_order_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "claim_boundary": (
            "No durable capacity-pressure evidence has been recorded yet."
        ),
    }
