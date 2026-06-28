from fastapi import APIRouter, Query

from ..data import live_readiness

router = APIRouter()


@router.get("/live")
async def get_live_readiness(sync_to_broker: bool = Query(default=False)):
    """Returns the plain-English live-operability checklist."""
    return live_readiness(sync_to_broker=sync_to_broker)
