"""HTTP routes for CAS Forex live-money progression status."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ..data import live_money_progression_packet
from ..route_cache import cache_first_payload, cached_payload_snapshot, invalidate_cache, start_cache_refresh
from cas_forex.live_money_progression_packet import build_live_money_progression_packet

router = APIRouter()


@router.get("/progression-packet")
async def get_progression_packet(refresh: bool = Query(default=False)) -> dict[str, Any]:
    """Return the read-only live-money progression packet."""
    if refresh:
        invalidate_cache("live_money_progression_packet")
    return cache_first_payload(
        "live_money_progression_packet",
        builder=live_money_progression_packet,
        fallback=_live_money_progression_warming,
        ttl_seconds=60.0,
        block_on_cold=False,
    )


@router.get("/progression-packet/fast")
async def get_progression_packet_fast() -> dict[str, Any]:
    """Return the cockpit-fast live-money progression summary."""
    cached_full = cached_payload_snapshot("live_money_progression_packet", ttl_seconds=60.0)
    if cached_full:
        packet = dict(cached_full)
        packet["fast_path"] = "cached_full_progression_packet"
        return packet

    packet = cache_first_payload(
        "live_money_progression_packet_fast",
        builder=_build_fast_progression_packet,
        fallback=_live_money_progression_fast_warming,
        ttl_seconds=15.0,
        block_on_cold=False,
    )
    start_cache_refresh("live_money_progression_packet", live_money_progression_packet)
    packet["fast_path"] = "fast_summary"
    return packet


def _build_fast_progression_packet() -> dict[str, Any]:
    return build_live_money_progression_packet(
        runtime_gates=_runtime_gates_fast(),
        broker_truth_packet=_broker_truth_fast(),
        live_recovery_report=_live_recovery_fast(),
        waste_pilot_promotion=_waste_pilot_fast(),
        waste_direction_review=_waste_direction_fast(),
        waste_direction_learning=_fast_source_unavailable("cas_forex_waste_direction_learning_ledger"),
        waste_direction_outcome_binding=_fast_source_unavailable("cas_forex_waste_direction_outcome_binding"),
        waste_adaptation_promotion_rule=_fast_source_unavailable("cas_forex_waste_adaptation_promotion_rule"),
        waste_adaptation_plan=_fast_source_unavailable("cas_forex_waste_adaptation_plan"),
        waste_adaptation_apply_preview=_fast_source_unavailable("cas_forex_waste_adaptation_apply_preview"),
        waste_adaptation_owner_review=_fast_source_unavailable("cas_forex_waste_adaptation_owner_review"),
        waste_adaptation_paper_apply=_fast_source_unavailable("cas_forex_waste_adaptation_paper_apply"),
        sweep_preview=_verified_profit_sweep_fast(),
        payout_recovery_status=_payout_recovery_fast(),
        live_readiness_report=_live_readiness_fast(),
    )


def _runtime_gates_fast() -> dict[str, Any]:
    try:
        from ..data import runtime_gates_report

        return runtime_gates_report()
    except Exception as exc:
        return _source_unavailable("cas_forex_runtime_gates", exc)


def _broker_truth_fast() -> dict[str, Any]:
    try:
        from cas_forex.broker_truth_recovery_packet import build_broker_truth_recovery_packet

        return build_broker_truth_recovery_packet()
    except Exception as exc:
        return _source_unavailable("cas_forex_broker_truth_recovery_packet", exc)


def _live_recovery_fast() -> dict[str, Any]:
    try:
        from cas_forex.live_recovery import build_live_recovery_report

        return build_live_recovery_report()
    except Exception as exc:
        return _source_unavailable("cas_forex_live_recovery_review", exc)


def _waste_pilot_fast() -> dict[str, Any]:
    try:
        from cas_forex.live_order_dry_run import DEFAULT_AUDIT_PATH, LiveOrderDryRunAuditLog
        from cas_forex.waste_pilot_promotion import build_waste_pilot_promotion_status

        latest = LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH).latest()
        return build_waste_pilot_promotion_status(dry_run_audit=latest or {})
    except Exception as exc:
        return _source_unavailable("cas_forex_waste_pilot_promotion", exc)


def _waste_direction_fast() -> dict[str, Any]:
    try:
        from cas_forex.waste_direction_review_packet import build_waste_direction_review_packet

        return build_waste_direction_review_packet()
    except Exception as exc:
        return _source_unavailable("cas_forex_waste_direction_review_packet", exc)


def _verified_profit_sweep_fast() -> dict[str, Any]:
    try:
        from ..data import verified_profit_sweep_preview_status

        return verified_profit_sweep_preview_status()
    except Exception as exc:
        return _source_unavailable("cas_forex_verified_profit_sweep_preview", exc)


def _payout_recovery_fast() -> dict[str, Any]:
    try:
        from cas_forex.payout_recovery import build_payout_recovery_status

        return build_payout_recovery_status()
    except Exception as exc:
        return _source_unavailable("cas_forex_payout_recovery", exc)


def _live_readiness_fast() -> dict[str, Any]:
    cached = cached_payload_snapshot("live_readiness:False", ttl_seconds=60.0)
    if cached:
        return cached
    return {
        "report_kind": "cas_forex_live_readiness",
        "overall_status": "NOT_READY_FOR_LIVE",
        "readiness_status": "FAST_SUMMARY_CACHE_MISSING",
        "live_money_authorized": False,
        "payment_movement_authorized": False,
        "checks_open": 1,
        "checks_mismatch": 0,
        "checks_currently_not_licensed": 1,
        "next_actions": ["Wait for the live-readiness cache to warm."],
        "claim_boundary": (
            "Fast live-readiness fallback is observational and fail-closed. It "
            "does not authorize live trading, broker ACCEPT, deposits, "
            "withdrawals, bank/card movement, payouts, or LICENSED status."
        ),
    }


def _source_unavailable(report_kind: str, exc: Exception) -> dict[str, Any]:
    packet = _fast_source_unavailable(report_kind)
    packet["error"] = f"{type(exc).__name__}: {exc}"
    return packet


def _fast_source_unavailable(report_kind: str) -> dict[str, Any]:
    return {
        "report_kind": report_kind,
        "status": "FAST_SUMMARY_NOT_LOADED",
        "next_action": "Open the full live-money packet for deep evidence details.",
        "claim_boundary": (
            "Fast live-money source placeholder is observational and fail-closed. "
            "It does not authorize live trading, broker ACCEPT, deposits, "
            "withdrawals, bank/card movement, payouts, or LICENSED status."
        ),
    }


def _live_money_progression_fast_warming() -> dict[str, Any]:
    packet = _live_money_progression_warming()
    packet["fast_path"] = "warming"
    packet["next_action"] = "Wait for the fast live-money progression summary to warm."
    return packet


def _live_money_progression_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_live_money_progression_packet",
        "status": "WARMING",
        "full_progression_clear": False,
        "live_dispatch_clear": False,
        "waste_pilot_clear": False,
        "verified_payout_clear": False,
        "blocker_count": 1,
        "blockers": [
            {
                "plane": "route-cache",
                "status": "WARMING",
                "reason": "Live-money progression cache is warming.",
            }
        ],
        "next_action": "Wait for the live-money progression cache to warm.",
    }
