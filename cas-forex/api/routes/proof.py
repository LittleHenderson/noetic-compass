from fastapi import APIRouter
from ..data import daily_schedule, ui_readiness

router = APIRouter()


@router.get("/readiness")
async def get_readiness():
    """Returns UI readiness report for the active proof plan."""
    return ui_readiness()


@router.get("/schedule")
async def get_schedule():
    """Returns daily schedule for the active proof plan."""
    return daily_schedule()
