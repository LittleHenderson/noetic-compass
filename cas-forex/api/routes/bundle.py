from fastapi import APIRouter
from ..data import daily_bundle, latest_decision, latest_risk

router = APIRouter()


@router.get("/daily")
async def get_daily():
    """Returns latest daily bundle."""
    return daily_bundle()


@router.get("/daily/{date}")
async def get_daily_date(date: str):
    """Returns daily bundle for a specific date."""
    return daily_bundle(date)


@router.get("/decision/latest")
async def get_decision():
    """Returns latest paper decision."""
    return latest_decision()


@router.get("/risk/latest")
async def get_risk():
    """Returns latest paper risk review."""
    return latest_risk()
