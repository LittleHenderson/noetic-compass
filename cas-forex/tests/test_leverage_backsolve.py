from pathlib import Path

import pytest

from cas_forex.leverage_backsolve import (
    AIAutonomyMode,
    AIAutonomyStatus,
    BacksolveVerdict,
    BrokerLeverageProfile,
    EvidenceProjection,
    choose_ai_autonomy_scenario,
    default_broker_profiles,
    evaluate_income_scenario,
    income_scenario_payload,
    required_monthly_return_pct,
    run_income_backsolve,
    write_backsolve_reports,
)


def _projection(
    *,
    base_monthly_income_usd=1_000.0,
    base_max_drawdown_usd=100.0,
) -> EvidenceProjection:
    return EvidenceProjection(
        source_report="fixture-walk-forward.json",
        symbols=("US30", "NAS100"),
        timeframes=("D1",),
        strategy_setting="tsmom_126_250_2_10",
        base_starting_balance=10_000.0,
        base_position_lots=0.05,
        evidence_months=12.0,
        total_windows=6,
        routed_windows=4,
        active_routed_windows=4,
        positive_routed_windows=3,
        positive_routed_window_rate=0.75,
        total_trades=40,
        base_total_profit_usd=12_000.0,
        base_monthly_income_usd=base_monthly_income_usd,
        base_max_drawdown_usd=base_max_drawdown_usd,
        base_max_drawdown_pct=1.0,
        worst_window_return_pct=-1.0,
        worst_window_loss_usd=100.0,
        research_grade="WALK_FORWARD_LEAD",
    )


def test_required_monthly_return_math_for_user_targets():
    assert required_monthly_return_pct(5_000, 5_000) == pytest.approx(100.0)
    assert required_monthly_return_pct(5_000, 12_000) == pytest.approx(240.0)


def test_leverage_changes_margin_not_strategy_edge():
    evidence = _projection()
    p100 = BrokerLeverageProfile(profile_id="p100", broker_name="research", leverage=100)
    p200 = BrokerLeverageProfile(profile_id="p200", broker_name="research", leverage=200)

    s100 = evaluate_income_scenario(
        evidence,
        broker_profile=p100,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=0.05,
        max_concurrent_trades=1,
    )
    s200 = evaluate_income_scenario(
        evidence,
        broker_profile=p200,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=0.05,
        max_concurrent_trades=1,
    )

    assert s100.projected_monthly_income_usd == s200.projected_monthly_income_usd
    assert s100.projected_monthly_return_pct == s200.projected_monthly_return_pct
    assert s200.margin_required_usd < s100.margin_required_usd


def test_target_reached_but_drawdown_above_ten_percent_fails():
    evidence = _projection(base_monthly_income_usd=1_000.0, base_max_drawdown_usd=101.0)
    profile = BrokerLeverageProfile(profile_id="p100", broker_name="research", leverage=100)

    scenario = evaluate_income_scenario(
        evidence,
        broker_profile=profile,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=0.25,
        max_concurrent_trades=1,
        max_loss_cap_pct=10.0,
    )

    assert scenario.target_reached is True
    assert scenario.max_loss_cap_passed is False
    assert scenario.verdict == BacksolveVerdict.TARGET_REACHED_BUT_DRAWDOWN_FAIL


def test_target_reached_but_margin_below_safety_threshold_fails():
    evidence = _projection(base_monthly_income_usd=1_000.0, base_max_drawdown_usd=1.0)
    profile = BrokerLeverageProfile(profile_id="p100", broker_name="research", leverage=100)

    scenario = evaluate_income_scenario(
        evidence,
        broker_profile=profile,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=10.0,
        max_concurrent_trades=4,
        max_loss_cap_pct=1_000.0,
    )

    assert scenario.target_reached is True
    assert scenario.max_loss_cap_passed is True
    assert scenario.margin_passed is False
    assert scenario.verdict == BacksolveVerdict.TARGET_REACHED_BUT_MARGIN_FAIL


def test_user_can_choose_arbitrary_loss_percentage_and_fifteen_trades():
    profile = BrokerLeverageProfile(profile_id="p200", broker_name="research", leverage=200)

    scenario = evaluate_income_scenario(
        _projection(base_monthly_income_usd=500.0, base_max_drawdown_usd=1.0),
        broker_profile=profile,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=0.05,
        max_concurrent_trades=15,
        max_loss_cap_pct=37.25,
    )

    assert scenario.max_concurrent_trades == 15
    assert scenario.max_loss_cap_pct == pytest.approx(37.25)
    assert scenario.verdict == BacksolveVerdict.SURVIVES_USER_LOSS_CAP


def test_more_than_fifteen_concurrent_trades_is_rejected():
    profile = BrokerLeverageProfile(profile_id="p200", broker_name="research", leverage=200)

    with pytest.raises(ValueError, match="cannot exceed 15"):
        evaluate_income_scenario(
            _projection(),
            broker_profile=profile,
            seed_capital=5_000,
            monthly_income_target=5_000,
            lot_size=0.05,
            max_concurrent_trades=16,
        )


def test_ai_full_auto_paper_can_select_viable_scenario():
    profile = BrokerLeverageProfile(profile_id="p200", broker_name="research", leverage=200)
    scenario = evaluate_income_scenario(
        _projection(base_monthly_income_usd=5_000.0, base_max_drawdown_usd=1.0),
        broker_profile=profile,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=0.05,
        max_concurrent_trades=1,
        max_loss_cap_pct=1.0,
    )

    decision = choose_ai_autonomy_scenario([scenario], AIAutonomyMode.AI_FULL_AUTO_PAPER)

    assert decision.status == AIAutonomyStatus.AI_FULL_AUTO_PAPER_SELECTED
    assert decision.selected_scenario_id == scenario.scenario_id
    assert decision.can_choose_risk_cap is True
    assert decision.can_open_paper_trades is True
    assert decision.can_place_live_trades is False


def test_ai_full_auto_live_request_is_recorded_but_blocked():
    decision = choose_ai_autonomy_scenario([], AIAutonomyMode.AI_FULL_AUTO_LIVE_REQUESTED)

    assert decision.status == AIAutonomyStatus.AI_FULL_AUTO_LIVE_BLOCKED_NOT_LICENSED
    assert decision.can_choose_risk_cap is True
    assert decision.can_place_live_trades is False
    assert decision.can_transfer_money is False
    assert "NOT LICENSED" in decision.reason


def test_regulatory_risk_profiles_cannot_create_broker_accept():
    for profile in default_broker_profiles():
        assert profile.regulatory_risk is True
        assert profile.can_create_broker_accept() is False
        assert profile.broker_accept_status == "NOT LICENSED"
        assert profile.broker_accept_verdict == BacksolveVerdict.NOT_LICENSED_LIVE_BLOCKED


def test_scenario_payload_preserves_not_licensed_boundaries():
    profile = default_broker_profiles()[0]
    scenario = evaluate_income_scenario(
        _projection(),
        broker_profile=profile,
        seed_capital=5_000,
        monthly_income_target=5_000,
        lot_size=0.01,
        max_concurrent_trades=1,
    )
    payload = income_scenario_payload(scenario)

    assert payload["deployment_status"] == "NOT LICENSED"
    assert payload["broker_accept_status"] == "NOT LICENSED"
    assert payload["payment_transfer_status"] == "NOT LICENSED"
    assert payload["live_deployment_verdict"] == "NOT_LICENSED_LIVE_BLOCKED"
    assert "NOT LICENSED" in payload["claim_boundary"]


def test_backsolve_runs_against_saved_us30_nas100_walk_forward_evidence(tmp_path):
    root = Path(__file__).resolve().parents[1]
    evidence_path = root / "evidence_runs" / "index_tsmom_h1_d1_go" / "walk-forward-20260622054921-report.json"
    assert evidence_path.exists()

    report = run_income_backsolve(
        evidence_report_path=evidence_path,
        seed_capital=5_000,
        monthly_targets=[5_000, 12_000],
        symbols=["US30", "NAS100"],
        strategies=["tsmom_126_250_2_10", "tsmom_252_500_2_8"],
        timeframes=["D1"],
        concurrent_trade_grid=[1, 15],
        lot_grid=[0.01, 10.0],
        max_loss_cap_pcts=[10.0, 37.25],
        ai_autonomy_mode=AIAutonomyMode.AI_FULL_AUTO_PAPER,
    )
    paths = write_backsolve_reports(report, tmp_path)
    json_text = Path(paths["json"]).read_text(encoding="utf-8")
    md_text = Path(paths["markdown"]).read_text(encoding="utf-8")

    assert report["deployment_status"] == "NOT LICENSED"
    assert report["broker_accept_status"] == "NOT LICENSED"
    assert report["payment_transfer_status"] == "NOT LICENSED"
    assert report["viable_scenario_count"] == 0
    assert report["arguments"]["max_loss_cap_pcts"] == [10.0, 37.25]
    assert report["arguments"]["concurrent_trade_grid"] == [1, 15]
    assert report["ai_autonomy"]["mode"] == "AI_FULL_AUTO_PAPER"
    assert report["ai_autonomy"]["status"] == "AI_NO_VIABLE_SCENARIO"
    assert all(item["conclusion"] == "NO_SCENARIO_SURVIVES_10_PERCENT_CAP_AND_MARGIN" for item in report["target_summaries"])
    assert "NOT LICENSED" in json_text
    assert "NOT LICENSED" in md_text
