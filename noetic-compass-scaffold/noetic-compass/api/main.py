"""Noetic Compass API — FastAPI application."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.errors import (
    DialViolationError,
    GenerationReadinessSuppression,
    LLMError,
    PipelineStageError,
    ScoringError,
    dial_violation_handler,
    generation_readiness_suppression_handler,
    llm_error_handler,
    pipeline_stage_error_handler,
    scoring_error_handler,
)
from api.middleware.auth import JWTAuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.audit import AuditLogMiddleware
from api.middleware.request_id import RequestIdMiddleware
from api.routes import (
    assess,
    auth,
    batch,
    benchmark,
    cohort,
    config,
    evidence,
    export,
    forecast,
    harness_evidence,
    health,
    idea_atlas,
    mode7,
    notation,
    reproducibility,
    scenarios,
    validation,
    wrap,
)


def _parse_cors_origins(raw: str) -> list[str]:
    """Parse comma-separated CORS origins from settings.

    Returns ["*"] for wildcard, otherwise a trimmed list of origins.
    """
    stripped = raw.strip()
    if stripped == "*":
        return ["*"]
    return [origin.strip() for origin in stripped.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    import logging

    logger = logging.getLogger("noetic.startup")

    # Startup: verify cas_engine is importable (non-fatal if missing)
    try:
        import cas_engine  # noqa: F401

        logger.info("cas_engine loaded successfully")
    except ImportError:
        logger.warning("cas_engine not available — running without Rust scoring engine")

    # Initialise database (no-op when DATABASE_URL is unset)
    from api.db import init_db, close_db

    await init_db()

    yield

    # Shutdown: close database connection pool
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — configured via NC_CORS_ORIGINS env var (default "*")
# Regex matches every Vercel deployment alias (preview, team-scoped, canonical)
# so stakeholder demos never hit "Failed to fetch" when Vercel rotates the URL.
cors_origins = _parse_cors_origins(settings.cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware (order matters: outermost first)
# RequestIdMiddleware runs first (outermost) so request_id is available to all others
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RequestIdMiddleware)

# Exception handlers
app.add_exception_handler(DialViolationError, dial_violation_handler)  # type: ignore[arg-type]
app.add_exception_handler(ScoringError, scoring_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(LLMError, llm_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(PipelineStageError, pipeline_stage_error_handler)  # type: ignore[arg-type]
# Stage 20 Generation Readiness Gate "suppress" decisions surface as
# HTTP 422 — a deliberate policy refusal, not a server error.
app.add_exception_handler(
    GenerationReadinessSuppression,
    generation_readiness_suppression_handler,  # type: ignore[arg-type]
)

# Routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(assess.router)
app.include_router(wrap.router)
app.include_router(batch.router)
app.include_router(benchmark.router)
app.include_router(cohort.router)
app.include_router(config.router)
app.include_router(export.router)
app.include_router(forecast.router)
app.include_router(scenarios.router)
app.include_router(validation.router)
app.include_router(notation.router)
app.include_router(reproducibility.router)
app.include_router(idea_atlas.router)
app.include_router(mode7.router)
app.include_router(evidence.router)
app.include_router(harness_evidence.router)
