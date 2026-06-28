"""MT4 ping roundtrip verifier for CAS Forex.

This lane proves the MT4 bridge is actually awake: CAS Forex writes one PING
command into the activated MT4 mailbox, then waits for the EA heartbeat and the
matching receipt JSON. It does not place orders.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from cas_forex.broker.mt4_mailbox_bridge import (
    COMMAND_SCHEMA,
    RECEIPT_SCHEMA,
    MT4MailboxBridge,
)
from cas_forex.mt4_terminal_activation import (
    DEFAULT_OUTPUT_DIR as DEFAULT_ACTIVATION_REPORT_DIR,
    MT4TerminalActivationError,
    load_latest_mt4_terminal_activation_report,
)
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt4_ping_roundtrip"
REPORT_KIND = "cas_forex_mt4_ping_roundtrip_report"
ROUNDTRIP_SCHEMA = "cas_forex_mt4_ping_roundtrip.v1"
HEARTBEAT_SCHEMA = "cas_forex_mt4_heartbeat.v1"
CLAIM_BOUNDARY = (
    "MT4 ping roundtrip writes one paper/demo PING command and observes the "
    "terminal heartbeat/receipt response. It does not place live broker "
    "orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, or "
    "automate payouts."
)


class MT4PingRoundtripError(ValueError):
    """Raised when MT4 ping roundtrip evidence cannot be built."""


def build_mt4_ping_roundtrip_report(
    *,
    mailbox_dir: Optional[Path | str] = None,
    activation_report: Optional[Mapping[str, Any]] = None,
    activation_report_dir: Path | str = DEFAULT_ACTIVATION_REPORT_DIR,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    wait_seconds: float = 0.0,
    poll_interval_seconds: float = 0.25,
    write_ping: bool = True,
    existing_command_id: Optional[str] = None,
    create_mailbox: bool = True,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Write or inspect one MT4 ping command and report the terminal response."""

    activation = _resolve_activation_report(activation_report, activation_report_dir)
    resolved_mailbox = str(Path(mailbox_dir)) if mailbox_dir else _mailbox_from_activation(activation)
    command: Optional[Dict[str, Any]] = None
    heartbeat: Dict[str, Any]
    receipt: Dict[str, Any]
    mailbox_state: Dict[str, Any]

    if not resolved_mailbox:
        heartbeat = _missing_heartbeat(None)
        receipt = _missing_receipt(existing_command_id)
        mailbox_state = _mailbox_state(None)
    else:
        mailbox_path = Path(resolved_mailbox)
        bridge = MT4MailboxBridge(mailbox_dir=mailbox_path)
        if create_mailbox:
            bridge.ensure_mailbox()

        if existing_command_id:
            command = _read_command_summary(mailbox_path, existing_command_id)
        elif write_ping:
            command = dict(bridge.write_ping())

        command_id = (command or {}).get("command_id") or existing_command_id
        heartbeat, receipt = _poll_terminal_response(
            mailbox_path,
            command_id=command_id,
            wait_seconds=max(float(wait_seconds), 0.0),
            poll_interval_seconds=max(float(poll_interval_seconds), 0.05),
        )
        mailbox_state = _mailbox_state(mailbox_path)

    summary = _summary(
        mailbox_state=mailbox_state,
        command=command,
        heartbeat=heartbeat,
        receipt=receipt,
        activation=activation,
    )
    status = _roundtrip_status(summary)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "roundtrip_status": status,
        "schema": ROUNDTRIP_SCHEMA,
        "mailbox_dir": resolved_mailbox,
        "activation_status": (activation or {}).get("activation_status"),
        "activation_report_path": (activation or {}).get("report_path"),
        "wait_seconds": float(wait_seconds),
        "poll_interval_seconds": float(poll_interval_seconds),
        "write_ping_requested": bool(write_ping),
        "existing_command_id": existing_command_id,
        "command": command,
        "expected_receipt_id": f"receipt-{summary['command_id']}" if summary.get("command_id") else None,
        "mailbox": mailbox_state,
        "heartbeat": heartbeat,
        "receipt": receipt,
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, resolved_mailbox),
        "operator_commands": _operator_commands(resolved_mailbox, output_dir=Path(output_dir)),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_mt4_ping_roundtrip_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_mt4_ping_roundtrip_report(report)
    return report


def write_mt4_ping_roundtrip_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt4_ping_roundtrip_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt4-ping-roundtrip-{stamp}-report.json"
    md_path = target_dir / f"mt4-ping-roundtrip-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt4_ping_roundtrip_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_mt4_ping_roundtrip_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt4-ping-roundtrip-*-report.json"))
    if not files:
        raise MT4PingRoundtripError(f"No MT4 ping roundtrip reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt4_ping_roundtrip_report(payload)
    return payload


def validate_mt4_ping_roundtrip_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "roundtrip_status",
        "schema",
        "mailbox_dir",
        "heartbeat",
        "receipt",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT4PingRoundtripError(f"MT4 ping roundtrip report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT4PingRoundtripError("unexpected MT4 ping roundtrip report_kind")
    if payload.get("schema") != ROUNDTRIP_SCHEMA:
        raise MT4PingRoundtripError("unexpected MT4 ping roundtrip schema")
    if "does not place live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT4PingRoundtripError("MT4 ping roundtrip claim boundary must preserve execution boundary")
    if not isinstance(payload.get("summary"), Mapping):
        raise MT4PingRoundtripError("summary must be an object")


def render_mt4_ping_roundtrip_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex MT4 Ping Roundtrip",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('roundtrip_status')}`",
        f"Mailbox: `{report.get('mailbox_dir') or 'N/A'}`",
        f"Command: `{summary.get('command_id') or 'N/A'}`",
        f"Receipt: `{report.get('expected_receipt_id') or 'N/A'}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Ping written: `{summary.get('ping_written')}`",
        f"- Heartbeat present: `{summary.get('heartbeat_present')}`",
        f"- Receipt present: `{summary.get('receipt_present')}`",
        f"- Receipt status: `{summary.get('receipt_status')}`",
        f"- Raw request hash match: `{summary.get('raw_request_hash_match')}`",
        f"- Live flag visible: `{summary.get('live_flag_visible')}`",
        "",
        f"Next action: {report.get('next_action')}",
    ]
    return "\n".join(lines) + "\n"


def _resolve_activation_report(
    activation_report: Optional[Mapping[str, Any]],
    activation_report_dir: Path | str,
) -> Optional[Dict[str, Any]]:
    if activation_report is not None:
        return dict(activation_report)
    try:
        return load_latest_mt4_terminal_activation_report(activation_report_dir)
    except MT4TerminalActivationError:
        return None


def _mailbox_from_activation(activation: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not activation:
        return None
    alignment = activation.get("path_alignment") or {}
    mailbox = alignment.get("recommended_cas_mailbox_dir")
    if mailbox:
        return str(mailbox)
    selected = activation.get("selected_terminal") or {}
    selected_mailbox = selected.get("mailbox") or {}
    mailbox = selected_mailbox.get("mailbox_dir")
    return str(mailbox) if mailbox else None


def _poll_terminal_response(
    mailbox_dir: Path,
    *,
    command_id: Optional[str],
    wait_seconds: float,
    poll_interval_seconds: float,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    deadline = time.monotonic() + wait_seconds
    heartbeat = _read_heartbeat(mailbox_dir / "heartbeat.json")
    receipt = _read_receipt(mailbox_dir, command_id)
    while time.monotonic() < deadline:
        if heartbeat.get("present") and receipt.get("present"):
            break
        time.sleep(min(poll_interval_seconds, max(deadline - time.monotonic(), 0.0)))
        heartbeat = _read_heartbeat(mailbox_dir / "heartbeat.json")
        receipt = _read_receipt(mailbox_dir, command_id)
    return heartbeat, receipt


def _read_command_summary(mailbox_dir: Path, command_id: str) -> Dict[str, Any]:
    path = mailbox_dir / "commands" / f"{command_id}.json"
    if not path.exists():
        return {
            "command_id": command_id,
            "command_path": str(path),
            "present": False,
            "command_type": None,
            "raw_request_hash": None,
        }
    payload = _read_json(path)
    return {
        "command_id": command_id,
        "command_path": str(path),
        "present": True,
        "schema": payload.get("schema"),
        "command_type": payload.get("command_type"),
        "broker_mode": payload.get("broker_mode"),
        "live_money_authorized": bool(payload.get("live_money_authorized", False)),
        "raw_request_hash": payload.get("raw_request_hash"),
    }


def _read_heartbeat(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _missing_heartbeat(path)
    try:
        payload = _read_json(path)
    except Exception as exc:
        return {
            "path": str(path),
            "present": True,
            "valid": False,
            "schema": None,
            "terminal": None,
            "state": None,
            "live_trading_allowed": None,
            "error": str(exc),
            "raw": {},
        }
    return {
        "path": str(path),
        "present": True,
        "valid": payload.get("schema") == HEARTBEAT_SCHEMA,
        "schema": payload.get("schema"),
        "terminal": payload.get("terminal") or payload.get("terminal_name"),
        "terminal_build": payload.get("terminal_build"),
        "state": payload.get("state"),
        "account_id_hash": payload.get("account_id_hash"),
        "server": payload.get("server"),
        "time": payload.get("time"),
        "live_trading_allowed": bool(payload.get("live_trading_allowed", False)),
        "raw": payload,
    }


def _read_receipt(mailbox_dir: Path, command_id: Optional[str]) -> Dict[str, Any]:
    if not command_id:
        return _missing_receipt(None)
    direct_path = mailbox_dir / "receipts" / f"receipt-{command_id}.json"
    paths = [direct_path]
    if not direct_path.exists():
        paths.extend(sorted((mailbox_dir / "receipts").glob("*.json")) if (mailbox_dir / "receipts").exists() else [])
    for path in paths:
        if not path.exists():
            continue
        try:
            payload = _read_json(path)
        except Exception as exc:
            return {
                "path": str(path),
                "present": True,
                "valid": False,
                "schema": None,
                "receipt_id": None,
                "command_id": command_id,
                "status": None,
                "raw_request_hash": None,
                "live_mode": None,
                "live_trading_allowed": None,
                "error": str(exc),
                "raw": {},
            }
        if str(payload.get("command_id")) != str(command_id):
            continue
        return {
            "path": str(path),
            "present": True,
            "valid": payload.get("schema") == RECEIPT_SCHEMA,
            "schema": payload.get("schema"),
            "receipt_id": payload.get("receipt_id"),
            "command_id": payload.get("command_id"),
            "status": payload.get("status"),
            "created_at": payload.get("created_at"),
            "raw_request_hash": payload.get("raw_request_hash"),
            "raw_response_hash": payload.get("raw_response_hash"),
            "terminal_name": payload.get("terminal_name"),
            "terminal_build": payload.get("terminal_build"),
            "account_id_hash": payload.get("account_id_hash"),
            "server": payload.get("server"),
            "broker_mode": payload.get("broker_mode"),
            "live_mode": bool(payload.get("live_mode", False)),
            "live_trading_allowed": bool(payload.get("live_trading_allowed", False)),
            "account_snapshot_present": bool(payload.get("account_snapshot")),
            "message": payload.get("message"),
            "error_code": payload.get("error_code"),
            "raw": payload,
        }
    return _missing_receipt(command_id)


def _mailbox_state(mailbox_dir: Optional[Path]) -> Dict[str, Any]:
    if mailbox_dir is None:
        return {
            "mailbox_dir": None,
            "mailbox_exists": False,
            "command_dir_exists": False,
            "receipt_dir_exists": False,
            "archive_dir_exists": False,
            "command_file_count": 0,
            "receipt_file_count": 0,
        }
    command_dir = mailbox_dir / "commands"
    receipt_dir = mailbox_dir / "receipts"
    archive_dir = mailbox_dir / "archive"
    return {
        "mailbox_dir": str(mailbox_dir),
        "mailbox_exists": mailbox_dir.exists(),
        "command_dir_exists": command_dir.exists(),
        "receipt_dir_exists": receipt_dir.exists(),
        "archive_dir_exists": archive_dir.exists(),
        "command_file_count": _json_file_count(command_dir),
        "receipt_file_count": _json_file_count(receipt_dir),
    }


def _summary(
    *,
    mailbox_state: Mapping[str, Any],
    command: Optional[Mapping[str, Any]],
    heartbeat: Mapping[str, Any],
    receipt: Mapping[str, Any],
    activation: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    command_id = (command or {}).get("command_id")
    command_hash = (command or {}).get("raw_request_hash")
    receipt_hash = receipt.get("raw_request_hash")
    raw_hash_match = bool(command_hash and receipt_hash and str(command_hash) == str(receipt_hash))
    live_flag_visible = bool(heartbeat.get("live_trading_allowed")) or bool(receipt.get("live_mode")) or bool(receipt.get("live_trading_allowed"))
    return {
        "activation_status": (activation or {}).get("activation_status"),
        "mailbox_ready": bool(
            mailbox_state.get("mailbox_exists")
            and mailbox_state.get("command_dir_exists")
            and mailbox_state.get("receipt_dir_exists")
            and mailbox_state.get("archive_dir_exists")
        ),
        "command_id": command_id,
        "command_path": (command or {}).get("command_path"),
        "ping_written": bool(command_id and (command or {}).get("command_path")),
        "command_schema_valid": (command or {}).get("schema", COMMAND_SCHEMA) == COMMAND_SCHEMA if command else False,
        "command_type": (command or {}).get("command_type"),
        "heartbeat_present": bool(heartbeat.get("present")),
        "heartbeat_valid": bool(heartbeat.get("valid")),
        "receipt_present": bool(receipt.get("present")),
        "receipt_valid": bool(receipt.get("valid")),
        "receipt_status": receipt.get("status"),
        "raw_request_hash_match": raw_hash_match,
        "live_flag_visible": live_flag_visible,
        "command_file_count": int(mailbox_state.get("command_file_count") or 0),
        "receipt_file_count": int(mailbox_state.get("receipt_file_count") or 0),
    }


def _roundtrip_status(summary: Mapping[str, Any]) -> str:
    if not summary.get("mailbox_ready"):
        return "MT4_PING_NEEDS_ACTIVATED_MAILBOX"
    if not summary.get("ping_written"):
        return "MT4_PING_NO_COMMAND_WRITTEN"
    if summary.get("live_flag_visible"):
        return "MT4_PING_LIVE_FLAG_VISIBLE"
    if summary.get("receipt_present") and not summary.get("receipt_valid"):
        return "MT4_PING_RECEIPT_INVALID"
    if summary.get("receipt_present") and not summary.get("raw_request_hash_match"):
        return "MT4_PING_RECEIPT_MISMATCH"
    if summary.get("receipt_present") and summary.get("receipt_status") != "ACKNOWLEDGED":
        return "MT4_PING_RECEIPT_NOT_ACKNOWLEDGED"
    if summary.get("receipt_present") and not summary.get("heartbeat_present"):
        return "MT4_PING_RECEIPT_ACK_HEARTBEAT_MISSING"
    if summary.get("heartbeat_present") and not summary.get("receipt_present"):
        return "MT4_PING_HEARTBEAT_PRESENT_WAITING_FOR_RECEIPT"
    if summary.get("heartbeat_present") and summary.get("receipt_present"):
        return "MT4_PING_ROUNDTRIP_ACKNOWLEDGED"
    return "MT4_PING_WRITTEN_WAITING_FOR_TERMINAL"


def _next_action(status: str, mailbox_dir: Optional[str]) -> str:
    if status == "MT4_PING_NEEDS_ACTIVATED_MAILBOX":
        return "Run MT4 terminal activation against a real MT4 data folder first; no activated mailbox exists for a ping roundtrip yet."
    if status == "MT4_PING_ROUNDTRIP_ACKNOWLEDGED":
        return "Roundtrip is alive. Rerun bridge supervisor, terminal watcher, receipt ingest, memory, daily rollup, and session autowake against this mailbox."
    if status == "MT4_PING_HEARTBEAT_PRESENT_WAITING_FOR_RECEIPT":
        return "The EA heartbeat is visible, but the ping receipt is missing. Confirm MaxCommandsPerTimer, command folder path, and EA timer status."
    if status == "MT4_PING_RECEIPT_ACK_HEARTBEAT_MISSING":
        return "The ping receipt exists but heartbeat is missing. Confirm the EA can write heartbeat.json to the same mailbox root."
    if status == "MT4_PING_LIVE_FLAG_VISIBLE":
        return "The terminal or receipt shows a live flag. Keep this lane isolated until owner live execution requirements are explicitly satisfied."
    if status in {"MT4_PING_RECEIPT_INVALID", "MT4_PING_RECEIPT_MISMATCH", "MT4_PING_RECEIPT_NOT_ACKNOWLEDGED"}:
        return "Inspect the receipt JSON and EA logs, then rerun the ping roundtrip after the mismatch is fixed."
    return f"Attach/run CASForexBridgeEA.mq4 inside MT4 and confirm it writes heartbeat plus receipt JSON in {mailbox_dir or 'the activated mailbox'}."


def _operator_commands(mailbox_dir: Optional[str], *, output_dir: Path) -> Dict[str, Any]:
    if not mailbox_dir:
        return {
            "activation_install": "py -3.12 scripts/run_mt4_terminal_activation.py --terminal-data-dir <MT4_DATA_DIR> --install",
            "roundtrip": "py -3.12 scripts/run_mt4_ping_roundtrip.py --mailbox-dir <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox --wait-seconds 10",
        }
    return {
        "roundtrip": f'py -3.12 scripts/run_mt4_ping_roundtrip.py --mailbox-dir "{mailbox_dir}" --wait-seconds 10 --output-dir "{output_dir}"',
        "supervisor_refresh": f'py -3.12 scripts/run_terminal_bridge_supervisor.py --mailbox-dir "{mailbox_dir}"',
        "watcher_refresh": f'py -3.12 scripts/run_terminal_receipt_watcher.py --mailbox-dir "{mailbox_dir}" --run-chain',
    }


def _missing_heartbeat(path: Optional[Path]) -> Dict[str, Any]:
    return {
        "path": str(path) if path else None,
        "present": False,
        "valid": False,
        "schema": None,
        "terminal": None,
        "state": None,
        "live_trading_allowed": None,
        "raw": {},
    }


def _missing_receipt(command_id: Optional[str]) -> Dict[str, Any]:
    return {
        "path": None,
        "present": False,
        "valid": False,
        "schema": None,
        "receipt_id": f"receipt-{command_id}" if command_id else None,
        "command_id": command_id,
        "status": None,
        "raw_request_hash": None,
        "live_mode": None,
        "live_trading_allowed": None,
        "raw": {},
    }


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MT4PingRoundtripError(f"Expected JSON object at {path}")
    return payload


def _json_file_count(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.glob("*.json") if path.is_file())
