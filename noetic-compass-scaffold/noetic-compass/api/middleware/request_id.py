"""Request ID tracking middleware.

Generates a UUID for each request if X-Request-ID header is not present.
Passes through existing X-Request-ID if provided.
Attaches to request.state.request_id and includes in response headers.
"""

from __future__ import annotations

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a unique tracking ID."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Use incoming header or generate a new UUID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Attach to request state for downstream access (audit, logging)
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # Include in response headers for client-side correlation
        response.headers["X-Request-ID"] = request_id

        return response
