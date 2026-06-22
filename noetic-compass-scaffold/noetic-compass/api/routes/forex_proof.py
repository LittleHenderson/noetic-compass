"""CAS Forex proof cockpit — READ-ONLY evidence endpoints.

Serves the local paper-proof evidence JSON for the active CAS Forex lead
(``index_tsmom_126_d1``) so the read-only proof cockpit (atlas-viewer ``/forex``)
can display live status instead of bundled fixtures.

HARD BOUNDARY. These endpoints are GET-only and serve already-non-secret
paper-proof evidence that is also checked into the repo. There is NO order,
transfer, unlock, promotion, or any other live-action path here — the router
only reads JSON files off disk. Live trading, broker ``ACCEPT``, auto-deposit,
debit/card/bank movement, and payout automation remain ``NOT LICENSED``.

The frontend calls ``/api/forex/...``; the atlas-viewer dev proxy strips ``/api``
so requests reach this router at ``/forex/...``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/forex", tags=["forex"])

# Repo root from this file: routes/ -> api/ -> noetic-compass/ ->
# noetic-compass-scaffold/ -> <repo root>. The cas-forex package and its
# evidence live at <repo root>/cas-forex/.
_DEFAULT_EVIDENCE_DIR = (
    Path(__file__).resolve().parents[4]
    / "cas-forex"
    / "evidence_runs"
    / "index_tsmom_126_paper_proof"
)

# Overridable so the API can point at a relocated/archived evidence dir without
# code changes. Read-only either way.
EVIDENCE_DIR = Path(os.environ.get("CAS_FOREX_EVIDENCE_DIR", str(_DEFAULT_EVIDENCE_DIR)))

_LEAD_PREFIX = "index-tsmom-126-d1-paper-proof"

# Endpoint suffix -> evidence filename. Fixed mapping (no user-supplied paths),
# so there is no path-traversal surface.
_FILES: dict[str, str] = {
    "paper": f"{_LEAD_PREFIX}-status.json",
    "ui-readiness": f"{_LEAD_PREFIX}-ui-readiness-status.json",
    "schedule": f"{_LEAD_PREFIX}-daily-schedule-status.json",
    "decision": f"{_LEAD_PREFIX}-paper-decision-status.json",
    "risk": f"{_LEAD_PREFIX}-paper-risk-status.json",
    "bundle": f"{_LEAD_PREFIX}-daily-bundle-status.json",
}


def _read_evidence(name: str) -> dict:
    """Read and parse one evidence file. 404 when absent so the cockpit can
    fall back to bundled fixtures without breaking."""
    filename = _FILES[name]
    path = EVIDENCE_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"CAS Forex evidence not found: {filename}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500, detail=f"Failed to read CAS Forex evidence {filename}: {exc}"
        ) from exc


@router.get("")
def forex_index() -> JSONResponse:
    """Read-only index of the available CAS Forex proof endpoints."""
    return JSONResponse(
        {
            "service": "cas-forex-proof",
            "mode": "READ_ONLY",
            "lead_id": "index_tsmom_126_d1",
            "deployment_status": "NOT LICENSED",
            "broker_accept_status": "NOT LICENSED",
            "payment_transfer_status": "NOT LICENSED",
            "endpoints": [f"/forex/proof/{suffix}" for suffix in _FILES],
            "evidence_available": EVIDENCE_DIR.is_dir(),
        }
    )


@router.get("/proof/paper")
def get_paper_proof() -> JSONResponse:
    return JSONResponse(_read_evidence("paper"))


@router.get("/proof/ui-readiness")
def get_ui_readiness() -> JSONResponse:
    return JSONResponse(_read_evidence("ui-readiness"))


@router.get("/proof/schedule")
def get_daily_schedule() -> JSONResponse:
    return JSONResponse(_read_evidence("schedule"))


@router.get("/proof/decision")
def get_paper_decision() -> JSONResponse:
    return JSONResponse(_read_evidence("decision"))


@router.get("/proof/risk")
def get_paper_risk() -> JSONResponse:
    return JSONResponse(_read_evidence("risk"))


@router.get("/proof/bundle")
def get_daily_bundle() -> JSONResponse:
    return JSONResponse(_read_evidence("bundle"))
