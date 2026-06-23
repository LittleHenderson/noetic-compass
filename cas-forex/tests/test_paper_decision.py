from datetime import date
from types import SimpleNamespace

import pytest

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.paper_decision import (
    append_paper_route_decision,
    evaluate_paper_route_decision,
    paper_decision_store_path,
    summarize_paper_route_decisions,
)
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan


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


class FailingMacro:
    def evaluate(self, at=None):
        return SimpleNamespace(status="FAIL", reason="Macro blackout: NFP", evidence={"event_type": "NFP"})


def test_paper_decision_routes_when_tsmom_signal_exists():
    plan = build_index_tsmom_126_paper_proof_plan()

    decision = evaluate_paper_route_decision(
        plan,
        trading_date=date(2026, 6, 22),
        candles_by_symbol={
            "US30": _trend_candles(),
            "NAS100": _flat_candles(),
        },
        macro_gate=PassingMacro(),
    )

    assert decision.route_action == "ROUTE_PAPER_SIGNAL"
    routed = [item for item in decision.symbol_decisions if item.action == "ROUTE_PAPER_SIGNAL"]
    assert routed[0].symbol == "US30"
    assert routed[0].direction == "LONG"
    assert routed[0].proposal is not None


def test_paper_decision_no_trade_when_no_signal():
    plan = build_index_tsmom_126_paper_proof_plan()

    decision = evaluate_paper_route_decision(
        plan,
        trading_date=date(2026, 6, 22),
        candles_by_symbol={
            "US30": _flat_candles(),
            "NAS100": _flat_candles(),
        },
        macro_gate=PassingMacro(),
    )

    assert decision.route_action == "NO_TRADE"
    assert {item.action for item in decision.symbol_decisions} == {"NO_TRADE"}


def test_paper_decision_macro_lock_blocks_route():
    plan = build_index_tsmom_126_paper_proof_plan()

    decision = evaluate_paper_route_decision(
        plan,
        trading_date=date(2026, 6, 22),
        candles_by_symbol={
            "US30": _trend_candles(),
            "NAS100": _trend_candles(),
        },
        macro_gate=FailingMacro(),
    )

    assert decision.route_action == "NO_TRADE_MACRO_LOCK"
    assert decision.event_context == "pre_NFP"


def test_paper_decision_append_chain_and_summary(tmp_path):
    plan = build_index_tsmom_126_paper_proof_plan()
    decision = evaluate_paper_route_decision(
        plan,
        trading_date=date(2026, 6, 22),
        candles_by_symbol={
            "US30": _trend_candles(),
            "NAS100": _flat_candles(),
        },
        macro_gate=PassingMacro(),
    )

    append_paper_route_decision(decision, tmp_path)
    summary = summarize_paper_route_decisions(plan, tmp_path)
    store = EvidenceStore(paper_decision_store_path(plan, tmp_path), run_id=f"{plan.plan_id}-paper-decisions")

    assert summary["decision_count"] == 1
    assert summary["route_counts"] == {"ROUTE_PAPER_SIGNAL": 1}
    assert summary["chain_verified"] is True
    assert store.verify_chain() is True


def test_paper_decision_refuses_live_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", False)
    plan = build_index_tsmom_126_paper_proof_plan()

    with pytest.raises(PermissionError, match="live_mode=False"):
        evaluate_paper_route_decision(
            plan,
            trading_date=date(2026, 6, 22),
            candles_by_symbol={"US30": _trend_candles(), "NAS100": _trend_candles()},
            macro_gate=PassingMacro(),
        )
