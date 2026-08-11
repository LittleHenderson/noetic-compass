from fastapi import APIRouter, Query

from cas_forex.movement_stream import MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS
from cas_forex.movement_stream import build_movement_source_truth_snapshot

from ..route_cache import cache_first_payload
from ..data import movement_stream

router = APIRouter()


@router.get("/snapshot")
async def get_movement_snapshot(use_provider: bool = Query(default=True)):
    """Returns paper/demo account + market movement telemetry snapshot.

    Provider/MT5 market snapshots are requested by default. Set
    ``use_provider=false`` only when a deterministic simulator-only snapshot is
    needed. The route remains paper/demo telemetry only and falls back to
    clearly marked paper-route static simulation per symbol when a provider is
    unavailable.
    """
    return cache_first_payload(
        f"movement_snapshot:{bool(use_provider)}",
        builder=lambda: movement_stream(use_provider_quotes=use_provider),
        fallback=lambda: _movement_snapshot_warming(use_provider=use_provider),
        ttl_seconds=10.0,
    )


def _movement_snapshot_warming(*, use_provider: bool = True):
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
    payload = {
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
        "market_data_provider_requested": bool(use_provider),
        "market_data_provider": "warming" if use_provider else "none",
        "provider_snapshot_symbols": [],
        "provider_usable_symbols": [],
        "static_fallback_symbols": [],
        "mt5_fallback_symbols": [],
        "provider_stale_symbols": [],
        "provider_freshness_max_age_seconds": MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS,
        "snapshot_age_seconds_by_symbol": {},
        "snapshot_source_by_symbol": {},
        "provider_errors": {},
        "price_source_status": "CACHE_WARMING",
        "static_simulation_active": False,
        "price_source_label": "WARMING",
        "price_source_summary": "Movement snapshot is warming; source truth is not ready yet.",
        "price_source_warning": None,
        "position_feed_title": "Simulator Proof Rows",
        "position_feed_count_label": "Simulator rows",
        "position_feed_label": "SIM PROOF",
        "position_feed_detail": "Movement snapshot is warming; source truth for paper/demo proof rows is not ready yet.",
        "broker_ticket_position_count": 0,
        "static_position_count": 0,
        "static_quote_count": 0,
    }
    payload["movement_source_truth"] = build_movement_source_truth_snapshot(
        payload,
        telemetry_source="none",
        telemetry_stale=True,
        telemetry_last_update_iso=None,
        movement_stream_present=False,
    )
    return payload
