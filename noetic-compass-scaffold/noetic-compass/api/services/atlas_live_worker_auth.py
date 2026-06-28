"""Shared-secret header helper for API -> Atlas live worker calls."""

from __future__ import annotations

from api.config import settings

WORKER_TOKEN_HEADER = "X-Atlas-Worker-Token"


def atlas_worker_auth_headers() -> dict[str, str]:
    """Return worker auth headers, or no headers when the token is unset.

    Empty-token behavior is deliberate: local dev, CI, and the older SSH-tunnel
    setup keep working. Production should set the same token on the API and
    worker so exposed worker routes only accept calls from the API.
    """
    token = settings.atlas_live_worker_token.strip()
    if not token:
        return {}
    return {WORKER_TOKEN_HEADER: token}
