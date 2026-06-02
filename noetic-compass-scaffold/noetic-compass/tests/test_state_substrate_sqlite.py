"""Contract + durability tests for the SQLite ``StateStore`` backend.

Two jobs:

* prove the SQLite backend passes the *same* backend-agnostic
  ``run_state_store_contract`` suite the reference store passes (substitutability), and
* prove the property the reference store deliberately CANNOT satisfy: committed
  records and leases **survive a close/reopen of the real database file**. That
  survival is the entire reason this backend exists, and the restart tests below
  are what earn it the right to call itself "durable on a single host."

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_sqlite.py -q
"""

from __future__ import annotations

import uuid

from api.services.production.state_substrate import (
    LedgerRecord,
    run_state_store_contract,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore

# A fixed, timezone-aware anchor mirrors the conformance suite so lease-expiry
# assertions are deterministic without ever sleeping.
from datetime import UTC, datetime, timedelta

_T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def test_sqlite_passes_state_store_contract(tmp_path):
    # The headline assertion: the SQLite backend satisfies every behaviour the
    # Protocol promises, exactly as the reference store does. The contract calls
    # the factory several times and expects each store to be isolated, so hand it
    # a UNIQUE database file per call.
    def factory() -> SqliteStateStore:
        return SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")

    run_state_store_contract(factory)


def test_records_survive_restart(tmp_path):
    # The durability proof for records: write to a real file, close it, then open a
    # brand-new store on the SAME path and confirm the committed state -- including
    # the full traceability envelope -- recovered intact.
    db = tmp_path / "ledger.db"

    store = SqliteStateStore(db)
    try:
        run_a = store.put(
            LedgerRecord.new(
                tenant_id="tenant-a",
                kind="run",
                record_id="run-001",
                payload={"status": "RUNNING", "shards": 4},
                parent_ids=("run-000",),
                source="restart-test",
                trace_id="trace-aaa",
            ),
            expected_version=0,
        )
        # A second tenant + a second kind, to prove tenant/kind partitioning also
        # survives the reopen (not just a single row).
        store.put(
            LedgerRecord.new(
                tenant_id="tenant-b",
                kind="worker",
                record_id="w-9",
                payload={"state": "idle"},
                source="restart-test",
                trace_id="trace-bbb",
            ),
            expected_version=0,
        )
        assert run_a.version == 1
    finally:
        store.close()

    # --- process-restart analogue: a fresh store object on the same file ---
    reopened = SqliteStateStore(db)
    try:
        fetched = reopened.get("tenant-a", "run", "run-001")
        assert fetched is not None, "committed record must survive reopen"
        assert fetched.version == 1
        assert fetched.payload == {"status": "RUNNING", "shards": 4}
        assert fetched.created_at == run_a.created_at, "created_at recovered exactly"
        assert fetched.updated_at == run_a.updated_at
        # Traceability envelope intact -- this is load-bearing for the project.
        assert fetched.source == "restart-test"
        assert fetched.trace_id == "trace-aaa"
        assert fetched.parent_ids == ("run-000",)

        # list recovers the row under the right tenant/kind...
        listed = reopened.list("tenant-a", "run")
        assert [r.record_id for r in listed] == ["run-001"]
        # ...and the other tenant's other-kind row survived independently.
        other = reopened.get("tenant-b", "worker", "w-9")
        assert other is not None and other.payload == {"state": "idle"}
        assert other.trace_id == "trace-bbb"
        # Fail-closed scoping still holds after reopen: tenant-b cannot see tenant-a's run.
        assert reopened.get("tenant-b", "run", "run-001") is None
    finally:
        reopened.close()


def test_leases_survive_restart(tmp_path):
    # The durability proof for leases: acquire with an injected `now` and a long
    # TTL, close, reopen on the same path, and confirm the live holder/token come
    # back -- and that the same lease reads as absent once `now` is past expiry.
    db = tmp_path / "leases.db"

    store = SqliteStateStore(db)
    try:
        lease = store.acquire_lease(
            "tenant-a", "shard-7", holder="worker-a", ttl_seconds=3600, now=_T0
        )
        token = lease.token
        holder = lease.holder
    finally:
        store.close()

    reopened = SqliteStateStore(db)
    try:
        # Inside the TTL window: the same holder and token are recovered.
        live = reopened.get_lease("tenant-a", "shard-7", now=_T0 + timedelta(seconds=10))
        assert live is not None, "committed lease must survive reopen"
        assert live.holder == holder
        assert live.token == token
        assert live.expires_at == _T0 + timedelta(seconds=3600)

        # Past expiry: the recovered lease reads as absent (expiry is decided by the
        # injected `now`, not by anything that was lost on restart).
        assert reopened.get_lease("tenant-a", "shard-7", now=_T0 + timedelta(seconds=3601)) is None
    finally:
        reopened.close()


def test_reopen_continues_version_sequence(tmp_path):
    # Versioning is a property of the durable ledger, not of any in-memory cache: a
    # record stored at version N, then reopened and updated, must go N -> N+1 with
    # no reset back to 1.
    db = tmp_path / "versions.db"

    store = SqliteStateStore(db)
    try:
        first = store.put(
            LedgerRecord.new(tenant_id="t", kind="run", record_id="r-1", payload={"n": 1}),
            expected_version=0,
        )
        second = store.put(first.with_payload({"n": 2}), expected_version=1)
        assert second.version == 2
    finally:
        store.close()

    reopened = SqliteStateStore(db)
    try:
        current = reopened.get("t", "run", "r-1")
        assert current is not None and current.version == 2

        # Updating the reopened record continues the sequence: 2 -> 3, not 1 -> 2.
        third = reopened.put(current.with_payload({"n": 3}), expected_version=2)
        assert third.version == 3
        assert third.created_at == first.created_at, "created_at immutable across restart + update"
    finally:
        reopened.close()
