from fastapi import APIRouter, Query

from ..route_cache import cache_first_payload
from ..data import movement_stream

router = APIRouter()


@router.get("/snapshot")
async def get_movement_snapshot(use_provider: bool = Query(default=False)):
    """Returns paper/demo account + market movement telemetry snapshot.

    Set ``use_provider=true`` to request configured-provider market snapshots.
    The route remains paper/demo telemetry only and falls back to deterministic
    paper-route prices per symbol when a provider is unavailable.
    """
    return cache_first_payload(
        f"movement_snapshot:{bool(use_provider)}",
        builder=lambda: movement_stream(use_provider_quotes=use_provider),
        fallback=_movement_snapshot_warming,
        ttl_seconds=10.0,
    )


def _movement_snapshot_warming():
    account = {
        "timestamp": "",
        "balance_usd": 0.0,
        "equity_usd": 0.0,
        "realized_pnl_usd": 0.0,
        "floating_pnl_usd": 0.0,
        "swap_usd": 0.0,
        "commission_usd": 0.0,
        "broker_fees_usd": 0.0,
        "margin_used_usd": 0.0,
        "free_margin_usd": 0.0,
        "drawdown_usd": 0.0,
        "drawdown_pct": 0.0,
        "deposit_usd": 0.0,
        "withdrawals_usd": 0.0,
        "payouts_usd": 0.0,
        "open_position_count": 0,
        "source": "CACHE_WARMING",
    }
    return {
        "report_kind": "cas_forex_movement_stream",
        "stream_id": "WARMING",
        "mode": "PAPER",
        "timestamp": "",
        "symbols": [],
        "account": account,
        "quotes": [],
        "positions": [],
        "account_streams": [],
        "market_streams": [],
        "evidence_refs": [],
        "claim_boundary": (
            "Movement stream cache warming is paper/demo telemetry only. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, payouts, "
            "or bank/card movement."
        ),
        "trading_edge_status": "OPEN",
        "live_trading_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "auto_deposit_status": "NOT LICENSED",
        "debit_card_bank_movement_status": "NOT LICENSED",
        "payout_automation_status": "NOT LICENSED",
        "live_money_authorized": False,
        "payment_movement_authorized": False,
        "notes": ["Movement stream cache is warming."],
    }
