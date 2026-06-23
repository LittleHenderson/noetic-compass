from fastapi import APIRouter
from ..data import pcba_cockpit

router = APIRouter()


@router.get("/cockpit")
async def get_pcba_cockpit():
    """Returns the live PCBA/CJT/CCB diagnostic cockpit payload."""
    return pcba_cockpit()


@router.get("/readiness/pcba")
async def get_pcba_readiness():
    """Returns PCBA production-readiness checks."""
    return pcba_cockpit()["pcba_readiness"]


@router.get("/readiness/cjt")
async def get_cjt_readiness():
    """Returns CJT production-readiness checks."""
    return pcba_cockpit()["cjt_readiness"]


@router.get("/readiness/ccb")
async def get_ccb_readiness():
    """Returns CCB design and claim-readiness checks."""
    return pcba_cockpit()["ccb_readiness"]


@router.get("/optimizer-guard")
async def get_optimizer_guard():
    """Returns the PCBA optimizer guard status."""
    return pcba_cockpit()["optimizer_guard"]
