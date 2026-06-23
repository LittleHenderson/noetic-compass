from fastapi import APIRouter
from ..data import mt5_receipt, mt_history

router = APIRouter()


@router.get("/history")
async def get_history():
    """Returns MT4/MT5 history summary."""
    return mt_history()


@router.get("/receipt/latest")
async def get_receipt():
    """Returns latest MT5 receipt."""
    return mt5_receipt()
