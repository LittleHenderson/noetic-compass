from fastapi import APIRouter
from ..data import adaptive_cockpit, latest_adaptive_compounding

router = APIRouter()


@router.get("/cockpit")
async def get_cockpit():
    """Returns adaptive cockpit payload."""
    return adaptive_cockpit()


@router.get("/compounding/latest")
async def get_compounding():
    """Returns latest adaptive compounding review."""
    return latest_adaptive_compounding()
