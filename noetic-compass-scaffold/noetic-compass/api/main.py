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
    billing,
    cas_harness_audit,
    cas_harness_live_worker_health,
    cohort,
    config,
    crm,
    evidence,
    evidence_shares,
    export,
    forecast,
    health,
    idea_atlas,
    mode7,
    notation,
    platform_accounts,
    reproducibility,
    scenarios,
    state_ledger_status,
    support,
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
    """Own one durable backend and share it across every account-mode service."""
    import logging

    from api.db import close_db, init_db
    from api.services.accounts import build_account_store
    from api.services.sessions import build_session_store
    from api.services.cas_harness_audit_sessions import configure_audit_session_store
    from api.services.cas_harness_evidence_object_store import (
        build_s3_evidence_packet_repository,
        configure_evidence_packet_repository,
    )
    from api.state_ledger_bootstrap import (
        _build_state_store,
        install_state_ledger,
        teardown_state_ledger,
    )

    logger = logging.getLogger("noetic.startup")
    app.state.state_ledger = None
    app.state.shared_state_store = None
    app.state.account_store = None
    app.state.session_store = None
    app.state.billing_entitlement_store = None
    app.state.billing_provider = None
    app.state.evidence_packet_repository = None
    app.state.evidence_share_service = None
    app.state.support_tickets = None
    app.state.support_public_abuse_guard = None
    configure_evidence_packet_repository(None)

    if (not settings.debug or settings.accounts_enabled) and (
        settings.jwt_secret == "change-me-in-production"
    ):
        raise RuntimeError(
            "Refusing to start: NC_JWT_SECRET is still change-me-in-production."
        )
    settings.validate_object_lock_receipt_attestation()
    settings.validate_account_storage()
    if settings.quotas_enabled and not settings.accounts_enabled:
        raise RuntimeError(
            "NC_QUOTAS_ENABLED=true requires NC_ACCOUNTS_ENABLED=true."
        )
    if settings.evidence_packet_object_store_enabled and not settings.accounts_enabled:
        raise RuntimeError(
            "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true requires "
            "NC_ACCOUNTS_ENABLED=true."
        )

    handle = None
    owned_state_store = None
    database_started = False
    try:
        try:
            import cas_engine  # noqa: F401

            logger.info("cas_engine loaded successfully")
        except ImportError:
            logger.warning("cas_engine not available - running without Rust scoring engine")

        database_started = True
        await init_db()
        handle = install_state_ledger(settings)
        app.state.state_ledger = handle
        shared_store = handle.store if handle is not None else None
        if settings.accounts_enabled and shared_store is None:
            owned_state_store = _build_state_store(settings)
            shared_store = owned_state_store
        app.state.shared_state_store = shared_store

        if settings.evidence_packet_object_store_enabled:
            if shared_store is None:
                raise RuntimeError(
                    "Shared Evidence Packet storage requires a durable StateStore."
                )
            app.state.evidence_packet_repository = build_s3_evidence_packet_repository(
                shared_store
            )
            configure_evidence_packet_repository(app.state.evidence_packet_repository)

        if settings.evidence_shares_enabled:
            if shared_store is None or app.state.evidence_packet_repository is None:
                raise RuntimeError(
                    "Evidence Packet sharing requires durable state and immutable packet storage."
                )
            from api.services.evidence_shares import EvidenceShareService

            app.state.evidence_share_service = EvidenceShareService(
                store=shared_store,
                repository=app.state.evidence_packet_repository,
                token_pepper=settings.evidence_share_token_pepper,
            )

        configure_audit_session_store(
            shared_store if settings.accounts_enabled else None
        )
        app.state.account_store = build_account_store(settings, store=shared_store)
        app.state.session_store = build_session_store(settings, store=shared_store)
        if settings.billing_entitlements_enabled:
            if shared_store is None:
                raise RuntimeError(
                    "Billing entitlements require the shared durable state store."
                )
            from api.services.billing_entitlements import BillingEntitlementStore
            from api.services.stripe_billing import build_billing_provider

            app.state.billing_entitlement_store = BillingEntitlementStore(shared_store)
            app.state.billing_provider = build_billing_provider(settings)
        if (
            app.state.account_store is not None
            and not app.state.account_store.has_active_owner()
            and not settings.account_bootstrap_secret
        ):
            raise RuntimeError(
                "Account mode has no owner; set NC_ACCOUNT_BOOTSTRAP_SECRET for first startup."
            )


        if handle is None:
            logger.info("state ledger: dark (dict-authoritative)")
        elif handle.read_authority:
            logger.info("state ledger: ENABLED, LEDGER READ-AUTHORITATIVE")
        else:
            logger.info("state ledger: ENABLED, dual-write shadow")
        logger.info(
            "accounts: %s",
            "ENABLED" if app.state.account_store is not None else "dark",
        )
        logger.info(
            "quotas: %s", "ENABLED" if settings.quotas_enabled else "dark"
        )
        logger.info(
            "billing entitlements: %s (provider=%s)",
            "ENABLED" if settings.billing_entitlements_enabled else "dark",
            settings.billing_provider.strip().lower(),
        )
        logger.info(
            "evidence packet object storage: %s",
            "ENABLED" if app.state.evidence_packet_repository is not None else "dark",
        )
        logger.info(
            "evidence packet sharing: %s",
            "ENABLED" if app.state.evidence_share_service is not None else "dark",
        )

        from api.services.crm import build_crm_service, build_public_lead_abuse_guard

        app.state.crm = build_crm_service(settings)
        app.state.crm_public_abuse_guard = build_public_lead_abuse_guard(settings)
        from api.services.crm.abuse import PublicLeadAbuseGuard
        from api.services.support_tickets import build_support_ticket_service

        app.state.support_tickets = build_support_ticket_service(settings)
        app.state.support_public_abuse_guard = PublicLeadAbuseGuard(
            max_submissions=settings.support_public_ticket_rate_limit_max,
            window_seconds=settings.support_public_ticket_rate_limit_window_seconds,
        )
        yield
    finally:
        # Clear wrappers before closing their shared backend so a repeated lifespan cannot reuse
        configure_audit_session_store(None)
        configure_evidence_packet_repository(None)
        # a stale closed store after either normal shutdown or partial startup failure.
        app.state.account_store = None
        app.state.session_store = None
        app.state.billing_entitlement_store = None
        app.state.billing_provider = None
        app.state.evidence_packet_repository = None
        app.state.evidence_share_service = None
        app.state.shared_state_store = None
        app.state.support_tickets = None
        app.state.support_public_abuse_guard = None
        try:
            if handle is not None:
                teardown_state_ledger(handle)
            elif owned_state_store is not None:
                owned_state_store.close()
        finally:
            app.state.state_ledger = None
            if database_started:
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
app.include_router(platform_accounts.router)
app.include_router(billing.router)
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
app.include_router(evidence_shares.router)
app.include_router(atlas_live.router)
app.include_router(visual_grounding.router)
app.include_router(state_ledger_status.router)
app.include_router(crm.router)
app.include_router(support.router)
