"""Structured JSON audit logging middleware."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("noetic.audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Logs structured JSON audit entries for all API requests."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        user = getattr(request.state, "user", "anonymous")
        api_key = getattr(request.state, "api_key", "default")

        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "user": user,
            "api_key": api_key,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
        }

        logger.info(json.dumps(entry))
        return response
