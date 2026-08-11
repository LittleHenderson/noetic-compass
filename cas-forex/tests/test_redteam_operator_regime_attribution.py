from __future__ import annotations

from scripts.redteam_operator_regime_attribution import build_report


def test_regime_attribution_redteam_is_no_touch_and_passes():
    report = build_report()

    assert report["status"] == "PASS_NO_TOUCH_REGIME_ATTRIBUTION"
    assert all(report["invariant_checks"].values())
    assert report["mixed_regime_scenario"]["outcome_ready_for_promotion"] is False
    assert report["unknown_regime_scenario"]["outcome_ready_for_promotion"] is False
    assert report["independently_ready_regime_scenario"][
        "outcome_ready_for_promotion"
    ] is True
    assert report["broker_touched"] is False
    assert report["order_send_called"] is False
    assert report["position_modified"] is False
    assert report["money_moved"] is False
