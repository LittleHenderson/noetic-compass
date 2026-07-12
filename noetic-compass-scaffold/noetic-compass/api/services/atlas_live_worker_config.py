"""Fail-closed connection policy for the hosted Atlas live worker.

An empty worker URL keeps the live path dark. A tokenless worker is allowed
only on the local loopback interface for developer use; every remote target
must have the shared service token configured before the API will contact it.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from urllib.parse import urlsplit

from api.config import settings


WORKER_CONFIG_NOT_CONFIGURED = "not_configured"
WORKER_CONFIG_INVALID_URL = "invalid_worker_url"
WORKER_CONFIG_TOKEN_REQUIRED = "worker_token_required"


@dataclass(frozen=True)
class AtlasWorkerTarget:
    """Validated worker target used by every API-side worker caller."""

    configured: bool
    allowed: bool
    base_url: str = ""
    error: str | None = None


def _is_loopback_host(hostname: str) -> bool:
    normalized = hostname.strip().rstrip(".").lower()
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def atlas_worker_target() -> AtlasWorkerTarget:
    """Return the current worker target after applying the security policy.

    Local ``localhost``/loopback HTTP remains convenient and tokenless. Any
    remote hostname or non-loopback IP requires ``ATLAS_LIVE_WORKER_TOKEN``.
    This makes a stale or half-configured public endpoint unavailable instead
    of silently sending prompts to an unauthenticated service.
    """

    base_url = settings.atlas_live_worker_url.strip().rstrip("/")
    if not base_url:
        return AtlasWorkerTarget(
            configured=False,
            allowed=False,
            error=WORKER_CONFIG_NOT_CONFIGURED,
        )

    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
    except ValueError:
        parsed = None
        hostname = None
    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return AtlasWorkerTarget(
            configured=True,
            allowed=False,
            base_url=base_url,
            error=WORKER_CONFIG_INVALID_URL,
        )

    token = settings.atlas_live_worker_token.strip()
    if not token and not _is_loopback_host(hostname):
        return AtlasWorkerTarget(
            configured=True,
            allowed=False,
            base_url=base_url,
            error=WORKER_CONFIG_TOKEN_REQUIRED,
        )

    return AtlasWorkerTarget(configured=True, allowed=True, base_url=base_url)
