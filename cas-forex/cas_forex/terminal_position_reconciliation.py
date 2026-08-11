"""Terminal position reconciliation for CAS Forex.

This report compares what CAS Forex remembers with what the terminal-side
evidence says about receipts, account snapshots, open positions, and closed
history. It is the cockpit's read-only "do our books match the terminal?"
layer before any operating session can be trusted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from cas_forex.agent_memory import load_latest_agent_memory_report
from cas_forex.mt4_history_export_verifier import load_latest_mt4_history_export_verifier_report
from cas_forex.terminal_bridge_supervisor import load_latest_terminal_bridge_supervisor_report
from cas_forex.terminal_history_ingest import load_latest_terminal_history_ingest_report
from cas_forex.terminal_receipt_ingest import load_latest_terminal_receipt_ingest_report
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_position_reconciliation"
REPORT_KIND = "cas_forex_terminal_position_reconciliation_report"
RECONCILIATION_SCHEMA = "cas_forex_terminal_position_reconciliation.v1"
MAX_UNMATCHED_HISTORY_DETAILS = 200
CLAIM_BOUNDARY = (
    "Terminal position reconciliation compares CAS Forex memory with terminal "
    "receipts, account snapshots, open-position evidence, and closed-history "
    "ingest. It does not by itself execute live broker orders, create broker "
    "ACCEPT, deposit, withdraw, move bank/card funds, automate payouts, or "
    "override terminal evidence."
)

STATUS_OK = "OK"
STATUS_MISMATCH = "MISMATCH"
STATUS_UNVERIFIABLE = "UNVERIFIABLE"

# Lane identifiers for per-lane breakdowns. Lane assignment is derived from
# the `broker_mode` field carried on memory rows, receipts, and snapshots:
# anything starting with PAPER_MT5 (or MT5) is the MT5 demo lane; everything
# else (including PAPER_MT4, MT4, or missing) falls back to the legacy MT4
# mailbox lane.
LANE_MT4_MAILBOX = "mt4_mailbox"
LANE_MT5_DEMO = "mt5_demo"


def _lane_for_record(record: Mapping[str, Any]) -> str:
    """Best-effort lane assignment from a memory/receipt/position record.

    The cockpit displays the broker mode written by the agent loop. The MT5
    paper/demo lane uses broker_mode values that start with ``PAPER_MT5``
    (and historically ``MT5``); every other value — including ``PAPER_MT4``,
    ``MT4``, or missing — is the legacy MT4 mailbox lane.
    """

    if not isinstance(record, Mapping):
        return LANE_MT4_MAILBOX
    broker_mode = record.get("broker_mode")
    if broker_mode is None:
        # Look one level deeper into nested snapshots used by terminal rows.
        snapshot = record.get("condition_snapshot_open") if isinstance(record.get("condition_snapshot_open"), Mapping) else None
        if snapshot is not None:
            broker_mode = snapshot.get("broker_mode")
    if broker_mode is None:
        return LANE_MT4_MAILBOX
    text = str(broker_mode).strip().upper()
    if "MT5" in text:
        return LANE_MT5_DEMO
    return LANE_MT4_MAILBOX


def _active_execution_lane(value: Any) -> str:
    token = str(value or LANE_MT4_MAILBOX).strip().lower()
    if token in {LANE_MT5_DEMO, "mt5", "mt5_direct", "paper_mt5", "live_mt5"}:
        return LANE_MT5_DEMO
    return LANE_MT4_MAILBOX


class TerminalPositionReconciliationError(ValueError):
    """Raised when terminal position reconciliation evidence is invalid."""


def build_terminal_position_reconciliation_report(
    *,
    terminal_bridge_report: Optional[Mapping[str, Any]] = None,
    receipt_ingest_report: Optional[Mapping[str, Any]] = None,
    history_ingest_report: Optional[Mapping[str, Any]] = None,
    memory_report: Optional[Mapping[str, Any]] = None,
    mt4_history_export_verifier_report: Optional[Mapping[str, Any]] = None,
    active_execution_lane: Optional[str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build a reconciliation report from the latest terminal/memory evidence."""

    active_lane = _active_execution_lane(active_execution_lane)
    bridge = _source("terminal_bridge_supervisor", terminal_bridge_report, load_latest_terminal_bridge_supervisor_report)
    receipts = _source("terminal_receipt_ingest", receipt_ingest_report, load_latest_terminal_receipt_ingest_report)
    history = _source("terminal_history_ingest", history_ingest_report, load_latest_terminal_history_ingest_report)
    memory = _source("agent_memory", memory_report, load_latest_agent_memory_report)
    mt4_export = _source("mt4_history_export_verifier", mt4_history_export_verifier_report, load_latest_mt4_history_export_verifier_report)

    account_snapshot = _latest_account_snapshot(bridge["payload"], receipts["payload"])
    history_records = list((history["payload"] or {}).get("history_records") or [])
    memory_updates = list((history["payload"] or {}).get("memory_updates") or [])
    memory_records = list((memory["payload"] or {}).get("memory_records") or [])
    receipt_records = list((receipts["payload"] or {}).get("receipt_records") or [])
    classified_unmatched_history = _classified_unmatched_history_rows(history["payload"])

    closed_keys = _closed_identity_keys(history_records, memory_updates, memory_records)
    terminal_positions = _terminal_open_positions(account_snapshot, receipt_records, closed_keys)
    cas_positions = _cas_open_positions(memory_records, closed_keys)
    reconciled, mismatched = _match_open_positions(cas_positions, terminal_positions)
    classified_unmatched = [_classify_unmatched_open_position(item) for item in mismatched]

    summary = _summary(
        bridge=bridge,
        receipts=receipts,
        history=history,
        memory=memory,
        mt4_export=mt4_export,
        account_snapshot=account_snapshot,
        terminal_positions=terminal_positions,
        cas_positions=cas_positions,
        reconciled=reconciled,
        mismatched=classified_unmatched,
        memory_updates=memory_updates,
        history_records=history_records,
        classified_unmatched_history=classified_unmatched_history,
        active_execution_lane=active_lane,
    )
    checks = _checks(summary)
    status = _reconciliation_status(summary, checks)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "reconciliation_status": status,
        "schema": RECONCILIATION_SCHEMA,
        "source_reports": {
            "terminal_bridge_supervisor": bridge["ref"],
            "terminal_receipt_ingest": receipts["ref"],
            "terminal_history_ingest": history["ref"],
            "agent_memory": memory["ref"],
            "mt4_history_export_verifier": mt4_export["ref"],
        },
        "summary": summary,
        "account_snapshot": account_snapshot,
        "terminal_open_positions": terminal_positions,
        "cas_open_positions": cas_positions,
        "reconciled_open_positions": reconciled,
        "unmatched_open_positions": mismatched,
        "classified_unmatched_open_positions": classified_unmatched,
        "closed_history": {
            "history_record_count": len(history_records),
            "memory_update_count": len(memory_updates),
            "history_records": history_records[:20],
            "memory_updates": memory_updates[:20],
        },
        "classified_unmatched_history_record_count": len(classified_unmatched_history),
        "classified_unmatched_history_records": classified_unmatched_history[:MAX_UNMATCHED_HISTORY_DETAILS],
        "classified_unmatched_history_records_truncated": len(classified_unmatched_history) > MAX_UNMATCHED_HISTORY_DETAILS,
        "checks": checks,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, summary),
        "operator_commands": _operator_commands(),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_terminal_position_reconciliation_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_terminal_position_reconciliation_report(report)
    return report


def write_terminal_position_reconciliation_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_terminal_position_reconciliation_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"terminal-position-reconciliation-{stamp}-report.json"
    md_path = target_dir / f"terminal-position-reconciliation-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_terminal_position_reconciliation_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_terminal_position_reconciliation_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("terminal-position-reconciliation-*-report.json"))
    if not files:
        raise TerminalPositionReconciliationError(f"No terminal position reconciliation reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_terminal_position_reconciliation_report(payload)
    return payload


def validate_terminal_position_reconciliation_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "reconciliation_status",
        "schema",
        "source_reports",
        "summary",
        "terminal_open_positions",
        "cas_open_positions",
        "checks",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise TerminalPositionReconciliationError(f"terminal position reconciliation report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise TerminalPositionReconciliationError("unexpected terminal position reconciliation report_kind")
    if payload.get("schema") != RECONCILIATION_SCHEMA:
        raise TerminalPositionReconciliationError("unexpected terminal position reconciliation schema")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise TerminalPositionReconciliationError("terminal position reconciliation claim boundary must preserve execution boundary")
    if not isinstance(payload.get("summary"), Mapping):
        raise TerminalPositionReconciliationError("summary must be an object")
    if not isinstance(payload.get("checks"), list):
        raise TerminalPositionReconciliationError("checks must be a list")


def render_terminal_position_reconciliation_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Terminal Position Reconciliation",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('reconciliation_status')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Bridge status: `{summary.get('bridge_status')}`",
        f"- Heartbeat status: `{summary.get('heartbeat_status')}`",
        f"- Account snapshot present: `{summary.get('account_snapshot_present')}`",
        f"- CAS open positions: `{summary.get('cas_open_position_count')}`",
        f"- Terminal open positions: `{summary.get('terminal_open_position_count')}`",
        f"- Reconciled open positions: `{summary.get('reconciled_open_position_count')}`",
        f"- Unmatched open positions: `{summary.get('unmatched_open_position_count')}`",
        f"- Pending receipts: `{summary.get('pending_receipt_count')}`",
        f"- Receipt mismatches: `{summary.get('receipt_mismatch_count')}`",
        f"- Closed history rows / memory updates: `{summary.get('history_record_count')}` / `{summary.get('memory_update_count')}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks") or []:
        lines.append(f"- `{check.get('status')}` `{check.get('check_id')}`: {check.get('detail')}")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _source(name: str, provided: Optional[Mapping[str, Any]], loader: Any) -> Dict[str, Any]:
    if provided is not None:
        return {"name": name, "present": True, "payload": dict(provided), "ref": _report_ref(provided)}
    try:
        payload = loader()
    except Exception as exc:
        return {
            "name": name,
            "present": False,
            "payload": None,
            "ref": {"present": False, "error_type": type(exc).__name__, "message": str(exc)},
        }
    return {"name": name, "present": True, "payload": payload, "ref": _report_ref(payload)}


def _report_ref(report: Mapping[str, Any]) -> Dict[str, Any]:
    artifact_paths = report.get("artifact_paths") if isinstance(report.get("artifact_paths"), Mapping) else {}
    return {
        "present": True,
        "report_kind": report.get("report_kind"),
        "status": (
            report.get("reconciliation_status")
            or report.get("supervisor_status")
            or report.get("ingest_status")
            or report.get("memory_status")
            or report.get("verifier_status")
        ),
        "report_path": report.get("report_path") or artifact_paths.get("json"),
        "created_at": report.get("created_at"),
        "summary": report.get("summary") or {},
    }


def _latest_account_snapshot(
    bridge_report: Optional[Mapping[str, Any]],
    receipt_ingest_report: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    bridge_account = ((bridge_report or {}).get("account_snapshot") or {}).get("latest_account_snapshot")
    if isinstance(bridge_account, Mapping) and bridge_account:
        return {"present": True, "source": "terminal_bridge_supervisor", "snapshot": dict(bridge_account)}
    for record in reversed(list((receipt_ingest_report or {}).get("receipt_records") or [])):
        snapshot = record.get("account_snapshot") if isinstance(record, Mapping) else None
        if isinstance(snapshot, Mapping) and snapshot:
            return {"present": True, "source": "terminal_receipt_ingest", "snapshot": dict(snapshot)}
    return {"present": False, "source": None, "snapshot": {}}


def _closed_identity_keys(
    history_records: Sequence[Mapping[str, Any]],
    memory_updates: Sequence[Mapping[str, Any]],
    memory_records: Sequence[Mapping[str, Any]],
) -> set[Tuple[str, str]]:
    keys: set[Tuple[str, str]] = set()
    for row in [*history_records, *memory_updates]:
        keys.update(_identity_keys(row))
    for row in memory_records:
        if _is_closed_memory(row):
            keys.update(_identity_keys(row))
    return keys


def _terminal_open_positions(
    account_snapshot: Mapping[str, Any],
    receipt_records: Sequence[Mapping[str, Any]],
    closed_keys: set[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    snapshot = account_snapshot.get("snapshot") if isinstance(account_snapshot.get("snapshot"), Mapping) else {}
    for source_key in ("positions", "open_positions", "open_trades", "trades"):
        value = snapshot.get(source_key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    rows.append(_position_record(item, source=f"account_snapshot.{source_key}"))
    for receipt in receipt_records:
        if not isinstance(receipt, Mapping):
            continue
        if str(receipt.get("lifecycle_status") or receipt.get("receipt_validation_status") or "") != "RECEIPT_VERIFIED":
            continue
        row = _position_record(receipt, source="terminal_receipt_ingest")
        row["broker_mode"] = receipt.get("broker_mode")
        row["lane"] = _lane_for_record(receipt)
        rows.append(row)
    deduped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if _has_closed_key(row, closed_keys):
            continue
        deduped[_position_dedupe_key(row)] = row
    return list(deduped.values())


def _cas_open_positions(
    memory_records: Sequence[Mapping[str, Any]],
    closed_keys: set[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for memory in memory_records:
        if not isinstance(memory, Mapping) or _is_closed_memory(memory):
            continue
        if not memory.get("decision_approved") or not memory.get("command_id"):
            continue
        row = _position_record(memory, source="agent_memory")
        row["receipt_pending"] = str(memory.get("outcome_label") or "") == "AWAITING_TERMINAL_RECEIPT" or not bool(memory.get("receipt_id"))
        row["learning_status"] = memory.get("learning_status")
        row["outcome_label"] = memory.get("outcome_label")
        row["broker_mode"] = memory.get("broker_mode")
        row["lane"] = _lane_for_record(memory)
        if not _has_closed_key(row, closed_keys):
            rows.append(row)
    return rows


def _position_record(row: Mapping[str, Any], *, source: str) -> Dict[str, Any]:
    open_snapshot = row.get("condition_snapshot_open") if isinstance(row.get("condition_snapshot_open"), Mapping) else {}
    order = open_snapshot.get("order_request") if isinstance(open_snapshot.get("order_request"), Mapping) else {}
    broker_mode = _first_text(row, open_snapshot, order, keys=("broker_mode", "account_mode"))
    record = {
        "position_id": _position_id(row, source),
        "source": source,
        "symbol": _first_text(row, open_snapshot, order, keys=("symbol", "instrument")),
        "direction": _normalize_direction(_first_text(row, open_snapshot, order, keys=("direction", "side", "type"))),
        "lots": _first_number(row, open_snapshot, order, keys=("lots", "lot_size", "volume", "filled_volume", "size")),
        "open_price": _first_number(row, open_snapshot, order, keys=("open_price", "entry_price", "filled_price", "price")),
        "current_price": _first_number(row, open_snapshot, order, keys=("current_price", "close_or_current_price", "market_price")),
        "stop_loss": _first_number(row, open_snapshot, order, keys=("stop_loss", "sl")),
        "take_profit": _first_number(row, open_snapshot, order, keys=("take_profit", "tp")),
        "broker_ticket": _first_text(row, open_snapshot, order, keys=("broker_ticket", "ticket", "position_ticket")),
        "command_id": _first_text(row, open_snapshot, order, keys=("command_id", "cas_command_id")),
        "receipt_id": _first_text(row, open_snapshot, order, keys=("receipt_id",)),
        "memory_id": row.get("memory_id"),
        "status": row.get("status") or row.get("terminal_receipt_status") or row.get("outcome_label"),
        "broker_mode": broker_mode,
    }
    record["lane"] = _lane_for_record(record)
    return record


def _match_open_positions(
    cas_positions: Sequence[Mapping[str, Any]],
    terminal_positions: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    matched: List[Dict[str, Any]] = []
    unmatched: List[Dict[str, Any]] = []
    claimed_terminal: set[int] = set()
    for cas in cas_positions:
        if cas.get("receipt_pending"):
            unmatched.append({"side": "cas", "reason": "receipt_pending", "position": dict(cas)})
            continue
        index, method = _best_terminal_match(cas, terminal_positions, claimed_terminal)
        if index is None:
            unmatched.append({"side": "cas", "reason": "no_matching_terminal_position", "position": dict(cas)})
            continue
        claimed_terminal.add(index)
        matched.append({"cas_position": dict(cas), "terminal_position": dict(terminal_positions[index]), "match_method": method})
    for index, terminal in enumerate(terminal_positions):
        if index not in claimed_terminal:
            unmatched.append({"side": "terminal", "reason": "no_matching_cas_memory_position", "position": dict(terminal)})
    return matched, unmatched


def _best_terminal_match(
    cas: Mapping[str, Any],
    terminal_positions: Sequence[Mapping[str, Any]],
    claimed_terminal: set[int],
) -> Tuple[Optional[int], Optional[str]]:
    for key, method in (("command_id", "command_id"), ("receipt_id", "receipt_id"), ("broker_ticket", "broker_ticket")):
        value = cas.get(key)
        if not value:
            continue
        for index, terminal in enumerate(terminal_positions):
            if index in claimed_terminal:
                continue
            if terminal.get(key) and str(terminal.get(key)) == str(value):
                return index, method
    for index, terminal in enumerate(terminal_positions):
        if index in claimed_terminal:
            continue
        if _loose_position_match(cas, terminal):
            return index, "symbol_direction_lots"
    return None, None


def _loose_position_match(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    if str(a.get("symbol") or "") != str(b.get("symbol") or ""):
        return False
    if str(a.get("direction") or "") != str(b.get("direction") or ""):
        return False
    lots_a = _to_float(a.get("lots"))
    lots_b = _to_float(b.get("lots"))
    return lots_a is not None and lots_b is not None and abs(lots_a - lots_b) <= 1e-6


def _summary(
    *,
    bridge: Mapping[str, Any],
    receipts: Mapping[str, Any],
    history: Mapping[str, Any],
    memory: Mapping[str, Any],
    mt4_export: Mapping[str, Any],
    account_snapshot: Mapping[str, Any],
    terminal_positions: Sequence[Mapping[str, Any]],
    cas_positions: Sequence[Mapping[str, Any]],
    reconciled: Sequence[Mapping[str, Any]],
    mismatched: Sequence[Mapping[str, Any]],
    memory_updates: Sequence[Mapping[str, Any]],
    history_records: Sequence[Mapping[str, Any]],
    classified_unmatched_history: Sequence[Mapping[str, Any]],
    active_execution_lane: str,
) -> Dict[str, Any]:
    bridge_summary = ((bridge.get("payload") or {}).get("summary") or {}) if bridge.get("present") else {}
    receipt_summary = ((receipts.get("payload") or {}).get("summary") or {}) if receipts.get("present") else {}
    history_summary = ((history.get("payload") or {}).get("summary") or {}) if history.get("present") else {}
    memory_summary = ((memory.get("payload") or {}).get("summary") or {}) if memory.get("present") else {}
    mt4_summary = ((mt4_export.get("payload") or {}).get("summary") or {}) if mt4_export.get("present") else {}
    cas_pending = sum(1 for row in cas_positions if row.get("receipt_pending"))
    cas_ack = len(cas_positions) - cas_pending
    terminal_unattributed = sum(
        1
        for row in mismatched
        if str(row.get("classification_status") or "") == "TERMINAL_UNATTRIBUTED_BROKER_POSITION"
    )
    terminal_memory_gap = sum(
        1
        for row in mismatched
        if str(row.get("classification_status") or "") == "TERMINAL_ATTRIBUTED_MEMORY_GAP_POSITION"
    )
    cas_memory_only = sum(
        1
        for row in mismatched
        if str(row.get("classification_status") or "") == "CAS_MEMORY_ONLY_POSITION"
    )
    cas_receipt_pending = sum(
        1
        for row in mismatched
        if str(row.get("classification_status") or "") == "CAS_RECEIPT_PENDING_POSITION"
    )
    unmatched_history_count = int(
        history_summary.get("unmatched_history_count")
        or len(
            [
                row
                for row in ((history.get("payload") or {}).get("classified_unmatched_history_records") or [])
                if isinstance(row, Mapping)
            ]
        )
        or 0
    )
    unmatched_unattributed_history_count = int(
        history_summary.get("unmatched_unattributed_history_count")
        or 0
    )
    unmatched_attributed_history_gap_count = int(
        history_summary.get("unmatched_attributed_history_memory_gap_count")
        or 0
    )

    # Per-lane breakdown: separate the MT4-mailbox legacy rows from the
    # MT5 demo lane so the cockpit can show which numbers belong to which
    # broker bridge instead of conflating stale MT4 rows with live MT5
    # broker truth.
    cas_open_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    pending_receipt_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    terminal_open_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    unmatched_open_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    unmatched_history_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    attributed_history_gap_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    unattributed_history_by_lane: Dict[str, int] = {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}
    for row in cas_positions:
        lane = row.get("lane") or _lane_for_record(row)
        cas_open_by_lane[lane] = cas_open_by_lane.get(lane, 0) + 1
        if row.get("receipt_pending"):
            pending_receipt_by_lane[lane] = pending_receipt_by_lane.get(lane, 0) + 1
    for row in terminal_positions:
        lane = row.get("lane") or _lane_for_record(row)
        terminal_open_by_lane[lane] = terminal_open_by_lane.get(lane, 0) + 1
    for row in mismatched:
        position = row.get("position") if isinstance(row.get("position"), Mapping) else {}
        lane = position.get("lane") or _lane_for_record(position)
        unmatched_open_by_lane[lane] = unmatched_open_by_lane.get(lane, 0) + 1
    for row in classified_unmatched_history:
        lane = row.get("lane") or _lane_for_record(row)
        unmatched_history_by_lane[lane] = unmatched_history_by_lane.get(lane, 0) + 1
        classification = str(row.get("classification_status") or "")
        if classification == "TERMINAL_ATTRIBUTED_HISTORY_MEMORY_GAP":
            attributed_history_gap_by_lane[lane] = attributed_history_gap_by_lane.get(lane, 0) + 1
        elif classification == "TERMINAL_UNATTRIBUTED_BROKER_HISTORY":
            unattributed_history_by_lane[lane] = unattributed_history_by_lane.get(lane, 0) + 1
    active_lane = _active_execution_lane(active_execution_lane)
    return {
        "active_execution_lane": active_lane,
        "mt4_lane_required": active_lane == LANE_MT4_MAILBOX,
        "bridge_report_present": bool(bridge.get("present")),
        "receipt_ingest_report_present": bool(receipts.get("present")),
        "history_ingest_report_present": bool(history.get("present")),
        "memory_report_present": bool(memory.get("present")),
        "mt4_history_export_verifier_present": bool(mt4_export.get("present")),
        "bridge_status": (bridge.get("ref") or {}).get("status"),
        "mt4_history_export_verifier_status": (mt4_export.get("ref") or {}).get("status"),
        "heartbeat_status": bridge_summary.get("heartbeat_status"),
        "heartbeat_present": bool(bridge_summary.get("heartbeat_present", False)),
        "account_snapshot_present": bool(account_snapshot.get("present")),
        "account_snapshot_source": account_snapshot.get("source"),
        "live_trading_flag_visible": bool(bridge_summary.get("live_trading_flag_visible", False)),
        "pending_receipt_count": int(receipt_summary.get("pending_receipt_count") or memory_summary.get("pending_receipt_count") or 0),
        "receipt_mismatch_count": int(receipt_summary.get("receipt_mismatch_count") or memory_summary.get("receipt_mismatch_count") or 0),
        "cas_open_position_count": len(cas_positions),
        "cas_open_position_count_by_lane": dict(cas_open_by_lane),
        "pending_receipt_count_by_lane": dict(pending_receipt_by_lane),
        "active_pending_receipt_count": int(pending_receipt_by_lane.get(active_lane, 0)),
        "cas_receipt_pending_open_count": cas_pending,
        "cas_receipt_ack_open_count": cas_ack,
        "terminal_open_position_count": len(terminal_positions),
        "terminal_open_position_count_by_lane": dict(terminal_open_by_lane),
        "active_terminal_open_position_count": int(terminal_open_by_lane.get(active_lane, 0)),
        "reconciled_open_position_count": len(reconciled),
        "unmatched_open_position_count": len(mismatched),
        "unmatched_open_position_count_by_lane": dict(unmatched_open_by_lane),
        "active_unmatched_open_position_count": int(unmatched_open_by_lane.get(active_lane, 0)),
        "terminal_unattributed_open_position_count": terminal_unattributed,
        "terminal_memory_gap_open_position_count": terminal_memory_gap,
        "cas_memory_only_open_position_count": cas_memory_only,
        "cas_receipt_pending_open_position_count": cas_receipt_pending,
        "history_record_count": len(history_records),
        "memory_update_count": len(memory_updates),
        "unmatched_history_count": unmatched_history_count or int(mt4_summary.get("unmatched_history_count") or 0),
        "unmatched_history_count_by_lane": dict(unmatched_history_by_lane),
        "active_unmatched_history_count": int(unmatched_history_by_lane.get(active_lane, 0)),
        "unmatched_unattributed_history_count": unmatched_unattributed_history_count,
        "unmatched_unattributed_history_count_by_lane": dict(unattributed_history_by_lane),
        "active_unmatched_unattributed_history_count": int(unattributed_history_by_lane.get(active_lane, 0)),
        "unmatched_attributed_history_memory_gap_count": unmatched_attributed_history_gap_count,
        "unmatched_attributed_history_memory_gap_count_by_lane": dict(attributed_history_gap_by_lane),
        "active_unmatched_attributed_history_memory_gap_count": int(attributed_history_gap_by_lane.get(active_lane, 0)),
        "terminal_history_joined_count": int(memory_summary.get("terminal_history_joined_count") or 0),
        "closed_profit_count": int(history_summary.get("closed_profit_count") or memory_summary.get("closed_profit_count") or 0),
        "closed_loss_count": int(history_summary.get("closed_loss_count") or memory_summary.get("closed_loss_count") or 0),
        "net_profit_loss_account": float(history_summary.get("net_profit_loss_account") or memory_summary.get("net_profit_loss_account") or 0.0),
    }


def _checks(summary: Mapping[str, Any]) -> List[Dict[str, Any]]:
    mt4_required = bool(summary.get("mt4_lane_required", True))
    active_pending = int(summary.get("active_pending_receipt_count", summary.get("pending_receipt_count", 0)) or 0)
    active_unmatched_open = int(
        summary.get("active_unmatched_open_position_count", summary.get("unmatched_open_position_count", 0)) or 0
    )
    active_history = int(summary.get("active_unmatched_history_count", summary.get("unmatched_history_count", 0)) or 0)
    active_unattributed_history = int(
        summary.get(
            "active_unmatched_unattributed_history_count",
            summary.get("unmatched_unattributed_history_count", 0),
        )
        or 0
    )
    active_attributed_history_gap = int(
        summary.get(
            "active_unmatched_attributed_history_memory_gap_count",
            summary.get("unmatched_attributed_history_memory_gap_count", 0),
        )
        or 0
    )
    checks = [
        _check(
            "terminal_bridge_report_present",
            STATUS_OK if summary.get("bridge_report_present") or not mt4_required else STATUS_UNVERIFIABLE,
            bool(summary.get("bridge_report_present")),
            "latest terminal bridge supervisor report present",
            (
                "Terminal bridge supervisor evidence is available."
                if summary.get("bridge_report_present")
                else (
                    "The MT4 bridge supervisor is inactive and is not required for the active MT5 execution lane."
                    if not mt4_required
                    else "No terminal bridge supervisor report is available."
                )
            ),
        ),
        _check(
            "heartbeat_fresh",
            STATUS_OK if summary.get("heartbeat_status") == "FRESH" or not mt4_required else STATUS_UNVERIFIABLE,
            summary.get("heartbeat_status"),
            "terminal heartbeat is fresh",
            (
                "The MT4 heartbeat is inactive and is not a readiness requirement for direct MT5 execution."
                if not mt4_required and summary.get("heartbeat_status") != "FRESH"
                else f"Heartbeat status is {summary.get('heartbeat_status') or 'missing'}; terminal position truth needs a fresh heartbeat."
            ),
        ),
        _check(
            "account_snapshot_present",
            STATUS_OK if summary.get("account_snapshot_present") or not mt4_required else STATUS_UNVERIFIABLE,
            summary.get("account_snapshot_present"),
            "terminal account snapshot is present",
            (
                "Account snapshot is present."
                if summary.get("account_snapshot_present")
                else (
                    "The MT4 mailbox snapshot is inactive; the broker-truth monitor reads the active MT5 account directly."
                    if not mt4_required
                    else "No terminal account snapshot is present."
                )
            ),
        ),
        _check(
            "receipt_lifecycle_clear",
            STATUS_MISMATCH if summary.get("receipt_mismatch_count", 0) > 0 else (STATUS_UNVERIFIABLE if active_pending > 0 else STATUS_OK),
            {
                "active_lane": summary.get("active_execution_lane"),
                "active_pending": active_pending,
                "pending_all_lanes": summary.get("pending_receipt_count"),
                "mismatches": summary.get("receipt_mismatch_count"),
            },
            "terminal receipts are verified and not pending",
            "Receipt lifecycle has no pending or mismatched terminal responses."
            if active_pending == 0 and summary.get("receipt_mismatch_count", 0) == 0
            else "The active execution lane still has pending or mismatched terminal responses.",
        ),
        _check(
            "open_positions_match",
            STATUS_MISMATCH if active_unmatched_open > 0 and active_pending == 0 else (STATUS_UNVERIFIABLE if active_pending > 0 else STATUS_OK),
            {
                "active_lane": summary.get("active_execution_lane"),
                "cas": summary.get("cas_open_position_count_by_lane", {}).get(summary.get("active_execution_lane")),
                "terminal": summary.get("active_terminal_open_position_count"),
                "unmatched": active_unmatched_open,
                "unmatched_all_lanes": summary.get("unmatched_open_position_count"),
            },
            "CAS open position memory matches terminal open positions",
            "Open positions match on the active execution lane."
            if active_unmatched_open == 0
            else "Open positions cannot all be matched between CAS memory and active-lane terminal evidence.",
        ),
        _check(
            "closed_history_joined",
            (
                STATUS_MISMATCH
                if active_attributed_history_gap > 0
                else (
                    STATUS_UNVERIFIABLE
                    if active_history > 0 or (summary.get("history_record_count", 0) > 0 and summary.get("memory_update_count", 0) == 0)
                    else STATUS_OK
                )
            ),
            {
                "active_lane": summary.get("active_execution_lane"),
                "history_rows": summary.get("history_record_count"),
                "memory_updates": summary.get("memory_update_count"),
                "active_unmatched_history": active_history,
                "active_unmatched_unattributed_history": active_unattributed_history,
                "active_unmatched_attributed_history_memory_gap": active_attributed_history_gap,
                "unmatched_history_all_lanes": summary.get("unmatched_history_count"),
            },
            "closed terminal history rows join back to CAS memory",
            "Closed history rows join memory or no closed-history rows exist yet."
            if active_history == 0
            else (
                f"Some active-lane closed-history rows do not join to CAS memory: unattributed={active_unattributed_history}, "
                f"attributed_memory_gap={active_attributed_history_gap}. Unattributed rows remain visible for review; only CAS-attributed memory gaps are a hard mismatch."
            ),
        ),
        _check(
            "live_flag_not_visible",
            STATUS_MISMATCH if summary.get("live_trading_flag_visible") and mt4_required else STATUS_OK,
            summary.get("live_trading_flag_visible"),
            "terminal evidence does not expose live-trading flag",
            (
                "No live-trading flag is visible in terminal supervisor evidence."
                if not summary.get("live_trading_flag_visible")
                else (
                    "The inactive MT4 supervisor exposes a live flag; it does not control the active MT5 lane."
                    if not mt4_required
                    else "Terminal supervisor evidence exposes a live-trading flag."
                )
            ),
        ),
    ]
    return checks


def _check(check_id: str, status: str, value: Any, description: str, detail: str) -> Dict[str, Any]:
    return {
        "check_id": check_id,
        "description": description,
        "status": status,
        "value": value,
        "detail": detail,
    }


def _reconciliation_status(summary: Mapping[str, Any], checks: Sequence[Mapping[str, Any]]) -> str:
    mt4_required = bool(summary.get("mt4_lane_required", True))
    if summary.get("live_trading_flag_visible") and mt4_required:
        return "TERMINAL_POSITION_RECONCILIATION_LIVE_FLAG_VISIBLE"
    if mt4_required and summary.get("mt4_history_export_verifier_status") == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL":
        return "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL"
    if mt4_required and summary.get("heartbeat_status") in {None, "MISSING"}:
        return "TERMINAL_POSITION_RECONCILIATION_NEEDS_TERMINAL_HEARTBEAT"
    if mt4_required and not summary.get("account_snapshot_present"):
        return "TERMINAL_POSITION_RECONCILIATION_NEEDS_ACCOUNT_SNAPSHOT"
    if any(check.get("status") == STATUS_MISMATCH for check in checks):
        return "TERMINAL_POSITION_RECONCILIATION_MISMATCH"
    if summary.get("active_pending_receipt_count", summary.get("pending_receipt_count", 0)) > 0:
        return "TERMINAL_POSITION_RECONCILIATION_WAITING_FOR_RECEIPTS"
    if any(check.get("status") == STATUS_UNVERIFIABLE for check in checks):
        return "TERMINAL_POSITION_RECONCILIATION_UNVERIFIABLE"
    if summary.get("active_terminal_open_position_count", summary.get("terminal_open_position_count", 0)) > 0:
        return "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS"
    return "TERMINAL_POSITION_RECONCILIATION_READY_FLAT"


def _next_action(status: str, summary: Mapping[str, Any]) -> str:
    if status == "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL":
        return "Install/open MT4, activate the terminal data folder, attach the bridge/history EAs, then rerun reconciliation."
    if status == "TERMINAL_POSITION_RECONCILIATION_NEEDS_TERMINAL_HEARTBEAT":
        return "Attach and run CASForexBridgeEA.mq4 until heartbeat.json is fresh, then rerun reconciliation."
    if status == "TERMINAL_POSITION_RECONCILIATION_NEEDS_ACCOUNT_SNAPSHOT":
        return "Generate a verified terminal receipt with account_snapshot so balance/equity and open positions can be compared."
    if status == "TERMINAL_POSITION_RECONCILIATION_WAITING_FOR_RECEIPTS":
        return "Let the terminal answer pending command files, run terminal_receipt_ingest, rebuild memory, then rerun reconciliation."
    if status == "TERMINAL_POSITION_RECONCILIATION_MISMATCH":
        if int(summary.get("terminal_unattributed_open_position_count", 0) or 0) > 0:
            return (
                "Owner-review unmatched broker-visible open positions that CAS cannot attribute; "
                "they may be external/manual broker state or missing CAS memory, and live dispatch stays blocked until resolved."
            )
        if int(summary.get("terminal_memory_gap_open_position_count", 0) or 0) > 0:
            return (
                "Run terminal receipt/history ingest and rebuild memory; broker-visible open positions carry CAS identifiers but are not fully joined back to CAS memory yet."
            )
        if int(summary.get("unmatched_unattributed_history_count", 0) or 0) > 0:
            return (
                "Owner-review unmatched broker closed-history rows that CAS cannot attribute; they may reflect external/manual broker closes or missing CAS identity fields."
            )
        if int(summary.get("unmatched_attributed_history_memory_gap_count", 0) or 0) > 0:
            return (
                "Run terminal history ingest and rebuild memory; closed broker history carries CAS identifiers but is not fully joined back to CAS memory yet."
            )
        return "Inspect unmatched_open_positions and closed_history unmatched rows before allowing another same-symbol cycle."
    if status == "TERMINAL_POSITION_RECONCILIATION_LIVE_FLAG_VISIBLE":
        return "Review the visible live flag against owner/runtime gates before any live command path is allowed."
    if status == "TERMINAL_POSITION_RECONCILIATION_UNVERIFIABLE":
        if int(summary.get("active_unmatched_unattributed_history_count", 0) or 0) > 0:
            return (
                "Review active-lane broker history rows that have no CAS identity. They remain visible as external/manual-or-missing-identity evidence, "
                "but they do not by themselves prove a current open-position mismatch."
            )
        return "Review the UNVERIFIABLE checks and refresh the active execution lane evidence."
    if status == "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS":
        return "Open positions reconcile; keep the supervisor and history exporter running so closes join memory."
    if summary.get("history_record_count", 0) == 0:
        return "Flat reconciliation is clean; next useful proof is a terminal close-history export after real/demo closes occur."
    return "Reconciliation is clean; feed the closed-history memory rows into daily rollup and strategy research."


def _operator_commands() -> Dict[str, str]:
    return {
        "terminal_session": "py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir <MT4_DATA_DIR> --install --wait-seconds 10",
        "receipt_ingest": "py -3.12 scripts/run_terminal_receipt_ingest.py",
        "history_export_verifier": "py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox",
        "position_reconciliation": "py -3.12 scripts/run_terminal_position_reconciliation.py --summary-only",
    }


def _is_closed_memory(record: Mapping[str, Any]) -> bool:
    return (
        str(record.get("terminal_history_status") or "") == "CLOSED_HISTORY_JOINED"
        or str(record.get("outcome_label") or "").startswith("TRADE_CLOSED_")
    )


def _identity_keys(record: Mapping[str, Any]) -> set[Tuple[str, str]]:
    keys: set[Tuple[str, str]] = set()
    for key in ("command_id", "receipt_id", "broker_ticket", "ticket"):
        value = record.get(key)
        if value is not None and str(value).strip():
            normalized_key = "broker_ticket" if key == "ticket" else key
            keys.add((normalized_key, str(value).strip()))
    return keys


def _has_closed_key(record: Mapping[str, Any], closed_keys: set[Tuple[str, str]]) -> bool:
    return bool(_identity_keys(record).intersection(closed_keys))


def _position_dedupe_key(record: Mapping[str, Any]) -> str:
    for key in ("broker_ticket", "command_id", "receipt_id"):
        if record.get(key):
            return f"{key}:{record[key]}"
    return "|".join(
        str(record.get(key) or "")
        for key in ("source", "symbol", "direction", "lots", "open_price")
    )


def _position_id(row: Mapping[str, Any], source: str) -> str:
    material = "|".join(
        str(value)
        for value in (
            source,
            row.get("memory_id"),
            row.get("command_id"),
            row.get("receipt_id"),
            row.get("broker_ticket") or row.get("ticket"),
            row.get("symbol"),
            row.get("direction") or row.get("side") or row.get("type"),
        )
    )
    return f"terminal-position-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"


def _classified_unmatched_history_rows(history_payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(history_payload, Mapping):
        return []
    rows = history_payload.get("classified_unmatched_history_records")
    if not isinstance(rows, list):
        rows = history_payload.get("unmatched_history_records")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        payload = dict(row)
        if not payload.get("classification_status"):
            command_id = str(payload.get("command_id") or "").strip()
            receipt_id = str(payload.get("receipt_id") or "").strip()
            if command_id or receipt_id:
                payload["classification_status"] = "TERMINAL_ATTRIBUTED_HISTORY_MEMORY_GAP"
                payload["classification_detail"] = (
                    "Closed broker history carries CAS identity, but CAS memory did not join it back yet."
                )
            else:
                payload["classification_status"] = "TERMINAL_UNATTRIBUTED_BROKER_HISTORY"
                payload["classification_detail"] = (
                    "Closed broker history has no CAS command/receipt identity and may be external/manual broker state."
                )
        out.append(payload)
    return out


def _classify_unmatched_open_position(row: Mapping[str, Any]) -> Dict[str, Any]:
    payload = dict(row or {})
    position = payload.get("position") if isinstance(payload.get("position"), Mapping) else {}
    side = str(payload.get("side") or "").strip().lower()
    reason = str(payload.get("reason") or "").strip().lower()
    command_id = str(position.get("command_id") or "").strip()
    receipt_id = str(position.get("receipt_id") or "").strip()
    broker_ticket = str(position.get("broker_ticket") or "").strip()

    classification = "UNMATCHED_OPEN_POSITION"
    detail = "Open-position reconciliation found an unmatched row."
    if side == "terminal" and reason == "no_matching_cas_memory_position":
        if command_id or receipt_id:
            classification = "TERMINAL_ATTRIBUTED_MEMORY_GAP_POSITION"
            detail = (
                "Broker-visible position carries CAS identifiers, but CAS memory/receipt history did not fully join it back yet."
            )
        else:
            classification = "TERMINAL_UNATTRIBUTED_BROKER_POSITION"
            detail = (
                "Broker-visible position has no CAS command/receipt identity. It may be external/manual broker state or missing CAS memory."
            )
    elif side == "cas" and reason == "receipt_pending":
        classification = "CAS_RECEIPT_PENDING_POSITION"
        detail = "CAS memory is still waiting for a verified terminal receipt for this open position."
    elif side == "cas" and reason == "no_matching_terminal_position":
        classification = "CAS_MEMORY_ONLY_POSITION"
        detail = "CAS memory shows an open position that terminal/broker evidence does not currently confirm."

    payload["classification_status"] = classification
    payload["classification_detail"] = detail
    payload["requires_owner_broker_review"] = classification == "TERMINAL_UNATTRIBUTED_BROKER_POSITION"
    payload["requires_reconciliation_repair"] = classification in {
        "TERMINAL_ATTRIBUTED_MEMORY_GAP_POSITION",
        "CAS_MEMORY_ONLY_POSITION",
        "CAS_RECEIPT_PENDING_POSITION",
    }
    payload["suggested_next_action"] = _classified_unmatched_next_action(classification)
    return payload


def _classified_unmatched_next_action(classification: str) -> str:
    if classification == "TERMINAL_UNATTRIBUTED_BROKER_POSITION":
        return (
            "Owner-review the unmatched broker-visible position against the terminal and broker history before any further live cycle."
        )
    if classification == "TERMINAL_ATTRIBUTED_MEMORY_GAP_POSITION":
        return "Run receipt/history ingest and rebuild CAS memory, then rerun terminal position reconciliation."
    if classification == "CAS_MEMORY_ONLY_POSITION":
        return "Refresh terminal/broker evidence and inspect whether CAS memory retained a stale open-position row."
    if classification == "CAS_RECEIPT_PENDING_POSITION":
        return "Wait for or ingest the terminal receipt before treating this position as reconciled."
    return "Inspect the unmatched row and rerun terminal position reconciliation."


def _first_text(*mappings: Mapping[str, Any], keys: Sequence[str]) -> Optional[str]:
    for mapping in mappings:
        for key in keys:
            if key in mapping and mapping[key] is not None and str(mapping[key]).strip():
                return str(mapping[key]).strip()
    return None


def _first_number(*mappings: Mapping[str, Any], keys: Sequence[str]) -> Optional[float]:
    for mapping in mappings:
        for key in keys:
            value = _to_float(mapping.get(key))
            if value is not None:
                return value
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _normalize_direction(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip().lower()
    if raw in {"buy", "long"}:
        return "LONG"
    if raw in {"sell", "short"}:
        return "SHORT"
    return str(value).strip().upper() if str(value).strip() else None
