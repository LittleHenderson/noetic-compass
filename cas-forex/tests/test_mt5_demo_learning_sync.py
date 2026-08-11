from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from cas_forex import mt5_demo_learning_sync as sync
from cas_forex.order_attempt_audit import OrderAttemptAuditStore


class _Bridge:
    def __init__(self, *, demo: bool = True, connected: bool = True) -> None:
        self._demo = demo
        self._connected = connected
        self._mt5 = object()
        self.mt5_path = "C:/Program Files/Hugosway/terminal64.exe"

    def is_connected(self) -> bool:
        return self._connected

    def is_demo_account(self) -> bool:
        return self._demo

    def _account_id_hash(self) -> str:
        return "account-hash"


def test_sync_reads_demo_history_and_refreshes_learning(tmp_path, monkeypatch):
    captured: dict = {}

    def history_builder(**kwargs):
        captured.update(kwargs)
        return {
            "account_mode": "demo",
            "ingest_status": "MT5_DEAL_HISTORY_INGESTED",
            "summary": {
                "history_record_count": 2,
                "memory_update_count": 1,
                "closed_position_count": 2,
                "net_profit_loss_account": 14.25,
            },
            "history_records": [
                {"broker_ticket": "7001", "broker_mode": "PAPER_MT5", "profit": 14.25}
            ],
            "artifact_paths": {"json": "history.json"},
        }

    monkeypatch.setattr(sync, "build_mt5_deal_history_ingest_report", history_builder)
    monkeypatch.setattr(
        sync,
        "build_waste_learning_outcomes",
        lambda **kwargs: {
            "learning_ready": True,
            "bound_trade_count": 1,
            "overall": {
                "trades": 1,
                "wins": 1,
                "net_pnl": 14.25,
                "exact_mt5_stop_fill_risk_reconstruction_count": 1,
                "exact_mt5_stop_fill_risk_reconstruction_tickets": ["7001"],
                "legacy_exact_mt5_stop_fill_risk_repair_count": 1,
                "legacy_exact_mt5_stop_fill_risk_repair_tickets": ["7001"],
            },
        },
    )

    report = sync.sync_mt5_demo_learning(
        bridge=_Bridge(),
        config=SimpleNamespace(mt5_path=""),
        state_path=tmp_path / "sync.json",
        deal_history_output_dir=tmp_path / "history",
        order_attempt_state_path=tmp_path / "empty-attempts.json",
        classification_correction_path=tmp_path / "classification-corrections.jsonl",
    )

    assert captured["account_mode"] == "demo"
    assert captured["confirm_live_history"] is False
    assert captured["run_terminal_history_ingest"] is True
    assert captured["write_report"] is True
    assert report["status"] == "MT5_DEMO_LEARNING_BOUND"
    assert report["binding_status"] == "BROKER_OUTCOME_BOUND_TO_AI_DECISION"
    assert report["history_record_count"] == 2
    assert report["bound_trade_count"] == 1
    assert report["learning_exact_mt5_stop_fill_risk_reconstruction_count"] == 1
    assert report["learning_exact_mt5_stop_fill_risk_reconstruction_tickets"] == [
        "7001"
    ]
    assert report["learning_legacy_exact_mt5_stop_fill_risk_repair_count"] == 1
    assert report["learning_legacy_exact_mt5_stop_fill_risk_repair_tickets"] == [
        "7001"
    ]
    assert report["broker_order_touched"] is False
    assert sync.load_mt5_demo_learning_sync(tmp_path / "sync.json")["learning_ready"] is True


def test_sync_binds_operator_order_attempt_to_exact_mt5_position(tmp_path, monkeypatch):
    attempts_path = tmp_path / "order-attempts.json"
    attempts_path.write_text(
        json.dumps(
            {
                "attempts": {
                    "attempt-1": {
                        "attempt_id": "attempt-1",
                        "created_at": "2026-07-10T13:32:16+00:00",
                        "decision_ref": "waste-dir-spx500",
                        "order_id": "waste-waste-dir-spx500",
                        "symbol": "SPX500",
                        "direction": "SHORT",
                        "mode": "PAPER",
                        "bridge_name": "MT5Bridge",
                        "executed": True,
                        "pre_trade_estimate": {
                            "entry_price": 7548.19,
                            "stop_loss": 7554.87,
                            "lots": 0.01,
                            "risk_at_stop_usd": 0.07,
                            "broker_contract_constraints": {
                                "tick_size": 0.01,
                                "tick_value": 1.0,
                            },
                        },
                        "outcome": {
                            "broker_ticket": 45944826,
                            "filled_price": 7548.19,
                            "account_id_hash": "account-hash",
                            "broker_mode": "LIVE_MT5",
                        },
                        "execution_provenance": {
                            "initiator": {
                                "kind": "AI_AUTOMATION",
                                "ai_action": "OPEN_LIVE_CANDLE_LEARNING",
                            },
                            "order_shape": {
                                "decision_ref": "waste-dir-spx500",
                                "order_id": "waste-waste-dir-spx500",
                                "symbol": "SPX500",
                                "direction": "SHORT",
                                "volume": 0.01,
                                "stop_loss": 7554.87,
                                "take_profit": 7521.11,
                            },
                            "strategy": {
                                "ai_action": "OPEN_LIVE_CANDLE_LEARNING",
                                "strategy_id": "live_candle_broker-candle_h1",
                                "market_regime": "directional_pressure",
                                "market_regime_source": "candidate_setup.regime",
                            },
                            "runtime_lane": {
                                "effective_lane": "LIVE_REAL_BROKER",
                                "real_broker_confirmed": True,
                            },
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def history_builder(**kwargs):
        memory = kwargs["memory_report"]
        assert memory["summary"]["memory_record_count"] == 1
        assert memory["memory_records"][0]["broker_ticket"] == "45944826"
        assert memory["memory_records"][0]["market_regime"] == (
            "directional_pressure"
        )
        assert memory["memory_records"][0]["condition_snapshot_open"][
            "market_regime"
        ] == "directional_pressure"
        return {
            "account_mode": "demo",
            "ingest_status": "MT5_DEAL_HISTORY_JOINED_TO_MEMORY",
            "summary": {
                "history_record_count": 1,
                "memory_update_count": 1,
                "closed_position_count": 1,
                "net_profit_loss_account": -6.73,
            },
            "history_records": [
                {
                    "broker_ticket": "45944826",
                    "broker_mode": "PAPER_MT5",
                    "symbol": "SPX500",
                    "direction": "sell",
                    "profit": -6.73,
                    "gross_profit": -6.68,
                    "commission": -0.05,
                    "swap": 0.0,
                    "close_reason": "STOP_LOSS",
                }
            ],
            "artifact_paths": {"json": "history.json"},
        }

    monkeypatch.setattr(sync, "build_mt5_deal_history_ingest_report", history_builder)
    correction_path = tmp_path / "classification-corrections.jsonl"
    report = sync.sync_mt5_demo_learning(
        bridge=_Bridge(),
        state_path=tmp_path / "sync.json",
        order_attempt_state_path=attempts_path,
        deal_history_output_dir=tmp_path / "history",
        classification_correction_path=correction_path,
    )

    assert report["status"] == "MT5_DEMO_LEARNING_BOUND"
    assert report["bound_trade_count"] == 1
    assert report["memory_update_count"] == 1
    assert report["learning_overall"]["losses"] == 1
    assert report["learning_overall"]["net_pnl"] == -6.73
    assert report["learning_grouping_basis"] == "symbol_x_timeframe_x_direction_x_profile"
    assert report["learning_regime_grouping_basis"] == (
        "symbol_x_timeframe_x_direction_x_profile_then_market_regime"
    )
    assert report["learning_pooled_profit_cannot_promote_across_regimes"] is True
    assert report["learning_regime_attributed_trade_count"] == 1
    assert report["learning_unknown_regime_trade_count"] == 0
    assert report["learning_regime_counts"] == {"DIRECTIONAL_PRESSURE": 1}
    assert report["learning_regime_source_counts"] == {
        "candidate_setup.regime": 1
    }
    assert report["learning_cycle_audit_path"] == str(
        tmp_path / "waste-cycle-audit.jsonl"
    )
    assert report["learning_ranking_basis"] == (
        "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl"
    )
    assert report["learning_lot_normalized_trade_count"] == 1
    assert report["learning_lot_normalized_evidence_complete"] is True
    assert report["learning_risk_normalized_trade_count"] == 1
    assert report["learning_risk_normalized_evidence_complete"] is True
    assert report["learning_after_cost_expectancy_r"] == -1.007485
    assert report["learning_stored_pre_trade_risk_mismatch_count"] == 1
    assert report["learning_win_rate_is_supporting_metric_only"] is True
    assert report["learning_group_stats"][0]["net_pnl"] == -6.73
    assert report["bound_outcomes"][0]["broker_ticket"] == "45944826"
    assert report["bound_outcomes"][0]["origin_source"] == "ORDER_ATTEMPT_LEDGER"
    assert report["bound_outcomes"][0]["market_regime"] == (
        "directional_pressure"
    )
    assert report["classification_correction_count"] == 1
    assert report["classification_correction_appended_count"] == 1

    second = sync.sync_mt5_demo_learning(
        bridge=_Bridge(),
        state_path=tmp_path / "sync.json",
        order_attempt_state_path=attempts_path,
        deal_history_output_dir=tmp_path / "history",
        classification_correction_path=correction_path,
    )
    corrections = [
        json.loads(line)
        for line in correction_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert second["classification_correction_appended_count"] == 0
    assert len(corrections) == 1
    assert corrections[0]["action"] == "EXECUTION_CLASSIFICATION_CORRECTED"
    assert corrections[0]["corrected"]["effective_lane"] == "MT5_DEMO_BROKER"
    assert corrections[0]["corrected"]["live_money"] is False


def test_sync_recovers_interrupted_demo_receipt_from_one_exact_history_match(
    tmp_path,
    monkeypatch,
):
    attempts_path = tmp_path / "order-attempts.json"
    attempts_path.write_text(
        json.dumps(
            {
                "attempts": {
                    "attempt-demo-interrupted": {
                        "report_kind": "cas_forex_order_attempt_audit",
                        "attempt_id": "attempt-demo-interrupted",
                        "created_at": "2026-07-13T00:05:52+00:00",
                        "updated_at": "2026-07-13T00:05:52+00:00",
                        "decision_ref": "waste-dir-demo-interrupted",
                        "order_id": "waste-waste-dir-demo-interrupted",
                        "symbol": "NAS100",
                        "direction": "SHORT",
                        "volume": 0.01,
                        "mode": "PAPER",
                        "bridge_name": "MT5Bridge",
                        "is_real_attempt": True,
                        "status": "ATTEMPT_STARTED",
                        "result_finalized": False,
                        "dispatched_to_bridge": False,
                        "executed": False,
                        "order": {
                            "order_id": "waste-waste-dir-demo-interrupted",
                            "decision_ref": "waste-dir-demo-interrupted",
                            "symbol": "NAS100",
                            "direction": "SHORT",
                            "volume": 0.01,
                            "stop_loss": 29777.83,
                            "take_profit": 29708.86,
                            "magic_number": 20260708,
                        },
                        "pre_trade_estimate": {
                            "risk_at_stop_usd": 27.68,
                            "risk_at_stop_pct_equity": 0.0618,
                        },
                        "execution_provenance": {
                            "initiator": {
                                "kind": "AI_AUTOMATION",
                                "ai_action": "OPEN_MICRO_SCALP_LEARNING",
                            },
                            "strategy": {
                                "ai_action": "OPEN_MICRO_SCALP_LEARNING",
                                "strategy_id": "micro_scalp_index-tsmom-126-d1_m1",
                            },
                            "order_shape": {
                                "decision_ref": "waste-dir-demo-interrupted",
                                "order_id": "waste-waste-dir-demo-interrupted",
                                "symbol": "NAS100",
                                "direction": "SHORT",
                                "volume": 0.01,
                                "stop_loss": 29777.83,
                                "take_profit": 29708.86,
                            },
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    history_record = {
        "broker_ticket": "45944950",
        "position_id": "45944950",
        "broker_mode": "PAPER_MT5",
        "symbol": "NAS100",
        "direction": "sell",
        "lots": 0.01,
        "magic": 20260708,
        "open_price": 29749.45,
        "open_time": "2026-07-13T00:05:57+00:00",
        "close_price": 29777.83,
        "close_time": "2026-07-13T00:06:54+00:00",
        "close_reason": "MT5_HISTORY_CLOSE:[sl 29777.83]",
        "gross_profit": -28.38,
        "commission": -0.05,
        "swap": 0.0,
        "profit": -28.43,
    }

    monkeypatch.setattr(
        sync,
        "build_mt5_deal_history_ingest_report",
        lambda **_kwargs: {
            "account_mode": "demo",
            "ingest_status": "MT5_DEAL_HISTORY_JOINED_TO_MEMORY",
            "summary": {
                "history_record_count": 1,
                "memory_update_count": 0,
                "closed_position_count": 1,
                "net_profit_loss_account": -28.43,
            },
            "history_records": [history_record],
            "artifact_paths": {"json": "history.json"},
        },
    )

    def learning_builder(*, attempts, **_kwargs):
        recovered = [
            row
            for row in attempts
            if row.get("decision_ref") == "waste-dir-demo-interrupted"
        ]
        assert len(recovered) == 1
        assert recovered[0]["result_finalized"] is True
        assert recovered[0]["executed"] is True
        assert recovered[0]["outcome"]["broker_ticket"] == "45944950"
        return {
            "learning_ready": False,
            "group_learning_ready": False,
            "overall_sample_ready": False,
            "bound_trade_count": 1,
            "overall": {"trades": 1, "losses": 1, "net_pnl": -28.43},
            "sample_bound_rows": [
                {"broker_ticket": "45944950", "origin_source": "ORDER_ATTEMPT_LEDGER"}
            ],
        }

    monkeypatch.setattr(sync, "build_waste_learning_outcomes", learning_builder)

    report = sync.sync_mt5_demo_learning(
        bridge=_Bridge(),
        state_path=tmp_path / "sync.json",
        order_attempt_state_path=attempts_path,
        deal_history_output_dir=tmp_path / "history",
        classification_correction_path=tmp_path / "classification-corrections.jsonl",
    )

    assert report["demo_attempt_recovered_count"] == 1
    assert report["demo_attempt_recovery"]["status"] == "DEMO_ATTEMPT_RECEIPTS_RECOVERED"
    assert report["demo_attempt_recovery"]["broker_order_touched"] is False
    assert report["demo_attempt_recovered_count_total"] == 1
    assert report["demo_attempt_recovery_history"]["latest_recovered_attempt"][
        "broker_ticket"
    ] == "45944950"
    status = OrderAttemptAuditStore(
        attempts_path,
        tmp_path / "order-attempts-audit.jsonl",
    ).build_status()
    recovered = status["latest_attempt"]
    assert recovered["result_status"] == "BROKER_EXECUTED_RECOVERED_FROM_DEMO_HISTORY"
    assert recovered["outcome"]["broker_ticket"] == "45944950"
    assert status["unresolved_real_attempt_count"] == 0

    second = sync.sync_mt5_demo_learning(
        bridge=_Bridge(),
        state_path=tmp_path / "sync.json",
        order_attempt_state_path=attempts_path,
        deal_history_output_dir=tmp_path / "history",
        classification_correction_path=tmp_path / "classification-corrections.jsonl",
    )
    assert second["demo_attempt_recovered_count"] == 0
    assert second["demo_attempt_recovered_count_total"] == 1
    assert second["demo_attempt_recovery_history"]["latest_recovered_attempt"][
        "broker_ticket"
    ] == "45944950"


@pytest.mark.parametrize(
    ("bridge", "message"),
    [
        (_Bridge(connected=False), "connected"),
        (_Bridge(demo=False), "non-demo"),
    ],
)
def test_sync_refuses_unconnected_or_non_demo_bridge(bridge, message):
    with pytest.raises(RuntimeError, match=message):
        sync.sync_mt5_demo_learning(bridge=bridge)
