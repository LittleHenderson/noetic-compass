"""Read-only MT5 market-data diagnostic for WASTE broker-truth readiness.

This report answers one narrow live-readiness question: can the local MT5
terminal provide broker-grade candles and tick spread for the active index lane?
It never sends, modifies, or closes orders.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.config import config
from cas_forex.market_data.connector import MT5TerminalMarketDataConnector
from cas_forex.time_utils import utc_now
from cas_forex.waste_market_data import DEFAULT_WASTE_BARS, DEFAULT_WASTE_TIMEFRAME

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "mt5-market-data-diagnostic.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "mt5-market-data-diagnostic-audit.jsonl"

REPORT_KIND = "cas_forex_mt5_market_data_diagnostic"
STATUS_READY = "MT5_MARKET_DATA_READY"
STATUS_NOT_READY = "MT5_MARKET_DATA_NOT_READY"
STATUS_ERROR = "MT5_MARKET_DATA_DIAGNOSTIC_ERROR"
SYMBOL_READY = "BROKER_TRUTH_READY"
SYMBOL_NOT_READY = "NO_BROKER_GRADE_CANDLES"

DEFAULT_SYMBOLS = ("NAS100", "US30")
COMMON_MT5_TERMINAL_PATHS = (
    r"C:\Program Files\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
)

CLAIM_BOUNDARY = (
    "MT5 market-data diagnostic reads broker-terminal candles and tick spread "
    "only. It does not place orders, close positions, call a broker execution "
    "bridge, create broker ACCEPT, create owner ACCEPT, authorize live trading, "
    "deposit, withdraw, transfer funds, automate payouts, register edge tokens, "
    "or turn fallback data into LICENSED evidence."
)


class MT5MarketDataDiagnosticLog:
    def __init__(
        self,
        state_path: Path | str = DEFAULT_STATE_PATH,
        audit_path: Path | str = DEFAULT_AUDIT_PATH,
    ) -> None:
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path)

    def record(self, report: Mapping[str, Any]) -> dict[str, Any]:
        record = {
            "audit_id": stable_ledger_id(
                "mt5-market-data-diagnostic",
                str(report.get("generated_at") or ""),
                str(report.get("status") or ""),
                json.dumps(report.get("symbols") or [], sort_keys=True, default=str),
            ),
            "action": "MT5_MARKET_DATA_DIAGNOSTIC",
            "timestamp": utc_now().isoformat(),
            "status": report.get("status"),
            "payload": dict(report),
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "report_kind": REPORT_KIND,
            "updated_at": utc_now().isoformat(),
            "latest_diagnostic": dict(report),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.state_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return record

    def latest(self) -> Optional[dict[str, Any]]:
        if not self.state_path.exists():
            return None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        latest = payload.get("latest_diagnostic") if isinstance(payload, Mapping) else None
        return dict(latest) if isinstance(latest, Mapping) else None


def latest_mt5_market_data_diagnostic(
    *,
    log: Optional[MT5MarketDataDiagnosticLog] = None,
) -> dict[str, Any]:
    log = log or MT5MarketDataDiagnosticLog()
    latest = log.latest()
    if latest is None:
        return {
            "report_kind": REPORT_KIND,
            "status": "NO_MT5_MARKET_DATA_DIAGNOSTIC",
            "broker_touched": False,
            "symbols": [],
            "detail": "No MT5 market-data diagnostic has been recorded yet.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    return latest


def run_mt5_market_data_diagnostic(
    *,
    symbols: Optional[Iterable[str]] = None,
    timeframe: str = DEFAULT_WASTE_TIMEFRAME,
    bars: int = DEFAULT_WASTE_BARS,
    connector: Optional[MT5TerminalMarketDataConnector] = None,
    log: Optional[MT5MarketDataDiagnosticLog] = None,
    terminal_locator: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    log = log or MT5MarketDataDiagnosticLog()
    terminal_locator = dict(terminal_locator or build_mt5_terminal_locator())
    auto_selected_path = (
        str(terminal_locator.get("preferred_path") or "")
        if terminal_locator.get("preferred_path_exists") and not getattr(config, "mt5_path", None)
        else ""
    )
    connector = connector or MT5TerminalMarketDataConnector(mt5_path=auto_selected_path or None)
    generated_at = utc_now().isoformat()
    requested_symbols = _normalize_symbols(symbols)
    try:
        checks = [
            _check_symbol(
                connector,
                symbol=symbol,
                timeframe=str(timeframe or DEFAULT_WASTE_TIMEFRAME).upper(),
                bars=max(40, int(bars)),
            )
            for symbol in requested_symbols
        ]
        ready = [row for row in checks if row.get("status") == SYMBOL_READY]
        report = {
            "report_kind": REPORT_KIND,
            "generated_at": generated_at,
            "status": STATUS_READY if ready else STATUS_NOT_READY,
            "ready_symbol_count": len(ready),
            "checked_symbol_count": len(checks),
            "symbols": checks,
            "timeframe": str(timeframe or DEFAULT_WASTE_TIMEFRAME).upper(),
            "bars_requested": max(40, int(bars)),
            "broker_touched": False,
            "edge_authorization_registered": False,
            "edge_token_persisted": False,
            "live_trading_authorized": False,
            "configured": {
                "market_data_provider": getattr(config, "market_data_provider", ""),
                "mt5_path_set": bool(getattr(config, "mt5_path", None)),
                "mt5_path_auto_selected_for_diagnostic": bool(auto_selected_path),
                "mt5_path_used_for_diagnostic": auto_selected_path or getattr(config, "mt5_path", None),
                "mt5_login_set": bool(getattr(config, "mt5_login", 0)),
                "mt5_symbol_overrides_configured": bool(getattr(config, "mt5_symbol_overrides", "")),
            },
            "terminal_locator": terminal_locator,
            "operator_commands": terminal_locator.get("operator_commands", {}),
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": _next_action(checks, terminal_locator),
        }
    except Exception as exc:
        report = {
            "report_kind": REPORT_KIND,
            "generated_at": generated_at,
            "status": STATUS_ERROR,
            "ready_symbol_count": 0,
            "checked_symbol_count": 0,
            "symbols": [],
            "timeframe": str(timeframe or DEFAULT_WASTE_TIMEFRAME).upper(),
            "bars_requested": max(40, int(bars)),
            "broker_touched": False,
            "edge_authorization_registered": False,
            "edge_token_persisted": False,
            "live_trading_authorized": False,
            "configured": {
                "market_data_provider": getattr(config, "market_data_provider", ""),
                "mt5_path_set": bool(getattr(config, "mt5_path", None)),
                "mt5_path_auto_selected_for_diagnostic": bool(auto_selected_path),
                "mt5_path_used_for_diagnostic": auto_selected_path or getattr(config, "mt5_path", None),
            },
            "terminal_locator": terminal_locator,
            "operator_commands": terminal_locator.get("operator_commands", {}),
            "error": f"{type(exc).__name__}: {exc}",
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": "Fix the MT5 market-data diagnostic error before using broker-grade WASTE evidence.",
        }
    audit = log.record(report)
    report["audit"] = audit
    return report


def _check_symbol(
    connector: MT5TerminalMarketDataConnector,
    *,
    symbol: str,
    timeframe: str,
    bars: int,
) -> dict[str, Any]:
    candles = connector.fetch_historical(symbol, bars=bars, timeframe=timeframe)
    error_after_candles = str(getattr(connector, "last_error", "") or "")
    resolution = _safe_json(getattr(connector, "last_symbol_resolution", None))
    snapshot = connector.fetch_snapshot(symbol) if candles else None
    spread = None
    quote = None
    if snapshot is not None:
        spread = _float(getattr(snapshot, "spread", None))
        quote = {
            "bid": _float(getattr(snapshot, "bid", None)),
            "ask": _float(getattr(snapshot, "ask", None)),
            "spread": spread,
            "timestamp": (
                snapshot.timestamp.isoformat()
                if hasattr(getattr(snapshot, "timestamp", None), "isoformat")
                else str(getattr(snapshot, "timestamp", ""))
            ),
            "is_market_open": bool(getattr(snapshot, "is_market_open", False)),
        }
    selected = resolution.get("selected_symbol") if isinstance(resolution, Mapping) else None
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "status": SYMBOL_READY if candles and selected else SYMBOL_NOT_READY,
        "candle_count": len(candles),
        "has_quote": quote is not None,
        "quote": quote,
        "spread_pips": spread,
        "broker_grade_market_truth": bool(candles and selected),
        "read_only_market_data": True,
        "selected_broker_symbol": selected,
        "symbol_resolution": resolution if isinstance(resolution, Mapping) else None,
        "detail": error_after_candles or None,
        "first_candle_time": candles[0].get("timestamp") if candles else None,
        "last_candle_time": candles[-1].get("timestamp") if candles else None,
    }


def _normalize_symbols(symbols: Optional[Iterable[str]]) -> tuple[str, ...]:
    if symbols is None:
        return DEFAULT_SYMBOLS
    out = tuple(str(symbol).strip() for symbol in symbols if str(symbol).strip())
    return out or DEFAULT_SYMBOLS


def build_mt5_terminal_locator(
    *,
    configured_path: Optional[str] = None,
    candidate_paths: Optional[Iterable[str | Path]] = None,
    process_rows: Optional[Iterable[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """Return a read-only operator hint for the MT5 executable/IPC blocker."""

    configured = str(configured_path if configured_path is not None else (getattr(config, "mt5_path", "") or "")).strip()
    rows = _candidate_path_rows(configured, candidate_paths)
    existing = [row for row in rows if row.get("exists")]
    preferred = configured if configured and Path(configured).exists() else str(existing[0]["path"]) if existing else ""
    if process_rows is None:
        process_probe = _probe_running_mt5_processes()
        processes = process_probe.get("processes", [])
    else:
        processes = [_safe_json(row) for row in process_rows]
        process_probe = {
            "status": "PROCESSES_FOUND" if processes else "NO_TERMINAL_PROCESS",
            "processes": processes,
            "error": None,
        }
    process_count = len(processes) if isinstance(processes, list) else 0
    locator = {
        "report_kind": "cas_forex_mt5_terminal_locator",
        "configured_path": configured or None,
        "configured_path_exists": bool(configured and Path(configured).exists()),
        "preferred_path": preferred or None,
        "preferred_path_exists": bool(preferred and Path(preferred).exists()),
        "candidate_paths": rows,
        "discovered_path_count": len(existing),
        "running_process_count": process_count,
        "process_probe": process_probe,
        "read_only": True,
        "claim_boundary": (
            "MT5 terminal locator inspects local path/process evidence only. It does not launch "
            "MetaTrader, log into an account, place orders, close positions, create ACCEPT, "
            "authorize live trading, or move money."
        ),
    }
    locator["operator_commands"] = _terminal_operator_commands(preferred or configured)
    locator["next_action"] = _terminal_next_action(locator)
    return locator


def _candidate_path_rows(configured_path: str, candidate_paths: Optional[Iterable[str | Path]]) -> list[dict[str, Any]]:
    paths: list[tuple[str, str]] = []
    if configured_path:
        paths.append((configured_path, "configured_env"))
    for path in (candidate_paths if candidate_paths is not None else _default_candidate_paths()):
        paths.append((str(path), "known_candidate"))
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for path, source in paths:
        cleaned = str(path).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        target = Path(cleaned)
        rows.append(
            {
                "path": cleaned,
                "source": source,
                "exists": target.exists(),
                "is_file": target.is_file() if target.exists() else False,
                "looks_like_mt5_terminal": target.name.lower() in {"terminal64.exe", "terminal.exe"},
            }
        )
    return rows


def _default_candidate_paths() -> tuple[str, ...]:
    paths: list[str] = list(COMMON_MT5_TERMINAL_PATHS)
    for key in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(key)
        if not base:
            continue
        try:
            for vendor in Path(base).iterdir():
                name = vendor.name.lower()
                if not any(part in name for part in ("hugo", "meta", "trader", "mt5")):
                    continue
                for exe_name in ("terminal64.exe", "terminal.exe"):
                    paths.extend(str(path) for path in vendor.glob(f"**/{exe_name}"))
        except OSError:
            continue
    return tuple(paths)


def _probe_running_mt5_processes() -> dict[str, Any]:
    if os.name != "nt":
        return {"status": "PROCESS_PROBE_UNAVAILABLE", "processes": [], "error": "process probe is Windows-only"}
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$rows = Get-CimInstance Win32_Process "
            "-Filter \"Name='terminal64.exe' OR Name='terminal.exe'\" | "
            "Select-Object Name,ProcessId,ExecutablePath; "
            "$rows | ConvertTo-Json -Compress"
        ),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except Exception as exc:
        return {"status": "PROCESS_PROBE_UNAVAILABLE", "processes": [], "error": f"{type(exc).__name__}: {exc}"}
    if completed.returncode != 0:
        return {
            "status": "PROCESS_PROBE_UNAVAILABLE",
            "processes": [],
            "error": (completed.stderr or completed.stdout or "").strip(),
        }
    text = completed.stdout.strip()
    if not text:
        return {"status": "NO_TERMINAL_PROCESS", "processes": [], "error": None}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "PROCESS_PROBE_UNAVAILABLE", "processes": [], "error": "PowerShell returned non-JSON process output"}
    items = payload if isinstance(payload, list) else [payload]
    processes = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        processes.append(
            {
                "name": item.get("Name"),
                "process_id": item.get("ProcessId"),
                "executable_path": item.get("ExecutablePath"),
            }
        )
    return {"status": "PROCESSES_FOUND" if processes else "NO_TERMINAL_PROCESS", "processes": processes, "error": None}


def _terminal_operator_commands(path: str) -> dict[str, str]:
    target = path or "<MT5_TERMINAL64_EXE>"
    return {
        "set_mt5_path_current_powershell": f'$env:CAS_FOREX_MT5_PATH="{target}"',
        "run_mt5_data_check": (
            "py -3.12 -c \"from cas_forex.mt5_market_data_diagnostic import "
            "run_mt5_market_data_diagnostic; "
            "print(run_mt5_market_data_diagnostic(symbols=['NAS100','US30'], timeframe='D1', bars=180)['status'])\""
        ),
        "run_mt5_api_verifier": f'py -3.12 scripts/run_mt5_terminal_api_verifier.py --mt5-path "{target}" --summary-only',
    }


def _terminal_next_action(locator: Mapping[str, Any]) -> str:
    configured = locator.get("configured_path")
    configured_exists = bool(locator.get("configured_path_exists"))
    preferred = locator.get("preferred_path")
    process_count = int(locator.get("running_process_count") or 0)
    if configured and not configured_exists:
        return "CAS_FOREX_MT5_PATH is set but the file was not found; set it to the actual terminal64.exe path, restart the API, then rerun Check MT5 Data."
    if process_count <= 0 and preferred:
        return f"Open/log into the MT5 terminal at {preferred}, then rerun Check MT5 Data."
    if process_count <= 0:
        return "Open/log into MetaTrader 5; if it is installed outside the default paths, set CAS_FOREX_MT5_PATH to terminal64.exe."
    if not configured and preferred:
        return (
            f"MT5 appears to be running at {preferred}; CAS Forex can auto-use "
            "that discovered terminal path for broker-grade market data and the "
            "gated bridge path. Set CAS_FOREX_MT5_PATH only if you want to pin a "
            "different terminal, then rerun Check MT5 Data."
        )
    return "MT5 process/path evidence is visible; rerun Check MT5 Data after the terminal is fully logged in and Market Watch includes NAS100/US30."


def _next_action(checks: list[Mapping[str, Any]], terminal_locator: Mapping[str, Any]) -> str:
    if any(check.get("status") == SYMBOL_READY for check in checks):
        return "MT5 broker-grade candles are available for at least one checked symbol; rerun WASTE real-candle probe and require BROKER TRUTH before live-pilot ACCEPT."
    details = " ".join(str(check.get("detail") or "") for check in checks)
    if "No IPC connection" in details or "initialize returned false" in details:
        locator_action = str(terminal_locator.get("next_action") or "").strip()
        return f"{locator_action} Then rerun this diagnostic." if locator_action else "Open/log into the local MT5 terminal or set CAS_FOREX_MT5_PATH, then rerun this diagnostic."
    unresolved = [
        check
        for check in checks
        if isinstance(check.get("symbol_resolution"), Mapping)
        and (check.get("symbol_resolution") or {}).get("status") == "UNRESOLVED"
    ]
    if unresolved:
        return "Set CAS_FOREX_MT5_SYMBOL_OVERRIDES for the broker's NAS100/US30 symbol names, then rerun this diagnostic."
    return "MT5 did not return broker-grade candles; inspect terminal connection, Market Watch visibility, and symbol overrides."


def _safe_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
