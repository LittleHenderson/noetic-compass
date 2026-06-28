"""MT4 terminal activation/staging report for CAS Forex.

The terminal bridge cannot produce heartbeat or receipt files until the MT4
Expert Advisor is visible inside the real terminal data folder and both sides
agree on the mailbox location. This module discovers MT4 terminal folders,
optionally stages CASForexBridgeEA.mq4, creates the MT4 file sandbox mailbox,
and writes a runbook-style evidence report.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from cas_forex.agent_state import DEFAULT_MAILBOX_DIR
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EA_SOURCE_PATH = REPO_ROOT / "mt4" / "Experts" / "CASForexBridgeEA.mq4"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt4_terminal_activation"
DEFAULT_MAILBOX_ROOT = "CASForexMailbox"
REPORT_KIND = "cas_forex_mt4_terminal_activation_report"
ACTIVATION_SCHEMA = "cas_forex_mt4_terminal_activation.v1"
CLAIM_BOUNDARY = (
    "MT4 terminal activation discovers and stages the CAS Forex MT4 Expert "
    "Advisor, mailbox folders, and operator runbook. It does not by itself "
    "execute live broker orders, create broker ACCEPT, deposit, withdraw, move "
    "bank/card funds, or automate payouts."
)


class MT4TerminalActivationError(ValueError):
    """Raised when MT4 terminal activation evidence cannot be built."""


def build_mt4_terminal_activation_report(
    *,
    terminal_data_dir: Optional[Path | str] = None,
    search_roots: Optional[Sequence[Path | str]] = None,
    ea_source_path: Path | str = DEFAULT_EA_SOURCE_PATH,
    mailbox_root: str = DEFAULT_MAILBOX_ROOT,
    use_common_files: bool = False,
    install_ea: bool = False,
    create_mailbox: bool = True,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one activation report and optionally stage the EA/mailbox."""

    source_path = Path(ea_source_path)
    source_info = _source_info(source_path)
    candidates = (
        [_terminal_candidate(Path(terminal_data_dir), source_path=source_path, mailbox_root=mailbox_root, use_common_files=use_common_files)]
        if terminal_data_dir
        else discover_mt4_terminal_roots(
            search_roots=search_roots,
            source_path=source_path,
            mailbox_root=mailbox_root,
            use_common_files=use_common_files,
        )
    )
    selected = dict(candidates[0]) if terminal_data_dir and candidates else _select_candidate(candidates)
    actions: list[dict[str, Any]] = []

    if selected and create_mailbox:
        actions.append(_ensure_mailbox_dirs(Path(selected["mailbox"]["mailbox_dir"])))
    if selected and install_ea:
        actions.append(_install_ea(source_path, selected))

    if selected:
        selected = _terminal_candidate(
            Path(selected["terminal_data_dir"]),
            source_path=source_path,
            mailbox_root=mailbox_root,
            use_common_files=use_common_files,
        )

    summary = _summary(
        candidates,
        selected=selected,
        source_info=source_info,
        install_ea=install_ea,
        create_mailbox=create_mailbox,
    )
    status = _activation_status(summary, selected=selected, install_requested=install_ea)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "activation_status": status,
        "schema": ACTIVATION_SCHEMA,
        "ea_source": source_info,
        "candidate_terminals": candidates,
        "selected_terminal": selected,
        "install_requested": bool(install_ea),
        "create_mailbox_requested": bool(create_mailbox),
        "actions": actions,
        "settings": _ea_settings(mailbox_root=mailbox_root, use_common_files=use_common_files),
        "path_alignment": _path_alignment(selected),
        "operator_commands": _operator_commands(selected, output_dir=Path(output_dir)),
        "activation_steps": _activation_steps(selected, mailbox_root=mailbox_root, use_common_files=use_common_files),
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, selected),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        written = write_mt4_terminal_activation_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in written.items()}
    validate_mt4_terminal_activation_report(report)
    return report


def discover_mt4_terminal_roots(
    *,
    search_roots: Optional[Sequence[Path | str]] = None,
    source_path: Path | str = DEFAULT_EA_SOURCE_PATH,
    mailbox_root: str = DEFAULT_MAILBOX_ROOT,
    use_common_files: bool = False,
) -> list[dict[str, Any]]:
    """Discover MetaQuotes terminal data folders and classify MT4 candidates."""

    roots = [Path(path) for path in search_roots] if search_roots else _default_search_roots()
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        root = Path(root).expanduser()
        if not root.exists():
            continue
        for candidate_dir in _candidate_dirs(root):
            key = str(_safe_resolve(candidate_dir)).lower()
            if key in seen:
                continue
            seen.add(key)
            if _looks_like_metaquotes_terminal(candidate_dir):
                found.append(
                    _terminal_candidate(
                        candidate_dir,
                        source_path=Path(source_path),
                        mailbox_root=mailbox_root,
                        use_common_files=use_common_files,
                    )
                )
    return sorted(found, key=lambda item: (0 if item["platform"] == "MT4" else 1, item["terminal_data_dir"].lower()))


def write_mt4_terminal_activation_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt4_terminal_activation_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt4-terminal-activation-{stamp}-report.json"
    md_path = target_dir / f"mt4-terminal-activation-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt4_terminal_activation_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_mt4_terminal_activation_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt4-terminal-activation-*-report.json"))
    if not files:
        raise MT4TerminalActivationError(f"No MT4 terminal activation reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt4_terminal_activation_report(payload)
    return payload


def validate_mt4_terminal_activation_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "activation_status",
        "schema",
        "ea_source",
        "candidate_terminals",
        "selected_terminal",
        "settings",
        "path_alignment",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT4TerminalActivationError(f"MT4 terminal activation report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT4TerminalActivationError("unexpected MT4 terminal activation report_kind")
    if payload.get("schema") != ACTIVATION_SCHEMA:
        raise MT4TerminalActivationError("unexpected MT4 terminal activation schema")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT4TerminalActivationError("MT4 terminal activation claim boundary must preserve execution boundary")
    selected = payload.get("selected_terminal")
    if selected is not None and not isinstance(selected, Mapping):
        raise MT4TerminalActivationError("selected_terminal must be an object or null")


def render_mt4_terminal_activation_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    selected = report.get("selected_terminal") or {}
    alignment = report.get("path_alignment") or {}
    lines = [
        "# CAS Forex MT4 Terminal Activation",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('activation_status')}`",
        f"Selected terminal: `{selected.get('terminal_data_dir', 'N/A')}`",
        f"EA target: `{(selected.get('ea') or {}).get('target_path', 'N/A')}`",
        f"Mailbox: `{(selected.get('mailbox') or {}).get('mailbox_dir', 'N/A')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- MT4 candidates: `{summary.get('mt4_candidate_count')}`",
        f"- MT5-only candidates: `{summary.get('mt5_only_candidate_count')}`",
        f"- EA source present: `{summary.get('ea_source_present')}`",
        f"- EA installed and matching: `{summary.get('ea_hash_matches')}`",
        f"- Mailbox ready: `{summary.get('mailbox_ready')}`",
        f"- Heartbeat present: `{summary.get('heartbeat_present')}`",
        f"- CAS mailbox alignment: `{alignment.get('alignment_status')}`",
        "",
        "## EA Settings",
        "",
    ]
    for key, value in (report.get("settings") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Activation Steps", ""])
    for step in report.get("activation_steps") or []:
        lines.append(f"- `{step.get('step')}`: {step.get('plain_english')}")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _source_info(path: Path) -> Dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": _sha256(path) if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else None,
    }


def _terminal_candidate(
    terminal_data_dir: Path,
    *,
    source_path: Path,
    mailbox_root: str,
    use_common_files: bool,
) -> Dict[str, Any]:
    terminal = Path(terminal_data_dir)
    mql4_dir = terminal / "MQL4"
    experts_dir = mql4_dir / "Experts"
    files_dir = mql4_dir / "Files"
    mql5_dir = terminal / "MQL5"
    mql5_experts_dir = mql5_dir / "Experts" / "Advisors"
    platform = "MT4" if mql4_dir.exists() or experts_dir.exists() or files_dir.exists() else ("MT5_ONLY" if mql5_dir.exists() else "UNKNOWN")
    target_path = experts_dir / source_path.name
    source_hash = _sha256(source_path) if source_path.exists() else None
    target_hash = _sha256(target_path) if target_path.exists() else None
    mailbox_dir = _mailbox_dir_for_terminal(terminal, mailbox_root=mailbox_root, use_common_files=use_common_files)
    return {
        "terminal_data_dir": str(terminal),
        "platform": platform,
        "mql4_dir": str(mql4_dir),
        "mql4_dir_exists": mql4_dir.exists(),
        "experts_dir": str(experts_dir),
        "experts_dir_exists": experts_dir.exists(),
        "files_dir": str(files_dir),
        "files_dir_exists": files_dir.exists(),
        "mql5_dir": str(mql5_dir),
        "mql5_dir_exists": mql5_dir.exists(),
        "mql5_experts_dir": str(mql5_experts_dir),
        "mql5_experts_dir_exists": mql5_experts_dir.exists(),
        "ea": {
            "target_path": str(target_path),
            "target_exists": target_path.exists(),
            "target_sha256": target_hash,
            "source_sha256": source_hash,
            "hash_matches": bool(source_hash and target_hash and source_hash == target_hash),
        },
        "mailbox": _mailbox_status(mailbox_dir),
    }


def _mailbox_status(mailbox_dir: Path) -> Dict[str, Any]:
    command_dir = mailbox_dir / "commands"
    receipt_dir = mailbox_dir / "receipts"
    archive_dir = mailbox_dir / "archive"
    heartbeat_path = mailbox_dir / "heartbeat.json"
    return {
        "mailbox_dir": str(mailbox_dir),
        "command_dir": str(command_dir),
        "receipt_dir": str(receipt_dir),
        "archive_dir": str(archive_dir),
        "heartbeat_path": str(heartbeat_path),
        "mailbox_exists": mailbox_dir.exists(),
        "command_dir_exists": command_dir.exists(),
        "receipt_dir_exists": receipt_dir.exists(),
        "archive_dir_exists": archive_dir.exists(),
        "mailbox_ready": mailbox_dir.exists() and command_dir.exists() and receipt_dir.exists() and archive_dir.exists(),
        "heartbeat_present": heartbeat_path.exists(),
        "command_file_count": _file_count(command_dir),
        "receipt_file_count": _file_count(receipt_dir),
    }


def _ensure_mailbox_dirs(mailbox_dir: Path) -> Dict[str, Any]:
    for child in (mailbox_dir, mailbox_dir / "commands", mailbox_dir / "receipts", mailbox_dir / "archive"):
        child.mkdir(parents=True, exist_ok=True)
    return {
        "action": "CREATE_MAILBOX_DIRS",
        "status": "COMPLETE",
        "mailbox_dir": str(mailbox_dir),
    }


def _install_ea(source_path: Path, selected: Mapping[str, Any]) -> Dict[str, Any]:
    if not source_path.exists():
        return {"action": "INSTALL_EA", "status": "FAILED", "reason": "EA source file is missing", "source_path": str(source_path)}
    if selected.get("platform") != "MT4":
        return {
            "action": "INSTALL_EA",
            "status": "FAILED",
            "reason": "Selected terminal is not an MT4 data folder with MQL4",
            "terminal_data_dir": selected.get("terminal_data_dir"),
        }
    target_path = Path((selected.get("ea") or {}).get("target_path", ""))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return {
        "action": "INSTALL_EA",
        "status": "COMPLETE",
        "source_path": str(source_path),
        "target_path": str(target_path),
        "target_sha256": _sha256(target_path),
    }


def _summary(
    candidates: Sequence[Mapping[str, Any]],
    *,
    selected: Optional[Mapping[str, Any]],
    source_info: Mapping[str, Any],
    install_ea: bool,
    create_mailbox: bool,
) -> Dict[str, Any]:
    selected_ea = (selected or {}).get("ea") or {}
    selected_mailbox = (selected or {}).get("mailbox") or {}
    return {
        "candidate_count": len(candidates),
        "mt4_candidate_count": sum(1 for item in candidates if item.get("platform") == "MT4"),
        "mt5_only_candidate_count": sum(1 for item in candidates if item.get("platform") == "MT5_ONLY"),
        "selected_terminal_present": selected is not None,
        "selected_platform": (selected or {}).get("platform"),
        "ea_source_present": bool(source_info.get("exists")),
        "ea_installed": bool(selected_ea.get("target_exists")),
        "ea_hash_matches": bool(selected_ea.get("hash_matches")),
        "mailbox_ready": bool(selected_mailbox.get("mailbox_ready")),
        "heartbeat_present": bool(selected_mailbox.get("heartbeat_present")),
        "command_file_count": int(selected_mailbox.get("command_file_count") or 0),
        "receipt_file_count": int(selected_mailbox.get("receipt_file_count") or 0),
        "install_requested": bool(install_ea),
        "create_mailbox_requested": bool(create_mailbox),
    }


def _activation_status(
    summary: Mapping[str, Any],
    *,
    selected: Optional[Mapping[str, Any]],
    install_requested: bool,
) -> str:
    if not summary.get("ea_source_present"):
        return "MT4_ACTIVATION_EA_SOURCE_MISSING"
    if selected is None:
        if summary.get("mt5_only_candidate_count", 0) > 0:
            return "MT4_ACTIVATION_NEEDS_MT4_TERMINAL"
        return "MT4_ACTIVATION_NEEDS_TERMINAL_PATH"
    if selected.get("platform") != "MT4":
        return "MT4_ACTIVATION_SELECTED_PATH_NOT_MT4"
    if not summary.get("ea_hash_matches"):
        return "MT4_ACTIVATION_INSTALL_FAILED" if install_requested else "MT4_ACTIVATION_DISCOVERED_NEEDS_INSTALL"
    if not summary.get("mailbox_ready"):
        return "MT4_ACTIVATION_NEEDS_MAILBOX"
    if summary.get("heartbeat_present"):
        return "MT4_ACTIVATION_HEARTBEAT_PRESENT"
    return "MT4_ACTIVATION_STAGED_NEEDS_TERMINAL_ATTACH"


def _next_action(status: str, selected: Optional[Mapping[str, Any]]) -> str:
    if status == "MT4_ACTIVATION_NEEDS_TERMINAL_PATH":
        return "Install/open MT4 once, then rerun activation with the terminal data folder path or let discovery find it."
    if status == "MT4_ACTIVATION_NEEDS_MT4_TERMINAL":
        return "Only MT5-style terminal folders were found. Install/open MT4, then rerun this activation lane for MQL4/Experts."
    if status == "MT4_ACTIVATION_SELECTED_PATH_NOT_MT4":
        return "Pick an MT4 terminal data folder that contains MQL4/Experts."
    if status == "MT4_ACTIVATION_DISCOVERED_NEEDS_INSTALL":
        return "Rerun with --install to copy CASForexBridgeEA.mq4 into MQL4/Experts and create the mailbox."
    if status == "MT4_ACTIVATION_INSTALL_FAILED":
        return "Review the activation actions, fix the EA source or terminal path, then rerun with --install."
    if status == "MT4_ACTIVATION_NEEDS_MAILBOX":
        return "Rerun activation with mailbox creation enabled so MQL4/Files/CASForexMailbox has commands, receipts, and archive folders."
    if status == "MT4_ACTIVATION_HEARTBEAT_PRESENT":
        return "Rerun terminal bridge supervisor against the activated mailbox and let receipt/history ingest continue."
    mailbox = ((selected or {}).get("mailbox") or {}).get("mailbox_dir", "the activated mailbox")
    return f"Open MT4, refresh Navigator, attach CASForexBridgeEA to a chart, use the reported EA settings, then verify heartbeat.json appears in {mailbox}."


def _ea_settings(*, mailbox_root: str, use_common_files: bool) -> Dict[str, Any]:
    return {
        "MailboxRoot": mailbox_root,
        "UseCommonFiles": bool(use_common_files),
        "LiveTradingAllowed": False,
        "SymbolSuffix": "",
        "TimerSeconds": 2,
        "MaxCommandsPerTimer": 10,
    }


def _path_alignment(selected: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    activated = ((selected or {}).get("mailbox") or {}).get("mailbox_dir")
    default_mailbox = str(DEFAULT_MAILBOX_DIR)
    aligned = bool(activated and _same_path(Path(activated), DEFAULT_MAILBOX_DIR))
    return {
        "cas_default_mailbox_dir": default_mailbox,
        "recommended_cas_mailbox_dir": activated,
        "alignment_status": "MATCHED" if aligned else ("NEEDS_ACTIVATED_MAILBOX_CONFIG" if activated else "NO_ACTIVATED_MAILBOX"),
        "recommended_env": {
            "CAS_FOREX_MT4_ENABLED": "true",
            "CAS_FOREX_MT4_MAILBOX_DIR": activated,
        }
        if activated
        else {},
        "plain_english": (
            "CAS command writers must use the same mailbox folder MT4 can read under MQL4/Files."
            if activated and not aligned
            else "CAS and MT4 mailbox paths are aligned." if aligned else "No activated MT4 mailbox path is available yet."
        ),
    }


def _operator_commands(selected: Optional[Mapping[str, Any]], *, output_dir: Path) -> Dict[str, Any]:
    if not selected:
        return {
            "activation_install": "py -3.12 scripts/run_mt4_terminal_activation.py --terminal-data-dir <MT4_DATA_DIR> --install",
            "supervisor_refresh": "py -3.12 scripts/run_terminal_bridge_supervisor.py --mailbox-dir <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox",
        }
    terminal = selected.get("terminal_data_dir")
    mailbox = ((selected or {}).get("mailbox") or {}).get("mailbox_dir")
    return {
        "activation_install": f'py -3.12 scripts/run_mt4_terminal_activation.py --terminal-data-dir "{terminal}" --install --output-dir "{output_dir}"',
        "supervisor_refresh": f'py -3.12 scripts/run_terminal_bridge_supervisor.py --mailbox-dir "{mailbox}"',
        "watcher_refresh": f'py -3.12 scripts/run_terminal_receipt_watcher.py --mailbox-dir "{mailbox}" --run-chain',
    }


def _activation_steps(
    selected: Optional[Mapping[str, Any]],
    *,
    mailbox_root: str,
    use_common_files: bool,
) -> list[dict[str, Any]]:
    target = ((selected or {}).get("ea") or {}).get("target_path", "MQL4\\Experts\\CASForexBridgeEA.mq4")
    mailbox = ((selected or {}).get("mailbox") or {}).get("mailbox_dir", "MQL4\\Files\\CASForexMailbox")
    return [
        {"step": 1, "plain_english": f"Confirm CASForexBridgeEA.mq4 is installed at {target}."},
        {"step": 2, "plain_english": "Open MT4, refresh Navigator, and attach CASForexBridgeEA to a chart."},
        {
            "step": 3,
            "plain_english": (
                f"Set MailboxRoot={mailbox_root}, UseCommonFiles={str(bool(use_common_files)).lower()}, "
                "LiveTradingAllowed=false, TimerSeconds=2, MaxCommandsPerTimer=10."
            ),
        },
        {"step": 4, "plain_english": f"Make CAS Forex command writers use the activated mailbox path: {mailbox}."},
        {"step": 5, "plain_english": "Rerun the bridge supervisor and confirm heartbeat.json plus receipt JSON appear."},
    ]


def _select_candidate(candidates: Sequence[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    for candidate in candidates:
        if candidate.get("platform") == "MT4":
            return dict(candidate)
    return None


def _mailbox_dir_for_terminal(terminal: Path, *, mailbox_root: str, use_common_files: bool) -> Path:
    if use_common_files:
        return terminal.parent / "Common" / "Files" / mailbox_root
    return terminal / "MQL4" / "Files" / mailbox_root


def _default_search_roots() -> list[Path]:
    roots: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / "MetaQuotes" / "Terminal")
    roots.append(Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal")
    roots.append(REPO_ROOT / "terminal_data")
    return roots


def _candidate_dirs(root: Path) -> Iterable[Path]:
    yield root
    if root.is_dir():
        for child in root.iterdir():
            if child.is_dir():
                yield child


def _looks_like_metaquotes_terminal(path: Path) -> bool:
    return (path / "MQL4").exists() or (path / "MQL5").exists()


def _file_count(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.glob("*.json") if path.is_file())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_path(left: Path, right: Path) -> bool:
    return str(_safe_resolve(left)).lower() == str(_safe_resolve(right)).lower()


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()
