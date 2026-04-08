"""GET /assessments/export — retrieve stored assessments for the authenticated user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from api.store import get_assessments

router = APIRouter(tags=["export"])


class ExportResponse(BaseModel):
    """Paginated list of persisted assessments."""

    assessments: list[dict[str, Any]]
    count: int
    limit: int
    offset: int


@router.get("/assessments/export", response_model=ExportResponse)
async def export_assessments(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ExportResponse:
    """Return saved assessments for the authenticated API key."""
    api_key: str = getattr(getattr(request, "state", None), "api_key", "default")
    records = await get_assessments(api_key=api_key, limit=limit, offset=offset)
    return ExportResponse(
        assessments=records,
        count=len(records),
        limit=limit,
        offset=offset,
    )
