"""Plain-English live-operability checklist for CAS Forex.

The lower-level modules track account ledger, market movement, broker receipts,
reconciliation, and runtime gates. This module rolls those pieces into one
owner-readable checklist: what is already built, what is still open, and what
must happen next before live-money execution can be treated as operatable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from cas_forex.authority_boundary import NOT_LICENSED, OPEN
from cas_forex.runtime_gates import AUTHORIZED

PASSED = "PASSED"
OPEN_STATUS = "OPEN"
MISMATCH = "MISMATCH"
UNVERIFIABLE = "UNVERIFIABLE"
NOT_READY_FOR_LIVE = "NOT_READY_FOR_LIVE"
READY_FOR_LIVE_EXECUTION = "READY_FOR_LIVE_EXECUTION"

CLAIM_BOUNDARY = (
    "Live readiness is an operability checklist. It can show which CAS Forex "
    "features are built, verified, open, mismatched, or currently not licensed, "
    "but it does not place orders, create broker ACCEPT, deposit, withdraw, "
    "move bank/card money, or automate payouts by itself."
)


@dataclass(frozen=True)
class LiveReadinessCheck:
    gate_id: str
    label: str
    status: str
    plain_english: str
    evidence: tuple[str, ...] = ()
    next_action: str = ""
    blocks_live: bool = True
    owner_action_required: bool = False
    capability: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveReadinessReport:
    report_kind: str
    mode: str
    overall_status: str
    plain_english_summary: str
    checks_total: int
    checks_passed: int
    checks_open: int
    checks_mismatch: int
    checks_unverifiable: int
    checks_currently_not_licensed: int
    live_money_authorized: bool
    payment_movement_authorized: bool
    next_actions: tuple[str, ...]
    checks: tuple[LiveReadinessCheck, ...]
    claim_boundary: str
    trading_edge_status: str
    live_trading_status: str
    broker_accept_status: str
    auto_deposit_status: str
    debit_card_bank_movement_status: str
    payout_automation_status: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [check.to_dict() for check in self.checks]
        return data


def build_live_readiness_report(
    *,
    ui_readiness: Mapping[str, Any],
    daily_bundle: Mapping[str, Any],
    account_ledger: Mapping[str, Any],
    movement_stream: Mapping[str, Any],
    account_reconciliation: Mapping[str, Any],
    backsolve: Mapping[str, Any],
    walk_forward: Mapping[str, Any],
    mt5_receipt: Mapping[str, Any],
    mt5_probe_status: Mapping[str, Any],
    runtime_gates: Mapping[str, Any],
    authority_boundary: Mapping[str, Any],
    adaptive: Mapping[str, Any] | None = None,
    owner_promotion: Mapping[str, Any] | None = None,
) -> LiveReadinessReport:
    checks = tuple(
        _owner_initial_investment(account_ledger)
        + _movement_checks(movement_stream)
        + _broker_checks(mt5_receipt, mt5_probe_status, account_reconciliation)
        + _evidence_and_edge_checks(ui_readiness, daily_bundle, backsolve, walk_forward, adaptive, owner_promotion)
        + _runtime_capability_checks(runtime_gates)
    )

    passed = sum(1 for check in checks if check.status == PASSED)
    open_count = sum(1 for check in checks if check.status == OPEN_STATUS)
    mismatch = sum(1 for check in checks if check.status == MISMATCH)
    unverifiable = sum(1 for check in checks if check.status == UNVERIFIABLE)
    currently_not_licensed = sum(1 for check in checks if check.status == NOT_LICENSED)
    blocking = [check for check in checks if check.blocks_live and check.status != PASSED]
    all_runtime_authorized = bool(runtime_gates.get("all_real_money_authorized", False))
    live_money_authorized = bool(authority_boundary.get("can_place_live_orders", False)) and all_runtime_authorized
    payment_movement_authorized = bool(authority_boundary.get("can_move_money", False))
    overall = READY_FOR_LIVE_EXECUTION if not blocking and live_money_authorized else NOT_READY_FOR_LIVE

    next_actions = tuple(dict.fromkeys(check.next_action for check in blocking if check.next_action))
    summary = (
        "CAS Forex is moving toward live owner trading, but live execution is not ready yet."
        if overall == NOT_READY_FOR_LIVE
        else "CAS Forex live execution requirements are satisfied by the current evidence and runtime gates."
    )

    return LiveReadinessReport(
        report_kind="cas_forex_live_readiness",
        mode="LIVE_OPERABILITY_CHECKLIST",
        overall_status=overall,
        plain_english_summary=summary,
        checks_total=len(checks),
        checks_passed=passed,
        checks_open=open_count,
        checks_mismatch=mismatch,
        checks_unverifiable=unverifiable,
        checks_currently_not_licensed=currently_not_licensed,
        live_money_authorized=live_money_authorized,
        payment_movement_authorized=payment_movement_authorized,
        next_actions=next_actions,
        checks=checks,
        claim_boundary=CLAIM_BOUNDARY,
        trading_edge_status=OPEN,
        live_trading_status=str(authority_boundary.get("live_trading_status", NOT_LICENSED)),
        broker_accept_status=str(authority_boundary.get("broker_accept_status", NOT_LICENSED)),
        auto_deposit_status=str(authority_boundary.get("auto_deposit_status", NOT_LICENSED)),
        debit_card_bank_movement_status=str(authority_boundary.get("debit_card_bank_movement_status", NOT_LICENSED)),
        payout_automation_status=str(authority_boundary.get("payout_automation_status", NOT_LICENSED)),
        notes=(
            "This report is the plain-English live-money checklist for the cockpit.",
            "A PASSED feature can be built for paper/demo while live authority remains pending.",
        ),
    )


def _owner_initial_investment(account_ledger: Mapping[str, Any]) -> list[LiveReadinessCheck]:
    summary = account_ledger.get("summary") or {}
    initial = float(summary.get("owner_selected_initial_investment_usd", 0.0) or 0.0)
    needs_review = bool(summary.get("requires_new_risk_review_for_selected_investment", False))
    if initial > 0 and not needs_review:
        status = PASSED
        next_action = ""
    elif initial > 0:
        status = OPEN_STATUS
        next_action = "Rerun paper risk sizing for the owner-selected investment amount."
    else:
        status = OPEN_STATUS
        next_action = "Enter a positive initial investment amount for account tracking."
    return [
        LiveReadinessCheck(
            gate_id="owner_initial_investment",
            label="Owner initial investment",
            status=status,
            plain_english=(
                "The owner can model any positive starting account amount."
                if initial > 0
                else "The account needs a positive starting amount before money movement can be tracked."
            ),
            evidence=(f"selected_initial_investment_usd={initial:.2f}",),
            next_action=next_action,
            blocks_live=status != PASSED,
            owner_action_required=status != PASSED,
        )
    ]


def _movement_checks(movement_stream: Mapping[str, Any]) -> list[LiveReadinessCheck]:
    account_streams = set(str(item) for item in (movement_stream.get("account_streams") or ()))
    market_streams = set(str(item) for item in (movement_stream.get("market_streams") or ()))
    positions = list(movement_stream.get("positions") or [])
    quotes = list(movement_stream.get("quotes") or [])
    account_required = {
        "balance",
        "equity",
        "realized_pnl",
        "floating_pnl",
        "swap",
        "commission",
        "broker_fees",
        "margin",
        "free_margin",
        "drawdown",
        "deposit",
        "withdrawal",
        "payout",
        "open_position_count",
    }
    market_required = {
        "bid",
        "ask",
        "mid",
        "spread",
        "synthetic_candle",
        "atr",
        "sl_distance",
        "tp_distance",
        "floating_pnl",
        "margin_estimate",
        "session",
        "source",
    }
    account_missing = tuple(sorted(account_required - account_streams))
    market_missing = tuple(sorted(market_required - market_streams))
    return [
        LiveReadinessCheck(
            gate_id="account_movement_tracking",
            label="Investment movement tracking",
            status=PASSED if not account_missing else OPEN_STATUS,
            plain_english="The cockpit tracks balance, equity, P/L, margin, cashflow, fees, and open-position count.",
            evidence=tuple(sorted(account_streams)),
            next_action=(
                "Add missing account movement fields: " + ", ".join(account_missing) + "."
                if account_missing
                else ""
            ),
            blocks_live=bool(account_missing),
        ),
        LiveReadinessCheck(
            gate_id="market_movement_tracking",
            label="Market movement tracking",
            status=PASSED if quotes and positions and not market_missing else OPEN_STATUS,
            plain_english="The cockpit tracks active quotes, spread, candles, volatility, SL/TP distance, and position P/L.",
            evidence=tuple(sorted(market_streams)) + (f"quotes={len(quotes)}", f"positions={len(positions)}"),
            next_action=(
                "Add missing market movement fields: " + ", ".join(market_missing) + "."
                if market_missing
                else "Keep replacing fallback paper prices with broker/provider tick or M1 data."
            ),
            blocks_live=not quotes or not positions or bool(market_missing),
        ),
    ]


def _broker_checks(
    mt5_receipt: Mapping[str, Any],
    mt5_probe_status: Mapping[str, Any],
    account_reconciliation: Mapping[str, Any],
) -> list[LiveReadinessCheck]:
    receipt_status = str(mt5_receipt.get("receipt_validation_status") or "")
    chain_verified = bool(mt5_receipt.get("chain_verified", False))
    receipt_ok = receipt_status == "BROKER_API_VERIFIED" and chain_verified
    account_snapshot = mt5_receipt.get("account_snapshot") or {}
    if not isinstance(account_snapshot, Mapping):
        account_snapshot = {}
    broker_balance = mt5_receipt.get("balance", account_snapshot.get("balance"))
    broker_equity = mt5_receipt.get("equity", account_snapshot.get("equity"))
    account_snapshot_ok = broker_balance is not None and broker_equity is not None
    recon_status = str(account_reconciliation.get("overall_status") or "MISSING")
    if recon_status == "RECONCILED":
        recon_gate_status = PASSED
    elif recon_status == "RECONCILED_WITH_WARNINGS":
        recon_gate_status = UNVERIFIABLE
    else:
        recon_gate_status = MISMATCH

    return [
        LiveReadinessCheck(
            gate_id="broker_demo_receipt",
            label="Broker/demo receipt",
            status=PASSED if receipt_ok else UNVERIFIABLE,
            plain_english="The app has a verified MT5 demo/broker receipt and evidence chain.",
            evidence=(f"receipt_validation_status={receipt_status}", f"chain_verified={chain_verified}"),
            next_action="" if receipt_ok else "Refresh the MT5 demo receipt until it verifies through the broker/API path.",
            blocks_live=not receipt_ok,
        ),
        LiveReadinessCheck(
            gate_id="broker_account_snapshot",
            label="Broker account snapshot",
            status=PASSED if account_snapshot_ok else UNVERIFIABLE,
            plain_english="The broker/demo receipt exposes balance and equity so CAS numbers can be checked against broker truth.",
            evidence=(f"balance_present={broker_balance is not None}", f"equity_present={broker_equity is not None}"),
            next_action="" if account_snapshot_ok else "Run the MT5 receipt probe from the Windows environment that has MetaTrader5 access.",
            blocks_live=not account_snapshot_ok,
        ),
        LiveReadinessCheck(
            gate_id="account_reconciliation",
            label="CAS vs broker account match",
            status=recon_gate_status,
            plain_english="CAS account numbers must match broker/demo account numbers before live use.",
            evidence=(
                f"overall_status={recon_status}",
                f"checks_ok={account_reconciliation.get('checks_ok')}",
                f"checks_mismatch={account_reconciliation.get('checks_mismatch')}",
                f"checks_unverifiable={account_reconciliation.get('checks_unverifiable')}",
            ),
            next_action=(
                ""
                if recon_gate_status == PASSED
                else "Use /api/forex/reconciliation/account?sync_to_broker=true as a paper/demo preview, then rerun risk sizing from the broker account seed or resolve the mismatch."
            ),
            blocks_live=recon_gate_status != PASSED,
        ),
        LiveReadinessCheck(
            gate_id="latest_probe_health",
            label="Latest MT5 probe health",
            status=PASSED if mt5_probe_status.get("status") == "BROKER_API_VERIFIED" else UNVERIFIABLE,
            plain_english="The newest MT5 probe attempt should be able to reach the demo terminal and produce a receipt.",
            evidence=(
                f"latest_probe_status={mt5_probe_status.get('status')}",
                f"account_snapshot_present={mt5_probe_status.get('account_snapshot_present')}",
            ),
            next_action="" if mt5_probe_status.get("status") == "BROKER_API_VERIFIED" else "Run the MT5 probe from Windows Python/terminal where MetaTrader5 is installed and logged in.",
            blocks_live=mt5_probe_status.get("status") != "BROKER_API_VERIFIED",
        ),
    ]


def _evidence_and_edge_checks(
    ui_readiness: Mapping[str, Any],
    daily_bundle: Mapping[str, Any],
    backsolve: Mapping[str, Any],
    walk_forward: Mapping[str, Any],
    adaptive: Mapping[str, Any] | None,
    owner_promotion: Mapping[str, Any] | None,
) -> list[LiveReadinessCheck]:
    latest_proof = daily_bundle.get("latest_proof") or {}
    chains = ui_readiness.get("chains_verified") or {}
    chains_ok = bool(chains.get("paper_proof")) and bool(chains.get("paper_decision")) and bool(chains.get("paper_risk"))
    complete_bundles = int(ui_readiness.get("complete_bundle_days", 0) or 0)
    min_bundles = int(ui_readiness.get("min_daily_bundles_for_ui", 5) or 5)
    proof_days = int(latest_proof.get("completed_trading_days", ui_readiness.get("completed_trading_days", 0)) or 0)
    required_days = int(latest_proof.get("required_trading_days", 30) or 30)
    proof_ok = complete_bundles >= min_bundles and proof_days >= required_days and bool(latest_proof.get("passed", False))
    viable = int(backsolve.get("viable_scenarios", 0) or 0)
    walk_grade = str(walk_forward.get("research_grade") or "")
    owner_edge_ok = bool((owner_promotion or {}).get("strategy_edge_passed", False))
    best_edge = (owner_promotion or {}).get("best_strategy_edge_candidate") or {}
    edge_ok = owner_edge_ok or (viable > 0 and walk_grade in {"PROMOTED", "WALK_FORWARD_LEAD", "LIVE_CANDIDATE"})
    adaptive_review = ((adaptive or {}).get("adaptive_compounding") or {}).get("latest_review") or {}
    adaptive_memory = list(adaptive_review.get("memory_snapshots") or [])
    adaptive_decisions = list(adaptive_review.get("decisions") or [])

    return [
        LiveReadinessCheck(
            gate_id="evidence_chain",
            label="Evidence chain",
            status=PASSED if chains_ok else OPEN_STATUS,
            plain_english="Paper proof, decision, and risk review chains are present and verified.",
            evidence=(f"paper_proof={chains.get('paper_proof')}", f"paper_decision={chains.get('paper_decision')}", f"paper_risk={chains.get('paper_risk')}"),
            next_action="" if chains_ok else "Regenerate missing proof, decision, or risk chain artifacts.",
            blocks_live=not chains_ok,
        ),
        LiveReadinessCheck(
            gate_id="paper_proof_maturity",
            label="Paper/demo proof window",
            status=PASSED if proof_ok else OPEN_STATUS,
            plain_english="The strategy needs enough verified paper/demo days before live promotion.",
            evidence=(f"complete_bundles={complete_bundles}/{min_bundles}", f"paper_days={proof_days}/{required_days}"),
            next_action="" if proof_ok else "Keep running daily paper bundles until the required proof window is complete.",
            blocks_live=not proof_ok,
        ),
        LiveReadinessCheck(
            gate_id="trading_edge",
            label="Trading edge",
            status=PASSED if edge_ok else OPEN_STATUS,
            plain_english=(
                "The active strategy edge has cleared simulator/walk-forward profitability and drawdown thresholds; paper-proof maturity remains separate."
                if edge_ok and owner_edge_ok
                else "The strategy still needs stronger evidence that it can make money after costs and drawdown."
            ),
            evidence=(
                f"viable_backsolve_scenarios={viable}",
                f"walk_forward_grade={walk_grade}",
                f"owner_promotion_strategy_edge_passed={owner_edge_ok}",
                f"best_strategy_setting={best_edge.get('strategy_setting')}",
                f"best_contexts={','.join(str(item) for item in (best_edge.get('condition_contexts') or []))}",
                f"simulator_wins={best_edge.get('simulator_wins')}",
                f"walk_forward_windows={best_edge.get('walk_forward_windows')}",
                f"positive_rate={best_edge.get('positive_routed_window_rate')}",
                f"mean_return_pct={best_edge.get('mean_return_pct')}",
                f"max_drawdown_pct={best_edge.get('max_drawdown_pct')}",
                f"trades={best_edge.get('trades')}",
            ),
            next_action="" if edge_ok else "Run broker-grade data, cost, walk-forward, and condition-bucket tests until a lead earns promotion.",
            blocks_live=not edge_ok,
        ),
        LiveReadinessCheck(
            gate_id="adaptive_ai_memory",
            label="AI compounding memory",
            status=PASSED if adaptive_decisions and adaptive_memory else OPEN_STATUS,
            plain_english="AI decisions and condition memories are being saved for future compounding/exit analysis.",
            evidence=(f"adaptive_decisions={len(adaptive_decisions)}", f"memory_snapshots={len(adaptive_memory)}"),
            next_action="" if adaptive_decisions and adaptive_memory else "Persist add-to-winner, stop, take-profit, and close outcomes into adaptive memory.",
            blocks_live=not adaptive_decisions or not adaptive_memory,
        ),
    ]


def _runtime_capability_checks(runtime_gates: Mapping[str, Any]) -> list[LiveReadinessCheck]:
    decisions = runtime_gates.get("decisions") or {}
    specs = (
        ("live_trading", "Live order execution", "CAS Forex can send real broker orders only when this is AUTHORIZED."),
        ("broker_accept", "Broker ACCEPT", "Broker ACCEPT can only be created after the live broker path is authorized."),
        ("auto_deposit", "Auto-deposit", "Automated deposit movement requires configured provider credentials and owner enablement."),
        ("bank_card_movement", "Bank/card movement", "Bank/card movement requires configured provider credentials and owner enablement."),
        ("payout_automation", "Payout automation", "Payouts require provider credentials, allowlisted destination, and owner enablement."),
    )
    checks: list[LiveReadinessCheck] = []
    for capability, label, plain in specs:
        decision = decisions.get(capability) or {}
        authorized = bool(decision.get("authorized", False))
        status = AUTHORIZED if authorized else str(decision.get("status") or NOT_LICENSED)
        missing = tuple(str(item) for item in (decision.get("missing_requirements") or ()))
        checks.append(
            LiveReadinessCheck(
                gate_id=capability,
                label=label,
                status=PASSED if authorized else status,
                plain_english=plain,
                evidence=missing if missing else tuple(str(item) for item in (decision.get("satisfied_requirements") or ())),
                next_action="" if authorized else str(decision.get("next_action") or ""),
                blocks_live=not authorized,
                owner_action_required=not authorized,
                capability=capability,
            )
        )
    return checks


def assert_live_readiness_boundary(report: LiveReadinessReport) -> None:
    if report.live_money_authorized and report.overall_status != READY_FOR_LIVE_EXECUTION:
        raise ValueError("live readiness cannot authorize live money while overall status is not ready")
    if report.payment_movement_authorized and report.overall_status != READY_FOR_LIVE_EXECUTION:
        raise ValueError("live readiness cannot authorize payment movement while overall status is not ready")
    if report.trading_edge_status != OPEN:
        raise ValueError("live readiness must preserve trading edge status OPEN until evidence promotes it")
