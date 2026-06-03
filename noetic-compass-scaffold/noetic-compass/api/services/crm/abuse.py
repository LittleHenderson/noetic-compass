"""Public lead-capture anti-abuse guard.

The CRM public endpoint is intentionally anonymous, so it is exempt from the API-key rate limiter.
This module provides the narrow protection that endpoint needs before broad public launch:

* a honeypot field that refuses obvious bot submissions before they are persisted;
* a small per-client sliding-window limiter that slows repeated anonymous submissions.

Honesty boundary: this is an in-process guard, not a WAF and not distributed abuse prevention. It
reduces accidental/spam load on one app process. Real public launch still needs edge-level controls.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
import time


class LeadAbuseRejected(ValueError):
    """Raised when a public lead submission is rejected before capture."""


class PublicLeadRateLimitExceeded(LeadAbuseRejected):
    """Raised when an anonymous client exceeds the public lead-capture limit."""

    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("public lead capture rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class PublicLeadAbuseDecision:
    """Traceable anti-abuse decision for route handling and tests."""

    allowed: bool
    reason: str = ""
    retry_after_seconds: int = 0


class PublicLeadAbuseGuard:
    """In-process honeypot + sliding-window rate limiter for anonymous lead capture."""

    def __init__(
        self,
        *,
        max_submissions: int,
        window_seconds: int,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_submissions = max(0, int(max_submissions))
        self.window_seconds = max(0, int(window_seconds))
        self._now = now
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, *, client_key: str, honeypot_value: str) -> PublicLeadAbuseDecision:
        """Return an allow/reject decision without mutating CRM lead state."""
        if honeypot_value.strip():
            return PublicLeadAbuseDecision(allowed=False, reason="honeypot")
        if self.max_submissions <= 0 or self.window_seconds <= 0:
            return PublicLeadAbuseDecision(allowed=True)

        now = self._now()
        cutoff = now - self.window_seconds
        key = client_key or "unknown"
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_submissions:
                retry_after = max(1, int(round((hits[0] + self.window_seconds) - now)))
                return PublicLeadAbuseDecision(
                    allowed=False,
                    reason="rate_limit",
                    retry_after_seconds=retry_after,
                )
            hits.append(now)
        return PublicLeadAbuseDecision(allowed=True)

    def reset(self) -> None:
        """Clear in-memory counters. Used by tests and process-local operator resets."""
        with self._lock:
            self._hits.clear()


def build_public_lead_abuse_guard(settings) -> PublicLeadAbuseGuard:
    """Construct the configured public lead anti-abuse guard."""
    return PublicLeadAbuseGuard(
        max_submissions=getattr(settings, "crm_public_lead_rate_limit_max", 5),
        window_seconds=getattr(settings, "crm_public_lead_rate_limit_window_seconds", 3600),
    )
