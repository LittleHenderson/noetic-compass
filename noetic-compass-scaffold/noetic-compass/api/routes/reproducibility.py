"""POST /reproducibility — test-retest reliability measurement.

Runs the same prompt against the same provider N times and computes
statistical measures of scoring consistency: mean, std dev, min, max,
coefficient of variation, and certification consistency.
"""

from __future__ import annotations

import math
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.llm_connectors.registry import get_connector
from api.models import DialConfigSchema
from api.pipeline.runner import WrapPipelineRunner

router = APIRouter()


class ReproducibilityRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    provider: str = Field(default="mock")
    model: str | None = None
    mock: bool = False
    runs: int = Field(default=10, ge=2, le=50)
    scoring_mode: str = Field(default="heuristic_fallback")
    scoring_provider: str | None = None
    scoring_model: str | None = None
    dial_config: DialConfigSchema = Field(default_factory=DialConfigSchema)


class RunResult(BaseModel):
    run_index: int
    composite: float
    certification: str
    operator_profile: float
    domain_coherence: float
    drive_rpm_integrity: float
    inversion_resistance: float
    elapsed_ms: float


class ReproducibilityStats(BaseModel):
    mean: float
    std_dev: float
    min: float
    max: float
    range: float
    coefficient_of_variation: float
    certification_consistency: float
    dominant_certification: str


class ReproducibilityResponse(BaseModel):
    prompt: str
    provider: str
    total_runs: int
    completed_runs: int
    stats: ReproducibilityStats
    runs: list[RunResult]
    total_elapsed_ms: float


def _compute_stats(scores: list[float], certifications: list[str]) -> ReproducibilityStats:
    n = len(scores)
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / max(1, n - 1)
    std_dev = math.sqrt(variance)
    min_val = min(scores)
    max_val = max(scores)
    cv = (std_dev / mean * 100) if mean > 0 else 0.0

    cert_counts: dict[str, int] = {}
    for c in certifications:
        cert_counts[c] = cert_counts.get(c, 0) + 1
    dominant = max(cert_counts, key=cert_counts.get)  # type: ignore[arg-type]
    consistency = cert_counts[dominant] / n * 100

    return ReproducibilityStats(
        mean=round(mean, 2),
        std_dev=round(std_dev, 2),
        min=round(min_val, 2),
        max=round(max_val, 2),
        range=round(max_val - min_val, 2),
        coefficient_of_variation=round(cv, 2),
        certification_consistency=round(consistency, 1),
        dominant_certification=dominant,
    )


@router.post("/reproducibility", response_model=ReproducibilityResponse)
async def reproducibility_test(req: ReproducibilityRequest) -> ReproducibilityResponse:
    """Run the same prompt N times and measure scoring consistency."""
    provider = "mock" if req.mock else req.provider
    connector = get_connector(provider, model=req.model)

    run_results: list[RunResult] = []
    t0 = time.monotonic()

    for i in range(req.runs):
        runner = WrapPipelineRunner(connector=connector, dial_config=req.dial_config)
        result = await runner.run(
            req.text,
            scoring_mode=req.scoring_mode,
            scoring_provider=req.scoring_provider,
            scoring_model=req.scoring_model,
        )
        elapsed = result.provenance.get("elapsed_ms", 0.0)
        run_results.append(RunResult(
            run_index=i,
            composite=result.nccs.composite,
            certification=result.nccs.certification,
            operator_profile=result.nccs.operator_profile,
            domain_coherence=result.nccs.domain_coherence,
            drive_rpm_integrity=result.nccs.drive_rpm_integrity,
            inversion_resistance=result.nccs.inversion_resistance,
            elapsed_ms=elapsed,
        ))

    total_elapsed = round((time.monotonic() - t0) * 1000, 1)
    composites = [r.composite for r in run_results]
    certifications = [r.certification for r in run_results]
    stats = _compute_stats(composites, certifications)

    return ReproducibilityResponse(
        prompt=req.text[:200],
        provider=provider,
        total_runs=req.runs,
        completed_runs=len(run_results),
        stats=stats,
        runs=run_results,
        total_elapsed_ms=total_elapsed,
    )
