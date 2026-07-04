"""Owner command broker routes: catalog, preview, execute, receipts.

Chat and the UI use these to ACT with a preview → typed CONFIRM → receipt. The
broker runs the same gated service functions the buttons use; it never bypasses
a gate. Admission to these routes is governed by owner auth (loopback free,
off-box needs pairing).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from cas_forex import owner_command_broker

router = APIRouter()


class PreviewRequest(BaseModel):
    command: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    command: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    confirm: str = Field(default="")


@router.get("/catalog")
async def get_catalog() -> dict[str, Any]:
    return {"report_kind": "cas_forex_owner_command", "commands": owner_command_broker.catalog(), "claim_boundary": owner_command_broker.CLAIM_BOUNDARY}


@router.post("/preview")
async def post_preview(body: PreviewRequest) -> dict[str, Any]:
    return owner_command_broker.preview(body.command, body.params)


@router.post("/execute")
async def post_execute(body: ExecuteRequest) -> dict[str, Any]:
    return owner_command_broker.execute(body.command, body.params, body.confirm)


@router.get("/receipts")
async def get_receipts(limit: Optional[int] = 25) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_owner_command",
        "receipts": owner_command_broker.recent_receipts(limit or 25),
    }
