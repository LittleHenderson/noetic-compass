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
        request_id = getattr(request.state, "request_id", None)

        # Content-Length from request headers (may be absent for GET)
        content_length = request.headers.get("Content-Length")

        entry: dict = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "request_id": request_id,
            "user": user,
            "api_key": api_key,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
            "content_length": int(content_length) if content_length else None,
        }

        logger.info(json.dumps(entry))
        return response
