from datetime import date

from cas_forex.config import config
from cas_forex.paper_daily_schedule import (
    evaluate_daily_paper_schedule,
    write_daily_paper_schedule_status,
)
from cas_forex.paper_decision import (
    PaperRouteDecision,
    PaperSymbolDecision,
    append_paper_route_decision,
)
from cas_forex.paper_proof import (
    BROKER_API_VERIFIED,
    append_paper_proof_day,
    build_index_tsmom_126_paper_proof_plan,
)
from cas_forex.paper_risk import append_paper_risk_review, review_paper_risk_budget


def _paper_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", False)
    monkeypatch.setattr(config, "paper_trading", True)


def _receipt(plan, day):
    return {
        "receipt_id": f"{plan.plan_id}-{day.isoformat()}-test-receipt",
        "source_attestation": BROKER_API_VERIFIED,
        "broker_mode": "PAPER_MT5",
        "trading_date": day.isoformat(),
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "symbols": plan.symbols,
        "timeframe": plan.timeframe,
        "orders_attempted": 0,
        "orders_paper_executed": 0,
        "open_positions_reconciled": True,
        "live_mode": False,
        "broker_export_sha256": "a" * 64,
        "account_id_hash": "b" * 64,
        "server": "Test-Demo",
        "terminal_name": "Test MT5",
        "provider_receipt_id": f"provider-{day.isoformat()}",
        "order_ids": [],
    }


def _append_complete_day(plan, out_dir, day):
    append_paper_proof_day(
        plan,
        out_dir,
        trading_date=day,
        broker_receipt=_receipt(plan, day),
        allow_api_verified_receipt=True,
    )
    decision = PaperRouteDecision(
        decision_id=f"{plan.plan_id}-{day.isoformat()}-paper-decision",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        date=day.isoformat(),
        timeframe=plan.timeframe,
        route_action="NO_TRADE",
        event_context="normal",
        macro_status="PASS",
        macro_reason="No macro blackout active.",
        symbol_decisions=[
            PaperSymbolDecision(symbol="US30", action="NO_TRADE", reason="fixture"),
            PaperSymbolDecision(symbol="NAS100", action="NO_TRADE", reason="fixture"),
        ],
    )
    append_paper_route_decision(decision, out_dir)
    review = review_paper_risk_budget(
        plan,
        {
            "decision_id": decision.decision_id,
            "date": decision.date,
            "timeframe": decision.timeframe,
            "route_action": decision.route_action,
            "symbol_decisions": [
                {"symbol": "US30", "action": "NO_TRADE"},
                {"symbol": "NAS100", "action": "NO_TRADE"},
            ],
        },
        account_equity=5_000,
    )
    append_paper_risk_review(review, out_dir)


def test_schedule_points_to_next_trading_day_after_complete_day(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    _append_complete_day(plan, tmp_path, date(2026, 6, 22))

    schedule = evaluate_daily_paper_schedule(plan, tmp_path, as_of_date=date(2026, 6, 22))

    assert schedule.next_due_status == "WAIT_NEXT_TRADING_DAY"
    assert schedule.next_due_date == "2026-06-23"
    assert schedule.complete_bundle_days == 1
    assert schedule.ui_bundles_remaining == 4
    assert schedule.missing_tracks_for_next_due == [
        "broker_verified_receipt",
        "paper_route_decision",
        "paper_risk_review",
    ]


def test_schedule_marks_unfinished_weekday_due_today(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    _append_complete_day(plan, tmp_path, date(2026, 6, 22))

    schedule = evaluate_daily_paper_schedule(plan, tmp_path, as_of_date=date(2026, 6, 23))

    assert schedule.next_due_status == "DUE_TODAY"
    assert schedule.next_due_date == "2026-06-23"
    assert "--date 2026-06-23" in schedule.recommended_command


def test_schedule_rolls_weekend_to_monday(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()

    schedule = evaluate_daily_paper_schedule(plan, tmp_path, as_of_date=date(2026, 6, 27))

    assert schedule.next_due_status == "WAIT_NEXT_TRADING_DAY"
    assert schedule.next_due_date == "2026-06-29"


def test_schedule_status_file_written(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    schedule = evaluate_daily_paper_schedule(plan, tmp_path, as_of_date=date(2026, 6, 22))

    path = write_daily_paper_schedule_status(plan, tmp_path, schedule)

    assert path.exists()
    assert path.name.endswith("-daily-schedule-status.json")
