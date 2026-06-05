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
    accounts,
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

def _browser_managed_cors_credentials_allowed(
    origins: list[str], origin_regex: str
) -> bool:
    """Fail closed while auth uses Bearer headers and preview origins use regex."""
    # Starlette applies one credential flag to exact and regex-matched origins.
    # With a broad preview regex, no exact allowlist can safely turn browser
    # cookies, client certificates, or browser-managed HTTP auth back on.
    del origins, origin_regex
    return False



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import logging

    logger = logging.getLogger("noetic.startup")

    # Fail loud in production on the default JWT secret. With debug=False a real deployment
    # MUST set NC_JWT_SECRET; otherwise every issued token is signed with a public, known
    # secret and is trivially forgeable. Refuse to start rather than serve a forgeable auth.
    # (CAS Harness scoped-beta Phase 1 — see api/routes/auth.py and api/config.py.)
    if not settings.debug and settings.jwt_secret == "change-me-in-production":
        raise RuntimeError(
            "Refusing to start: NC_JWT_SECRET is still the default 'change-me-in-production' "
            "with debug=False. Set a real secret (NC_JWT_SECRET) before running in production."
        )

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

    # Durable account/invite store (PAID-user security spine — account half). Dark by default
    # (accounts_enabled off => None => /accounts/* return 503, /auth/token keeps the shared-secret
    # mint). When enabled, build_account_store selects the SAME durable backend as the state ledger
    # (Postgres when NC_DATABASE_URL set, else SQLite) and FAILS LOUD if no durable backend can be
    # built — account state is durable or absent, never silently in-memory.
    from api.services.accounts import build_account_store

    app.state.account_store = build_account_store(settings)
    if app.state.account_store is None:
        logger.info("accounts: dark (shared-secret mint only)")
    else:
        logger.info("accounts: ENABLED, durable account store installed")

    # Per-tenant usage quotas (PAID-user metering spine). Dark by default — the quota engine
    # (api/services/quotas.py) is INERT unless NC_QUOTAS_ENABLED is set, and even when set this PR
    # only ARMS the engine (route wiring is a separate change). Quotas are PER-ACCOUNT, so enabling
    # them without identity is a config error: there is no tenant to meter without accounts. Fail
    # loud rather than silently meter nothing. (Mirrors the accounts-half posture above; the engine
    # itself imports nothing from FastAPI and is exercised only by tests/test_quotas.py here.)
    if settings.quotas_enabled and not settings.accounts_enabled:
        raise RuntimeError(
            "Refusing to start: NC_QUOTAS_ENABLED=true requires NC_ACCOUNTS_ENABLED=true "
            "(quotas are per-account)."
        )
    if settings.quotas_enabled:
        logger.info("quotas: ENABLED, per-tenant monthly audit quota armed (route wiring pending)")
    else:
        logger.info("quotas: dark (engine inert, no metering)")

    # Durable session store (PAID-user security spine — session half). Shares the accounts_enabled
    # flag: a session is only meaningful once identity login is on. Dark by default
    # (accounts_enabled off => None => no jti is embedded and the dispatch middleware does no session
    # lookup, so legacy no-jti tokens flow byte-for-byte as today). When enabled, build_session_store
    # selects the SAME durable backend as the state ledger and FAILS LOUD if no durable backend can
    # be built — session state is durable or absent (a forgetful session store would silently log
    # every user out on redeploy AND make a revoked session forgettable).
    from api.services.sessions import build_session_store

    app.state.session_store = build_session_store(settings)
    if app.state.session_store is None:
        logger.info("sessions: dark (no session enforcement)")
    else:
        logger.info("sessions: ENABLED, durable session store installed")

    # CRM lead capture: build the service from settings and stash it for the routes. Dark by
    # default (in-memory store + null provider) unless NC_CRM_LEAD_STORE_PATH / NC_CRM_PROVIDER are
    # set. build_crm_service fails loud for a provider we have not implemented, so a misconfigured
    # CRM surfaces at startup rather than silently syncing nothing.
    from api.services.crm import build_crm_service, build_public_lead_abuse_guard

    app.state.crm = build_crm_service(settings)
    app.state.crm_public_abuse_guard = build_public_lead_abuse_guard(settings)
    _crm_store = type(app.state.crm.store).__name__
    _crm_provider = getattr(app.state.crm.provider, "provider_name", "unknown")
    _crm_abuse = app.state.crm_public_abuse_guard
    logger.info(
        "crm lead capture: store=%s provider=%s public_limit=%s/%ss",
        _crm_store,
        _crm_provider,
        _crm_abuse.max_submissions,
        _crm_abuse.window_seconds,
    )

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
# Browser-managed credentials stay disabled for every origin. Authentication
# uses explicit Bearer headers rather than cookies, and allow_headers below
# preserves Authorization after a successful preflight. This matters because
# Starlette uses one credential flag for both the exact allowlist and the broad
# Vercel preview regex; enabling credentials for the former would silently
# enable cookies, client certificates, and browser-managed HTTP auth for every
# regex-matched preview origin too.
allow_credentialed_cors = _browser_managed_cors_credentials_allowed(
    cors_origins, settings.cors_origin_regex
)
# Middleware — Starlette applies the LAST-added as the OUTERMOST layer.
# CORS is added last so browser-visible 401/429 responses carry CORS headers.
# Inside CORS: RequestId -> AuditLog -> JWTAuth -> RateLimit. AuditLog wraps
# JWTAuth so failed-auth (401) requests are still logged; previously
# it sat innermost and never saw auth rejections (credential-stuffing on
# /auth/token, forged-token probes) — a security-observability gap.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=allow_credentialed_cors,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(DialViolationError, dial_violation_handler)  # type: ignore[arg-type]
app.add_exception_handler(ScoringError, scoring_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(LLMError, llm_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(PipelineStageError, pipeline_stage_error_handler)  # type: ignore[arg-type]

# Routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(accounts.router)
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
