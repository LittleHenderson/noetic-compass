"""Lead-specific paper-proof ledgers for CAS FOREX.

The proof ledger keeps a candidate strategy visible while it earns real paper
evidence. It records daily Evidence Packets and refuses to convert research
evidence into broker authority.
"""

from __future__ import annotations

import json
import uuid
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.evidence import (
    ForexEvidencePacket,
    PacketStatus,
    PaperTradingSessionReport,
)
from cas_forex.time_utils import utc_now


PAPER_PROOF_CLAIM_BOUNDARY = (
    "Paper proof is incomplete until 30 real trading days verify. "
    "Live trading, broker ACCEPT, and payment transfers remain NOT LICENSED."
)
INDEX_TSMOM_126_PLAN_ID = "index-tsmom-126-d1-paper-proof"
BROKER_EXPORT_HASHED = "BROKER_EXPORT_HASHED"
BROKER_API_VERIFIED = "BROKER_API_VERIFIED"
PAPER_RECEIPT_ATTESTATIONS = {BROKER_EXPORT_HASHED, BROKER_API_VERIFIED}
VERIFIED_PAPER_BROKER_MODES = {"PAPER_MT5", "PAPER_MT4", "PAPER_BROKER_DEMO"}


@dataclass(frozen=True)
class PaperProofPlan:
    """Research-to-paper proof plan for a single strategy lead."""

    plan_id: str
    lead_id: str
    strategy_setting: str
    symbols: List[str]
    timeframe: str
    required_trading_days: int = 30
    owner_mode: str = "LIMITED_PAPER"
    max_paper_trades_per_day: int = 3
    risk_limits: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    deployment_status: str = "NOT LICENSED"
    broker_accept_status: str = "NOT LICENSED"
    payment_transfer_status: str = "NOT LICENSED"
    claim_boundary: str = PAPER_PROOF_CLAIM_BOUNDARY


def build_index_tsmom_126_paper_proof_plan() -> PaperProofPlan:
    """Build the current strongest index TSMOM paper-proof plan."""

    return PaperProofPlan(
        plan_id=INDEX_TSMOM_126_PLAN_ID,
        lead_id="index_tsmom_126_d1",
        strategy_setting="tsmom_126_250_2_10",
        symbols=["US30", "NAS100"],
        timeframe="D1",
        owner_mode="LIMITED_PAPER",
        max_paper_trades_per_day=3,
        risk_limits={
            "seed_capital_usd_range": [2000, 5000],
            "monthly_income_target_usd_range": [5000, 12000],
            "capital_goal_risk_label": "SURVIVAL_RISK",
            "max_drawdown_pct_research_gate": 8.0,
            "max_daily_paper_trades": 3,
            "live_funds_allowed": False,
            "auto_deposit_or_card_transfer_allowed": False,
        },
        evidence_refs=[
            "evidence_runs/index_tsmom_h1_d1_go/walk-forward-20260622054921-report.json",
            "evidence_runs/condition_tally/condition-tally-20260622055042-report.json",
            "evidence_runs/index_tsmom_sdg_owner_go/condition-lab-20260622055024-report.json",
            "evidence_runs/owner_promotion_review/owner-promotion-review-20260622055433-report.json",
        ],
    )


def write_paper_proof_plan(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    """Persist a paper-proof plan next to its daily evidence chain."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / f"{plan.plan_id}-plan.json"
    plan_path.write_text(json.dumps(asdict(plan), indent=2), encoding="utf-8")
    return plan_path


def paper_proof_store_path(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    """Return the append-only evidence-chain path for this plan."""

    return Path(output_dir) / f"{plan.plan_id}.jsonl"


def append_paper_proof_day(
    plan: PaperProofPlan,
    output_dir: str | Path,
    *,
    trading_date: Optional[date] = None,
    orders_attempted: int = 0,
    orders_paper_executed: int = 0,
    broker_mode: str = "PAPER_PLAN_ONLY",
    open_positions_reconciled: bool = True,
    notes: Optional[List[str]] = None,
    broker_receipt: Optional[Mapping[str, Any]] = None,
    allow_api_verified_receipt: bool = False,
) -> Dict[str, Any]:
    """Append one paper-proof day to the plan ledger.

    This function is intentionally paper-only. It refuses live mode. User
    supplied broker exports are hash-bound but do not count as source-verified;
    only a future broker/demo adapter may pass allow_api_verified_receipt=True.
    """

    if config.live_mode or not config.paper_trading:
        raise PermissionError("Paper proof requires paper_trading=True and live_mode=False.")

    day = trading_date or utc_now().date()
    if day.weekday() >= 5:
        raise ValueError(f"{day.isoformat()} is not a weekday trading date.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(paper_proof_store_path(plan, out_dir), run_id=plan.plan_id)
    existing_summaries = _load_daily_summaries(store, dedupe=False)
    existing_dates = {str(summary.get("date")) for summary in existing_summaries}
    duplicate_date = day.isoformat() in existing_dates
    if duplicate_date and broker_receipt is None:
        raise ValueError(f"Paper proof already has an entry for {day.isoformat()}.")
    receipt_summary: Dict[str, Any] = {}
    if broker_receipt is not None:
        receipt_summary = validate_paper_broker_receipt(
            plan,
            broker_receipt,
            expected_date=day,
            allow_api_verified=allow_api_verified_receipt,
        )

    if duplicate_date:
        trading_day = int(
            next(
                summary.get("trading_day", 0)
                for summary in existing_summaries
                if str(summary.get("date")) == day.isoformat()
            )
            or len(_load_daily_summaries(store)) + 1
        )
    else:
        trading_day = len(_load_daily_summaries(store)) + 1
    if receipt_summary:
        orders_attempted = int(receipt_summary["orders_attempted"])
        orders_paper_executed = int(receipt_summary["orders_paper_executed"])
        broker_mode = str(receipt_summary["broker_mode"])
        open_positions_reconciled = bool(receipt_summary["open_positions_reconciled"])
    summary = {
        "plan_id": plan.plan_id,
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "symbols": plan.symbols,
        "timeframe": plan.timeframe,
        "trading_day": trading_day,
        "date": day.isoformat(),
        "orders_attempted": int(orders_attempted),
        "orders_paper_executed": int(orders_paper_executed),
        "broker_mode": broker_mode,
        "broker_source_verified": bool(receipt_summary.get("broker_source_verified", False)),
        "broker_receipt_validated": bool(receipt_summary),
        "broker_receipt_hash_sha256": receipt_summary.get("receipt_hash_sha256"),
        "broker_api_authenticated": bool(receipt_summary.get("broker_api_authenticated", False)),
        "receipt_validation_status": receipt_summary.get("receipt_validation_status", "PLAN_ONLY"),
        "receipt_id": receipt_summary.get("receipt_id"),
        "provider_receipt_id": receipt_summary.get("provider_receipt_id"),
        "terminal_name": receipt_summary.get("terminal_name"),
        "account_id_hash": receipt_summary.get("account_id_hash"),
        "server": receipt_summary.get("server"),
        "broker_export_sha256": receipt_summary.get("broker_export_sha256"),
        "account_snapshot": receipt_summary.get("account_snapshot"),
        "realized_pnl": _coerce_pnl(receipt_summary.get("realized_pnl")),
        "open_positions_reconciled": bool(open_positions_reconciled),
        "live_mode": False,
        "deployment_status": "NOT LICENSED",
        "claim_boundary": PAPER_PROOF_CLAIM_BOUNDARY,
    }
    packet_notes = [
        "Lead-specific paper-proof heartbeat; no live order route invoked.",
        PAPER_PROOF_CLAIM_BOUNDARY,
    ]
    if receipt_summary.get("broker_source_verified"):
        packet_notes.append("Broker/demo API-verified paper receipt attached.")
    elif receipt_summary:
        packet_notes.append(
            "Broker/demo receipt hash attached but not API-authenticated; this day does not satisfy verified paper-source proof."
        )
    else:
        packet_notes.append("Broker/demo source is not verified by this offline runner.")
    packet_notes.extend(notes or [])
    source = "paper-proof-broker-receipt" if receipt_summary else "paper-proof-plan"
    trace_suffix = f"day-{trading_day:02d}"
    if receipt_summary and duplicate_date:
        trace_suffix = f"{trace_suffix}-receipt-{store.record_count + 1:02d}"
    packet = ForexEvidencePacket(
        packet_id=str(uuid.uuid4()),
        trace_id=f"{plan.plan_id}-{trace_suffix}",
        status=PacketStatus.SUPPRESSED,
        notes=packet_notes,
        close_outcome=summary,
    )
    packet.finalize()
    receipt = store.append(packet, source=source)
    summary["receipt"] = receipt.model_dump(mode="json")
    return summary


def paper_broker_receipt_template(
    plan: PaperProofPlan,
    *,
    trading_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Return a broker/demo paper receipt template for this proof plan."""

    day = trading_date or utc_now().date()
    return {
        "receipt_id": f"{plan.plan_id}-{day.isoformat()}-broker-demo-receipt",
        "source_attestation": BROKER_EXPORT_HASHED,
        "broker_mode": "PAPER_MT5",
        "trading_date": day.isoformat(),
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "symbols": plan.symbols,
        "timeframe": plan.timeframe,
        "orders_attempted": 0,
        "orders_paper_executed": 0,
        "realized_pnl": 0.0,
        "open_positions_reconciled": True,
        "live_mode": False,
        "broker_export_sha256": "replace_with_sha256_of_broker_export_file",
        "account_id_hash": "replace_with_hash_not_raw_account_number",
        "server": "replace_with_demo_server_name",
        "terminal_name": "replace_with_terminal_name",
        "provider_receipt_id": "replace_with_broker_or_demo_export_id",
        "order_ids": [],
        "notes": [
            "This template is not proof until populated from a paper/demo broker export.",
            PAPER_PROOF_CLAIM_BOUNDARY,
        ],
    }


def validate_paper_broker_receipt(
    plan: PaperProofPlan,
    receipt: Mapping[str, Any],
    *,
    expected_date: date,
    allow_api_verified: bool = False,
) -> Dict[str, Any]:
    """Validate and hash a paper/demo broker receipt for a proof day."""

    if not isinstance(receipt, Mapping):
        raise ValueError("Broker receipt must be a JSON object.")
    required = {
        "receipt_id",
        "source_attestation",
        "broker_mode",
        "trading_date",
        "lead_id",
        "strategy_setting",
        "symbols",
        "timeframe",
        "orders_attempted",
        "orders_paper_executed",
        "open_positions_reconciled",
        "live_mode",
        "broker_export_sha256",
        "account_id_hash",
        "server",
    }
    missing = sorted(key for key in required if key not in receipt)
    if missing:
        raise ValueError(f"Broker receipt missing required fields: {missing}")

    attestation = str(receipt["source_attestation"])
    if attestation not in PAPER_RECEIPT_ATTESTATIONS:
        raise ValueError(f"Unsupported source_attestation: {attestation}")
    broker_mode = str(receipt["broker_mode"])
    if broker_mode not in VERIFIED_PAPER_BROKER_MODES:
        raise ValueError(f"Broker receipt must use a paper/demo broker mode, got {broker_mode}")
    if bool(receipt.get("live_mode")):
        raise ValueError("Broker receipt live_mode must be false.")
    if str(receipt["lead_id"]) != plan.lead_id:
        raise ValueError("Broker receipt lead_id does not match plan.")
    if str(receipt["strategy_setting"]) != plan.strategy_setting:
        raise ValueError("Broker receipt strategy_setting does not match plan.")
    if str(receipt["timeframe"]) != plan.timeframe:
        raise ValueError("Broker receipt timeframe does not match plan.")

    receipt_date = date.fromisoformat(str(receipt["trading_date"]))
    if receipt_date != expected_date:
        raise ValueError(
            f"Broker receipt date {receipt_date.isoformat()} does not match expected {expected_date.isoformat()}."
        )
    symbols = [str(symbol) for symbol in receipt["symbols"]]
    if sorted(symbols) != sorted(plan.symbols):
        raise ValueError("Broker receipt symbols must match the proof plan symbols.")

    orders_attempted = int(receipt["orders_attempted"])
    orders_paper_executed = int(receipt["orders_paper_executed"])
    if orders_attempted < 0 or orders_paper_executed < 0:
        raise ValueError("Broker receipt order counts must be non-negative.")
    if orders_paper_executed > orders_attempted:
        raise ValueError("orders_paper_executed cannot exceed orders_attempted.")

    broker_export_sha256 = str(receipt["broker_export_sha256"])
    if not _is_sha256_hex(broker_export_sha256):
        raise ValueError("broker_export_sha256 must be a 64-character SHA-256 hex digest.")
    account_id_hash = str(receipt["account_id_hash"])
    if len(account_id_hash) < 32 or " " in account_id_hash:
        raise ValueError("account_id_hash must be a hash-like value, not a raw account label.")
    if not str(receipt["server"]).strip():
        raise ValueError("Broker receipt server must be present.")

    broker_api_authenticated = attestation == BROKER_API_VERIFIED and allow_api_verified
    validation_status = BROKER_API_VERIFIED if broker_api_authenticated else BROKER_EXPORT_HASHED
    account_snapshot = _normalize_account_snapshot(receipt.get("account_snapshot") or {})
    normalized = {
        "receipt_id": str(receipt["receipt_id"]),
        "receipt_validation_status": validation_status,
        "source_attestation": attestation,
        "broker_mode": broker_mode,
        "trading_date": receipt_date.isoformat(),
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "symbols": symbols,
        "timeframe": plan.timeframe,
        "orders_attempted": orders_attempted,
        "orders_paper_executed": orders_paper_executed,
        "open_positions_reconciled": bool(receipt["open_positions_reconciled"]),
        "live_mode": False,
        "broker_export_sha256": broker_export_sha256,
        "account_id_hash": account_id_hash,
        "server": str(receipt["server"]),
        "terminal_name": receipt.get("terminal_name"),
        "provider_receipt_id": receipt.get("provider_receipt_id"),
        "order_ids": list(receipt.get("order_ids", [])),
        "broker_api_authenticated": broker_api_authenticated,
        "broker_source_verified": broker_api_authenticated,
        "account_snapshot": account_snapshot,
        "realized_pnl": _coerce_pnl(receipt.get("realized_pnl")),
    }
    normalized["receipt_hash_sha256"] = _sha256_json(normalized)
    return normalized



def _normalize_account_snapshot(value: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}

    def number(key: str) -> float | None:
        raw = value.get(key)
        if raw is None:
            return None
        try:
            return round(float(raw), 2)
        except (TypeError, ValueError):
            return None

    snapshot = {
        "balance": number("balance"),
        "equity": number("equity"),
        "margin": number("margin"),
        "margin_free": number("margin_free"),
        "currency": value.get("currency"),
        "leverage": value.get("leverage"),
        "server": value.get("server"),
        "account_id_hash": value.get("account_id_hash"),
    }
    return {k: v for k, v in snapshot.items() if v is not None}

def summarize_paper_proof(
    plan: PaperProofPlan,
    output_dir: str | Path,
) -> PaperTradingSessionReport:
    """Summarize the paper-proof ledger and keep deployment gates honest."""

    store = EvidenceStore(paper_proof_store_path(plan, output_dir), run_id=plan.plan_id)
    summaries = _load_daily_summaries(store)
    chain_verified = store.verify_chain()
    live_mode_used = bool(config.live_mode) or any(bool(s.get("live_mode")) for s in summaries)
    open_positions_reconciled = bool(summaries) and all(
        bool(summary.get("open_positions_reconciled")) for summary in summaries
    )
    broker_verified_days = sum(
        1 for summary in summaries if bool(summary.get("broker_source_verified"))
    )
    profit = _profit_metrics(plan, summaries)

    report = PaperTradingSessionReport(
        report_id=f"report-{plan.plan_id}",
        session_id=plan.plan_id,
        required_trading_days=plan.required_trading_days,
        completed_trading_days=len(summaries),
        symbols=plan.symbols,
        packet_count=store.record_count,
        chain_verified=chain_verified,
        live_mode_used=live_mode_used,
        open_positions_reconciled=open_positions_reconciled,
        daily_summaries=summaries,
        broker_verified_days=broker_verified_days,
        net_pnl_usd=round(profit["net_pnl_usd"], 2),
        max_drawdown_pct=round(profit["max_drawdown_pct"], 2),
        days_with_trades=profit["days_with_trades"],
        min_trade_days_required=profit["min_trade_days"],
        profit_passed=profit["profit_passed"],
        profit_thresholds=profit["thresholds"],
    )

    if len(summaries) < plan.required_trading_days:
        report.failure_reasons.append(
            f"paper_days {len(summaries)} < required {plan.required_trading_days}"
        )
    if broker_verified_days < plan.required_trading_days:
        report.failure_reasons.append(
            f"broker_verified_days {broker_verified_days} < required {plan.required_trading_days}"
        )
    if not chain_verified:
        report.failure_reasons.append("Evidence chain did not verify.")
    if live_mode_used:
        report.failure_reasons.append("Live mode was used during a paper-proof session.")
    if not open_positions_reconciled:
        report.failure_reasons.append("Open positions were not reconciled for every day.")
    if not profit["net_ok"]:
        report.failure_reasons.append(
            f"net P&L {report.net_pnl_usd:.2f} is not above the required "
            f"{profit['thresholds']['min_net_pnl_usd']:.2f} (proof must be net-positive)"
        )
    if not profit["dd_ok"]:
        report.failure_reasons.append(
            f"max drawdown {report.max_drawdown_pct:.2f}% exceeds the "
            f"{profit['thresholds']['max_drawdown_pct']:.2f}% limit"
        )
    if not profit["trades_ok"]:
        report.failure_reasons.append(
            f"days with real trades {report.days_with_trades} < required "
            f"{report.min_trade_days_required}"
        )

    report.completed_at = utc_now()
    report.passed = (
        len(summaries) >= plan.required_trading_days
        and broker_verified_days >= plan.required_trading_days
        and chain_verified
        and not live_mode_used
        and open_positions_reconciled
        and profit["profit_passed"]
    )
    if not report.passed and not report.failure_reasons:
        report.failure_reasons.append(PAPER_PROOF_CLAIM_BOUNDARY)
    return report


def _coerce_pnl(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _profit_metrics(plan: PaperProofPlan, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Realized P&L, drawdown, and activity across broker-verified proof days.

    Only broker-verified days carry weight - a plan-only heartbeat never counts
    as profit. Drawdown is measured on a realized-equity curve seeded from the
    plan's conservative seed capital. Thresholds are owner-adjustable in-app.
    """

    from cas_forex.proof_control import resolve_profit_thresholds

    thresholds = resolve_profit_thresholds(plan)
    verified = sorted(
        (s for s in summaries if bool(s.get("broker_source_verified"))),
        key=lambda s: str(s.get("date", "")),
    )

    net_pnl = 0.0
    equity = float(thresholds.seed_capital_usd)
    peak = equity
    max_dd_pct = 0.0
    days_with_trades = 0
    for summary in verified:
        pnl = _coerce_pnl(summary.get("realized_pnl"))
        net_pnl += pnl
        equity += pnl
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown = (peak - equity) / peak * 100.0
            if drawdown > max_dd_pct:
                max_dd_pct = drawdown
        if int(summary.get("orders_paper_executed") or 0) > 0:
            days_with_trades += 1

    min_trade_days = thresholds.min_trade_days(plan.required_trading_days)
    net_ok = (not thresholds.require_net_positive) or (net_pnl > thresholds.min_net_pnl_usd)
    dd_ok = max_dd_pct <= thresholds.max_drawdown_pct
    trades_ok = days_with_trades >= min_trade_days
    return {
        "net_pnl_usd": net_pnl,
        "max_drawdown_pct": max_dd_pct,
        "days_with_trades": days_with_trades,
        "min_trade_days": min_trade_days,
        "net_ok": net_ok,
        "dd_ok": dd_ok,
        "trades_ok": trades_ok,
        "profit_passed": net_ok and dd_ok and trades_ok,
        "thresholds": {
            "require_net_positive": thresholds.require_net_positive,
            "min_net_pnl_usd": thresholds.min_net_pnl_usd,
            "max_drawdown_pct": thresholds.max_drawdown_pct,
            "min_trade_days_fraction": thresholds.min_trade_days_fraction,
            "seed_capital_usd": thresholds.seed_capital_usd,
        },
    }


def write_paper_proof_status(
    plan: PaperProofPlan,
    output_dir: str | Path,
    report: Optional[PaperTradingSessionReport] = None,
) -> Path:
    """Write the latest paper-proof status report."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = report or summarize_paper_proof(plan, out_dir)
    status_path = out_dir / f"{plan.plan_id}-status.json"
    payload = {
        "claim_boundary": PAPER_PROOF_CLAIM_BOUNDARY,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
        "report": status.model_dump(mode="json"),
    }
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return status_path


def _load_daily_summaries(store: EvidenceStore, *, dedupe: bool = True) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for record in store._records():
        packet = record.get("packet") if isinstance(record, Mapping) else None
        if not isinstance(packet, Mapping):
            continue
        close_outcome = packet.get("close_outcome")
        if isinstance(close_outcome, Mapping):
            summaries.append(dict(close_outcome))
    if not dedupe:
        return summaries
    return _dedupe_daily_summaries(summaries)


def _dedupe_daily_summaries(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_date: Dict[str, Dict[str, Any]] = {}
    for summary in summaries:
        key = str(summary.get("date", ""))
        if not key:
            continue
        current = by_date.get(key)
        if current is None or _summary_strength(summary) >= _summary_strength(current):
            by_date[key] = summary
    return sorted(by_date.values(), key=lambda item: str(item.get("date", "")))


def _summary_strength(summary: Mapping[str, Any]) -> tuple:
    return (
        bool(summary.get("broker_source_verified")),
        bool(summary.get("broker_receipt_validated")),
        int(summary.get("orders_paper_executed", 0) or 0),
        int(summary.get("orders_attempted", 0) or 0),
    )


def _is_sha256_hex(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_json(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
