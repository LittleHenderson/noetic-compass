"""Operator-level MT4 terminal session verifier for CAS Forex.

This combines the terminal activation, ping roundtrip, bridge supervisor, and
watcher refresh chain into one report. It is the "is the MT4 terminal lane
ready to operate?" check, not an order placer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH
from cas_forex.mt4_ping_roundtrip import build_mt4_ping_roundtrip_report
from cas_forex.mt4_terminal_activation import (
    DEFAULT_EA_SOURCE_PATH,
    DEFAULT_MAILBOX_ROOT,
    build_mt4_terminal_activation_report,
)
from cas_forex.terminal_bridge_supervisor import build_terminal_bridge_supervisor_report
from cas_forex.terminal_history_ingest import DEFAULT_SOURCE_DIR as DEFAULT_HISTORY_SOURCE_DIR
from cas_forex.terminal_receipt_watcher import build_terminal_receipt_watcher_report
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt4_terminal_session_verifier"
REPORT_KIND = "cas_forex_mt4_terminal_session_verifier_report"
SESSION_SCHEMA = "cas_forex_mt4_terminal_session_verifier.v1"
CLAIM_BOUNDARY = (
    "MT4 terminal session verifier coordinates activation, ping, supervisor, "
    "watcher, and downstream evidence refresh checks. It does not place live "
    "broker orders, create broker ACCEPT, deposit, withdraw, move bank/card "
    "funds, or automate payouts."
)


class MT4TerminalSessionVerifierError(ValueError):
    """Raised when MT4 terminal session verification cannot be built."""


def build_mt4_terminal_session_verifier_report(
    *,
    terminal_data_dir: Optional[Path | str] = None,
    mailbox_dir: Optional[Path | str] = None,
    search_roots: Optional[Sequence[Path | str]] = None,
    ea_source_path: Path | str = DEFAULT_EA_SOURCE_PATH,
    mailbox_root: str = DEFAULT_MAILBOX_ROOT,
    use_common_files: bool = False,
    install_ea: bool = False,
    create_mailbox: bool = True,
    wait_seconds: float = 0.0,
    poll_interval_seconds: float = 0.25,
    write_ping: bool = True,
    existing_command_id: Optional[str] = None,
    run_refresh_chain: bool = True,
    force_refresh_chain: bool = True,
    history_source_paths: Optional[Sequence[Path | str]] = None,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    chain_output_root: Optional[Path | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    child_output_root: Optional[Path | str] = None,
    now: Optional[str] = None,
    write_child_reports: bool = True,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Run one operator-level MT4 session verification pass."""

    root = Path(child_output_root) if child_output_root is not None else REPO_ROOT / "evidence_runs"
    steps: list[Dict[str, Any]] = []
    reports: Dict[str, Any] = {}

    activation = _run_step(
        steps,
        "mt4_terminal_activation",
        lambda: build_mt4_terminal_activation_report(
            terminal_data_dir=terminal_data_dir,
            search_roots=search_roots,
            ea_source_path=ea_source_path,
            mailbox_root=mailbox_root,
            use_common_files=use_common_files,
            install_ea=install_ea,
            create_mailbox=create_mailbox,
            output_dir=root / "mt4_terminal_activation",
            write_report=write_child_reports,
        ),
        status_key="activation_status",
    )
    if activation is not None:
        reports["mt4_terminal_activation"] = _report_ref(activation, "activation_status")

    resolved_mailbox = _resolve_mailbox(mailbox_dir=mailbox_dir, activation=activation)
    history_sources = _history_sources(history_source_paths, resolved_mailbox)
    ping = _run_step(
        steps,
        "mt4_ping_roundtrip",
        lambda: build_mt4_ping_roundtrip_report(
            mailbox_dir=resolved_mailbox,
            activation_report=activation,
            output_dir=root / "mt4_ping_roundtrip",
            wait_seconds=wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
            write_ping=write_ping,
            existing_command_id=existing_command_id,
            create_mailbox=create_mailbox,
            write_report=write_child_reports,
        ),
        status_key="roundtrip_status",
    )
    if ping is not None:
        reports["mt4_ping_roundtrip"] = _report_ref(ping, "roundtrip_status")

    supervisor = None
    watcher = None
    if resolved_mailbox:
        supervisor = _run_step(
            steps,
            "terminal_bridge_supervisor",
            lambda: build_terminal_bridge_supervisor_report(
                mailbox_dir=resolved_mailbox,
                history_source_paths=history_sources,
                event_log_path=event_log_path,
                output_dir=root / "terminal_bridge_supervisor",
                now=now,
                write_report=write_child_reports,
            ),
            status_key="supervisor_status",
        )
        if supervisor is not None:
            reports["terminal_bridge_supervisor"] = _report_ref(supervisor, "supervisor_status")

        if run_refresh_chain:
            watcher = _run_step(
                steps,
                "terminal_receipt_watcher_refresh_chain",
                lambda: build_terminal_receipt_watcher_report(
                    mailbox_dir=resolved_mailbox,
                    history_source_paths=history_sources,
                    event_log_path=event_log_path,
                    output_dir=root / "terminal_receipt_watcher",
                    chain_output_root=chain_output_root or root,
                    run_chain=True,
                    force_run=force_refresh_chain,
                    now=now,
                    write_report=write_child_reports,
                ),
                status_key="watch_status",
            )
            if watcher is not None:
                reports["terminal_receipt_watcher"] = _report_ref(watcher, "watch_status")
    else:
        _append_skipped_step(
            steps,
            "terminal_bridge_supervisor",
            "No activated MT4 mailbox path exists yet.",
        )
        _append_skipped_step(
            steps,
            "terminal_receipt_watcher_refresh_chain",
            "No activated MT4 mailbox path exists yet.",
        )

    summary = _summary(
        activation=activation,
        ping=ping,
        supervisor=supervisor,
        watcher=watcher,
        steps=steps,
        mailbox_dir=resolved_mailbox,
    )
    status = _session_status(summary)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "session_status": status,
        "schema": SESSION_SCHEMA,
        "terminal_data_dir": str(terminal_data_dir) if terminal_data_dir is not None else None,
        "mailbox_dir": str(resolved_mailbox) if resolved_mailbox else None,
        "search_roots": [str(path) for path in search_roots] if search_roots else [],
        "event_log_path": str(Path(event_log_path)),
        "history_source_paths": [str(path) for path in history_sources],
        "output_dir": str(Path(output_dir)),
        "child_output_root": str(root),
        "settings": {
            "install_ea": bool(install_ea),
            "create_mailbox": bool(create_mailbox),
            "wait_seconds": float(wait_seconds),
            "poll_interval_seconds": float(poll_interval_seconds),
            "write_ping": bool(write_ping),
            "run_refresh_chain": bool(run_refresh_chain),
            "force_refresh_chain": bool(force_refresh_chain),
        },
        "step_results": steps,
        "child_reports": reports,
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, resolved_mailbox),
        "operator_commands": _operator_commands(resolved_mailbox),
    }
    if write_report:
        paths = write_mt4_terminal_session_verifier_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_mt4_terminal_session_verifier_report(report)
    return report


def write_mt4_terminal_session_verifier_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt4_terminal_session_verifier_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt4-terminal-session-verifier-{stamp}-report.json"
    md_path = target_dir / f"mt4-terminal-session-verifier-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt4_terminal_session_verifier_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_mt4_terminal_session_verifier_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt4-terminal-session-verifier-*-report.json"))
    if not files:
        raise MT4TerminalSessionVerifierError(f"No MT4 terminal session verifier reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt4_terminal_session_verifier_report(payload)
    return payload


def validate_mt4_terminal_session_verifier_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "session_status",
        "schema",
        "step_results",
        "child_reports",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT4TerminalSessionVerifierError(f"MT4 terminal session verifier report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT4TerminalSessionVerifierError("unexpected MT4 terminal session verifier report_kind")
    if payload.get("schema") != SESSION_SCHEMA:
        raise MT4TerminalSessionVerifierError("unexpected MT4 terminal session verifier schema")
    if "does not place live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT4TerminalSessionVerifierError("MT4 terminal session verifier claim boundary must preserve execution boundary")
    if not isinstance(payload.get("step_results"), list):
        raise MT4TerminalSessionVerifierError("step_results must be a list")
    if not isinstance(payload.get("summary"), Mapping):
        raise MT4TerminalSessionVerifierError("summary must be an object")


def render_mt4_terminal_session_verifier_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex MT4 Terminal Session Verifier",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('session_status')}`",
        f"Mailbox: `{report.get('mailbox_dir') or 'N/A'}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Activation: `{summary.get('activation_status')}`",
        f"- Ping: `{summary.get('roundtrip_status')}`",
        f"- Supervisor: `{summary.get('supervisor_status')}`",
        f"- Watcher: `{summary.get('watch_status')}`",
        f"- Heartbeat present: `{summary.get('heartbeat_present')}`",
        f"- Receipt present: `{summary.get('receipt_present')}`",
        f"- Refresh chain complete: `{summary.get('refresh_chain_complete')}`",
        f"- Failed steps: `{summary.get('failed_step_count')}`",
        "",
        "## Steps",
        "",
    ]
    for step in report.get("step_results") or []:
        lines.append(f"- `{step.get('step')}` `{step.get('status')}` `{step.get('status_label')}`: {step.get('message', '')}")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _run_step(
    steps: list[Dict[str, Any]],
    name: str,
    callback: Callable[[], Mapping[str, Any]],
    *,
    status_key: str,
) -> Optional[Dict[str, Any]]:
    started = utc_now()
    try:
        report = dict(callback())
    except Exception as exc:  # pragma: no cover - exercised through failure report shape in integration failures.
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
            "status_label": report.get(status_key),
            "message": report.get("next_action"),
            "started_at": started.isoformat(),
            "finished_at": utc_now().isoformat(),
            "artifact_paths": report.get("artifact_paths") or {},
            "summary": report.get("summary") or {},
        }
    )
    return report


def _append_skipped_step(steps: list[Dict[str, Any]], name: str, message: str) -> None:
    now = utc_now().isoformat()
    steps.append(
        {
            "step": name,
            "status": "SKIPPED",
            "status_label": "NO_ACTIVATED_MAILBOX",
            "message": message,
            "started_at": now,
            "finished_at": now,
        }
    )


def _resolve_mailbox(
    *,
    mailbox_dir: Optional[Path | str],
    activation: Optional[Mapping[str, Any]],
) -> Optional[Path]:
    if mailbox_dir is not None:
        return Path(mailbox_dir)
    selected = (activation or {}).get("selected_terminal") or {}
    selected_mailbox = selected.get("mailbox") or {}
    mailbox = selected_mailbox.get("mailbox_dir")
    if mailbox:
        return Path(str(mailbox))
    alignment = (activation or {}).get("path_alignment") or {}
    mailbox = alignment.get("recommended_cas_mailbox_dir")
    return Path(str(mailbox)) if mailbox else None


def _history_sources(
    history_source_paths: Optional[Sequence[Path | str]],
    mailbox_dir: Optional[Path],
) -> list[Path]:
    if history_source_paths:
        return [Path(path) for path in history_source_paths]
    sources = [DEFAULT_HISTORY_SOURCE_DIR]
    if mailbox_dir is not None:
        sources.append(Path(mailbox_dir) / "history")
    out: list[Path] = []
    seen: set[str] = set()
    for source in sources:
        key = str(source)
        if key in seen:
            continue
        seen.add(key)
        out.append(source)
    return out


def _summary(
    *,
    activation: Optional[Mapping[str, Any]],
    ping: Optional[Mapping[str, Any]],
    supervisor: Optional[Mapping[str, Any]],
    watcher: Optional[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    mailbox_dir: Optional[Path],
) -> Dict[str, Any]:
    activation_summary = (activation or {}).get("summary") or {}
    ping_summary = (ping or {}).get("summary") or {}
    supervisor_summary = (supervisor or {}).get("summary") or {}
    watcher_summary = (watcher or {}).get("summary") or {}
    chain_steps = list((watcher or {}).get("chain_steps") or [])
    failed_steps = [step for step in steps if step.get("status") == "FAILED"]
    skipped_steps = [step for step in steps if step.get("status") == "SKIPPED"]
    chain_failed = [step for step in chain_steps if step.get("status") == "FAILED"]
    return {
        "activation_status": (activation or {}).get("activation_status"),
        "roundtrip_status": (ping or {}).get("roundtrip_status"),
        "supervisor_status": (supervisor or {}).get("supervisor_status"),
        "watch_status": (watcher or {}).get("watch_status"),
        "mailbox_dir": str(mailbox_dir) if mailbox_dir else None,
        "mt4_candidate_count": int(activation_summary.get("mt4_candidate_count") or 0),
        "mt5_only_candidate_count": int(activation_summary.get("mt5_only_candidate_count") or 0),
        "selected_terminal_present": bool(activation_summary.get("selected_terminal_present")),
        "mailbox_ready": bool(ping_summary.get("mailbox_ready") or activation_summary.get("mailbox_ready")),
        "ping_written": bool(ping_summary.get("ping_written")),
        "heartbeat_present": bool(ping_summary.get("heartbeat_present") or activation_summary.get("heartbeat_present")),
        "receipt_present": bool(ping_summary.get("receipt_present")),
        "receipt_status": ping_summary.get("receipt_status"),
        "live_flag_visible": bool(ping_summary.get("live_flag_visible") or supervisor_summary.get("visible_live_flag")),
        "command_file_count": int(ping_summary.get("command_file_count") or supervisor_summary.get("command_file_count") or 0),
        "receipt_file_count": int(ping_summary.get("receipt_file_count") or supervisor_summary.get("receipt_file_count") or 0),
        "chain_requested": watcher is not None,
        "chain_step_count": len(chain_steps),
        "chain_step_complete_count": sum(1 for step in chain_steps if step.get("status") == "COMPLETE"),
        "chain_step_failed_count": len(chain_failed),
        "refresh_chain_complete": bool(chain_steps) and not chain_failed,
        "step_count": len(steps),
        "failed_step_count": len(failed_steps),
        "skipped_step_count": len(skipped_steps),
        "watcher_terminal_file_count": int(watcher_summary.get("terminal_file_count") or 0),
        "watcher_changed_file_count": int(watcher_summary.get("changed_file_count") or 0),
    }


def _session_status(summary: Mapping[str, Any]) -> str:
    if summary.get("failed_step_count", 0) > 0:
        return "MT4_SESSION_VERIFIER_FAILED"
    if summary.get("live_flag_visible"):
        return "MT4_SESSION_LIVE_FLAG_VISIBLE"
    if summary.get("activation_status") == "MT4_ACTIVATION_NEEDS_MT4_TERMINAL":
        return "MT4_SESSION_NEEDS_MT4_TERMINAL"
    if not summary.get("mailbox_ready"):
        return "MT4_SESSION_NEEDS_ACTIVATED_MAILBOX"
    if summary.get("roundtrip_status") == "MT4_PING_ROUNDTRIP_ACKNOWLEDGED":
        if summary.get("refresh_chain_complete"):
            return "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN"
        return "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_PENDING"
    if summary.get("ping_written"):
        return "MT4_SESSION_PING_WRITTEN_WAITING_FOR_TERMINAL"
    return "MT4_SESSION_WAITING_FOR_TERMINAL_ACTIVATION"


def _next_action(status: str, mailbox_dir: Optional[Path]) -> str:
    if status == "MT4_SESSION_NEEDS_MT4_TERMINAL":
        return "Install/open MT4, identify the terminal data folder with MQL4\\Experts, then rerun this verifier with --terminal-data-dir and --install."
    if status == "MT4_SESSION_NEEDS_ACTIVATED_MAILBOX":
        return "Run MT4 activation with --install so CASForexBridgeEA.mq4 and MQL4\\Files\\CASForexMailbox exist."
    if status == "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN":
        return "The terminal answered the ping and the evidence refresh chain ran. Next verify closed-history export coverage for completed trades."
    if status == "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_PENDING":
        return "The terminal answered the ping. Rerun with refresh chain enabled or run the watcher chain against the same mailbox."
    if status == "MT4_SESSION_LIVE_FLAG_VISIBLE":
        return "The terminal evidence shows a live flag. Keep this session isolated until explicit live execution requirements are satisfied."
    if status == "MT4_SESSION_VERIFIER_FAILED":
        return "Inspect failed step messages in this report, fix the first failed step, and rerun the session verifier."
    return f"Attach/run CASForexBridgeEA.mq4 inside MT4 and confirm heartbeat plus receipt JSON appear in {mailbox_dir or 'the activated mailbox'}."


def _operator_commands(mailbox_dir: Optional[Path]) -> Dict[str, str]:
    if mailbox_dir is None:
        return {
            "session_verifier": "py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir <MT4_DATA_DIR> --install --wait-seconds 10",
            "activation": "py -3.12 scripts/run_mt4_terminal_activation.py --terminal-data-dir <MT4_DATA_DIR> --install",
            "ping": "py -3.12 scripts/run_mt4_ping_roundtrip.py --mailbox-dir <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox --wait-seconds 10",
            "history_exporter": "Attach CASForexHistoryExporterEA.mq4 inside MT4 after CASForexBridgeEA.mq4; expected export: <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox\\history\\cas_forex_closed_history.json",
        }
    return {
        "session_verifier": f'py -3.12 scripts/run_mt4_terminal_session_verifier.py --mailbox-dir "{mailbox_dir}" --wait-seconds 10',
        "ping": f'py -3.12 scripts/run_mt4_ping_roundtrip.py --mailbox-dir "{mailbox_dir}" --wait-seconds 10',
        "supervisor": f'py -3.12 scripts/run_terminal_bridge_supervisor.py --mailbox-dir "{mailbox_dir}"',
        "watcher_chain": f'py -3.12 scripts/run_terminal_receipt_watcher.py --mailbox-dir "{mailbox_dir}" --force-run',
        "history_exporter": f'Attach CASForexHistoryExporterEA.mq4 inside MT4 with MailboxRoot=CASForexMailbox; expected export: "{mailbox_dir}\\history\\cas_forex_closed_history.json"',
    }


def _report_ref(report: Mapping[str, Any], status_key: str) -> Dict[str, Any]:
    return {
        "report_kind": report.get("report_kind"),
        "status": report.get(status_key),
        "report_path": report.get("report_path") or (report.get("artifact_paths") or {}).get("json"),
        "summary": report.get("summary") or {},
    }
