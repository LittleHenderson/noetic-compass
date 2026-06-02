"""The executable contract for :class:`StateStore`.

``run_state_store_contract(make_store)`` exercises every behaviour a backend must
agree on: record round-trips, fail-closed tenant scoping, optimistic concurrency,
version-checked deletes, and the full single-holder / expiring / renew-release
lease lifecycle. It takes a *factory* (``Callable[[], StateStore]``) rather than a
store instance so it can construct fresh, isolated stores and -- for durable
backends -- be re-pointed at the same storage to prove survival across a reopen.

Why a shared suite instead of per-backend tests: the whole value of the Protocol
is substitutability. If the in-memory store and the SQLite store can disagree
about, say, whether an expired lease is renewable, then code written against the
Protocol is not actually portable and the durability ladder is a lie. Running the
*same* assertions against every backend is what makes "swap the backend, keep the
behaviour" a checked fact rather than a hope.

Expiry is tested by injecting ``now`` (fixed ``_T0`` plus ``timedelta``s), never by
sleeping. A test that sleeps to observe a TTL is slow and flaky; the substrate
takes ``now`` everywhere precisely so time is an argument, not a side effect.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Callable

from .interface import (
    LeaseExpired,
    LeaseHeld,
    LedgerRecord,
    StateStore,
    TenantScopeViolation,
    UnknownLease,
    VersionConflict,
)

# A fixed, timezone-aware anchor so every time-dependent assertion is deterministic.
_T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def run_state_store_contract(make_store: Callable[[], StateStore]) -> None:
    """Run the full contract against stores produced by ``make_store``.

    Raises ``AssertionError`` on the first violated behaviour. A backend that
    returns from this call cleanly is substitutable for the reference store with
    respect to every behaviour the project depends on.
    """

    _records_roundtrip(make_store)
    _tenant_scoping_fails_closed(make_store)
    _optimistic_concurrency(make_store)
    _delete_semantics(make_store)
    _lease_single_holder(make_store)
    _lease_expiry(make_store)
    _lease_renew_release(make_store)


def _records_roundtrip(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        rec = LedgerRecord.new(
            tenant_id="tenant-a",
            kind="run",
            record_id="run-001",
            payload={"status": "QUEUED", "shards": 4},
            source="conformance",
            trace_id="trace-xyz",
        )
        assert rec.version == 0, "a freshly built, unpersisted record is version 0"

        stored = store.put(rec, expected_version=0)
        assert stored.version == 1, "first put promotes version 0 -> 1"
        assert stored.created_at == rec.created_at, "created_at is preserved by put"
        assert stored.payload["status"] == "QUEUED"
        assert stored.trace_id == "trace-xyz", "traceability envelope survives the round-trip"
        assert stored.source == "conformance"

        fetched = store.get("tenant-a", "run", "run-001")
        assert fetched is not None
        assert fetched.version == 1
        assert fetched.payload == {"status": "QUEUED", "shards": 4}

        # Update: hand back the version we read, get the next one.
        updated = store.put(stored.with_payload({"status": "RUNNING", "shards": 4}), expected_version=1)
        assert updated.version == 2
        assert updated.created_at == stored.created_at, "created_at immutable across updates"
        assert updated.updated_at >= stored.updated_at, "updated_at moves forward (or holds)"

        listed = store.list("tenant-a", "run")
        assert [r.record_id for r in listed] == ["run-001"]
        assert listed[0].version == 2, "list reflects the latest stored version"
    finally:
        store.close()


def _tenant_scoping_fails_closed(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        store.put(
            LedgerRecord.new(tenant_id="tenant-a", kind="run", record_id="run-1", payload={"x": 1}),
            expected_version=0,
        )
        store.put(
            LedgerRecord.new(tenant_id="tenant-b", kind="run", record_id="run-1", payload={"x": 2}),
            expected_version=0,
        )

        # Same record_id, different tenant: each tenant sees only its own row.
        a = store.get("tenant-a", "run", "run-1")
        b = store.get("tenant-b", "run", "run-1")
        assert a is not None and a.payload == {"x": 1}
        assert b is not None and b.payload == {"x": 2}

        # Cross-tenant read of a row that exists for someone else -> indistinguishable
        # from absent. tenant-c must not even learn the row exists.
        assert store.get("tenant-c", "run", "run-1") is None

        # list is tenant-scoped.
        assert [r.tenant_id for r in store.list("tenant-a", "run")] == ["tenant-a"]
        assert store.list("tenant-c", "run") == ()

        # Cross-tenant *mutation* fails loudly rather than silently missing.
        try:
            store.delete("tenant-c", "run", "run-1", expected_version=1)
        except TenantScopeViolation:
            pass
        else:
            raise AssertionError("cross-tenant delete must raise TenantScopeViolation")
    finally:
        store.close()


def _optimistic_concurrency(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        first = store.put(
            LedgerRecord.new(tenant_id="t", kind="worker", record_id="w-1", payload={"state": "idle"}),
            expected_version=0,
        )
        assert first.version == 1

        # Creating something that already exists (expected_version 0) is a conflict.
        try:
            store.put(
                LedgerRecord.new(tenant_id="t", kind="worker", record_id="w-1", payload={"state": "dup"}),
                expected_version=0,
            )
        except VersionConflict as exc:
            assert exc.actual == 1 and exc.expected == 0
        else:
            raise AssertionError("re-creating an existing record must raise VersionConflict")

        # Two readers both hold version 1. The first writer wins.
        store.put(first.with_payload({"state": "busy"}), expected_version=1)
        # The second writer, still on the stale version 1, loses.
        try:
            store.put(first.with_payload({"state": "stale"}), expected_version=1)
        except VersionConflict as exc:
            assert exc.actual == 2, "store reports the version the loser must rebase onto"
        else:
            raise AssertionError("stale-version put must raise VersionConflict")

        # The winning value is what persisted.
        assert store.get("t", "worker", "w-1").payload == {"state": "busy"}
    finally:
        store.close()


def _delete_semantics(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        stored = store.put(
            LedgerRecord.new(tenant_id="t", kind="lease-row", record_id="r-1", payload={}),
            expected_version=0,
        )
        # Wrong version -> conflict, row survives.
        try:
            store.delete("t", "lease-row", "r-1", expected_version=99)
        except VersionConflict as exc:
            assert exc.actual == stored.version
        else:
            raise AssertionError("delete with wrong version must raise VersionConflict")
        assert store.get("t", "lease-row", "r-1") is not None

        # Correct version -> gone.
        store.delete("t", "lease-row", "r-1", expected_version=stored.version)
        assert store.get("t", "lease-row", "r-1") is None
    finally:
        store.close()


def _lease_single_holder(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        lease = store.acquire_lease("t", "shard-7", holder="worker-a", ttl_seconds=60, now=_T0)
        assert lease.holder == "worker-a"
        assert lease.expires_at == _T0 + timedelta(seconds=60)

        # get_lease reports the live holder.
        live = store.get_lease("t", "shard-7", now=_T0 + timedelta(seconds=1))
        assert live is not None and live.holder == "worker-a"

        # A different holder cannot take a live lease.
        try:
            store.acquire_lease("t", "shard-7", holder="worker-b", ttl_seconds=60, now=_T0 + timedelta(seconds=1))
        except LeaseHeld as exc:
            assert exc.holder == "worker-a"
        else:
            raise AssertionError("second holder must not acquire a live lease")

        # Same holder re-acquiring is idempotent (extends, fresh token).
        again = store.acquire_lease("t", "shard-7", holder="worker-a", ttl_seconds=120, now=_T0 + timedelta(seconds=2))
        assert again.holder == "worker-a"
        assert again.token != lease.token, "re-acquire issues a fresh token"
        assert again.expires_at == _T0 + timedelta(seconds=122)

        # Lease is tenant-scoped: another tenant's same-named resource is independent.
        other = store.acquire_lease("t2", "shard-7", holder="worker-z", ttl_seconds=60, now=_T0)
        assert other.holder == "worker-z"
        assert store.get_lease("t", "shard-7", now=_T0 + timedelta(seconds=2)).holder == "worker-a"
    finally:
        store.close()


def _lease_expiry(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        store.acquire_lease("t", "shard-9", holder="worker-a", ttl_seconds=30, now=_T0)

        # Before expiry: held.
        assert store.get_lease("t", "shard-9", now=_T0 + timedelta(seconds=29)) is not None
        # At/after expiry: reported absent.
        assert store.get_lease("t", "shard-9", now=_T0 + timedelta(seconds=30)) is None

        # Once expired, a different holder may claim it.
        taken = store.acquire_lease("t", "shard-9", holder="worker-b", ttl_seconds=30, now=_T0 + timedelta(seconds=31))
        assert taken.holder == "worker-b"
    finally:
        store.close()


def _lease_renew_release(make_store: Callable[[], StateStore]) -> None:
    store = make_store()
    try:
        lease = store.acquire_lease("t", "shard-3", holder="worker-a", ttl_seconds=60, now=_T0)

        # Renew before expiry pushes expires_at out and keeps the same token.
        renewed = store.renew_lease(lease.token, ttl_seconds=60, now=_T0 + timedelta(seconds=30))
        assert renewed.token == lease.token, "renew preserves the token the holder already has"
        assert renewed.expires_at == _T0 + timedelta(seconds=90)

        # Renewing an unknown token fails.
        try:
            store.renew_lease("not-a-real-token", ttl_seconds=60, now=_T0)
        except UnknownLease:
            pass
        else:
            raise AssertionError("renewing an unknown token must raise UnknownLease")

        # Let it lapse, then renew -> LeaseExpired (renew never resurrects the dead).
        try:
            store.renew_lease(lease.token, ttl_seconds=60, now=_T0 + timedelta(seconds=120))
        except LeaseExpired:
            pass
        else:
            raise AssertionError("renewing an expired lease must raise LeaseExpired")

        # Release frees the resource; releasing again is an idempotent no-op.
        fresh = store.acquire_lease("t", "shard-3", holder="worker-a", ttl_seconds=60, now=_T0 + timedelta(seconds=200))
        store.release_lease(fresh.token)
        assert store.get_lease("t", "shard-3", now=_T0 + timedelta(seconds=201)) is None
        store.release_lease(fresh.token)  # no raise
    finally:
        store.close()
