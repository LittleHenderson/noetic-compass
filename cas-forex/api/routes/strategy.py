from fastapi import APIRouter
from ..data import backsolve_summary, condition_tally, strategy_leads, walk_forward_summary

router = APIRouter()


@router.get("/leads")
async def get_leads():
    """Returns all strategy leads."""
    return strategy_leads()


@router.get("/backsolve")
async def get_backsolve():
    """Returns latest leverage backsolve summary."""
    return backsolve_summary()


@router.get("/condition-tally")
async def get_condition_tally():
    """Returns condition tally buckets."""
    return condition_tally()


@router.get("/walk-forward")
async def get_walk_forward():
    """Returns latest walk-forward summary."""
    return walk_forward_summary()
