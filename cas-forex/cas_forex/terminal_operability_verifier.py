"""Top-level terminal operability verifier for CAS Forex.

This report is the operator-facing "can this terminal lane be trusted right
now?" bundle. It reads the latest MT4 session, MT5 terminal API, MT5
paper/demo execution, bridge heartbeat, receipt ingest, history export,
position reconciliation, and runtime gate evidence and turns them into one
go/no-go view.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from cas_forex.mt4_history_export_verifier import load_latest_mt4_history_export_verifier_report
from cas_forex.mt4_terminal_session_verifier import load_latest_mt4_terminal_session_verifier_report
from cas_forex.mt5_paper_execution_verifier import load_latest_mt5_paper_execution_verifier_report
from cas_forex.mt5_deal_history_ingest import load_latest_mt5_deal_history_ingest_report
from cas_forex.mt5_terminal_api_verifier import load_latest_mt5_terminal_api_verifier_report
from cas_forex.runtime_gates import build_runtime_gates_report
from cas_forex.terminal_bridge_supervisor import load_latest_terminal_bridge_supervisor_report
from cas_forex.terminal_history_ingest import load_latest_terminal_history_ingest_report
from cas_forex.terminal_position_reconciliation import load_latest_terminal_position_reconciliation_report
from cas_forex.terminal_receipt_ingest import load_latest_terminal_receipt_ingest_report
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_operability_verifier"
REPORT_KIND = "cas_forex_terminal_operability_verifier_report"
OPERABILITY_SCHEMA = "cas_forex_terminal_operability_verifier.v1"
CLAIM_BOUNDARY = (
    "Terminal operability verifier bundles terminal session, MT5 terminal API, "
    "MT5 paper/demo execution, heartbeat, receipt, history export, position "
    "reconciliation, and runtime-gate evidence into one go/no-go report. It "
    "does not execute live broker orders, create broker ACCEPT, deposit, "
    "withdraw, move bank/card funds, automate payouts, or override child "
    "evidence."
)

STATUS_OK = "OK"
STATUS_WAITING = "WAITING"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNVERIFIABLE = "UNVERIFIABLE"

# Lane identifiers shown in the operability summary. These mirror the lane
# labels emitted by terminal_position_reconciliation.py so the cockpit can
# show a per-lane breakdown of CAS open positions and pending receipts and
# pick which lane the top-level numbers reflect.
ACTIVE_LANE_MT4_MAILBOX = "MT4_MAILBOX"
ACTIVE_LANE_MT5_DEMO = "MT5_DEMO"
_LANE_KEY_MT4_MAILBOX = "mt4_mailbox"
_LANE_KEY_MT5_DEMO = "mt5_demo"


def _detect_active_terminal_lane(
    *,
    mt5_api_payload: Mapping[str, Any],
    mt5_execution_payload: Mapping[str, Any],
) -> str:
    """Pick the terminal lane whose numbers should drive the top-level summary.

    MT5 evidence wins when an MT5 terminal-API verifier report is present and
    the broker API is verified, or when the MT5 paper/demo execution verifier
    actually reached the terminal. Otherwise fall back to the legacy MT4
    mailbox lane, which is the historical default.
    """

    mt5_api_status = str(mt5_api_payload.get("verifier_status") or "")
    if mt5_api_status == "MT5_API_VERIFIER_BROKER_API_VERIFIED":
        return ACTIVE_LANE_MT5_DEMO
    mt5_exec_status = str(mt5_execution_payload.get("verifier_status") or "")
    if mt5_exec_status and mt5_exec_status not in {
        "",
        "MT5_PAPER_EXECUTION_BLOCKED_BY_API_VERIFIER",
        "MT5_PAPER_EXECUTION_UNAVAILABLE",
    }:
        return ACTIVE_LANE_MT5_DEMO
    exec_summary = mt5_execution_payload.get("summary") or {}
    if exec_summary and (
        exec_summary.get("execution_attempted")
        or exec_summary.get("order_request_built")
    ):
        # An MT5 demo order request was at least built — the operator is
        # operating in the MT5 lane even if the broker rejected.
        return ACTIVE_LANE_MT5_DEMO
    return ACTIVE_LANE_MT4_MAILBOX


class TerminalOperabilityVerifierError(ValueError):
    """Raised when terminal operability verifier evidence is invalid."""


def build_terminal_operability_verifier_report(
    *,
    session_report: Optional[Mapping[str, Any]] = None,
    bridge_report: Optional[Mapping[str, Any]] = None,
    receipt_ingest_report: Optional[Mapping[str, Any]] = None,
    history_export_verifier_report: Optional[Mapping[str, Any]] = None,
    mt5_terminal_api_verifier_report: Optional[Mapping[str, Any]] = None,
    mt5_paper_execution_verifier_report: Optional[Mapping[str, Any]] = None,
    mt5_deal_history_ingest_report: Optional[Mapping[str, Any]] = None,
    history_ingest_report: Optional[Mapping[str, Any]] = None,
    position_reconciliation_report: Optional[Mapping[str, Any]] = None,
    runtime_gates_report: Optional[Mapping[str, Any]] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one terminal operability go/no-go report."""

    session = _source("mt4_terminal_session_verifier", session_report, load_latest_mt4_terminal_session_verifier_report)
    bridge = _source("terminal_bridge_supervisor", bridge_report, load_latest_terminal_bridge_supervisor_report)
    receipts = _source("terminal_receipt_ingest", receipt_ingest_report, load_latest_terminal_receipt_ingest_report)
    history_export = _source("mt4_history_export_verifier", history_export_verifier_report, load_latest_mt4_history_export_verifier_report)
    mt5_api = _source("mt5_terminal_api_verifier", mt5_terminal_api_verifier_report, load_latest_mt5_terminal_api_verifier_report)
    mt5_execution = _source("mt5_paper_execution_verifier", mt5_paper_execution_verifier_report, load_latest_mt5_paper_execution_verifier_report)
    mt5_deal_history = _source("mt5_deal_history_ingest", mt5_deal_history_ingest_report, load_latest_mt5_deal_history_ingest_report)
    history = _source("terminal_history_ingest", history_ingest_report, load_latest_terminal_history_ingest_report)
    reconciliation = _source("terminal_position_reconciliation", position_reconciliation_report, load_latest_terminal_position_reconciliation_report)
    gates = _runtime_gates_source(runtime_gates_report)

    summary = _summary(
        session=session,
        bridge=bridge,
        receipts=receipts,
        history_export=history_export,
        mt5_api=mt5_api,
        mt5_execution=mt5_execution,
        mt5_deal_history=mt5_deal_history,
        history=history,
        reconciliation=reconciliation,
        gates=gates,
    )
    checks = _checks(summary)
    status = _operability_status(summary, checks)
    go_no_go = _go_no_go(status, summary)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "operability_status": status,
        "schema": OPERABILITY_SCHEMA,
        "source_reports": {
            "mt4_terminal_session_verifier": session["ref"],
            "terminal_bridge_supervisor": bridge["ref"],
            "terminal_receipt_ingest": receipts["ref"],
            "mt4_history_export_verifier": history_export["ref"],
            "mt5_terminal_api_verifier": mt5_api["ref"],
            "mt5_paper_execution_verifier": mt5_execution["ref"],
            "mt5_deal_history_ingest": mt5_deal_history["ref"],
            "terminal_history_ingest": history["ref"],
            "terminal_position_reconciliation": reconciliation["ref"],
            "runtime_gates": gates["ref"],
        },
        "summary": summary,
        "checks": checks,
        "go_no_go": go_no_go,
        "runtime_gate_decisions": gates["payload"].get("decisions", {}) if gates.get("payload") else {},
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(status, summary),
        "operator_commands": _operator_commands(summary),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_terminal_operability_verifier_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_terminal_operability_verifier_report(report)
    return report


def write_terminal_operability_verifier_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_terminal_operability_verifier_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"terminal-operability-verifier-{stamp}-report.json"
    md_path = target_dir / f"terminal-operability-verifier-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_terminal_operability_verifier_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_terminal_operability_verifier_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("terminal-operability-verifier-*-report.json"))
    if not files:
        raise TerminalOperabilityVerifierError(f"No terminal operability verifier reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_terminal_operability_verifier_report(payload)
    return payload


def validate_terminal_operability_verifier_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "operability_status",
        "schema",
        "source_reports",
        "summary",
        "checks",
        "go_no_go",
        "runtime_gate_decisions",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise TerminalOperabilityVerifierError(f"terminal operability verifier report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise TerminalOperabilityVerifierError("unexpected terminal operability verifier report_kind")
    if payload.get("schema") != OPERABILITY_SCHEMA:
        raise TerminalOperabilityVerifierError("unexpected terminal operability verifier schema")
    if "does not execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise TerminalOperabilityVerifierError("terminal operability verifier claim boundary must preserve execution boundary")
    if not isinstance(payload.get("summary"), Mapping):
        raise TerminalOperabilityVerifierError("summary must be an object")
    if not isinstance(payload.get("checks"), list):
        raise TerminalOperabilityVerifierError("checks must be a list")
    if not isinstance(payload.get("go_no_go"), Mapping):
        raise TerminalOperabilityVerifierError("go_no_go must be an object")


def render_terminal_operability_verifier_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    go_no_go = report.get("go_no_go") or {}
    lines = [
        "# CAS Forex Terminal Operability Verifier",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('operability_status')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Go / No-Go",
        "",
        f"- Terminal lane go: `{go_no_go.get('terminal_lane_go')}`",
        f"- Live order go: `{go_no_go.get('live_order_go')}`",
        f"- Broker ACCEPT go: `{go_no_go.get('broker_accept_go')}`",
        f"- Money movement go: `{go_no_go.get('money_movement_go')}`",
        "",
        "## Summary",
        "",
        f"- Session: `{summary.get('session_status')}`",
        f"- Bridge: `{summary.get('bridge_status')}`",
        f"- Heartbeat: `{summary.get('heartbeat_status')}`",
        f"- History export: `{summary.get('history_export_verifier_status')}`",
        f"- Position reconciliation: `{summary.get('position_reconciliation_status')}`",
        f"- CAS / terminal open positions: `{summary.get('cas_open_position_count')}` / `{summary.get('terminal_open_position_count')}`",
        f"- Reconciled / unmatched positions: `{summary.get('reconciled_open_position_count')}` / `{summary.get('unmatched_open_position_count')}`",
        f"- Pending receipts / receipt mismatches: `{summary.get('pending_receipt_count')}` / `{summary.get('receipt_mismatch_count')}`",
        f"- Live trading authorized: `{summary.get('live_trading_authorized')}`",
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
        payload = dict(provided)
        return {"name": name, "present": True, "payload": payload, "ref": _report_ref(payload)}
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


def _runtime_gates_source(provided: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if provided is not None:
        payload = dict(provided)
    else:
        payload = build_runtime_gates_report().to_dict()
    return {
        "name": "runtime_gates",
        "present": True,
        "payload": payload,
        "ref": {
            "present": True,
            "report_kind": payload.get("report_kind"),
            "status": "ALL_AUTHORIZED" if payload.get("all_real_money_authorized") else "CURRENTLY_NOT_LICENSED",
            "summary": {"all_real_money_authorized": payload.get("all_real_money_authorized"), "summary": payload.get("summary")},
        },
    }


def _report_ref(report: Mapping[str, Any]) -> Dict[str, Any]:
    artifact_paths = report.get("artifact_paths") if isinstance(report.get("artifact_paths"), Mapping) else {}
    return {
        "present": True,
        "report_kind": report.get("report_kind"),
        "status": _status_value(report),
        "report_path": report.get("report_path") or artifact_paths.get("json"),
        "created_at": report.get("created_at"),
        "summary": report.get("summary") or {},
    }


def _status_value(report: Mapping[str, Any]) -> Optional[str]:
    for key in (
        "session_status",
        "supervisor_status",
        "ingest_status",
        "verifier_status",
        "reconciliation_status",
        "operability_status",
    ):
        value = report.get(key)
        if value:
            return str(value)
    return None


def _summary(
    *,
    session: Mapping[str, Any],
    bridge: Mapping[str, Any],
    receipts: Mapping[str, Any],
    history_export: Mapping[str, Any],
    mt5_api: Mapping[str, Any],
    mt5_execution: Mapping[str, Any],
    mt5_deal_history: Mapping[str, Any],
    history: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    gates: Mapping[str, Any],
) -> Dict[str, Any]:
    session_payload = session.get("payload") or {}
    bridge_payload = bridge.get("payload") or {}
    receipt_payload = receipts.get("payload") or {}
    history_export_payload = history_export.get("payload") or {}
    mt5_api_payload = mt5_api.get("payload") or {}
    mt5_execution_payload = mt5_execution.get("payload") or {}
    history_payload = history.get("payload") or {}
    reconciliation_payload = reconciliation.get("payload") or {}
    gate_payload = gates.get("payload") or {}

    session_summary = session_payload.get("summary") or {}
    bridge_summary = bridge_payload.get("summary") or {}
    receipt_summary = receipt_payload.get("summary") or {}
    history_export_summary = history_export_payload.get("summary") or {}
    mt5_api_summary = mt5_api_payload.get("summary") or {}
    mt5_execution_summary = mt5_execution_payload.get("summary") or {}
    mt5_deal_history_payload = mt5_deal_history.get("payload") or {}
    mt5_deal_history_summary = mt5_deal_history_payload.get("summary") or {}
    history_summary = history_payload.get("summary") or {}
    reconciliation_summary = reconciliation_payload.get("summary") or {}
    gate_decisions = gate_payload.get("decisions") or {}

    live_decision = gate_decisions.get("live_trading") or {}
    broker_decision = gate_decisions.get("broker_accept") or {}
    auto_deposit_decision = gate_decisions.get("auto_deposit") or {}
    bank_card_decision = gate_decisions.get("bank_card_movement") or {}
    payout_decision = gate_decisions.get("payout_automation") or {}
    money_movement_authorized = all(
        bool(decision.get("authorized"))
        for decision in (auto_deposit_decision, bank_card_decision, payout_decision)
    )

    heartbeat_status = reconciliation_summary.get("heartbeat_status") or bridge_summary.get("heartbeat_status")

    # Lane awareness: the legacy MT4 mailbox journal can still hold stale
    # receipt-pending rows even after the operator moved to the MT5 demo
    # lane. Detect the active lane, surface a per-lane breakdown, and let
    # the top-level numbers reflect the lane the operator is actually
    # using so the cockpit stops conflating stale MT4 rows with MT5 truth.
    active_terminal_lane = _detect_active_terminal_lane(
        mt5_api_payload=mt5_api_payload,
        mt5_execution_payload=mt5_execution_payload,
    )
    legacy_pending_receipt_count = int(
        reconciliation_summary.get("pending_receipt_count")
        or receipt_summary.get("pending_receipt_count")
        or 0
    )
    legacy_cas_open_position_count = int(reconciliation_summary.get("cas_open_position_count") or 0)
    legacy_terminal_open_position_count = int(reconciliation_summary.get("terminal_open_position_count") or 0)

    raw_cas_open_by_lane = reconciliation_summary.get("cas_open_position_count_by_lane")
    if isinstance(raw_cas_open_by_lane, Mapping) and raw_cas_open_by_lane:
        cas_open_by_lane = {
            _LANE_KEY_MT4_MAILBOX: int(raw_cas_open_by_lane.get(_LANE_KEY_MT4_MAILBOX, 0) or 0),
            _LANE_KEY_MT5_DEMO: int(raw_cas_open_by_lane.get(_LANE_KEY_MT5_DEMO, 0) or 0),
        }
    else:
        # Reconciliation summary predates lane awareness — attribute all
        # legacy rows to the MT4 mailbox lane so the cockpit still shows
        # something honest.
        cas_open_by_lane = {
            _LANE_KEY_MT4_MAILBOX: legacy_cas_open_position_count,
            _LANE_KEY_MT5_DEMO: 0,
        }

    raw_pending_by_lane = reconciliation_summary.get("pending_receipt_count_by_lane")
    if isinstance(raw_pending_by_lane, Mapping) and raw_pending_by_lane:
        pending_receipt_by_lane = {
            _LANE_KEY_MT4_MAILBOX: int(raw_pending_by_lane.get(_LANE_KEY_MT4_MAILBOX, 0) or 0),
            _LANE_KEY_MT5_DEMO: int(raw_pending_by_lane.get(_LANE_KEY_MT5_DEMO, 0) or 0),
        }
    else:
        pending_receipt_by_lane = {
            _LANE_KEY_MT4_MAILBOX: legacy_pending_receipt_count,
            _LANE_KEY_MT5_DEMO: 0,
        }

    raw_terminal_open_by_lane = reconciliation_summary.get("terminal_open_position_count_by_lane")
    if isinstance(raw_terminal_open_by_lane, Mapping) and raw_terminal_open_by_lane:
        terminal_open_by_lane = {
            _LANE_KEY_MT4_MAILBOX: int(raw_terminal_open_by_lane.get(_LANE_KEY_MT4_MAILBOX, 0) or 0),
            _LANE_KEY_MT5_DEMO: int(raw_terminal_open_by_lane.get(_LANE_KEY_MT5_DEMO, 0) or 0),
        }
    else:
        terminal_open_by_lane = {
            _LANE_KEY_MT4_MAILBOX: legacy_terminal_open_position_count,
            _LANE_KEY_MT5_DEMO: 0,
        }

    active_lane_key = _LANE_KEY_MT5_DEMO if active_terminal_lane == ACTIVE_LANE_MT5_DEMO else _LANE_KEY_MT4_MAILBOX
    active_cas_open_count = cas_open_by_lane.get(active_lane_key, 0)
    active_pending_receipt_count = pending_receipt_by_lane.get(active_lane_key, 0)
    return {
        "session_report_present": bool(session.get("present")),
        "bridge_report_present": bool(bridge.get("present")),
        "receipt_ingest_report_present": bool(receipts.get("present")),
        "history_export_verifier_present": bool(history_export.get("present")),
        "mt5_terminal_api_verifier_present": bool(mt5_api.get("present")),
        "mt5_paper_execution_verifier_present": bool(mt5_execution.get("present")),
        "mt5_deal_history_ingest_present": bool(mt5_deal_history.get("present")),
        "history_ingest_report_present": bool(history.get("present")),
        "position_reconciliation_report_present": bool(reconciliation.get("present")),
        "runtime_gates_present": bool(gates.get("present")),
        "session_status": session_payload.get("session_status"),
        "activation_status": session_summary.get("activation_status"),
        "roundtrip_status": session_summary.get("roundtrip_status"),
        "bridge_status": bridge_payload.get("supervisor_status") or reconciliation_summary.get("bridge_status"),
        "heartbeat_status": heartbeat_status,
        "heartbeat_present": bool(reconciliation_summary.get("heartbeat_present") or bridge_summary.get("heartbeat_present")),
        "mailbox_ready": bool(session_summary.get("mailbox_ready") or history_export_summary.get("mailbox_ready")),
        "receipt_present": bool(session_summary.get("receipt_present") or receipt_summary.get("receipt_count")),
        "pending_receipt_count": active_pending_receipt_count,
        "pending_receipt_count_legacy_total": legacy_pending_receipt_count,
        "pending_receipt_count_by_lane": dict(pending_receipt_by_lane),
        "receipt_mismatch_count": int(reconciliation_summary.get("receipt_mismatch_count") or receipt_summary.get("receipt_mismatch_count") or 0),
        "history_export_verifier_status": history_export_payload.get("verifier_status"),
        "history_export_present": bool(history_export_summary.get("history_export_present")),
        "history_export_parse_status": history_export_summary.get("history_export_parse_status"),
        "mt5_terminal_api_verifier_status": mt5_api_payload.get("verifier_status"),
        "mt5_terminal_connected": bool(mt5_api_summary.get("terminal_connected")),
        "mt5_broker_api_verified": mt5_api_payload.get("verifier_status") == "MT5_API_VERIFIER_BROKER_API_VERIFIED",
        "mt5_account_snapshot_present": bool(mt5_api_summary.get("account_snapshot_present")),
        "mt5_open_position_count": int(mt5_api_summary.get("open_position_count") or 0),
        "mt5_open_positions_reconciled": bool(mt5_api_summary.get("open_positions_reconciled")),
        "mt5_server": mt5_api_summary.get("server"),
        "mt5_account_balance": mt5_api_summary.get("account_balance"),
        "mt5_account_equity": mt5_api_summary.get("account_equity"),
        "mt5_paper_execution_verifier_status": mt5_execution_payload.get("verifier_status"),
        "mt5_paper_order_request_built": bool(mt5_execution_summary.get("order_request_built")),
        "mt5_paper_order_check_status": mt5_execution_summary.get("order_check_status"),
        "mt5_paper_execution_attempted": bool(mt5_execution_summary.get("execution_attempted")),
        "mt5_paper_execution_status": mt5_execution_summary.get("execution_status"),
        "mt5_paper_execution_error_message": mt5_execution_summary.get("execution_error_message"),
        "mt5_paper_terminal_trade_allowed": mt5_execution_summary.get("terminal_trade_allowed"),
        "mt5_paper_raw_response_hash": mt5_execution_summary.get("raw_response_hash"),
        "mt5_paper_close_attempted": bool(mt5_execution_summary.get("close_attempted")),
        "mt5_paper_close_success": bool(mt5_execution_summary.get("close_success")),
        "mt5_deal_history_ingest_status": mt5_deal_history_payload.get("ingest_status"),
        "mt5_deal_history_raw_deal_count": int(mt5_deal_history_summary.get("raw_deal_count") or 0),
        "mt5_deal_history_closed_position_count": int(mt5_deal_history_summary.get("closed_position_count") or 0),
        "mt5_deal_history_memory_update_count": int(mt5_deal_history_summary.get("memory_update_count") or 0),
        "mt5_deal_history_unmatched_count": int(mt5_deal_history_summary.get("unmatched_history_count") or 0),
        "mt5_deal_history_net_profit_loss_account": float(mt5_deal_history_summary.get("net_profit_loss_account") or 0.0),
        "history_record_count": int(reconciliation_summary.get("history_record_count") or mt5_deal_history_summary.get("history_record_count") or history_summary.get("history_record_count") or history_export_summary.get("history_record_count") or 0),
        "memory_update_count": int(reconciliation_summary.get("memory_update_count") or mt5_deal_history_summary.get("memory_update_count") or history_summary.get("memory_update_count") or history_export_summary.get("memory_update_count") or 0),
        "unmatched_history_count": int(reconciliation_summary.get("unmatched_history_count") or mt5_deal_history_summary.get("unmatched_history_count") or history_summary.get("unmatched_history_count") or 0),
        "position_reconciliation_status": reconciliation_payload.get("reconciliation_status"),
        "account_snapshot_present": bool(reconciliation_summary.get("account_snapshot_present")),
        "cas_open_position_count": active_cas_open_count,
        "cas_open_position_count_legacy_total": legacy_cas_open_position_count,
        "cas_open_position_count_by_lane": dict(cas_open_by_lane),
        "active_terminal_lane": active_terminal_lane,
        "terminal_open_position_count": int(reconciliation_summary.get("terminal_open_position_count") or 0),
        "terminal_open_position_count_by_lane": dict(terminal_open_by_lane),
        "reconciled_open_position_count": int(reconciliation_summary.get("reconciled_open_position_count") or 0),
        "unmatched_open_position_count": int(reconciliation_summary.get("unmatched_open_position_count") or 0),
        "live_flag_visible": bool(
            session_summary.get("live_flag_visible")
            or bridge_summary.get("visible_live_flag")
            or reconciliation_summary.get("live_trading_flag_visible")
        ),
        "live_trading_authorized": bool(live_decision.get("authorized")),
        "broker_accept_authorized": bool(broker_decision.get("authorized")),
        "money_movement_authorized": money_movement_authorized,
        "all_real_money_authorized": bool(gate_payload.get("all_real_money_authorized")),
        "runtime_gate_pending_capabilities": [
            capability
            for capability, decision in gate_decisions.items()
            if not bool((decision or {}).get("authorized"))
        ],
        "net_profit_loss_account": float(reconciliation_summary.get("net_profit_loss_account") or history_summary.get("net_profit_loss_account") or 0.0),
    }


def _checks(summary: Mapping[str, Any]) -> list[Dict[str, Any]]:
    checks = [
        _check(
            "mt4_session_report_present",
            STATUS_OK if summary.get("session_report_present") else STATUS_UNVERIFIABLE,
            summary.get("session_report_present"),
            "latest MT4 session verifier report is present",
            "MT4 session verifier evidence is available." if summary.get("session_report_present") else "No MT4 session verifier report is available.",
        ),
        _check(
            "mt4_session_roundtrip_ready",
            STATUS_OK if summary.get("session_status") == "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN" else STATUS_WAITING,
            summary.get("session_status"),
            "MT4 session reached ping ACK plus refresh-chain run",
            f"Session status is {summary.get('session_status') or 'missing'}; full operator trust needs the terminal to answer and refresh evidence.",
        ),
        _check(
            "heartbeat_fresh",
            STATUS_OK if summary.get("heartbeat_status") == "FRESH" else STATUS_WAITING,
            summary.get("heartbeat_status"),
            "terminal heartbeat is fresh",
            f"Heartbeat status is {summary.get('heartbeat_status') or 'missing'}.",
        ),
        _check(
            "receipt_lifecycle_clear",
            STATUS_BLOCKED if summary.get("receipt_mismatch_count", 0) > 0 else (STATUS_WAITING if summary.get("pending_receipt_count", 0) > 0 else STATUS_OK),
            {"pending": summary.get("pending_receipt_count"), "mismatches": summary.get("receipt_mismatch_count")},
            "terminal receipts are clear",
            "Receipt lifecycle is clear." if summary.get("pending_receipt_count", 0) == 0 and summary.get("receipt_mismatch_count", 0) == 0 else "Receipt lifecycle still has pending or mismatched terminal responses.",
        ),
        _check(
            "history_export_ready",
            STATUS_OK if summary.get("history_export_verifier_status") in {"MT4_HISTORY_EXPORT_EMPTY", "MT4_HISTORY_EXPORT_INGEST_READY", "MT4_HISTORY_EXPORT_READY_NO_INGEST"} else STATUS_WAITING,
            summary.get("history_export_verifier_status"),
            "MT4 closed-history exporter is producing parseable output",
            f"History export verifier status is {summary.get('history_export_verifier_status') or 'missing'}.",
        ),
        _check(
            "mt5_broker_api_verified",
            STATUS_OK if summary.get("mt5_broker_api_verified") else STATUS_WAITING,
            summary.get("mt5_terminal_api_verifier_status"),
            "MT5 demo broker API is verified",
            "MT5 demo broker API is verified with a connected terminal and account snapshot."
            if summary.get("mt5_broker_api_verified")
            else f"MT5 terminal API verifier status is {summary.get('mt5_terminal_api_verifier_status') or 'missing'}.",
        ),
        _check(
            "mt5_paper_execution_path",
            STATUS_OK
            if summary.get("mt5_paper_execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"}
            else (STATUS_WAITING if summary.get("mt5_paper_order_request_built") else STATUS_UNVERIFIABLE),
            {
                "verifier_status": summary.get("mt5_paper_execution_verifier_status"),
                "order_check_status": summary.get("mt5_paper_order_check_status"),
                "execution_status": summary.get("mt5_paper_execution_status"),
                "execution_error_message": summary.get("mt5_paper_execution_error_message"),
                "terminal_trade_allowed": summary.get("mt5_paper_terminal_trade_allowed"),
            },
            "MT5 paper/demo execution path is proven",
            "MT5 paper/demo execution produced a broker response."
            if summary.get("mt5_paper_execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"}
            else (
                f"MT5 demo order send reached the terminal but was rejected: {summary.get('mt5_paper_execution_error_message')}."
                if summary.get("mt5_paper_execution_status") == "ORDER_REJECTED"
                else
                "MT5 paper/demo request builds and checks, but no demo order has been sent yet."
                if summary.get("mt5_paper_order_request_built")
                else "No MT5 paper execution verifier report is available."
            ),
        ),
        _check(
            "mt5_closed_deal_history_ingested",
            STATUS_OK
            if int(summary.get("mt5_deal_history_closed_position_count") or 0) > 0
            else (STATUS_WAITING if summary.get("mt5_paper_execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"} else STATUS_UNVERIFIABLE),
            {
                "ingest_status": summary.get("mt5_deal_history_ingest_status"),
                "raw_deal_count": summary.get("mt5_deal_history_raw_deal_count"),
                "closed_position_count": summary.get("mt5_deal_history_closed_position_count"),
                "memory_update_count": summary.get("mt5_deal_history_memory_update_count"),
                "unmatched_history_count": summary.get("mt5_deal_history_unmatched_count"),
            },
            "MT5 closed deal history has been read back",
            "MT5 closed deal history was exported and is available for memory/learning."
            if int(summary.get("mt5_deal_history_closed_position_count") or 0) > 0
            else (
                "MT5 demo execution is proven, but closed-deal history has not been read back yet."
                if summary.get("mt5_paper_execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"}
                else "MT5 deal-history ingest waits until a demo execution exists."
            ),
        ),
        _check(
            "positions_reconciled",
            STATUS_OK if str(summary.get("position_reconciliation_status") or "").startswith("TERMINAL_POSITION_RECONCILIATION_READY") else (STATUS_BLOCKED if summary.get("position_reconciliation_status") == "TERMINAL_POSITION_RECONCILIATION_MISMATCH" else STATUS_WAITING),
            summary.get("position_reconciliation_status"),
            "CAS memory matches terminal position evidence",
            f"Position reconciliation status is {summary.get('position_reconciliation_status') or 'missing'}.",
        ),
        _check(
            "live_flag_not_visible",
            STATUS_BLOCKED if summary.get("live_flag_visible") else STATUS_OK,
            summary.get("live_flag_visible"),
            "terminal live flag is not unexpectedly visible",
            "No visible live-trading flag in terminal evidence." if not summary.get("live_flag_visible") else "Terminal evidence exposes a live-trading flag that must be reviewed.",
        ),
        _check(
            "runtime_live_trading_gate",
            STATUS_OK if summary.get("live_trading_authorized") else STATUS_WAITING,
            summary.get("live_trading_authorized"),
            "live trading runtime gate is authorized",
            "Live trading runtime gate is authorized." if summary.get("live_trading_authorized") else "Live trading runtime gate is CURRENTLY NOT LICENSED.",
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


def _operability_status(summary: Mapping[str, Any], checks: list[Mapping[str, Any]]) -> str:
    if summary.get("live_flag_visible"):
        return "TERMINAL_OPERABILITY_LIVE_FLAG_VISIBLE_REVIEW"
    if summary.get("mt5_broker_api_verified") and summary.get("mt5_paper_execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"}:
        return "TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED"
    if summary.get("mt5_broker_api_verified") and summary.get("mt5_paper_execution_status") == "ORDER_REJECTED":
        if "autotrading disabled" in str(summary.get("mt5_paper_execution_error_message") or "").lower():
            return "TERMINAL_OPERABILITY_MT5_AUTOTRADING_DISABLED"
        return "TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_REJECTED"
    if summary.get("mt5_broker_api_verified") and summary.get("mt5_paper_order_request_built"):
        return "TERMINAL_OPERABILITY_MT5_DRY_RUN_READY_DEMO_SEND_REQUIRED"
    if summary.get("mt5_broker_api_verified") and (
        summary.get("session_status") == "MT4_SESSION_NEEDS_MT4_TERMINAL"
        or summary.get("position_reconciliation_status") == "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL"
        or summary.get("history_export_verifier_status") == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL"
    ):
        return "TERMINAL_OPERABILITY_MT5_API_VERIFIED_MT4_BRIDGE_MISSING"
    if summary.get("session_status") == "MT4_SESSION_NEEDS_MT4_TERMINAL":
        return "TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL"
    if summary.get("position_reconciliation_status") == "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL":
        return "TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL"
    if summary.get("history_export_verifier_status") == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL":
        return "TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL"
    if summary.get("session_status") in {None, "MT4_SESSION_WAITING_FOR_TERMINAL_ACTIVATION", "MT4_SESSION_NEEDS_ACTIVATED_MAILBOX"}:
        return "TERMINAL_OPERABILITY_NEEDS_SESSION_REFRESH"
    if summary.get("heartbeat_status") != "FRESH":
        return "TERMINAL_OPERABILITY_NEEDS_HEARTBEAT"
    if not summary.get("account_snapshot_present"):
        return "TERMINAL_OPERABILITY_NEEDS_ACCOUNT_SNAPSHOT"
    if summary.get("receipt_mismatch_count", 0) > 0:
        return "TERMINAL_OPERABILITY_RECEIPT_MISMATCH"
    if summary.get("pending_receipt_count", 0) > 0:
        return "TERMINAL_OPERABILITY_WAITING_FOR_RECEIPTS"
    if summary.get("history_export_verifier_status") not in {"MT4_HISTORY_EXPORT_EMPTY", "MT4_HISTORY_EXPORT_INGEST_READY", "MT4_HISTORY_EXPORT_READY_NO_INGEST"}:
        return "TERMINAL_OPERABILITY_NEEDS_HISTORY_EXPORT"
    if summary.get("position_reconciliation_status") == "TERMINAL_POSITION_RECONCILIATION_MISMATCH":
        return "TERMINAL_OPERABILITY_POSITION_MISMATCH"
    if any(check.get("status") == STATUS_BLOCKED for check in checks):
        return "TERMINAL_OPERABILITY_BLOCKED"
    if summary.get("position_reconciliation_status") == "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS":
        return "TERMINAL_OPERABILITY_READY_OPEN_POSITIONS"
    if summary.get("position_reconciliation_status") == "TERMINAL_POSITION_RECONCILIATION_READY_FLAT":
        return "TERMINAL_OPERABILITY_READY_FLAT"
    return "TERMINAL_OPERABILITY_UNVERIFIABLE"


def _go_no_go(status: str, summary: Mapping[str, Any]) -> Dict[str, Any]:
    terminal_go = status in {
        "TERMINAL_OPERABILITY_READY_OPEN_POSITIONS",
        "TERMINAL_OPERABILITY_READY_FLAT",
        "TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED",
    }
    live_order_go = terminal_go and bool(summary.get("live_trading_authorized"))
    broker_accept_go = live_order_go and bool(summary.get("broker_accept_authorized"))
    money_movement_go = broker_accept_go and bool(summary.get("money_movement_authorized"))
    reasons = []
    if not terminal_go:
        reasons.append(status)
    if terminal_go and not summary.get("live_trading_authorized"):
        reasons.append("live_trading CURRENTLY NOT LICENSED")
    if live_order_go and not summary.get("broker_accept_authorized"):
        reasons.append("broker_accept CURRENTLY NOT LICENSED")
    if broker_accept_go and not summary.get("money_movement_authorized"):
        reasons.append("money_movement CURRENTLY NOT LICENSED")
    return {
        "terminal_lane_go": terminal_go,
        "live_order_go": live_order_go,
        "broker_accept_go": broker_accept_go,
        "money_movement_go": money_movement_go,
        "blocking_reasons": reasons,
    }


def _next_action(status: str, summary: Mapping[str, Any]) -> str:
    if status == "TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL":
        return "Install/open MT4, identify the terminal data folder, run the session verifier with --install, attach both CASForexBridgeEA.mq4 and CASForexHistoryExporterEA.mq4, then rerun operability."
    if status == "TERMINAL_OPERABILITY_MT5_API_VERIFIED_MT4_BRIDGE_MISSING":
        return "MT5 demo broker API is verified on this machine. Next choose the operating lane: wire paper/demo execution through the MT5 bridge, or install/attach MT4 if the EA mailbox path is still preferred."
    if status == "TERMINAL_OPERABILITY_MT5_DRY_RUN_READY_DEMO_SEND_REQUIRED":
        return "MT5 request build and order_check are ready in dry-run mode. Next run the MT5 paper execution verifier with --execute-demo-order --confirm-demo-order on a demo terminal that allows trading, then rerun operability."
    if status == "TERMINAL_OPERABILITY_MT5_AUTOTRADING_DISABLED":
        return "MT5 demo order send reached the terminal, but MT5 returned AutoTrading disabled by client. Turn on Algo Trading/AutoTrading in the MT5 terminal, confirm the EA/trading permissions, rerun the MT5 paper execution verifier, then rerun operability."
    if status == "TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_REJECTED":
        return "MT5 demo order send reached the terminal but was rejected. Inspect mt5_paper_execution_error_message, resolve the broker/terminal reason, rerun the MT5 paper execution verifier, then rerun operability."
    if status == "TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED":
        if int(summary.get("mt5_deal_history_closed_position_count") or 0) == 0:
            return "MT5 demo execution path is proven. Next run MT5 deal-history ingest so the closed trade, P/L, commission, and swap are read back from account history, then rerun memory, daily rollup, and operability."
        if int(summary.get("mt5_deal_history_memory_update_count") or 0) == 0:
            return "MT5 demo execution and closed-deal history are proven, but the deal has not matched a CAS memory row yet. Add/retain broker_ticket, command_id, or receipt_id linkage, then rerun memory, daily rollup, and operability."
        return "MT5 demo execution path and closed-deal history are proven. Rerun agent memory, daily rollup, strategy-dev queue, and operability after new terminal evidence settles."
    if status == "TERMINAL_OPERABILITY_NEEDS_SESSION_REFRESH":
        return "Run the MT4 terminal session verifier until activation, ping ACK, supervisor, watcher, and refresh chain evidence are present."
    if status == "TERMINAL_OPERABILITY_NEEDS_HEARTBEAT":
        return "Attach and run CASForexBridgeEA.mq4 until heartbeat.json is fresh, then rerun bridge supervisor and operability."
    if status == "TERMINAL_OPERABILITY_NEEDS_ACCOUNT_SNAPSHOT":
        return "Generate a terminal receipt/account snapshot so balance, equity, and open positions are visible to CAS."
    if status == "TERMINAL_OPERABILITY_WAITING_FOR_RECEIPTS":
        return "Let MT4 answer pending commands, run terminal_receipt_ingest, rebuild memory, rerun reconciliation, then rerun operability."
    if status == "TERMINAL_OPERABILITY_RECEIPT_MISMATCH":
        return "Inspect receipt hash mismatches before allowing more same-symbol terminal commands."
    if status == "TERMINAL_OPERABILITY_NEEDS_HISTORY_EXPORT":
        return "Attach/run CASForexHistoryExporterEA.mq4 and rerun the MT4 history export verifier until output is parseable."
    if status == "TERMINAL_OPERABILITY_POSITION_MISMATCH":
        return "Inspect unmatched open positions and closed-history rows before allowing another same-symbol cycle."
    if status == "TERMINAL_OPERABILITY_LIVE_FLAG_VISIBLE_REVIEW":
        return "Review the visible terminal live flag against runtime gates before any live command path is allowed."
    if status in {"TERMINAL_OPERABILITY_READY_OPEN_POSITIONS", "TERMINAL_OPERABILITY_READY_FLAT"} and not summary.get("live_trading_authorized"):
        return "Terminal lane is operable, but live trading remains CURRENTLY NOT LICENSED until owner runtime requirements are configured."
    if status == "TERMINAL_OPERABILITY_READY_OPEN_POSITIONS":
        return "Terminal lane is operable with reconciled open positions; keep supervisor/history exporter running and route new commands through receipt gates."
    if status == "TERMINAL_OPERABILITY_READY_FLAT":
        return "Terminal lane is operable and flat; next command cycle can start if owner/runtime gates authorize the intended mode."
    return "Run terminal session, history export verifier, position reconciliation, and runtime gates again; fix the first WAITING/BLOCKED check."


def _operator_commands(summary: Mapping[str, Any]) -> Dict[str, str]:
    return {
        "terminal_session": "py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir <MT4_DATA_DIR> --install --wait-seconds 10",
        "receipt_ingest": "py -3.12 scripts/run_terminal_receipt_ingest.py",
        "history_export_verifier": "py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir <MT4_DATA_DIR>\\MQL4\\Files\\CASForexMailbox --summary-only",
        "mt5_paper_execution_dry_run": "py -3.12 scripts/run_mt5_paper_execution_verifier.py --summary-only",
        "mt5_paper_execution_demo_order": "py -3.12 scripts/run_mt5_paper_execution_verifier.py --execute-demo-order --confirm-demo-order --summary-only",
        "mt5_deal_history_ingest": "py -3.12 scripts/run_mt5_deal_history_ingest.py --days-back 7 --summary-only",
        "position_reconciliation": "py -3.12 scripts/run_terminal_position_reconciliation.py --summary-only",
        "operability_verifier": "py -3.12 scripts/run_terminal_operability_verifier.py --summary-only",
        "live_gate_status": f"live_trading_authorized={bool(summary.get('live_trading_authorized'))}",
    }
