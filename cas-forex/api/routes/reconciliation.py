from fastapi import APIRouter, Query

from ..route_cache import cache_first_payload
from ..data import account_reconciliation

router = APIRouter()


@router.get("/account")
async def get_account_reconciliation(sync_to_broker: bool = Query(default=False)):
    """Returns the broker/demo account reconciliation report.

    By default this compares the owner/risk-review paper ledger against broker
    evidence. Set ``sync_to_broker=true`` to preview a paper/demo reconciliation
    ledger seeded from the verified broker account snapshot balance; this is
    accounting/reconciliation only and does not authorize live money.
    """
    return cache_first_payload(
        f"account_reconciliation:{bool(sync_to_broker)}",
        builder=lambda: account_reconciliation(sync_to_broker=sync_to_broker),
        fallback=lambda: _account_reconciliation_warming(sync_to_broker),
        ttl_seconds=10.0,
        block_on_cold=bool(sync_to_broker),
    )


def _account_reconciliation_warming(sync_to_broker: bool = False):
    return {
        "report_kind": "cas_forex_account_reconciliation",
        "mode": "BROKER_SYNC_PREVIEW" if sync_to_broker else "PAPER_DEMO_RECONCILIATION",
        "as_of_date": "",
        "plan_id": "WARMING",
        "lead_id": "WARMING",
        "overall_status": "WARMING",
        "checks_total": 0,
        "checks_ok": 0,
        "checks_mismatch": 0,
        "checks_unverifiable": 0,
        "broker_mode": "UNKNOWN",
        "broker_receipt_id": None,
        "broker_receipt_validation_status": None,
        "broker_chain_verified": False,
        "internal_symbols": [],
        "broker_symbols": [],
        "checks": [],
        "blockers": ["ACCOUNT_RECONCILIATION_CACHE_WARMING"],
        "claim_boundary": (
            "Account reconciliation cache warming is observational only. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, payouts, "
            "or bank/card movement."
        ),
        "trading_edge_status": "OPEN",
        "live_trading_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "deployment_status": "OPEN",
        "live_money_authorized": False,
        "payment_movement_authorized": False,
        "sync_to_broker_snapshot": False,
        "broker_snapshot_initial_investment_usd": None,
        "notes": ["Account reconciliation cache is warming."],
    }
