"""Request ID tracking middleware.

Generates a UUID for each request if X-Request-ID header is not present.
Passes through existing X-Request-ID if provided.
Attaches to request.state.request_id and includes in response headers.
"""

from __future__ import annotations

import re
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


_ANONYMOUS_EVIDENCE_SHARE_PATTERN = re.compile(
    r"^/evidence/shared/shr_[A-Za-z0-9_-]{20,64}$"
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a unique tracking ID."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Anonymous share credentials live in X-Evidence-Share-Token. Always
        # mint the request id for that endpoint so a caller cannot accidentally
        # copy the bearer token into X-Request-ID and make the audit middleware
        # persist it as a trace field (including on a pre-route 429 response).
        if _ANONYMOUS_EVIDENCE_SHARE_PATTERN.fullmatch(request.url.path):
            request_id = str(uuid.uuid4())
        else:
            # Preserve the existing pass-through contract everywhere else.
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Attach to request state for downstream access (audit, logging)
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # Include in response headers for client-side correlation
        response.headers["X-Request-ID"] = request_id

        return response
