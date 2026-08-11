"""Runtime process-topology status route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from cas_forex.runtime_topology import build_runtime_topology_status


router = APIRouter()


@router.get("")
async def get_runtime_topology() -> dict[str, Any]:
    return build_runtime_topology_status()
