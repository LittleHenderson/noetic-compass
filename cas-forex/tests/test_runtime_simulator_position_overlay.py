from __future__ import annotations

import json

from api.data import _overlay_runtime_simulator_positions
from cas_forex.movement_stream import build_movement_position_feed_truth


def test_runtime_overlay_separates_planned_orders_from_executed_positions(tmp_path):
    state = tmp_path / "simulated-broker-state.json"
    state.write_text(
        json.dumps(
            {
                "updated_at": "2026-07-10T11:09:46+00:00",
                "void_event_count": 10,
                "positions": {
                    "923871908": {
                        "fill_price": 52582.49,
                        "volume": 0.01,
                        "timestamp": "2026-07-10T11:09:46+00:00",
                        "order": {
                            "order_id": "waste-waste-dir-current",
                            "decision_ref": "waste-dir-current",
                            "symbol": "US30",
                            "direction": "SHORT",
                            "volume": 0.01,
                            "stop_loss": 52674.47,
                            "take_profit": 52491.39,
                            "comment": "CAS_PAPER_LEARNING",
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    planned = [
        {"symbol": "US30", "status": "PAPER_ATTEMPT_ALLOWED"},
        {"symbol": "NAS100", "status": "PAPER_ATTEMPT_ALLOWED"},
    ]
    ledger = {
        "summary": {"open_position_count": 2, "order_count": 2},
        "positions": planned,
        "orders": list(planned),
        "notes": [],
    }

    result = _overlay_runtime_simulator_positions(ledger, state_path=state)

    assert result["paper_order_intents"] == planned
    assert len(result["positions"]) == 1
    position = result["positions"][0]
    assert position["symbol"] == "US30"
    assert position["side"] == "SHORT"
    assert position["simulator_ticket"] == "923871908"
    assert position["status"] == "PAPER_SIMULATOR_EXECUTED_OPEN"
    assert result["summary"]["open_position_count"] == 1
    assert result["summary"]["order_count"] == 2
    assert result["runtime_position_source"]["planned_order_intent_count"] == 2
    assert result["runtime_position_source"]["void_event_count"] == 10


def test_executed_runtime_positions_have_an_explicit_paper_simulator_feed_label():
    truth = build_movement_position_feed_truth(
        positions=[
            {
                "symbol": "US30",
                "status": "PAPER_SIMULATOR_EXECUTED_OPEN",
                "broker_ticket": None,
                "price_source": "provider_snapshot:MT5TerminalMarketDataConnector",
            }
        ],
        quotes=[],
        price_source_status="PROVIDER_ACTIVE",
        market_data_provider_requested=True,
        configured_market_data_provider="OANDARestConnector",
        provider_usable_symbols=["US30"],
        static_fallback_symbols=[],
        mt5_fallback_symbols=["US30"],
    )

    assert truth["position_feed_title"] == "Paper Simulator Positions"
    assert truth["position_feed_count_label"] == "Open paper positions"
    assert truth["position_feed_label"] == "PAPER SIM"
    assert truth["durable_simulator_position_count"] == 1
    assert "approved-only plans" in truth["position_feed_detail"]
