from types import SimpleNamespace

from cas_forex.daily_loss_guard import evaluate_daily_realized_loss


def _account(realized_today):
    return {
        "realized_today_usd": realized_today,
        "account_growth_reconciliation": {
            "reconciled": realized_today is not None,
            "event_hash": "growth-proof-1" if realized_today is not None else None,
        },
    }


def test_zero_daily_loss_cap_disables_entry_block_when_truth_is_unavailable():
    report = evaluate_daily_realized_loss(
        _account(None),
        control_values={"daily_loss_cap_usd": 0.0},
    )

    assert report["status"] == "DISABLED"
    assert report["block_new_exposure"] is False


def test_daily_realized_loss_cap_blocks_at_boundary_but_allows_management():
    report = evaluate_daily_realized_loss(
        _account(-50.13),
        control_values={"daily_loss_cap_usd": 50.0},
    )

    assert report["status"] == "DAILY_REALIZED_LOSS_CAP_REACHED"
    assert report["block_new_exposure"] is True
    assert report["remaining_loss_budget_usd"] == 0.0
    assert report["position_management_allowed"] is True
    assert report["take_profit_and_stop_management_allowed"] is True


def test_active_daily_loss_cap_fails_closed_without_reconciled_realized_truth():
    report = evaluate_daily_realized_loss(
        _account(None),
        control_values={"daily_loss_cap_usd": 50.0},
    )

    assert report["status"] == "DAILY_REALIZED_LOSS_TRUTH_UNAVAILABLE"
    assert report["block_new_exposure"] is True


def test_daily_loss_cap_allows_entry_inside_remaining_budget():
    report = evaluate_daily_realized_loss(
        _account(-30.0),
        config=SimpleNamespace(daily_loss_cap_usd=999.0),
        control_values={"daily_loss_cap_usd": 50.0},
    )

    assert report["status"] == "WITHIN_DAILY_REALIZED_LOSS_CAP"
    assert report["block_new_exposure"] is False
    assert report["remaining_loss_budget_usd"] == 20.0
    assert report["cap_source"] == "supplied_control_values"


def test_active_daily_loss_cap_fails_closed_for_previous_utc_day_snapshot():
    account = _account(-50.0)
    account["account_growth_reconciliation"].update(
        {
            "period_utc_day": "2026-07-11",
            "current_utc_day": "2026-07-12",
            "period_current": False,
        }
    )

    report = evaluate_daily_realized_loss(
        account,
        control_values={"daily_loss_cap_usd": 50.0},
    )

    assert report["status"] == "DAILY_REALIZED_LOSS_UTC_PERIOD_STALE"
    assert report["realized_today_usd"] is None
    assert report["block_new_exposure"] is True
