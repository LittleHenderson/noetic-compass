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
        "movement_stream_present": False,
        "movement_price_source_status": None,
        "movement_position_feed_label": None,
        "movement_position_feed_detail": None,
        "movement_source_truth": {
            "movement_stream_present": False,
            "price_source_status": "WARMING",
            "price_source_label": "WARMING",
            "price_source_summary": "Account reconciliation cache is warming; movement source truth is not ready yet.",
            "position_feed_label": "WARMING",
            "position_feed_detail": "Account reconciliation cache is warming; movement source truth for prices and floating P&L is not ready yet.",
            "static_simulation_active": False,
            "open_position_count": 0,
            "broker_ticket_position_count": 0,
            "simulator_position_count": 0,
            "provider_priced_simulator_position_count": 0,
            "static_simulator_position_count": 0,
            "stale_price_position_count": 0,
            "source_label_counts": {},
            "provider_usable_symbols": [],
            "static_fallback_symbols": [],
            "mt5_fallback_symbols": [],
            "provider_stale_symbols": [],
            "provider_error_count": 0,
            "attention_required": False,
            "detail": "Account reconciliation cache is warming.",
            "local_detail": "Account reconciliation cache is warming.",
        },
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
