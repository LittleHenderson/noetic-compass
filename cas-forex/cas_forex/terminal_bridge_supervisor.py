"""Terminal bridge supervisor for CAS Forex.

This module observes the MT4/MT5 bridge files: heartbeat, command mailbox,
receipt inbox, close-history exports, and the agent event journal. It reports
whether the terminal bridge is alive enough for the rest of the paper/demo
evidence chain to trust its files.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH, AgentEventStore
from cas_forex.agent_state import DEFAULT_MAILBOX_DIR
from cas_forex.broker.mt4_mailbox_bridge import COMMAND_SCHEMA, RECEIPT_SCHEMA
from cas_forex.terminal_history_ingest import DEFAULT_SOURCE_DIR as DEFAULT_HISTORY_SOURCE_DIR
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_bridge_supervisor"
REPORT_KIND = "cas_forex_terminal_bridge_supervisor_report"
HEARTBEAT_SCHEMA = "cas_forex_mt4_heartbeat.v1"
SUPERVISOR_SCHEMA = "cas_forex_terminal_bridge_supervisor.v1"
CLAIM_BOUNDARY = (
    "Terminal bridge supervisor observes paper/demo MT4/MT5 bridge heartbeat, "
    "mailbox, receipts, history exports, and event-journal freshness. It does "
    "not by itself execute live broker orders, create broker ACCEPT, deposit, "
    "withdraw, move bank/card funds, automate payouts, or override terminal "
    "receipt/history evidence."
)


class TerminalBridgeSupervisorError(ValueError):
    """Raised when terminal bridge supervisor evidence cannot be built."""


def build_terminal_bridge_supervisor_report(
    *,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    history_source_paths: Optional[Sequence[Path | str]] = None,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    now: Optional[str | datetime] = None,
    heartbeat_stale_seconds: int = 180,
    receipt_stale_seconds: int = 900,
    history_stale_seconds: int = 86400,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one terminal bridge supervision report."""

    now_dt = _parse_now(now)
    mailbox = Path(mailbox_dir)
    command_dir = mailbox / "commands"
    receipt_dir = mailbox / "receipts"
    heartbeat_path = mailbox / "heartbeat.json"
    history_sources = _history_sources(history_source_paths)

    heartbeat = _heartbeat_status(heartbeat_path, now_dt=now_dt, stale_seconds=heartbeat_stale_seconds)
    commands = _command_status(command_dir)
    receipts = _receipt_status(receipt_dir, commands, now_dt=now_dt, stale_seconds=receipt_stale_seconds)
    history = _history_status(history_sources, now_dt=now_dt, stale_seconds=history_stale_seconds)
    event_journal = _event_journal_status(event_log_path)
    account = _account_snapshot_status(heartbeat, receipts)
    alerts = _alerts(
        mailbox=mailbox,
        command_dir=command_dir,
        receipt_dir=receipt_dir,
        heartbeat=heartbeat,
        receipts=receipts,
        history=history,
        account=account,
        event_journal=event_journal,
    )
    summary = _summary(heartbeat, commands, receipts, history, event_journal, account, alerts)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "supervisor_status": _supervisor_status(summary),
        "schema": SUPERVISOR_SCHEMA,
        "as_of": now_dt.isoformat(),
        "mailbox_dir": str(mailbox),
        "command_dir": str(command_dir),
        "receipt_dir": str(receipt_dir),
        "heartbeat_path": str(heartbeat_path),
        "history_source_paths": [str(path) for path in history_sources],
        "event_log_path": str(Path(event_log_path)),
        "output_dir": str(Path(output_dir)),
        "thresholds": {
            "heartbeat_stale_seconds": heartbeat_stale_seconds,
            "receipt_stale_seconds": receipt_stale_seconds,
            "history_stale_seconds": history_stale_seconds,
        },
        "summary": summary,
        "heartbeat": heartbeat,
        "mailbox": {
            "mailbox_exists": mailbox.exists(),
            "command_dir_exists": command_dir.exists(),
            "receipt_dir_exists": receipt_dir.exists(),
        },
        "commands": commands,
        "receipts": receipts,
        "history": history,
        "event_journal": event_journal,
        "account_snapshot": account,
        "alerts": alerts,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_terminal_bridge_supervisor_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_terminal_bridge_supervisor_report(report)
    return report


def write_terminal_bridge_supervisor_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_terminal_bridge_supervisor_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"terminal-bridge-supervisor-{stamp}-report.json"
    md_path = target_dir / f"terminal-bridge-supervisor-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_terminal_bridge_supervisor_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_terminal_bridge_supervisor_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("terminal-bridge-supervisor-*-report.json"))
    if not files:
        raise TerminalBridgeSupervisorError(f"No terminal bridge supervisor reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_terminal_bridge_supervisor_report(payload)
    return payload


def validate_terminal_bridge_supervisor_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "supervisor_status",
        "schema",
        "as_of",
        "summary",
        "heartbeat",
        "mailbox",
        "commands",
        "receipts",
        "history",
        "event_journal",
        "account_snapshot",
        "alerts",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise TerminalBridgeSupervisorError(f"terminal bridge supervisor report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise TerminalBridgeSupervisorError("unexpected terminal bridge supervisor report_kind")
    if payload.get("schema") != SUPERVISOR_SCHEMA:
        raise TerminalBridgeSupervisorError("unexpected terminal bridge supervisor schema")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise TerminalBridgeSupervisorError("terminal bridge supervisor claim boundary must preserve execution boundary")


def render_terminal_bridge_supervisor_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Terminal Bridge Supervisor",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('supervisor_status')}`",
        f"As of: `{report.get('as_of')}`",
        f"Mailbox: `{report.get('mailbox_dir')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Heartbeat status: `{summary.get('heartbeat_status')}`",
        f"- Commands / receipts: `{summary.get('command_file_count')}` / `{summary.get('receipt_file_count')}`",
        f"- Pending command receipts: `{summary.get('pending_command_receipt_count')}`",
        f"- History files: `{summary.get('history_file_count')}`",
        f"- Account snapshot present: `{summary.get('account_snapshot_present')}`",
        f"- Alerts: `{summary.get('alert_count')}`",
        "",
        "## Alerts",
        "",
    ]
    for alert in report.get("alerts") or []:
        lines.append(f"- `{alert.get('severity')}` `{alert.get('alert_id')}`: {alert.get('plain_english')}")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _heartbeat_status(path: Path, *, now_dt: datetime, stale_seconds: int) -> Dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "present": False,
            "status": "MISSING",
            "schema": None,
            "age_seconds": None,
            "terminal": None,
            "terminal_build": None,
            "state": None,
            "account_id_hash": None,
            "server": None,
            "live_trading_allowed": None,
            "raw": {},
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "path": str(path),
            "present": True,
            "status": "INVALID_JSON",
            "schema": None,
            "age_seconds": _file_age_seconds(path, now_dt),
            "error": str(exc),
            "raw": {},
        }
    age = _heartbeat_age_seconds(path, payload, now_dt)
    status = "FRESH" if age is not None and age <= stale_seconds else "STALE"
    if payload.get("schema") != HEARTBEAT_SCHEMA:
        status = "UNEXPECTED_SCHEMA"
    if bool(payload.get("live_trading_allowed")):
        status = "LIVE_FLAG_VISIBLE"
    return {
        "path": str(path),
        "present": True,
        "status": status,
        "schema": payload.get("schema"),
        "age_seconds": age,
        "terminal": payload.get("terminal") or payload.get("terminal_name"),
        "terminal_build": payload.get("terminal_build"),
        "state": payload.get("state"),
        "account_id_hash": payload.get("account_id_hash"),
        "server": payload.get("server"),
        "live_trading_allowed": bool(payload.get("live_trading_allowed", False)),
        "raw": payload,
    }


def _command_status(command_dir: Path) -> Dict[str, Any]:
    records = [_read_command(path) for path in sorted(command_dir.glob("*.json"))] if command_dir.exists() else []
    return {
        "command_dir": str(command_dir),
        "command_dir_exists": command_dir.exists(),
        "command_file_count": len(records),
        "paper_command_count": sum(1 for item in records if item.get("broker_mode") == "PAPER_MT4"),
        "live_command_count": sum(1 for item in records if item.get("broker_mode") == "LIVE_MT4"),
        "invalid_command_count": sum(1 for item in records if item.get("parse_status") != "VALID"),
        "latest_command_id": records[-1].get("command_id") if records else None,
        "latest_command_created_at": records[-1].get("created_at") if records else None,
        "commands": records,
    }


def _receipt_status(
    receipt_dir: Path,
    commands: Mapping[str, Any],
    *,
    now_dt: datetime,
    stale_seconds: int,
) -> Dict[str, Any]:
    records = [_read_receipt(path, now_dt=now_dt, stale_seconds=stale_seconds) for path in sorted(receipt_dir.glob("*.json"))] if receipt_dir.exists() else []
    receipt_command_ids = {str(item.get("command_id")) for item in records if item.get("command_id")}
    command_ids = [str(item.get("command_id")) for item in commands.get("commands") or [] if item.get("command_id")]
    pending = [command_id for command_id in command_ids if command_id not in receipt_command_ids]
    latest_account = next((item.get("account_snapshot") for item in reversed(records) if item.get("account_snapshot")), None)
    return {
        "receipt_dir": str(receipt_dir),
        "receipt_dir_exists": receipt_dir.exists(),
        "receipt_file_count": len(records),
        "valid_receipt_count": sum(1 for item in records if item.get("parse_status") == "VALID"),
        "invalid_receipt_count": sum(1 for item in records if item.get("parse_status") != "VALID"),
        "stale_receipt_count": sum(1 for item in records if item.get("freshness_status") == "STALE"),
        "live_receipt_count": sum(1 for item in records if bool(item.get("live_mode")) or bool(item.get("live_trading_allowed"))),
        "pending_command_receipt_count": len(pending),
        "pending_command_ids": pending,
        "latest_receipt_id": records[-1].get("receipt_id") if records else None,
        "latest_receipt_status": records[-1].get("status") if records else None,
        "latest_account_snapshot": latest_account,
        "receipts": records,
    }


def _history_status(sources: Sequence[Path], *, now_dt: datetime, stale_seconds: int) -> Dict[str, Any]:
    files: List[Path] = []
    for source in sources:
        files.extend(_iter_history_files(source))
    records = []
    for path in sorted(dict.fromkeys(files)):
        age = _file_age_seconds(path, now_dt)
        records.append(
            {
                "path": str(path),
                "name": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(),
                "age_seconds": age,
                "freshness_status": "FRESH" if age is not None and age <= stale_seconds else "STALE",
            }
        )
    return {
        "history_source_paths": [str(path) for path in sources],
        "history_file_count": len(records),
        "fresh_history_file_count": sum(1 for item in records if item["freshness_status"] == "FRESH"),
        "stale_history_file_count": sum(1 for item in records if item["freshness_status"] == "STALE"),
        "latest_history_path": records[-1]["path"] if records else None,
        "history_files": records,
    }


def _event_journal_status(event_log_path: Path | str) -> Dict[str, Any]:
    path = Path(event_log_path)
    if not path.exists():
        return {
            "event_log_path": str(path),
            "present": False,
            "event_count": 0,
            "pending_receipt_count": 0,
            "open_receipt_command_ids": [],
        }
    summary = AgentEventStore(path).summary()
    return {
        "event_log_path": str(path),
        "present": True,
        **summary,
    }


def _account_snapshot_status(heartbeat: Mapping[str, Any], receipts: Mapping[str, Any]) -> Dict[str, Any]:
    latest = receipts.get("latest_account_snapshot")
    return {
        "account_id_hash": heartbeat.get("account_id_hash"),
        "server": heartbeat.get("server"),
        "account_snapshot_present": bool(latest),
        "latest_account_snapshot": latest,
        "source": "receipt" if latest else ("heartbeat_identity" if heartbeat.get("account_id_hash") else None),
    }


def _alerts(
    *,
    mailbox: Path,
    command_dir: Path,
    receipt_dir: Path,
    heartbeat: Mapping[str, Any],
    receipts: Mapping[str, Any],
    history: Mapping[str, Any],
    account: Mapping[str, Any],
    event_journal: Mapping[str, Any],
) -> List[Dict[str, str]]:
    alerts: List[Dict[str, str]] = []
    if not mailbox.exists():
        alerts.append(_alert("mailbox_missing", "HIGH", "Mailbox root does not exist; MT4/MT5 has not created or reached the shared mailbox."))
    if not command_dir.exists():
        alerts.append(_alert("command_dir_missing", "HIGH", "Command folder is missing; CAS cannot place paper/demo command files for the bridge."))
    if not receipt_dir.exists():
        alerts.append(_alert("receipt_dir_missing", "HIGH", "Receipt folder is missing; terminal receipt JSON cannot be observed."))
    if heartbeat.get("status") == "MISSING":
        alerts.append(_alert("heartbeat_missing", "HIGH", "No heartbeat.json is present; the EA/terminal has not proven it is awake."))
    elif heartbeat.get("status") == "STALE":
        alerts.append(_alert("heartbeat_stale", "HIGH", "Heartbeat exists but is stale; verify MT4/MT5 is still running and attached to the EA."))
    elif heartbeat.get("status") == "LIVE_FLAG_VISIBLE":
        alerts.append(_alert("live_trading_flag_visible", "HIGH", "Heartbeat says live trading is enabled; keep this visible for owner review and gate checks."))
    elif heartbeat.get("status") not in {"FRESH"}:
        alerts.append(_alert("heartbeat_invalid", "HIGH", "Heartbeat exists but is invalid or uses an unexpected schema."))
    if receipts.get("pending_command_receipt_count", 0) > 0:
        alerts.append(_alert("pending_command_receipts", "MEDIUM", "One or more command files do not yet have matching terminal receipt JSON."))
    if receipts.get("invalid_receipt_count", 0) > 0:
        alerts.append(_alert("invalid_receipts", "HIGH", "One or more receipt files are invalid or use an unexpected schema."))
    if receipts.get("live_receipt_count", 0) > 0:
        alerts.append(_alert("live_receipt_visible", "HIGH", "At least one receipt claims live mode or live trading allowed."))
    if event_journal.get("pending_receipt_count", 0) > 0:
        alerts.append(_alert("event_journal_pending_receipts", "MEDIUM", "The agent event journal still has open commands waiting for receipts."))
    if not account.get("account_snapshot_present"):
        alerts.append(_alert("account_snapshot_missing", "MEDIUM", "No latest receipt account snapshot is present; balance/equity cannot be observed from terminal receipts yet."))
    if history.get("history_file_count", 0) == 0:
        alerts.append(_alert("history_exports_missing", "MEDIUM", "No terminal close-history exports are present; closed PnL cannot enter memory yet."))
    return alerts


def _summary(
    heartbeat: Mapping[str, Any],
    commands: Mapping[str, Any],
    receipts: Mapping[str, Any],
    history: Mapping[str, Any],
    event_journal: Mapping[str, Any],
    account: Mapping[str, Any],
    alerts: Sequence[Mapping[str, str]],
) -> Dict[str, Any]:
    return {
        "heartbeat_status": heartbeat.get("status"),
        "heartbeat_present": bool(heartbeat.get("present")),
        "heartbeat_age_seconds": heartbeat.get("age_seconds"),
        "mailbox_ready": bool(commands.get("command_dir_exists") and receipts.get("receipt_dir_exists")),
        "command_file_count": commands.get("command_file_count", 0),
        "receipt_file_count": receipts.get("receipt_file_count", 0),
        "pending_command_receipt_count": receipts.get("pending_command_receipt_count", 0),
        "event_journal_pending_receipt_count": event_journal.get("pending_receipt_count", 0),
        "history_file_count": history.get("history_file_count", 0),
        "account_snapshot_present": bool(account.get("account_snapshot_present")),
        "live_trading_flag_visible": bool(heartbeat.get("live_trading_allowed")) or receipts.get("live_receipt_count", 0) > 0,
        "alert_count": len(alerts),
        "high_alert_count": sum(1 for alert in alerts if alert.get("severity") == "HIGH"),
        "medium_alert_count": sum(1 for alert in alerts if alert.get("severity") == "MEDIUM"),
        "terminal_bridge_ready": bool(
            heartbeat.get("status") == "FRESH"
            and commands.get("command_dir_exists")
            and receipts.get("receipt_dir_exists")
            and not bool(heartbeat.get("live_trading_allowed"))
        ),
    }


def _supervisor_status(summary: Mapping[str, Any]) -> str:
    if summary.get("live_trading_flag_visible"):
        return "TERMINAL_BRIDGE_LIVE_FLAG_VISIBLE"
    if summary.get("heartbeat_status") == "MISSING":
        return "TERMINAL_BRIDGE_HEARTBEAT_MISSING"
    if summary.get("heartbeat_status") == "STALE":
        return "TERMINAL_BRIDGE_HEARTBEAT_STALE"
    if summary.get("heartbeat_status") not in {"FRESH"}:
        return "TERMINAL_BRIDGE_HEARTBEAT_INVALID"
    if not summary.get("mailbox_ready"):
        return "TERMINAL_BRIDGE_MAILBOX_INCOMPLETE"
    if summary.get("pending_command_receipt_count", 0) > 0 or summary.get("event_journal_pending_receipt_count", 0) > 0:
        return "TERMINAL_BRIDGE_READY_PENDING_RECEIPTS"
    if not summary.get("account_snapshot_present"):
        return "TERMINAL_BRIDGE_READY_WAITING_FOR_ACCOUNT_SNAPSHOT"
    if summary.get("history_file_count", 0) == 0:
        return "TERMINAL_BRIDGE_READY_WAITING_FOR_HISTORY_EXPORT"
    return "TERMINAL_BRIDGE_READY"


def _next_action(summary: Mapping[str, Any]) -> str:
    status = _supervisor_status(summary)
    if status == "TERMINAL_BRIDGE_HEARTBEAT_MISSING":
        return "Attach and run CASForexBridgeEA.mq4 in MT4/MT5 with MailboxRoot pointed at the shared mailbox so heartbeat.json appears."
    if status == "TERMINAL_BRIDGE_HEARTBEAT_STALE":
        return "Verify the terminal and EA timer are still running, then rerun the supervisor."
    if status == "TERMINAL_BRIDGE_LIVE_FLAG_VISIBLE":
        return "Review the visible live-trading flag against owner and licensing gates before allowing any live command path."
    if status == "TERMINAL_BRIDGE_READY_PENDING_RECEIPTS":
        return "Let the terminal bridge process pending command files, then rerun receipt ingest, watcher, and supervisor."
    if status == "TERMINAL_BRIDGE_READY_WAITING_FOR_ACCOUNT_SNAPSHOT":
        return "Generate at least one valid terminal receipt with account_snapshot so balance/equity can be observed."
    if status == "TERMINAL_BRIDGE_READY_WAITING_FOR_HISTORY_EXPORT":
        return "Export or ingest MT4/MT5 closed account history so memory and daily rollup can see closed PnL."
    return "Keep supervisor running while terminal files arrive, then refresh the watcher and learning chain."


def _read_command(path: Path) -> Dict[str, Any]:
    payload = _read_json_file(path)
    if not payload.get("ok"):
        return {"path": str(path), "parse_status": "INVALID_JSON", "error": payload.get("error")}
    data = payload["data"]
    return {
        "path": str(path),
        "parse_status": "VALID" if data.get("schema") == COMMAND_SCHEMA else "UNEXPECTED_SCHEMA",
        "schema": data.get("schema"),
        "command_id": data.get("command_id"),
        "command_type": data.get("command_type"),
        "created_at": data.get("created_at"),
        "broker_mode": data.get("broker_mode"),
        "live_money_authorized": bool(data.get("live_money_authorized", False)),
        "raw_request_hash": data.get("raw_request_hash"),
    }


def _read_receipt(path: Path, *, now_dt: datetime, stale_seconds: int) -> Dict[str, Any]:
    payload = _read_json_file(path)
    age = _file_age_seconds(path, now_dt)
    if not payload.get("ok"):
        return {
            "path": str(path),
            "parse_status": "INVALID_JSON",
            "freshness_status": "FRESH" if age is not None and age <= stale_seconds else "STALE",
            "age_seconds": age,
            "error": payload.get("error"),
        }
    data = payload["data"]
    return {
        "path": str(path),
        "parse_status": "VALID" if data.get("schema") == RECEIPT_SCHEMA else "UNEXPECTED_SCHEMA",
        "schema": data.get("schema"),
        "receipt_id": data.get("receipt_id"),
        "command_id": data.get("command_id"),
        "status": data.get("status"),
        "created_at": data.get("created_at"),
        "terminal_name": data.get("terminal_name"),
        "terminal_build": data.get("terminal_build"),
        "account_id_hash": data.get("account_id_hash"),
        "server": data.get("server"),
        "broker_mode": data.get("broker_mode"),
        "live_mode": bool(data.get("live_mode", False)),
        "live_trading_allowed": bool(data.get("live_trading_allowed", False)),
        "account_snapshot": data.get("account_snapshot") if isinstance(data.get("account_snapshot"), Mapping) else None,
        "age_seconds": age,
        "freshness_status": "FRESH" if age is not None and age <= stale_seconds else "STALE",
    }


def _read_json_file(path: Path) -> Dict[str, Any]:
    try:
        return {"ok": True, "data": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _iter_history_files(source: Path) -> List[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        return []
    files: List[Path] = []
    for pattern in ("*.json", "*.csv", "*.txt", "*.html", "*.htm"):
        files.extend(sorted(path for path in source.glob(pattern) if path.is_file()))
    return files


def _history_sources(history_source_paths: Optional[Sequence[Path | str]]) -> List[Path]:
    if history_source_paths:
        return [Path(path) for path in history_source_paths]
    return [DEFAULT_HISTORY_SOURCE_DIR]


def _heartbeat_age_seconds(path: Path, payload: Mapping[str, Any], now_dt: datetime) -> Optional[float]:
    parsed = _parse_terminal_time(payload.get("time"))
    if parsed is not None:
        return max(0.0, (now_dt - parsed).total_seconds())
    return _file_age_seconds(path, now_dt)


def _file_age_seconds(path: Path, now_dt: datetime) -> Optional[float]:
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return max(0.0, (now_dt - modified).total_seconds())


def _parse_terminal_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    for candidate in (text, text.replace(".", "-")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def _parse_now(now: Optional[str | datetime]) -> datetime:
    if now is None:
        return utc_now()
    if isinstance(now, datetime):
        return now if now.tzinfo else now.replace(tzinfo=UTC)
    text = str(now).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _alert(alert_id: str, severity: str, plain_english: str) -> Dict[str, str]:
    return {"alert_id": alert_id, "severity": severity, "plain_english": plain_english}
