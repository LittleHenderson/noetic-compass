"""WASTE adaptation apply-preview coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_adaptation_apply_preview import (
    STATUS_BLOCKED,
    STATUS_READY,
    build_waste_adaptation_apply_preview,
)
from cas_forex.waste_adaptation_plan import build_waste_adaptation_plan


def _authority_snapshot() -> dict:
    return {
        "report_kind": "cas_forex_ai_control_authority",
        "owner_envelope": {
            "monthly_profit_target_usd": 5000.0,
            "daily_profit_floor_usd": 250.0,
            "daily_profit_cap_usd": 3500.0,
            "allowed_symbols": ["NAS100", "US30"],
            "allowed_sessions": ["London", "NewYork"],
            "allow_long": True,
            "allow_short": True,
            "edge_threshold_min": 0.65,
            "edge_threshold_max": 0.95,
            "max_risk_pct_per_trade": 2.0,
            "max_concurrent_trades": 5,
            "max_compound_units": 3,
            "require_fresh_pass_for_entry": True,
            "require_fresh_pass_for_compound": True,
        },
        "control_surface": {
            "values": {
                "edge_threshold": 0.65,
                "max_risk_pct_per_trade": 0.5,
                "max_concurrent_trades": 3,
                "daily_loss_cap_usd": 100.0,
                "max_compound_units": 2,
                "symbols": ["NAS100"],
                "sessions": ["NewYork"],
            },
            "bounds": {
                "edge_threshold": {"min": 0.65, "max": 0.95},
            },
        },
    }


def _runtime() -> dict:
    return {
        "report_kind": "cas_forex_runtime_gates",
        "all_real_money_authorized": False,
        "decisions": {
            "live_trading": {"authorized": False},
            "broker_accept": {"authorized": False},
            "payout_automation": {"authorized": False},
        },
    }


def _learning(*, ready: bool) -> dict:
    group_key = "recommended_group" if ready else "dominant_observed_group"
    return {
        "report_kind": "cas_forex_waste_direction_learning_ledger",
        "status": "WASTE_DIRECTION_LEARNING_ACTIVE",
        "direction_rows": 6,
        "confirmed_direction_count": 5 if ready else 0,
        "blocked_direction_count": 1 if ready else 6,
        "direction_counts": {"LONG": 6},
        "edge_status_counts": {"PASS": 5 if ready else 0, "NO_TRADE_NULL_FAILED": 1 if ready else 6},
        "learning_ready_for_adaptation": ready,
        "profile_recommendation": {
            "status": "PROFILE_DIRECTION_REVIEW_READY" if ready else "INSUFFICIENT_CONFIRMED_EDGE",
            "ready_for_adaptation": ready,
            "min_confirmed_for_adaptation": 5,
            group_key: {
                "symbol": "NAS100",
                "timeframe": "D1",
                "profile": "blend",
                "direction": "LONG",
                "cycles": 6,
                "confirmed_count": 5 if ready else 0,
            },
        },
    }


def _review() -> dict:
    return {
        "report_kind": "cas_forex_waste_direction_review_packet",
        "status": "WASTE_DIRECTION_EDGE_CONFIRMED",
        "direction_edge_confirmed": True,
        "direction_summary": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": "LONG",
            "opposite_direction": "SHORT",
            "chosen_score": 0.74,
            "opposite_score": 0.22,
            "score_margin": 0.52,
        },
        "edge_gate_summary": {
            "status": "PASS",
            "reason": "test pass",
        },
    }


def _promotion(*, ready: bool) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_promotion_rule",
        "status": "WASTE_ADAPTATION_PROMOTION_READY_FOR_OWNER_REVIEW" if ready else "WASTE_ADAPTATION_PROMOTION_COLLECTING",
        "dry_run": True,
        "read_only": True,
        "promotion_ready_for_owner_review": ready,
        "learning_ready_for_adaptation": ready,
        "outcome_ready_for_promotion": ready,
        "min_confirmed_for_adaptation": 5,
        "confirmed_direction_count": 5 if ready else 0,
        "confirmed_samples_needed": 0 if ready else 5,
        "bound_outcome_count": 5 if ready else 0,
        "bound_outcomes_needed": 0 if ready else 5,
        "net_paper_pnl": 125.0 if ready else 0.0,
        "direction_rows": 6,
        "blocked_direction_count": 1 if ready else 6,
        "dominant_group": {"symbol": "NAS100", "timeframe": "D1", "profile": "blend", "direction": "LONG"},
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "money_moved": False,
    }


def _plan(*, ready: bool) -> dict:
    return build_waste_adaptation_plan(
        direction_learning=_learning(ready=ready),
        direction_review=_review(),
        adaptation_promotion_rule=_promotion(ready=ready),
    )


def test_apply_preview_blocks_collecting_plan_without_side_effects():
    preview = build_waste_adaptation_apply_preview(
        adaptation_plan=_plan(ready=False),
        authority_snapshot=_authority_snapshot(),
        runtime_gates=_runtime(),
    )

    assert preview["report_kind"] == "cas_forex_waste_adaptation_apply_preview"
    assert preview["status"] == STATUS_BLOCKED
    assert preview["dry_run"] is True
    assert preview["preview_ready_for_owner_review"] is False
    assert preview["apply_allowed_now"] is False
    assert preview["runtime_changed"] is False
    assert preview["runtime_change_attempted"] is False
    assert preview["would_apply_runtime_change"] is False
    assert preview["would_lower_edge_threshold"] is False
    assert preview["would_enable_live_trading"] is False
    assert preview["would_raise_risk"] is False
    assert preview["owner_accept_created"] is False
    assert preview["broker_touched"] is False
    assert preview["live_order_attempted"] is False
    assert preview["edge_token_minted"] is False
    assert preview["money_moved"] is False
    blocker_ids = {blocker["blocker_id"] for blocker in preview["blockers"]}
    assert "adaptation_ready_for_owner_review" in blocker_ids


def test_apply_preview_ready_still_does_not_apply_runtime_or_owner_accept():
    preview = build_waste_adaptation_apply_preview(
        adaptation_plan=_plan(ready=True),
        authority_snapshot=_authority_snapshot(),
        runtime_gates=_runtime(),
    )

    assert preview["status"] == STATUS_READY
    assert preview["preview_ready_for_owner_review"] is True
    assert preview["apply_allowed_now"] is False
    assert preview["apply_endpoint_available"] is False
    assert preview["runtime_changed"] is False
    assert preview["owner_accept_created"] is False
    assert preview["money_moved"] is False
    change_types = {change["change_type"] for change in preview["simulated_changes"]}
    assert "PAPER_PROFILE_PRIORITY_HINT" in change_types
    assert "KEEP_GATE_AUTHORITY" in change_types
    assert all(change["would_apply_runtime_change"] is False for change in preview["simulated_changes"])


def test_apply_preview_flags_unsafe_plan_claims_as_blockers():
    plan = _plan(ready=True)
    plan["would_lower_edge_threshold"] = True
    plan["would_enable_live_trading"] = True

    preview = build_waste_adaptation_apply_preview(
        adaptation_plan=plan,
        authority_snapshot=_authority_snapshot(),
        runtime_gates=_runtime(),
    )

    assert preview["status"] == STATUS_BLOCKED
    blocker_ids = {blocker["blocker_id"] for blocker in preview["blockers"]}
    assert "edge_threshold_not_lowered" in blocker_ids
    assert "live_trading_not_enabled" in blocker_ids
    assert preview["would_lower_edge_threshold"] is False
    assert preview["would_enable_live_trading"] is False


def test_apply_preview_route(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_adaptation_apply_preview",
        lambda: build_waste_adaptation_apply_preview(
            adaptation_plan=_plan(ready=False),
            authority_snapshot=_authority_snapshot(),
            runtime_gates=_runtime(),
        ),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/adaptation-apply-preview")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_adaptation_apply_preview"
    assert body["dry_run"] is True
    assert body["apply_allowed_now"] is False
    assert body["runtime_changed"] is False
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
