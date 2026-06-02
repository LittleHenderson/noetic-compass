"""In-memory reference implementation of :class:`StateStore`.

This is the *reference* store: it defines, by construction, what every other
backend must agree with. It is fast, dependency-free, and thread-safe -- and it
is **not durable**. When the process exits, every record and lease is gone. That
is the honest boundary of this class, and it is the reason the SQLite and
Postgres backends exist.

Use it for:
* tests (it passes the full ``run_state_store_contract`` suite),
* local development where losing state on restart is fine,
* as the executable specification a durable backend is diffed against.

Do **not** use it where "survives restart" or "spans hosts" is a real requirement.
It cannot make those claims and does not pretend to.

Concurrency note: a single ``threading.RLock`` guards all state. This makes every
operation atomic with respect to every other, which is the simplest model that is
also correct. The substrate's operations are short (dict lookups), so lock
contention is not the bottleneck a real deployment would optimise -- a durable
multi-host backend pushes concurrency control into the database, where it belongs.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from .interface import (
    Kind,
    LeaseExpired,
    LeaseHeld,
    LedgerRecord,
    Lease,
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


class InMemoryStateStore(StateStore):
    """Process-local, thread-safe, non-durable ``StateStore``."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Records keyed by the full (tenant, kind, id) triple so that two tenants
        # may legitimately use the same record_id for unrelated rows.
        self._records: dict[tuple[TenantId, Kind, RecordId], LedgerRecord] = {}
        # Leases keyed by (tenant, resource); the token index lets renew/release
        # find a lease by token alone without scanning.
        self._leases: dict[tuple[TenantId, str], Lease] = {}
        self._token_index: dict[str, tuple[TenantId, str]] = {}
        self._closed = False

    # --- records -----------------------------------------------------------

    def put(self, record: LedgerRecord, *, expected_version: Version) -> LedgerRecord:
        self._ensure_open()
        key = (record.tenant_id, record.kind, record.record_id)
        with self._lock:
            current = self._records.get(key)
            current_version = current.version if current is not None else 0
            if current_version != expected_version:
                raise VersionConflict(
                    kind=record.kind,
                    record_id=record.record_id,
                    expected=expected_version,
                    actual=current_version,
                )
            # created_at is immutable across updates: the row's birth is a fact,
            # not something a later writer can rewrite. updated_at moves forward.
            created_at = current.created_at if current is not None else record.created_at
            now = utc_now()
            stored = LedgerRecord(
                record_id=record.record_id,
                tenant_id=record.tenant_id,
                kind=record.kind,
                version=expected_version + 1,
                created_at=created_at,
                updated_at=now if current is not None else record.updated_at,
                payload=dict(record.payload),
                parent_ids=tuple(record.parent_ids),
                source=record.source,
                trace_id=record.trace_id,
            )
            self._records[key] = stored
            return stored

    def get(self, tenant_id: TenantId, kind: Kind, record_id: RecordId) -> Optional[LedgerRecord]:
        self._ensure_open()
        with self._lock:
            record = self._records.get((tenant_id, kind, record_id))
            # Defence in depth: the key already scopes by tenant, but require_tenant
            # keeps the fail-closed contract explicit and survives future refactors.
            return require_tenant(record, tenant_id)

    def list(self, tenant_id: TenantId, kind: Kind) -> tuple[LedgerRecord, ...]:
        self._ensure_open()
        with self._lock:
            rows = [
                rec
                for (t, k, _), rec in self._records.items()
                if t == tenant_id and k == kind
            ]
        # Stable, meaningful order: insertion time, then id as a deterministic
        # tie-break. Callers that page or diff results can rely on it.
        rows.sort(key=lambda r: (r.created_at, r.record_id))
        return tuple(rows)

    def delete(self, tenant_id: TenantId, kind: Kind, record_id: RecordId, *, expected_version: Version) -> None:
        self._ensure_open()
        key = (tenant_id, kind, record_id)
        with self._lock:
            current = self._records.get(key)
            if current is None:
                # Also check whether the row exists under a *different* tenant: that
                # is a caller bug worth surfacing loudly, not a silent no-op.
                for (t, k, rid), rec in self._records.items():
                    if k == kind and rid == record_id and t != tenant_id:
                        raise TenantScopeViolation(
                            f"delete addressed tenant {tenant_id!r} but {kind}/{record_id} "
                            f"belongs to another tenant"
                        )
                # Deleting something absent is a version conflict (expected != 0),
                # unless the caller also expected absence (expected_version 0), which
                # we treat as an idempotent no-op.
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
            del self._records[key]

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
        key = (tenant_id, resource_id)
        with self._lock:
            existing = self._leases.get(key)
            if existing is not None and not existing.is_expired(now=stamp):
                if existing.holder != holder:
                    # Live lease owned by someone else: the caller lost the race.
                    raise LeaseHeld(resource_id=resource_id, holder=existing.holder)
                # Same holder re-acquiring a live lease: idempotent extend. Retire the
                # old token so a stale token cannot renew a lease the holder has moved on
                # from, and issue a fresh one.
                self._token_index.pop(existing.token, None)
            elif existing is not None:
                # Expired lease (possibly another holder's): reclaim it.
                self._token_index.pop(existing.token, None)
            lease = self._make_lease(tenant_id, resource_id, holder, stamp, ttl_seconds)
            self._leases[key] = lease
            self._token_index[lease.token] = key
            return lease

    def renew_lease(self, token: str, *, ttl_seconds: float, now: Optional[datetime] = None) -> Lease:
        self._ensure_open()
        if ttl_seconds <= 0:
            raise StateStoreError("ttl_seconds must be positive")
        stamp = now or utc_now()
        with self._lock:
            key = self._token_index.get(token)
            if key is None:
                raise UnknownLease(f"no live lease for token {token!r}")
            lease = self._leases.get(key)
            if lease is None or lease.token != token:
                # Token was superseded (e.g. by a re-acquire) or already released.
                self._token_index.pop(token, None)
                raise UnknownLease(f"no live lease for token {token!r}")
            if lease.is_expired(now=stamp):
                # Renew never resurrects a dead lease -- the holder is presumed gone and
                # the resource is free for anyone. Force them back through acquire.
                raise LeaseExpired(
                    f"lease on {lease.resource_id!r} expired at {lease.expires_at.isoformat()}"
                )
            renewed = self._make_lease(
                lease.tenant_id, lease.resource_id, lease.holder, stamp, ttl_seconds, token=token
            )
            self._leases[key] = renewed
            return renewed

    def release_lease(self, token: str) -> None:
        self._ensure_open()
        with self._lock:
            key = self._token_index.pop(token, None)
            if key is None:
                # Releasing an unknown/already-released token is an idempotent no-op:
                # the post-condition ("this token holds nothing") already holds.
                return
            lease = self._leases.get(key)
            if lease is not None and lease.token == token:
                del self._leases[key]

    def get_lease(self, tenant_id: TenantId, resource_id: str, *, now: Optional[datetime] = None) -> Optional[Lease]:
        self._ensure_open()
        stamp = now or utc_now()
        with self._lock:
            lease = self._leases.get((tenant_id, resource_id))
            if lease is None:
                return None
            if lease.is_expired(now=stamp):
                # An expired lease is reported as absent: callers ask "is this held?"
                # and the honest answer for a lapsed lease is "no."
                return None
            return lease

    def close(self) -> None:
        # Idempotent. We drop references so a use-after-close is a loud error rather
        # than silently operating on a store the caller thinks is gone.
        with self._lock:
            self._closed = True
            self._records.clear()
            self._leases.clear()
            self._token_index.clear()

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

    def _ensure_open(self) -> None:
        if self._closed:
            raise StateStoreError("operation on a closed InMemoryStateStore")
