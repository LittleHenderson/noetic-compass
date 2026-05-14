"""In-memory tiered token bucket rate limiter (per API key)."""

from __future__ import annotations

import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import settings
from api.middleware.auth import PUBLIC_PATHS

# Tier definitions: (requests_per_minute, monthly_limit)
# monthly_limit=0 means unlimited
TIER_LIMITS: dict[str, tuple[int, int]] = {
    "community": (10, 50),
    "professional": (30, 500),
    "enterprise": (120, 0),
}
DASHBOARD_API_KEY_PREFIX = "dashboard:"


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

    def _get_bucket(self, key: str) -> TokenBucket:
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                rate=self.rpm / 60.0,
                capacity=self.rpm,
            )
        return self.buckets[key]

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
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
        monthly_limit = 0 if api_key.startswith(DASHBOARD_API_KEY_PREFIX) else self.monthly_limit
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
