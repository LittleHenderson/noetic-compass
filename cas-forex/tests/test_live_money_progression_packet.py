"""Live-money progression packet coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import live_money as route_module
from cas_forex.live_money_progression_packet import (
    STATUS_BLOCKED,
    STATUS_READY_FOR_OWNER_REVIEW,
    build_live_money_progression_packet,
)


def _runtime(*, live: bool = False, broker_accept: bool = False, payout: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_runtime_gates",
        "all_real_money_authorized": live and broker_accept and payout,
        "summary": "test runtime gates",
        "decisions": {
            "live_trading": {
                "capability": "live_trading",
                "authorized": live,
                "status": "AUTHORIZED" if live else "CURRENTLY NOT LICENSED",
                "missing_requirements": [] if live else ["owner_enable_live_trading flag is ON"],
                "next_action": "" if live else "Owner must authorize live trading.",
            },
            "broker_accept": {
                "capability": "broker_accept",
                "authorized": broker_accept,
                "status": "AUTHORIZED" if broker_accept else "CURRENTLY NOT LICENSED",
                "missing_requirements": [] if broker_accept else ["owner_enable_broker_accept flag is ON"],
                "next_action": "" if broker_accept else "Owner must authorize broker ACCEPT.",
            },
            "payout_automation": {
                "capability": "payout_automation",
                "authorized": payout,
                "status": "AUTHORIZED" if payout else "CURRENTLY NOT LICENSED",
                "missing_requirements": [] if payout else ["owner_enable_payout_automation flag is ON"],
                "next_action": "" if payout else "Owner must authorize payout automation.",
            },
        },
    }


def _broker_truth(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_broker_truth_recovery_packet",
        "status": "BROKER_TRUTH_RECOVERY_CLEAR" if clear else "BROKER_TRUTH_RECOVERY_BLOCKED",
        "broker_truth_clear_for_live_recovery": clear,
        "blockers": [] if clear else [{"blocker_id": "mt5_live_account_visible"}],
        "monitor_summary": {"mt5_is_demo": not clear},
        "next_action": "" if clear else "Connect the owner-approved live MT5 account.",
    }


def _live_recovery(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_live_recovery_review",
        "recovery_status": "CLEAR" if clear else "OPEN",
        "recovery_clear_for_live": clear,
        "requires_recovery_review": not clear,
        "missing_requirements": [] if clear else ["live_account_visible"],
        "next_action": "" if clear else "Clear live recovery.",
    }


def _pilot(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_pilot_promotion",
        "status": "WASTE_PILOT_READY" if clear else "WASTE_PILOT_BLOCKED",
        "ready_for_pilot_sequence": clear,
        "symbol": "NAS100",
        "direction": "LONG",
        "lots": 0.01,
        "entry_pair_count": 40,
        "missing_requirements": [] if clear else ["pilot_policy_accept_capacity"],
        "next_action": "" if clear else "Owner ACCEPT the small live pilot policy.",
    }


def _direction_review(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_direction_review_packet",
        "status": "WASTE_DIRECTION_EDGE_CONFIRMED" if clear else "WASTE_DIRECTION_EDGE_BLOCKED",
        "direction_edge_confirmed": clear,
        "direction_summary": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": "LONG",
            "opposite_direction": "SHORT",
            "chosen_score": 0.72,
            "opposite_score": 0.18,
            "score_margin": 0.54,
            "entry_pair_count": 40,
        },
        "edge_gate_summary": {
            "status": "PASS" if clear else "NO_TRADE_NULL_FAILED",
            "has_edge_token": clear,
        },
        "profit_box": {"valid": True, "reward_r": 2.0},
        "blockers": [] if clear else [{"blocker_id": "edge_gate_passed_for_direction"}],
        "next_action": "" if clear else "Keep WASTE in PAPER until the selected direction beats null.",
    }


def _direction_learning(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_direction_learning_ledger",
        "status": "WASTE_DIRECTION_LEARNING_ACTIVE",
        "direction_rows": 5 if clear else 3,
        "confirmed_direction_count": 5 if clear else 0,
        "blocked_direction_count": 0 if clear else 3,
        "direction_counts": {"LONG": 5 if clear else 3},
        "edge_status_counts": {"PASS" if clear else "NO_TRADE_NULL_FAILED": 5 if clear else 3},
        "learning_ready_for_adaptation": clear,
        "profile_recommendation": {
            "status": "PROFILE_DIRECTION_REVIEW_READY" if clear else "INSUFFICIENT_CONFIRMED_EDGE",
            "ready_for_adaptation": clear,
            "recommended_group" if clear else "dominant_observed_group": {
                "symbol": "NAS100",
                "timeframe": "D1",
                "profile": "blend",
                "direction": "LONG",
                "cycles": 5 if clear else 3,
                "confirmed_count": 5 if clear else 0,
            },
        },
        "next_action": "Direction learning test fixture.",
    }


def _outcome_binding(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_direction_outcome_binding",
        "status": "WASTE_DIRECTION_OUTCOME_READY_FOR_PROMOTION_REVIEW" if clear else "WASTE_DIRECTION_OUTCOME_NO_CONFIRMED_EDGE",
        "dry_run": True,
        "read_only": True,
        "paper_only": True,
        "outcome_ready_for_promotion": clear,
        "min_bound_outcomes_for_promotion": 5,
        "confirmed_direction_count": 5 if clear else 0,
        "executed_confirmed_count": 5 if clear else 0,
        "closed_history_count": 5 if clear else 0,
        "bound_outcome_count": 5 if clear else 0,
        "unbound_confirmed_count": 0,
        "bound_outcomes_needed": 0 if clear else 5,
        "profitable_bound_count": 5 if clear else 0,
        "losing_bound_count": 0,
        "net_paper_pnl": 125.0 if clear else 0.0,
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "money_moved": False,
        "next_action": "Outcome binding test fixture.",
    }


def _promotion_rule(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_promotion_rule",
        "status": "WASTE_ADAPTATION_PROMOTION_READY_FOR_OWNER_REVIEW" if clear else "WASTE_ADAPTATION_PROMOTION_COLLECTING",
        "dry_run": True,
        "read_only": True,
        "promotion_ready_for_owner_review": clear,
        "learning_ready_for_adaptation": clear,
        "outcome_ready_for_promotion": clear,
        "min_confirmed_for_adaptation": 5,
        "confirmed_direction_count": 5 if clear else 0,
        "confirmed_samples_needed": 0 if clear else 5,
        "bound_outcome_count": 5 if clear else 0,
        "bound_outcomes_needed": 0 if clear else 5,
        "net_paper_pnl": 125.0 if clear else 0.0,
        "blocked_direction_count": 0 if clear else 3,
        "direction_rows": 5 if clear else 3,
        "profile_recommendation_status": "PROFILE_DIRECTION_REVIEW_READY" if clear else "INSUFFICIENT_CONFIRMED_EDGE",
        "dominant_group": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "profile": "blend",
            "direction": "LONG",
        },
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "money_moved": False,
        "next_action": "Promotion rule test fixture.",
    }


def _adaptation_plan(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_plan",
        "status": "WASTE_ADAPTATION_PLAN_READY_FOR_OWNER_REVIEW" if clear else "WASTE_ADAPTATION_PLAN_COLLECTING",
        "dry_run": True,
        "adaptation_ready_for_owner_review": clear,
        "runtime_changed": False,
        "proposal_count": 2,
        "learning_summary": {
            "learning_ready_for_adaptation": clear,
            "confirmed_direction_count": 5 if clear else 0,
            "blocked_direction_count": 0 if clear else 3,
        },
        "latest_direction_summary": {
            "direction": "LONG",
            "edge_status": "PASS" if clear else "NO_TRADE_NULL_FAILED",
        },
        "next_action": "Adaptation plan test fixture.",
    }


def _adaptation_apply_preview(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_apply_preview",
        "status": "WASTE_ADAPTATION_APPLY_PREVIEW_READY_FOR_OWNER_REVIEW" if clear else "WASTE_ADAPTATION_APPLY_PREVIEW_BLOCKED",
        "dry_run": True,
        "preview_ready_for_owner_review": clear,
        "apply_allowed_now": False,
        "apply_endpoint_available": False,
        "runtime_changed": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "simulated_change_count": 2 if clear else 1,
        "blocker_count": 0 if clear else 1,
        "adaptation_plan_summary": {
            "status": "WASTE_ADAPTATION_PLAN_READY_FOR_OWNER_REVIEW" if clear else "WASTE_ADAPTATION_PLAN_COLLECTING",
        },
        "next_action": "Adaptation apply preview test fixture.",
    }


def _adaptation_owner_review(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_owner_review",
        "owner_review_status": "ACCEPT" if clear else "OPEN",
        "owner_review_decision": "ACCEPT_PAPER_ONLY" if clear else "HOLD_PAPER_ONLY",
        "paper_only_review_current": True,
        "paper_only_accept_current": clear,
        "evidence_ready_for_owner_accept": clear,
        "dry_run": True,
        "paper_only": True,
        "apply_allowed_now": False,
        "runtime_changed": False,
        "would_apply_runtime_change": False,
        "would_enable_live_trading": False,
        "money_moved": False,
        "preview_summary": {
            "status": "WASTE_ADAPTATION_APPLY_PREVIEW_READY_FOR_OWNER_REVIEW" if clear else "WASTE_ADAPTATION_APPLY_PREVIEW_BLOCKED",
        },
        "next_action": "Adaptation owner review test fixture.",
    }


def _adaptation_paper_apply(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_paper_apply",
        "status": "WASTE_ADAPTATION_PAPER_APPLY_CURRENT" if clear else "WASTE_ADAPTATION_PAPER_APPLY_BLOCKED",
        "paper_apply_ready": clear,
        "paper_apply_current": clear,
        "paper_apply_recorded": clear,
        "dry_run": True,
        "paper_only": True,
        "runtime_changed": False,
        "would_apply_runtime_change": False,
        "would_enable_live_trading": False,
        "money_moved": False,
        "simulated_change_count": 2 if clear else 0,
        "missing_requirements": [] if clear else ["owner_paper_accept_current"],
        "next_action": "Adaptation paper apply test fixture.",
    }


def _sweep(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_verified_profit_sweep_preview",
        "status": "READY" if clear else "BLOCKED",
        "winnings": {
            "claim_status": "SWEEPABLE" if clear else "DEMO_NOT_SWEEPABLE",
            "sweepable_winnings_usd": 5000.0 if clear else 0.0,
        },
        "sweep_amount_usd": 1200.0 if clear else 0.0,
        "payout_gate": {"authorized": clear, "status": "AUTHORIZED" if clear else "CURRENTLY NOT LICENSED"},
        "reason": "" if clear else "Demo profit is not real sweepable money.",
    }


def _payout_recovery(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_payout_recovery",
        "has_pending_recovery": not clear,
        "pending_count": 0 if clear else 1,
        "latest_attempt": None,
        "next_action": "" if clear else "Resolve pending payout attempts.",
    }


def _readiness(*, clear: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_live_readiness",
        "overall_status": "READY_FOR_LIVE_EXECUTION" if clear else "NOT_READY_FOR_LIVE",
        "live_money_authorized": clear,
        "payment_movement_authorized": clear,
        "checks_open": 0 if clear else 3,
        "checks_mismatch": 0,
        "checks_currently_not_licensed": 0 if clear else 2,
        "next_actions": [] if clear else ["Clear live readiness."],
    }


def _packet(*, clear: bool = False) -> dict:
    return build_live_money_progression_packet(
        runtime_gates=_runtime(live=clear, broker_accept=clear, payout=clear),
        broker_truth_packet=_broker_truth(clear=clear),
        live_recovery_report=_live_recovery(clear=clear),
        waste_pilot_promotion=_pilot(clear=clear),
        waste_direction_review=_direction_review(clear=clear),
        waste_direction_learning=_direction_learning(clear=clear),
        waste_direction_outcome_binding=_outcome_binding(clear=clear),
        waste_adaptation_promotion_rule=_promotion_rule(clear=clear),
        waste_adaptation_plan=_adaptation_plan(clear=clear),
        waste_adaptation_apply_preview=_adaptation_apply_preview(clear=clear),
        waste_adaptation_owner_review=_adaptation_owner_review(clear=clear),
        waste_adaptation_paper_apply=_adaptation_paper_apply(clear=clear),
        sweep_preview=_sweep(clear=clear),
        payout_recovery_status=_payout_recovery(clear=clear),
        live_readiness_report=_readiness(clear=clear),
    )


def test_live_money_progression_packet_blocks_demo_and_dirty_live_path():
    packet = _packet(clear=False)

    assert packet["report_kind"] == "cas_forex_live_money_progression_packet"
    assert packet["status"] == STATUS_BLOCKED
    assert packet["live_dispatch_clear"] is False
    assert packet["waste_pilot_clear"] is False
    assert packet["verified_payout_clear"] is False
    assert packet["broker_touched"] is False
    assert packet["live_order_attempted"] is False
    assert packet["attempt_finalized"] is False
    assert packet["edge_token_minted"] is False
    assert packet["owner_accept_created"] is False
    assert packet["money_moved"] is False
    blocker_ids = {blocker["blocker_id"] for blocker in packet["blockers"]}
    assert "runtime_live_trading_authorized" in blocker_ids
    assert "broker_truth_clear_for_live_recovery" in blocker_ids
    assert "waste_direction_edge_confirmed" in blocker_ids
    assert "verified_profit_sweep_ready" in blocker_ids


def test_live_money_progression_packet_clears_only_when_all_sources_clear():
    packet = _packet(clear=True)

    assert packet["status"] == STATUS_READY_FOR_OWNER_REVIEW
    assert packet["live_dispatch_clear"] is True
    assert packet["waste_pilot_clear"] is True
    assert packet["verified_payout_clear"] is True
    assert packet["full_progression_clear"] is True
    assert packet["blockers"] == []
    assert packet["active_waste_intent"]["direction"] == "LONG"
    assert packet["source_summaries"]["waste_direction_learning"]["learning_ready_for_adaptation"] is True
    assert packet["source_summaries"]["waste_direction_outcome_binding"]["outcome_ready_for_promotion"] is True
    assert packet["source_summaries"]["waste_direction_outcome_binding"]["money_moved"] is False
    assert packet["source_summaries"]["waste_adaptation_promotion_rule"]["promotion_ready_for_owner_review"] is True
    assert packet["source_summaries"]["waste_adaptation_promotion_rule"]["outcome_ready_for_promotion"] is True
    assert packet["source_summaries"]["waste_adaptation_promotion_rule"]["money_moved"] is False
    assert packet["source_summaries"]["waste_adaptation_plan"]["dry_run"] is True
    assert packet["source_summaries"]["waste_adaptation_plan"]["runtime_changed"] is False
    assert packet["source_summaries"]["waste_adaptation_apply_preview"]["dry_run"] is True
    assert packet["source_summaries"]["waste_adaptation_apply_preview"]["apply_allowed_now"] is False
    assert packet["source_summaries"]["waste_adaptation_apply_preview"]["would_enable_live_trading"] is False
    assert packet["source_summaries"]["waste_adaptation_owner_review"]["paper_only"] is True
    assert packet["source_summaries"]["waste_adaptation_owner_review"]["apply_allowed_now"] is False
    assert packet["source_summaries"]["waste_adaptation_owner_review"]["would_enable_live_trading"] is False
    assert packet["source_summaries"]["waste_adaptation_paper_apply"]["paper_only"] is True
    assert packet["source_summaries"]["waste_adaptation_paper_apply"]["paper_apply_current"] is True
    assert packet["source_summaries"]["waste_adaptation_paper_apply"]["would_enable_live_trading"] is False
    assert packet["money_moved"] is False


def test_live_money_progression_route(monkeypatch):
    monkeypatch.setattr(route_module, "live_money_progression_packet", lambda: _packet(clear=False))
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-money")
    client = TestClient(app)

    response = client.get("/api/forex/live-money/progression-packet")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_live_money_progression_packet"
    assert body["status"] == STATUS_BLOCKED
    assert body["broker_touched"] is False
    assert body["money_moved"] is False


def test_live_money_progression_route_refresh_invalidates_without_blocking(monkeypatch):
    captured: dict[str, object] = {}

    def fake_invalidate_cache(*keys: str) -> None:
        captured["invalidated"] = keys

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
                "builder_callable": callable(builder),
                "fallback_callable": callable(fallback),
            }
        )
        return _packet(clear=False)

    monkeypatch.setattr(route_module, "invalidate_cache", fake_invalidate_cache)
    monkeypatch.setattr(route_module, "cache_first_payload", fake_cache_first_payload)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-money")
    client = TestClient(app)

    response = client.get("/api/forex/live-money/progression-packet?refresh=true")

    assert response.status_code == 200
    assert captured["invalidated"] == ("live_money_progression_packet",)
    assert captured["key"] == "live_money_progression_packet"
    assert captured["block_on_cold"] is False
    assert captured["builder_callable"] is True
    assert captured["fallback_callable"] is True


def test_live_money_progression_fast_route_prefers_cached_full_packet(monkeypatch):
    captured: dict[str, object] = {}

    def fake_cached_payload_snapshot(key, *, ttl_seconds):
        captured["snapshot_key"] = key
        captured["ttl_seconds"] = ttl_seconds
        return {
            **_packet(clear=False),
            "cache_status": "fresh",
            "cache_built_at_epoch": 123.0,
        }

    monkeypatch.setattr(route_module, "cached_payload_snapshot", fake_cached_payload_snapshot)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-money")
    client = TestClient(app)

    response = client.get("/api/forex/live-money/progression-packet/fast")

    assert response.status_code == 200
    body = response.json()
    assert captured["snapshot_key"] == "live_money_progression_packet"
    assert body["fast_path"] == "cached_full_progression_packet"
    assert body["status"] == STATUS_BLOCKED
    assert body["cache_status"] == "fresh"


def test_live_money_progression_fast_route_uses_fast_cache_and_starts_full_refresh(monkeypatch):
    captured: dict[str, object] = {}

    def fake_cached_payload_snapshot(key, *, ttl_seconds):
        captured.setdefault("snapshot_keys", []).append(key)
        return None

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
                "builder_callable": callable(builder),
            }
        )
        return _packet(clear=False)

    def fake_start_cache_refresh(key, builder):
        captured["refresh_key"] = key
        captured["refresh_builder_callable"] = callable(builder)
        return True

    monkeypatch.setattr(route_module, "cached_payload_snapshot", fake_cached_payload_snapshot)
    monkeypatch.setattr(route_module, "cache_first_payload", fake_cache_first_payload)
    monkeypatch.setattr(route_module, "start_cache_refresh", fake_start_cache_refresh)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-money")
    client = TestClient(app)

    response = client.get("/api/forex/live-money/progression-packet/fast")

    assert response.status_code == 200
    body = response.json()
    assert captured["key"] == "live_money_progression_packet_fast"
    assert captured["block_on_cold"] is False
    assert captured["builder_callable"] is True
    assert captured["refresh_key"] == "live_money_progression_packet"
    assert captured["refresh_builder_callable"] is True
    assert body["fast_path"] == "fast_summary"
    assert body["status"] == STATUS_BLOCKED
