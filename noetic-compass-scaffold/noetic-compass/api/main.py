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
from api.middleware.request_id import RequestIdMiddleware
from api.routes import (
    assess,
    auth,
    batch,
    benchmark,
    cas_harness_audit,
    cas_harness_live_worker_health,
    cohort,
    config,
    crm,
    evidence,
    export,
    forecast,
    health,
    idea_atlas,
    mode7,
    notation,
    reproducibility,
    scenarios,
    state_ledger_status,
    validation,
    atlas_live,
    visual_grounding,
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
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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

    # Durable state ledger: dark by default (no mirror installed) unless an operator sets
    # NC_STATE_LEDGER_ENABLED. All logic lives in the bootstrap module; the lifespan only
    # installs, stashes the handle for shutdown, and logs the honest serving posture.
    from api.state_ledger_bootstrap import install_state_ledger, teardown_state_ledger

    handle = install_state_ledger(settings)
    app.state.state_ledger = handle
    if handle is None:
        logger.info("state ledger: dark (dict-authoritative)")
    elif handle.read_authority:
        logger.info("state ledger: ENABLED, LEDGER READ-AUTHORITATIVE")
    else:
        logger.info("state ledger: ENABLED, dual-write+shadow, dict-authoritative")

    # CRM lead capture: build the service from settings and stash it for the routes. Dark by
    # default (in-memory store + null provider) unless NC_CRM_LEAD_STORE_PATH / NC_CRM_PROVIDER are
    # set. build_crm_service fails loud for a provider we have not implemented, so a misconfigured
    # CRM surfaces at startup rather than silently syncing nothing.
    from api.services.crm import build_crm_service

    app.state.crm = build_crm_service(settings)
    _crm_store = type(app.state.crm.store).__name__
    _crm_provider = getattr(app.state.crm.provider, "provider_name", "unknown")
    logger.info("crm lead capture: store=%s provider=%s", _crm_store, _crm_provider)

    yield

    # Shutdown: uninstall the ledger mirror (returns to dark) and close the database pool.
    teardown_state_ledger(handle)
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

# Routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(assess.router)
app.include_router(wrap.router)
app.include_router(batch.router)
app.include_router(benchmark.router)
app.include_router(cas_harness_audit.router)
app.include_router(cas_harness_live_worker_health.router)
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
app.include_router(atlas_live.router)
app.include_router(visual_grounding.router)
app.include_router(state_ledger_status.router)
app.include_router(crm.router)
