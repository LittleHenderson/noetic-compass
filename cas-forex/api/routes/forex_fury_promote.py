"""HTTP route for Forex Fury candidate promotion.

POST /promote — binds a replay candidate to a strategy_leads research-lane
entry after sha256-verifying the underlying .set file against the import
manifest. Always lands in ``PROMOTED_PAPER_LANE``; live-money execution
remains operator-driven and out of scope here.

GET /promotion-status — reports whether a candidate is already represented
in strategy_leads.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cas_forex.forex_fury_promote import (
    ForexFuryPromotionResult,
    find_promoted_lead,
    promote_candidate,
)


router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPLAY_GLOB = (
    "evidence_runs/forex_fury_replay_candidates/forex-fury-replay-candidates-*-report.json"
)
DEFAULT_LEADS_PATH = REPO_ROOT / "strategy_leads.json"


# ---------------------------------------------------------------------------
# Injection hooks for tests
# ---------------------------------------------------------------------------


def _default_loader() -> dict[str, Any]:
    """Load the latest replay-candidates report from disk.

    Returns ``{"candidates": []}`` if no report can be located so the
    promotion logic returns a clean ``candidate not found`` rejection rather
    than raising 500.
    """
    matches = sorted(REPO_ROOT.glob(DEFAULT_REPLAY_GLOB))
    if not matches:
        return {"candidates": []}
    try:
        return json.loads(matches[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"candidates": []}


_LOADER: Callable[[], dict[str, Any]] = _default_loader
_LEADS_PATH: Path = DEFAULT_LEADS_PATH
_REPO_ROOT: Path = REPO_ROOT


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed replay-candidates loader. Tests only."""
    global _LOADER
    _LOADER = loader


def set_leads_path_for_testing(path: Path) -> None:
    """Override the strategy_leads.json path. Tests only."""
    global _LEADS_PATH
    _LEADS_PATH = Path(path)


def set_repo_root_for_testing(path: Path) -> None:
    """Override the repo root used as base for relative .set lookup. Tests only."""
    global _REPO_ROOT
    _REPO_ROOT = Path(path)


def reset_loader_for_testing() -> None:
    """Restore disk-backed defaults."""
    global _LOADER, _LEADS_PATH, _REPO_ROOT
    _LOADER = _default_loader
    _LEADS_PATH = DEFAULT_LEADS_PATH
    _REPO_ROOT = REPO_ROOT


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PromoteRequest(BaseModel):
    candidate_id: str
    # Owner override: promote even if the .set file is missing / unverified.
    allow_unverified: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _result_to_payload(result: ForexFuryPromotionResult) -> dict[str, Any]:
    return result.to_dict()


@router.post("/promote")
async def promote(request: PromoteRequest) -> dict[str, Any]:
    """Promote a replay candidate into the paper research lane.

    400 on a rejected promotion (unknown candidate, missing .set, or sha256
    mismatch) with ``{error, message, integrity}``. 200 on accept with the
    full ``ForexFuryPromotionResult`` payload, including the lead path and
    integrity record.
    """

    candidates_payload = _LOADER()
    result = promote_candidate(
        candidate_id=request.candidate_id,
        replay_candidates=candidates_payload,
        repo_root=_REPO_ROOT,
        leads_path=_LEADS_PATH,
        allow_unverified=request.allow_unverified,
    )
    if not result.accepted:
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.rejection_reason or "promotion rejected",
                "message": (result.integrity.error_message if result.integrity else None)
                or result.rejection_reason
                or "promotion rejected",
                "integrity": result.integrity.to_dict() if result.integrity else None,
                "candidate_id": request.candidate_id,
            },
        )
    return _result_to_payload(result)


@router.get("/promotion-status")
async def promotion_status(candidate_id: Optional[str] = None) -> dict[str, Any]:
    """Report whether ``candidate_id`` has already been promoted to a paper-lane lead.

    Looks up the most recent lead entry in strategy_leads.json that
    references the candidate. ``promoted`` reflects existence only; it does
    NOT reflect live-money status (those leads carry a different status
    field which this module never sets).
    """

    if not candidate_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "candidate_id is required"},
        )
    lead = find_promoted_lead(_LEADS_PATH, candidate_id)
    return {
        "candidate_id": candidate_id,
        "promoted": lead is not None,
        "lead_id": lead.get("lead_id") if lead else None,
    }
