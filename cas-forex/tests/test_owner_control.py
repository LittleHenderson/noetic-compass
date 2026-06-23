from cas_forex.owner_control import (
    MAX_OWNER_AUTO_TRADES,
    OwnerControlMode,
    OwnerPromotionVerdict,
    PromotionThresholds,
    StrategyPromotionCandidate,
    candidate_from_tally_bucket,
    count_condition_lab_simulator_wins,
    review_owner_promotion,
)


def _candidate(**overrides):
    data = {
        "lead_id": "range_scalper_filtered_fx_d1",
        "strategy_setting": "range_scalper_24_120",
        "source": "cas-sdg+walk-forward+paper",
        "simulator_wins": 14,
        "walk_forward_windows": 12,
        "positive_routed_window_rate": 0.75,
        "mean_return_pct": 0.9,
        "max_drawdown_pct": 2.8,
        "trades": 44,
        "paper_days": 30,
        "paper_passed": True,
        "evidence_refs": ["evidence_runs/example.json"],
        "condition_contexts": ["normal", "range", "D1", "EUR/USD"],
    }
    data.update(overrides)
    return StrategyPromotionCandidate(**data)


def test_owner_can_authorize_limited_paper_after_thresholds_pass():
    decision = review_owner_promotion(
        _candidate(),
        owner_mode=OwnerControlMode.LIMITED_PAPER,
        max_paper_trades=3,
    )

    assert decision.verdict == OwnerPromotionVerdict.LIMITED_PAPER_AUTHORIZED
    assert decision.max_paper_trades_authorized == 3
    assert decision.can_place_live_trades is False
    assert decision.can_transfer_money is False


def test_owner_can_authorize_ai_full_auto_paper_with_fifteen_trade_ceiling():
    decision = review_owner_promotion(
        _candidate(),
        owner_mode=OwnerControlMode.AI_FULL_AUTO_PAPER,
        max_paper_trades=99,
    )

    assert decision.verdict == OwnerPromotionVerdict.AI_FULL_AUTO_PAPER_AUTHORIZED
    assert decision.max_paper_trades_authorized == MAX_OWNER_AUTO_TRADES
    assert decision.notification_required is False
    assert decision.can_place_live_trades is False
    assert decision.can_transfer_money is False
    assert any("AI_FULL_AUTO_PAPER" in reason for reason in decision.reasons)


def test_owner_can_keep_passing_candidate_notify_only():
    decision = review_owner_promotion(_candidate(), owner_mode=OwnerControlMode.NOTIFY_ONLY)

    assert decision.verdict == OwnerPromotionVerdict.NOTIFY
    assert "NOTIFY_ONLY" in decision.reasons[0]
    assert decision.notification_required is True


def test_live_auto_is_blocked_even_after_thresholds_pass():
    decision = review_owner_promotion(_candidate(), owner_mode=OwnerControlMode.LIVE_AUTO)

    assert decision.verdict == OwnerPromotionVerdict.LIVE_BLOCKED_NOT_LICENSED
    assert decision.can_place_live_trades is False
    assert decision.can_transfer_money is False
    assert any("NOT LICENSED" in reason for reason in decision.reasons)


def test_ai_full_auto_live_request_is_blocked_even_after_thresholds_pass():
    decision = review_owner_promotion(_candidate(), owner_mode=OwnerControlMode.AI_FULL_AUTO_LIVE_REQUESTED)

    assert decision.verdict == OwnerPromotionVerdict.LIVE_BLOCKED_NOT_LICENSED
    assert decision.can_place_live_trades is False
    assert decision.can_transfer_money is False
    assert any("NOT LICENSED" in reason for reason in decision.reasons)


def test_under_threshold_candidate_only_notifies_blockers():
    decision = review_owner_promotion(
        _candidate(
            simulator_wins=2,
            positive_routed_window_rate=0.4,
            paper_days=0,
            paper_passed=False,
        ),
        owner_mode=OwnerControlMode.PAPER_AUTO,
    )

    assert decision.verdict == OwnerPromotionVerdict.NOTIFY
    assert decision.max_paper_trades_authorized == 0
    assert any("simulator_wins" in reason for reason in decision.reasons)
    assert any("paper_passed is false" in reason for reason in decision.reasons)


def test_candidate_from_tally_bucket_can_feed_owner_control():
    bucket = {
        "axes": {
            "symbol": "EUR/USD",
            "timeframe": "D1",
            "test_event_context": "normal",
            "setting": "range_scalper_24_120",
        },
        "routed_windows": 12,
        "positive_window_rate": 0.75,
        "mean_return_pct": 0.9,
        "max_drawdown_pct": 2.8,
        "trades": 44,
    }
    candidate = candidate_from_tally_bucket(
        bucket,
        lead_id="range_scalper_filtered_fx_d1",
        source="condition_tally",
        simulator_wins=14,
        paper_days=30,
        paper_passed=True,
        evidence_refs=["evidence_runs/example.json"],
    )

    assert candidate.strategy_setting == "range_scalper_24_120"
    assert candidate.condition_contexts == ["EUR/USD", "D1", "normal"]
    assert candidate.walk_forward_windows == 12


def test_thresholds_can_require_more_wins_for_survival_risk_goal():
    strict = PromotionThresholds(
        min_simulator_wins=25,
        min_walk_forward_windows=20,
        min_positive_routed_window_rate=0.8,
        min_mean_return_pct=1.0,
        max_drawdown_pct=3.0,
        min_trades=50,
        min_paper_days=45,
    )
    decision = review_owner_promotion(
        _candidate(),
        thresholds=strict,
        owner_mode=OwnerControlMode.LIMITED_PAPER,
    )

    assert decision.verdict == OwnerPromotionVerdict.NOTIFY
    assert len(decision.reasons) >= 4


def test_count_condition_lab_simulator_wins_filters_by_setting_and_gaps():
    cells = [
        {
            "setting": "range_scalper_24_120",
            "is_gap": False,
            "mean_return_pct": 1.1,
            "mean_max_dd_pct": 2.0,
            "mean_trades": 4,
        },
        {
            "setting": "range_scalper_24_120",
            "is_gap": True,
            "mean_return_pct": 9.0,
            "mean_max_dd_pct": 1.0,
            "mean_trades": 8,
        },
        {
            "setting": "tsmom_252_500_2_8",
            "is_gap": False,
            "mean_return_pct": 1.5,
            "mean_max_dd_pct": 3.0,
            "mean_trades": 5,
        },
    ]

    assert count_condition_lab_simulator_wins(cells, setting="range_scalper_24_120") == 1
    assert count_condition_lab_simulator_wins(cells, require_non_gap=False) == 3
