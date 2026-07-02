from pathlib import Path

from api.data import strategy_lead_summaries, strategy_leads
from cas_forex.strategy_ledger import active_strategy_leads, load_strategy_lead_ledger


def test_strategy_lead_ledger_preserves_active_winners():
    ledger = load_strategy_lead_ledger()
    leads = {lead["lead_id"]: lead for lead in ledger["leads"]}

    assert ledger["claim_boundary"] == "Research leads only. Live trading remains NOT LICENSED."
    assert "range_scalper_filtered_fx_d1" in leads
    assert "index_tsmom_126_d1" in leads
    assert "index_tsmom_252_d1" in leads
    assert leads["index_tsmom_126_d1"]["priority"] == 1
    assert leads["index_tsmom_252_d1"]["priority"] == 2
    assert leads["range_scalper_filtered_fx_d1"]["priority"] == 4
    assert leads["range_scalper_filtered_fx_d1"]["status"] == "WATCHLIST_ONLY"
    assert "range-scalper-realtest-report.json" in " ".join(
        leads["range_scalper_filtered_fx_d1"]["evidence_refs"]
    )
    assert leads["range_scalper_filtered_fx_d1"]["deployment_status"] == "NOT LICENSED"
    assert leads["index_tsmom_126_d1"]["deployment_status"] == "NOT LICENSED"
    assert leads["index_tsmom_252_d1"]["deployment_status"] == "NOT LICENSED"


def test_strategy_lead_evidence_refs_resolve_when_file_refs():
    repo_root = Path(__file__).resolve().parents[1]
    for lead in active_strategy_leads():
        for ref in lead["evidence_refs"]:
            if ref.endswith(".json"):
                assert (repo_root / ref).exists(), f"{lead['lead_id']} missing evidence ref {ref}"


def test_strategy_lead_summaries_keep_dashboard_fields_but_drop_heavy_refs():
    full = strategy_leads()
    summaries = strategy_lead_summaries(limit=3)

    assert 0 < len(summaries) <= 3
    assert len(str(summaries)) < len(str(full))
    for row in summaries:
        assert row["summary_only"] is True
        assert "lead_id" in row
        assert "priority" in row
        assert "status" in row
        assert "family" in row
        assert isinstance(row["symbols_promoted_for_next_tests"], list)
        assert len(row["headline_results"]) <= 1
        assert row["evidence_refs"] == []
