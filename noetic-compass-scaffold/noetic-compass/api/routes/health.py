"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()


@router.get("/health/db")
async def health_db() -> JSONResponse:
    """Check database connectivity. Returns 200 or 503."""
    from api.db import check_db

    healthy = await check_db()
    if healthy:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": "connected"},
        )
    return JSONResponse(
        status_code=503,
        content={"status": "unavailable", "database": "disconnected"},
    )


@router.get("/deployment")
async def deployment_identity() -> JSONResponse:
    """Report which exact artifact, build, and commit this process is running.

    This is the AWS analogue of asking the platform which deploy is live. Render injected a
    ``RENDER_SERVICE_ID`` and exposed a ``dep-`` deploy id through its API; AWS injects
    neither, so the deployment writes these identifiers into the environment and the process
    reports them back. The root-CI deploy evidence collector reads this endpoint and compares
    it with the registry digest and the build record, so a mismatch between what CI signed off
    and what is actually serving traffic is detectable rather than assumed.

    Only identifiers are returned. No credential, URL, bucket, or key material is read here,
    and every absent value is reported as ``null`` so a caller fails closed instead of
    guessing at a default.
    """
    import os

    fields = {
        "provider": "NC_DEPLOYMENT_PROVIDER",
        "service_id": "NC_DEPLOYMENT_SERVICE_ID",
        "service_name": "NC_DEPLOYMENT_SERVICE_NAME",
        "image_digest": "NC_DEPLOYMENT_IMAGE_DIGEST",
        "build_id": "NC_DEPLOYMENT_BUILD_ID",
        "commit_sha": "NC_BUILD_COMMIT_SHA",
        "region": "NC_DEPLOYMENT_REGION",
    }
    reported = {name: (os.environ.get(var) or None) for name, var in fields.items()}
    reported["configured"] = all(
        reported[name] is not None
        for name in ("provider", "service_id", "image_digest", "commit_sha")
    )
    return JSONResponse(status_code=200, headers={"Cache-Control": "no-store"}, content=reported)


@router.get("/health/ready")
async def health_ready() -> JSONResponse:
    """Readiness probe: return 200 only when load-bearing systems are healthy.

    ``/health`` remains a cheap process-liveness signal.  This endpoint also
    checks any configured live worker and S3 Object-Lock authority, using
    metadata-only probes with a short internal cache.
    """
    from api.db import check_db
    from api.services.production_dependency_readiness import (
        get_production_dependency_readiness,
    )

    checks: dict[str, dict] = {}
    all_healthy = True

    # 1. API check (always ok if we can serve this request)
    checks["api"] = {"status": "ok"}

    # 2. CAS engine check
    try:
        import cas_engine  # noqa: F401

        checks["cas_engine"] = {"status": "ok"}
    except Exception:
        checks["cas_engine"] = {"status": "error", "detail": "import_failed"}
        all_healthy = False

    # 3. Database check (only if configured)
    from api.config import settings

    if settings.database_url:
        db_ok = await check_db()
        if db_ok:
            checks["database"] = {"status": "ok"}
        else:
            checks["database"] = {"status": "error", "detail": "unreachable"}
            all_healthy = False
    else:
        checks["database"] = {"status": "not_configured"}

    # 4. Configured production dependencies.  Fail closed but never expose
    # provider exception text, URLs, bucket names, or credential material.
    dependency_checked_at = None
    dependency_cache_ttl_seconds = None
    try:
        dependencies = await get_production_dependency_readiness()
        checks.update(dependencies["checks"])
        dependency_checked_at = dependencies.get("checked_at")
        dependency_cache_ttl_seconds = dependencies.get("cache_ttl_seconds")
        if dependencies.get("ready") is not True:
            all_healthy = False
    except Exception:
        checks["production_dependencies"] = {
            "status": "error",
            "required": True,
            "reason": "readiness_check_failed",
        }
        all_healthy = False

    status_code = 200 if all_healthy else 503
    return JSONResponse(
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
        content={
            "status": "ok" if all_healthy else "degraded",
            "ready": all_healthy,
            "dependency_checked_at": dependency_checked_at,
            "dependency_cache_ttl_seconds": dependency_cache_ttl_seconds,
            "checks": checks,
        },
    )
