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


@router.get("/health/ready")
async def health_ready() -> JSONResponse:
    """Readiness probe: returns 200 only if ALL subsystems are healthy."""
    from api.db import check_db

    checks: dict[str, dict] = {}
    all_healthy = True

    # 1. API check (always ok if we can serve this request)
    checks["api"] = {"status": "ok"}

    # 2. CAS engine check
    try:
        import cas_engine  # noqa: F401

        checks["cas_engine"] = {"status": "ok"}
    except Exception as exc:
        checks["cas_engine"] = {"status": "error", "detail": str(exc)}
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

    status_code = 200 if all_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if all_healthy else "degraded",
            "checks": checks,
        },
    )
