from fastapi import APIRouter, Query

from ..route_cache import cache_first_payload
from ..data import account_ledger, apply_broker_synced_risk_review, broker_synced_risk_preview

router = APIRouter()


@router.get("/ledger")
async def get_account_ledger(initial_investment: float | None = Query(default=None, gt=0)):
    """Returns owner-selectable paper/demo account ledger state.

    ``initial_investment`` previews any positive owner-selected paper/demo seed.
    It does not deposit, withdraw, place live orders, or move external money.
    """
    cache_key = "account_ledger:default" if initial_investment is None else f"account_ledger:{float(initial_investment):.2f}"
    return cache_first_payload(
        cache_key,
        builder=lambda: account_ledger(initial_investment_usd=initial_investment),
        fallback=lambda: _account_ledger_warming(initial_investment),
        ttl_seconds=10.0,
    )


def _account_ledger_warming(initial_investment: float | None = None):
    selected = float(initial_investment or 0.0)
    summary = {
        "mode": "PAPER",
        "initial_investment_usd": selected,
        "owner_selected_initial_investment_usd": selected,
        "risk_review_account_equity_usd": 0.0,
        "requires_new_risk_review_for_selected_investment": bool(initial_investment),
        "deposit_usd": 0.0,
        "withdrawals_usd": 0.0,
        "payouts_usd": 0.0,
        "realized_pnl_usd": 0.0,
        "floating_pnl_usd": 0.0,
        "swap_usd": 0.0,
        "commission_usd": 0.0,
        "broker_fees_usd": 0.0,
        "balance_usd": 0.0,
        "equity_usd": 0.0,
        "margin_used_usd": 0.0,
        "free_margin_usd": 0.0,
        "planned_risk_usd": 0.0,
        "planned_risk_pct_of_selected_equity": 0.0,
        "drawdown_usd": 0.0,
        "drawdown_pct": 0.0,
        "event_count": 0,
        "open_position_count": 0,
        "order_count": 0,
        "deal_count": 0,
        "currency": "USD",
    }
    return {
        "report_kind": "cas_forex_account_ledger",
        "plan_id": "WARMING",
        "lead_id": "WARMING",
        "strategy_setting": "WARMING",
        "as_of_date": "",
        "mode": "PAPER",
        "summary": summary,
        "cashflow_events": [],
        "positions": [],
        "orders": [],
        "deals": [],
        "supported_history_tabs": ["positions", "orders", "deals"],
        "supported_time_filters": [],
        "evidence_refs": [],
        "claim_boundary": (
            "Account ledger cache warming is paper/demo telemetry only. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, payouts, "
            "or bank/card movement."
        ),
        "trading_edge_status": "OPEN",
        "live_trading_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "auto_deposit_status": "NOT LICENSED",
        "debit_card_bank_movement_status": "NOT LICENSED",
        "payout_automation_status": "NOT LICENSED",
        "deployment_status": "OPEN",
        "live_money_authorized": False,
        "payment_movement_authorized": False,
        "notes": ["Account ledger cache is warming."],
    }


@router.get("/broker-sync-risk-preview")
async def get_broker_synced_risk_preview():
    """Returns paper risk sizing rerun from the verified broker demo balance.

    This is preview-only. It does not append the paper-risk evidence chain,
    place orders, create broker ACCEPT, or move money.
    """
    return broker_synced_risk_preview()


@router.post("/apply-broker-sync-risk-review")
async def post_apply_broker_synced_risk_review(confirm_apply: bool = Query(default=False)):
    """Append broker-synced paper risk sizing after explicit owner confirmation.

    This mutates only the local paper-risk evidence chain. It does not place
    orders, create broker ACCEPT, deposit, withdraw, or move external money.
    """
    return apply_broker_synced_risk_review(confirm_apply=confirm_apply)
