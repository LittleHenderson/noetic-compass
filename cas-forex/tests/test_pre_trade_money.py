from types import SimpleNamespace as NS

from cas_forex.pre_trade_money import (
    build_open_position_stop_risk,
    build_pre_trade_money_estimate,
    summarize_open_position_stop_risk,
)


def test_pre_trade_money_estimate_calculates_risk_margin_and_reward():
    estimate = build_pre_trade_money_estimate(
        symbol="EUR/USD",
        direction="LONG",
        lots=0.1,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
        proposed_intent={"spread_units": 1.2},
        account_snapshot={
            "balance": 1000.0,
            "equity": 1000.0,
            "margin": 0.0,
            "free_margin": 1000.0,
            "leverage": 100,
        },
    )

    assert estimate["status"] == "ESTIMATED"
    assert estimate["symbol"] == "EUR/USD"
    assert estimate["price_unit_name"] == "pip"
    assert estimate["stop_distance_units"] == 100.0
    assert estimate["risk_at_stop_usd"] == 100.0
    assert estimate["risk_at_stop_pct_equity"] == 10.0
    assert estimate["reward_at_take_profit_usd"] == 200.0
    assert estimate["reward_risk_ratio"] == 2.0
    assert estimate["estimated_notional_usd"] == 11000.0
    assert estimate["estimated_margin_required_usd"] == 110.0
    assert estimate["estimated_free_margin_after_usd"] == 890.0
    assert estimate["spread_cost_estimate_usd"] == 1.2
    assert "does not authorize execution" in estimate["claim_boundary"]


def test_pre_trade_money_estimate_marks_market_order_without_entry_as_partial():
    estimate = build_pre_trade_money_estimate(
        symbol="EUR/USD",
        direction="LONG",
        lots=0.1,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1200,
        account_snapshot={"equity": 1000.0},
    )

    assert estimate["status"] == "PARTIAL"
    assert estimate["entry_price"] is None
    assert estimate["risk_at_stop_usd"] is None
    assert any("Market order entry price was not supplied" in item for item in estimate["assumptions"])


def test_pre_trade_money_estimate_reports_unsupported_symbol():
    estimate = build_pre_trade_money_estimate(
        symbol="UNKNOWN",
        direction="LONG",
        lots=0.1,
        price=1.0,
        stop_loss=0.9,
        take_profit=1.2,
    )

    assert estimate["status"] == "UNAVAILABLE"
    assert "Unsupported symbol" in estimate["detail"]


class _BrokerAwareBridge:
    def symbol_info(self, symbol):
        if symbol != "EURUSD":
            return None
        return NS(
            point=0.00001,
            digits=5,
            volume_min=0.01,
            volume_max=10.0,
            volume_step=0.01,
            trade_contract_size=100000.0,
            trade_tick_size=0.00001,
            trade_tick_value=1.0,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbols_get(self, pattern=None):
        return [NS(name="EURUSD")]

    def symbol_info_tick(self, symbol):
        return NS(ask=1.1000, bid=1.0999)

    def account_info(self):
        return NS(leverage=500)

    def order_calc_margin(self, order_type, symbol, volume, price):
        assert symbol == "EURUSD"
        assert volume == 0.1
        return 120.0


def test_pre_trade_money_estimate_prefers_broker_margin_truth_when_available():
    estimate = build_pre_trade_money_estimate(
        symbol="EUR/USD",
        direction="LONG",
        lots=0.1,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1200,
        account_snapshot={
            "balance": 1000.0,
            "equity": 1000.0,
            "margin": 25.0,
            "free_margin": 975.0,
        },
        bridge=_BrokerAwareBridge(),
    )

    assert estimate["status"] == "ESTIMATED"
    assert estimate["entry_price"] == 1.1
    assert estimate["entry_price_source"] == "broker_symbol_tick.ask"
    assert estimate["selected_broker_symbol"] == "EURUSD"
    assert estimate["margin_estimate_source"] == "broker.order_calc_margin"
    assert estimate["estimated_margin_required_usd"] == 120.0
    assert estimate["estimated_margin_after_usd"] == 145.0
    assert estimate["estimated_free_margin_after_usd"] == 855.0
    assert estimate["broker_contract_constraints"]["contract_size"] == 100000.0
    assert estimate["account_leverage"] == 500.0
    assert estimate["account_leverage_source"] == "broker.account_info.leverage"
    assert "Broker symbol metadata via" in estimate["broker_contract_source"]


class _IndexBrokerBridge:
    def symbol_info(self, symbol):
        if symbol != "US30":
            return None
        return NS(
            point=0.01,
            digits=2,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_contract_size=1.0,
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            trade_tick_value_loss=1.0,
            trade_tick_value_profit=1.0,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbols_get(self, pattern=None):
        return [NS(name="US30")]

    def get_account_info(self):
        return {
            "balance": 44_779.12,
            "equity": 44_779.12,
            "margin": 0.0,
            "margin_free": 44_779.12,
            "leverage": 500,
        }


def test_index_stop_risk_uses_broker_tick_economics_and_fresh_account_equity():
    estimate = build_pre_trade_money_estimate(
        symbol="US30",
        direction="SHORT",
        lots=0.01,
        price=52_597.82,
        stop_loss=52_734.75,
        take_profit=52_374.18,
        proposed_intent={"expected_loss_usd": 1.40},
        bridge=_IndexBrokerBridge(),
    )

    assert estimate["unit_value_source"] == "broker.trade_tick_value/trade_tick_size"
    assert estimate["static_unit_value_per_lot_usd"] == 1.0
    assert estimate["broker_unit_value_per_lot_usd"] == 100.0
    assert estimate["geometry_risk_at_stop_usd"] == 136.93
    assert estimate["risk_at_stop_usd"] == 136.93
    assert estimate["risk_at_stop_pct_equity"] == 0.3058
    assert estimate["account_equity_usd"] == 44_779.12
    assert estimate["account_snapshot_source"] == "bridge.get_account_info"
    assert estimate["risk_source"].startswith("conservative_max(")


def test_open_index_position_exposes_broker_valued_cap_breach_without_forced_action():
    risk = build_open_position_stop_risk(
        symbol="US30",
        direction="SHORT",
        lots=0.01,
        open_price=52_597.82,
        current_price=52_650.00,
        stop_loss=52_734.75,
        take_profit=52_374.18,
        bridge=_IndexBrokerBridge(),
        risk_cap_pct=0.1,
    )

    assert risk["status"] == "POSITION_RISK_CAP_BREACH"
    assert risk["risk_at_stop_usd"] == 136.93
    assert risk["risk_at_stop_pct_equity"] == 0.3058
    assert risk["remaining_to_stop_drawdown_usd"] == 84.75
    assert risk["risk_cap_pct"] == 0.1
    assert risk["risk_cap_breached"] is True
    assert risk["risk_economics_source"] == "broker.trade_tick_value/trade_tick_size"
    assert "not a close instruction" in risk["claim_boundary"]

    summary = summarize_open_position_stop_risk(
        [{"ticket": 45944855, "stop_loss": 52_734.75, **risk}],
        risk_cap_pct=0.1,
    )
    assert summary["status"] == "POSITION_RISK_CAP_BREACH"
    assert summary["risk_cap_breach_tickets"] == [45944855]
    assert summary["combined_entry_to_stop_risk_usd"] == 136.93
    assert "does not add a retroactive forced-close rule" in summary["detail"]


def test_open_position_stop_beyond_entry_reports_locked_profit_not_entry_loss():
    risk = build_open_position_stop_risk(
        symbol="US30",
        direction="LONG",
        lots=0.01,
        open_price=52_500.00,
        current_price=52_700.00,
        stop_loss=52_600.00,
        take_profit=52_900.00,
        bridge=_IndexBrokerBridge(),
        risk_cap_pct=0.1,
    )

    assert risk["status"] == "PROFIT_LOCKED_BY_STOP"
    assert risk["risk_at_stop_usd"] == 0.0
    assert risk["risk_cap_breached"] is False
    assert risk["stop_locked_profit_usd"] == 100.0
    assert risk["remaining_to_stop_drawdown_usd"] == 100.0
