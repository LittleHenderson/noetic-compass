"""Read-only binding between WASTE direction edges and realized paper outcomes.

Direction learning is not allowed to become adaptation authority merely because
the edge gate liked a setup. This report joins WASTE PASS-token direction cycles
to paper/demo dispatch attempts and closed MT5 paper/demo history, so future
adaptation can rely on realized outcomes instead of unclosed hypotheses.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.mt5_deal_history_ingest import (
    DEFAULT_OUTPUT_DIR as DEFAULT_MT5_DEAL_HISTORY_DIR,
    load_latest_mt5_deal_history_ingest_report,
)
from cas_forex.order_attempt_audit import DEFAULT_STATE_PATH as DEFAULT_ORDER_ATTEMPT_STATE_PATH
from cas_forex.time_utils import utc_now
from cas_forex.waste_cycle_audit import DEFAULT_AUDIT_PATH as DEFAULT_WASTE_AUDIT_PATH

REPORT_KIND = "cas_forex_waste_direction_outcome_binding"
STATUS_NO_CONFIRMED_EDGE = "WASTE_DIRECTION_OUTCOME_NO_CONFIRMED_EDGE"
STATUS_AWAITING_EXECUTION = "WASTE_DIRECTION_OUTCOME_AWAITING_PAPER_EXECUTION"
STATUS_AWAITING_CLOSED_HISTORY = "WASTE_DIRECTION_OUTCOME_AWAITING_CLOSED_HISTORY"
STATUS_COLLECTING = "WASTE_DIRECTION_OUTCOME_COLLECTING"
STATUS_READY = "WASTE_DIRECTION_OUTCOME_READY_FOR_PROMOTION_REVIEW"
DEFAULT_MIN_BOUND_OUTCOMES_FOR_PROMOTION = 5

CLAIM_BOUNDARY = (
    "WASTE direction outcome binding is read-only PAPER/DEMO evidence joining. "
    "It can bind PASS-token direction cycles to paper/demo order attempts and "
    "closed MT5 paper/demo outcomes, but it does not place orders, close "
    "positions, create broker ACCEPT, create owner ACCEPT, authorize live "
    "trading, mint edge tokens, lower thresholds, deposit, withdraw, move "
    "bank/card money, automate payouts, or mark evidence LICENSED."
)


def build_waste_direction_outcome_binding(
    *,
    cycles: Iterable[Mapping[str, Any]] | None = None,
    attempts: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
    history_report: Mapping[str, Any] | None = None,
    audit_path: Path | str = DEFAULT_WASTE_AUDIT_PATH,
    order_attempt_state_path: Path | str = DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    history_report_dir: Path | str = DEFAULT_MT5_DEAL_HISTORY_DIR,
    max_cycles: int = 250,
    min_bound_outcomes_for_promotion: int = DEFAULT_MIN_BOUND_OUTCOMES_FOR_PROMOTION,
) -> dict[str, Any]:
    """Bind confirmed WASTE direction samples to realized paper/demo outcomes."""

    cycle_rows = _cycle_rows(
        list(cycles) if cycles is not None else _load_cycles(audit_path, max_cycles=max_cycles)
    )
    confirmed_cycles = [row for row in cycle_rows if row.get("edge_confirmed")]
    attempt_rows = _attempt_rows(
        attempts if attempts is not None else _load_attempts(order_attempt_state_path)
    )
    history = dict(history_report) if history_report is not None else _latest_history(history_report_dir)
    history_rows = _history_rows(history)

    attempts_by_decision = _index_by(attempt_rows, "decision_ref")
    attempts_by_order = _index_by(attempt_rows, "order_id")
    history_by_ticket = _index_by(history_rows, "broker_ticket")

    bound_rows: list[dict[str, Any]] = []
    unbound_confirmed_rows: list[dict[str, Any]] = []
    executed_confirmed = 0
    for row in confirmed_cycles:
        attempt = _matching_attempt(row, attempts_by_decision, attempts_by_order)
        ticket = _broker_ticket(row, attempt)
        history_row = history_by_ticket.get(ticket) if ticket else None
        if attempt and bool(attempt.get("executed", False)):
            executed_confirmed += 1
        if attempt and history_row and _paper_demo_history(history_row):
            bound_rows.append(_bound_row(row, attempt, history_row))
        else:
            unbound_confirmed_rows.append(
                _unbound_row(row, attempt=attempt, broker_ticket=ticket, history_row=history_row)
            )

    net_pnl = round(sum(_float(row.get("net_pnl"), 0.0) for row in bound_rows), 6)
    profitable = [row for row in bound_rows if _float(row.get("net_pnl"), 0.0) > 0.0]
    losing = [row for row in bound_rows if _float(row.get("net_pnl"), 0.0) < 0.0]
    flat = [row for row in bound_rows if _float(row.get("net_pnl"), 0.0) == 0.0]
    min_bound = max(1, int(min_bound_outcomes_for_promotion))
    outcome_ready = len(bound_rows) >= min_bound and net_pnl > 0.0
    status = _status(
        confirmed_count=len(confirmed_cycles),
        executed_count=executed_confirmed,
        history_count=len(history_rows),
        bound_count=len(bound_rows),
        outcome_ready=outcome_ready,
    )

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "read_only": True,
        "dry_run": True,
        "paper_only": True,
        "outcome_ready_for_promotion": outcome_ready,
        "min_bound_outcomes_for_promotion": min_bound,
        "direction_rows": len(cycle_rows),
        "confirmed_direction_count": len(confirmed_cycles),
        "executed_confirmed_count": executed_confirmed,
        "closed_history_count": len(history_rows),
        "bound_outcome_count": len(bound_rows),
        "unbound_confirmed_count": len(unbound_confirmed_rows),
        "bound_outcomes_needed": max(0, min_bound - len(bound_rows)),
        "profitable_bound_count": len(profitable),
        "losing_bound_count": len(losing),
        "flat_bound_count": len(flat),
        "net_paper_pnl": net_pnl,
        "avg_bound_pnl": round(net_pnl / len(bound_rows), 6) if bound_rows else 0.0,
        "direction_counts": dict(Counter(str(row.get("direction") or "UNKNOWN") for row in bound_rows)),
        "profile_counts": dict(Counter(str(row.get("profile") or "UNKNOWN") for row in bound_rows)),
        "paper_demo_history_status": history.get("ingest_status"),
        "history_account_mode": history.get("account_mode"),
        "history_report_path": history.get("report_path"),
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "bound_rows": bound_rows[-10:],
        "unbound_confirmed_rows": unbound_confirmed_rows[-10:],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, len(bound_rows), max(0, min_bound - len(bound_rows))),
    }


def _load_cycles(audit_path: Path | str, *, max_cycles: int) -> list[dict[str, Any]]:
    path = Path(audit_path)
    if not path.exists():
        return []
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(max_cycles)):]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


def _load_attempts(state_path: Path | str) -> list[dict[str, Any]]:
    path = Path(state_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    attempts = payload.get("attempts") if isinstance(payload, Mapping) else {}
    if not isinstance(attempts, Mapping):
        return []
    return [dict(row) for row in attempts.values() if isinstance(row, Mapping)]


def _latest_history(report_dir: Path | str) -> dict[str, Any]:
    try:
        return load_latest_mt5_deal_history_ingest_report(report_dir)
    except Exception as exc:
        return {
            "report_kind": "cas_forex_mt5_deal_history_ingest_report",
            "ingest_status": "UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
            "history_records": [],
        }


def _cycle_rows(cycles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cycle in cycles:
        candidate = _mapping(cycle.get("candidate"))
        edge = _mapping(cycle.get("edge"))
        direction = _direction(candidate.get("direction"))
        decision_ref = str(candidate.get("decision_ref") or "")
        if direction not in {"LONG", "SHORT"} or not decision_ref:
            continue
        rows.append(
            {
                "cycle_id": cycle.get("cycle_id"),
                "generated_at": cycle.get("generated_at"),
                "decision": cycle.get("decision"),
                "symbol": candidate.get("symbol"),
                "timeframe": candidate.get("timeframe"),
                "direction": direction,
                "profile": _profile(candidate),
                "decision_ref": decision_ref,
                "order_id": f"waste-{decision_ref}",
                "edge_status": edge.get("status"),
                "edge_confirmed": edge.get("status") == "PASS" and bool(edge.get("has_edge_token", False)),
                "measured_win_prob": edge.get("measured_win_prob"),
                "threshold": edge.get("threshold"),
                "execute_result": _mapping(cycle.get("execute_result")),
            }
        )
    return rows


def _attempt_rows(raw: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = raw.values() if isinstance(raw, Mapping) else raw
    return [dict(row) for row in values if isinstance(row, Mapping)]


def _history_rows(history_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = history_report.get("history_records") if isinstance(history_report.get("history_records"), list) else []
    return [dict(row) for row in rows if isinstance(row, Mapping) and _paper_demo_history(row)]


def _matching_attempt(
    cycle: Mapping[str, Any],
    attempts_by_decision: Mapping[str, Mapping[str, Any]],
    attempts_by_order: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    decision_ref = str(cycle.get("decision_ref") or "")
    order_id = str(cycle.get("order_id") or "")
    attempt = attempts_by_decision.get(decision_ref) or attempts_by_order.get(order_id)
    return dict(attempt) if isinstance(attempt, Mapping) else None


def _bound_row(cycle: Mapping[str, Any], attempt: Mapping[str, Any], history: Mapping[str, Any]) -> dict[str, Any]:
    net_pnl = _float(history.get("profit"), 0.0)
    return {
        "binding_id": stable_ledger_id(
            "waste-direction-outcome",
            cycle.get("cycle_id"),
            cycle.get("decision_ref"),
            history.get("broker_ticket") or history.get("ticket"),
            net_pnl,
        ),
        "cycle_id": cycle.get("cycle_id"),
        "decision_ref": cycle.get("decision_ref"),
        "order_id": attempt.get("order_id") or cycle.get("order_id"),
        "broker_ticket": history.get("broker_ticket") or history.get("ticket"),
        "symbol": cycle.get("symbol") or history.get("symbol"),
        "timeframe": cycle.get("timeframe"),
        "direction": cycle.get("direction"),
        "history_direction": _direction(history.get("direction")),
        "direction_matches_history": _direction(history.get("direction")) in {None, cycle.get("direction")},
        "profile": cycle.get("profile"),
        "edge_status": cycle.get("edge_status"),
        "attempt_status": attempt.get("status"),
        "attempt_mode": attempt.get("mode"),
        "history_broker_mode": history.get("broker_mode"),
        "net_pnl": net_pnl,
        "gross_profit": _float(history.get("gross_profit"), 0.0),
        "commission": _float(history.get("commission"), 0.0),
        "swap": _float(history.get("swap"), 0.0),
        "close_reason": history.get("close_reason"),
        "open_time": history.get("open_time"),
        "close_time": history.get("close_time"),
        "paper_demo_only": True,
    }


def _unbound_row(
    cycle: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any] | None,
    broker_ticket: str | None,
    history_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not attempt:
        missing = "paper_order_attempt"
    elif not bool(attempt.get("executed", False)):
        missing = "executed_paper_attempt"
    elif not broker_ticket:
        missing = "broker_ticket"
    elif not history_row:
        missing = "closed_mt5_paper_history"
    else:
        missing = "paper_demo_closed_history"
    return {
        "cycle_id": cycle.get("cycle_id"),
        "decision_ref": cycle.get("decision_ref"),
        "order_id": cycle.get("order_id"),
        "symbol": cycle.get("symbol"),
        "timeframe": cycle.get("timeframe"),
        "direction": cycle.get("direction"),
        "profile": cycle.get("profile"),
        "edge_status": cycle.get("edge_status"),
        "attempt_status": attempt.get("status") if attempt else None,
        "attempt_executed": bool(attempt.get("executed", False)) if attempt else False,
        "broker_ticket": broker_ticket,
        "missing": missing,
    }


def _index_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            index[value] = dict(row)
    return index


def _broker_ticket(cycle: Mapping[str, Any], attempt: Mapping[str, Any] | None) -> str | None:
    candidates: list[Any] = []
    if attempt:
        outcome = _mapping(attempt.get("outcome"))
        result = _mapping(attempt.get("result"))
        candidates.extend(
            (
                outcome.get("broker_ticket"),
                result.get("broker_ticket"),
                result.get("ticket"),
            )
        )
    execute = _mapping(cycle.get("execute_result"))
    outcome = _mapping(execute.get("outcome"))
    candidates.extend((execute.get("broker_ticket"), execute.get("ticket"), outcome.get("broker_ticket")))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _paper_demo_history(row: Mapping[str, Any]) -> bool:
    mode = str(row.get("broker_mode") or "").upper()
    return bool(row.get("broker_ticket") or row.get("ticket")) and ("PAPER" in mode or "DEMO" in mode) and "LIVE" not in mode


def _profile(candidate: Mapping[str, Any]) -> str | None:
    hypothesis = _mapping(candidate.get("directional_hypothesis"))
    meta = _mapping(candidate.get("market_state_meta"))
    cas_map = _mapping(meta.get("cas_feature_map"))
    value = hypothesis.get("profile") or cas_map.get("selected_profile")
    return str(value) if value else None


def _status(
    *,
    confirmed_count: int,
    executed_count: int,
    history_count: int,
    bound_count: int,
    outcome_ready: bool,
) -> str:
    if confirmed_count <= 0:
        return STATUS_NO_CONFIRMED_EDGE
    if executed_count <= 0:
        return STATUS_AWAITING_EXECUTION
    if history_count <= 0 or bound_count <= 0:
        return STATUS_AWAITING_CLOSED_HISTORY
    if outcome_ready:
        return STATUS_READY
    return STATUS_COLLECTING


def _next_action(status: str, bound_count: int, needed: int) -> str:
    if status == STATUS_NO_CONFIRMED_EDGE:
        return "Let WASTE keep running in PAPER until a LONG/SHORT setup earns a PASS edge token."
    if status == STATUS_AWAITING_EXECUTION:
        return "A PASS-token direction exists, but no matching paper/demo execution attempt is finalized yet."
    if status == STATUS_AWAITING_CLOSED_HISTORY:
        return "Run MT5 paper/demo deal-history ingest after the matched paper position closes."
    if status == STATUS_READY:
        return "Realized paper/demo outcomes are bound; promotion may move to owner review while all live gates remain separate."
    return f"Collect {needed} more bound closed paper/demo outcome(s); currently bound {bound_count}."


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _direction(value: Any) -> str | None:
    text = str(value or "").upper()
    if text in {"LONG", "BUY"}:
        return "LONG"
    if text in {"SHORT", "SELL"}:
        return "SHORT"
    return None


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return round(float(default), 6)


__all__ = [
    "DEFAULT_MIN_BOUND_OUTCOMES_FOR_PROMOTION",
    "REPORT_KIND",
    "STATUS_AWAITING_CLOSED_HISTORY",
    "STATUS_AWAITING_EXECUTION",
    "STATUS_COLLECTING",
    "STATUS_NO_CONFIRMED_EDGE",
    "STATUS_READY",
    "build_waste_direction_outcome_binding",
]
