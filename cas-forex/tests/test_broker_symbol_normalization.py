from types import SimpleNamespace

import pytest

from cas_forex.broker.mt5_bridge import MT5Bridge
from cas_forex.instruments import (
    broker_symbol_candidates,
    canonical_or_normalized_symbol,
    canonical_symbol,
    resolve_broker_symbol,
)
from cas_forex.schemas.forecast import Direction, ForecastProposal, ModelSource
from cas_forex.schemas.order import BrokerOrderRequest, OrderStatus


def test_canonical_symbol_accepts_common_mt5_aliases():
    assert canonical_symbol("EURUSD") == "EUR/USD"
    assert canonical_symbol("EURUSDm") == "EUR/USD"
    assert canonical_symbol("XAUUSD") == "XAU/USD"
    assert canonical_symbol("GOLD") == "XAU/USD"
    assert canonical_symbol("NAS100.cash") == "NAS100"
    assert canonical_symbol("US30.pro") == "US30"


def test_growth_identity_collapses_supported_aliases_without_merging_unknowns():
    assert canonical_or_normalized_symbol("USTEC.cash") == "NAS100"
    assert canonical_or_normalized_symbol("US500m") == "SPX500"
    assert canonical_or_normalized_symbol("GOLD") == "XAU/USD"
    assert canonical_or_normalized_symbol("private.synthetic-7") == "PRIVATESYNTHETIC7"
    assert canonical_or_normalized_symbol("") == "UNKNOWN"


def test_owner_symbol_override_candidates_are_first():
    candidates = broker_symbol_candidates("NAS100", "NAS100=NAS100.cash|USTEC")

    assert candidates[:2] == ("NAS100.cash", "USTEC")
    assert "NAS100" in candidates


def test_resolve_broker_symbol_discovers_visible_suffix_symbol():
    class FakeMT5:
        def __init__(self):
            self.selected = []

        def symbol_select(self, symbol, enabled):
            self.selected.append((symbol, enabled))
            return True

        def symbol_info(self, symbol):
            return SimpleNamespace(trade_mode=1) if symbol == "NAS100.pro" else None

        def symbols_get(self, pattern=None):
            return [SimpleNamespace(name="NAS100.pro"), SimpleNamespace(name="EURUSD")]

    fake = FakeMT5()
    resolution = resolve_broker_symbol("NAS100", broker=fake)

    assert resolution.selected_symbol == "NAS100.pro"
    assert resolution.resolution_source == "BROKER_SYMBOL_DISCOVERY"
    assert ("NAS100.pro", True) in fake.selected


def test_order_and_forecast_store_canonical_symbol_from_broker_alias():
    order = BrokerOrderRequest(
        order_id="ord-alias",
        decision_ref="dec-alias",
        symbol="EURUSDm",
        direction=Direction.LONG,
        volume=0.01,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
    )
    proposal = ForecastProposal(
        proposal_id="prop-alias",
        symbol="XAUUSDm",
        direction=Direction.LONG,
        entry_price=2300.0,
        stop_loss=2280.0,
        take_profit=2340.0,
        confidence=0.7,
        model_source=ModelSource.TECHNICAL,
    )

    assert order.symbol == "EUR/USD"
    assert proposal.symbol == "XAU/USD"


def test_mt5_bridge_routes_order_to_discovered_broker_symbol():
    class FakeMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TYPE_BUY_LIMIT = 2
        ORDER_TYPE_SELL_LIMIT = 3
        ORDER_TYPE_BUY_STOP = 4
        ORDER_TYPE_SELL_STOP = 5
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1

        def __init__(self):
            self.selected = []

        def symbol_select(self, symbol, enabled):
            self.selected.append((symbol, enabled))
            return True

        def symbol_info(self, symbol):
            if symbol != "NAS100.pro":
                return None
            return SimpleNamespace(
                point=1.0,
                digits=2,
                filling_mode=2,
                trade_mode=1,
                volume_min=0.01,
                volume_step=0.01,
                volume_max=100.0,
                trade_stops_level=0,
                trade_freeze_level=0,
            )

        def symbol_info_tick(self, symbol):
            assert symbol == "NAS100.pro"
            return SimpleNamespace(bid=19000.0, ask=19001.0)

        def symbols_get(self, pattern=None):
            return [SimpleNamespace(name="NAS100.pro")]

    order = BrokerOrderRequest(
        order_id="nas-discovered",
        decision_ref="dec-1",
        symbol="NAS100",
        direction=Direction.LONG,
        volume=0.02,
        price=19001.0,
        stop_loss=18900.0,
        take_profit=19200.0,
    )
    bridge = MT5Bridge()
    bridge._mt5 = FakeMT5()
    bridge._connected = True

    request = bridge._build_mt5_request(order)

    assert request["symbol"] == "NAS100.pro"
    assert bridge.last_symbol_resolution["selected_symbol"] == "NAS100.pro"
    assert bridge.last_symbol_resolution["resolution_source"] == "BROKER_SYMBOL_DISCOVERY"


def test_mt5_bridge_rejects_volume_below_broker_min_before_send():
    class FakeMT5:
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_REJECT = 10006
        TRADE_RETCODE_CANCEL = 10007
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TYPE_BUY_LIMIT = 2
        ORDER_TYPE_SELL_LIMIT = 3
        ORDER_TYPE_BUY_STOP = 4
        ORDER_TYPE_SELL_STOP = 5
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1
        ACCOUNT_TRADE_MODE_DEMO = 0

        def __init__(self):
            self.sent = []

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def account_info(self):
            return SimpleNamespace(trade_mode=0, server="Broker-Demo")

        def symbol_info(self, symbol):
            return SimpleNamespace(
                point=0.00001,
                digits=5,
                filling_mode=1,
                volume_min=0.1,
                volume_step=0.1,
                volume_max=10.0,
            ) if symbol == "EURUSD" else None

        def symbol_info_tick(self, symbol):
            return SimpleNamespace(bid=1.0999, ask=1.1001)

        def order_send(self, request):
            self.sent.append(dict(request))
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=1, price=request["price"])

    fake = FakeMT5()
    bridge = MT5Bridge()
    bridge._mt5 = fake
    bridge._connected = True
    order = BrokerOrderRequest(
        order_id="below-min",
        decision_ref="dec-1",
        symbol="EUR/USD",
        direction=Direction.LONG,
        volume=0.01,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
    )

    outcome = bridge.execute_order(order)

    assert outcome.status == OrderStatus.REJECTED
    assert "below broker minimum" in (outcome.error_message or "")
    assert outcome.broker_symbol_resolution["selected_symbol"] == "EURUSD"
    assert fake.sent == []


@pytest.mark.parametrize("volume", [0.15, 0.25])
def test_mt5_bridge_rejects_volume_not_aligned_to_lot_step(volume):
    class FakeMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TYPE_BUY_LIMIT = 2
        ORDER_TYPE_SELL_LIMIT = 3
        ORDER_TYPE_BUY_STOP = 4
        ORDER_TYPE_SELL_STOP = 5
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1

        def symbol_info(self, symbol):
            return SimpleNamespace(
                point=0.00001,
                digits=5,
                filling_mode=1,
                volume_min=0.1,
                volume_step=0.1,
                volume_max=10.0,
            ) if symbol == "EURUSD" else None

    bridge = MT5Bridge()
    bridge._mt5 = FakeMT5()
    order = BrokerOrderRequest(
        order_id=f"bad-step-{volume}",
        decision_ref="dec-1",
        symbol="EURUSD",
        direction=Direction.LONG,
        volume=volume,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
    )

    with pytest.raises(ValueError, match="volume_step"):
        bridge._build_mt5_request(order)
