from fastapi import APIRouter, Query
from ..data import movement_stream

router = APIRouter()


@router.get("/snapshot")
async def get_movement_snapshot(use_provider: bool = Query(default=False)):
    """Returns paper/demo account + market movement telemetry snapshot.

    Set ``use_provider=true`` to request configured-provider market snapshots.
    The route remains paper/demo telemetry only and falls back to deterministic
    paper-route prices per symbol when a provider is unavailable.
    """
    return movement_stream(use_provider_quotes=use_provider)
