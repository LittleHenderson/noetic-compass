from fastapi import APIRouter
from ..route_cache import cache_first_payload
from ..data import pcba_cockpit

router = APIRouter()
_PCBA_CACHE_TTL_SECONDS = 300.0


@router.get("/cockpit")
async def get_pcba_cockpit():
    """Returns the live PCBA/CJT/CCB diagnostic cockpit payload."""
    return cache_first_payload(
        "pcba_cockpit",
        builder=pcba_cockpit,
        fallback=_pcba_cockpit_warming,
        ttl_seconds=_PCBA_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


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


def _pcba_cockpit_warming() -> dict:
    empty_readiness = {
        "report_id": "pcba-cockpit-warming",
        "generated_at": None,
        "summary": "PCBA/CJT diagnostics are warming.",
        "all_ready": False,
        "any_live_authority": False,
        "any_broker_accept_authority": False,
        "checks": [],
    }
    return {
        "report_kind": "cas_forex_pcba_cockpit",
        "panels_active": False,
        "source": "warming",
        "claim_boundary": (
            "PCBA/CJT/CCB diagnostics are warming and fail closed. This packet "
            "does not create broker ACCEPT, unlock live trading, auto-deposit, "
            "move bank/card funds, automate payouts, or mark anything LICENSED."
        ),
        "summary": {
            "pcba_ready_checks": 0,
            "pcba_total_checks": 0,
            "cjt_ready_checks": 0,
            "cjt_total_checks": 0,
            "ccb_designs_well_formed": False,
            "ccb_claims_licensed": False,
            "goal_complete": False,
            "current_boundary_honest": True,
        },
        "local_evidence": {
            "pcba": {},
            "cjt": {},
            "pcba_present_count": 0,
            "pcba_total_count": 0,
            "cjt_present_count": 0,
            "cjt_total_count": 0,
        },
        "reference_boards": [],
        "component_catalog": [],
        "pcba_readiness": empty_readiness,
        "cjt_readiness": dict(empty_readiness, report_id="cjt-cockpit-warming"),
        "ccb_readiness": {
            "report_id": "ccb-cockpit-warming",
            "summary": "CCB diagnostics are warming.",
            "all_designs_well_formed": False,
            "any_claim_licensed": False,
            "board_checks": [],
            "prediction_head": {
                "status": "OPEN",
                "present_evidence": [],
                "required_evidence": [],
                "rationale": "Prediction-head diagnostics are warming.",
            },
        },
        "optimizer_guard": {
            "guard": "CASPCBAOptimizerGuard",
            "active": False,
            "proposal_counts": {"research_queue": 0, "flagged": 0, "rejected": 0},
            "claim_boundary": "Optimizer guard diagnostics are warming and provide no live authority.",
            "can_create_broker_accept": False,
            "can_unlock_live_trading": False,
        },
        "goal_status": {
            "goal_complete": False,
            "current_boundary_honest": True,
            "status": "OPEN",
        },
    }
