from fastapi import APIRouter, Query

from ..data import live_readiness
from ..route_cache import cache_first_payload

router = APIRouter()


@router.get("/live")
async def get_live_readiness(sync_to_broker: bool = Query(default=False)):
    """Returns the plain-English live-operability checklist."""
    return cache_first_payload(
        f"live_readiness:{bool(sync_to_broker)}",
        builder=lambda: live_readiness(sync_to_broker=sync_to_broker),
        fallback=_live_readiness_warming,
        ttl_seconds=60.0,
        block_on_cold=bool(sync_to_broker),
    )


def _live_readiness_warming():
    return {
        "report_kind": "cas_forex_live_readiness",
        "mode": "LIVE_OPERABILITY_CHECKLIST",
        "overall_status": "NOT_READY_FOR_LIVE",
        "readiness_status": "WARMING",
        "plain_english_summary": "Live-readiness evidence is warming; no live authority is granted.",
        "checks_total": 0,
        "checks_passed": 0,
        "checks_open": 0,
        "checks_mismatch": 0,
        "checks_unverifiable": 0,
        "checks_currently_not_licensed": 0,
        "live_money_authorized": False,
        "payment_movement_authorized": False,
        "checks": [],
        "blocking_checks": [],
        "next_actions": ["Live-readiness cache is warming."],
        "claim_boundary": (
            "Live-readiness cache warming is observational only. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, "
            "bank/card movement, payouts, or LICENSED status."
        ),
    }
