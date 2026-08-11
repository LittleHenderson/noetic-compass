from fastapi import APIRouter, Query

from ..route_cache import cache_first_payload
from ..data import (
    account_health,
    account_ledger,
    active_account_truth,
    apply_broker_synced_risk_review,
    broker_synced_risk_preview,
)

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


@router.get("/health")
async def get_account_health(initial_investment: float | None = Query(default=None, gt=0)):
    """Returns decision-grade account health and performance metrics.

    The report is read-only. It does not place orders, authorize live trading,
    or move money.
    """
    cache_key = "account_health:default" if initial_investment is None else f"account_health:{float(initial_investment):.2f}"
    return cache_first_payload(
        cache_key,
        builder=lambda: account_health(initial_investment_usd=initial_investment),
        fallback=lambda: _account_health_warming(initial_investment),
        ttl_seconds=10.0,
    )


@router.get("/active")
def get_active_account_truth():
    """Return the source-ranked account used by owner-facing cockpit surfaces."""

    return active_account_truth()


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
        "movement_stream_id": None,
        "movement_stream_timestamp": None,
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
        "movement_source_truth": {
            "movement_stream_present": False,
            "price_source_status": "WARMING",
            "price_source_label": "WARMING",
            "price_source_summary": "Account ledger cache is warming; movement source truth is not ready yet.",
            "price_source_warning": None,
            "position_feed_label": "WARMING",
            "position_feed_detail": "Account ledger cache is warming; movement source truth for prices and floating P&L is not ready yet.",
            "static_simulation_active": False,
            "open_position_count": 0,
            "broker_ticket_position_count": 0,
            "simulator_position_count": 0,
            "provider_priced_simulator_position_count": 0,
            "static_simulator_position_count": 0,
            "stale_price_position_count": 0,
            "source_label_counts": {},
            "configured_market_data_provider": None,
            "provider_usable_symbols": [],
            "static_fallback_symbols": [],
            "mt5_fallback_symbols": [],
            "provider_stale_symbols": [],
            "provider_freshness_max_age_seconds": None,
            "snapshot_age_seconds_by_symbol": {},
            "provider_error_count": 0,
            "stale_positions": [],
            "static_positions": [],
            "attention_required": False,
            "detail": "Account ledger cache is warming.",
            "local_detail": "Account ledger cache is warming.",
        },
        "notes": ["Account ledger cache is warming."],
    }


def _account_health_warming(initial_investment: float | None = None):
    selected = float(initial_investment or 0.0)
    return {
        "report_kind": "cas_forex_account_health",
        "status": "WARMING",
        "generated_from": {
            "source_report_kind": "cas_forex_account_ledger",
            "mode": "PAPER",
            "as_of_date": "",
            "live_money_authorized": False,
        },
        "blockers": [],
        "account": {
            "mode": "PAPER",
            "currency": "USD",
            "initial_investment_usd": selected,
            "balance_usd": 0.0,
            "equity_usd": 0.0,
            "free_margin_usd": 0.0,
            "margin_used_usd": 0.0,
            "margin_utilization_pct": None,
            "realized_pnl_usd": 0.0,
            "floating_pnl_usd": 0.0,
            "drawdown_usd": 0.0,
            "drawdown_pct": 0.0,
            "return_on_initial_pct": None,
        },
        "daily": {"as_of_date": "", "realized_pnl_usd": 0.0, "realized_trade_event_count": 0},
        "closed_trade_performance": {
            "closed_trade_count": 0,
            "winning_trade_count": 0,
            "losing_trade_count": 0,
            "breakeven_trade_count": 0,
            "win_rate_pct": None,
            "gross_profit_usd": 0.0,
            "gross_loss_usd": 0.0,
            "net_pnl_usd": 0.0,
            "profit_factor": None,
            "profit_factor_state": "NO_CLOSED_TRADES",
            "expectancy_usd": None,
            "average_r_multiple": None,
            "by_symbol": {},
        },
        "open_exposure": {
            "open_position_count": 0,
            "pending_order_count": 0,
            "open_lots": 0.0,
            "unprotected_position_count": 0,
            "protective_order_coverage_pct": 100.0,
            "open_risk_estimate_usd": None,
        },
        "source_health": {
            "movement_stream_present": False,
            "price_source_status": "WARMING",
            "price_source_label": None,
            "price_source_summary": None,
            "price_source_warning": None,
            "position_feed_label": None,
            "position_feed_detail": None,
            "open_position_count": 0,
            "broker_ticket_position_count": 0,
            "simulator_position_count": 0,
            "provider_priced_simulator_position_count": 0,
            "static_simulator_position_count": 0,
            "stale_price_position_count": 0,
            "source_label_counts": {},
            "configured_market_data_provider": None,
            "provider_usable_symbols": [],
            "static_fallback_symbols": [],
            "mt5_fallback_symbols": [],
            "provider_stale_symbols": [],
            "provider_freshness_max_age_seconds": None,
            "snapshot_age_seconds_by_symbol": {},
            "provider_error_count": 0,
            "stale_positions": [],
            "static_positions": [],
            "attention_required": False,
            "detail": "Account health cache is warming.",
            "local_detail": "Account health cache is warming.",
        },
        "data_quality": {"ledger_present": False, "notes": ["Account health cache is warming."]},
        "decision_metrics": {},
        "claim_boundary": (
            "Account health cache warming is read-only telemetry. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, "
            "payouts, or bank/card movement."
        ),
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
