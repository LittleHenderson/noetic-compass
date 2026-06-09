"""Per-tenant usage-quota engine for paid CAS Harness accounts.

The module is deliberately route-agnostic: callers provide a tenant-scoped
StateStore, a tenant id, a period key, and a limit. Nothing here imports FastAPI
or settings. With ``NC_QUOTAS_ENABLED=false`` no route calls this code, so the
engine stays inert.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from api.services.production.state_substrate.interface import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

USAGE_COUNTER_KIND = "usage_counter"
DEFAULT_AUDITS_PER_MONTH = 100
_DEFAULT_SOURCE = "cas_harness_audit"
_MAX_RETRIES = 5


class QuotaExceeded(Exception):
    """A tenant reached its usage cap; the rejected unit was not consumed."""

    def __init__(self, tenant_id: str, limit: int, count: int) -> None:
        self.tenant_id = tenant_id
        self.limit = limit
        self.count = count
        super().__init__(
            f"quota exceeded for tenant {tenant_id!r}: count {count} >= limit {limit}"
        )


def get_quota_limit(plan_id: Optional[str] = None) -> int:
    """Return the monthly audit allowance for a plan.

    The account model has no subscription/plan record yet, so every tenant gets
    the same honest default. ``plan_id`` is accepted for the future shape.
    """
    return DEFAULT_AUDITS_PER_MONTH


def monthly_period_key(now: datetime) -> str:
    """Build the monthly audits counter key, e.g. ``audits:2026-06``."""
    return f"audits:{now.year:04d}-{now.month:02d}"


def current_monthly_period_key() -> str:
    """Return the current UTC monthly audits counter key."""
    return monthly_period_key(datetime.now(UTC))


def get_usage(store: StateStore, *, tenant_id: str, period_key: str) -> int:
    """Return current usage for ``tenant_id`` and ``period_key``; absent means 0."""
    record = store.get(tenant_id, USAGE_COUNTER_KIND, period_key)
    if record is None:
        return 0
    return int(record.payload.get("count", 0))


def increment_usage(
    store: StateStore,
    *,
    tenant_id: str,
    period_key: str,
    amount: int = 1,
    limit: int,
    source: str = _DEFAULT_SOURCE,
) -> int:
    """Increment usage and return the new count.

    This mechanical bump stores ``limit`` for traceability but does not enforce
    the cap. Use ``consume_quota`` for checked route metering.
    """
    last_conflict: Optional[VersionConflict] = None
    for _ in range(_MAX_RETRIES):
        existing = store.get(tenant_id, USAGE_COUNTER_KIND, period_key)
        if existing is None:
            new_count = amount
            record = LedgerRecord.new(
                tenant_id=tenant_id,
                kind=USAGE_COUNTER_KIND,
                record_id=period_key,
                payload={"count": new_count, "limit": limit, "period": period_key},
                source=source,
            )
            try:
                store.put(record, expected_version=0)
                return new_count
            except VersionConflict as conflict:
                last_conflict = conflict
                continue

        new_count = int(existing.payload.get("count", 0)) + amount
        updated = existing.with_payload(
            {"count": new_count, "limit": limit, "period": period_key}
        )
        try:
            store.put(updated, expected_version=existing.version)
            return new_count
        except VersionConflict as conflict:
            last_conflict = conflict
            continue

    assert last_conflict is not None
    raise last_conflict


def consume_quota(
    store: StateStore,
    *,
    tenant_id: str,
    period_key: str,
    limit: int,
    source: str = _DEFAULT_SOURCE,
) -> int:
    """Consume one audit unit or raise ``QuotaExceeded`` without incrementing.

    The limit check is repeated after every optimistic-concurrency conflict, so
    concurrent callers cannot slip the count past the cap.
    """
    last_conflict: Optional[VersionConflict] = None
    for _ in range(_MAX_RETRIES):
        existing = store.get(tenant_id, USAGE_COUNTER_KIND, period_key)
        current = 0 if existing is None else int(existing.payload.get("count", 0))

        if current >= limit:
            raise QuotaExceeded(tenant_id=tenant_id, limit=limit, count=current)

        new_count = current + 1
        if existing is None:
            record = LedgerRecord.new(
                tenant_id=tenant_id,
                kind=USAGE_COUNTER_KIND,
                record_id=period_key,
                payload={"count": new_count, "limit": limit, "period": period_key},
                source=source,
            )
            try:
                store.put(record, expected_version=0)
                return new_count
            except VersionConflict as conflict:
                last_conflict = conflict
                continue

        updated = existing.with_payload(
            {"count": new_count, "limit": limit, "period": period_key}
        )
        try:
            store.put(updated, expected_version=existing.version)
            return new_count
        except VersionConflict as conflict:
            last_conflict = conflict
            continue

    assert last_conflict is not None
    raise last_conflict


__all__ = [
    "USAGE_COUNTER_KIND",
    "DEFAULT_AUDITS_PER_MONTH",
    "QuotaExceeded",
    "get_quota_limit",
    "monthly_period_key",
    "current_monthly_period_key",
    "get_usage",
    "increment_usage",
    "consume_quota",
]
