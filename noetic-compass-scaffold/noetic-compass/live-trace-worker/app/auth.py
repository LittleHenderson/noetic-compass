"""Optional shared-secret middleware for the live-trace worker."""

from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

WORKER_TOKEN_ENV = "ATLAS_LIVE_WORKER_TOKEN"
WORKER_TOKEN_HEADER = "X-Atlas-Worker-Token"
EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/health/realmode"})


def _configured_token() -> str:
    return os.environ.get(WORKER_TOKEN_ENV, "").strip()


def auth_enabled() -> bool:
    return bool(_configured_token())


def _token_ok(presented: str | None, expected: str) -> bool:
    if not presented:
        return False
    return hmac.compare_digest(presented.strip(), expected)


class WorkerTokenMiddleware(BaseHTTPMiddleware):
    """Require X-Atlas-Worker-Token when ATLAS_LIVE_WORKER_TOKEN is set.

    The middleware is a no-op by default, which preserves local dev and CI.
    Health paths stay public so RunPod and the API can probe worker readiness.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        expected = _configured_token()
        if not expected or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        if not _token_ok(request.headers.get(WORKER_TOKEN_HEADER), expected):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing or invalid Atlas worker token",
                    "header": WORKER_TOKEN_HEADER,
                },
            )
        return await call_next(request)
