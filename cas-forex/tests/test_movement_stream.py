from datetime import datetime, timedelta, timezone

from cas_forex.account_ledger import build_account_ledger_from_paper_review
from cas_forex.movement_stream import (
    MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS,
    assert_movement_stream_boundary,
    build_movement_stream_state,
)
from cas_forex.time_utils import utc_now


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
    assert state.positions[0].price_source == "operator_quote_override"
    assert state.positions[0].price_stale is False
    assert state.positions[0].stale_reason is None
    assert state.positions[0].position_source_label == "PAPER_SIM_PROVIDER_PRICED"
    assert state.positions[0].opened_at is not None
    assert state.positions[0].age_seconds is not None
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
    assert "not an execution surface" in state.claim_boundary
    assert "guarded dispatch/provider paths" in state.claim_boundary
    assert_movement_stream_boundary(state)

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
    assert state.positions[0].price_source == "provider_snapshot:MarketSnapshot"
    assert state.positions[0].price_stale is False
    assert state.quotes[0].source == "provider_snapshot:MarketSnapshot"
    assert state.quotes[0].session == "NEW_YORK"
    assert state.quotes[0].is_market_open is True
    assert state.quotes[0].synthetic_candle["close"] == 51845.87
    assert state.live_money_authorized is False
    assert state.payment_movement_authorized is False
    assert_movement_stream_boundary(state)


def test_movement_stream_preserves_snapshot_source_name_for_mt5_priced_sim_rows():
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
        market_snapshot_sources={"US30": "MT5TerminalMarketDataConnector"},
    )

    assert state.positions[0].price_source == "provider_snapshot:MT5TerminalMarketDataConnector"
    assert state.positions[0].position_source_label == "PAPER_SIM_MT5_PRICED"
    assert state.quotes[0].source == "provider_snapshot:MT5TerminalMarketDataConnector"
    assert_movement_stream_boundary(state)


def test_movement_stream_rejects_closed_provider_snapshot_as_price_authority():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    closed_snapshot = MarketSnapshot(
        symbol="US30",
        timestamp=datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc),
        bid=50000.0,
        ask=50002.0,
        spread=2.0,
        high=50002.0,
        low=50000.0,
        close=50001.0,
        timeframe="M1",
        session="UNKNOWN",
        is_market_open=False,
        synthetic_fallback=True,
    )

    state = build_movement_stream_state(
        ledger,
        timestamp="2026-06-23T12:00:00Z",
        market_snapshots={"US30": closed_snapshot},
    )

    assert state.positions[0].current_price == 51745.87
    assert state.positions[0].floating_pnl_usd == 0.0
    assert state.positions[0].price_source == "paper_route_snapshot:static_simulation"
    assert state.positions[0].price_stale is True
    assert state.positions[0].stale_reason == "Static paper-route snapshot: no usable provider or MT5 quote is pricing this simulator row."
    assert state.positions[0].position_source_label == "PAPER_SIM_STATIC"
    assert state.quotes[0].source == "paper_route_snapshot:static_simulation"
    assert state.quotes[0].stale is True
    assert "Static simulator fallback used for: US30." in state.notes
    assert_movement_stream_boundary(state)


def test_movement_stream_accepts_fresh_closed_market_snapshot_for_observational_repricing():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    closed_market_snapshot = MarketSnapshot(
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
        is_market_open=False,
        synthetic_fallback=False,
    )

    state = build_movement_stream_state(
        ledger,
        timestamp="2026-06-23T12:00:00Z",
        market_snapshots={"US30": closed_market_snapshot},
        market_snapshot_sources={"US30": "MT5TerminalMarketDataConnector"},
    )

    assert state.positions[0].current_price == 51845.87
    assert state.positions[0].floating_pnl_usd == 1.0
    assert state.positions[0].price_source == "provider_snapshot:MT5TerminalMarketDataConnector"
    assert state.positions[0].price_stale is False
    assert state.positions[0].position_source_label == "PAPER_SIM_MT5_PRICED"
    assert state.quotes[0].source == "provider_snapshot:MT5TerminalMarketDataConnector"
    assert state.quotes[0].stale is False
    assert state.quotes[0].is_market_open is False
    assert "Provider-backed current prices used for: US30." in state.notes
    assert_movement_stream_boundary(state)


def test_api_movement_stream_reports_static_fallback_when_provider_closed(monkeypatch):
    import api.data as data_module

    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()

    class ClosedConnector:
        def __init__(self):
            self.last_error = ""

        def fetch_snapshot(self, symbol: str):
            self.last_error = f"symbol {symbol} is not available on the configured OANDA account"
            return MarketSnapshot(
                symbol=symbol,
                timestamp=datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc),
                bid=50000.0,
                ask=50002.0,
                spread=2.0,
                high=50002.0,
                low=50000.0,
                close=50001.0,
                timeframe="M1",
                session="UNKNOWN",
                is_market_open=False,
                synthetic_fallback=True,
            )

    monkeypatch.setattr(data_module, "account_ledger", lambda: ledger)
    monkeypatch.setattr(data_module, "get_connector", lambda: ClosedConnector())
    monkeypatch.setattr(data_module, "MT5TerminalMarketDataConnector", ClosedConnector)

    payload = data_module.movement_stream(use_provider_quotes=True)

    assert payload["market_data_provider_requested"] is True
    assert payload["market_data_provider"] == "ClosedConnector"
    assert payload["provider_snapshot_symbols"] == ["US30"]
    assert payload["provider_usable_symbols"] == []
    assert payload["static_fallback_symbols"] == ["US30"]
    assert payload["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert payload["price_source_label"] == "STATIC SIM"
    assert payload["static_simulation_active"] is True
    assert "Static simulation only" in payload["price_source_summary"]
    assert "Static simulator rows are not being moved by usable provider/MT5 quotes right now" in payload["price_source_warning"]
    assert payload["position_feed_title"] == "Simulator Proof Rows"
    assert payload["position_feed_count_label"] == "Simulator rows"
    assert payload["position_feed_label"] == "SIM PROOF"
    assert "Static simulator fallback is active for 1/1 row(s)" in payload["position_feed_detail"]
    assert payload["broker_ticket_position_count"] == 0
    assert payload["static_position_count"] == 1
    assert payload["static_quote_count"] == 1
    assert isinstance(payload.get("movement_source_truth"), dict)
    assert payload["movement_source_truth"]["movement_stream_present"] is True
    assert payload["movement_source_truth"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert payload["movement_source_truth"]["position_feed_label"] == "SIM PROOF"
    assert payload["movement_source_truth"]["static_quote_count"] == 1
    assert payload["movement_source_truth"]["detail"] == payload["position_feed_detail"]
    assert payload["positions"][0]["price_source"] == "paper_route_snapshot:static_simulation"
    assert payload["positions"][0]["price_stale"] is True
    assert payload["positions"][0]["stale_reason"]
    assert payload["positions"][0]["position_source_label"] == "PAPER_SIM_STATIC"


def test_api_movement_stream_uses_mt5_after_hours_last_price_when_primary_snapshot_is_unusable(monkeypatch):
    import api.data as data_module

    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()

    class ClosedConnector:
        def __init__(self):
            self.last_error = ""

        def fetch_snapshot(self, symbol: str):
            self.last_error = f"symbol {symbol} is not available on the configured OANDA account"
            return MarketSnapshot(
                symbol=symbol,
                timestamp=datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc),
                bid=50000.0,
                ask=50002.0,
                spread=2.0,
                high=50002.0,
                low=50000.0,
                close=50001.0,
                timeframe="M1",
                session="UNKNOWN",
                is_market_open=False,
                synthetic_fallback=True,
            )

    class Mt5FallbackConnector:
        def fetch_snapshot(self, symbol: str):
            return MarketSnapshot(
                symbol=symbol,
                timestamp=utc_now(),
                bid=51844.87,
                ask=51846.87,
                spread=2.0,
                high=51900.0,
                low=51700.0,
                close=51845.87,
                timeframe="M1",
                session="NEW_YORK",
                is_market_open=False,
                synthetic_fallback=False,
            )

    monkeypatch.setattr(data_module, "account_ledger", lambda: ledger)
    monkeypatch.setattr(data_module, "get_connector", lambda: ClosedConnector())
    monkeypatch.setattr(data_module, "MT5TerminalMarketDataConnector", Mt5FallbackConnector)

    payload = data_module.movement_stream(use_provider_quotes=True)

    assert payload["configured_market_data_provider"] == "ClosedConnector"
    assert payload["market_data_provider"] == "ClosedConnector"
    assert payload["provider_snapshot_symbols"] == ["US30"]
    assert payload["provider_usable_symbols"] == ["US30"]
    assert payload["closed_market_symbols"] == ["US30"]
    assert payload["closed_market_quote_count"] == 1
    assert payload["static_fallback_symbols"] == []
    assert payload["unsupported_provider_symbols"] == ["US30"]
    assert payload["mt5_fallback_symbols"] == ["US30"]
    assert payload["snapshot_source_by_symbol"]["US30"] == "Mt5FallbackConnector"
    assert payload["price_source_status"] == "PROVIDER_ACTIVE"
    assert payload["price_source_label"] == "PROVIDER"
    assert payload["static_simulation_active"] is False
    assert "repricing paper/demo rows" in payload["price_source_summary"]
    assert "Configured provider ClosedConnector does not support: US30." in payload["price_source_summary"]
    assert "Fresh closed-market last prices are being used for: US30" in payload["price_source_summary"]
    assert payload["price_source_warning"] is None
    assert payload["position_feed_label"] == "SIM PROOF"
    assert "paper/demo proof rows, not MT5 broker-truth positions" in payload["position_feed_detail"]
    assert "Usable provider or MT5 quotes are repricing current prices and floating P&L." in payload["position_feed_detail"]
    assert "Configured provider ClosedConnector does not support: US30." in payload["position_feed_detail"]
    assert "Market-closed rows: 1/1 are using fresh last-known provider/MT5 prices for US30 until the venue reopens." in payload["position_feed_detail"]
    assert payload["broker_ticket_position_count"] == 0
    assert payload["static_position_count"] == 0
    assert payload["static_quote_count"] == 0
    assert isinstance(payload.get("movement_source_truth"), dict)
    assert payload["movement_source_truth"]["price_source_status"] == "PROVIDER_ACTIVE"
    assert payload["movement_source_truth"]["mt5_fallback_symbols"] == ["US30"]
    assert payload["movement_source_truth"]["closed_market_symbols"] == ["US30"]
    assert payload["movement_source_truth"]["closed_market_quote_count"] == 1
    assert payload["movement_source_truth"]["unsupported_provider_symbols"] == ["US30"]
    assert payload["movement_source_truth"]["provider_priced_simulator_position_count"] == 1
    assert payload["positions"][0]["price_source"] == "provider_snapshot:Mt5FallbackConnector"
    assert payload["positions"][0]["position_source_label"] == "PAPER_SIM_PROVIDER_PRICED"


def test_api_movement_stream_rejects_stale_provider_snapshot(monkeypatch):
    import api.data as data_module

    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    stale_timestamp = utc_now() - timedelta(seconds=MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS + 60)

    class StaleOpenConnector:
        def fetch_snapshot(self, symbol: str):
            return MarketSnapshot(
                symbol=symbol,
                timestamp=stale_timestamp,
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

    class ClosedMt5Connector:
        def fetch_snapshot(self, symbol: str):
            return MarketSnapshot(
                symbol=symbol,
                timestamp=utc_now(),
                bid=50000.0,
                ask=50002.0,
                spread=2.0,
                high=50002.0,
                low=50000.0,
                close=50001.0,
                timeframe="M1",
                session="UNKNOWN",
                is_market_open=False,
                synthetic_fallback=True,
            )

    monkeypatch.setattr(data_module, "account_ledger", lambda: ledger)
    monkeypatch.setattr(data_module, "get_connector", lambda: StaleOpenConnector())
    monkeypatch.setattr(data_module, "MT5TerminalMarketDataConnector", ClosedMt5Connector)

    payload = data_module.movement_stream(use_provider_quotes=True)

    assert payload["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert payload["provider_stale_symbols"] == ["US30"]
    assert payload["provider_freshness_max_age_seconds"] == MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS
    assert payload["snapshot_age_seconds_by_symbol"]["US30"] > MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS
    assert "stale snapshot for movement pricing" in payload["provider_errors"]["US30"]
    assert "synthetic fallback snapshot" in payload["provider_errors"]["US30"]
    assert "Stale provider/MT5 snapshots rejected for: US30" in payload["price_source_summary"]
    assert "Stale provider/MT5 snapshots were rejected for: US30" in payload["position_feed_detail"]
    assert f"(max age {MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS}s)." in payload["position_feed_detail"]
    assert payload["positions"][0]["price_source"] == "paper_route_snapshot:static_simulation"
    assert payload["positions"][0]["price_stale"] is True


def test_movement_route_warming_preserves_provider_request_flag():
    from api.routes.movement import _movement_snapshot_warming

    provider_warming = _movement_snapshot_warming(use_provider=True)
    static_warming = _movement_snapshot_warming(use_provider=False)

    assert provider_warming["market_data_provider_requested"] is True
    assert provider_warming["market_data_provider"] == "warming"
    assert provider_warming["price_source_status"] == "CACHE_WARMING"
    assert provider_warming["price_source_label"] == "WARMING"
    assert provider_warming["static_simulation_active"] is False
    assert provider_warming["position_feed_label"] == "SIM PROOF"
    assert provider_warming["position_feed_detail"] == "Movement snapshot is warming; source truth for paper/demo proof rows is not ready yet."
    assert provider_warming["broker_ticket_position_count"] == 0
    assert provider_warming["static_position_count"] == 0
    assert provider_warming["static_quote_count"] == 0
    assert provider_warming["provider_stale_symbols"] == []
    assert provider_warming["provider_freshness_max_age_seconds"] == MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS
    assert provider_warming["snapshot_age_seconds_by_symbol"] == {}
    assert provider_warming["snapshot_source_by_symbol"] == {}
    assert isinstance(provider_warming.get("movement_source_truth"), dict)
    assert provider_warming["movement_source_truth"]["movement_stream_present"] is False
    assert provider_warming["movement_source_truth"]["telemetry_source"] == "none"
    assert provider_warming["movement_source_truth"]["price_source_status"] == "CACHE_WARMING"
    assert provider_warming["movement_source_truth"]["position_feed_detail"] == provider_warming["position_feed_detail"]
    assert static_warming["market_data_provider_requested"] is False
    assert static_warming["market_data_provider"] == "none"


def test_movement_stream_marks_old_static_simulator_rows_with_age():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    ledger["positions"][0]["timestamp"] = "2026-06-01T00:00:00Z"

    state = build_movement_stream_state(ledger, timestamp="2026-06-23T12:00:00Z")

    position = state.positions[0]
    assert position.price_stale is True
    assert position.position_source_label == "PAPER_SIM_STATIC"
    assert position.opened_at == "2026-06-01T00:00:00Z"
    assert position.age_days == 22.5
    assert "Static paper-route snapshot" in (position.stale_reason or "")


def test_movement_stream_marks_broker_ticket_rows_as_sim_proof_when_static():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    ledger["positions"][0]["broker_ticket"] = "45938644"

    state = build_movement_stream_state(ledger, timestamp="2026-06-23T12:00:00Z")

    position = state.positions[0]
    assert position.broker_ticket == "45938644"
    assert position.price_source == "paper_route_snapshot:static_simulation"
    assert position.price_stale is True
    assert position.position_source_label == "PAPER_SIM_BROKER_TICKET_STATIC"


def test_movement_stream_marks_broker_ticket_rows_as_sim_proof_when_mt5_priced():
    ledger = build_account_ledger_from_paper_review(_risk_review()).to_dict()
    ledger["positions"][0]["broker_ticket"] = "45938644"
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
        market_snapshot_sources={"US30": "MT5TerminalMarketDataConnector"},
    )

    position = state.positions[0]
    assert position.broker_ticket == "45938644"
    assert position.price_source == "provider_snapshot:MT5TerminalMarketDataConnector"
    assert position.price_stale is False
    assert position.position_source_label == "PAPER_SIM_BROKER_TICKET_MT5_PRICED"
