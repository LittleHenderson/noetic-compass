from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.edge_gate import EdgeTestDecision
from cas_forex.live_order_dry_run import LiveOrderDryRunAuditLog
from cas_forex.waste_real_candle_probe import (
    STATUS_EDGE_BLOCKED,
    WasteRealCandleProbeDryRunError,
    WasteRealCandleProbeLog,
    build_live_order_dry_run_from_latest_probe,
    latest_waste_real_candle_probe,
    run_waste_real_candle_probe,
)


def _candles(start: float = 19_000.0, step: float = 45.0, n: int = 180):
    out = []
    price = start
    for i in range(n):
        price += step
        out.append(
            {
                "timestamp": f"2026-06-{(i % 28) + 1:02d}T00:00:00+00:00",
                "open": price - step * 0.2,
                "high": price + abs(step) + 10.0,
                "low": price - abs(step) - 10.0,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return out


class FakeConnector:
    def __init__(self):
        self.requests = []

    def fetch_historical(self, symbol: str, bars: int = 100, timeframe: str = "M5"):
        self.requests.append((symbol, bars, timeframe))
        return _candles()[-bars:]

    def fetch_snapshot(self, symbol: str):
        return SimpleNamespace(
            symbol=symbol,
            bid=19_100.0,
            ask=19_102.0,
            spread=2.0,
            session="NewYork",
            is_market_open=True,
            timestamp=SimpleNamespace(isoformat=lambda: "2026-06-30T12:00:00+00:00"),
        )

    def is_connected(self) -> bool:
        return True


class BrokerTruthConnector(FakeConnector):
    broker_grade_market_truth = True
    read_only_market_data = True
    claim_boundary = "read-only broker-grade test connector; no broker execution bridge"


def test_waste_real_candle_probe_records_candidate_without_broker_or_authorization(tmp_path, monkeypatch):
    log = WasteRealCandleProbeLog(
        tmp_path / "waste-real-candle-probe.json",
        tmp_path / "waste-real-candle-probe-audit.jsonl",
    )

    def fake_eval(setup, entry_pairs, **kwargs):
        return EdgeTestDecision(
            status="NO_TRADE_NULL_FAILED",
            measured_win_prob=0.40,
            null_p95=0.02,
            threshold=kwargs.get("threshold", 0.65),
            edge_token=None,
            evaluated_at="2026-06-30T12:00:00+00:00",
            reason="test edge refused",
        )

    monkeypatch.setattr("cas_forex.waste_real_candle_probe.evaluate_candidate", fake_eval)

    report = run_waste_real_candle_probe(
        symbol="NAS100",
        timeframe="D1",
        connector=FakeConnector(),
        log=log,
    )
    latest = latest_waste_real_candle_probe(log=log)

    assert report["status"] == STATUS_EDGE_BLOCKED
    assert report["broker_touched"] is False
    assert report["edge_authorization_registered"] is False
    assert report["edge_token_persisted"] is False
    assert report["candidate"]["symbol"] == "NAS100"
    assert report["edge"]["status"] == "NO_TRADE_NULL_FAILED"
    cas_map = report["market_state"]["cas_feature_map"]
    assert cas_map["report_kind"] == "cas_forex_waste_cas_feature_map"
    assert cas_map["selected_profile"] == report["market_state"]["selected_directional_profile"]
    assert "cannot create broker ACCEPT" in cas_map["claim_boundary"]
    assert report["market_state"]["directional_hypothesis_tuning"]["cas_feature_map"]["selected_profile"] == cas_map["selected_profile"]
    assert "does not start the timed WASTE runner" in report["claim_boundary"]
    assert latest["status"] == STATUS_EDGE_BLOCKED
    assert (tmp_path / "waste-real-candle-probe-audit.jsonl").exists()


def test_waste_real_candle_probe_can_build_guarded_live_order_dry_run_from_broker_grade_source(tmp_path, monkeypatch):
    log = WasteRealCandleProbeLog(
        tmp_path / "waste-real-candle-probe.json",
        tmp_path / "waste-real-candle-probe-audit.jsonl",
    )
    dry_run_audit = LiveOrderDryRunAuditLog(tmp_path / "live-order-dry-run-audit.jsonl")

    def fake_eval(setup, entry_pairs, **kwargs):
        return EdgeTestDecision(
            status="NO_TRADE_UNDERPOWERED",
            measured_win_prob=0.51,
            null_p95=0.49,
            threshold=kwargs.get("threshold", 0.65),
            edge_token=None,
            evaluated_at="2026-06-30T12:00:00+00:00",
            reason="test edge underpowered",
        )

    monkeypatch.setattr("cas_forex.waste_real_candle_probe.evaluate_candidate", fake_eval)

    probe = run_waste_real_candle_probe(
        symbol="NAS100",
        timeframe="D1",
        connector=BrokerTruthConnector(),
        log=log,
    )
    report = build_live_order_dry_run_from_latest_probe(
        volume=0.01,
        log=log,
        dry_run_audit=dry_run_audit,
    )

    assert probe["status"] == STATUS_EDGE_BLOCKED
    assert probe["broker_grade_market_truth"] is True
    assert report["report_kind"] == "cas_forex_live_order_dry_run"
    assert report["broker_touched"] is False
    assert report["status"] == "DRY_RUN_BLOCKED"
    source = report["waste_real_candle_source"]
    assert source["status"] == "WASTE_PROBE_DRY_RUN_HANDOFF_READY"
    assert source["broker_grade_market_truth"] is True
    assert source["entry_pair_count"] > 0
    assert any(
        check["check_id"] == "broker_grade_market_truth" and check["passed"]
        for check in source["checks"]
    )
    latest = dry_run_audit.latest()
    assert latest is not None
    assert latest["payload"]["waste_real_candle_source"]["decision_ref"] == probe["candidate"]["decision_ref"]


def test_waste_real_candle_probe_dry_run_rejects_non_broker_grade_source(tmp_path, monkeypatch):
    log = WasteRealCandleProbeLog(
        tmp_path / "waste-real-candle-probe.json",
        tmp_path / "waste-real-candle-probe-audit.jsonl",
    )

    def fake_eval(setup, entry_pairs, **kwargs):
        return EdgeTestDecision(
            status="NO_TRADE_UNDERPOWERED",
            measured_win_prob=0.51,
            null_p95=0.49,
            threshold=kwargs.get("threshold", 0.65),
            edge_token=None,
            evaluated_at="2026-06-30T12:00:00+00:00",
            reason="test edge underpowered",
        )

    monkeypatch.setattr("cas_forex.waste_real_candle_probe.evaluate_candidate", fake_eval)

    run_waste_real_candle_probe(
        symbol="NAS100",
        timeframe="D1",
        connector=FakeConnector(),
        log=log,
    )

    with pytest.raises(WasteRealCandleProbeDryRunError, match="broker_grade_market_truth"):
        build_live_order_dry_run_from_latest_probe(volume=0.01, log=log)


def test_waste_real_candle_probe_route_registered_and_returns_report(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "run_waste_real_candle_probe",
        lambda **kwargs: {
            "report_kind": "cas_forex_waste_real_candle_probe",
            "status": "NO_CANDIDATE",
            "broker_touched": False,
            "edge_authorization_registered": False,
            "kwargs": kwargs,
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.post(
        "/api/forex/waste-loop-control/real-candle-probe/run",
        json={"symbol": "NAS100", "timeframe": "D1", "bars": 120, "max_pairs": 40},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_real_candle_probe"
    assert body["broker_touched"] is False
    assert body["kwargs"]["symbol"] == "NAS100"


def test_waste_real_candle_probe_dry_run_route_registered_and_returns_report(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_live_order_dry_run_from_latest_probe",
        lambda **kwargs: {
            "report_kind": "cas_forex_live_order_dry_run",
            "status": "DRY_RUN_BLOCKED",
            "broker_touched": False,
            "kwargs": kwargs,
            "waste_real_candle_source": {
                "status": "WASTE_PROBE_DRY_RUN_HANDOFF_READY",
                "broker_grade_market_truth": True,
            },
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.post(
        "/api/forex/waste-loop-control/real-candle-probe/dry-run",
        json={"volume": 0.01},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_live_order_dry_run"
    assert body["broker_touched"] is False
    assert body["kwargs"]["volume"] == 0.01
    assert body["waste_real_candle_source"]["status"] == "WASTE_PROBE_DRY_RUN_HANDOFF_READY"


def test_waste_real_candle_probe_dry_run_route_rejects_invalid_source(monkeypatch):
    def raise_source_error(**kwargs):
        raise WasteRealCandleProbeDryRunError("blocked source")

    monkeypatch.setattr(route_module, "build_live_order_dry_run_from_latest_probe", raise_source_error)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.post(
        "/api/forex/waste-loop-control/real-candle-probe/dry-run",
        json={"volume": 0.01},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "blocked source"
