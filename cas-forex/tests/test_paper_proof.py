from datetime import date
from dataclasses import replace

import pytest

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.paper_proof import (
    PAPER_PROOF_CLAIM_BOUNDARY,
    append_paper_proof_day,
    build_index_tsmom_126_paper_proof_plan,
    paper_broker_receipt_template,
    paper_proof_store_path,
    summarize_paper_proof,
    write_paper_proof_plan,
    write_paper_proof_status,
)


@pytest.fixture(autouse=True)
def _reset_profit_overrides():
    """Owner profit-threshold overrides are process-global; isolate each test."""
    from cas_forex.proof_control import clear_profit_threshold_overrides

    clear_profit_threshold_overrides()
    yield
    clear_profit_threshold_overrides()


def _paper_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", False)
    monkeypatch.setattr(config, "paper_trading", True)


def _receipt(plan, **overrides):
    data = {
        "receipt_id": "receipt-001",
        "source_attestation": "BROKER_EXPORT_HASHED",
        "broker_mode": "PAPER_MT5",
        "trading_date": "2026-06-22",
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "symbols": plan.symbols,
        "timeframe": plan.timeframe,
        "orders_attempted": 1,
        "orders_paper_executed": 1,
        "open_positions_reconciled": True,
        "live_mode": False,
        "broker_export_sha256": "a" * 64,
        "account_id_hash": "b" * 64,
        "server": "Demo-Server",
        "terminal_name": "MT5 Demo",
        "provider_receipt_id": "demo-export-001",
        "order_ids": ["paper-order-001"],
    }
    data.update(overrides)
    return data


def test_index_tsmom_plan_preserves_not_licensed_boundary(tmp_path):
    plan = build_index_tsmom_126_paper_proof_plan()
    path = write_paper_proof_plan(plan, tmp_path)

    assert plan.lead_id == "index_tsmom_126_d1"
    assert plan.strategy_setting == "tsmom_126_250_2_10"
    assert plan.symbols == ["US30", "NAS100"]
    assert plan.timeframe == "D1"
    assert plan.deployment_status == "NOT LICENSED"
    assert plan.broker_accept_status == "NOT LICENSED"
    assert plan.payment_transfer_status == "NOT LICENSED"
    assert PAPER_PROOF_CLAIM_BOUNDARY in path.read_text(encoding="utf-8")


def test_append_day_keeps_status_incomplete_until_real_paper_proof(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()

    summary = append_paper_proof_day(
        plan,
        tmp_path,
        trading_date=date(2026, 6, 22),
        orders_attempted=0,
        orders_paper_executed=0,
    )
    report = summarize_paper_proof(plan, tmp_path)
    status_path = write_paper_proof_status(plan, tmp_path, report)
    store = EvidenceStore(paper_proof_store_path(plan, tmp_path), run_id=plan.plan_id)

    assert summary["trading_day"] == 1
    assert summary["broker_source_verified"] is False
    assert report.completed_trading_days == 1
    assert report.chain_verified is True
    assert report.passed is False
    assert any("paper_days 1 < required 30" in reason for reason in report.failure_reasons)
    assert any("broker_verified_days 0 < required 30" in reason for reason in report.failure_reasons)
    assert store.verify_chain() is True
    assert "NOT LICENSED" in status_path.read_text(encoding="utf-8")


def test_paper_proof_refuses_live_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", True)
    plan = build_index_tsmom_126_paper_proof_plan()

    with pytest.raises(PermissionError, match="live_mode=False"):
        append_paper_proof_day(plan, tmp_path, trading_date=date(2026, 6, 22))


def test_duplicate_trading_day_cannot_inflate_paper_count(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    append_paper_proof_day(plan, tmp_path, trading_date=date(2026, 6, 22))

    with pytest.raises(ValueError, match="already has an entry"):
        append_paper_proof_day(plan, tmp_path, trading_date=date(2026, 6, 22))

    assert summarize_paper_proof(plan, tmp_path).completed_trading_days == 1


def test_receipt_template_is_scoped_to_current_plan():
    plan = build_index_tsmom_126_paper_proof_plan()
    template = paper_broker_receipt_template(plan, trading_date=date(2026, 6, 22))

    assert template["lead_id"] == plan.lead_id
    assert template["strategy_setting"] == plan.strategy_setting
    assert template["symbols"] == plan.symbols
    assert template["timeframe"] == "D1"
    assert template["source_attestation"] == "BROKER_EXPORT_HASHED"
    assert template["live_mode"] is False


def test_hash_bound_broker_export_does_not_count_as_api_verified(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()
    append_paper_proof_day(plan, tmp_path, trading_date=date(2026, 6, 22))

    summary = append_paper_proof_day(
        plan,
        tmp_path,
        trading_date=date(2026, 6, 22),
        broker_receipt=_receipt(plan),
    )
    report = summarize_paper_proof(plan, tmp_path)
    store = EvidenceStore(paper_proof_store_path(plan, tmp_path), run_id=plan.plan_id)

    assert summary["trading_day"] == 1
    assert summary["broker_receipt_validated"] is True
    assert summary["broker_source_verified"] is False
    assert summary["broker_api_authenticated"] is False
    assert len(summary["broker_receipt_hash_sha256"]) == 64
    assert report.completed_trading_days == 1
    assert report.packet_count == 2
    assert report.passed is False
    assert any("broker_verified_days 0 < required 30" in reason for reason in report.failure_reasons)
    assert store.verify_chain() is True


def test_api_verified_receipt_can_satisfy_short_test_plan(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = replace(build_index_tsmom_126_paper_proof_plan(), required_trading_days=1)

    append_paper_proof_day(
        plan,
        tmp_path,
        trading_date=date(2026, 6, 22),
        broker_receipt=_receipt(plan, source_attestation="BROKER_API_VERIFIED", realized_pnl=15.0),
        allow_api_verified_receipt=True,
    )
    report = summarize_paper_proof(plan, tmp_path)

    assert report.completed_trading_days == 1
    assert report.chain_verified is True
    assert report.broker_verified_days == 1
    assert report.net_pnl_usd == 15.0
    assert report.profit_passed is True
    assert report.passed is True
    assert report.failure_reasons == []


def test_live_broker_receipt_is_rejected(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = build_index_tsmom_126_paper_proof_plan()

    with pytest.raises(ValueError, match="live_mode must be false"):
        append_paper_proof_day(
            plan,
            tmp_path,
            trading_date=date(2026, 6, 22),
            broker_receipt=_receipt(plan, live_mode=True),
        )


def _append_verified(plan, tmp_path, day, **overrides):
    overrides.setdefault("source_attestation", "BROKER_API_VERIFIED")
    overrides["trading_date"] = day.isoformat()
    overrides["receipt_id"] = f"receipt-{day.isoformat()}"
    append_paper_proof_day(
        plan,
        tmp_path,
        trading_date=day,
        broker_receipt=_receipt(plan, **overrides),
        allow_api_verified_receipt=True,
    )


def test_profit_gate_blocks_when_proof_is_not_net_positive(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = replace(build_index_tsmom_126_paper_proof_plan(), required_trading_days=1)

    _append_verified(plan, tmp_path, date(2026, 6, 22), realized_pnl=-5.0)
    report = summarize_paper_proof(plan, tmp_path)

    assert report.broker_verified_days == 1
    assert report.net_pnl_usd == -5.0
    assert report.profit_passed is False
    assert report.passed is False
    assert any("net P&L" in reason for reason in report.failure_reasons)


def test_profit_gate_blocks_when_drawdown_exceeds_limit(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    plan = replace(build_index_tsmom_126_paper_proof_plan(), required_trading_days=2)

    # Net positive (+200) but a 12% peak-to-trough drawdown on the 2000 seed.
    _append_verified(plan, tmp_path, date(2026, 6, 22), realized_pnl=500.0)
    _append_verified(plan, tmp_path, date(2026, 6, 23), realized_pnl=-300.0)
    report = summarize_paper_proof(plan, tmp_path)

    assert report.net_pnl_usd == 200.0
    assert report.max_drawdown_pct >= 8.0
    assert report.profit_passed is False
    assert report.passed is False
    assert any("drawdown" in reason for reason in report.failure_reasons)


def test_plan_only_days_can_never_pass_even_when_count_met(monkeypatch, tmp_path):
    """Anti-gaming: a ledger of plan-only heartbeats is never a passed proof."""
    _paper_mode(monkeypatch)
    plan = replace(build_index_tsmom_126_paper_proof_plan(), required_trading_days=1)

    append_paper_proof_day(
        plan,
        tmp_path,
        trading_date=date(2026, 6, 22),
        orders_attempted=0,
        orders_paper_executed=0,
    )
    report = summarize_paper_proof(plan, tmp_path)

    assert report.completed_trading_days == 1
    assert report.broker_verified_days == 0
    assert report.profit_passed is False
    assert report.passed is False
    assert any("broker_verified_days 0 < required 1" in reason for reason in report.failure_reasons)


def test_profit_thresholds_are_owner_adjustable(monkeypatch, tmp_path):
    from cas_forex.proof_control import (
        clear_profit_threshold_overrides,
        set_profit_threshold_overrides,
    )

    _paper_mode(monkeypatch)
    plan = replace(build_index_tsmom_126_paper_proof_plan(), required_trading_days=1)
    _append_verified(plan, tmp_path, date(2026, 6, 22), realized_pnl=15.0)

    assert summarize_paper_proof(plan, tmp_path).passed is True

    # Raise the bar above the achieved P&L: the same ledger no longer passes.
    set_profit_threshold_overrides(min_net_pnl_usd=50.0)
    assert summarize_paper_proof(plan, tmp_path).passed is False

    clear_profit_threshold_overrides()
    assert summarize_paper_proof(plan, tmp_path).passed is True
