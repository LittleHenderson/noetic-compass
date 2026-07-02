"""Verified profit sweep accounting.

This layer is stricter than the older ``ProfitSweeper``: it does not accept a
free-floating "realized profit" number. It derives sweepable money from
broker-confirmed closed trade rows/events, keeps paper/demo profit separate, and
withholds the owner's tax reserve before calculating the payout sweep.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from cas_forex.account_ledger import money, stable_ledger_id
from cas_forex.money_movement import MovementEngine
from cas_forex.payout_recovery import PayoutAttemptStore, default_payout_attempt_store
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP_POLICY_PATH = REPO_ROOT / "runtime" / "profit-sweep-policy.json"
DEFAULT_SWEEP_AUDIT_PATH = REPO_ROOT / "runtime" / "profit-sweep-audit.jsonl"


@dataclass(frozen=True)
class ProfitSweepSettings:
    """Owner settings for verified net winnings sweep."""

    sweep_pct: float = 30.0
    tax_reserve_pct: float = 20.0
    min_sweep_usd: float = 25.0
    destination_id: Optional[str] = None
    allow_principal_sweep: bool = False
    policy_id: str = "verified-profit-sweep-default"

    def normalized(self) -> "ProfitSweepSettings":
        if not 0.0 <= float(self.sweep_pct) <= 100.0:
            raise ValueError("sweep_pct must be between 0 and 100")
        if not 0.0 <= float(self.tax_reserve_pct) <= 100.0:
            raise ValueError("tax_reserve_pct must be between 0 and 100")
        if float(self.min_sweep_usd) < 0:
            raise ValueError("min_sweep_usd must be >= 0")
        return replace(
            self,
            sweep_pct=float(self.sweep_pct),
            tax_reserve_pct=float(self.tax_reserve_pct),
            min_sweep_usd=float(self.min_sweep_usd),
            destination_id=self.destination_id or None,
            allow_principal_sweep=bool(self.allow_principal_sweep),
            policy_id=str(self.policy_id or "verified-profit-sweep-default"),
        )


@dataclass(frozen=True)
class VerifiedWinningsSummary:
    ledger_mode: str
    live_money_authorized: bool
    verified_closed_trade_count: int
    verified_profit_usd: float
    verified_loss_usd: float
    verified_costs_usd: float
    net_verified_winnings_usd: float
    sweepable_winnings_usd: float
    ignored_unverified_rows: int
    claim_status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SweepPreview:
    settings: ProfitSweepSettings
    winnings: VerifiedWinningsSummary
    tax_reserve_usd: float
    post_tax_winnings_usd: float
    sweep_amount_usd: float
    keep_in_broker_usd: float
    principal_sweep_usd: float
    status: str
    reason: str
    payout_gate: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": "cas_forex_verified_profit_sweep_preview",
            "settings": asdict(self.settings),
            "winnings": self.winnings.to_dict(),
            "tax_reserve_usd": self.tax_reserve_usd,
            "post_tax_winnings_usd": self.post_tax_winnings_usd,
            "sweep_amount_usd": self.sweep_amount_usd,
            "keep_in_broker_usd": self.keep_in_broker_usd,
            "principal_sweep_usd": self.principal_sweep_usd,
            "status": self.status,
            "reason": self.reason,
            "payout_gate": self.payout_gate,
            "hard_rule": (
                "Sweep is calculated from broker-confirmed closed-trade net "
                "winnings only. Paper/demo or unverified profit is not real "
                "sweepable money."
            ),
        }


class ProfitSweepPolicyStore:
    def __init__(self, path: Path | str = DEFAULT_SWEEP_POLICY_PATH) -> None:
        self.path = Path(path)

    def load(self) -> ProfitSweepSettings:
        if not self.path.exists():
            return ProfitSweepSettings()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ProfitSweepSettings()
        return ProfitSweepSettings(**payload).normalized()

    def save(self, settings: ProfitSweepSettings) -> ProfitSweepSettings:
        normalized = settings.normalized()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(normalized), indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
        return normalized

    def update(self, **changes: Any) -> ProfitSweepSettings:
        current = self.load()
        allowed = set(asdict(current))
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise ValueError(f"Unknown sweep setting(s): {unknown}")
        return self.save(replace(current, **changes))


class ProfitSweepAuditLog:
    def __init__(self, path: Path | str = DEFAULT_SWEEP_AUDIT_PATH) -> None:
        self.path = Path(path)

    def append(self, action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        record = {
            "audit_id": stable_ledger_id("sweep-audit", action, utc_now().isoformat(), json.dumps(payload, sort_keys=True, default=str)),
            "action": action,
            "timestamp": utc_now().isoformat(),
            "payload": dict(payload),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return record

    def latest(self) -> Optional[dict[str, Any]]:
        if not self.path.exists():
            return None
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError:
            return None


def summarize_verified_winnings(account_ledger: Mapping[str, Any]) -> VerifiedWinningsSummary:
    """Summarize broker-confirmed closed-trade net winnings from a ledger."""
    mode = str(account_ledger.get("mode") or "")
    live_money = bool(account_ledger.get("live_money_authorized", False)) or mode.upper().startswith("LIVE")
    events = list(account_ledger.get("cashflow_events") or [])
    deals = list(account_ledger.get("deals") or [])

    verified_events = [e for e in events if _is_verified_trade_event(e)]
    ignored = len([e for e in events if _is_trade_money_event(e) and not _is_verified_trade_event(e)])
    profit = 0.0
    losses = 0.0
    costs = 0.0
    count = 0

    if verified_events:
        for event in verified_events:
            event_type = str(_get(event, "event_type") or "")
            amount = _event_amount(event)
            if event_type in {"realized_profit", "positive_swap"}:
                profit += max(0.0, amount)
            elif event_type == "realized_loss":
                losses += abs(amount)
            elif event_type in {"commission", "broker_fee", "negative_swap"}:
                costs += abs(amount)
            if event_type in {"realized_profit", "realized_loss"}:
                count += 1
    else:
        for deal in deals:
            if not _is_verified_deal(deal):
                if _looks_like_deal(deal):
                    ignored += 1
                continue
            pnl = float(_get(deal, "net_pnl_usd") or 0.0)
            commission = abs(float(_get(deal, "commission_usd") or 0.0))
            fees = abs(float(_get(deal, "fees_usd") or 0.0))
            swap = float(_get(deal, "swap_usd") or 0.0)
            if pnl >= 0:
                profit += pnl
            else:
                losses += abs(pnl)
            costs += commission + fees + abs(min(0.0, swap))
            profit += max(0.0, swap)
            count += 1

    net = money(max(0.0, profit - losses - costs))
    if not live_money:
        sweepable = 0.0
        status = "DEMO_NOT_SWEEPABLE"
        reason = "Ledger is paper/demo or not live-authorized; demo profit is not real sweepable money."
    elif count <= 0:
        sweepable = 0.0
        status = "NO_VERIFIED_CLOSED_TRADES"
        reason = "No broker-confirmed closed trade profit rows were found."
    elif net <= 0:
        sweepable = 0.0
        status = "NO_NET_WINNINGS"
        reason = "Verified closed trades do not have positive net winnings after losses and costs."
    else:
        sweepable = net
        status = "SWEEPABLE"
        reason = "Positive live broker-confirmed net winnings are available for sweep calculation."

    return VerifiedWinningsSummary(
        ledger_mode=mode,
        live_money_authorized=live_money,
        verified_closed_trade_count=count,
        verified_profit_usd=money(profit),
        verified_loss_usd=money(losses),
        verified_costs_usd=money(costs),
        net_verified_winnings_usd=net,
        sweepable_winnings_usd=money(sweepable),
        ignored_unverified_rows=ignored,
        claim_status=status,
        reason=reason,
    )


def build_sweep_preview(
    account_ledger: Mapping[str, Any],
    settings: ProfitSweepSettings,
    *,
    config: Any = None,
) -> SweepPreview:
    settings = settings.normalized()
    winnings = summarize_verified_winnings(account_ledger)
    from cas_forex import runtime_gates

    payout_gate = runtime_gates.evaluate_payout_automation(config).to_dict()
    sweepable = winnings.sweepable_winnings_usd
    tax = money(sweepable * settings.tax_reserve_pct / 100.0)
    post_tax = money(max(0.0, sweepable - tax))
    sweep_amount = money(post_tax * settings.sweep_pct / 100.0)
    keep = money(post_tax - sweep_amount)
    status = "READY" if sweep_amount >= settings.min_sweep_usd and winnings.claim_status == "SWEEPABLE" else "BLOCKED"
    reason = "Sweep preview ready; payout still requires explicit confirmation and payout gate authorization."
    if winnings.claim_status != "SWEEPABLE":
        reason = winnings.reason
    elif sweep_amount < settings.min_sweep_usd:
        reason = f"Sweep amount {sweep_amount:.2f} below minimum {settings.min_sweep_usd:.2f}."
    return SweepPreview(
        settings=settings,
        winnings=winnings,
        tax_reserve_usd=tax,
        post_tax_winnings_usd=post_tax,
        sweep_amount_usd=sweep_amount,
        keep_in_broker_usd=keep,
        principal_sweep_usd=0.0,
        status=status,
        reason=reason,
        payout_gate=payout_gate,
    )


def request_verified_profit_sweep(
    account_ledger: Mapping[str, Any],
    settings: ProfitSweepSettings,
    *,
    confirm: bool,
    destination_id: Optional[str] = None,
    engine: Optional[MovementEngine] = None,
    audit: Optional[ProfitSweepAuditLog] = None,
    config: Any = None,
    attempt_store: Optional[PayoutAttemptStore] = None,
    idempotency_key: Optional[str] = None,
    live_recovery_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Request a payout of the previewed sweep amount.

    No provider is touched unless ``confirm`` is true and the preview is READY.
    Even then, ``MovementEngine`` re-checks the payout gate before any movement.
    """
    preview = build_sweep_preview(account_ledger, settings, config=config)
    audit = audit or ProfitSweepAuditLog()
    if preview.status != "READY":
        record = audit.append("SWEEP_BLOCKED", preview.to_dict())
        return {"status": "BLOCKED", "preview": preview.to_dict(), "audit": record}
    if live_recovery_report is not None and not bool(live_recovery_report.get("recovery_clear_for_live", False)):
        recovery = _compact_live_recovery(live_recovery_report)
        record = audit.append(
            "SWEEP_LIVE_RECOVERY_BLOCKED",
            {"preview": preview.to_dict(), "live_recovery": recovery},
        )
        return {
            "status": "LIVE_RECOVERY_BLOCKED",
            "detail": (
                "Verified profit sweep is blocked until live recovery is CLEAR; "
                "resolve broker truth, open-position, order-attempt, and payout recovery first."
            ),
            "preview": preview.to_dict(),
            "live_recovery": recovery,
            "audit": record,
        }
    if not confirm:
        record = audit.append("SWEEP_CONFIRM_REQUIRED", preview.to_dict())
        return {
            "status": "CONFIRM_REQUIRED",
            "detail": "Verified profit sweep requires explicit confirm=true before payout is attempted.",
            "preview": preview.to_dict(),
            "audit": record,
        }
    engine = engine or MovementEngine.from_config(config)
    attempt = None
    key = idempotency_key or _sweep_idempotency_key(preview, destination_id or settings.destination_id)
    if bool(preview.payout_gate.get("authorized", False)):
        attempt_store = attempt_store or default_payout_attempt_store()
        attempt, can_call_provider = attempt_store.reserve(
            key,
            amount_usd=preview.sweep_amount_usd,
            destination_id=destination_id or settings.destination_id,
            preview=preview.to_dict(),
        )
        if not can_call_provider:
            record = audit.append(
                "SWEEP_PAYOUT_RECOVERY_BLOCK",
                {"preview": preview.to_dict(), "payout_attempt": attempt},
            )
            return {
                "status": "PAYOUT_RECOVERY_REQUIRED"
                if attempt.get("status") == "RECOVERY_REQUIRED"
                else "PAYOUT_ALREADY_RECORDED",
                "detail": "Payout attempt with this idempotency key already exists; resolve it before retrying.",
                "preview": preview.to_dict(),
                "payout_attempt": attempt,
                "audit": record,
            }
    movement = engine.payout(
        preview.sweep_amount_usd,
        destination_id=destination_id or settings.destination_id,
        strategy_id="verified-profit-sweep",
    )
    if attempt is not None:
        attempt = attempt_store.record_result(key, movement=movement.to_dict())
    record = audit.append(
        "SWEEP_PAYOUT_ATTEMPT",
        {"preview": preview.to_dict(), "movement": movement.to_dict(), "payout_attempt": attempt},
    )
    return {
        "status": movement.status,
        "preview": preview.to_dict(),
        "movement": movement.to_dict(),
        "payout_attempt": attempt,
        "audit": record,
    }


def _sweep_idempotency_key(preview: SweepPreview, destination_id: Optional[str]) -> str:
    winnings = preview.winnings
    material = {
        "policy_id": preview.settings.policy_id,
        "destination_id": destination_id or preview.settings.destination_id or "",
        "sweep_pct": preview.settings.sweep_pct,
        "tax_reserve_pct": preview.settings.tax_reserve_pct,
        "sweep_amount_usd": preview.sweep_amount_usd,
        "ledger_mode": winnings.ledger_mode,
        "verified_closed_trade_count": winnings.verified_closed_trade_count,
        "net_verified_winnings_usd": winnings.net_verified_winnings_usd,
    }
    return stable_ledger_id("verified-profit-sweep", json.dumps(material, sort_keys=True, default=str))


def _compact_live_recovery(report: Mapping[str, Any]) -> dict[str, Any]:
    order_attempt_summary = report.get("order_attempt_summary")
    if not isinstance(order_attempt_summary, Mapping):
        order_attempt_summary = {}
    return {
        "report_kind": report.get("report_kind"),
        "recovery_status": report.get("recovery_status"),
        "recovery_clear_for_live": bool(report.get("recovery_clear_for_live", False)),
        "requires_recovery_review": bool(report.get("requires_recovery_review", False)),
        "evidence_ready_for_owner_accept": bool(report.get("evidence_ready_for_owner_accept", False)),
        "missing_requirements": list(report.get("missing_requirements") or []),
        "current_fingerprint": report.get("current_fingerprint"),
        "order_attempt_summary": {
            "unresolved_real_attempt_count": order_attempt_summary.get("unresolved_real_attempt_count", 0),
            "has_unresolved_real_attempt": bool(order_attempt_summary.get("has_unresolved_real_attempt", False)),
        },
        "next_action": report.get("next_action"),
    }


def _is_trade_money_event(event: Any) -> bool:
    return str(_get(event, "event_type") or "") in {
        "realized_profit",
        "realized_loss",
        "commission",
        "broker_fee",
        "positive_swap",
        "negative_swap",
    }


def _is_verified_trade_event(event: Any) -> bool:
    return _is_trade_money_event(event) and bool(_get(event, "broker_ticket")) and _has_evidence(event)


def _is_verified_deal(deal: Any) -> bool:
    return _looks_like_deal(deal) and bool(_get(deal, "broker_ticket")) and _has_evidence(deal)


def _looks_like_deal(deal: Any) -> bool:
    return _get(deal, "net_pnl_usd") is not None


def _has_evidence(row: Any) -> bool:
    refs = _get(row, "evidence_refs") or ()
    return bool(_get(row, "evidence_packet_id")) or bool(refs)


def _event_amount(event: Any) -> float:
    raw = _get(event, "balance_delta_usd")
    if raw is None:
        raw = _get(event, "amount_usd")
    return float(raw or 0.0)


def _get(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    return getattr(row, key, None)
