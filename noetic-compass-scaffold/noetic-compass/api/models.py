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
    manipulation_resistance: float = Field(ge=0.0, le=1.0, default=1.0)
    overton_drift_resistance: float = Field(ge=0.0, le=1.0, default=1.0)


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
    social_engineering: float
    composite: float
    certification: str


class StageResult(BaseModel):
    """Result from a single pipeline stage."""

    stage: str
    success: bool
    data: dict = Field(default_factory=dict)
    error: str | None = None


class WrapResponse(BaseModel):
    """Full wrap pipeline response."""

    nccs: NccsResponse
    stages: list[StageResult]
    llm_response: LLMResponseSchema | None = None


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


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_type: str = "api_error"
