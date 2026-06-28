from cas_forex.account_ledger import build_account_ledger_from_paper_review
from cas_forex.movement_stream import assert_movement_stream_boundary, build_movement_stream_state


def _risk_review():
    return {
        "plan_id": "plan-1",
        "lead_id": "lead-1",
        "strategy_setting": "tsmom_126_250_2_10",
        "date": "2026-06-23",
        "review_id": "review-1",
        "account_equity": 5000.0,
        "route_action": "ROUTE_PAPER_SIGNAL",
        "total_planned_risk_usd": 25.30,
        "sizing": [
            {
                "symbol": "US30",
                "direction": "LONG",
                "entry_price": 51745.87,
                "stop_loss": 50485.56,
                "take_profit": 58047.44,
                "sized_lots": 0.01,
                "proposal_id": "proposal-us30",
                "attempt_status": "PAPER_ATTEMPT_ALLOWED",
            }
        ],
    }


def test_movement_stream_tracks_account_and_market_movement_from_ledger():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    state = build_movement_stream_state(
        ledger,
        timestamp="2026-06-23T12:00:00Z",
        quote_overrides={"US30": 51845.87},
    )

    assert state.mode == "PAPER_DEMO_REALTIME_SCAFFOLD"
    assert state.symbols == ("US30",)
    assert state.account.balance_usd == 5000.0
    assert state.account.floating_pnl_usd == 1.0
    assert state.account.equity_usd == 5001.0
    assert state.account.margin_used_usd > 0
    assert state.account.free_margin_usd == state.account.equity_usd - state.account.margin_used_usd
    assert state.quotes[0].symbol == "US30"
    assert state.quotes[0].bid < state.quotes[0].ask
    assert state.quotes[0].synthetic_candle["close"] == 51845.87
    assert state.positions[0].floating_pnl_units == 100.0
    assert state.positions[0].distance_to_sl_units > 0
    assert state.positions[0].distance_to_tp_units > 0
    assert "balance" in state.account_streams
    assert "swap" in state.account_streams
    assert "commission" in state.account_streams
    assert "broker_fees" in state.account_streams
    assert "open_position_count" in state.account_streams
    assert "bid" in state.market_streams
    assert "floating_pnl" in state.market_streams
    assert "margin_estimate" in state.market_streams
    assert "session" in state.market_streams
    assert state.live_money_authorized is False
    assert state.payment_movement_authorized is False
    assert_movement_stream_boundary(state)


def test_movement_stream_preserves_not_licensed_boundary():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    state = build_movement_stream_state(ledger, timestamp="2026-06-23T12:00:00Z")

    assert state.trading_edge_status == "OPEN"
    assert state.live_trading_status == "CURRENTLY NOT LICENSED"
    assert state.broker_accept_status == "CURRENTLY NOT LICENSED"
    assert state.auto_deposit_status == "CURRENTLY NOT LICENSED"
    assert state.debit_card_bank_movement_status == "CURRENTLY NOT LICENSED"
    assert state.payout_automation_status == "CURRENTLY NOT LICENSED"
    assert "do not place live orders" in state.claim_boundary
    assert_movement_stream_boundary(state)

from datetime import datetime, timezone
from cas_forex.schemas.market import MarketSnapshot


def test_movement_stream_uses_provider_snapshot_when_supplied_without_authority_change():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    snapshot = MarketSnapshot(
        symbol="US30",
        timestamp=datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc),
        bid=51844.87,
        ask=51846.87,
        spread=2.0,
        high=51900.0,
        low=51700.0,
        close=51845.87,
        timeframe="M1",
        session="NEW_YORK",
        is_market_open=True,
    )

    state = build_movement_stream_state(
        ledger,
        timestamp="2026-06-23T12:00:00Z",
        market_snapshots={"US30": snapshot},
    )

    assert state.positions[0].current_price == 51845.87
    assert state.positions[0].floating_pnl_usd == 1.0
    assert state.quotes[0].source == "provider_snapshot:MarketSnapshot"
    assert state.quotes[0].session == "NEW_YORK"
    assert state.quotes[0].is_market_open is True
    assert state.quotes[0].synthetic_candle["close"] == 51845.87
    assert state.live_money_authorized is False
    assert state.payment_movement_authorized is False
    assert_movement_stream_boundary(state)
