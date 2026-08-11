from __future__ import annotations

import json
from datetime import datetime, timezone

from cas_forex.mt5_account_growth import (
    account_identity_hash,
    build_mt5_account_growth_report,
    refresh_mt5_account_growth_if_due,
)


def _deal(
    *,
    ticket: int,
    when: str,
    deal_type: int,
    profit: float = 0.0,
    commission: float = 0.0,
    swap: float = 0.0,
    fee: float = 0.0,
) -> dict:
    return {
        "ticket": ticket,
        "type": deal_type,
        "time_iso": when,
        "profit": profit,
        "commission": commission,
        "swap": swap,
        "fee": fee,
    }


def _history(*, balance: float, deals: list[dict], closed: list[dict] | None = None) -> dict:
    return {
        "account_mode": "demo",
        "query": {
            "start": "2026-01-01T00:00:00+00:00",
            "end": "2026-07-11T14:00:00+00:00",
            "days_back": 36500,
            "account_mode": "demo",
        },
        "terminal_snapshot": {
            "account": {
                "account_id_hash": account_identity_hash(1000694, "Hugosway-Demo"),
                "server": "Hugosway-Demo",
                "currency": "USD",
                "balance": balance,
                "equity": balance,
            }
        },
        "raw_deals": deals,
        "history_records": list(closed or []),
    }


def test_reconciles_funding_closed_pnl_and_open_entry_commission():
    history = _history(
        balance=99_989.85,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-17T08:17:43+00:00",
                deal_type=2,
                profit=100_000.0,
            ),
            _deal(
                ticket=2,
                when="2026-06-18T10:00:00+00:00",
                deal_type=0,
                commission=-0.05,
            ),
            _deal(
                ticket=3,
                when="2026-06-18T10:05:00+00:00",
                deal_type=1,
                profit=-10.0,
                commission=-0.05,
            ),
            _deal(
                ticket=4,
                when="2026-07-11T12:00:00+00:00",
                deal_type=0,
                commission=-0.05,
            ),
        ],
        closed=[{"profit": -10.10}],
    )

    report = build_mt5_account_growth_report(
        history,
        generated_at=datetime(2026, 7, 11, 13, 0, tzinfo=timezone.utc),
    )

    assert report["status"] == "RECONCILED_CASHFLOW_ADJUSTED_GROWTH"
    assert report["baseline"]["net_external_capital_flow_account_currency"] == 100_000.0
    assert report["realized_growth"]["cashflow_adjusted_all_time_account_currency"] == -10.15
    assert report["realized_growth"]["closed_position_net_pnl_account_currency"] == -10.10
    assert report["realized_growth"][
        "trade_effect_not_in_closed_position_rows_account_currency"
    ] == -0.05
    assert report["realized_growth"]["today_account_currency"] == -0.05
    assert report["realized_growth"]["month_account_currency"] == -0.05
    assert report["components"]["trade_commission_account_currency"] == -0.15
    assert report["reconciliation"]["ledger_ties_to_current_balance"] is True
    assert report["reconciliation"]["growth_components_tie"] is True
    assert report["period"] == {
        "timezone": "UTC",
        "utc_day": "2026-07-11",
        "utc_month": "2026-07",
        "day_start": "2026-07-11T00:00:00+00:00",
        "month_start": "2026-07-01T00:00:00+00:00",
    }
    assert report["history"]["latest_deal_fingerprint"]


def test_deposit_and_withdrawal_are_capital_flow_not_profit():
    history = _history(
        balance=8_100.0,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-01T00:00:00+00:00",
                deal_type=2,
                profit=10_000.0,
            ),
            _deal(
                ticket=2,
                when="2026-06-02T00:00:00+00:00",
                deal_type=2,
                profit=-2_000.0,
            ),
            _deal(
                ticket=3,
                when="2026-06-03T00:00:00+00:00",
                deal_type=1,
                profit=100.0,
            ),
        ],
        closed=[{"profit": 100.0}],
    )

    report = build_mt5_account_growth_report(history)

    assert report["baseline"]["balance_deposits_account_currency"] == 10_000.0
    assert report["baseline"]["balance_withdrawals_account_currency"] == 2_000.0
    assert report["baseline"]["net_external_capital_flow_account_currency"] == 8_000.0
    assert report["realized_growth"]["cashflow_adjusted_all_time_account_currency"] == 100.0
    assert report["realized_growth"]["growth_pct_on_net_external_capital"] == 1.25


def test_unknown_deal_type_blocks_reconciled_baseline():
    history = _history(
        balance=10_001.0,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-01T00:00:00+00:00",
                deal_type=2,
                profit=10_000.0,
            ),
            _deal(
                ticket=2,
                when="2026-06-02T00:00:00+00:00",
                deal_type=99,
                profit=1.0,
            ),
        ],
    )

    report = build_mt5_account_growth_report(history)

    assert report["status"] == "PARTIAL_ACCOUNT_HISTORY_UNKNOWN_DEAL_TYPES"
    assert report["baseline"]["status"] == "UNAVAILABLE_UNKNOWN_MT5_DEAL_TYPES"
    assert report["reconciliation"]["unknown_deal_types"] == ["99"]


def test_balance_residual_blocks_reconciled_baseline():
    history = _history(
        balance=9_999.0,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-01T00:00:00+00:00",
                deal_type=2,
                profit=10_000.0,
            )
        ],
    )

    report = build_mt5_account_growth_report(history)

    assert report["status"] == "ACCOUNT_LEDGER_DOES_NOT_TIE_TO_BALANCE"
    assert report["reconciliation"]["balance_residual_account_currency"] == -1.0
    assert report["period_realized_status"] == "UNAVAILABLE_NO_PERIOD_RECONCILIATION"


def test_refresh_reuses_recent_snapshot_only_when_account_and_balance_match(tmp_path):
    history = _history(
        balance=10_100.0,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-01T00:00:00+00:00",
                deal_type=2,
                profit=10_000.0,
            ),
            _deal(
                ticket=2,
                when="2026-06-02T00:00:00+00:00",
                deal_type=1,
                profit=100.0,
            ),
        ],
    )
    state_path = tmp_path / "growth.json"
    existing = build_mt5_account_growth_report(history)
    state_path.write_text(json.dumps(existing), encoding="utf-8")
    calls = []

    def should_not_run(**kwargs):
        calls.append(kwargs)
        raise AssertionError("full history should stay cached")

    cached = refresh_mt5_account_growth_if_due(
        mt5_module=object(),
        mt5_path=None,
        current_history_report=history,
        state_path=state_path,
        history_builder=should_not_run,
    )

    assert cached["refresh_status"] == "CACHED_ACCOUNT_BALANCE_UNCHANGED"
    assert calls == []

    changed = _history(balance=10_101.0, deals=history["raw_deals"])

    refresh_calls = []

    def refresh(**kwargs):
        refresh_calls.append(kwargs)
        return changed

    refreshed = refresh_mt5_account_growth_if_due(
        mt5_module=object(),
        mt5_path=None,
        current_history_report=changed,
        state_path=state_path,
        history_builder=refresh,
    )

    assert refreshed["refresh_status"] == "FULL_HISTORY_REFRESHED"
    assert refreshed["status"] == "ACCOUNT_LEDGER_DOES_NOT_TIE_TO_BALANCE"
    assert refresh_calls[0]["days_back"] < 36_500
    assert refreshed["refresh_history_window_status"] == (
        "BOUNDED_FROM_RECONCILED_FIRST_EVENT"
    )
    assert refreshed["refresh_effective_history_days"] == refresh_calls[0]["days_back"]


def test_refresh_forces_full_history_at_utc_day_rollover_with_unchanged_balance(
    tmp_path,
    monkeypatch,
):
    day_one = datetime(2026, 7, 11, 23, 59, tzinfo=timezone.utc)
    day_two = datetime(2026, 7, 12, 0, 1, tzinfo=timezone.utc)
    history = _history(
        balance=9_950.0,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-01T00:00:00+00:00",
                deal_type=2,
                profit=10_000.0,
            ),
            _deal(
                ticket=2,
                when="2026-07-11T20:00:00+00:00",
                deal_type=1,
                profit=-50.0,
            ),
        ],
        closed=[{"profit": -50.0}],
    )
    state_path = tmp_path / "growth.json"
    existing = build_mt5_account_growth_report(history, generated_at=day_one)
    assert existing["realized_growth"]["today_account_currency"] == -50.0
    state_path.write_text(json.dumps(existing), encoding="utf-8")
    monkeypatch.setattr("cas_forex.mt5_account_growth.utc_now", lambda: day_two)
    calls = []

    def refresh(**kwargs):
        calls.append(kwargs)
        return history

    refreshed = refresh_mt5_account_growth_if_due(
        mt5_module=object(),
        mt5_path=None,
        current_history_report=history,
        state_path=state_path,
        history_builder=refresh,
    )

    assert len(calls) == 1
    assert refreshed["refresh_status"] == "FULL_HISTORY_REFRESHED"
    assert refreshed["refresh_reason"] == "UTC_DAY_ROLLOVER"
    assert refreshed["period"]["utc_day"] == "2026-07-12"
    assert refreshed["realized_growth"]["today_account_currency"] == 0.0


def test_refresh_detects_new_deals_even_when_balance_returns_to_same_value(
    tmp_path,
    monkeypatch,
):
    observed = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    initial = _history(
        balance=10_000.0,
        deals=[
            _deal(
                ticket=1,
                when="2026-06-01T00:00:00+00:00",
                deal_type=2,
                profit=10_000.0,
            )
        ],
    )
    changed = _history(
        balance=10_000.0,
        deals=[
            *initial["raw_deals"],
            _deal(
                ticket=2,
                when="2026-07-12T11:00:00+00:00",
                deal_type=1,
                profit=-10.0,
            ),
            _deal(
                ticket=3,
                when="2026-07-12T11:01:00+00:00",
                deal_type=2,
                profit=10.0,
            ),
        ],
        closed=[{"profit": -10.0}],
    )
    state_path = tmp_path / "growth.json"
    existing = build_mt5_account_growth_report(initial, generated_at=observed)
    state_path.write_text(json.dumps(existing), encoding="utf-8")
    monkeypatch.setattr("cas_forex.mt5_account_growth.utc_now", lambda: observed)

    refreshed = refresh_mt5_account_growth_if_due(
        mt5_module=object(),
        mt5_path=None,
        current_history_report=changed,
        state_path=state_path,
        history_builder=lambda **_kwargs: changed,
    )

    assert refreshed["refresh_reason"] == "RECENT_DEAL_FINGERPRINT_CHANGED"
    assert refreshed["realized_growth"]["today_account_currency"] == -10.0
    assert refreshed["baseline"]["net_external_capital_flow_account_currency"] == 10_010.0
