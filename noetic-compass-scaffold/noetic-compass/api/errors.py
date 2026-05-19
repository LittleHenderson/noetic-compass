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


class GenerationReadinessSuppression(Exception):
    """Raised when the Stage 20 Generation Readiness Gate decides to suppress
    customer-facing emission.

    This is a *deliberate refusal*, not an error. The Wrap Pipeline runner
    raises this when the gate returns the ``suppress`` action so the Output
    Gate companion can surface the decision through an HTTP 422 (Unprocessable
    Entity) rather than the 500 path used for genuine pipeline errors.

    The serialized ``GenerationReadinessResult.as_dict()`` is attached as
    ``result`` for the handler to surface in the response body.
    """

    def __init__(self, result: dict):
        self.result = result


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


async def generation_readiness_suppression_handler(
    _request: Request, exc: GenerationReadinessSuppression
) -> JSONResponse:
    """Surface a Stage 20 suppress decision as HTTP 422.

    The body uses reserved policy language (caveat / constrain / suppress)
    rather than "rejected" or "failed"; the decision is a structured policy
    output, not an error. The full GenerationReadinessResult payload is
    included as ``reason`` so the client (and audit trail) can inspect the
    risk score, reasons, and recommended mode.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Generation suppressed by Stage 20 readiness gate.",
            "error_type": "generation_readiness_suppression",
            "gate_action": "suppress",
            "reason": exc.result,
        },
    )
