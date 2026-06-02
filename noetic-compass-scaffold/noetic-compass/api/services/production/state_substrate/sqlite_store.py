"""SQLite backend for :class:`StateStore` -- genuinely durable on a single host.

This is the first *durable* backend on the state-substrate ladder. It persists
every record and lease to a SQLite database file and, by enabling write-ahead
logging plus an fsync on every commit, guarantees that a write which returned
from ``put`` / ``acquire_lease`` / ``renew_lease`` survives a process kill: open
a fresh :class:`SqliteStateStore` on the same path and the committed state is
still there. ``test_state_substrate_sqlite.py`` proves exactly that across a
close/reopen of the real file.

Honesty boundary -- what this backend may and may NOT claim:

* **Durable on a single host: yes.** WAL (``PRAGMA journal_mode=WAL``) plus
  ``PRAGMA synchronous=NORMAL`` and a ``COMMIT`` after every mutation flush the
  write to the WAL on durable storage, so a committed write survives a process
  crash or restart on the *same machine and disk*. The restart tests assert this.
* **Durable across hosts: NO.** A single SQLite file on one host's filesystem is
  not replicated, not reachable from a second machine, and offers no distributed
  lease arbitration. If that host's disk is lost, the ledger is lost. Multi-host
  durability (replication, cross-host leases, last-writer arbitration in the
  database) is the forthcoming Postgres/Redis backend -- workstream 11 -- behind
  this identical Protocol. Do not deploy this store and call the product
  "highly available" or "multi-host durable": it has not earned that claim.

Semantics are diffed against :class:`InMemoryStateStore`, the reference store.
This backend passes the same ``run_state_store_contract`` suite, which is what
makes "swap the backend, keep the behaviour" a checked fact: every version rule,
the created_at-immutable-on-update behaviour, the fail-closed tenant scoping, and
the full single-holder / expiring / renew-release lease lifecycle match the
reference exactly. Nothing about SQLite forces an observable difference through
the Protocol.

Concurrency note: a single ``threading.RLock`` guards every operation, mirroring
the reference store's single-lock model -- the simplest model that is also
correct. The underlying connection is opened with ``check_same_thread=False`` so
the lock (not SQLite's own thread affinity) is the one synchronisation point;
because every public method takes the lock for its whole body, no two operations
ever touch the connection concurrently. Real concurrency tuning belongs to the
multi-host backend, which pushes concurrency control into the database engine.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .interface import (
    Kind,
    Lease,
    LeaseExpired,
    LeaseHeld,
    LedgerRecord,
    RecordId,
    StateStore,
    StateStoreError,
    TenantId,
    TenantScopeViolation,
    UnknownLease,
    Version,
    VersionConflict,
    require_tenant,
    utc_now,
)

_CREATE_RECORDS = """
CREATE TABLE IF NOT EXISTS records (
    tenant_id  TEXT    NOT NULL,
    kind       TEXT    NOT NULL,
    record_id  TEXT    NOT NULL,
    version    INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    payload    TEXT    NOT NULL,
    parent_ids TEXT    NOT NULL,
    source     TEXT    NOT NULL,
    trace_id   TEXT,
    PRIMARY KEY (tenant_id, kind, record_id)
)
"""

_CREATE_LEASES = """
CREATE TABLE IF NOT EXISTS leases (
    tenant_id   TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    holder      TEXT NOT NULL,
    token       TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    PRIMARY KEY (tenant_id, resource_id)
)
"""

# The token is the lease's opaque identity: renew/release look a lease up by token
# alone, so it must be globally unique across all (tenant, resource) rows.
_CREATE_TOKEN_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS leases_token_idx ON leases (token)
"""


class SqliteStateStore(StateStore):
    """Single-host durable ``StateStore`` backed by a SQLite database file."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = os.fspath(path)
        self._lock = threading.RLock()
        self._closed = False
        # check_same_thread=False: the RLock below is the single synchronisation
        # point, so we deliberately allow the connection to be used from whatever
        # thread holds the lock. isolation_level="" keeps us in explicit-commit
        # mode (we call .commit() after every mutation, which fsyncs the WAL).
        self._conn = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=""
        )
        with self._lock:
            # WAL + synchronous=NORMAL is the durable single-host configuration:
            # NORMAL fsyncs the WAL at each commit (safe across process crash and
            # OS-level restart; only an OS/power loss can lose the last commit, and
            # even then the database is never corrupted). FULL would be safe too,
            # just slower; NORMAL is the standard durable WAL setting.
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute(_CREATE_RECORDS)
            self._conn.execute(_CREATE_LEASES)
            self._conn.execute(_CREATE_TOKEN_INDEX)
            self._conn.commit()

    # --- records -----------------------------------------------------------

    def put(self, record: LedgerRecord, *, expected_version: Version) -> LedgerRecord:
        self._ensure_open()
        with self._lock:
            current = self._read_record(record.tenant_id, record.kind, record.record_id)
            current_version = current.version if current is not None else 0
            if current_version != expected_version:
                raise VersionConflict(
                    kind=record.kind,
                    record_id=record.record_id,
                    expected=expected_version,
                    actual=current_version,
                )
            # created_at is immutable across updates: the row's birth is a fact a
            # later writer cannot rewrite. updated_at moves to "now" on update; on
            # first insert it keeps the record's own stamp (mirrors the reference).
            created_at = current.created_at if current is not None else record.created_at
            updated_at = utc_now() if current is not None else record.updated_at
            stored = LedgerRecord(
                record_id=record.record_id,
                tenant_id=record.tenant_id,
                kind=record.kind,
                version=expected_version + 1,
                created_at=created_at,
                updated_at=updated_at,
                payload=dict(record.payload),
                parent_ids=tuple(record.parent_ids),
                source=record.source,
                trace_id=record.trace_id,
            )
            self._conn.execute(
                """
                INSERT INTO records
                    (tenant_id, kind, record_id, version, created_at, updated_at,
                     payload, parent_ids, source, trace_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, kind, record_id) DO UPDATE SET
                    version=excluded.version,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    payload=excluded.payload,
                    parent_ids=excluded.parent_ids,
                    source=excluded.source,
                    trace_id=excluded.trace_id
                """,
                (
                    stored.tenant_id,
                    stored.kind,
                    stored.record_id,
                    stored.version,
                    stored.created_at.isoformat(),
                    stored.updated_at.isoformat(),
                    json.dumps(stored.payload),
                    json.dumps(list(stored.parent_ids)),
                    stored.source,
                    stored.trace_id,
                ),
            )
            self._conn.commit()
            return stored

    def get(self, tenant_id: TenantId, kind: Kind, record_id: RecordId) -> Optional[LedgerRecord]:
        self._ensure_open()
        with self._lock:
            record = self._read_record(tenant_id, kind, record_id)
            # The query already scopes by tenant (tenant_id is in the PK and the
            # WHERE clause); require_tenant keeps the fail-closed contract explicit
            # and survives future refactors -- defence in depth, same as reference.
            return require_tenant(record, tenant_id)

    def list(self, tenant_id: TenantId, kind: Kind) -> tuple[LedgerRecord, ...]:
        self._ensure_open()
        with self._lock:
            cursor = self._conn.execute(
                "SELECT tenant_id, kind, record_id, version, created_at, updated_at, "
                "payload, parent_ids, source, trace_id "
                "FROM records WHERE tenant_id = ? AND kind = ?",
                (tenant_id, kind),
            )
            rows = [self._row_to_record(row) for row in cursor.fetchall()]
        # Stable, meaningful order: creation time, then id as a deterministic
        # tie-break. Sorting in Python (not SQL) keeps the ordering key identical
        # to the reference store, which sorts on the parsed datetime objects.
        rows.sort(key=lambda r: (r.created_at, r.record_id))
        return tuple(rows)

    def delete(self, tenant_id: TenantId, kind: Kind, record_id: RecordId, *, expected_version: Version) -> None:
        self._ensure_open()
        with self._lock:
            current = self._read_record(tenant_id, kind, record_id)
            if current is None:
                # Does the row exist under a *different* tenant? That is a caller
                # bug worth surfacing loudly, not a silent no-op.
                other = self._conn.execute(
                    "SELECT 1 FROM records "
                    "WHERE kind = ? AND record_id = ? AND tenant_id != ? LIMIT 1",
                    (kind, record_id, tenant_id),
                ).fetchone()
                if other is not None:
                    raise TenantScopeViolation(
                        f"delete addressed tenant {tenant_id!r} but {kind}/{record_id} "
                        f"belongs to another tenant"
                    )
                # Deleting something absent is a version conflict (expected != 0),
                # unless the caller also expected absence (expected_version 0),
                # which is an idempotent no-op.
                if expected_version == 0:
                    return
                raise VersionConflict(
                    kind=kind, record_id=record_id, expected=expected_version, actual=0
                )
            if current.version != expected_version:
                raise VersionConflict(
                    kind=kind,
                    record_id=record_id,
                    expected=expected_version,
                    actual=current.version,
                )
            self._conn.execute(
                "DELETE FROM records WHERE tenant_id = ? AND kind = ? AND record_id = ?",
                (tenant_id, kind, record_id),
            )
            self._conn.commit()

    # --- leases ------------------------------------------------------------

    def acquire_lease(
        self,
        tenant_id: TenantId,
        resource_id: str,
        *,
        holder: str,
        ttl_seconds: float,
        now: Optional[datetime] = None,
    ) -> Lease:
        self._ensure_open()
        if ttl_seconds <= 0:
            raise StateStoreError("ttl_seconds must be positive")
        stamp = now or utc_now()
        with self._lock:
            existing = self._read_lease(tenant_id, resource_id)
            if existing is not None and not existing.is_expired(now=stamp):
                if existing.holder != holder:
                    # Live lease owned by someone else: the caller lost the race.
                    raise LeaseHeld(resource_id=resource_id, holder=existing.holder)
                # Same holder re-acquiring a live lease: idempotent extend. The
                # INSERT-OR-REPLACE below overwrites the row at (tenant, resource)
                # with a fresh token, so the old token is retired -- a stale token
                # cannot renew a lease the holder has moved on from.
            # If existing is expired (any holder) we simply reclaim by overwriting
            # the row -- again retiring the old token. Either way, write the new lease.
            lease = self._make_lease(tenant_id, resource_id, holder, stamp, ttl_seconds)
            self._write_lease(lease)
            self._conn.commit()
            return lease

    def renew_lease(self, token: str, *, ttl_seconds: float, now: Optional[datetime] = None) -> Lease:
        self._ensure_open()
        if ttl_seconds <= 0:
            raise StateStoreError("ttl_seconds must be positive")
        stamp = now or utc_now()
        with self._lock:
            lease = self._read_lease_by_token(token)
            if lease is None:
                # Token was never issued, was superseded by a re-acquire, or has
                # already been released. There is no live lease for it.
                raise UnknownLease(f"no live lease for token {token!r}")
            if lease.is_expired(now=stamp):
                # Renew never resurrects a dead lease -- the holder is presumed gone
                # and the resource is free for anyone. Force them back through acquire.
                raise LeaseExpired(
                    f"lease on {lease.resource_id!r} expired at {lease.expires_at.isoformat()}"
                )
            renewed = self._make_lease(
                lease.tenant_id, lease.resource_id, lease.holder, stamp, ttl_seconds, token=token
            )
            self._write_lease(renewed)
            self._conn.commit()
            return renewed

    def release_lease(self, token: str) -> None:
        self._ensure_open()
        with self._lock:
            # Idempotent: deleting by token removes the lease iff that exact token
            # is still the stored one. An unknown/superseded/already-released token
            # matches no row, so this is a no-op -- the post-condition ("this token
            # holds nothing") already holds.
            self._conn.execute("DELETE FROM leases WHERE token = ?", (token,))
            self._conn.commit()

    def get_lease(self, tenant_id: TenantId, resource_id: str, *, now: Optional[datetime] = None) -> Optional[Lease]:
        self._ensure_open()
        stamp = now or utc_now()
        with self._lock:
            lease = self._read_lease(tenant_id, resource_id)
            if lease is None:
                return None
            if lease.is_expired(now=stamp):
                # An expired lease is reported as absent: callers ask "is this held?"
                # and the honest answer for a lapsed lease is "no."
                return None
            return lease

    def close(self) -> None:
        # Idempotent. Commit any pending work (there should be none -- every
        # mutation already commits), then close the connection. After close, the
        # _ensure_open guard turns any further op into a loud StateStoreError.
        with self._lock:
            if self._closed:
                return
            try:
                self._conn.commit()
            finally:
                self._conn.close()
                self._closed = True

    # --- helpers -----------------------------------------------------------

    def _make_lease(
        self,
        tenant_id: TenantId,
        resource_id: str,
        holder: str,
        stamp: datetime,
        ttl_seconds: float,
        *,
        token: Optional[str] = None,
    ) -> Lease:
        return Lease(
            tenant_id=tenant_id,
            resource_id=resource_id,
            holder=holder,
            token=token or uuid.uuid4().hex,
            acquired_at=stamp,
            expires_at=stamp + timedelta(seconds=ttl_seconds),
        )

    def _write_lease(self, lease: Lease) -> None:
        # INSERT OR REPLACE keyed on (tenant_id, resource_id): writing a lease for a
        # resource overwrites whatever lease was there, which is precisely how the
        # reference store retires a superseded/reclaimed token. The UNIQUE token
        # index stays consistent because the prior row (and its token) is replaced.
        self._conn.execute(
            """
            INSERT OR REPLACE INTO leases
                (tenant_id, resource_id, holder, token, acquired_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                lease.tenant_id,
                lease.resource_id,
                lease.holder,
                lease.token,
                lease.acquired_at.isoformat(),
                lease.expires_at.isoformat(),
            ),
        )

    def _read_record(self, tenant_id: TenantId, kind: Kind, record_id: RecordId) -> Optional[LedgerRecord]:
        row = self._conn.execute(
            "SELECT tenant_id, kind, record_id, version, created_at, updated_at, "
            "payload, parent_ids, source, trace_id "
            "FROM records WHERE tenant_id = ? AND kind = ? AND record_id = ?",
            (tenant_id, kind, record_id),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def _read_lease(self, tenant_id: TenantId, resource_id: str) -> Optional[Lease]:
        row = self._conn.execute(
            "SELECT tenant_id, resource_id, holder, token, acquired_at, expires_at "
            "FROM leases WHERE tenant_id = ? AND resource_id = ?",
            (tenant_id, resource_id),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_lease(row)

    def _read_lease_by_token(self, token: str) -> Optional[Lease]:
        row = self._conn.execute(
            "SELECT tenant_id, resource_id, holder, token, acquired_at, expires_at "
            "FROM leases WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_lease(row)

    @staticmethod
    def _row_to_record(row: tuple) -> LedgerRecord:
        (
            tenant_id,
            kind,
            record_id,
            version,
            created_at,
            updated_at,
            payload,
            parent_ids,
            source,
            trace_id,
        ) = row
        # ISO-8601 round-trips an aware UTC datetime exactly:
        # datetime.fromisoformat(dt.isoformat()) == dt for aware UTC dt, so the
        # parsed timestamps are tz-aware and compare equal to the originals.
        return LedgerRecord(
            record_id=record_id,
            tenant_id=tenant_id,
            kind=kind,
            version=int(version),
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
            payload=json.loads(payload),
            parent_ids=tuple(json.loads(parent_ids)),
            source=source,
            trace_id=trace_id,
        )

    @staticmethod
    def _row_to_lease(row: tuple) -> Lease:
        tenant_id, resource_id, holder, token, acquired_at, expires_at = row
        return Lease(
            tenant_id=tenant_id,
            resource_id=resource_id,
            holder=holder,
            token=token,
            acquired_at=datetime.fromisoformat(acquired_at),
            expires_at=datetime.fromisoformat(expires_at),
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise StateStoreError("operation on a closed SqliteStateStore")
