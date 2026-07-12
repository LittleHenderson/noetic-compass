"""Per-tenant usage-quota engine -- storage + check/increment unit tests.

Pure unit tests of ``api/services/quotas.py`` over a REAL durable store (a fresh per-test
``SqliteStateStore`` on a tmp_path file, the same fixture shape as ``test_evidence_ownership.py``
and ``test_accounts_invites.py``). No FastAPI, no routes, no settings: the engine is route-agnostic
and INERT until a flag the route layer owns turns it on, so there is nothing app-level to exercise
here. These tests pin the storage contract the future route wiring will depend on.

Coverage:
* usage starts at 0 when absent; increment bumps; get reflects.
* ``consume_quota`` allows exactly up to ``limit``, then raises ``QuotaExceeded`` (carrying
  tenant_id / limit / count), and the rejected call consumes nothing.
* cross-tenant isolation: tenant A's counter is invisible to tenant B under the same period key.
* ``monthly_period_key`` format for a known datetime.
* VersionConflict path: a store wrapper that raises ``VersionConflict`` once proves the retry loop
  converges and never double-counts past the cap (for both ``increment_usage`` and ``consume_quota``).
* ``get_quota_limit()`` returns the default.

Run ONLY this file:
    python -m pytest tests/test_quotas.py -q
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from api.services.production.state_substrate.interface import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)
from api.services.quotas import (
    DEFAULT_AUDITS_PER_MONTH,
    USAGE_COUNTER_KIND,
    QuotaExceeded,
    consume_audit_quota,
    consume_quota,
    get_quota_limit,
    get_usage,
    increment_usage,
    monthly_period_key,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore

_PERIOD = "audits:2026-06"


@pytest.fixture
def backend(tmp_path) -> SqliteStateStore:
    """A fresh durable SQLite-backed StateStore per test (mirrors test_evidence_ownership.py)."""
    store = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    try:
        yield store
    finally:
        store.close()


# --- basic read / increment ------------------------------------------------


def test_usage_is_zero_when_absent(backend):
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 0


def test_increment_bumps_and_get_reflects(backend):
    n1 = increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    assert n1 == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 1

    n2 = increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    assert n2 == 2
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 2


def test_increment_amount_greater_than_one(backend):
    n = increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, amount=5, limit=100)
    assert n == 5
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 5


def test_counter_carries_traceability_envelope(backend):
    """Every object knows where it came from: source / version / created_at, plus the payload."""
    increment_usage(
        backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100, source="cas_harness_audit"
    )
    rec = backend.get("tenant-A", USAGE_COUNTER_KIND, _PERIOD)
    assert rec is not None
    assert rec.source == "cas_harness_audit"
    assert rec.version == 1  # put(expected_version=0) promotes a v0 record to v1
    assert rec.created_at is not None
    assert rec.payload["count"] == 1
    assert rec.payload["limit"] == 100
    assert rec.payload["period"] == _PERIOD


# --- consume_quota: allow up to limit, then refuse -------------------------


def test_consume_allows_up_to_limit_then_raises(backend):
    limit = 3
    counts = [
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
        for _ in range(limit)
    ]
    assert counts == [1, 2, 3]
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 3

    # The (limit+1)-th consume is refused.
    with pytest.raises(QuotaExceeded) as exc:
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)

    # The exception carries the diagnostic triple the route layer maps to HTTP 429.
    assert exc.value.tenant_id == "tenant-A"
    assert exc.value.limit == limit
    assert exc.value.count == limit


def test_consume_rejection_consumes_nothing(backend):
    """A rejected consume must not bill: the stored count stays at the cap, not cap+1."""
    limit = 2
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    with pytest.raises(QuotaExceeded):
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    # Still exactly at the cap -- the rejected call did not increment.
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == limit


def test_consume_on_fresh_tenant_with_zero_limit_refuses_immediately(backend):
    """A limit of 0 means the very first consume is refused and no counter is written."""
    with pytest.raises(QuotaExceeded) as exc:
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=0)
    assert exc.value.count == 0
    assert exc.value.limit == 0
    # Nothing was minted -- a refusal at count 0 leaves the store empty for this tenant/period.
    assert backend.get("tenant-A", USAGE_COUNTER_KIND, _PERIOD) is None


# --- cross-tenant isolation ------------------------------------------------


def test_cross_tenant_counters_are_independent(backend):
    """Tenant A's counter under a period key is invisible to tenant B's read and increment."""
    increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, amount=3, limit=100)

    # B has recorded nothing under the SAME period key.
    assert get_usage(backend, tenant_id="tenant-B", period_key=_PERIOD) == 0
    # Direct store read confirms cross-tenant get is None (indistinguishable from absent).
    assert backend.get("tenant-B", USAGE_COUNTER_KIND, _PERIOD) is None

    # B increments its own counter; A's is untouched.
    assert increment_usage(backend, tenant_id="tenant-B", period_key=_PERIOD, limit=100) == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 3
    assert get_usage(backend, tenant_id="tenant-B", period_key=_PERIOD) == 1


def test_cross_tenant_consume_does_not_share_a_cap(backend):
    """A's exhausted cap does not stop B: caps are per-tenant under the same period key."""
    limit = 1
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    with pytest.raises(QuotaExceeded):
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    # B is unaffected -- its own first unit is available.
    assert consume_quota(backend, tenant_id="tenant-B", period_key=_PERIOD, limit=limit) == 1


# --- period key format -----------------------------------------------------


def test_monthly_period_key_format_for_known_datetime():
    dt = datetime(2026, 6, 5, 13, 30, tzinfo=UTC)
    assert monthly_period_key(dt) == "audits:2026-06"


def test_monthly_period_key_zero_pads_month():
    dt = datetime(2026, 1, 9, tzinfo=UTC)
    assert monthly_period_key(dt) == "audits:2026-01"


# --- get_quota_limit default -----------------------------------------------


def test_get_quota_limit_returns_default():
    assert get_quota_limit() == DEFAULT_AUDITS_PER_MONTH
    # plan_id is accepted but ignored for now (single-allowance data model).
    assert get_quota_limit("any-plan") == DEFAULT_AUDITS_PER_MONTH


def test_audit_quota_is_idempotent_by_audit_id(backend):
    assert consume_audit_quota(
        backend,
        tenant_id="tenant-A",
        period_key=_PERIOD,
        audit_id="audit-1",
        limit=2,
    ) == 1
    assert consume_audit_quota(
        backend,
        tenant_id="tenant-A",
        period_key=_PERIOD,
        audit_id="audit-1",
        limit=2,
    ) == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 1


def test_audit_quota_is_tenant_isolated_and_caps_distinct_audits(backend):
    for tenant in ("tenant-A", "tenant-B"):
        assert consume_audit_quota(
            backend,
            tenant_id=tenant,
            period_key=_PERIOD,
            audit_id="audit-1",
            limit=1,
        ) == 1
    with pytest.raises(QuotaExceeded):
        consume_audit_quota(
            backend,
            tenant_id="tenant-A",
            period_key=_PERIOD,
            audit_id="audit-2",
            limit=1,
        )
    assert get_usage(backend, tenant_id="tenant-B", period_key=_PERIOD) == 1


def test_audit_quota_uses_independent_month_buckets(backend):
    for period in ("audits:2026-06", "audits:2026-07"):
        assert consume_audit_quota(
            backend,
            tenant_id="tenant-A",
            period_key=period,
            audit_id="audit-1",
            limit=1,
        ) == 1


# --- VersionConflict path --------------------------------------------------


class _ConflictOnceStore:
    """A thin StateStore wrapper that injects exactly ONE VersionConflict on ``put``, then delegates.

    Simulates a concurrent writer that wins the race for a single attempt: the first ``put`` the
    engine makes is rejected as if another caller had bumped the version underneath it; every
    subsequent call (including the engine's retry) passes through to the real store. Lets us assert
    the retry loop re-reads and converges to the correct count, never double-counting.
    """

    def __init__(self, inner: StateStore) -> None:
        self._inner = inner
        self._conflicts_left = 1

    def put(self, record: LedgerRecord, *, expected_version: int) -> LedgerRecord:
        if self._conflicts_left > 0:
            self._conflicts_left -= 1
            raise VersionConflict(
                kind=record.kind,
                record_id=record.record_id,
                expected=expected_version,
                actual=expected_version + 1,
            )
        return self._inner.put(record, expected_version=expected_version)

    # Everything else delegates unchanged.
    def __getattr__(self, name):  # pragma: no cover - trivial delegation
        return getattr(self._inner, name)


def test_increment_retries_on_version_conflict_and_does_not_double_count(backend):
    """One injected conflict on the create path: increment must converge to exactly 1, not 2."""
    wrapped = _ConflictOnceStore(backend)
    n = increment_usage(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    assert n == 1
    # Read via the real backend: the retry produced exactly one unit, no phantom double-write.
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 1


def test_increment_retries_on_conflict_during_update(backend):
    """A conflict on the UPDATE path (counter already exists) also converges without double-count."""
    # Seed an existing counter at 1 through the real store.
    increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    # Now wrap so the next put (an update from 1 -> 2) conflicts once, then succeeds on retry.
    wrapped = _ConflictOnceStore(backend)
    n = increment_usage(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    assert n == 2
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 2


def test_consume_retries_on_version_conflict_and_converges(backend):
    """consume_quota survives one injected conflict and still consumes exactly one unit."""
    wrapped = _ConflictOnceStore(backend)
    n = consume_quota(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    assert n == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 1


def test_consume_does_not_exceed_cap_even_with_conflict_retry(backend):
    """The cap holds across a conflict retry: at the cap, a conflicting attempt still ends in refusal.

    Seed the counter to the cap, then wrap the store so the engine's first write attempt would
    conflict. consume_quota must re-read, observe count == limit, and raise QuotaExceeded rather than
    retry its way past the cap. (The injected conflict is never reached because the limit re-check
    fires first on the post-conflict re-read; the counter must remain exactly at the cap.)
    """
    limit = 2
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == limit

    wrapped = _ConflictOnceStore(backend)
    with pytest.raises(QuotaExceeded) as exc:
        consume_quota(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    assert exc.value.count == limit
    # Cap intact -- no over-count slipped through the retry path.
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == limit
