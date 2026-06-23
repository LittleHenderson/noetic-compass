from fastapi import APIRouter
from ..data import (
    authority_boundary,
    owner_control,
    runtime_gates_report,
    ai_model_status,
    broker_candidate_profiles,
)

router = APIRouter()


@router.get("/owner-control")
async def get_owner_control():
    """Returns owner control state."""
    return owner_control()


@router.get("/authority-boundary")
async def get_authority_boundary():
    """Returns the current owner-controlled live-money authority boundary."""
    return authority_boundary()


@router.get("/runtime-gates")
async def get_runtime_gates():
    """Returns each real-money capability gate: authorized vs pending owner enable,
    with the exact requirements still missing for each."""
    return runtime_gates_report()


@router.get("/ai-model")
async def get_ai_model():
    """Returns the open-weight AI research-model status (advisory only)."""
    return ai_model_status()


@router.get("/broker-candidates")
async def get_broker_candidates():
    """Returns owner-requested broker candidates and verification status."""
    return broker_candidate_profiles()
