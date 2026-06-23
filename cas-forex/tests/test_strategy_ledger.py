from pathlib import Path

from cas_forex.strategy_ledger import active_strategy_leads, load_strategy_lead_ledger


def test_strategy_lead_ledger_preserves_active_winners():
    ledger = load_strategy_lead_ledger()
    leads = {lead["lead_id"]: lead for lead in ledger["leads"]}

    assert ledger["claim_boundary"] == "Research leads only. Live trading remains NOT LICENSED."
    assert "range_scalper_filtered_fx_d1" in leads
    assert "index_tsmom_126_d1" in leads
    assert "index_tsmom_252_d1" in leads
    assert leads["range_scalper_filtered_fx_d1"]["priority"] == 1
    assert leads["index_tsmom_126_d1"]["priority"] == 2
    assert leads["range_scalper_filtered_fx_d1"]["deployment_status"] == "NOT LICENSED"
    assert leads["index_tsmom_126_d1"]["deployment_status"] == "NOT LICENSED"
    assert leads["index_tsmom_252_d1"]["deployment_status"] == "NOT LICENSED"


def test_strategy_lead_evidence_refs_resolve_when_file_refs():
    repo_root = Path(__file__).resolve().parents[1]
    for lead in active_strategy_leads():
        for ref in lead["evidence_refs"]:
            if ref.endswith(".json"):
                assert (repo_root / ref).exists(), f"{lead['lead_id']} missing evidence ref {ref}"
