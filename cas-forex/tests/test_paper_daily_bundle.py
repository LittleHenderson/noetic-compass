from datetime import date
from types import SimpleNamespace

import pytest

from cas_forex.config import config
from cas_forex.paper_broker_adapter import PaperBrokerReceiptProbe
from cas_forex.paper_daily_bundle import run_daily_paper_bundle
from cas_forex.paper_decision import summarize_paper_route_decisions
from cas_forex.paper_proof import BROKER_API_VERIFIED, build_index_tsmom_126_paper_proof_plan, summarize_paper_proof
from cas_forex.paper_risk import summarize_paper_risk_reviews


def _trend_candles(count=130, start=100.0, step=0.25):
    candles = []
    for idx in range(count):
        close = start + idx * step
        candles.append(
            {
                "timestamp": f"2026-01-{(idx % 28) + 1:02d}T00:00:00+00:00",
                "open": close - 0.1,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1000,
            }
        )
    return candles


def _flat_candles(count=130, price=100.0):
    return [
        {
            "timestamp": f"2026-01-{(idx % 28) + 1:02d}T00:00:00+00:00",
            "open": price,
            "high": price + 0.1,
            "low": price - 0.1,
            "close": price,
            "volume": 1000,
        }
        for idx in range(count)
    ]


class PassingMacro:
    def evaluate(self, at=None):
        return SimpleNamespace(status="PASS", reason="No macro blackout active.", evidence={})


class FakeVerifiedReceiptAdapter:
    def probe(self, plan, trading_date):
        return PaperBrokerReceiptProbe(
            status=BROKER_API_VERIFIED,
            broker="FAKE_MT5",
            trading_date=trading_date.isoformat(),
            receipt={
                "receipt_id": f"{plan.plan_id}-{trading_date.isoformat()}-fake-mt5",
                "source_attestation": BROKER_API_VERIFIED,
                "broker_mode": "PAPER_MT5",
                "trading_date": trading_date.isoformat(),
                "lead_id": plan.lead_id,
                "strategy_setting": plan.strategy_setting,
                "symbols": plan.symbols,
                "timeframe": plan.timeframe,
                "orders_attempted": 0,
                "orders_paper_executed": 0,
                "open_positions_reconciled": True,
                "live_mode": False,
                "broker_export_sha256": "a" * 64,
                "account_id_hash": "b" * 64,
                "server": "Fake-Demo",
                "terminal_name": "Fake MT5",
                "provider_receipt_id": "fake-provider",
                "order_ids": [],
            },
        )


def _paper_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", False)
    monkeypatch.setattr(config, "paper_trading", True)


def test_daily_bundle_appends_receipt_decision_and_risk(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()

    bundle = run_daily_paper_bundle(
        plan,
        tmp_path,
        trading_date=date(2026, 6, 22),
        mt5_adapter=FakeVerifiedReceiptAdapter(),
        macro_gate=PassingMacro(),
        candles_by_symbol={"US30": _trend_candles(), "NAS100": _flat_candles()},
        account_equity=5_000,
    )

    assert bundle.completed is True
    assert [step.status for step in bundle.steps] == ["APPENDED", "APPENDED", "APPENDED"]
    assert bundle.latest_proof["completed_trading_days"] == 1
    assert bundle.latest_decision["latest_decision"]["route_action"] == "ROUTE_PAPER_SIGNAL"
    assert bundle.latest_risk["latest_review"]["risk_status"] == "PAPER_ATTEMPTS_ALLOWED"


def test_daily_bundle_skips_existing_date_without_duplicate_packets(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    kwargs = {
        "trading_date": date(2026, 6, 22),
        "mt5_adapter": FakeVerifiedReceiptAdapter(),
        "macro_gate": PassingMacro(),
        "candles_by_symbol": {"US30": _trend_candles(), "NAS100": _flat_candles()},
        "account_equity": 5_000,
    }

    run_daily_paper_bundle(plan, tmp_path, **kwargs)
    second = run_daily_paper_bundle(plan, tmp_path, **kwargs)

    assert [step.status for step in second.steps] == [
        "SKIPPED_EXISTING",
        "SKIPPED_EXISTING",
        "SKIPPED_EXISTING",
    ]
    assert summarize_paper_proof(plan, tmp_path).packet_count == 1
    assert summarize_paper_route_decisions(plan, tmp_path)["decision_count"] == 1
    assert summarize_paper_risk_reviews(plan, tmp_path)["review_count"] == 1


def test_daily_bundle_refuses_live_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", False)
    plan = build_index_tsmom_126_paper_proof_plan()

    with pytest.raises(PermissionError, match="live_mode=False"):
        run_daily_paper_bundle(plan, tmp_path, trading_date=date(2026, 6, 22))
