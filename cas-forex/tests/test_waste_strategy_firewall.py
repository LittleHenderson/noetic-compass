from __future__ import annotations

import json
from pathlib import Path

from cas_forex.waste_strategy_firewall import evaluate_waste_strategy_firewall


def _lead(
    lead_id: str,
    *,
    status: str = "ACTIVE_RESEARCH_LEAD",
    symbol: str = "EUR/USD",
    timeframes: list[str] | None = None,
    priority: int = 1,
) -> dict:
    return {
        "lead_id": lead_id,
        "status": status,
        "deployment_status": "NOT LICENSED",
        "priority": priority,
        "condition_fit": {"preferred_timeframes": timeframes or ["M15"]},
        "symbols_promoted_for_next_tests": [symbol],
        "symbols_watchlist": [],
        "symbols_excluded_until_condition_proof": [],
        "evidence_refs": ["evidence_runs/test/report.json"],
        "open_gates": ["paper proof remains open"],
    }


def _ledger(path: Path, leads: list[dict]) -> Path:
    path.write_text(
        json.dumps(
            {
                "claim_boundary": "Research leads only. Live trading remains NOT LICENSED.",
                "schema_version": "test",
                "updated_at": "2026-06-30T00:00:00+00:00",
                "leads": leads,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_active_research_lead_allows_waste_candidate_testing(tmp_path):
    path = _ledger(tmp_path / "strategy_leads.json", [_lead("eur-m15")])

    decision = evaluate_waste_strategy_firewall("EUR/USD", "M15", ledger_path=path)

    assert decision.candidate_allowed is True
    assert decision.firewall_status == "ELIGIBLE_RESEARCH_LEAD"
    assert decision.lead_id == "eur-m15"
    assert decision.deployment_status == "NOT LICENSED"
    assert "edge-gate testing only" in decision.to_dict()["reason"]


def test_watchlist_only_lead_blocks_candidate_formation(tmp_path):
    path = _ledger(
        tmp_path / "strategy_leads.json",
        [_lead("range-scalper", status="WATCHLIST_ONLY", symbol="GBP/USD", timeframes=["D1"])],
    )

    decision = evaluate_waste_strategy_firewall("GBP/USD", "D1", ledger_path=path)

    assert decision.candidate_allowed is False
    assert decision.firewall_status == "NO_TRADE_LEAD_STATUS_BLOCKED"
    assert decision.lead_status == "WATCHLIST_ONLY"
    assert "cannot form WASTE candidates" in decision.to_dict()["reason"]


def test_active_symbol_wrong_timeframe_blocks_until_fresh_evidence(tmp_path):
    path = _ledger(
        tmp_path / "strategy_leads.json",
        [_lead("index-d1", symbol="NAS100", timeframes=["D1"])],
    )

    decision = evaluate_waste_strategy_firewall("NAS100", "M15", ledger_path=path)

    assert decision.candidate_allowed is False
    assert decision.firewall_status == "NO_TRADE_TIMEFRAME_BLOCKED"
    assert decision.lead_id == "index-d1"
    assert "outside preferred_timeframes" in decision.to_dict()["reason"]


def test_unknown_symbol_blocks_instead_of_creating_new_live_hypothesis(tmp_path):
    path = _ledger(tmp_path / "strategy_leads.json", [_lead("eur-m15")])

    decision = evaluate_waste_strategy_firewall("XAU/USD", "M15", ledger_path=path)

    assert decision.candidate_allowed is False
    assert decision.firewall_status == "NO_TRADE_NO_LEDGER_MATCH"
    assert decision.lead_id is None


def test_default_ledger_allows_index_d1_but_blocks_range_scalper_watchlist():
    index_decision = evaluate_waste_strategy_firewall("NAS100", "D1")
    range_decision = evaluate_waste_strategy_firewall("GBP/USD", "D1")

    assert index_decision.candidate_allowed is True
    assert index_decision.lead_id in {"index_tsmom_126_d1", "index_tsmom_252_d1"}
    assert index_decision.deployment_status == "NOT LICENSED"
    assert range_decision.candidate_allowed is False
    assert range_decision.lead_id == "range_scalper_filtered_fx_d1"
