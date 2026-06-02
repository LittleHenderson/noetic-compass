"""Contract + durability + fencing tests for the Postgres ``StateStore`` backend.

Three jobs, two of which need a live Postgres and one of which does NOT:

1. **(live, skipped without a DB)** prove the Postgres backend passes the *same*
   backend-agnostic ``run_state_store_contract`` suite the in-memory and SQLite
   backends pass (substitutability), and prove durability across a close/reopen of
   the real server -- mirroring ``test_state_substrate_sqlite.py``.
2. **(live, skipped without a DB)** prove the FENCING MINT path: successive
   ``acquire_lease`` calls on the same resource carry strictly-increasing
   ``Lease.fence`` values issued by the Postgres sequence (docs 11 §5.2).
3. **(pure logic, ALWAYS runs)** prove the resource-side fencing guard
   (``reject_stale_fence`` / ``FencingGuard``) accepts a strictly-increasing
   sequence and rejects an equal-or-lower fence with ``StaleFenceToken`` -- the
   half of the §5.2 fix that actually stops a stale stalled-holder write, verifiable
   with no database at all. Plus a tiny guard that the additive ``Lease.fence``
   field defaults to 0 (so the existing conformance suite and the in-memory / SQLite
   stores stay green).

VERIFICATION NOTE (read this): the live tests below SKIP unless
``NC_TEST_POSTGRES_URL`` points at a reachable server. They have now been OBSERVED
to pass: on 2026-06-02 all 10 tests in this file passed (3 consecutive runs) against
a real PostgreSQL 16.4 server (a no-admin embedded EDB binary cluster) reachable via
``NC_TEST_POSTGRES_URL``. "PostgresStateStore passes the contract + durability +
fence-MINT monotonicity" is therefore now a *verified* claim against PostgreSQL 16.4,
not merely a declared one. (What remains config-dependent and NOT verified here:
survival of *host loss*, which needs synchronous replication + failover -- see the
honesty boundary in ``postgres_store.py``.) The fencing-logic tests in job 3 also
give real, observed coverage of the resource-side check with no DB at all.

Run ONLY this file (fencing-logic tests run; live tests skip without the env var):
    C:/Python314/python.exe -m pytest tests/test_state_substrate_postgres.py -q

Run the live tests against a throwaway Postgres, e.g.:
    docker run --rm -e POSTGRES_PASSWORD=pw -p 5432:5432 postgres:16
    set NC_TEST_POSTGRES_URL=postgresql://postgres:pw@localhost:5432/postgres
    C:/Python314/python.exe -m pytest tests/test_state_substrate_postgres.py -q
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from api.services.production.state_substrate import (
    FencingGuard,
    Lease,
    LedgerRecord,
    StaleFenceToken,
    reject_stale_fence,
    run_state_store_contract,
)

# A fixed, timezone-aware anchor mirrors the conformance suite so lease-expiry
# assertions are deterministic without ever sleeping.
_T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

# The live Postgres DSN. When unset, every live-DB test in this module skips; the
# pure fencing-logic tests still run.
_PG_URL = os.environ.get("NC_TEST_POSTGRES_URL")
_PG_REASON = "NC_TEST_POSTGRES_URL is not set; skipping live-Postgres tests"


# ---------------------------------------------------------------------------
# Pure fencing-logic tests -- NO database required; these always run.
# ---------------------------------------------------------------------------


def test_lease_fence_defaults_to_zero():
    # The additive ``fence`` field must default to 0 so every existing ``Lease(...)``
    # construction (memory_store, sqlite_store, conformance, the existing tests)
    # stays valid and the existing conformance suite stays green. This is the
    # backward-compatibility guarantee in one assertion.
    lease = Lease(
        tenant_id="t",
        resource_id="r",
        holder="h",
        token="tok",
        acquired_at=_T0,
        expires_at=_T0 + timedelta(seconds=60),
    )
    assert lease.fence == 0


def test_reject_stale_fence_accepts_strictly_increasing():
    # A strictly-increasing sequence is accepted, and each acceptance returns the
    # new high-water mark so a caller can thread it functionally.
    highest = 0
    for nxt in (1, 2, 3, 10, 11, 1000):
        highest = reject_stale_fence(highest, nxt)
        assert highest == nxt


def test_reject_stale_fence_rejects_equal_and_lower():
    # Equal fence is rejected (strictly-greater, not >=): re-presenting the same
    # fence is the stalled-holder attack the guard refuses.
    with pytest.raises(StaleFenceToken) as ei_equal:
        reject_stale_fence(5, 5)
    assert ei_equal.value.highest_seen == 5
    assert ei_equal.value.incoming == 5

    # A lower fence is rejected.
    with pytest.raises(StaleFenceToken) as ei_lower:
        reject_stale_fence(5, 4)
    assert ei_lower.value.highest_seen == 5
    assert ei_lower.value.incoming == 4


def test_fencing_guard_high_water_mark_advances_and_rejects():
    guard = FencingGuard()
    assert guard.highest_seen == 0

    # Accept an increasing run; the mark advances to the latest accepted fence.
    assert guard.check(1) == 1
    assert guard.highest_seen == 1
    assert guard.check(7) == 7
    assert guard.highest_seen == 7

    # The classic Kleppmann scenario: a stalled holder wakes with an OLD fence (5)
    # after a newer holder already acted with a HIGHER fence (7). The resource must
    # reject the stale write and must NOT move its high-water mark backwards.
    with pytest.raises(StaleFenceToken):
        guard.check(5)
    assert guard.highest_seen == 7, "a rejected stale fence must not move the mark"

    # Equal to the mark is also rejected (no two operations may share a fence).
    with pytest.raises(StaleFenceToken):
        guard.check(7)
    assert guard.highest_seen == 7

    # The next strictly-greater fence is accepted and advances the mark.
    assert guard.check(8) == 8
    assert guard.highest_seen == 8


def test_fencing_guard_can_be_seeded_with_persisted_mark():
    # A resource that persists its high-water mark (the cross-host case) restores it
    # on restart; a fence at-or-below the restored mark is still rejected.
    guard = FencingGuard(highest_seen=42)
    assert guard.highest_seen == 42
    with pytest.raises(StaleFenceToken):
        guard.check(42)
    assert guard.check(43) == 43


# ---------------------------------------------------------------------------
# Live-Postgres tests -- SKIPPED unless NC_TEST_POSTGRES_URL is set.
# Each factory call gets its own throwaway schema so repeated runs and the
# contract's multiple make_store() calls are fully isolated.
# ---------------------------------------------------------------------------


def _schema_scoped_dsn(base_dsn: str, schema: str) -> str:
    """Return ``base_dsn`` with libpq ``options`` forcing ``search_path=<schema>``.

    The store issues ``CREATE TABLE IF NOT EXISTS`` / ``CREATE SEQUENCE IF NOT
    EXISTS`` unqualified, so pointing ``search_path`` at a fresh schema lands all of
    its objects there -- giving each factory call an isolated namespace without
    modifying ``PostgresStateStore``.
    """

    import psycopg

    # `-c search_path=<schema>` is a libpq start-up option; make_conninfo merges it
    # safely whether base_dsn is URL-form or keyword-form.
    return psycopg.conninfo.make_conninfo(base_dsn, options=f"-c search_path={schema}")


@pytest.fixture
def pg_admin():
    """Yield an autocommit admin connection to the live server (default search_path).

    Skips the test if no live Postgres is configured or the driver is missing. This
    is the one connection that creates/drops the throwaway schemas the tests land
    their objects in; it never touches the application tables itself.
    """

    if not _PG_URL:
        pytest.skip(_PG_REASON)
    try:
        import psycopg
    except ModuleNotFoundError:
        pytest.skip("psycopg is not installed; skipping live-Postgres tests")

    try:
        admin = psycopg.connect(_PG_URL, autocommit=True)
    except psycopg.Error as exc:  # pragma: no cover - depends on a live server
        pytest.skip(f"could not connect to NC_TEST_POSTGRES_URL: {exc}")
    try:
        yield admin
    finally:
        admin.close()


@pytest.fixture
def pg_schema(pg_admin):
    """Create ONE unique throwaway schema, yield a schema-scoped DSN, drop it after.

    Used by the durability/reconnect tests, where TWO store objects must address the
    SAME storage to prove a committed record survives a close/reopen -- so they share
    a single schema by design.
    """

    schema = f"nc_test_{uuid.uuid4().hex}"
    pg_admin.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield _schema_scoped_dsn(_PG_URL, schema)
    finally:
        pg_admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_postgres_passes_state_store_contract(pg_admin):
    # The headline live assertion: the Postgres backend satisfies every behaviour
    # the Protocol promises, exactly as the reference store does.
    #
    # The contract calls the factory SEVERAL times and -- like the in-memory and
    # SQLite suites -- expects each store to be ISOLATED (the SQLite suite hands its
    # factory a unique database file per call for exactly this reason). The contract's
    # sub-tests are NOT all disjoint: ``_records_roundtrip`` writes tenant-a/run/run-001
    # and ``_tenant_scoping_fails_closed`` writes tenant-a/run/run-1, then asserts
    # ``list("tenant-a", "run")`` has exactly one element. Sharing one schema across
    # factory calls would leak the first row into the second sub-test's ``list`` and
    # fail that assertion -- a real cross-test leak, not a store bug. So each factory
    # call gets its OWN fresh schema, the Postgres analogue of "a unique file per call".
    # (Cross-object SHARED storage is exercised separately by the reconnect tests via
    # the single-schema ``pg_schema`` fixture, which is where shared state is correct.)
    from api.services.production.state_substrate.postgres_store import PostgresStateStore

    created: list[str] = []

    def factory() -> PostgresStateStore:
        schema = f"nc_test_{uuid.uuid4().hex}"
        pg_admin.execute(f'CREATE SCHEMA "{schema}"')
        created.append(schema)
        return PostgresStateStore(_schema_scoped_dsn(_PG_URL, schema))

    try:
        run_state_store_contract(factory)
    finally:
        for schema in created:
            pg_admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_records_survive_reconnect(pg_schema):
    # Durability across a close/reopen of the real server, mirroring the SQLite
    # restart test. A committed record -- including its full traceability envelope --
    # must be readable by a brand-new store object connecting to the same server.
    from api.services.production.state_substrate.postgres_store import PostgresStateStore

    store = PostgresStateStore(pg_schema)
    try:
        run_a = store.put(
            LedgerRecord.new(
                tenant_id="tenant-a",
                kind="run",
                record_id="run-001",
                payload={"status": "RUNNING", "shards": 4},
                parent_ids=("run-000",),
                source="reconnect-test",
                trace_id="trace-aaa",
            ),
            expected_version=0,
        )
        store.put(
            LedgerRecord.new(
                tenant_id="tenant-b",
                kind="worker",
                record_id="w-9",
                payload={"state": "idle"},
                source="reconnect-test",
                trace_id="trace-bbb",
            ),
            expected_version=0,
        )
        assert run_a.version == 1
    finally:
        store.close()

    reopened = PostgresStateStore(pg_schema)
    try:
        fetched = reopened.get("tenant-a", "run", "run-001")
        assert fetched is not None, "committed record must survive reconnect"
        assert fetched.version == 1
        assert fetched.payload == {"status": "RUNNING", "shards": 4}
        assert fetched.created_at == run_a.created_at, "created_at recovered exactly"
        assert fetched.updated_at == run_a.updated_at
        # Traceability envelope intact -- load-bearing for the project.
        assert fetched.source == "reconnect-test"
        assert fetched.trace_id == "trace-aaa"
        assert fetched.parent_ids == ("run-000",)

        listed = reopened.list("tenant-a", "run")
        assert [r.record_id for r in listed] == ["run-001"]
        other = reopened.get("tenant-b", "worker", "w-9")
        assert other is not None and other.payload == {"state": "idle"}
        assert other.trace_id == "trace-bbb"
        # Fail-closed scoping still holds after reconnect.
        assert reopened.get("tenant-b", "run", "run-001") is None
    finally:
        reopened.close()


def test_leases_survive_reconnect(pg_schema):
    # Durability for leases: acquire with injected `now` + long TTL, close, reopen,
    # confirm the live holder/token/fence come back, and that the same lease reads as
    # absent once `now` is past expiry.
    from api.services.production.state_substrate.postgres_store import PostgresStateStore

    store = PostgresStateStore(pg_schema)
    try:
        lease = store.acquire_lease(
            "tenant-a", "shard-7", holder="worker-a", ttl_seconds=3600, now=_T0
        )
        token = lease.token
        holder = lease.holder
        fence = lease.fence
        assert fence >= 1, "a real Postgres acquire mints a fence from the sequence"
    finally:
        store.close()

    reopened = PostgresStateStore(pg_schema)
    try:
        live = reopened.get_lease("tenant-a", "shard-7", now=_T0 + timedelta(seconds=10))
        assert live is not None, "committed lease must survive reconnect"
        assert live.holder == holder
        assert live.token == token
        assert live.fence == fence, "the fence is persisted with the lease"
        assert live.expires_at == _T0 + timedelta(seconds=3600)

        assert (
            reopened.get_lease("tenant-a", "shard-7", now=_T0 + timedelta(seconds=3601))
            is None
        )
    finally:
        reopened.close()


def test_reconnect_continues_version_sequence(pg_schema):
    # Versioning is a property of the durable ledger: a record at version N, reopened
    # and updated, goes N -> N+1 with no reset.
    from api.services.production.state_substrate.postgres_store import PostgresStateStore

    store = PostgresStateStore(pg_schema)
    try:
        first = store.put(
            LedgerRecord.new(tenant_id="t", kind="run", record_id="r-1", payload={"n": 1}),
            expected_version=0,
        )
        second = store.put(first.with_payload({"n": 2}), expected_version=1)
        assert second.version == 2
    finally:
        store.close()

    reopened = PostgresStateStore(pg_schema)
    try:
        current = reopened.get("t", "run", "r-1")
        assert current is not None and current.version == 2
        third = reopened.put(current.with_payload({"n": 3}), expected_version=2)
        assert third.version == 3
        assert third.created_at == first.created_at, "created_at immutable across reconnect + update"
    finally:
        reopened.close()


def test_fence_strictly_increases_per_resource(pg_schema):
    # The MINT half of fencing (docs 11 §5.2) against a real sequence: every
    # successful acquire of a resource carries a strictly larger fence than every
    # prior acquire of that resource -- including reclaim-after-expiry and
    # same-holder re-acquire. (The resource-side REJECT half is unit-tested above
    # without a DB.)
    from api.services.production.state_substrate.postgres_store import PostgresStateStore

    store = PostgresStateStore(pg_schema)
    try:
        # First acquire.
        a1 = store.acquire_lease("t", "shard-1", holder="worker-a", ttl_seconds=30, now=_T0)
        # Same holder re-acquires (idempotent extend) -> fresh token AND larger fence.
        a2 = store.acquire_lease(
            "t", "shard-1", holder="worker-a", ttl_seconds=30, now=_T0 + timedelta(seconds=1)
        )
        assert a2.token != a1.token
        assert a2.fence > a1.fence, "re-acquire advances the fence"

        # Let it lapse; a different holder reclaims -> larger fence still.
        a3 = store.acquire_lease(
            "t", "shard-1", holder="worker-b", ttl_seconds=30, now=_T0 + timedelta(seconds=100)
        )
        assert a3.holder == "worker-b"
        assert a3.fence > a2.fence, "reclaim-after-expiry advances the fence"

        # A different resource draws from the same monotonic sequence; its fence is
        # still strictly greater than anything minted before it (global monotonicity
        # implies per-resource monotonicity -- the property the resource check needs).
        b1 = store.acquire_lease("t", "shard-2", holder="worker-c", ttl_seconds=30, now=_T0)
        assert b1.fence > a3.fence

        # Feeding the minted fences, in acquire order, through a resource-side guard
        # for shard-1 is accepted monotonically; replaying the stale first fence is
        # then rejected -- the end-to-end story, with the real sequence on the mint
        # side and the guard on the check side.
        guard = FencingGuard()
        guard.check(a1.fence)
        guard.check(a2.fence)
        guard.check(a3.fence)
        with pytest.raises(StaleFenceToken):
            guard.check(a1.fence)  # stalled worker-a wakes with its old fence
    finally:
        store.close()
