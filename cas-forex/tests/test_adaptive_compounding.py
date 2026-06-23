import pytest

from cas_forex.adaptive_compounding import (
    AdaptiveAction,
    append_adaptive_compounding_review,
    adaptive_compounding_store_path,
    review_adaptive_compounding,
    summarize_adaptive_compounding_reviews,
)
from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan


def _decision(direction="LONG", confidence=0.76):
    return {
        "decision_id": "d1",
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
                "direction": direction,
                "confidence": confidence,
                "proposal": {
                    "proposal_id": "paper-US30",
                    "symbol": "US30",
                    "direction": direction,
                    "entry_price": 100.0,
                    "stop_loss": 90.0 if direction == "LONG" else 110.0,
                    "take_profit": 130.0 if direction == "LONG" else 70.0,
                    "confidence": confidence,
                },
            }
        ],
    }


def _strong_tally():
    return {
        "buckets": [
            {
                "key": "US30-strong",
                "axes": {
                    "symbol": "US30",
                    "timeframe": "D1",
                    "test_event_context": "normal",
                    "route_action": "ROUTE",
                    "setting": "tsmom_126_250_2_10",
                },
                "routed_windows": 5,
                "positive_window_rate": 0.8,
                "active_window_rate": 1.0,
                "mean_return_pct": 1.4,
                "max_drawdown_pct": 3.0,
            }
        ]
    }


def _winning_position(current_price=108.0):
    return {
        "position_id": "p1",
        "symbol": "US30",
        "direction": "LONG",
        "entry_price": 100.0,
        "current_price": current_price,
        "lots": 0.1,
        "stop_loss": 95.0,
        "take_profit": 130.0,
    }


def test_adaptive_compounding_opens_initial_when_no_basket():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_adaptive_compounding(plan, _decision(), condition_tally=_strong_tally())

    assert review.decisions[0].action == AdaptiveAction.OPEN_INITIAL.value
    assert review.decisions[0].stop_loss == 90.0
    assert review.decisions[0].take_profit == 130.0
    assert review.deployment_status == "NOT LICENSED"


def test_adaptive_compounding_adds_to_clear_winner_with_evidence():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_adaptive_compounding(
        plan,
        _decision(),
        active_positions=[_winning_position()],
        condition_tally=_strong_tally(),
    )

    decision = review.decisions[0]
    assert decision.action == AdaptiveAction.ADD_TO_WINNER.value
    assert decision.lot_size == 0.1
    assert decision.stop_loss >= 100.0
    assert decision.evidence_status == "EVIDENCE_SUPPORTS_COMPOUNDING"
    assert review.memory_snapshots[0].snapshot_type == "WINNING_CONDITION"


def test_adaptive_compounding_tightens_stop_when_evidence_is_missing():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_adaptive_compounding(
        plan,
        _decision(),
        active_positions=[_winning_position()],
    )

    decision = review.decisions[0]
    assert decision.action == AdaptiveAction.TIGHTEN_STOP.value
    assert decision.stop_loss >= 100.0
    assert decision.evidence_status == "NO_MATCH"


def test_adaptive_compounding_closes_basket_on_signal_flip():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_adaptive_compounding(
        plan,
        _decision(direction="SHORT"),
        active_positions=[_winning_position()],
        condition_tally=_strong_tally(),
    )

    assert review.decisions[0].action == AdaptiveAction.CLOSE_BASKET.value
    assert "conflicts" in review.decisions[0].reason


def test_adaptive_compounding_partial_profit_threshold():
    plan = build_index_tsmom_126_paper_proof_plan()

    review = review_adaptive_compounding(
        plan,
        _decision(),
        active_positions=[_winning_position(current_price=112.0)],
        condition_tally=_strong_tally(),
    )

    assert review.decisions[0].action == AdaptiveAction.PARTIAL_TAKE_PROFIT.value


def test_adaptive_compounding_append_chain_and_summary(tmp_path):
    plan = build_index_tsmom_126_paper_proof_plan()
    review = review_adaptive_compounding(
        plan,
        _decision(),
        active_positions=[_winning_position()],
        condition_tally=_strong_tally(),
    )

    append_adaptive_compounding_review(review, tmp_path)
    summary = summarize_adaptive_compounding_reviews(plan, tmp_path)
    store = EvidenceStore(adaptive_compounding_store_path(plan, tmp_path), run_id=f"{plan.plan_id}-adaptive-compounding")

    assert summary["review_count"] == 1
    assert summary["action_counts"] == {"ADD_TO_WINNER": 1}
    assert summary["chain_verified"] is True
    assert store.verify_chain() is True
    assert summary["broker_accept_status"] == "NOT LICENSED"


def test_adaptive_compounding_refuses_live_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", False)
    plan = build_index_tsmom_126_paper_proof_plan()

    with pytest.raises(PermissionError, match="live_mode=False"):
        review_adaptive_compounding(plan, _decision())

