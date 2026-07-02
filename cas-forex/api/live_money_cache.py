"""Shared invalidation for live-money gate/progression read models."""

from __future__ import annotations

from .route_cache import invalidate_cache


LIVE_MONEY_GATE_CACHE_KEYS = (
    "live_money_progression_packet",
    "live_money_progression_packet_fast",
    "live_enable_authorization_report",
    "live_enable_state_report",
    "settings_authority_boundary",
    "settings_runtime_gates",
    "verified_profit_sweep_state",
    "verified_profit_sweep_policy",
    "verified_profit_sweep_payout_recovery",
    "live_readiness:False",
    "live_readiness:True",
    "live_recovery_status",
    "live_order_dry_run_review",
    "compound_add_order_dry_run_review",
    "waste_entry_dispatch_handoff",
    "waste_entry_pilot_promotion",
    "compound_add_dispatch_handoff",
    "account_ledger:default",
    "movement_snapshot:False",
    "movement_snapshot:True",
    "account_reconciliation:False",
    "account_reconciliation:True",
)


def invalidate_live_money_gate_caches(*extra_keys: str) -> None:
    """Refresh owner-visible gate/progression packets after a gate write."""

    invalidate_cache(*(LIVE_MONEY_GATE_CACHE_KEYS + tuple(extra_keys)))
    try:
        from cas_forex.live_enable_control import invalidate_live_enable_report_cache

        invalidate_live_enable_report_cache()
    except Exception:
        pass
