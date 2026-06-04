"""Shared API-side auth header for the Atlas live worker.

The worker's own auth shim is optional and controlled by
``ATLAS_LIVE_WORKER_TOKEN``. When production sets that token on the worker, the
API must send the same value on every non-health worker request. Empty token
keeps local/dev behavior unchanged.
"""

from __future__ import annotations

from api.config import settings


ATLAS_WORKER_TOKEN_HEADER = "X-Atlas-Worker-Token"


def atlas_worker_auth_headers() -> dict[str, str]:
    """Return the worker shared-secret header, or no headers when unset."""

    token = settings.atlas_live_worker_token.strip()
    if not token:
        return {}
    return {ATLAS_WORKER_TOKEN_HEADER: token}
