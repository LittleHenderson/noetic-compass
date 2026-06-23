from cas_forex.condition_tally import tally_by_event_context, tally_walk_forward_conditions
from cas_forex.walk_forward import WalkForwardWindow


def _window(**overrides):
    data = {
        "window_index": 0,
        "symbol": "EUR/USD",
        "timeframe": "D1",
        "time_scale": "day",
        "train_start_index": 0,
        "train_end_index": 100,
        "test_start_index": 100,
        "test_end_index": 130,
        "train_start_timestamp": None,
        "train_end_timestamp": None,
        "test_start_timestamp": None,
        "test_end_timestamp": None,
        "test_regime": "range",
        "test_vol_mult": 1.0,
        "test_event_context": "normal",
        "route_key": "source=real|symbol=EUR/USD|event_context=normal",
        "route_action": "ROUTE",
        "setting": "range_scalper_24_120",
        "family": "range_scalper",
        "test_return_pct": 1.2,
        "test_max_dd_pct": 2.1,
        "test_trades": 8,
    }
    data.update(overrides)
    return WalkForwardWindow(**data)


def test_tally_walk_forward_conditions_preserves_winning_pockets():
    windows = [
        _window(test_event_context="normal", test_return_pct=1.2, test_trades=8),
        _window(window_index=1, test_event_context="post_NFP", test_return_pct=0.7, test_trades=3),
        _window(
            window_index=2,
            symbol="US30",
            timeframe="H1",
            time_scale="hour",
            test_regime="range",
            test_event_context="conflict_shock",
            route_action="NO_TRADE",
            setting=None,
            test_return_pct=0.0,
            test_trades=0,
        ),
    ]

    tally = tally_walk_forward_conditions(windows)

    assert tally["summary"]["windows"] == 3
    assert tally["summary"]["routed_windows"] == 2
    assert tally["summary"]["positive_routed_window_rate"] == 1.0
    assert tally["summary"]["event_context_counts"] == {
        "conflict_shock": 1,
        "normal": 1,
        "post_NFP": 1,
    }
    assert tally["claim_boundary"].endswith("Live trading remains NOT LICENSED.")
    assert tally["buckets"][0]["routed_windows"] == 1
    assert tally["buckets"][0]["positive_windows"] == 1


def test_tally_by_event_context_groups_macro_conditions():
    windows = [
        _window(test_event_context="post_NFP", test_return_pct=1.0),
        _window(window_index=1, test_event_context="post_NFP", test_return_pct=-0.5),
    ]

    tally = tally_by_event_context(windows)

    assert tally["axes"] == ["test_event_context", "symbol", "timeframe", "route_action", "setting"]
    assert tally["buckets"][0]["axes"]["test_event_context"] == "post_NFP"
    assert tally["buckets"][0]["windows"] == 2
    assert tally["buckets"][0]["positive_window_rate"] == 0.5


def test_tally_defaults_missing_legacy_event_context_to_normal():
    tally = tally_by_event_context([
        {
            "symbol": "EUR/USD",
            "timeframe": "D1",
            "route_action": "ROUTE",
            "setting": "range_scalper_24_120",
            "test_return_pct": 0.4,
            "test_trades": 2,
        }
    ])

    assert tally["summary"]["event_context_counts"] == {"normal": 1}
    assert tally["buckets"][0]["axes"]["test_event_context"] == "normal"
