"""Per-tenant usage-quota engine -- the metering primitive for paid CAS Harness accounts.

The harness will, once paid accounts ship, meter each tenant's monthly audit usage against a cap.
This module is the storage + check/increment logic for that meter, and ONLY that: it is a set of
pure functions over a :class:`StateStore`, with no FastAPI/route/settings imports. The route layer
(a SEPARATE change, stacked on this one) decides WHEN to consume a unit and how to translate a
:class:`QuotaExceeded` into an HTTP 429; this module only provides the read, the increment, and the
single guarded ``consume_quota`` entry point a route will call.

INERT BY DEFAULT. Nothing here runs unless ``settings.quotas_enabled`` is on (default off), and even
then route wiring is follow-on work. With the flag off, no code path reaches these functions, no
usage counter is ever written or read, and app behaviour is byte-for-byte unchanged. The flag and
its startup guard ("quotas require accounts") live in ``api/config.py`` / ``api/main.py``; this
module makes no policy decision about whether quotas are active -- it just does the arithmetic when
asked.

Isolation. A usage counter is a tenant-scoped :class:`LedgerRecord` exactly like an evidence
ownership row (see ``api/services/evidence_ownership.py``). Isolation is NOT a hand-rolled tenant
comparison here -- it is enforced by the store's mandatory tenant partitioning: a counter written
under tenant A's id is simply invisible to ``store.get(tenant_B, ...)`` (a cross-tenant read returns
``None``, indistinguishable from "absent"). So one tenant can never read, increment, or be billed
against another tenant's counter, and we never have to re-derive that guarantee.

Concurrency. A counter is read-modify-write, unlike the write-once ownership row, so it genuinely
races: two concurrent audits for the same tenant in the same month both read count=N and both try to
write count=N+1 at the same ``expected_version``. The store's optimistic concurrency turns the loser
into a :class:`VersionConflict` rather than a silent lost update. We handle that the honest way the
substrate prescribes -- "re-read, re-decide, re-attempt" -- in a small bounded retry loop, and (this
is the load-bearing part for a CAP) we RE-CHECK the limit after every re-read in ``consume_quota`` so
a concurrent caller can never push the count past the cap by winning a race we then blindly retried.

Every counter carries the project's traceability envelope (``created_at`` / ``version`` / ``source``
/ ``trace_id``): every object knows where it came from.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from api.services.production.state_substrate.interface import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

# The record ``kind`` under which usage counters live in the ledger. A distinct kind keeps these
# rows from colliding with account/session/evidence rows that share the same store, and makes the
# usage namespace greppable.
USAGE_COUNTER_KIND = "usage_counter"

# Default provenance for a counter row minted by the CAS Harness audit flow. Recorded in the
# traceability envelope's ``source`` so a row can be traced to the subsystem that wrote it.
_DEFAULT_SOURCE = "cas_harness_audit"

# Default monthly audit allowance, applied to EVERY tenant for now. The account model deliberately
# has no plan/tier field yet, so there is exactly one number and it is this one. Chosen as a sane,
# round starting cap; the real per-plan numbers arrive with the subscription record (see
# :func:`get_quota_limit`).
DEFAULT_AUDITS_PER_MONTH = 100

# How many times ``increment_usage`` / ``consume_quota`` will re-read-and-retry on a
# :class:`VersionConflict` before giving up. A conflict means a concurrent caller bumped the same
# counter between our read and our write; re-reading and retrying converges quickly under any
# realistic contention. Bounded so a pathological hot-loop cannot spin forever -- exhausting the
# budget re-raises the last conflict rather than silently miscounting.
_MAX_RETRIES = 5


class QuotaExceeded(Exception):
    """A tenant has reached its usage cap for the period; the unit was NOT consumed.

    Carries the ``tenant_id``, the ``limit`` that was hit, and the current ``count`` (which equals
    or exceeds the limit) so the future route layer can map this to an honest HTTP 429 without a
    second store round-trip. Raising this is the ONLY way ``consume_quota`` declines: a decline
    leaves the stored counter untouched, so a rejected request is never billed.
    """

    def __init__(self, tenant_id: str, limit: int, count: int) -> None:
        self.tenant_id = tenant_id
        self.limit = limit
        self.count = count
        super().__init__(
            f"quota exceeded for tenant {tenant_id!r}: count {count} >= limit {limit}"
        )


def get_quota_limit(plan_id: Optional[str] = None) -> int:
    """Return the monthly audit allowance for a plan.

    For now this ALWAYS returns :data:`DEFAULT_AUDITS_PER_MONTH`, ignoring ``plan_id`` (which is
    accepted only so the call site is already plan-shaped and the follow-up is a body change, not a
    signature change). The account model has no plan/tier field yet and there is no subscription
    record, so there is exactly one allowance and every tenant gets it. When a subscription/plan
    record lands, this becomes a lookup keyed by ``plan_id`` with this value as the fallback for an
    unknown or absent plan. Deliberately NOT building a plan system here -- one number, honestly
    labelled, is the correct amount of mechanism for the current data model.
    """
    return DEFAULT_AUDITS_PER_MONTH


def monthly_period_key(now: datetime) -> str:
    """Build the period key for the calendar month containing ``now`` -- e.g. ``"audits:2026-06"``.

    The key namespaces the counter by metered resource ("audits") and by month, so a tenant gets a
    fresh counter each month simply by addressing a new record id; nothing has to reset an old one.

    ``now`` is a REQUIRED parameter and is never read from the wall clock inside this pure helper, so
    tests are deterministic. A timezone-aware ``now`` is interpreted in its own zone for the
    year/month fields; pass UTC (as :func:`current_monthly_period_key` does) for a stable global
    month boundary. (The substrate's own ``utc_now`` is the canonical 'now' for production callers.)
    """
    return f"audits:{now.year:04d}-{now.month:02d}"


def current_monthly_period_key() -> str:
    """Thin wrapper over :func:`monthly_period_key` defaulting to the current UTC month.

    Production callers use this; tests use :func:`monthly_period_key` with a fixed datetime so the
    period is not clock-dependent. Kept separate precisely so the pure helper stays pure.
    """
    return monthly_period_key(datetime.now(UTC))


def get_usage(store: StateStore, *, tenant_id: str, period_key: str) -> int:
    """Return the current usage count for ``(tenant_id, period_key)`` -- ``0`` if no counter exists.

    A pure tenant-scoped read. Leans on the store's partitioning: ``get`` returns the row only when
    it exists AND belongs to ``tenant_id``; a cross-tenant or absent counter both read as ``None``,
    which we report as ``0`` (no usage recorded for this tenant this period). One tenant therefore
    cannot even observe another tenant's usage.
    """
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
    """Add ``amount`` to the tenant's counter for ``period_key`` and return the NEW count.

    Read-modify-write with optimistic concurrency. If no counter exists yet we create it at
    ``expected_version=0`` (the substrate's create contract); otherwise we re-put the existing record
    with a bumped count at the version we just read. A concurrent writer that mutated the row between
    our read and our write makes the store raise :class:`VersionConflict`; we catch it, re-read, and
    retry up to :data:`_MAX_RETRIES` times. Because each attempt re-reads the current count first, a
    retry never double-counts -- it adds ``amount`` to the freshly observed value, not to a stale
    one, so concurrent increments serialize into the correct total.

    This is a pure mechanical bump and does NOT itself enforce the cap (it takes ``limit`` only to
    persist it in the payload alongside the count, so a stored counter is self-describing for audit).
    Cap enforcement is :func:`consume_quota`'s job. Returns the post-increment count.

    Note the same partitioning asymmetry as evidence ownership: the row we read/create is only ever
    this tenant's; another tenant's counter under the same ``period_key`` is invisible here and is
    never read, bumped, or overwritten.
    """
    last_conflict: Optional[VersionConflict] = None
    for _ in range(_MAX_RETRIES):
        existing = store.get(tenant_id, USAGE_COUNTER_KIND, period_key)
        if existing is None:
            # First use this period: mint a v0 counter; put(expected_version=0) promotes it to v1.
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
                # A concurrent caller created the counter between our get and our create. Re-read
                # and retry: the next loop iteration takes the update branch with the real version.
                last_conflict = conflict
                continue

        # Counter exists: bump from the value we just read, at the version we just read.
        new_count = int(existing.payload.get("count", 0)) + amount
        updated = existing.with_payload(
            {"count": new_count, "limit": limit, "period": period_key}
        )
        try:
            store.put(updated, expected_version=existing.version)
            return new_count
        except VersionConflict as conflict:
            # Lost the race: someone else bumped the counter under us. Re-read, re-add, re-attempt.
            last_conflict = conflict
            continue

    # Exhausted the retry budget under sustained contention. Surface the conflict honestly rather
    # than returning a count we are not sure we persisted -- the caller (and any test) sees the real
    # failure, never a silently miscounted success.
    assert last_conflict is not None  # only reachable after at least one caught VersionConflict
    raise last_conflict


def consume_quota(
    store: StateStore,
    *,
    tenant_id: str,
    period_key: str,
    limit: int,
    source: str = _DEFAULT_SOURCE,
) -> int:
    """Consume ONE unit of the tenant's quota for ``period_key``, or raise :class:`QuotaExceeded`.

    The single entry point a route will call. Semantics: if the tenant's current count is already at
    or above ``limit``, raise :class:`QuotaExceeded` and consume nothing; otherwise increment by one
    and return the new count. This is the check-then-increment that has to be race-safe.

    Race safety is the whole point. A naive "if get_usage() < limit: increment()" has a TOCTOU hole:
    two callers at count == limit-1 both pass the check and both increment, pushing the count to
    limit+1 -- one audit over the cap. We close it by folding the limit re-check INTO the
    read-modify-write retry loop: on every attempt we read the current count, refuse if it is already
    at the cap, and only then attempt the versioned write. If the write loses to a concurrent caller
    (:class:`VersionConflict`), we do NOT blindly retry the increment -- we loop back, RE-READ, and
    RE-CHECK the limit against the new count, so the caller that pushes the counter to the cap causes
    the next caller to be rejected rather than allowed. The cap holds under concurrency: the store's
    version check serializes the writers, and re-checking after each conflict means at most ``limit``
    writes can ever succeed.

    Returns the post-increment count (which is ``<= limit``).
    """
    last_conflict: Optional[VersionConflict] = None
    for _ in range(_MAX_RETRIES):
        existing = store.get(tenant_id, USAGE_COUNTER_KIND, period_key)
        current = 0 if existing is None else int(existing.payload.get("count", 0))

        # Re-checked on EVERY attempt (including after a conflict re-read), so a concurrent caller
        # cannot slip the count past the cap: once count hits limit, every subsequent attempt here
        # refuses before writing.
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

    # Sustained contention exhausted the retry budget without a successful write. Surface the
    # conflict rather than pretend the unit was consumed.
    assert last_conflict is not None  # only reachable after at least one caught VersionConflict
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
