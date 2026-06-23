"""Persistent strategy-lead ledger for CAS FOREX.

The ledger keeps profitable research leads visible while new strategies are
tested. It is memory, not deployment authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


LEDGER_PATH = Path(__file__).resolve().parents[1] / "strategy_leads.json"
REQUIRED_STATUSES = {"ACTIVE_RESEARCH_LEAD", "WATCHLIST_ONLY", "RETIRED"}


def load_strategy_lead_ledger(path: Path = LEDGER_PATH) -> Dict[str, Any]:
    """Load and validate the CAS FOREX strategy-lead ledger."""
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_strategy_lead_ledger(data)
    return data


def validate_strategy_lead_ledger(data: Dict[str, Any]) -> None:
    if data.get("claim_boundary") != "Research leads only. Live trading remains NOT LICENSED.":
        raise ValueError("Strategy ledger must preserve the NOT LICENSED claim boundary")
    leads = data.get("leads")
    if not isinstance(leads, list) or not leads:
        raise ValueError("Strategy ledger must contain at least one lead")
    lead_ids = set()
    for lead in leads:
        lead_id = lead.get("lead_id")
        if not lead_id or lead_id in lead_ids:
            raise ValueError(f"Invalid or duplicate lead_id: {lead_id!r}")
        lead_ids.add(lead_id)
        if lead.get("status") not in REQUIRED_STATUSES:
            raise ValueError(f"{lead_id} has invalid status {lead.get('status')!r}")
        if lead.get("deployment_status") != "NOT LICENSED":
            raise ValueError(f"{lead_id} must remain NOT LICENSED until live gates close")
        if not lead.get("evidence_refs"):
            raise ValueError(f"{lead_id} must keep evidence references")
        if not lead.get("open_gates"):
            raise ValueError(f"{lead_id} must list open gates")


def active_strategy_leads(path: Path = LEDGER_PATH) -> List[Dict[str, Any]]:
    """Return active leads ordered by priority."""
    data = load_strategy_lead_ledger(path)
    leads = [lead for lead in data["leads"] if lead["status"] == "ACTIVE_RESEARCH_LEAD"]
    return sorted(leads, key=lambda lead: int(lead.get("priority", 999)))
