"""In-memory tiered token bucket rate limiter (per API key)."""

from __future__ import annotations

import hashlib
import re
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import settings
from api.middleware.auth import is_public_path

# Tier definitions: (requests_per_minute, monthly_limit)
# monthly_limit=0 means unlimited
TIER_LIMITS: dict[str, tuple[int, int]] = {
    "community": (10, 50),
    "professional": (30, 500),
    "enterprise": (120, 0),
}
DASHBOARD_API_KEY_PREFIX = "dashboard:"
_ANONYMOUS_EVIDENCE_SHARE_PATTERN = re.compile(
    r"^/evidence/shared/(?P<share_id>shr_[A-Za-z0-9_-]{20,64})$"
)
_EVIDENCE_SHARE_CLIENT_RPM = 120
_EVIDENCE_SHARE_CLIENT_AND_SHARE_RPM = 60


class TokenBucket:
    """Simple token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class MonthlyCounter:
    """Tracks monthly usage per API key."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.month: int = time.gmtime().tm_mon

    def increment(self, key: str) -> int:
        current_month = time.gmtime().tm_mon
        if current_month != self.month:
            self.counts.clear()
            self.month = current_month
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def get_count(self, key: str) -> int:
        return self.counts.get(key, 0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-API-key tiered rate limiting using token bucket + monthly cap."""

    def __init__(self, app, rpm: int | None = None):  # type: ignore[no-untyped-def]
        super().__init__(app)
        tier = settings.rate_limit_tier.lower()
        tier_rpm, self.monthly_limit = TIER_LIMITS.get(tier, TIER_LIMITS["community"])
        self.rpm = rpm or settings.rate_limit_rpm
        self.buckets: dict[str, TokenBucket] = {}
        self.monthly = MonthlyCounter()
        self.sensitive_buckets: dict[str, TokenBucket] = {}
        self.sensitive_rpm = 60

    def _get_bucket(self, key: str) -> TokenBucket:
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                rate=self.rpm / 60.0,
                capacity=self.rpm,
            )
        return self.buckets[key]

    def _consume_sensitive_bucket(self, *, key: str, rpm: int) -> bool:
        bucket = self.sensitive_buckets.get(key)
        if bucket is None:
            if len(self.sensitive_buckets) >= 10_000:
                self.sensitive_buckets.pop(next(iter(self.sensitive_buckets)))
            bucket = TokenBucket(rate=rpm / 60.0, capacity=rpm)
            self.sensitive_buckets[key] = bucket
        return bucket.consume()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.method == "OPTIONS":
            return await call_next(request)
        client_host = request.client.host if request.client is not None else "unknown"
        share_match = _ANONYMOUS_EVIDENCE_SHARE_PATTERN.fullmatch(request.url.path)
        if share_match is not None:
            # The bearer token is intentionally never part of a limiter key. A
            # client-wide bucket stops path cycling; a second, hashed-share
            # bucket limits repeated valid S3 reads without retaining a public
            # share identifier in middleware state.
            share_digest = hashlib.sha256(
                share_match.group("share_id").encode("ascii")
            ).hexdigest()[:24]
            allowed = self._consume_sensitive_bucket(
                key=f"evidence-share-client:{client_host}",
                rpm=_EVIDENCE_SHARE_CLIENT_RPM,
            )
            if allowed:
                allowed = self._consume_sensitive_bucket(
                    key=f"evidence-share:{client_host}:{share_digest}",
                    rpm=_EVIDENCE_SHARE_CLIENT_AND_SHARE_RPM,
                )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded (evidence share)"},
                    headers={
                        "Cache-Control": "no-store, max-age=0",
                        "Pragma": "no-cache",
                    },
                )
            return await call_next(request)
        sensitive_public = {
            "/auth/token": self.sensitive_rpm,
            "/accounts/bootstrap": self.sensitive_rpm,
            "/accounts/invite/redeem": self.sensitive_rpm,
            "/platform/tenants": self.sensitive_rpm,
            "/platform/billing/manual-comped-subscription": self.sensitive_rpm,
            # Signed provider deliveries can legitimately burst at renewal time,
            # but malformed-signature floods must not bypass all throttling.
            "/billing/webhook/stripe": 600,
        }
        if request.url.path in sensitive_public:
            key = f"{request.url.path}:{client_host}"
            if not self._consume_sensitive_bucket(
                key=key, rpm=sensitive_public[request.url.path]
            ):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded (credential endpoint)"},
                )
            return await call_next(request)
        if is_public_path(request.url.path):
            return await call_next(request)

        api_key = getattr(request.state, "api_key", "default")

        # Per-minute rate limit
        bucket = self._get_bucket(api_key)
        if not bucket.consume():
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded (per-minute)"},
            )

        # Monthly cap (0 = unlimited). Dashboard login tokens represent the
        # interactive app session, not a metered external API key; keep the
        # per-minute throttle above but do not let local/stakeholder demos
        # strand the compiler UI behind the community monthly cap.
        unmetered_interactive = api_key.startswith((DASHBOARD_API_KEY_PREFIX, "account:"))
        monthly_limit = 0 if unmetered_interactive else self.monthly_limit
        if monthly_limit > 0:
            count = self.monthly.increment(api_key)
            if count > monthly_limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Monthly limit exceeded ({monthly_limit} assessments). "
                        f"Upgrade tier or wait until next month.",
                    },
                )

        return await call_next(request)
