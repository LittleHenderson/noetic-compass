"""SQLite backend for :class:`StateStore` on one host and database file.

This backend persists records and leases to a SQLite database file. The current
tests establish close/reopen persistence for that file and compare-and-swap
arbitration between two independent connections to the same file. They do not
inject a process crash, operating-system restart, power loss, filesystem fault,
or storage-device failure, so this module makes no tested durability claim for
those events.

Honesty boundary -- what this backend may and may NOT claim:

* **Close/reopen persistence on one tested host/file: yes.** The store uses WAL,
  ``PRAGMA synchronous=NORMAL``, and a ``COMMIT`` after every mutation. The tests
  close one store and reopen the same file; they do not prove an fsync boundary,
  crash survival, OS-restart survival, or power-loss survival.
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

Concurrency note: a ``threading.RLock`` guards each connection within its process,
and every read-modify-write mutation starts ``BEGIN IMMEDIATE`` before reading.
SQLite's database write lock therefore serializes independent connections and
processes using the same single-host database file; expected-version decisions are
made inside that transaction. This is same-file arbitration, not replication,
host-loss survival, or multi-host authority. Those stronger properties still
belong to the shared Postgres backend.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
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
    """Single-host ``StateStore`` backed by one SQLite database file."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = os.fspath(path)
        self._lock = threading.RLock()
        self._closed = False
        # check_same_thread=False lets the per-connection RLock serialize local
        # threads. Cross-connection/process mutations are serialized separately by
        # BEGIN IMMEDIATE in _write_transaction. isolation_level="" permits those
        # explicit transactions and commits.
        self._conn = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=""
        )
        with self._lock:
            # WAL + synchronous=NORMAL is the configured local persistence mode.
            # Current evidence covers close/reopen and two-connection same-file
            # arbitration only; it does not test fsync, crash, OS-restart, power-
            # loss, corruption, or storage-device guarantees.
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
            with self._write_transaction():
                current = self._read_record(
                    record.tenant_id, record.kind, record.record_id
                )
                current_version = current.version if current is not None else 0
                if current_version != expected_version:
                    raise VersionConflict(
                        kind=record.kind,
                        record_id=record.record_id,
                        expected=expected_version,
                        actual=current_version,
                    )
                # created_at is immutable across updates: the row's birth is a fact
                # a later writer cannot rewrite. updated_at moves to "now" on
                # update; on first insert it keeps the record's own stamp.
                created_at = (
                    current.created_at if current is not None else record.created_at
                )
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
                if current is None:
                    try:
                        self._conn.execute(
                            """
                            INSERT INTO records
                                (tenant_id, kind, record_id, version, created_at,
                                 updated_at, payload, parent_ids, source, trace_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            self._record_values(stored),
                        )
                    except sqlite3.IntegrityError as exc:
                        actual = self._read_record(
                            record.tenant_id, record.kind, record.record_id
                        )
                        if actual is not None:
                            raise VersionConflict(
                                kind=record.kind,
                                record_id=record.record_id,
                                expected=expected_version,
                                actual=actual.version,
                            ) from exc
                        raise
                else:
                    cursor = self._conn.execute(
                        """
                        UPDATE records SET
                            version = ?, updated_at = ?, payload = ?, parent_ids = ?,
                            source = ?, trace_id = ?
                        WHERE tenant_id = ? AND kind = ? AND record_id = ?
                          AND version = ?
                        """,
                        (
                            stored.version,
                            stored.updated_at.isoformat(),
                            json.dumps(stored.payload),
                            json.dumps(list(stored.parent_ids)),
                            stored.source,
                            stored.trace_id,
                            stored.tenant_id,
                            stored.kind,
                            stored.record_id,
                            expected_version,
                        ),
                    )
                    if cursor.rowcount != 1:
                        actual = self._read_record(
                            record.tenant_id, record.kind, record.record_id
                        )
                        raise VersionConflict(
                            kind=record.kind,
                            record_id=record.record_id,
                            expected=expected_version,
                            actual=actual.version if actual is not None else 0,
                        )
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
            with self._write_transaction():
                current = self._read_record(tenant_id, kind, record_id)
                if current is None:
                    # Does the row exist under a *different* tenant? That is a
                    # caller bug worth surfacing loudly, not a silent no-op.
                    other = self._conn.execute(
                        "SELECT 1 FROM records "
                        "WHERE kind = ? AND record_id = ? AND tenant_id != ? LIMIT 1",
                        (kind, record_id, tenant_id),
                    ).fetchone()
                    if other is not None:
                        raise TenantScopeViolation(
                            f"delete addressed tenant {tenant_id!r} but "
                            f"{kind}/{record_id} belongs to another tenant"
                        )
                    # Deleting something absent is a version conflict
                    # (expected != 0), unless the caller also expected absence.
                    if expected_version == 0:
                        return
                    raise VersionConflict(
                        kind=kind,
                        record_id=record_id,
                        expected=expected_version,
                        actual=0,
                    )
                if current.version != expected_version:
                    raise VersionConflict(
                        kind=kind,
                        record_id=record_id,
                        expected=expected_version,
                        actual=current.version,
                    )
                cursor = self._conn.execute(
                    "DELETE FROM records WHERE tenant_id = ? AND kind = ? "
                    "AND record_id = ? AND version = ?",
                    (tenant_id, kind, record_id, expected_version),
                )
                if cursor.rowcount != 1:
                    actual = self._read_record(tenant_id, kind, record_id)
                    raise VersionConflict(
                        kind=kind,
                        record_id=record_id,
                        expected=expected_version,
                        actual=actual.version if actual is not None else 0,
                    )

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
            with self._write_transaction():
                existing = self._read_lease(tenant_id, resource_id)
                if existing is not None and not existing.is_expired(now=stamp):
                    if existing.holder != holder:
                        # Live lease owned by someone else: the caller lost the race.
                        raise LeaseHeld(
                            resource_id=resource_id, holder=existing.holder
                        )
                    # Same holder re-acquiring a live lease: idempotent extend. The
                    # replacement retires the old token.
                # An expired lease may be reclaimed by either holder.
                lease = self._make_lease(
                    tenant_id, resource_id, holder, stamp, ttl_seconds
                )
                self._write_lease(lease)
                return lease

    def renew_lease(self, token: str, *, ttl_seconds: float, now: Optional[datetime] = None) -> Lease:
        self._ensure_open()
        if ttl_seconds <= 0:
            raise StateStoreError("ttl_seconds must be positive")
        stamp = now or utc_now()
        with self._lock:
            with self._write_transaction():
                lease = self._read_lease_by_token(token)
                if lease is None:
                    # Token was never issued, was superseded by a re-acquire, or
                    # has already been released.
                    raise UnknownLease(f"no live lease for token {token!r}")
                if lease.is_expired(now=stamp):
                    # Renew never resurrects a dead lease.
                    raise LeaseExpired(
                        f"lease on {lease.resource_id!r} expired at "
                        f"{lease.expires_at.isoformat()}"
                    )
                renewed = self._make_lease(
                    lease.tenant_id,
                    lease.resource_id,
                    lease.holder,
                    stamp,
                    ttl_seconds,
                    token=token,
                )
                cursor = self._conn.execute(
                    """
                    UPDATE leases SET acquired_at = ?, expires_at = ?
                    WHERE tenant_id = ? AND resource_id = ? AND token = ?
                    """,
                    (
                        renewed.acquired_at.isoformat(),
                        renewed.expires_at.isoformat(),
                        renewed.tenant_id,
                        renewed.resource_id,
                        token,
                    ),
                )
                if cursor.rowcount != 1:
                    raise UnknownLease(f"no live lease for token {token!r}")
                return renewed

    def release_lease(self, token: str) -> None:
        self._ensure_open()
        with self._lock:
            # Idempotent: deleting by token removes the lease iff that exact token
            # is still the stored one. An unknown/superseded/already-released token
            # matches no row, so this is a no-op -- the post-condition ("this token
            # holds nothing") already holds.
            with self._write_transaction():
                self._conn.execute("DELETE FROM leases WHERE token = ?", (token,))

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

    @contextmanager
    def _write_transaction(self) -> Iterator[None]:
        """Serialize one read-modify-write decision across SQLite connections."""

        if self._conn.in_transaction:
            raise StateStoreError("nested SQLite write transaction is not supported")
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            yield
            self._conn.commit()
        except sqlite3.Error as exc:
            if self._conn.in_transaction:
                self._conn.rollback()
            raise StateStoreError(f"SQLite write transaction failed: {exc}") from exc
        except BaseException:
            if self._conn.in_transaction:
                self._conn.rollback()
            raise

    @staticmethod
    def _record_values(record: LedgerRecord) -> tuple[object, ...]:
        return (
            record.tenant_id,
            record.kind,
            record.record_id,
            record.version,
            record.created_at.isoformat(),
            record.updated_at.isoformat(),
            json.dumps(record.payload),
            json.dumps(list(record.parent_ids)),
            record.source,
            record.trace_id,
        )

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
