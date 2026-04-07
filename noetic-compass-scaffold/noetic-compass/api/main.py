"""Noetic Compass API — FastAPI application."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.errors import (
    DialViolationError,
    LLMError,
    PipelineStageError,
    ScoringError,
    dial_violation_handler,
    llm_error_handler,
    pipeline_stage_error_handler,
    scoring_error_handler,
)
from api.middleware.auth import JWTAuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.audit import AuditLogMiddleware
from api.routes import assess, auth, batch, cohort, config, export, health, wrap


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup: verify cas_engine is importable
    import cas_engine  # noqa: F401

    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware (order matters: outermost first)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)

# Exception handlers
app.add_exception_handler(DialViolationError, dial_violation_handler)  # type: ignore[arg-type]
app.add_exception_handler(ScoringError, scoring_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(LLMError, llm_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(PipelineStageError, pipeline_stage_error_handler)  # type: ignore[arg-type]

# Routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(assess.router)
app.include_router(wrap.router)
app.include_router(batch.router)
app.include_router(cohort.router)
app.include_router(config.router)
app.include_router(export.router)
