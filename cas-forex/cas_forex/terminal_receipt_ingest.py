"""Join MT4/MT5 terminal receipts back into the CAS Forex agent journal.

The mailbox bridge can write commands and read receipt JSON files. This module
is the missing joinback: it links each terminal receipt to the command event,
checks the request hash and terminal/account identity fields, then appends the
receipt lifecycle events the overseer can consume before another same-symbol
route is allowed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from cas_forex.agent_message_bus import (
    DEFAULT_EVENT_LOG_PATH,
    AgentEventStore,
    AgentMessageBusError,
    make_agent_event,
)
from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAILBOX_DIR = REPO_ROOT / "evidence_runs" / "agent_workflow_mt4_mailbox"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_receipt_ingest"
REPORT_KIND = "cas_forex_terminal_receipt_ingest"
CLAIM_BOUNDARY = (
    "Terminal receipt ingest verifies paper/demo terminal receipts against "
    "CAS Forex command events and account snapshots. It does not by itself "
    "execute live broker orders, create broker ACCEPT, deposit, withdraw, move "
    "bank/card funds, or automate payouts."
)


class TerminalReceiptIngestError(ValueError):
    """Raised when terminal receipts cannot be joined to the agent journal."""


def ingest_terminal_receipts(
    *,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Read mailbox receipts, validate them, append lifecycle events, and report.

    The operation is idempotent by ``receipt_id``. Running it again will not
    append duplicate receipt lifecycle events for a receipt already represented
    in the event journal.
    """

    store = AgentEventStore(event_log_path)
    try:
        events = store.read_events(limit=100000)
    except AgentMessageBusError as exc:
        raise TerminalReceiptIngestError(str(exc)) from exc

    command_events = _command_events_by_id(events)
    already_ingested = _ingested_receipt_ids(events)
    bridge = MT4MailboxBridge(mailbox_dir=mailbox_dir)
    receipts = bridge.read_receipts()

    records: List[Dict[str, Any]] = []
    appended_event_ids: List[str] = []
    for receipt in receipts:
        receipt_id = str(receipt.get("receipt_id"))
        record = _build_receipt_record(receipt, command_events)
        if receipt_id in already_ingested:
            record["ingest_action"] = "SKIPPED_ALREADY_INGESTED"
            records.append(record)
            continue

        lifecycle_events = _events_for_receipt(record)
        for event in lifecycle_events:
            store.append_event(event)
            appended_event_ids.append(event.event_id)
        record["ingest_action"] = "APPENDED_EVENTS"
        record["event_ids"] = [event.event_id for event in lifecycle_events]
        records.append(record)

    summary = _summarize_records(records, appended_event_ids, store.summary())
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "ingest_status": "RECEIPT_INGEST_COMPLETE",
        "mailbox_dir": str(Path(mailbox_dir)),
        "event_log_path": str(Path(event_log_path)),
        "summary": summary,
        "receipt_records": records,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_terminal_receipt_ingest_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_terminal_receipt_ingest_report(report)
    return report


def write_terminal_receipt_ingest_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_terminal_receipt_ingest_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"terminal-receipt-ingest-{stamp}-report.json"
    md_path = target_dir / f"terminal-receipt-ingest-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_terminal_receipt_ingest_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_terminal_receipt_ingest_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("terminal-receipt-ingest-*-report.json"))
    if not files:
        raise TerminalReceiptIngestError(f"No terminal receipt ingest reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_terminal_receipt_ingest_report(payload)
    return payload


def validate_terminal_receipt_ingest_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "ingest_status",
        "mailbox_dir",
        "event_log_path",
        "summary",
        "receipt_records",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise TerminalReceiptIngestError(f"terminal receipt ingest report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise TerminalReceiptIngestError("unexpected terminal receipt ingest report_kind")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise TerminalReceiptIngestError("terminal receipt ingest claim boundary must preserve execution boundary")
    if not isinstance(payload.get("receipt_records"), list):
        raise TerminalReceiptIngestError("receipt_records must be a list")
    summary = payload.get("summary") or {}
    if not isinstance(summary, Mapping):
        raise TerminalReceiptIngestError("summary must be an object")


def render_terminal_receipt_ingest_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Terminal Receipt Ingest",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('ingest_status')}`",
        f"Mailbox: `{report.get('mailbox_dir')}`",
        f"Event log: `{report.get('event_log_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Receipts found: `{summary.get('receipt_count')}`",
        f"- New receipts: `{summary.get('new_receipt_count')}`",
        f"- Verified receipts: `{summary.get('verified_receipt_count')}`",
        f"- Reconciled receipts: `{summary.get('reconciled_receipt_count')}`",
        f"- Next-cycle allowed: `{summary.get('next_cycle_allowed_count')}`",
        f"- Receipt mismatches: `{summary.get('receipt_mismatch_count')}`",
        f"- Pending after ingest: `{summary.get('pending_receipt_count')}`",
        "",
        "## Receipts",
        "",
    ]
    for record in report.get("receipt_records") or []:
        lines.append(
            "- "
            f"`{record.get('receipt_id')}` command `{record.get('command_id')}` "
            f"status `{record.get('lifecycle_status')}` reconcile `{record.get('reconcile_status')}`"
        )
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _command_events_by_id(events: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for event in events:
        if event.get("event_type") != "TERMINAL_COMMAND_WRITTEN":
            continue
        payload = event.get("payload") or {}
        command_id = payload.get("command_id")
        if command_id:
            out[str(command_id)] = dict(event)
    return out


def _ingested_receipt_ids(events: Iterable[Mapping[str, Any]]) -> set[str]:
    receipt_ids: set[str] = set()
    for event in events:
        if event.get("event_type") not in {
            "TERMINAL_RECEIPT_RECEIVED",
            "TERMINAL_RECEIPT_MISMATCH",
        }:
            continue
        payload = event.get("payload") or {}
        receipt_id = payload.get("receipt_id")
        if receipt_id:
            receipt_ids.add(str(receipt_id))
    return receipt_ids


def _build_receipt_record(
    receipt: Mapping[str, Any],
    command_events: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    command_id = str(receipt.get("command_id"))
    command_event = command_events.get(command_id)
    command_payload = dict((command_event or {}).get("payload") or {})
    command_path = command_payload.get("command_path")
    command_file_payload = _read_command_file(command_path)
    expected_hash = command_payload.get("raw_request_hash") or command_file_payload.get("raw_request_hash")
    receipt_hash = receipt.get("raw_request_hash")
    account_snapshot = receipt.get("account_snapshot") or {}
    reasons: List[str] = []

    if command_event is None:
        reasons.append("no matching TERMINAL_COMMAND_WRITTEN event")
    if not expected_hash:
        reasons.append("matching command is missing raw_request_hash")
    if not receipt_hash:
        reasons.append("receipt missing raw_request_hash")
    if expected_hash and receipt_hash and str(expected_hash) != str(receipt_hash):
        reasons.append("receipt raw_request_hash does not match command raw_request_hash")
    if not receipt.get("terminal_name"):
        reasons.append("receipt missing terminal_name")
    if not receipt.get("account_id_hash"):
        reasons.append("receipt missing account_id_hash")
    if not receipt.get("server"):
        reasons.append("receipt missing server")
    if not isinstance(account_snapshot, Mapping) or not account_snapshot:
        reasons.append("receipt missing account_snapshot")
    if bool(receipt.get("live_mode")) or bool(receipt.get("live_trading_allowed")):
        reasons.append("receipt claims live mode/live trading allowed")

    hash_match = bool(expected_hash and receipt_hash and str(expected_hash) == str(receipt_hash))
    terminal_identity_present = bool(receipt.get("terminal_name") and receipt.get("account_id_hash") and receipt.get("server"))
    account_snapshot_present = isinstance(account_snapshot, Mapping) and bool(account_snapshot)
    verified = not reasons
    lifecycle_status = "RECEIPT_VERIFIED" if verified else "RECEIPT_MISMATCH"
    reconcile_status = "RECONCILED" if verified else "TERMINAL_LOCKED_FOR_SYMBOL"
    next_cycle_status = "NEXT_CYCLE_ALLOWED" if verified else "BLOCKED_BY_RECEIPT_MISMATCH"

    order = command_file_payload.get("order") or {}
    if not isinstance(order, Mapping):
        order = {}
    record = {
        "receipt_id": receipt.get("receipt_id"),
        "command_id": command_id,
        "cycle_id": (command_event or {}).get("cycle_id"),
        "intent_id": command_payload.get("intent_id"),
        "decision_id": order.get("decision_ref"),
        "agent_id": command_payload.get("agent_id"),
        "symbol": command_payload.get("symbol") or order.get("symbol"),
        "timeframe": command_payload.get("timeframe"),
        "strategy_setting": None,
        "command_path": command_path,
        "receipt_path": receipt.get("receipt_path"),
        "status": receipt.get("status"),
        "receipt_validation_status": lifecycle_status,
        "lifecycle_status": lifecycle_status,
        "reconcile_status": reconcile_status,
        "next_cycle_status": next_cycle_status,
        "raw_request_hash": receipt_hash,
        "expected_raw_request_hash": expected_hash,
        "raw_request_hash_match": hash_match,
        "raw_response_hash": receipt.get("raw_response_hash"),
        "terminal_name": receipt.get("terminal_name"),
        "terminal_build": receipt.get("terminal_build"),
        "account_id_hash": receipt.get("account_id_hash"),
        "server": receipt.get("server"),
        "broker_mode": receipt.get("broker_mode") or command_payload.get("broker_mode"),
        "live_mode": bool(receipt.get("live_mode", False)),
        "live_trading_allowed": bool(receipt.get("live_trading_allowed", False)),
        "broker_ticket": receipt.get("broker_ticket"),
        "filled_price": receipt.get("filled_price"),
        "filled_volume": receipt.get("filled_volume"),
        "slippage_pips": receipt.get("slippage_pips"),
        "commission": receipt.get("commission"),
        "swap": receipt.get("swap"),
        "error_code": receipt.get("error_code"),
        "account_snapshot_present": account_snapshot_present,
        "account_snapshot": dict(account_snapshot) if isinstance(account_snapshot, Mapping) else {},
        "terminal_identity_present": terminal_identity_present,
        "reasons": reasons,
        "receipt_sha256": _file_sha256(receipt.get("receipt_path")),
        "ingest_action": "PENDING",
        "event_ids": [],
    }
    return record


def _events_for_receipt(record: Mapping[str, Any]) -> List[Any]:
    cycle_id = str(record.get("cycle_id") or f"terminal-receipt-{record.get('command_id')}")
    source_refs = [path for path in (record.get("command_path"), record.get("receipt_path")) if path]
    base_kwargs = {
        "cycle_id": cycle_id,
        "symbol": record.get("symbol"),
        "timeframe": record.get("timeframe"),
        "strategy_setting": record.get("strategy_setting"),
        "source_refs": source_refs,
        "correlation_id": record.get("command_id"),
    }
    events = [
        make_agent_event(
            **base_kwargs,
            producer_agent_id="terminal_bridge_agent",
            consumer_agent_ids=["overseer_agent", "audit_memory_agent"],
            event_type="TERMINAL_RECEIPT_RECEIVED",
            subject=str(record.get("command_id")),
            payload=dict(record),
            status=str(record.get("lifecycle_status")),
            priority=20,
        )
    ]
    if record.get("lifecycle_status") == "RECEIPT_VERIFIED":
        events.append(
            make_agent_event(
                **base_kwargs,
                producer_agent_id="terminal_bridge_agent",
                consumer_agent_ids=["overseer_agent", "audit_memory_agent"],
                event_type="TERMINAL_RECEIPT_RECONCILED",
                subject=str(record.get("command_id")),
                payload=dict(record),
                status="RECONCILED",
                priority=15,
            )
        )
        events.append(
            make_agent_event(
                **base_kwargs,
                producer_agent_id="overseer_agent",
                consumer_agent_ids=["micro_scalp_agent", "hourly_intraday_agent", "terminal_bridge_agent"],
                event_type="NEXT_CYCLE_ALLOWED",
                subject=str(record.get("symbol") or record.get("command_id")),
                payload={
                    "command_id": record.get("command_id"),
                    "receipt_id": record.get("receipt_id"),
                    "intent_id": record.get("intent_id"),
                    "symbol": record.get("symbol"),
                    "timeframe": record.get("timeframe"),
                    "reason": "terminal receipt verified and reconciled",
                },
                status="NEXT_CYCLE_ALLOWED",
                priority=10,
            )
        )
    else:
        events.append(
            make_agent_event(
                **base_kwargs,
                producer_agent_id="terminal_bridge_agent",
                consumer_agent_ids=["overseer_agent", "audit_memory_agent"],
                event_type="TERMINAL_RECEIPT_MISMATCH",
                subject=str(record.get("command_id")),
                payload=dict(record),
                status="TERMINAL_LOCKED_FOR_SYMBOL",
                priority=5,
            )
        )
    return events


def _summarize_records(
    records: List[Mapping[str, Any]],
    appended_event_ids: List[str],
    event_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    new_records = [record for record in records if record.get("ingest_action") == "APPENDED_EVENTS"]
    verified = [record for record in new_records if record.get("lifecycle_status") == "RECEIPT_VERIFIED"]
    mismatches = [record for record in new_records if record.get("lifecycle_status") == "RECEIPT_MISMATCH"]
    return {
        "receipt_count": len(records),
        "new_receipt_count": len(new_records),
        "skipped_already_ingested_count": sum(1 for record in records if record.get("ingest_action") == "SKIPPED_ALREADY_INGESTED"),
        "verified_receipt_count": len(verified),
        "reconciled_receipt_count": len(verified),
        "next_cycle_allowed_count": len(verified),
        "receipt_mismatch_count": len(mismatches),
        "terminal_locked_count": len(mismatches),
        "appended_event_count": len(appended_event_ids),
        "appended_event_ids": appended_event_ids,
        "pending_receipt_count": event_summary.get("pending_receipt_count", 0),
        "event_count": event_summary.get("event_count", 0),
        "latest_event_id": event_summary.get("latest_event_id"),
        "latest_cycle_id": event_summary.get("latest_cycle_id"),
        "event_type_counts": event_summary.get("event_type_counts", {}),
        "status_counts": event_summary.get("status_counts", {}),
    }


def _next_action(summary: Mapping[str, Any]) -> str:
    if int(summary.get("receipt_count", 0) or 0) == 0:
        return "Attach/run the MT4 EA so it writes receipt JSON files into the mailbox receipts directory."
    if int(summary.get("receipt_mismatch_count", 0) or 0) > 0:
        return "Fix receipt mismatches before allowing more same-symbol commands."
    if int(summary.get("verified_receipt_count", 0) or 0) > 0:
        return "Wire overseer same-symbol routing to consume NEXT_CYCLE_ALLOWED events."
    return "No new receipts were ingested; keep monitoring the mailbox."


def _read_command_file(command_path: Any) -> Dict[str, Any]:
    if not command_path:
        return {}
    path = Path(str(command_path))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _file_sha256(path_value: Any) -> Optional[str]:
    if not path_value:
        return None
    path = Path(str(path_value))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()
