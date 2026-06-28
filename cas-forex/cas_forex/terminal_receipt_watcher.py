"""Terminal receipt/history watcher for the CAS Forex agent desk.

The terminal bridge writes receipt JSON and close-history exports. This module
is the desk coordinator that notices those file changes and reruns the existing
ingest-memory-research-strategy-rollup-autowake chain.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.agent_memory import build_agent_memory_report
from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.agent_research_queue import build_agent_research_queue_report
from cas_forex.agent_state import DEFAULT_MAILBOX_DIR
from cas_forex.daily_learning_rollup import build_daily_learning_rollup_report
from cas_forex.session_autowake_runner import build_session_autowake_report
from cas_forex.strategy_dev_queue import build_strategy_dev_queue_report
from cas_forex.strategy_patch_runner import build_strategy_patch_runner_report
from cas_forex.terminal_history_ingest import DEFAULT_SOURCE_DIR as DEFAULT_HISTORY_SOURCE_DIR
from cas_forex.terminal_history_ingest import ingest_terminal_history
from cas_forex.terminal_receipt_ingest import ingest_terminal_receipts
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_receipt_watcher"
REPORT_KIND = "cas_forex_terminal_receipt_watcher_report"
FILE_SCHEMA = "cas_forex_terminal_file_fingerprint.v1"
CLAIM_BOUNDARY = (
    "Terminal receipt watcher detects paper/demo MT4/MT5 receipt and history "
    "file changes and reruns CAS Forex evidence refresh steps. It does not by "
    "itself execute live broker orders, create broker ACCEPT, deposit, "
    "withdraw, move bank/card funds, automate payouts, or override terminal "
    "receipt/history evidence."
)


class TerminalReceiptWatcherError(ValueError):
    """Raised when the terminal receipt watcher cannot build evidence."""


def build_terminal_receipt_watcher_report(
    *,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    history_source_paths: Optional[Sequence[Path | str]] = None,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    chain_output_root: Optional[Path | str] = None,
    previous_report: Optional[Mapping[str, Any]] = None,
    run_chain: bool = True,
    force_run: bool = False,
    now: Optional[str | datetime] = None,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one watcher pass and optionally rerun the downstream evidence chain."""

    now_dt = _parse_now(now)
    mailbox = Path(mailbox_dir)
    history_sources = _history_sources(history_source_paths)
    fingerprints = collect_terminal_file_fingerprints(mailbox_dir=mailbox, history_source_paths=history_sources)
    previous = dict(previous_report) if previous_report is not None else _load_previous_report_or_empty(output_dir)
    changes = diff_file_fingerprints(previous.get("file_fingerprints") or [], fingerprints)
    should_run = bool(force_run or (run_chain and _change_count(changes) > 0))

    chain_steps: List[Dict[str, Any]] = []
    chain_reports: Dict[str, Any] = {}
    if should_run:
        chain_steps, chain_reports = _run_refresh_chain(
            mailbox_dir=mailbox,
            history_source_paths=history_sources,
            event_log_path=event_log_path,
            chain_output_root=chain_output_root,
            now=now_dt,
        )

    summary = _summary(fingerprints, changes, chain_steps, should_run)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "watch_status": _watch_status(summary, run_chain=run_chain, force_run=force_run),
        "schema": FILE_SCHEMA,
        "as_of": now_dt.isoformat(),
        "mailbox_dir": str(mailbox),
        "receipt_dir": str(mailbox / "receipts"),
        "history_source_paths": [str(path) for path in history_sources],
        "event_log_path": str(Path(event_log_path)),
        "output_dir": str(Path(output_dir)),
        "chain_output_root": str(Path(chain_output_root)) if chain_output_root is not None else None,
        "summary": summary,
        "file_fingerprints": fingerprints,
        "file_changes": changes,
        "chain_steps": chain_steps,
        "chain_reports": chain_reports,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_terminal_receipt_watcher_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_terminal_receipt_watcher_report(report)
    return report


def collect_terminal_file_fingerprints(
    *,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    history_source_paths: Optional[Sequence[Path | str]] = None,
) -> List[Dict[str, Any]]:
    """Return deterministic fingerprints for terminal receipt/history files."""

    mailbox = Path(mailbox_dir)
    sources: List[tuple[str, Path, tuple[str, ...]]] = [
        ("terminal_receipt", mailbox / "receipts", ("*.json",)),
    ]
    for source in _history_sources(history_source_paths):
        sources.append(("terminal_history", source, ("*.json", "*.csv", "*.txt", "*.html", "*.htm")))

    out: List[Dict[str, Any]] = []
    seen: set[Path] = set()
    for role, source, patterns in sources:
        for path in _iter_source_files(source, patterns):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(_fingerprint_file(path, role=role))
    return sorted(out, key=lambda item: (str(item["file_role"]), str(item["path"])))


def diff_file_fingerprints(
    previous: Iterable[Mapping[str, Any]],
    current: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Compare prior/current file fingerprints by role and path."""

    previous_map = {_fingerprint_key(item): dict(item) for item in previous if isinstance(item, Mapping)}
    current_map = {_fingerprint_key(item): dict(item) for item in current if isinstance(item, Mapping)}
    changes: List[Dict[str, Any]] = []
    for key, item in current_map.items():
        prior = previous_map.get(key)
        if prior is None:
            status = "NEW"
        elif _fingerprint_changed(prior, item):
            status = "CHANGED"
        else:
            status = "UNCHANGED"
        changes.append(_change_record(status, item, prior))
    for key, prior in previous_map.items():
        if key not in current_map:
            changes.append(_change_record("DELETED", {}, prior))

    counts: Dict[str, int] = {"NEW": 0, "CHANGED": 0, "DELETED": 0, "UNCHANGED": 0}
    for change in changes:
        counts[str(change["change_status"])] = counts.get(str(change["change_status"]), 0) + 1
    return {
        "change_counts": counts,
        "changed_files": sorted(changes, key=lambda item: (str(item.get("file_role")), str(item.get("path")))),
    }


def write_terminal_receipt_watcher_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_terminal_receipt_watcher_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"terminal-receipt-watcher-{stamp}-report.json"
    md_path = target_dir / f"terminal-receipt-watcher-{stamp}-report.md"
    jsonl_path = target_dir / f"terminal-receipt-watcher-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_terminal_receipt_watcher_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for change in (report.get("file_changes") or {}).get("changed_files") or []:
            handle.write(json.dumps(change, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_terminal_receipt_watcher_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("terminal-receipt-watcher-*-report.json"))
    if not files:
        raise TerminalReceiptWatcherError(f"No terminal receipt watcher reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_terminal_receipt_watcher_report(payload)
    return payload


def run_terminal_receipt_watcher_loop(
    *,
    interval_seconds: float = 30.0,
    iterations: Optional[int] = None,
    pass_runner: Optional[Callable[..., Mapping[str, Any]]] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Run repeated watcher passes. Tests can inject ``pass_runner``."""

    if interval_seconds < 0:
        raise TerminalReceiptWatcherError("interval_seconds must be non-negative")
    runner = pass_runner or build_terminal_receipt_watcher_report
    reports: List[Dict[str, Any]] = []
    completed = 0
    while iterations is None or completed < iterations:
        previous = reports[-1] if reports else kwargs.pop("previous_report", None)
        report = dict(runner(previous_report=previous, **kwargs))
        reports.append(report)
        completed += 1
        if iterations is not None and completed >= iterations:
            break
        time.sleep(interval_seconds)
    return reports


def validate_terminal_receipt_watcher_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "watch_status",
        "schema",
        "as_of",
        "summary",
        "file_fingerprints",
        "file_changes",
        "chain_steps",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise TerminalReceiptWatcherError(f"terminal receipt watcher report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise TerminalReceiptWatcherError("unexpected terminal receipt watcher report_kind")
    if payload.get("schema") != FILE_SCHEMA:
        raise TerminalReceiptWatcherError("unexpected terminal receipt watcher schema")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise TerminalReceiptWatcherError("terminal receipt watcher claim boundary must preserve execution boundary")
    if not isinstance(payload.get("file_fingerprints"), list):
        raise TerminalReceiptWatcherError("file_fingerprints must be a list")
    if not isinstance(payload.get("chain_steps"), list):
        raise TerminalReceiptWatcherError("chain_steps must be a list")


def render_terminal_receipt_watcher_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    changes = report.get("file_changes") or {}
    counts = changes.get("change_counts") or {}
    lines = [
        "# CAS Forex Terminal Receipt Watcher",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('watch_status')}`",
        f"As of: `{report.get('as_of')}`",
        f"Receipt dir: `{report.get('receipt_dir')}`",
        f"History sources: `{report.get('history_source_paths')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Terminal files: `{summary.get('terminal_file_count')}`",
        f"- Receipt files: `{summary.get('receipt_file_count')}`",
        f"- History files: `{summary.get('history_file_count')}`",
        f"- New/changed/deleted: `{counts.get('NEW', 0)}` / `{counts.get('CHANGED', 0)}` / `{counts.get('DELETED', 0)}`",
        f"- Chain requested: `{summary.get('chain_requested')}`",
        f"- Chain steps complete: `{summary.get('chain_step_complete_count')}`",
        f"- Chain steps failed: `{summary.get('chain_step_failed_count')}`",
        "",
        "## Chain Steps",
        "",
    ]
    for step in report.get("chain_steps") or []:
        lines.append(f"- `{step.get('step')}`: `{step.get('status')}` `{step.get('status_label')}`")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _run_refresh_chain(
    *,
    mailbox_dir: Path,
    history_source_paths: Sequence[Path],
    event_log_path: Path | str,
    chain_output_root: Optional[Path | str],
    now: datetime,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    dirs = _chain_dirs(chain_output_root)
    steps: List[Dict[str, Any]] = []
    reports: Dict[str, Any] = {}

    receipt_report = _run_step(
        steps,
        "terminal_receipt_ingest",
        lambda: ingest_terminal_receipts(
            mailbox_dir=mailbox_dir,
            event_log_path=event_log_path,
            output_dir=dirs["terminal_receipt_ingest"],
        ),
    )
    if receipt_report is None:
        return steps, reports
    reports["terminal_receipt_ingest"] = _report_ref(receipt_report, "ingest_status")

    history_report = _run_step(
        steps,
        "terminal_history_ingest",
        lambda: ingest_terminal_history(
            source_paths=history_source_paths,
            output_dir=dirs["terminal_history_ingest"],
        ),
    )
    if history_report is None:
        return steps, reports
    reports["terminal_history_ingest"] = _report_ref(history_report, "ingest_status")

    memory_report = _run_step(
        steps,
        "agent_memory",
        lambda: build_agent_memory_report(
            event_log_path=event_log_path,
            terminal_history_report_dir=dirs["terminal_history_ingest"],
            output_dir=dirs["agent_memory"],
        ),
    )
    if memory_report is None:
        return steps, reports
    reports["agent_memory"] = _report_ref(memory_report, "memory_status")

    research_report = _run_step(
        steps,
        "agent_research_queue",
        lambda: build_agent_research_queue_report(
            memory_report=memory_report,
            output_dir=dirs["agent_research_queue"],
        ),
    )
    if research_report is None:
        return steps, reports
    reports["agent_research_queue"] = _report_ref(research_report, "queue_status")

    strategy_dev_report = _run_step(
        steps,
        "strategy_dev_queue",
        lambda: build_strategy_dev_queue_report(
            research_queue_report=research_report,
            memory_report=memory_report,
            output_dir=dirs["strategy_dev_queue"],
        ),
    )
    if strategy_dev_report is None:
        return steps, reports
    reports["strategy_dev_queue"] = _report_ref(strategy_dev_report, "queue_status")

    patch_report = _run_step(
        steps,
        "strategy_patch_runner",
        lambda: build_strategy_patch_runner_report(
            strategy_dev_queue_report=strategy_dev_report,
            output_dir=dirs["strategy_patch_runner"],
        ),
    )
    if patch_report is None:
        return steps, reports
    reports["strategy_patch_runner"] = _report_ref(patch_report, "runner_status")

    rollup_report = _run_step(
        steps,
        "daily_learning_rollup",
        lambda: build_daily_learning_rollup_report(
            memory_report=memory_report,
            terminal_history_report=history_report,
            research_queue_report=research_report,
            strategy_dev_queue_report=strategy_dev_report,
            strategy_patch_runner_report=patch_report,
            output_dir=dirs["daily_learning_rollup"],
        ),
    )
    if rollup_report is None:
        return steps, reports
    reports["daily_learning_rollup"] = _report_ref(rollup_report, "rollup_status")

    autowake_report = _run_step(
        steps,
        "session_autowake",
        lambda: build_session_autowake_report(
            now=now,
            daily_learning_rollup=rollup_report,
            execute_cycle=False,
            output_dir=dirs["session_autowake_runner"],
        ),
    )
    if autowake_report is not None:
        reports["session_autowake"] = _report_ref(autowake_report, "autowake_status")
    return steps, reports


def _run_step(
    steps: List[Dict[str, Any]],
    name: str,
    callback: Callable[[], Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    started = utc_now()
    try:
        report = dict(callback())
    except Exception as exc:  # pragma: no cover - exercised through failure report shape if a chain step fails.
        steps.append(
            {
                "step": name,
                "status": "FAILED",
                "status_label": type(exc).__name__,
                "message": str(exc),
                "started_at": started.isoformat(),
                "finished_at": utc_now().isoformat(),
            }
        )
        return None
    steps.append(
        {
            "step": name,
            "status": "COMPLETE",
            "status_label": _status_label(report),
            "started_at": started.isoformat(),
            "finished_at": utc_now().isoformat(),
            "artifact_paths": report.get("artifact_paths") or {},
            "summary": report.get("summary") or {},
        }
    )
    return report


def _chain_dirs(chain_output_root: Optional[Path | str]) -> Dict[str, Path]:
    if chain_output_root is None:
        root = REPO_ROOT / "evidence_runs"
    else:
        root = Path(chain_output_root)
    return {
        "terminal_receipt_ingest": root / "terminal_receipt_ingest",
        "terminal_history_ingest": root / "terminal_history_ingest",
        "agent_memory": root / "agent_memory",
        "agent_research_queue": root / "agent_research_queue",
        "strategy_dev_queue": root / "strategy_dev_queue",
        "strategy_patch_runner": root / "strategy_patch_runner",
        "daily_learning_rollup": root / "daily_learning_rollup",
        "session_autowake_runner": root / "session_autowake_runner",
    }


def _report_ref(report: Mapping[str, Any], status_key: str) -> Dict[str, Any]:
    return {
        "report_kind": report.get("report_kind"),
        "status": report.get(status_key),
        "report_path": report.get("report_path") or (report.get("artifact_paths") or {}).get("json"),
        "summary": report.get("summary") or {},
    }


def _status_label(report: Mapping[str, Any]) -> str:
    for key in ("ingest_status", "memory_status", "queue_status", "runner_status", "rollup_status", "autowake_status"):
        if report.get(key):
            return str(report[key])
    return str(report.get("report_kind") or "COMPLETE")


def _summary(
    fingerprints: Sequence[Mapping[str, Any]],
    changes: Mapping[str, Any],
    chain_steps: Sequence[Mapping[str, Any]],
    chain_requested: bool,
) -> Dict[str, Any]:
    change_count = _change_count(changes)
    receipt_count = sum(1 for item in fingerprints if item.get("file_role") == "terminal_receipt")
    history_count = sum(1 for item in fingerprints if item.get("file_role") == "terminal_history")
    complete = sum(1 for step in chain_steps if step.get("status") == "COMPLETE")
    failed = sum(1 for step in chain_steps if step.get("status") == "FAILED")
    return {
        "terminal_file_count": len(fingerprints),
        "receipt_file_count": receipt_count,
        "history_file_count": history_count,
        "changed_file_count": change_count,
        "chain_requested": chain_requested,
        "chain_step_count": len(chain_steps),
        "chain_step_complete_count": complete,
        "chain_step_failed_count": failed,
        "latest_completed_step": next((step.get("step") for step in reversed(chain_steps) if step.get("status") == "COMPLETE"), None),
        "first_failed_step": next((step.get("step") for step in chain_steps if step.get("status") == "FAILED"), None),
    }


def _watch_status(summary: Mapping[str, Any], *, run_chain: bool, force_run: bool) -> str:
    if summary.get("chain_step_failed_count"):
        return "WATCHER_CHAIN_FAILED"
    if summary.get("chain_step_complete_count"):
        return "WATCHER_FORCE_RAN" if force_run else "WATCHER_CHAIN_RAN"
    if not summary.get("terminal_file_count"):
        return "WATCHER_IDLE_NO_TERMINAL_FILES"
    if summary.get("changed_file_count") and not run_chain:
        return "WATCHER_CHANGE_DETECTED_NO_CHAIN_RUN"
    if summary.get("changed_file_count"):
        return "WATCHER_CHANGE_DETECTED_CHAIN_NOT_RUN"
    return "WATCHER_IDLE_NO_CHANGES"


def _next_action(summary: Mapping[str, Any]) -> str:
    if summary.get("chain_step_failed_count"):
        return f"Fix the failed watcher chain step `{summary.get('first_failed_step')}` and rerun the watcher."
    if summary.get("chain_step_complete_count"):
        return "Review refreshed ingest, memory, queue, rollup, and autowake reports; keep the terminal watcher running for new MT4/MT5 files."
    if not summary.get("terminal_file_count"):
        return "Start or verify the MT4/MT5 terminal bridge so receipt JSON or closed-history exports appear in the watched folders."
    if summary.get("changed_file_count"):
        return "Rerun the watcher with chain execution enabled to refresh CAS Forex evidence from the changed terminal files."
    return "No terminal file changes detected; keep watching receipt/history folders."


def _iter_source_files(source: Path, patterns: Sequence[str]) -> List[Path]:
    if source.is_dir():
        files: List[Path] = []
        for pattern in patterns:
            files.extend(sorted(path for path in source.glob(pattern) if path.is_file()))
        return files
    if source.is_file():
        return [source]
    return []


def _fingerprint_file(path: Path, *, role: str) -> Dict[str, Any]:
    stat = path.stat()
    content = path.read_bytes()
    return {
        "schema": FILE_SCHEMA,
        "file_role": role,
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        "mtime_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _fingerprint_key(item: Mapping[str, Any]) -> str:
    return f"{item.get('file_role')}::{item.get('path')}"


def _fingerprint_changed(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return any(previous.get(key) != current.get(key) for key in ("sha256", "size_bytes", "mtime_ns"))


def _change_record(status: str, current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> Dict[str, Any]:
    base = current if current else previous or {}
    return {
        "schema": FILE_SCHEMA,
        "change_status": status,
        "file_role": base.get("file_role"),
        "path": base.get("path"),
        "name": base.get("name"),
        "sha256": current.get("sha256"),
        "previous_sha256": (previous or {}).get("sha256"),
        "size_bytes": current.get("size_bytes"),
        "previous_size_bytes": (previous or {}).get("size_bytes"),
        "modified_at": current.get("modified_at"),
        "previous_modified_at": (previous or {}).get("modified_at"),
    }


def _change_count(changes: Mapping[str, Any]) -> int:
    counts = changes.get("change_counts") or {}
    return int(counts.get("NEW", 0)) + int(counts.get("CHANGED", 0)) + int(counts.get("DELETED", 0))


def _history_sources(history_source_paths: Optional[Sequence[Path | str]]) -> List[Path]:
    if history_source_paths:
        return [Path(path) for path in history_source_paths]
    return [DEFAULT_HISTORY_SOURCE_DIR]


def _load_previous_report_or_empty(output_dir: Path | str) -> Dict[str, Any]:
    try:
        return load_latest_terminal_receipt_watcher_report(output_dir)
    except TerminalReceiptWatcherError:
        return {"file_fingerprints": []}


def _parse_now(now: Optional[str | datetime]) -> datetime:
    if now is None:
        return utc_now()
    if isinstance(now, datetime):
        return now if now.tzinfo else now.replace(tzinfo=UTC)
    text = str(now).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
