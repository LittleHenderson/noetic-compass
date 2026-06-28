"""Broker/demo account reconciliation for CAS Forex.

The owner handoff requires that "every balance/equity update should be
reconcilable to broker/demo/account data" and lists "broker reconciliation
snapshots" as a live-readiness requirement. Before any live-money cockpit can be
trusted, the internal paper/demo ledger and movement state must be cross-checked
against the broker/demo receipt evidence, and mismatches must be made visible
instead of hidden.

This module performs that reconciliation. It does not place orders, move money,
or change authority: it only compares the internal account/movement state with
broker/demo receipt evidence and reports per-check status so failures surface in
the cockpit and tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from cas_forex.authority_boundary import AUTHORIZED, NOT_LICENSED, OPEN

CLAIM_BOUNDARY = (
    "Account reconciliation compares internal paper/demo ledger and movement "
    "state against broker/demo receipt evidence. It is read-only verification: "
    "it does not place orders, create broker ACCEPT, deposit, withdraw, move "
    "bank/card money, or automate payouts. Reconciliation passing is required "
    "before live capability can be authorized, but it does not itself authorize "
    "any real-money capability."
)

STATUS_OK = "OK"
STATUS_MISMATCH = "MISMATCH"
STATUS_UNVERIFIABLE = "UNVERIFIABLE"

# Overall verdicts.
RECONCILED = "RECONCILED"
RECONCILED_WITH_WARNINGS = "RECONCILED_WITH_WARNINGS"
RECONCILIATION_FAILED = "RECONCILIATION_FAILED"


@dataclass(frozen=True)
class ReconciliationCheck:
    check_id: str
    description: str
    status: str
    internal_value: Any
    broker_value: Any
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AccountReconciliationReport:
    report_kind: str
    mode: str
    as_of_date: str
    plan_id: str
    lead_id: str
    overall_status: str
    checks_total: int
    checks_ok: int
    checks_mismatch: int
    checks_unverifiable: int
    broker_mode: str
    broker_receipt_id: str | None
    broker_receipt_validation_status: str | None
    broker_chain_verified: bool
    internal_symbols: tuple[str, ...]
    broker_symbols: tuple[str, ...]
    checks: tuple[ReconciliationCheck, ...]
    blockers: tuple[str, ...]
    claim_boundary: str
    trading_edge_status: str
    live_trading_status: str
    broker_accept_status: str
    deployment_status: str
    live_money_authorized: bool
    payment_movement_authorized: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [check.to_dict() for check in self.checks]
        return data


def _symbols_of(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    out: list[str] = []
    for row in rows:
        sym = row.get("symbol")
        if sym and sym not in out:
            out.append(str(sym))
    return tuple(out)


def build_account_reconciliation_report(
    account_ledger: Mapping[str, Any],
    broker_receipt: Mapping[str, Any],
    *,
    movement_stream: Mapping[str, Any] | None = None,
) -> AccountReconciliationReport:
    """Reconcile internal paper/demo account state against broker/demo evidence.

    The reconciliation is intentionally conservative: anything that cannot be
    confirmed from broker evidence is reported ``UNVERIFIABLE`` (a warning), and
    only concrete contradictions are reported ``MISMATCH`` (a failure). This
    keeps the cockpit honest about what broker/demo data does and does not yet
    prove, instead of pretending unverifiable values are reconciled.
    """

    summary = account_ledger.get("summary") or {}
    positions = list(account_ledger.get("positions") or [])
    internal_symbols = _symbols_of(positions)
    broker_symbols = tuple(str(s) for s in (broker_receipt.get("symbols") or []))

    checks: list[ReconciliationCheck] = []

    # 1. Broker receipt must be validated, not just present.
    receipt_status = broker_receipt.get("receipt_validation_status")
    receipt_ok = receipt_status in {"BROKER_API_VERIFIED", "VERIFIED"}
    checks.append(
        ReconciliationCheck(
            check_id="broker_receipt_validated",
            description="Broker/demo receipt is validated evidence.",
            status=STATUS_OK if receipt_ok else STATUS_MISMATCH,
            internal_value="expects_validated_receipt",
            broker_value=receipt_status,
            detail=(
                "Broker/demo receipt reports a validated status."
                if receipt_ok
                else "Broker/demo receipt is missing or not validated; account state cannot be reconciled."
            ),
        )
    )

    # 2. Broker evidence chain must be verified.
    chain_verified = bool(broker_receipt.get("chain_verified", False))
    checks.append(
        ReconciliationCheck(
            check_id="broker_chain_verified",
            description="Broker/demo evidence hash chain is verified.",
            status=STATUS_OK if chain_verified else STATUS_MISMATCH,
            internal_value="expects_verified_chain",
            broker_value=chain_verified,
            detail=(
                "Broker/demo evidence chain verified."
                if chain_verified
                else "Broker/demo evidence chain is not verified; reconciliation cannot trust the receipt."
            ),
        )
    )

    # 3. Live-mode safety: internal paper ledger must match a non-live receipt.
    internal_live = bool(account_ledger.get("live_money_authorized", False))
    broker_live = bool(broker_receipt.get("live_mode", False))
    live_consistent = internal_live == broker_live
    checks.append(
        ReconciliationCheck(
            check_id="live_mode_consistency",
            description="Internal live-money authorization matches broker live mode.",
            status=STATUS_OK if live_consistent else STATUS_MISMATCH,
            internal_value=internal_live,
            broker_value=broker_live,
            detail=(
                "Internal and broker live-mode flags agree."
                if live_consistent
                else "Internal and broker live-mode flags disagree; this is a safety mismatch."
            ),
        )
    )

    # 4. Symbol coverage: every internal position symbol should appear in broker symbols.
    if not internal_symbols:
        symbol_status = STATUS_UNVERIFIABLE
        symbol_detail = "No internal open positions to reconcile against broker symbols."
        missing: tuple[str, ...] = ()
    else:
        missing = tuple(sym for sym in internal_symbols if sym not in broker_symbols)
        if not broker_symbols:
            symbol_status = STATUS_UNVERIFIABLE
            symbol_detail = "Broker receipt lists no symbols; internal positions cannot be confirmed."
        elif missing:
            symbol_status = STATUS_MISMATCH
            symbol_detail = f"Internal position symbols missing from broker evidence: {', '.join(missing)}."
        else:
            symbol_status = STATUS_OK
            symbol_detail = "All internal position symbols are present in broker evidence."
    checks.append(
        ReconciliationCheck(
            check_id="symbol_coverage",
            description="Internal position symbols are covered by broker evidence.",
            status=symbol_status,
            internal_value=list(internal_symbols),
            broker_value=list(broker_symbols),
            detail=symbol_detail,
        )
    )

    # 5. Order/position count: internal open positions vs broker reported orders.
    internal_open = int(summary.get("open_position_count", len(positions)) or 0)
    orders_attempted = broker_receipt.get("orders_attempted")
    open_positions_reconciled = bool(broker_receipt.get("open_positions_reconciled", False))
    if orders_attempted is None:
        count_status = STATUS_UNVERIFIABLE
        count_detail = "Broker receipt does not report order counts; internal open count cannot be confirmed."
    elif int(orders_attempted) == 0 and internal_open > 0:
        # Paper/demo receipts commonly attempt zero live orders; this is expected
        # in paper mode and is reported as a warning, not a hard failure, as long
        # as the broker confirms position reconciliation.
        count_status = STATUS_OK if open_positions_reconciled else STATUS_UNVERIFIABLE
        count_detail = (
            "Broker attempted 0 live orders (expected in paper/demo) and confirmed open-position reconciliation."
            if open_positions_reconciled
            else "Broker attempted 0 live orders and did not confirm open-position reconciliation; internal intents are unconfirmed."
        )
    else:
        count_status = STATUS_OK
        count_detail = (
            f"Broker reported {orders_attempted} attempted order(s) against {internal_open} internal open position(s)."
        )
    checks.append(
        ReconciliationCheck(
            check_id="open_position_reconciliation",
            description="Internal open positions reconcile with broker position evidence.",
            status=count_status,
            internal_value=internal_open,
            broker_value={"orders_attempted": orders_attempted, "open_positions_reconciled": open_positions_reconciled},
            detail=count_detail,
        )
    )

    # 6. Balance/equity reconcilability against broker account figures (if present).
    account_snapshot = broker_receipt.get("account_snapshot") or {}
    if not isinstance(account_snapshot, Mapping):
        account_snapshot = {}
    broker_balance = _first_present(broker_receipt, ("balance", "account_balance"))
    broker_equity = _first_present(broker_receipt, ("equity", "account_equity"))
    if broker_balance is None:
        broker_balance = _first_present(account_snapshot, ("balance", "account_balance"))
    if broker_equity is None:
        broker_equity = _first_present(account_snapshot, ("equity", "account_equity"))
    internal_balance = summary.get("balance_usd")
    internal_equity = summary.get("equity_usd")
    if broker_balance is None and broker_equity is None:
        balance_status = STATUS_UNVERIFIABLE
        balance_detail = (
            "Broker/demo receipt does not expose account balance/equity figures; "
            "internal balance/equity is not yet reconcilable to broker truth (live-readiness gap)."
        )
    else:
        bal_ok = broker_balance is None or _close(internal_balance, broker_balance)
        eq_ok = broker_equity is None or _close(internal_equity, broker_equity)
        if bal_ok and eq_ok:
            balance_status = STATUS_OK
            balance_detail = "Internal balance/equity matches broker-reported figures."
        else:
            balance_status = STATUS_MISMATCH
            balance_detail = (
                f"Balance/equity mismatch: internal balance={internal_balance}, equity={internal_equity}; "
                f"broker balance={broker_balance}, equity={broker_equity}."
            )
    checks.append(
        ReconciliationCheck(
            check_id="balance_equity_reconciliation",
            description="Internal balance/equity reconciles to broker/demo account figures.",
            status=balance_status,
            internal_value={"balance_usd": internal_balance, "equity_usd": internal_equity},
            broker_value={"balance": broker_balance, "equity": broker_equity},
            detail=balance_detail,
        )
    )

    # 7. Movement-stream consistency (optional input).
    if movement_stream is not None:
        ms_account = movement_stream.get("account") or {}
        ms_balance = ms_account.get("balance_usd")
        movement_ok = _close(ms_balance, internal_balance)
        checks.append(
            ReconciliationCheck(
                check_id="movement_internal_consistency",
                description="Movement stream account balance matches the ledger balance.",
                status=STATUS_OK if movement_ok else STATUS_MISMATCH,
                internal_value=internal_balance,
                broker_value=ms_balance,
                detail=(
                    "Movement-stream balance matches the account ledger balance."
                    if movement_ok
                    else "Movement-stream balance does not match the account ledger balance."
                ),
            )
        )

    checks_ok = sum(1 for c in checks if c.status == STATUS_OK)
    checks_mismatch = sum(1 for c in checks if c.status == STATUS_MISMATCH)
    checks_unverifiable = sum(1 for c in checks if c.status == STATUS_UNVERIFIABLE)

    if checks_mismatch > 0:
        overall = RECONCILIATION_FAILED
    elif checks_unverifiable > 0:
        overall = RECONCILED_WITH_WARNINGS
    else:
        overall = RECONCILED

    blockers = tuple(
        f"{c.check_id}: {c.detail}" for c in checks if c.status in {STATUS_MISMATCH, STATUS_UNVERIFIABLE}
    )

    notes = [
        "Reconciliation is read-only verification of internal vs broker/demo evidence.",
        "UNVERIFIABLE checks are live-readiness gaps to close before live promotion, not silent passes.",
    ]
    if overall == RECONCILED_WITH_WARNINGS:
        notes.append("Reconciled with warnings: some account fields are not yet provable from broker/demo evidence.")
    elif overall == RECONCILIATION_FAILED:
        notes.append("Reconciliation failed: internal state contradicts broker/demo evidence; do not promote.")

    return AccountReconciliationReport(
        report_kind="cas_forex_account_reconciliation",
        mode="PAPER_DEMO_ACCOUNT_RECONCILIATION",
        as_of_date=str(account_ledger.get("as_of_date") or broker_receipt.get("trading_date") or "unknown-date"),
        plan_id=str(account_ledger.get("plan_id") or "unknown-plan"),
        lead_id=str(account_ledger.get("lead_id") or "unknown-lead"),
        overall_status=overall,
        checks_total=len(checks),
        checks_ok=checks_ok,
        checks_mismatch=checks_mismatch,
        checks_unverifiable=checks_unverifiable,
        broker_mode=str(broker_receipt.get("broker_mode") or "UNKNOWN"),
        broker_receipt_id=broker_receipt.get("receipt_id"),
        broker_receipt_validation_status=broker_receipt.get("receipt_validation_status"),
        broker_chain_verified=chain_verified,
        internal_symbols=internal_symbols,
        broker_symbols=broker_symbols,
        checks=tuple(checks),
        blockers=blockers,
        claim_boundary=CLAIM_BOUNDARY,
        trading_edge_status=OPEN,
        live_trading_status=NOT_LICENSED,
        broker_accept_status=NOT_LICENSED,
        deployment_status="NOT LICENSED",
        live_money_authorized=False,
        payment_movement_authorized=False,
        notes=tuple(notes),
    )


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _close(a: Any, b: Any, *, tol: float = 0.01) -> bool:
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def assert_reconciliation_boundary(report: AccountReconciliationReport) -> None:
    """Reject any reconciliation report that advertises live/payment authority."""
    if report.live_money_authorized or report.payment_movement_authorized:
        raise ValueError("account reconciliation must not authorize live money or payment movement")
    statuses = {report.live_trading_status, report.broker_accept_status}
    if AUTHORIZED in statuses:
        raise ValueError("account reconciliation cannot report AUTHORIZED real-money capability")
    if report.trading_edge_status != OPEN:
        raise ValueError("account reconciliation must preserve trading edge status OPEN")
