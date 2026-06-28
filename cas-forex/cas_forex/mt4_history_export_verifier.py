"""MT4 closed-history export verifier for CAS Forex.

This checks whether CASForexHistoryExporterEA.mq4 has produced a closed-history
JSON file inside the activated MT4 mailbox and whether terminal_history_ingest
can consume it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from cas_forex.mt4_terminal_session_verifier import (
    load_latest_mt4_terminal_session_verifier_report,
)
from cas_forex.terminal_history_ingest import ingest_terminal_history
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EA_SOURCE_PATH = REPO_ROOT / "mt4" / "Experts" / "CASForexHistoryExporterEA.mq4"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt4_history_export_verifier"
DEFAULT_INGEST_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_history_ingest"
REPORT_KIND = "cas_forex_mt4_history_export_verifier_report"
VERIFIER_SCHEMA = "cas_forex_mt4_history_export_verifier.v1"
EXPORT_SCHEMA = "cas_forex_mt4_closed_history_export.v1"
CLAIM_BOUNDARY = (
    "MT4 history export verifier inspects terminal-side closed-history export "
    "files and optional ingest results. It does not place live broker orders, "
    "create broker ACCEPT, deposit, withdraw, move bank/card funds, automate "
    "payouts, or override terminal receipt/history evidence."
)


class MT4HistoryExportVerifierError(ValueError):
    """Raised when the MT4 history export verifier report is invalid."""


def build_mt4_history_export_verifier_report(
    *,
    terminal_data_dir: Optional[Path | str] = None,
    mailbox_dir: Optional[Path | str] = None,
    history_export_path: Optional[Path | str] = None,
    status_path: Optional[Path | str] = None,
    ea_source_path: Path | str = DEFAULT_EA_SOURCE_PATH,
    session_report: Optional[Mapping[str, Any]] = None,
    memory_report: Optional[Mapping[str, Any]] = None,
    memory_report_dir: Optional[Path | str] = None,
    run_ingest: bool = True,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    ingest_output_dir: Path | str = DEFAULT_INGEST_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one MT4 history export verification report."""

    source = _source_status(Path(ea_source_path))
    session = _session_ref(session_report)
    mailbox = _resolve_mailbox(
        terminal_data_dir=terminal_data_dir,
        mailbox_dir=mailbox_dir,
        session_report=session_report,
    )
    export_path = Path(history_export_path) if history_export_path is not None else (
        mailbox / "history" / "cas_forex_closed_history.json" if mailbox is not None else None
    )
    exporter_status_path = Path(status_path) if status_path is not None else (
        mailbox / "status" / "cas_forex_closed_history_status.json" if mailbox is not None else None
    )
    export = _export_status(export_path)
    exporter_status = _status_file_status(exporter_status_path)
    ingest = None
    ingest_error = None
    if run_ingest and export.get("present") and export.get("parse_status") == "PARSED":
        try:
            ingest = ingest_terminal_history(
                source_paths=[Path(str(export_path))],
                memory_report=memory_report,
                memory_report_dir=memory_report_dir,
                output_dir=ingest_output_dir,
            )
        except Exception as exc:
            ingest_error = {"error_type": type(exc).__name__, "message": str(exc)}

    summary = _summary(
        source=source,
        mailbox=mailbox,
        export=export,
        exporter_status=exporter_status,
        ingest=ingest,
        ingest_error=ingest_error,
    )
    verifier_status = _verifier_status(summary)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "verifier_status": verifier_status,
        "schema": VERIFIER_SCHEMA,
        "ea_source": source,
        "session_report": session,
        "mailbox_dir": str(mailbox) if mailbox is not None else None,
        "history_export_path": str(export_path) if export_path is not None else None,
        "status_path": str(exporter_status_path) if exporter_status_path is not None else None,
        "history_export": export,
        "exporter_status": exporter_status,
        "ingest_report": _ingest_ref(ingest),
        "ingest_error": ingest_error,
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(verifier_status, export_path),
        "operator_commands": _operator_commands(mailbox),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_mt4_history_export_verifier_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_mt4_history_export_verifier_report(report)
    return report


def write_mt4_history_export_verifier_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt4_history_export_verifier_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt4-history-export-verifier-{stamp}-report.json"
    md_path = target_dir / f"mt4-history-export-verifier-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt4_history_export_verifier_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_mt4_history_export_verifier_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt4-history-export-verifier-*-report.json"))
    if not files:
        raise MT4HistoryExportVerifierError(f"No MT4 history export verifier reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt4_history_export_verifier_report(payload)
    return payload


def validate_mt4_history_export_verifier_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "verifier_status",
        "schema",
        "ea_source",
        "history_export",
        "exporter_status",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT4HistoryExportVerifierError(f"MT4 history export verifier report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT4HistoryExportVerifierError("unexpected MT4 history export verifier report_kind")
    if payload.get("schema") != VERIFIER_SCHEMA:
        raise MT4HistoryExportVerifierError("unexpected MT4 history export verifier schema")
    if "does not place live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT4HistoryExportVerifierError("MT4 history export verifier claim boundary must preserve execution boundary")
    if not isinstance(payload.get("summary"), Mapping):
        raise MT4HistoryExportVerifierError("summary must be an object")


def render_mt4_history_export_verifier_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex MT4 History Export Verifier",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('verifier_status')}`",
        f"Mailbox: `{report.get('mailbox_dir') or 'N/A'}`",
        f"History export: `{report.get('history_export_path') or 'N/A'}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- EA source present: `{summary.get('ea_source_present')}`",
        f"- Export present: `{summary.get('history_export_present')}`",
        f"- Export parse status: `{summary.get('history_export_parse_status')}`",
        f"- Export rows: `{summary.get('history_record_count')}`",
        f"- Exporter status: `{summary.get('exporter_status')}`",
        f"- Ingest status: `{summary.get('ingest_status')}`",
        f"- Memory updates: `{summary.get('memory_update_count')}`",
        "",
        f"Next action: {report.get('next_action')}",
    ]
    return "\n".join(lines) + "\n"


def _resolve_mailbox(
    *,
    terminal_data_dir: Optional[Path | str],
    mailbox_dir: Optional[Path | str],
    session_report: Optional[Mapping[str, Any]],
) -> Optional[Path]:
    if mailbox_dir is not None:
        return Path(mailbox_dir)
    if terminal_data_dir is not None:
        return Path(terminal_data_dir) / "MQL4" / "Files" / "CASForexMailbox"
    if session_report is None:
        try:
            session_report = load_latest_mt4_terminal_session_verifier_report()
        except Exception:
            session_report = None
    mailbox = (session_report or {}).get("mailbox_dir")
    return Path(str(mailbox)) if mailbox else None


def _session_ref(session_report: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if session_report is None:
        try:
            session_report = load_latest_mt4_terminal_session_verifier_report()
        except Exception:
            session_report = None
    return {
        "present": session_report is not None,
        "session_status": (session_report or {}).get("session_status"),
        "mailbox_dir": (session_report or {}).get("mailbox_dir"),
        "report_path": (session_report or {}).get("report_path")
        or ((session_report or {}).get("artifact_paths") or {}).get("json"),
        "summary": (session_report or {}).get("summary") or {},
    }


def _source_status(path: Path) -> Dict[str, Any]:
    present = path.exists()
    return {
        "path": str(path),
        "present": present,
        "sha256": _file_sha256(path) if present else None,
        "size_bytes": path.stat().st_size if present else 0,
    }


def _export_status(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {"present": False, "path": None, "parse_status": "NO_MAILBOX", "history_records": []}
    if not path.exists():
        return {"present": False, "path": str(path), "parse_status": "MISSING", "history_records": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "present": True,
            "path": str(path),
            "sha256": _file_sha256(path),
            "size_bytes": path.stat().st_size,
            "parse_status": "PARSE_FAILED",
            "parse_error": str(exc),
            "history_records": [],
        }
    rows = payload.get("history_records") if isinstance(payload, Mapping) else []
    if not isinstance(rows, list):
        rows = []
    return {
        "present": True,
        "path": str(path),
        "sha256": _file_sha256(path),
        "size_bytes": path.stat().st_size,
        "schema": payload.get("schema") if isinstance(payload, Mapping) else None,
        "schema_valid": isinstance(payload, Mapping) and payload.get("schema") == EXPORT_SCHEMA,
        "parse_status": "PARSED",
        "history_record_count": len(rows),
        "history_records": rows[:20],
        "summary": payload.get("summary") if isinstance(payload, Mapping) else {},
    }


def _status_file_status(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {"present": False, "path": None, "parse_status": "NO_MAILBOX"}
    if not path.exists():
        return {"present": False, "path": str(path), "parse_status": "MISSING"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "present": True,
            "path": str(path),
            "sha256": _file_sha256(path),
            "parse_status": "PARSE_FAILED",
            "parse_error": str(exc),
        }
    return {
        "present": True,
        "path": str(path),
        "sha256": _file_sha256(path),
        "schema": payload.get("schema") if isinstance(payload, Mapping) else None,
        "export_status": payload.get("export_status") if isinstance(payload, Mapping) else None,
        "exported_order_count": payload.get("exported_order_count") if isinstance(payload, Mapping) else None,
        "parse_status": "PARSED",
        "payload": payload,
    }


def _summary(
    *,
    source: Mapping[str, Any],
    mailbox: Optional[Path],
    export: Mapping[str, Any],
    exporter_status: Mapping[str, Any],
    ingest: Optional[Mapping[str, Any]],
    ingest_error: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    ingest_summary = (ingest or {}).get("summary") or {}
    return {
        "ea_source_present": bool(source.get("present")),
        "mailbox_ready": mailbox is not None and mailbox.exists(),
        "mailbox_dir": str(mailbox) if mailbox is not None else None,
        "history_export_present": bool(export.get("present")),
        "history_export_parse_status": export.get("parse_status"),
        "history_export_schema_valid": bool(export.get("schema_valid")),
        "history_record_count": int(export.get("history_record_count") or 0),
        "exporter_status_present": bool(exporter_status.get("present")),
        "exporter_status": exporter_status.get("export_status"),
        "ingest_status": (ingest or {}).get("ingest_status"),
        "ingest_error_type": (ingest_error or {}).get("error_type"),
        "memory_update_count": int(ingest_summary.get("memory_update_count") or 0),
        "unmatched_history_count": int(ingest_summary.get("unmatched_history_count") or 0),
        "closed_profit_count": int(ingest_summary.get("closed_profit_count") or 0),
        "closed_loss_count": int(ingest_summary.get("closed_loss_count") or 0),
        "net_profit_loss_account": float(ingest_summary.get("net_profit_loss_account") or 0.0),
    }


def _verifier_status(summary: Mapping[str, Any]) -> str:
    if not summary.get("ea_source_present"):
        return "MT4_HISTORY_EXPORT_SOURCE_MISSING"
    if not summary.get("mailbox_dir"):
        return "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL"
    if not summary.get("mailbox_ready"):
        return "MT4_HISTORY_EXPORT_NEEDS_ACTIVATED_MAILBOX"
    if not summary.get("history_export_present"):
        return "MT4_HISTORY_EXPORT_FILE_MISSING"
    if summary.get("history_export_parse_status") != "PARSED":
        return "MT4_HISTORY_EXPORT_PARSE_FAILED"
    if not summary.get("history_export_schema_valid"):
        return "MT4_HISTORY_EXPORT_SCHEMA_MISMATCH"
    if int(summary.get("history_record_count") or 0) == 0:
        return "MT4_HISTORY_EXPORT_EMPTY"
    if summary.get("ingest_error_type"):
        return "MT4_HISTORY_EXPORT_INGEST_FAILED"
    if summary.get("ingest_status") == "TERMINAL_HISTORY_INGEST_COMPLETE":
        return "MT4_HISTORY_EXPORT_INGEST_READY"
    return "MT4_HISTORY_EXPORT_READY_NO_INGEST"


def _next_action(status: str, export_path: Optional[Path]) -> str:
    if status == "MT4_HISTORY_EXPORT_SOURCE_MISSING":
        return "Restore mt4\\Experts\\CASForexHistoryExporterEA.mq4 before trying to verify closed-history export."
    if status == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL":
        return "Install/open MT4, activate the terminal data folder, then attach CASForexHistoryExporterEA.mq4."
    if status == "MT4_HISTORY_EXPORT_NEEDS_ACTIVATED_MAILBOX":
        return "Run MT4 terminal activation with --install so MQL4\\Files\\CASForexMailbox exists."
    if status == "MT4_HISTORY_EXPORT_FILE_MISSING":
        return f"Attach/run CASForexHistoryExporterEA.mq4 in MT4 and wait for {export_path} to appear."
    if status == "MT4_HISTORY_EXPORT_PARSE_FAILED":
        return "Open the closed-history export JSON and fix the malformed export before ingest."
    if status == "MT4_HISTORY_EXPORT_SCHEMA_MISMATCH":
        return "Regenerate the export with CASForexHistoryExporterEA.mq4 so schema cas_forex_mt4_closed_history_export.v1 is present."
    if status == "MT4_HISTORY_EXPORT_EMPTY":
        return "Confirm MT4 Account History has closed orders in the configured lookback window, then rerun the exporter."
    if status == "MT4_HISTORY_EXPORT_INGEST_FAILED":
        return "Inspect ingest_error, then rerun terminal_history_ingest against the export file."
    if status == "MT4_HISTORY_EXPORT_INGEST_READY":
        return "Rerun agent memory and daily rollup so closed MT4 PnL becomes learning evidence."
    return "Run terminal_history_ingest against the MT4 closed-history export."


def _operator_commands(mailbox: Optional[Path]) -> Dict[str, str]:
    if mailbox is None:
        return {
            "session_verifier": "py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir <MT4_DATA_DIR> --install --wait-seconds 10",
            "history_export_verifier": "py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox",
        }
    return {
        "history_export_verifier": f'py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir "{mailbox}"',
        "terminal_history_ingest": f'py -3.12 scripts/run_terminal_history_ingest.py --source "{mailbox}\\history\\cas_forex_closed_history.json"',
    }


def _ingest_ref(ingest: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    if ingest is None:
        return None
    return {
        "report_kind": ingest.get("report_kind"),
        "ingest_status": ingest.get("ingest_status"),
        "artifact_paths": ingest.get("artifact_paths") or {},
        "summary": ingest.get("summary") or {},
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
