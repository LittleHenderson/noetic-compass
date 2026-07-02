"""Durable auto-halt circuit breakers for CAS Forex live-money safety.

The manual emergency stop is necessary, but live money also needs automatic
tripwires. This module evaluates live broker account evidence for max drawdown,
consecutive closed-trade losses, live-vs-paper divergence, and reconciliation
failure. When any hard breaker trips it writes a durable halt latch under
``runtime/``. Runtime gates then treat live trading as not authorized until the
owner explicitly clears that latch.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTO_HALT_STATE_PATH = REPO_ROOT / "runtime" / "auto-halt-state.json"

STATUS_CLEAR = "AUTO_HALT_CLEAR"
STATUS_ACTIVE = "AUTO_HALT_ACTIVE"
CHECK_OK = "OK"
CHECK_TRIPPED = "TRIPPED"
CHECK_UNVERIFIABLE = "UNVERIFIABLE"

CLAIM_BOUNDARY = (
    "Auto-halt is a live-money safety layer. It can disable live trading and "
    "force CAS Forex back to paper/fail-closed mode when evidence trips a "
    "breaker. It does not place orders, close positions, move bank/card money, "
    "automate payouts, or authorize any real-money capability."
)


@dataclass(frozen=True)
class AutoHaltSettings:
    max_account_drawdown_pct: float = 10.0
    max_consecutive_losses: int = 3
    max_live_paper_divergence_pct: float = 25.0

    def normalized(self) -> "AutoHaltSettings":
        if float(self.max_account_drawdown_pct) < 0:
            raise ValueError("max_account_drawdown_pct must be >= 0")
        if int(self.max_consecutive_losses) < 1:
            raise ValueError("max_consecutive_losses must be >= 1")
        if float(self.max_live_paper_divergence_pct) < 0:
            raise ValueError("max_live_paper_divergence_pct must be >= 0")
        return AutoHaltSettings(
            max_account_drawdown_pct=float(self.max_account_drawdown_pct),
            max_consecutive_losses=int(self.max_consecutive_losses),
            max_live_paper_divergence_pct=float(self.max_live_paper_divergence_pct),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())


@dataclass(frozen=True)
class AutoHaltCheck:
    check_id: str
    status: str
    metric: Any
    threshold: Any
    detail: str
    trips_halt: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _state_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_AUTO_HALT_STATE_PATH)


def load_auto_halt_state(path: Path | str | None = None) -> dict[str, Any]:
    target = _state_path(path)
    if not target.exists():
        return {"active": False, "force_paper_mode": False, "reasons": []}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"active": True, "force_paper_mode": True, "reasons": ["AUTO_HALT_STATE_UNREADABLE"]}
    return {
        "active": bool(payload.get("active", False)),
        "force_paper_mode": bool(payload.get("force_paper_mode", False)),
        "halt_id": payload.get("halt_id"),
        "triggered_at": payload.get("triggered_at"),
        "reasons": list(payload.get("reasons") or []),
        "checks": list(payload.get("checks") or []),
        "cleared_at": payload.get("cleared_at"),
        "clear_reason": payload.get("clear_reason"),
    }


def is_auto_halt_active(path: Path | str | None = None) -> bool:
    state = load_auto_halt_state(path)
    return bool(state.get("active") or state.get("force_paper_mode"))


def activate_auto_halt(
    reasons: Sequence[str],
    checks: Sequence[Mapping[str, Any]],
    *,
    path: Path | str | None = None,
) -> dict[str, Any]:
    target = _state_path(path)
    payload = {
        "active": True,
        "force_paper_mode": True,
        "halt_id": stable_ledger_id("auto-halt", utc_now().isoformat(), ",".join(reasons)),
        "triggered_at": utc_now().isoformat(),
        "reasons": list(dict.fromkeys(str(reason) for reason in reasons if reason)),
        "checks": [dict(check) for check in checks],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(target)
    return payload


def clear_auto_halt(
    *,
    confirm_clear: bool,
    reason: str = "OWNER_CLEAR",
    path: Path | str | None = None,
) -> dict[str, Any]:
    if not confirm_clear:
        raise ValueError("confirm_clear=true is required to clear auto-halt")
    target = _state_path(path)
    previous = load_auto_halt_state(target)
    payload = {
        **previous,
        "active": False,
        "force_paper_mode": False,
        "cleared_at": utc_now().isoformat(),
        "clear_reason": reason or "OWNER_CLEAR",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(target)
    return payload


def build_auto_halt_report(
    *,
    live_account_ledger: Optional[Mapping[str, Any]] = None,
    paper_account_ledger: Optional[Mapping[str, Any]] = None,
    reconciliation_report: Optional[Mapping[str, Any]] = None,
    settings: AutoHaltSettings | None = None,
    persist: bool = False,
    state_path: Path | str | None = None,
) -> dict[str, Any]:
    settings = (settings or AutoHaltSettings()).normalized()
    checks = [
        _drawdown_check(live_account_ledger, settings),
        _consecutive_loss_check(live_account_ledger, settings),
        _divergence_check(live_account_ledger, paper_account_ledger, settings),
        _reconciliation_check(live_account_ledger, reconciliation_report),
    ]
    tripped = [check for check in checks if check.trips_halt]
    active_state = load_auto_halt_state(state_path)
    if tripped and persist:
        active_state = activate_auto_halt(
            [check.check_id for check in tripped],
            [check.to_dict() for check in checks],
            path=state_path,
        )
    halt_active = bool(active_state.get("active") or active_state.get("force_paper_mode") or tripped)
    return {
        "report_kind": "cas_forex_auto_halt",
        "generated_at": utc_now().isoformat(),
        "status": STATUS_ACTIVE if halt_active else STATUS_CLEAR,
        "halt_active": halt_active,
        "force_paper_mode": halt_active,
        "settings": settings.to_dict(),
        "checks": [check.to_dict() for check in checks],
        "triggered_checks": [check.check_id for check in tripped],
        "active_state": active_state,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": (
            "Live trading is auto-halted. Review broker/account evidence, keep CAS in paper mode, then clear only after owner verification."
            if halt_active
            else "Auto-halt is clear; continue monitoring live broker truth before any scaling."
        ),
    }


def _drawdown_check(ledger: Optional[Mapping[str, Any]], settings: AutoHaltSettings) -> AutoHaltCheck:
    if not _is_live_ledger(ledger):
        return AutoHaltCheck("max_account_drawdown_pct", CHECK_UNVERIFIABLE, None, settings.max_account_drawdown_pct, "No live account ledger is available.", False)
    summary = ledger.get("summary") or {}
    drawdown = _float(summary.get("drawdown_pct")) or 0.0
    tripped = drawdown >= settings.max_account_drawdown_pct
    return AutoHaltCheck(
        "max_account_drawdown_pct",
        CHECK_TRIPPED if tripped else CHECK_OK,
        round(drawdown, 4),
        settings.max_account_drawdown_pct,
        f"Live account drawdown is {drawdown:.4f}%.",
        tripped,
    )


def _consecutive_loss_check(ledger: Optional[Mapping[str, Any]], settings: AutoHaltSettings) -> AutoHaltCheck:
    if not _is_live_ledger(ledger):
        return AutoHaltCheck("max_consecutive_losses", CHECK_UNVERIFIABLE, None, settings.max_consecutive_losses, "No live account ledger is available.", False)
    losses = _consecutive_closed_losses(ledger)
    tripped = losses >= settings.max_consecutive_losses
    return AutoHaltCheck(
        "max_consecutive_losses",
        CHECK_TRIPPED if tripped else CHECK_OK,
        losses,
        settings.max_consecutive_losses,
        f"Live account has {losses} consecutive closed-trade loss(es).",
        tripped,
    )


def _divergence_check(
    live_ledger: Optional[Mapping[str, Any]],
    paper_ledger: Optional[Mapping[str, Any]],
    settings: AutoHaltSettings,
) -> AutoHaltCheck:
    if not _is_live_ledger(live_ledger):
        return AutoHaltCheck("live_vs_paper_divergence_pct", CHECK_UNVERIFIABLE, None, settings.max_live_paper_divergence_pct, "No live account ledger is available.", False)
    if not paper_ledger:
        return AutoHaltCheck("live_vs_paper_divergence_pct", CHECK_UNVERIFIABLE, None, settings.max_live_paper_divergence_pct, "No paired paper ledger is available.", False)
    paper_summary = paper_ledger.get("summary") or {}
    live_summary = live_ledger.get("summary") or {}
    paper_deals = int(paper_summary.get("deal_count", 0) or 0)
    if paper_deals <= 0:
        return AutoHaltCheck("live_vs_paper_divergence_pct", CHECK_UNVERIFIABLE, None, settings.max_live_paper_divergence_pct, "Paired paper ledger has no closed deals to compare.", False)
    paper_pnl = _float(paper_summary.get("realized_pnl_usd")) or 0.0
    live_pnl = _float(live_summary.get("realized_pnl_usd")) or 0.0
    divergence = abs(live_pnl - paper_pnl) / max(abs(paper_pnl), 1.0) * 100.0
    tripped = divergence >= settings.max_live_paper_divergence_pct
    return AutoHaltCheck(
        "live_vs_paper_divergence_pct",
        CHECK_TRIPPED if tripped else CHECK_OK,
        round(divergence, 4),
        settings.max_live_paper_divergence_pct,
        f"Live realized P/L {live_pnl:.2f} vs paper realized P/L {paper_pnl:.2f}.",
        tripped,
    )


def _reconciliation_check(
    ledger: Optional[Mapping[str, Any]],
    reconciliation_report: Optional[Mapping[str, Any]],
) -> AutoHaltCheck:
    if not _is_live_ledger(ledger):
        return AutoHaltCheck("broker_truth_reconciliation", CHECK_UNVERIFIABLE, None, "RECONCILED", "No live account ledger is available.", False)
    if not reconciliation_report:
        return AutoHaltCheck("broker_truth_reconciliation", CHECK_UNVERIFIABLE, None, "RECONCILED", "No reconciliation report is available.", False)
    status = str(reconciliation_report.get("overall_status") or "")
    tripped = status == "RECONCILIATION_FAILED"
    return AutoHaltCheck(
        "broker_truth_reconciliation",
        CHECK_TRIPPED if tripped else CHECK_OK,
        status or None,
        "RECONCILED",
        f"Broker-truth reconciliation status is {status or 'unavailable'}.",
        tripped,
    )


def _is_live_ledger(ledger: Optional[Mapping[str, Any]]) -> bool:
    return bool(ledger and ledger.get("live_money_authorized") and str(ledger.get("mode") or "").upper().startswith("LIVE"))


def _consecutive_closed_losses(ledger: Mapping[str, Any]) -> int:
    rows: list[tuple[str, float]] = []
    for row in ledger.get("deals") or []:
        rows.append((str(row.get("timestamp") or ""), _float(row.get("net_pnl_usd")) or 0.0))
    if not rows:
        for event in ledger.get("cashflow_events") or []:
            if str(event.get("event_type")) in {"realized_profit", "realized_loss"}:
                rows.append((str(event.get("timestamp") or ""), _float(event.get("balance_delta_usd")) or 0.0))
    count = 0
    for _timestamp, pnl in sorted(rows, key=lambda item: item[0], reverse=True):
        if pnl < 0:
            count += 1
            continue
        break
    return count


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
