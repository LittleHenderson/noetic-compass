"""MT5 terminal API verifier for CAS Forex.

This is a read-only verifier for the MT5 terminal already installed on the
machine. It proves whether CAS can reach MetaTrader 5 through the official
Python API, read a demo/paper account snapshot, and collect the same
BROKER_API_VERIFIED receipt used by the paper-proof ledger.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from cas_forex.config import config
from cas_forex.paper_broker_adapter import MT5DemoPaperReceiptAdapter
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MT5_DEPS = REPO_ROOT / ".mt5deps"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt5_terminal_api_verifier"
REPORT_KIND = "cas_forex_mt5_terminal_api_verifier_report"
VERIFIER_SCHEMA = "cas_forex_mt5_terminal_api_verifier.v1"
CLAIM_BOUNDARY = (
    "MT5 terminal API verifier inspects demo/paper broker account state through "
    "the MetaTrader5 Python API. It does not place live broker orders, create "
    "broker ACCEPT, deposit, withdraw, move bank/card funds, automate payouts, "
    "or override runtime gates."
)


class MT5TerminalApiVerifierError(ValueError):
    """Raised when MT5 terminal API verifier evidence is invalid."""


def build_mt5_terminal_api_verifier_report(
    *,
    mt5_path: Optional[Path | str] = None,
    trading_date: Optional[date | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    mt5_module: Any | None = None,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one read-only MT5 API verifier report."""

    _add_local_mt5_deps()
    plan = build_index_tsmom_126_paper_proof_plan()
    resolved_date = date.fromisoformat(trading_date) if isinstance(trading_date, str) else trading_date or utc_now().date()
    old_mt5_path = config.mt5_path
    if mt5_path is not None:
        config.mt5_path = str(mt5_path)
    try:
        adapter = MT5DemoPaperReceiptAdapter(mt5_module=mt5_module)
        probe = adapter.probe(plan, resolved_date)
        terminal_snapshot = _terminal_snapshot(mt5_module=mt5_module, mt5_path=mt5_path)
    finally:
        config.mt5_path = old_mt5_path

    summary = _summary(probe=probe.__dict__, terminal_snapshot=terminal_snapshot)
    verifier_status = _verifier_status(summary)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "verifier_status": verifier_status,
        "schema": VERIFIER_SCHEMA,
        "trading_date": resolved_date.isoformat(),
        "mt5_path": str(mt5_path) if mt5_path is not None else config.mt5_path,
        "probe": probe.__dict__,
        "terminal_snapshot": terminal_snapshot,
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(verifier_status),
        "operator_commands": _operator_commands(mt5_path),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_mt5_terminal_api_verifier_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_mt5_terminal_api_verifier_report(report)
    return report


def write_mt5_terminal_api_verifier_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt5_terminal_api_verifier_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt5-terminal-api-verifier-{stamp}-report.json"
    md_path = target_dir / f"mt5-terminal-api-verifier-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt5_terminal_api_verifier_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_mt5_terminal_api_verifier_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt5-terminal-api-verifier-*-report.json"))
    if not files:
        raise MT5TerminalApiVerifierError(f"No MT5 terminal API verifier reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt5_terminal_api_verifier_report(payload)
    return payload


def validate_mt5_terminal_api_verifier_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "verifier_status",
        "schema",
        "trading_date",
        "probe",
        "terminal_snapshot",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT5TerminalApiVerifierError(f"MT5 terminal API verifier report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT5TerminalApiVerifierError("unexpected MT5 terminal API verifier report_kind")
    if payload.get("schema") != VERIFIER_SCHEMA:
        raise MT5TerminalApiVerifierError("unexpected MT5 terminal API verifier schema")
    if "does not place live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT5TerminalApiVerifierError("MT5 terminal API verifier claim boundary must preserve execution boundary")
    if not isinstance(payload.get("summary"), Mapping):
        raise MT5TerminalApiVerifierError("summary must be an object")


def render_mt5_terminal_api_verifier_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex MT5 Terminal API Verifier",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('verifier_status')}`",
        f"Trading date: `{report.get('trading_date')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- MT5 package available: `{summary.get('mt5_package_available')}`",
        f"- Terminal connected: `{summary.get('terminal_connected')}`",
        f"- Probe status: `{summary.get('probe_status')}`",
        f"- Broker mode: `{summary.get('broker_mode')}`",
        f"- Server: `{summary.get('server')}`",
        f"- Account snapshot present: `{summary.get('account_snapshot_present')}`",
        f"- Open positions: `{summary.get('open_position_count')}`",
        f"- Open positions reconciled: `{summary.get('open_positions_reconciled')}`",
        f"- Live mode used: `{summary.get('live_mode_used')}`",
        "",
        f"Next action: {report.get('next_action')}",
    ]
    return "\n".join(lines) + "\n"


def _add_local_mt5_deps() -> None:
    if LOCAL_MT5_DEPS.exists():
        path = str(LOCAL_MT5_DEPS)
        if path not in sys.path:
            sys.path.insert(0, path)


def _terminal_snapshot(*, mt5_module: Any | None, mt5_path: Optional[Path | str]) -> Dict[str, Any]:
    mt5 = mt5_module or _import_mt5()
    if mt5 is None:
        return {"mt5_package_available": False, "initialize_ok": False, "terminal": {}, "account": {}, "positions": []}
    kwargs: Dict[str, Any] = {}
    path = str(mt5_path or config.mt5_path or "")
    if path:
        kwargs["path"] = path
    try:
        terminal = _object_to_dict(mt5.terminal_info())
        if not terminal or not bool(terminal.get("connected")):
            mt5.initialize(**kwargs)
            terminal = _object_to_dict(mt5.terminal_info())
        account = _redacted_account_snapshot(_object_to_dict(mt5.account_info()))
        positions = [_position_snapshot(_object_to_dict(position)) for position in (mt5.positions_get() or [])]
        return {
            "mt5_package_available": True,
            "initialize_ok": bool(terminal),
            "terminal": _terminal_info_snapshot(terminal),
            "account": account,
            "positions": positions,
            "positions_sha256": _sha256_json(positions),
        }
    except Exception as exc:
        return {
            "mt5_package_available": True,
            "initialize_ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
            "terminal": {},
            "account": {},
            "positions": [],
        }


def _summary(*, probe: Mapping[str, Any], terminal_snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    receipt = probe.get("receipt") if isinstance(probe.get("receipt"), Mapping) else {}
    account = terminal_snapshot.get("account") if isinstance(terminal_snapshot.get("account"), Mapping) else {}
    terminal = terminal_snapshot.get("terminal") if isinstance(terminal_snapshot.get("terminal"), Mapping) else {}
    positions = list(terminal_snapshot.get("positions") or [])
    return {
        "mt5_package_available": bool(terminal_snapshot.get("mt5_package_available")),
        "initialize_ok": bool(terminal_snapshot.get("initialize_ok")),
        "terminal_connected": bool(terminal.get("connected")),
        "probe_status": probe.get("status"),
        "broker": probe.get("broker"),
        "broker_mode": receipt.get("broker_mode"),
        "receipt_validation_status": receipt.get("receipt_validation_status"),
        "broker_api_authenticated": bool(receipt.get("broker_api_authenticated")),
        "broker_source_verified": bool(receipt.get("broker_source_verified")),
        "server": receipt.get("server") or account.get("server"),
        "terminal_name": receipt.get("terminal_name") or terminal.get("name"),
        "account_snapshot_present": bool(receipt.get("account_snapshot") or account),
        "account_currency": (receipt.get("account_snapshot") or account or {}).get("currency"),
        "account_balance": (receipt.get("account_snapshot") or account or {}).get("balance"),
        "account_equity": (receipt.get("account_snapshot") or account or {}).get("equity"),
        "open_position_count": len(positions),
        "open_positions_reconciled": bool(receipt.get("open_positions_reconciled")),
        "orders_attempted": int(receipt.get("orders_attempted") or 0),
        "orders_paper_executed": int(receipt.get("orders_paper_executed") or 0),
        "live_mode_used": bool(receipt.get("live_mode")),
        "reasons": list(probe.get("reasons") or []),
    }


def _verifier_status(summary: Mapping[str, Any]) -> str:
    if not summary.get("mt5_package_available"):
        return "MT5_API_VERIFIER_PACKAGE_MISSING"
    if summary.get("probe_status") == "BLOCKED":
        return "MT5_API_VERIFIER_BLOCKED"
    if summary.get("probe_status") == "UNAVAILABLE":
        return "MT5_API_VERIFIER_UNAVAILABLE"
    if not summary.get("terminal_connected"):
        return "MT5_API_VERIFIER_TERMINAL_DISCONNECTED"
    if not summary.get("account_snapshot_present"):
        return "MT5_API_VERIFIER_ACCOUNT_UNAVAILABLE"
    if summary.get("live_mode_used"):
        return "MT5_API_VERIFIER_LIVE_MODE_VISIBLE"
    if summary.get("probe_status") == "BROKER_API_VERIFIED" and summary.get("receipt_validation_status") == "BROKER_API_VERIFIED":
        return "MT5_API_VERIFIER_BROKER_API_VERIFIED"
    return "MT5_API_VERIFIER_UNVERIFIABLE"


def _next_action(status: str) -> str:
    if status == "MT5_API_VERIFIER_PACKAGE_MISSING":
        return "Install the MetaTrader5 Python package into .mt5deps, then rerun this verifier."
    if status == "MT5_API_VERIFIER_TERMINAL_DISCONNECTED":
        return "Open/log into MetaTrader 5, set CAS_FOREX_MT5_PATH if needed, then rerun this verifier."
    if status == "MT5_API_VERIFIER_ACCOUNT_UNAVAILABLE":
        return "Log into the MT5 demo account so account_info and account snapshot are available."
    if status == "MT5_API_VERIFIER_BLOCKED":
        return "The MT5 account was not identified as paper/demo; keep live runtime gates off until live requirements are explicitly satisfied."
    if status == "MT5_API_VERIFIER_LIVE_MODE_VISIBLE":
        return "Review live-mode visibility against runtime gates before allowing any live command path."
    if status == "MT5_API_VERIFIER_BROKER_API_VERIFIED":
        return "MT5 demo broker API is verified; keep collecting daily receipts and wire paper/demo execution only through owner-controlled gates."
    return "Inspect verifier reasons and rerun after the MT5 terminal and account are connected."


def _operator_commands(mt5_path: Optional[Path | str]) -> Dict[str, str]:
    path = str(mt5_path or config.mt5_path or "<MT5_TERMINAL64_EXE>")
    return {
        "install_local_mt5_deps": "py -3.12 -m pip install --target .mt5deps --upgrade MetaTrader5",
        "mt5_api_verifier": f'py -3.12 scripts/run_mt5_terminal_api_verifier.py --mt5-path "{path}" --summary-only',
        "mt5_paper_receipt": f'$env:PYTHONPATH=".mt5deps"; $env:CAS_FOREX_MT5_PATH="{path}"; py -3.12 scripts/run_mt5_paper_receipt.py --append-if-verified',
    }


def _import_mt5() -> Any | None:
    try:
        import MetaTrader5 as mt5  # type: ignore

        return mt5
    except ImportError:
        return None


def _terminal_info_snapshot(terminal: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "connected": bool(terminal.get("connected")),
        "name": terminal.get("name"),
        "company": terminal.get("company"),
        "path": terminal.get("path"),
        "data_path": terminal.get("data_path"),
        "commondata_path": terminal.get("commondata_path"),
        "trade_allowed": terminal.get("trade_allowed"),
        "dlls_allowed": terminal.get("dlls_allowed"),
        "build": terminal.get("build"),
    }


def _redacted_account_snapshot(account: Mapping[str, Any]) -> Dict[str, Any]:
    if not account:
        return {}

    def number(key: str) -> float | None:
        value = account.get(key)
        if value is None:
            return None
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    return {
        "account_id_hash": _sha256_json({"login": account.get("login"), "server": account.get("server")}),
        "balance": number("balance"),
        "equity": number("equity"),
        "margin": number("margin"),
        "margin_free": number("margin_free"),
        "currency": account.get("currency"),
        "leverage": account.get("leverage"),
        "server": account.get("server"),
        "company": account.get("company"),
        "trade_mode": account.get("trade_mode"),
    }


def _position_snapshot(position: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "ticket": position.get("ticket"),
        "symbol": position.get("symbol"),
        "type": position.get("type"),
        "volume": position.get("volume"),
        "price_open": position.get("price_open"),
        "price_current": position.get("price_current"),
        "profit": position.get("profit"),
        "swap": position.get("swap"),
        "comment": position.get("comment"),
        "magic": position.get("magic"),
    }


def _object_to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    data: Dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        try:
            attr = getattr(value, key)
        except Exception:
            continue
        if callable(attr):
            continue
        if isinstance(attr, (str, int, float, bool, type(None))):
            data[key] = attr
    return data


def _sha256_json(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
