from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from api.services.production.state_substrate.interface import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.quotas import (
    DEFAULT_AUDITS_PER_MONTH,
    USAGE_COUNTER_KIND,
    QuotaExceeded,
    consume_quota,
    get_quota_limit,
    get_usage,
    increment_usage,
    monthly_period_key,
)

_PERIOD = "audits:2026-06"


@pytest.fixture
def backend(tmp_path) -> SqliteStateStore:
    store = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    try:
        yield store
    finally:
        store.close()


def test_usage_is_zero_when_absent(backend):
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 0


def test_increment_bumps_and_get_reflects(backend):
    assert increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100) == 1
    assert increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100) == 2
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 2


def test_increment_amount_greater_than_one(backend):
    assert (
        increment_usage(
            backend,
            tenant_id="tenant-A",
            period_key=_PERIOD,
            amount=5,
            limit=100,
        )
        == 5
    )
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 5


def test_counter_carries_traceability_envelope(backend):
    increment_usage(
        backend,
        tenant_id="tenant-A",
        period_key=_PERIOD,
        limit=100,
        source="cas_harness_audit",
    )
    rec = backend.get("tenant-A", USAGE_COUNTER_KIND, _PERIOD)
    assert rec is not None
    assert rec.source == "cas_harness_audit"
    assert rec.version == 1
    assert rec.created_at is not None
    assert rec.payload == {"count": 1, "limit": 100, "period": _PERIOD}


def test_consume_allows_up_to_limit_then_raises(backend):
    limit = 3
    assert [
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
        for _ in range(limit)
    ] == [1, 2, 3]

    with pytest.raises(QuotaExceeded) as exc:
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)

    assert exc.value.tenant_id == "tenant-A"
    assert exc.value.limit == limit
    assert exc.value.count == limit
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == limit


def test_consume_on_fresh_tenant_with_zero_limit_refuses_immediately(backend):
    with pytest.raises(QuotaExceeded) as exc:
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=0)
    assert exc.value.count == 0
    assert backend.get("tenant-A", USAGE_COUNTER_KIND, _PERIOD) is None


def test_cross_tenant_counters_are_independent(backend):
    increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, amount=3, limit=100)

    assert get_usage(backend, tenant_id="tenant-B", period_key=_PERIOD) == 0
    assert backend.get("tenant-B", USAGE_COUNTER_KIND, _PERIOD) is None
    assert increment_usage(backend, tenant_id="tenant-B", period_key=_PERIOD, limit=100) == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 3
    assert get_usage(backend, tenant_id="tenant-B", period_key=_PERIOD) == 1


def test_cross_tenant_consume_does_not_share_a_cap(backend):
    limit = 1
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    with pytest.raises(QuotaExceeded):
        consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    assert consume_quota(backend, tenant_id="tenant-B", period_key=_PERIOD, limit=limit) == 1


def test_monthly_period_key_format_for_known_datetime():
    assert monthly_period_key(datetime(2026, 6, 5, 13, 30, tzinfo=UTC)) == "audits:2026-06"
    assert monthly_period_key(datetime(2026, 1, 9, tzinfo=UTC)) == "audits:2026-01"


def test_get_quota_limit_returns_default():
    assert get_quota_limit() == DEFAULT_AUDITS_PER_MONTH
    assert get_quota_limit("any-plan") == DEFAULT_AUDITS_PER_MONTH


class _ConflictOnceStore:
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

    def __getattr__(self, name):
        return getattr(self._inner, name)


def test_increment_retries_on_version_conflict_and_does_not_double_count(backend):
    wrapped = _ConflictOnceStore(backend)
    assert increment_usage(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=100) == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 1


def test_increment_retries_on_conflict_during_update(backend):
    increment_usage(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=100)
    wrapped = _ConflictOnceStore(backend)
    assert increment_usage(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=100) == 2
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 2


def test_consume_retries_on_version_conflict_and_converges(backend):
    wrapped = _ConflictOnceStore(backend)
    assert consume_quota(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=100) == 1
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == 1


def test_consume_does_not_exceed_cap_even_with_conflict_retry(backend):
    limit = 2
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    consume_quota(backend, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)
    wrapped = _ConflictOnceStore(backend)

    with pytest.raises(QuotaExceeded) as exc:
        consume_quota(wrapped, tenant_id="tenant-A", period_key=_PERIOD, limit=limit)

    assert exc.value.count == limit
    assert get_usage(backend, tenant_id="tenant-A", period_key=_PERIOD) == limit
