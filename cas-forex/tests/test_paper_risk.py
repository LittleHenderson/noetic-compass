import pytest

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.paper_risk import (
    append_paper_risk_review,
    paper_risk_store_path,
    review_paper_risk_budget,
    summarize_paper_risk_reviews,
)


def _latest_route_decision():
    return {
        "decision_id": "index-tsmom-126-d1-paper-proof-2026-06-22-paper-decision",
        "plan_id": "index-tsmom-126-d1-paper-proof",
        "lead_id": "index_tsmom_126_d1",
        "strategy_setting": "tsmom_126_250_2_10",
        "date": "2026-06-22",
        "timeframe": "D1",
        "route_action": "ROUTE_PAPER_SIGNAL",
        "event_context": "normal",
        "symbol_decisions": [
            {
                "symbol": "US30",
                "action": "ROUTE_PAPER_SIGNAL",
                "direction": "LONG",
                "confidence": 0.4612,
                "proposal": {
                    "proposal_id": "paper-US30",
                    "symbol": "US30",
                    "direction": "LONG",
                    "entry_price": 51745.87,
                    "stop_loss": 50485.56,
                    "take_profit": 58047.44,
                    "confidence": 0.4612,
                },
            },
            {
                "symbol": "NAS100",
                "action": "ROUTE_PAPER_SIGNAL",
                "direction": "LONG",
                "confidence": 0.7539,
                "proposal": {
                    "proposal_id": "paper-NAS100",
                    "symbol": "NAS100",
                    "direction": "LONG",
                    "entry_price": 30241.62,
                    "stop_loss": 28971.74,
                    "take_profit": 36591.0,
                    "confidence": 0.7539,
                },
            },
        ],
    }


def test_paper_risk_sizes_index_attempts_under_budget():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_paper_risk_budget(
        plan,
        _latest_route_decision(),
        account_equity=5_000,
        max_risk_per_trade_pct=0.5,
        daily_risk_budget_pct=1.0,
    )

    assert review.risk_status == "PAPER_ATTEMPTS_ALLOWED"
    assert review.proposed_attempts == 2
    assert review.allowed_attempts == 2
    assert review.total_planned_risk_usd <= 50.0
    assert review.total_planned_risk_pct <= 1.0
    assert {item.symbol: item.sized_lots for item in review.sizing} == {
        "US30": 0.01,
        "NAS100": 0.01,
    }
    assert all(item.planned_risk_usd <= 25.0 for item in review.sizing)


def test_paper_risk_attempt_cap_suppresses_extra_candidates():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_paper_risk_budget(
        plan,
        _latest_route_decision(),
        account_equity=5_000,
        max_risk_per_trade_pct=0.5,
        daily_risk_budget_pct=1.0,
        max_paper_attempts=1,
    )

    assert review.risk_status == "PARTIAL_PAPER_ATTEMPTS_ALLOWED"
    assert review.allowed_attempts == 1
    assert review.suppressed_attempts == 1
    assert [item.attempt_status for item in review.sizing] == [
        "PAPER_ATTEMPT_ALLOWED",
        "SUPPRESSED_ATTEMPT_LIMIT",
    ]


def test_paper_risk_no_trade_has_no_attempt():
    plan = build_index_tsmom_126_paper_proof_plan()
    decision = {
        "decision_id": "d1",
        "date": "2026-06-22",
        "timeframe": "D1",
        "route_action": "NO_TRADE",
        "symbol_decisions": [
            {"symbol": "US30", "action": "NO_TRADE"},
            {"symbol": "NAS100", "action": "NO_TRADE"},
        ],
    }

    review = review_paper_risk_budget(plan, decision, account_equity=5_000)

    assert review.risk_status == "NO_PAPER_ATTEMPT"
    assert review.proposed_attempts == 0
    assert review.allowed_attempts == 0
    assert review.total_planned_risk_usd == 0.0


def test_paper_risk_suppresses_when_budget_cannot_reach_min_lot():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_paper_risk_budget(
        plan,
        _latest_route_decision(),
        account_equity=500,
        max_risk_per_trade_pct=0.1,
        daily_risk_budget_pct=0.1,
    )

    assert review.risk_status == "PAPER_ATTEMPTS_SUPPRESSED"
    assert review.allowed_attempts == 0
    assert {item.attempt_status for item in review.sizing} == {"SUPPRESSED_MIN_LOT_RISK"}


def test_paper_risk_append_chain_and_summary(tmp_path):
    plan = build_index_tsmom_126_paper_proof_plan()
    review = review_paper_risk_budget(plan, _latest_route_decision(), account_equity=5_000)

    append_paper_risk_review(review, tmp_path)
    summary = summarize_paper_risk_reviews(plan, tmp_path)
    store = EvidenceStore(paper_risk_store_path(plan, tmp_path), run_id=f"{plan.plan_id}-paper-risk")

    assert summary["review_count"] == 1
    assert summary["risk_status_counts"] == {"PAPER_ATTEMPTS_ALLOWED": 1}
    assert summary["chain_verified"] is True
    assert store.verify_chain() is True
    assert summary["latest_review"]["broker_accept_status"] == "NOT LICENSED"


def test_paper_risk_refuses_live_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", False)
    plan = build_index_tsmom_126_paper_proof_plan()

    with pytest.raises(PermissionError, match="live_mode=False"):
        review_paper_risk_budget(plan, _latest_route_decision(), account_equity=5_000)
