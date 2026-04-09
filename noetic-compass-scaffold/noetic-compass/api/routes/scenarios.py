"""Scenario catalog API — serves adversarial resilience scenarios."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

CATALOG_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios" / "catalog"


@router.get("/catalog")
async def get_catalog():
    """Return all adversarial resilience scenarios."""
    path = CATALOG_DIR / "adversarial_resilience.json"
    if not path.exists():
        return {"scenarios": [], "metadata": {}}
    data = json.loads(path.read_text())
    return data
