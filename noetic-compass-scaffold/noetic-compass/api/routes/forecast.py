"""Predictive Lacunarity Risk routes."""

from fastapi import APIRouter

from api.models import ForecastRequest, ForecastResponse
from api.pipeline.forecast import compute_predictive_lacunarity_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("", response_model=ForecastResponse)
@router.post("/", response_model=ForecastResponse)
async def forecast(req: ForecastRequest) -> ForecastResponse:
    """Compute structural risk forecasts from existing CAS metrics."""
    result = compute_predictive_lacunarity_forecast(
        operator_scores=req.operator_scores,
        domain_scores=req.domain_scores,
        drive_scores=req.drive_scores,
        rpm_completeness=req.rpm_completeness,
        fractal_sequence=req.fractal_sequence,
        resolution_details=req.resolution_details,
    )
    return ForecastResponse(
        context_label=req.context_label,
        source=req.source,
        overall_risk_score=result["overall_risk_score"],
        risk_band=result["risk_band"],
        lacunarity=result["lacunarity"],
        forecasts=result["forecasts"],
        dominant_structural_gaps=result["dominant_structural_gaps"],
        validation_status=result["validation_status"],
        limitations=result["limitations"],
    )
