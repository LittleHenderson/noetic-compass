"""Optional app-level auth shim for the live-trace worker.

Why this exists
---------------
Until now the only thing keeping the worker private was transport: the API
reached it over an SSH tunnel and the pod exposed nothing but port 22. The
launch-grade plan (see
``docs/working/atlas_live_worker_launch_grade_exposure_2026_05_31.md``) replaces
that tunnel with an exposed HTTP port behind the RunPod proxy. An exposed port
is internet-reachable, so the worker must add an *app-level* check that the
caller is our API — the reachability gating the tunnel gave us for free.

Contract
--------
* Env var ``ATLAS_LIVE_WORKER_TOKEN``:
    - **unset / empty -> auth DISABLED** (default; dev, CI, local smoke, and the
      existing SSH-tunnel deployment are unaffected).
    - **set -> every request MUST send ``X-Atlas-Worker-Token: <token>``** or get
      HTTP 401, EXCEPT the exempt health paths below.
* Exempt paths: ``/health`` and ``/health/realmode``. RunPod health checks and
  the API's liveness / real-mode proxy must keep working without the shared
  secret. These endpoints expose no user data and run no inference.

This is a coarse "is this our API" gate (shared-secret bearer), deliberately
simple. It is NOT user identity (the API owns that) and NOT a replacement for
keeping the worker off the public browser path.
"""

from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

WORKER_TOKEN_ENV = "ATLAS_LIVE_WORKER_TOKEN"
WORKER_TOKEN_HEADER = "X-Atlas-Worker-Token"

# Health paths are always reachable without the token so platform health checks
# and the API real-mode proxy keep working. Keep this list tiny and explicit.
EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/health/realmode"})


def _configured_token() -> str:
    """Return the configured shared secret, or '' when auth is disabled.

    Read at request time (not import time) so tests and operators can toggle the
    env var without reconstructing the app.
    """
    return os.environ.get(WORKER_TOKEN_ENV, "").strip()


def auth_enabled() -> bool:
    """True when a non-empty ``ATLAS_LIVE_WORKER_TOKEN`` is configured."""
    return bool(_configured_token())


def _token_ok(presented: str | None, expected: str) -> bool:
    if not presented:
        return False
    # Constant-time compare to avoid leaking the secret via timing.
    return hmac.compare_digest(presented.strip(), expected)


class WorkerTokenMiddleware(BaseHTTPMiddleware):
    """Reject requests that lack a valid ``X-Atlas-Worker-Token`` when enabled.

    No-op (pass-through) whenever ``ATLAS_LIVE_WORKER_TOKEN`` is unset/empty, so
    the default developer and CI experience is unchanged.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        expected = _configured_token()
        if not expected:
            # Auth disabled — backward-compatible default.
            return await call_next(request)

        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        presented = request.headers.get(WORKER_TOKEN_HEADER)
        if not _token_ok(presented, expected):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing or invalid Atlas worker token",
                    "header": WORKER_TOKEN_HEADER,
                },
            )
        return await call_next(request)
