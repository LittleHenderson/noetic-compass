"""Pydantic request/response schemas for the Noetic Compass API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DialConfigSchema(BaseModel):
    """Dial configuration for 10 cognitive operators. Each value in [3, 9]."""

    values: list[int] = Field(
        default=[6] * 10,
        min_length=10,
        max_length=10,
        description="Dial values for CO-0 through CO-9",
    )

    @field_validator("values")
    @classmethod
    def validate_dial_values(cls, v: list[int]) -> list[int]:
        for i, val in enumerate(v):
            if val < 3 or val > 9:
                raise ValueError(f"dial CO-{i} value {val} out of range [3, 9]")
        # Check involution pair divergence
        pairs = [(2, 3), (5, 6), (8, 9)]
        for a, b in pairs:
            if abs(v[a] - v[b]) > 4:
                raise ValueError(
                    f"involution pair CO-{a}/CO-{b} divergence "
                    f"{abs(v[a] - v[b])} exceeds max of 4"
                )
        return v


class AssessRequest(BaseModel):
    """Direct assessment request — bypasses LLM, takes pre-scored data."""

    operator_scores: list[float] = Field(min_length=10, max_length=10)
    domain_averages: list[float] = Field(min_length=4, max_length=4)
    drive_scores: list[float] = Field(min_length=7, max_length=7)
    rpm_completeness: float = Field(ge=0.0, le=1.0)
    pathway_rpm_completeness: float = Field(ge=0.0, le=1.0, default=1.0)
    bias_flag_count: int = Field(ge=0, default=0)
    inversion_axis_scores: list[float] = Field(
        min_length=7, max_length=7, default=[1.0] * 7
    )
    stealth_resistance: float = Field(ge=0.0, le=1.0, default=1.0)
    compound_severity: float = Field(ge=0.0, le=1.0, default=0.0)
    manipulation_resistance: float = Field(ge=0.0, le=1.0, default=0.5)
    overton_drift_resistance: float = Field(ge=0.0, le=1.0, default=0.5)

    @field_validator("domain_averages")
    @classmethod
    def validate_simplex(cls, v: list[float]) -> list[float]:
        """Domain averages must lie on the open probability simplex (sum≈1, all>0)."""
        if any(x <= 0 for x in v):
            raise ValueError("domain_averages must all be strictly positive (open simplex)")
        total = sum(v)
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"domain_averages must sum to 1.0 (got {total:.4f}). "
                "Normalize before sending."
            )
        return v


class WrapRequest(BaseModel):
    """Full 8-stage wrap pipeline request."""

    text: str = Field(min_length=1, max_length=50000)
    provider: str = Field(default="mock")
    dial_config: DialConfigSchema = Field(default_factory=DialConfigSchema)
    model: str | None = None
    mock: bool = False


class BatchRequest(BaseModel):
    """Batch assessment request."""

    texts: list[str] = Field(min_length=1, max_length=1000)
    provider: str = Field(default="mock")
    dial_config: DialConfigSchema = Field(default_factory=DialConfigSchema)
    model: str | None = None
    mock: bool = False
    max_concurrency: int = Field(default=10, ge=1, le=100)


class LLMResponseSchema(BaseModel):
    """Response from an LLM call."""

    text: str
    model: str
    usage: dict = Field(default_factory=dict)
    latency_ms: float


class NccsResponse(BaseModel):
    """NCCS scoring result."""

    operator_profile: float
    domain_coherence: float
    drive_rpm_integrity: float
    pathway_quality: float
    inversion_resistance: float
    social_engineering: float | None = None  # None = not measured
    bias_flags: int | None = None  # None = not measured
    composite: float
    certification: str
    not_measured: list[str] = Field(default_factory=list)


class StageResult(BaseModel):
    """Result from a single pipeline stage."""

    stage: str
    success: bool
    data: dict = Field(default_factory=dict)
    error: str | None = None


class InterpretationSchema(BaseModel):
    """AI-generated executive briefing for non-technical stakeholders."""

    bottom_line: str
    findings: list[str]
    recommendations: list[str]


class FractalAnalysisSchema(BaseModel):
    """Cognitive Fractal analysis of the operator sequence."""

    dominant_sequence: list[int] = Field(default_factory=list)
    canonical_form: list[int] = Field(default_factory=list)
    cancellations_detected: int = 0
    classification: str = "neutral"
    orbit_length: int = 1
    has_fixed_point: bool = True


class WrapResponse(BaseModel):
    """Full wrap pipeline response."""

    nccs: NccsResponse
    stages: list[StageResult]
    llm_response: LLMResponseSchema | None = None
    scoring_method: str = "heuristic"
    provenance: dict = Field(default_factory=dict)
    interpretation: InterpretationSchema | None = None
    fractal_analysis: FractalAnalysisSchema | None = None


class BatchResponse(BaseModel):
    """Batch assessment response."""

    results: list[WrapResponse]
    total: int
    succeeded: int
    failed: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    engine: str = "cas-engine"


class CohortProfile(BaseModel):
    """A single candidate profile for cohort comparison."""

    label: str = Field(min_length=1, max_length=200)
    operator_scores: list[float] = Field(min_length=10, max_length=10)
    domain_averages: list[float] = Field(min_length=4, max_length=4)

    @field_validator("domain_averages")
    @classmethod
    def validate_cohort_simplex(cls, v: list[float]) -> list[float]:
        if any(x <= 0 for x in v):
            raise ValueError("domain_averages must all be strictly positive")
        total = sum(v)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"domain_averages must sum to 1.0 (got {total:.4f})")
        return v


class CohortCompareRequest(BaseModel):
    """Request for cohort distance comparison."""

    profiles: list[CohortProfile] = Field(min_length=2, max_length=100)


class CohortDistance(BaseModel):
    """Pairwise distance between two profiles."""

    from_label: str
    to_label: str
    geodesic_distance: float
    alignment_pct: float
    bhattacharyya_coefficient: float
    similarity_pct: float


class CohortCluster(BaseModel):
    """Cluster assignment for a profile."""

    label: str
    cluster: int


class CohortCompareResponse(BaseModel):
    """Response with pairwise distances and cluster assignments."""

    distances: list[CohortDistance]
    labels: list[str]
    clusters: list[CohortCluster]


class BenchmarkRequest(BaseModel):
    """Multi-provider benchmark request — runs each provider N times."""

    text: str = Field(min_length=1, max_length=50000)
    providers: list[str] = Field(min_length=1)
    runs_per_provider: int = Field(default=5, ge=2, le=20)
    dial_config: DialConfigSchema = Field(default_factory=DialConfigSchema)
    max_concurrency: int = Field(default=3, ge=1, le=20)


class ProviderBenchmarkResult(BaseModel):
    """Statistical results for a single provider across multiple runs."""

    provider: str
    scores: list[float]
    mean: float
    std_dev: float
    min: float
    max: float
    certification_counts: dict[str, int]
    high_variance: bool
    failed_runs: int
    avg_latency_ms: float


class BenchmarkResponse(BaseModel):
    """Aggregated benchmark results across providers."""

    results: list[ProviderBenchmarkResult]
    prompt_preview: str
    runs_per_provider: int
    total_runs: int
    variance_threshold: float = 5.0


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_type: str = "api_error"
