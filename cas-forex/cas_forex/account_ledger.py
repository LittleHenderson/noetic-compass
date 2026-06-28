"""Owner-selectable paper/demo account ledger for CAS Forex.

This module is the accounting bridge between today's paper-proof cockpit and the
intended live-money owner cockpit. It lets the owner model any positive initial
investment amount in paper/demo mode, tracks account movement fields using broker
terminal language, and keeps the real-money boundary explicit: these ledger rows
are internal paper/demo evidence until runtime/broker/payment gates authorize
live movement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence

from cas_forex.authority_boundary import AUTHORIZED, NOT_LICENSED, OPEN

CLAIM_BOUNDARY = (
    "Owner investment ledger is internal paper/demo accounting now. It can model "
    "any positive owner-selected initial investment amount and reconcile paper "
    "positions, orders, deals, balance, equity, margin, fees, swap, withdrawals, "
    "and payouts, but it does not deposit funds, withdraw funds, create broker "
    "ACCEPT, place live orders, move bank/card money, or automate payouts until "
    "the owner-controlled runtime gates authorize those capabilities."
)

MODE = "PAPER_DEMO_ACCOUNT_LEDGER"
DEPLOYMENT_STATUS = "NOT LICENSED"

CREDIT_EVENT_TYPES = {"initial_investment", "deposit", "realized_profit", "positive_swap", "balance_adjustment_credit"}
DEBIT_EVENT_TYPES = {"withdrawal", "payout", "realized_loss", "commission", "broker_fee", "negative_swap", "balance_adjustment_debit"}
NEUTRAL_EVENT_TYPES = {"paper_order_intent", "paper_position_snapshot", "paper_deal_snapshot", "risk_reserve", "broker_reconciliation"}
ALL_EVENT_TYPES = CREDIT_EVENT_TYPES | DEBIT_EVENT_TYPES | NEUTRAL_EVENT_TYPES


@dataclass(frozen=True)
class AccountLedgerEvent:
    ledger_id: str
    event_type: str
    timestamp: str
    amount_usd: float
    balance_delta_usd: float
    equity_delta_usd: float
    margin_delta_usd: float = 0.0
    symbol: str | None = None
    side: str | None = None
    lot_size: float | None = None
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    broker_ticket: str | None = None
    simulator_ticket: str | None = None
    strategy_id: str | None = None
    ai_action: str | None = None
    evidence_packet_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    note: str = ""
    external_money_movement: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerminalTradeRow:
    row_id: str
    tab: str
    symbol: str
    side: str
    lot_size: float
    open_price: float
    close_or_current_price: float | None
    stop_loss: float | None
    take_profit: float | None
    timestamp: str
    broker_ticket: str | None
    simulator_ticket: str
    strategy_id: str
    ai_action: str
    evidence_packet_id: str
    net_pnl_usd: float
    swap_usd: float = 0.0
    commission_usd: float = 0.0
    fees_usd: float = 0.0
    status: str = "PAPER_INTENT"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AccountLedgerSummary:
    mode: str
    initial_investment_usd: float
    owner_selected_initial_investment_usd: float
    risk_review_account_equity_usd: float
    requires_new_risk_review_for_selected_investment: bool
    deposit_usd: float
    withdrawals_usd: float
    payouts_usd: float
    realized_pnl_usd: float
    floating_pnl_usd: float
    swap_usd: float
    commission_usd: float
    broker_fees_usd: float
    balance_usd: float
    equity_usd: float
    margin_used_usd: float
    free_margin_usd: float
    planned_risk_usd: float
    planned_risk_pct_of_selected_equity: float
    drawdown_usd: float
    drawdown_pct: float
    event_count: int
    open_position_count: int
    order_count: int
    deal_count: int
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AccountLedgerState:
    report_kind: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    as_of_date: str
    mode: str
    summary: AccountLedgerSummary
    cashflow_events: tuple[AccountLedgerEvent, ...]
    positions: tuple[TerminalTradeRow, ...]
    orders: tuple[TerminalTradeRow, ...]
    deals: tuple[TerminalTradeRow, ...]
    supported_history_tabs: tuple[str, ...]
    supported_time_filters: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_boundary: str
    trading_edge_status: str
    live_trading_status: str
    broker_accept_status: str
    auto_deposit_status: str
    debit_card_bank_movement_status: str
    payout_automation_status: str
    deployment_status: str
    live_money_authorized: bool
    payment_movement_authorized: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["summary"] = self.summary.to_dict()
        data["cashflow_events"] = [event.to_dict() for event in self.cashflow_events]
        data["positions"] = [row.to_dict() for row in self.positions]
        data["orders"] = [row.to_dict() for row in self.orders]
        data["deals"] = [row.to_dict() for row in self.deals]
        return data


def stable_ledger_id(prefix: str, *parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    digest = sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def money(value: float) -> float:
    return round(float(value), 2)


def pct(value: float) -> float:
    return round(float(value), 4)


def validate_initial_investment(initial_investment_usd: float) -> float:
    try:
        amount = float(initial_investment_usd)
    except (TypeError, ValueError) as exc:
        raise ValueError("initial_investment_usd must be a positive number") from exc
    if amount <= 0:
        raise ValueError("initial_investment_usd must be positive")
    return amount


def build_paper_account_ledger(
    *,
    initial_investment_usd: float,
    plan_id: str,
    lead_id: str,
    strategy_setting: str,
    as_of_date: str,
    risk_review_account_equity_usd: float | None = None,
    planned_risk_usd: float = 0.0,
    floating_pnl_usd: float = 0.0,
    margin_used_usd: float = 0.0,
    cashflow_events: Sequence[AccountLedgerEvent] = (),
    positions: Sequence[TerminalTradeRow] = (),
    orders: Sequence[TerminalTradeRow] = (),
    deals: Sequence[TerminalTradeRow] = (),
    evidence_refs: Sequence[str] = (),
) -> AccountLedgerState:
    """Build a paper/demo account ledger from owner-selected investment data.

    ``initial_investment_usd`` is intentionally not fixed at 5,000. Any positive
    amount is accepted. If it differs from the latest paper-risk review equity,
    the ledger still previews the account movement but marks that a fresh paper
    risk review is required before sizing decisions can be treated as current.
    """

    initial = validate_initial_investment(initial_investment_usd)
    risk_equity = float(risk_review_account_equity_usd if risk_review_account_equity_usd is not None else initial)
    if risk_equity <= 0:
        raise ValueError("risk_review_account_equity_usd must be positive when supplied")

    seed_event = AccountLedgerEvent(
        ledger_id=stable_ledger_id("ledger", plan_id, as_of_date, "initial_investment", money(initial)),
        event_type="initial_investment",
        timestamp=f"{as_of_date}T00:00:00Z",
        amount_usd=money(initial),
        balance_delta_usd=money(initial),
        equity_delta_usd=money(initial),
        strategy_id=lead_id,
        evidence_packet_id=plan_id,
        evidence_refs=tuple(evidence_refs),
        note="Owner-selected initial investment for paper/demo account tracking; no external funds moved.",
        external_money_movement=False,
    )
    events = (seed_event, *tuple(cashflow_events))
    _validate_events(events)

    cash_balance = sum(event.balance_delta_usd for event in events)
    floating = float(floating_pnl_usd)
    margin = max(0.0, float(margin_used_usd) + sum(event.margin_delta_usd for event in events))

    realized_pnl = sum(
        event.balance_delta_usd
        for event in events
        if event.event_type in {"realized_profit", "realized_loss"}
    )
    swap = sum(event.balance_delta_usd for event in events if event.event_type in {"positive_swap", "negative_swap"})
    commission = sum(event.balance_delta_usd for event in events if event.event_type == "commission")
    fees = sum(event.balance_delta_usd for event in events if event.event_type == "broker_fee")
    withdrawals = abs(sum(event.balance_delta_usd for event in events if event.event_type == "withdrawal"))
    payouts = abs(sum(event.balance_delta_usd for event in events if event.event_type == "payout"))
    deposits = sum(event.balance_delta_usd for event in events if event.event_type in {"initial_investment", "deposit"})

    equity = cash_balance + floating
    free_margin = max(0.0, equity - margin)
    drawdown = max(0.0, initial - equity)
    requires_review = abs(initial - risk_equity) > 0.0049
    planned_risk_pct = (float(planned_risk_usd) / initial * 100.0) if initial else 0.0

    summary = AccountLedgerSummary(
        mode=MODE,
        initial_investment_usd=money(initial),
        owner_selected_initial_investment_usd=money(initial),
        risk_review_account_equity_usd=money(risk_equity),
        requires_new_risk_review_for_selected_investment=requires_review,
        deposit_usd=money(deposits),
        withdrawals_usd=money(withdrawals),
        payouts_usd=money(payouts),
        realized_pnl_usd=money(realized_pnl),
        floating_pnl_usd=money(floating),
        swap_usd=money(swap),
        commission_usd=money(abs(commission)),
        broker_fees_usd=money(abs(fees)),
        balance_usd=money(cash_balance),
        equity_usd=money(equity),
        margin_used_usd=money(margin),
        free_margin_usd=money(free_margin),
        planned_risk_usd=money(planned_risk_usd),
        planned_risk_pct_of_selected_equity=pct(planned_risk_pct),
        drawdown_usd=money(drawdown),
        drawdown_pct=pct(drawdown / initial * 100.0),
        event_count=len(events),
        open_position_count=len(positions),
        order_count=len(orders),
        deal_count=len(deals),
    )

    notes = [
        "Paper/demo ledger supports owner-selected initial investment; no bank/card/provider movement is performed.",
        "History tabs expose Positions, Orders, and Deals shape now so MT4/MT5-style terminal rows can reconcile later.",
    ]
    if requires_review:
        notes.append(
            "Selected initial investment differs from the latest paper-risk review equity; rerun paper risk sizing for this amount before relying on lots/risk percentages."
        )

    return AccountLedgerState(
        report_kind="cas_forex_account_ledger",
        plan_id=plan_id,
        lead_id=lead_id,
        strategy_setting=strategy_setting,
        as_of_date=as_of_date,
        mode=MODE,
        summary=summary,
        cashflow_events=events,
        positions=tuple(positions),
        orders=tuple(orders),
        deals=tuple(deals),
        supported_history_tabs=("Positions", "Orders", "Deals"),
        supported_time_filters=("Seconds", "Minutes", "Hour", "Day", "Week", "Month", "Custom"),
        evidence_refs=tuple(evidence_refs),
        claim_boundary=CLAIM_BOUNDARY,
        trading_edge_status=OPEN,
        live_trading_status=NOT_LICENSED,
        broker_accept_status=NOT_LICENSED,
        auto_deposit_status=NOT_LICENSED,
        debit_card_bank_movement_status=NOT_LICENSED,
        payout_automation_status=NOT_LICENSED,
        deployment_status=DEPLOYMENT_STATUS,
        live_money_authorized=False,
        payment_movement_authorized=False,
        notes=tuple(notes),
    )


def build_account_ledger_from_paper_review(
    risk_review: Mapping[str, Any],
    *,
    initial_investment_usd: float | None = None,
    decision: Mapping[str, Any] | None = None,
    evidence_refs: Sequence[str] = (),
) -> AccountLedgerState:
    """Convert the latest paper risk/decision evidence into an account ledger."""

    risk_equity = float(risk_review.get("account_equity", 0.0) or 0.0)
    initial = validate_initial_investment(initial_investment_usd if initial_investment_usd is not None else risk_equity)
    plan_id = str(risk_review.get("plan_id") or (decision or {}).get("plan_id") or "unknown-plan")
    lead_id = str(risk_review.get("lead_id") or (decision or {}).get("lead_id") or "unknown-lead")
    setting = str(risk_review.get("strategy_setting") or (decision or {}).get("strategy_setting") or "unknown-setting")
    as_of_date = str(risk_review.get("date") or (decision or {}).get("date") or "unknown-date")
    planned_risk = float(risk_review.get("total_planned_risk_usd", 0.0) or 0.0)

    rows = tuple(_rows_from_risk_sizing(risk_review, decision=decision))
    risk_event = AccountLedgerEvent(
        ledger_id=stable_ledger_id("ledger", plan_id, as_of_date, "risk_reserve", money(planned_risk)),
        event_type="risk_reserve",
        timestamp=f"{as_of_date}T00:00:01Z",
        amount_usd=money(planned_risk),
        balance_delta_usd=0.0,
        equity_delta_usd=0.0,
        strategy_id=lead_id,
        evidence_packet_id=str(risk_review.get("review_id") or plan_id),
        evidence_refs=tuple(evidence_refs),
        note="Paper planned-risk reserve for display/reconciliation only; it is not a broker margin debit.",
        external_money_movement=False,
    )
    order_events = tuple(_events_from_terminal_rows(rows, risk_event.timestamp))

    return build_paper_account_ledger(
        initial_investment_usd=initial,
        plan_id=plan_id,
        lead_id=lead_id,
        strategy_setting=setting,
        as_of_date=as_of_date,
        risk_review_account_equity_usd=risk_equity,
        planned_risk_usd=planned_risk,
        cashflow_events=(risk_event, *order_events),
        positions=rows,
        orders=rows,
        deals=(),
        evidence_refs=evidence_refs,
    )


def _rows_from_risk_sizing(
    risk_review: Mapping[str, Any],
    *,
    decision: Mapping[str, Any] | None = None,
) -> Iterable[TerminalTradeRow]:
    plan_id = str(risk_review.get("plan_id") or (decision or {}).get("plan_id") or "unknown-plan")
    lead_id = str(risk_review.get("lead_id") or (decision or {}).get("lead_id") or "unknown-lead")
    strategy_id = str(risk_review.get("strategy_setting") or (decision or {}).get("strategy_setting") or "unknown-setting")
    date = str(risk_review.get("date") or (decision or {}).get("date") or "unknown-date")
    review_id = str(risk_review.get("review_id") or plan_id)
    ai_action_by_symbol: dict[str, str] = {}
    if decision:
        for item in decision.get("symbol_decisions", []) or []:
            symbol = str(item.get("symbol", ""))
            if symbol:
                ai_action_by_symbol[symbol] = str(item.get("action") or decision.get("route_action") or "PAPER_SIGNAL")

    for idx, sizing in enumerate(risk_review.get("sizing", []) or [], start=1):
        symbol = str(sizing.get("symbol") or f"SYMBOL_{idx}")
        proposal_id = str(sizing.get("proposal_id") or stable_ledger_id("proposal", plan_id, date, symbol, idx))
        sim_ticket = stable_ledger_id("sim", plan_id, date, proposal_id)
        side = str(sizing.get("direction") or "UNKNOWN")
        entry = float(sizing.get("entry_price", 0.0) or 0.0)
        row = TerminalTradeRow(
            row_id=stable_ledger_id("row", plan_id, date, proposal_id),
            tab="Positions",
            symbol=symbol,
            side=side,
            lot_size=float(sizing.get("sized_lots", 0.0) or 0.0),
            open_price=entry,
            close_or_current_price=entry,
            stop_loss=_optional_float(sizing.get("stop_loss")),
            take_profit=_optional_float(sizing.get("take_profit")),
            timestamp=f"{date}T00:00:00Z",
            broker_ticket=None,
            simulator_ticket=sim_ticket,
            strategy_id=strategy_id,
            ai_action=ai_action_by_symbol.get(symbol, str(risk_review.get("route_action") or "PAPER_SIGNAL")),
            evidence_packet_id=review_id,
            net_pnl_usd=0.0,
            status=str(sizing.get("attempt_status") or "PAPER_INTENT"),
        )
        yield row


def _events_from_terminal_rows(rows: Sequence[TerminalTradeRow] | tuple[TerminalTradeRow, ...], timestamp: str) -> Iterable[AccountLedgerEvent]:
    for row in rows:
        yield AccountLedgerEvent(
            ledger_id=stable_ledger_id("ledger", row.evidence_packet_id, row.simulator_ticket, row.symbol, row.side),
            event_type="paper_order_intent",
            timestamp=timestamp,
            amount_usd=0.0,
            balance_delta_usd=0.0,
            equity_delta_usd=0.0,
            symbol=row.symbol,
            side=row.side,
            lot_size=row.lot_size,
            price=row.open_price,
            sl=row.stop_loss,
            tp=row.take_profit,
            broker_ticket=row.broker_ticket,
            simulator_ticket=row.simulator_ticket,
            strategy_id=row.strategy_id,
            ai_action=row.ai_action,
            evidence_packet_id=row.evidence_packet_id,
            note="Paper order intent only; no broker order was placed.",
            external_money_movement=False,
        )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _validate_events(events: Iterable[AccountLedgerEvent]) -> None:
    for event in events:
        if event.event_type not in ALL_EVENT_TYPES:
            raise ValueError(f"unsupported account ledger event_type {event.event_type!r}")
        if event.external_money_movement:
            raise ValueError("paper/demo account ledger events must not claim external money movement")
        if event.event_type in CREDIT_EVENT_TYPES and event.balance_delta_usd < 0:
            raise ValueError(f"credit event {event.event_type!r} cannot have negative balance_delta_usd")
        if event.event_type in DEBIT_EVENT_TYPES and event.balance_delta_usd > 0:
            raise ValueError(f"debit event {event.event_type!r} cannot have positive balance_delta_usd")
        if event.event_type in NEUTRAL_EVENT_TYPES and abs(event.balance_delta_usd) > 1e-9:
            raise ValueError(f"neutral event {event.event_type!r} cannot change balance")


def assert_account_ledger_boundary(state: AccountLedgerState) -> None:
    """Reject any account ledger that advertises unauthorized live/payment power."""

    if state.live_money_authorized or state.payment_movement_authorized:
        raise ValueError("paper/demo account ledger must not authorize live money or payment movement")
    active_statuses = {
        state.live_trading_status,
        state.broker_accept_status,
        state.auto_deposit_status,
        state.debit_card_bank_movement_status,
        state.payout_automation_status,
    }
    if AUTHORIZED in active_statuses:
        raise ValueError("account ledger cannot report AUTHORIZED real-money capability in paper/demo mode")
    if state.trading_edge_status != OPEN:
        raise ValueError("account ledger must preserve trading edge status OPEN")
