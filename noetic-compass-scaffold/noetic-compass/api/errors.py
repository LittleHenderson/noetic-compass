"""Custom exceptions and FastAPI exception handlers."""

from fastapi import Request
from fastapi.responses import JSONResponse


class DialViolationError(Exception):
    """Raised when dial configuration violates safety constraints."""

    def __init__(self, detail: str):
        self.detail = detail


class ScoringError(Exception):
    """Raised when scoring engine encounters invalid input."""

    def __init__(self, detail: str):
        self.detail = detail


class LLMError(Exception):
    """Raised when an LLM connector fails."""

    def __init__(self, detail: str, provider: str = "unknown"):
        self.detail = detail
        self.provider = provider


class PipelineStageError(Exception):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: str, detail: str):
        self.stage = stage
        self.detail = detail


async def dial_violation_handler(_request: Request, exc: DialViolationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.detail, "error_type": "dial_violation"},
    )


async def scoring_error_handler(_request: Request, exc: ScoringError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.detail, "error_type": "scoring_error"},
    )


async def llm_error_handler(_request: Request, exc: LLMError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": exc.detail,
            "error_type": "llm_error",
            "provider": exc.provider,
        },
    )


async def pipeline_stage_error_handler(
    _request: Request, exc: PipelineStageError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": exc.detail,
            "error_type": "pipeline_error",
            "stage": exc.stage,
        },
    )
