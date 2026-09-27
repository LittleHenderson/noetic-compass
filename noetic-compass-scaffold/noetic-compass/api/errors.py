"""Custom exceptions and FastAPI exception handlers."""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# Request fields whose submitted value must never be echoed back to the caller.
#
# FastAPI's default RequestValidationError response includes the offending ``input`` for every
# error, so a credential that fails validation is returned in the response body and lands in
# whatever records that response: proxies, browser devtools, error trackers, and the test
# transcripts of anyone debugging. This was observed live: a bootstrap attempt with a malformed
# credential came back with the credential in ``detail[0].input``.
#
# Only the echoed value is replaced. Validation itself is untouched: the same status code, the
# same error types, the same locations, so nothing is weakened and no client sees a different
# verdict than before.
SENSITIVE_VALIDATION_FIELDS = frozenset(
    {
        "api_credential",
        "api_key",
        "bootstrap_secret",
        "code",
        "credential",
        "invite_code",
        "mint_secret",
        "password",
        "secret",
        "token",
    }
)
REDACTED = "<redacted>"


def _redact_value(value: Any) -> Any:
    """Replace sensitive values anywhere inside a submitted input.

    The submitted input is often a nested object - an audit target carries an ``api_key`` beside
    its kind, for example - so redacting only when the field name itself looks sensitive would
    miss the credential inside. Nested keys are checked by name at every level.
    """
    if isinstance(value, dict):
        return {
            key: (REDACTED if str(key).lower() in SENSITIVE_VALIDATION_FIELDS else _redact_value(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def redacted_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Return this exception's errors with sensitive inputs replaced."""
    redacted: list[dict[str, Any]] = []
    for error in exc.errors():
        item: dict[str, Any] = dict(error)
        location = [str(part).lower() for part in item.get("loc", ())]
        if any(part in SENSITIVE_VALIDATION_FIELDS for part in location):
            item["input"] = REDACTED
        elif "input" in item:
            item["input"] = _redact_value(item["input"])
        redacted.append(item)
    return redacted


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 with the same detail as FastAPI's default, minus any credential value.

    ``jsonable_encoder`` is required, not cosmetic: the error context can hold the original
    exception object (``ctx: {"error": ValueError(...)}``) for validator failures, and returning
    that raw makes the response unserialisable. FastAPI's own handler encodes it the same way.
    """
    from fastapi.encoders import jsonable_encoder

    return JSONResponse(
        status_code=422, content={"detail": jsonable_encoder(redacted_validation_errors(exc))}
    )


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
