from dataclasses import replace
from datetime import date
from types import SimpleNamespace

from cas_forex.config import config
from cas_forex.paper_broker_adapter import MT5DemoPaperReceiptAdapter
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan, summarize_paper_proof


def _paper_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", False)
    monkeypatch.setattr(config, "paper_trading", True)


class FakeDemoMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def initialize(self, **kwargs):
        return True

    def terminal_info(self):
        return SimpleNamespace(connected=True, name="Fake MT5 Demo")

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            server="Fake-Demo",
            trade_mode=self.ACCOUNT_TRADE_MODE_DEMO,
            company="Fake Demo Broker",
            currency="USD",
            leverage=100,
        )

    def history_orders_get(self, start, end):
        return [
            SimpleNamespace(
                ticket=1001,
                order=1001,
                symbol="US30",
                volume_initial=0.05,
                comment="CAS_FOREX paper",
            )
        ]

    def history_deals_get(self, start, end):
        return [
            SimpleNamespace(
                ticket=2001,
                order=1001,
                symbol="US30",
                volume=0.05,
                profit=12.5,
                comment="CAS_FOREX paper",
            )
        ]

    def positions_get(self):
        return []


class FakeDisconnectedMT5(FakeDemoMT5):
    def terminal_info(self):
        return SimpleNamespace(connected=False, name="Fake MT5 Demo")


class FakeRealMT5(FakeDemoMT5):
    ACCOUNT_TRADE_MODE_DEMO = 0

    def account_info(self):
        return SimpleNamespace(
            login=555555,
            server="Real-Server",
            trade_mode=1,
            company="Real Broker",
            currency="USD",
            leverage=100,
        )


def test_mt5_demo_adapter_collects_api_verified_receipt(monkeypatch):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    adapter = MT5DemoPaperReceiptAdapter(mt5_module=FakeDemoMT5())

    receipt = adapter.collect_receipt(plan, date(2026, 6, 22))

    assert receipt["receipt_validation_status"] == "BROKER_API_VERIFIED"
    assert receipt["broker_source_verified"] is True
    assert receipt["broker_api_authenticated"] is True
    assert receipt["orders_attempted"] == 1
    assert receipt["orders_paper_executed"] == 1
    assert receipt["broker_mode"] == "PAPER_MT5"
    assert len(receipt["receipt_hash_sha256"]) == 64


def test_mt5_demo_adapter_can_append_verified_short_plan(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = replace(build_index_tsmom_126_paper_proof_plan(), required_trading_days=1)
    adapter = MT5DemoPaperReceiptAdapter(mt5_module=FakeDemoMT5())

    adapter.append_verified_day(plan, str(tmp_path), date(2026, 6, 22))
    report = summarize_paper_proof(plan, tmp_path)

    assert report.completed_trading_days == 1
    assert report.chain_verified is True
    assert report.passed is True


def test_mt5_real_account_is_blocked(monkeypatch):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    adapter = MT5DemoPaperReceiptAdapter(mt5_module=FakeRealMT5())

    probe = adapter.probe(plan, date(2026, 6, 22))

    assert probe.status == "BLOCKED"
    assert "not identified as demo" in probe.reasons[0]


def test_mt5_disconnected_account_is_unavailable(monkeypatch):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    adapter = MT5DemoPaperReceiptAdapter(mt5_module=FakeDisconnectedMT5())

    probe = adapter.probe(plan, date(2026, 6, 22))

    assert probe.status == "UNAVAILABLE"
    assert "not connected" in probe.reasons[0]
