"""POST /assess — single prompt direct assessment (bypasses LLM)."""

from fastapi import APIRouter

try:
    import cas_engine
except ImportError:
    cas_engine = None  # type: ignore[assignment]

from api.models import AssessRequest, NccsResponse

router = APIRouter()


@router.post("/assess", response_model=NccsResponse)
async def assess(req: AssessRequest) -> NccsResponse:
    """Direct assessment from pre-scored input. No LLM call."""
    result = cas_engine.compute_nccs(
        operator_scores=req.operator_scores,
        domain_averages=req.domain_averages,
        drive_scores=req.drive_scores,
        rpm_completeness=req.rpm_completeness,
        pathway_rpm_completeness=req.pathway_rpm_completeness,
        bias_flag_count=req.bias_flag_count,
        inversion_axis_scores=req.inversion_axis_scores,
        stealth_resistance=req.stealth_resistance,
        compound_severity=req.compound_severity,
        manipulation_resistance=req.manipulation_resistance,
        overton_drift_resistance=req.overton_drift_resistance,
    )

    return NccsResponse(
        operator_profile=result["operator_profile"],
        domain_coherence=result["domain_coherence"],
        drive_rpm_integrity=result["drive_rpm_integrity"],
        pathway_quality=result["pathway_quality"],
        inversion_resistance=result["inversion_resistance"],
        social_engineering=result["social_engineering"],
        composite=result["composite"],
        certification=result["certification"],
    )
