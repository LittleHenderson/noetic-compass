from datetime import date, timedelta

from cas_forex.config import config
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
from cas_forex.paper_ui_readiness import (
    evaluate_paper_ui_readiness,
    write_paper_ui_readiness_status,
)


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


def _decision(plan, day):
    return PaperRouteDecision(
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
        notes=["Fixture paper decision."],
    )


def _decision_payload(decision):
    return {
        "decision_id": decision.decision_id,
        "plan_id": decision.plan_id,
        "lead_id": decision.lead_id,
        "strategy_setting": decision.strategy_setting,
        "date": decision.date,
        "timeframe": decision.timeframe,
        "route_action": decision.route_action,
        "event_context": decision.event_context,
        "macro_status": decision.macro_status,
        "macro_reason": decision.macro_reason,
        "symbol_decisions": [
            {
                "symbol": item.symbol,
                "action": item.action,
                "reason": item.reason,
                "proposal": item.proposal,
            }
            for item in decision.symbol_decisions
        ],
    }


def _append_complete_day(plan, out_dir, day):
    append_paper_proof_day(
        plan,
        out_dir,
        trading_date=day,
        broker_receipt=_receipt(plan, day),
        allow_api_verified_receipt=True,
    )
    decision = _decision(plan, day)
    append_paper_route_decision(decision, out_dir)
    review = review_paper_risk_budget(plan, _decision_payload(decision), account_equity=5_000)
    append_paper_risk_review(review, out_dir)


def test_ui_readiness_not_ready_with_one_complete_day(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    _append_complete_day(plan, tmp_path, date(2026, 6, 22))

    report = evaluate_paper_ui_readiness(plan, tmp_path, min_daily_bundles_for_ui=5)

    assert report.readiness_status == "NOT_READY_FOR_UI_UX"
    assert report.complete_bundle_days == 1
    assert "complete_bundle_days 1 < required 5" in report.blockers
    assert report.deployment_status == "NOT LICENSED"


def test_ui_readiness_ready_after_minimum_complete_days(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    start = date(2026, 6, 22)
    for offset in range(5):
        _append_complete_day(plan, tmp_path, start + timedelta(days=offset))

    report = evaluate_paper_ui_readiness(plan, tmp_path, min_daily_bundles_for_ui=5)

    assert report.readiness_status == "READY_FOR_PROOF_COCKPIT_UI_UX"
    assert report.complete_bundle_days == 5
    assert report.blockers == []
    assert report.broker_accept_status == "NOT LICENSED"


def test_ui_readiness_status_file_written(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    _append_complete_day(plan, tmp_path, date(2026, 6, 22))
    report = evaluate_paper_ui_readiness(plan, tmp_path, min_daily_bundles_for_ui=5)

    path = write_paper_ui_readiness_status(plan, tmp_path, report)

    assert path.exists()
    assert path.name.endswith("-ui-readiness-status.json")
