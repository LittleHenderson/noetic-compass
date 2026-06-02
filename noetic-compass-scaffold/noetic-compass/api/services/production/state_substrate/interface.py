"""The durable run/worker/tenant state substrate -- contract layer.

Everything the public CAS Harness currently keeps in process-global dicts
(``_DISTRIBUTED_AUDITS``, ``_WORKERS``, ``_FLEET_RUNS``, ``_FRAGMENT_REFS``)
needs to survive a restart, span more than one host, and be partitioned by
tenant before the harness can carry real customers. This module defines the
*one* interface every such record goes through: a tenant-scoped, version-checked,
lease-aware key/value ledger.

Why an interface and not just a table:

* **Durability is a backend property, not an interface property.** The same
  ``StateStore`` Protocol is implemented by an in-memory reference store (fast,
  non-durable, for tests), a SQLite store (genuinely durable on a single host),
  and -- later -- Postgres/Redis (durable across hosts). Code that depends on the
  Protocol does not change when the durability tier changes. The honest claim a
  given deployment can make ("survives restart", "survives host loss") is exactly
  the claim its chosen backend earns, no more.
* **Tenant scoping is mandatory, not optional.** Every read and write takes an
  explicit ``tenant_id``. A read addressed to the wrong tenant fails closed
  (returns ``None`` / raises), so a coding mistake cannot leak one customer's run
  state into another's. This is the seam workstream 06 (tenant isolation) builds on.
* **Optimistic concurrency, not last-writer-wins.** Multi-host execution means two
  schedulers can race on the same run record. Every mutation carries the version
  the caller believed it was updating; a mismatch raises ``VersionConflict`` rather
  than silently clobbering. This is what makes the ledger safe under the fleet
  executor's lease/ack/merge flow when more than one process is live.
* **Single-holder expiring leases.** A worker, a shard placement, or a run-level
  "who owns the next scheduling pass" question all reduce to "exactly one holder at
  a time, and the hold lapses if the holder dies." That primitive lives here so
  every workstream gets the same tested semantics instead of re-deriving them.

Honesty note: this Protocol describes *behaviour*, not durability. ``InMemoryStateStore``
satisfies every method below and passes the full conformance suite, yet loses all
state when the process exits -- and says so. Do not read "implements StateStore" as
"durable." Durability is asserted only by backends whose tests prove survival across
a close/reopen of real storage (see ``test_state_substrate_sqlite.py`` once it lands).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Mapping, Optional, Protocol, runtime_checkable

# --- core scalar types -----------------------------------------------------
# Deliberately thin aliases: the substrate does not care what a tenant or record
# "is" beyond an opaque, comparable string. Keeping them as ``str`` means callers
# can adopt the ledger without first adopting a new identity type.

TenantId = str
RecordId = str
Kind = str
Version = int


def utc_now() -> datetime:
    """Single source of 'now' for the substrate, always timezone-aware UTC.

    Centralised so every record and lease timestamp is comparable and so tests
    can reason about ordering. Naive datetimes are a recurring footgun; the
    substrate never produces one.
    """

    return datetime.now(UTC)


def new_record_id(prefix: str) -> RecordId:
    """Generate a fresh, traceable record id of the form ``<prefix>-<uuid4hex>``.

    The prefix keeps ids human-greppable (``run-...``, ``worker-...``) without
    making them collide across kinds. Uniqueness comes from the uuid4 tail.
    """

    if not prefix or not prefix.isidentifier():
        raise StateStoreError(
            f"record-id prefix must be a non-empty identifier, got {prefix!r}"
        )
    return f"{prefix}-{uuid.uuid4().hex}"


# --- exceptions ------------------------------------------------------------


class StateStoreError(RuntimeError):
    """Base class for every substrate-level failure.

    Catching this catches all substrate errors without also catching unrelated
    runtime errors from the backend (e.g. a raw sqlite ``OperationalError``,
    which a backend is expected to translate into a subclass of this).
    """


class VersionConflict(StateStoreError):
    """A mutation's ``expected_version`` did not match the stored version.

    This is the optimistic-concurrency signal: the record changed underneath the
    caller. The honest response is almost never "retry blindly" -- it is "re-read,
    re-decide, re-attempt", because the state you based your decision on is stale.
    """

    def __init__(self, *, kind: Kind, record_id: RecordId, expected: Version, actual: Optional[Version]) -> None:
        self.kind = kind
        self.record_id = record_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"version conflict on {kind}/{record_id}: "
            f"expected version {expected}, store holds {actual}"
        )


class TenantScopeViolation(StateStoreError):
    """An operation tried to touch a record under the wrong tenant.

    Raised on the *mutating* paths (delete, lease handoff) where silently doing
    nothing would hide a bug. Read paths fail closed by returning ``None`` instead,
    so a cross-tenant read is indistinguishable from "not found" to the caller --
    that is intentional: one tenant must not even learn another's record exists.
    """


class LeaseHeld(StateStoreError):
    """Tried to acquire a lease that another holder currently owns (and it is live).

    Carries the conflicting holder so a scheduler can log *who* it lost the race to
    without a second round-trip.
    """

    def __init__(self, *, resource_id: str, holder: str) -> None:
        self.resource_id = resource_id
        self.holder = holder
        super().__init__(f"resource {resource_id!r} is already leased by {holder!r}")


class LeaseExpired(StateStoreError):
    """Tried to renew a lease whose TTL had already lapsed.

    Renew is not the same as re-acquire: an expired lease means the holder is
    presumed dead and the resource is free for *anyone*, so the original holder
    must go back through ``acquire_lease`` (and may lose to a competitor).
    """


class UnknownLease(StateStoreError):
    """Tried to renew or release a lease token the store has never issued (or already released)."""


class StaleFenceToken(StateStoreError):
    """A protected resource rejected a write carrying a stale (non-monotonic) fence.

    This is the *resource-side* half of the fencing-token defence (docs 11 §5.2).
    A lease's ``token`` proves ownership but not recency; the monotonic ``fence``
    minted at acquire time proves recency. A resource guards itself by remembering
    the highest fence it has acted on and rejecting any operation whose fence is
    less-than-or-equal to that high-water mark -- which is exactly how a stalled
    holder that wakes *after* its lease lapsed is stopped at the point of effect
    (the only place it can be stopped, since the lease layer has already, and
    correctly, handed the lease to a newer holder).

    Per Kleppmann ("How to do distributed locking"): fencing is "a property of the
    resource, not of the lock." This exception is the resource saying "your fence
    is older than one I've already honoured; I will not let you act."
    """

    def __init__(self, *, highest_seen: int, incoming: int) -> None:
        self.highest_seen = highest_seen
        self.incoming = incoming
        super().__init__(
            f"stale fence token: incoming fence {incoming} is not strictly greater "
            f"than the highest already honoured ({highest_seen}); refusing the write"
        )


# --- records ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """One durable, tenant-scoped, versioned object in the ledger.

    The payload is an opaque mapping -- the substrate does not interpret it. What
    the substrate *does* guarantee is the envelope around it: identity, tenant,
    version, timestamps, and the traceability fields the project treats as
    load-bearing (``parent_ids`` / ``source`` / ``trace_id``). Every object knows
    where it came from; that is the spine, not a feature.
    """

    record_id: RecordId
    tenant_id: TenantId
    kind: Kind
    version: Version
    created_at: datetime
    updated_at: datetime
    payload: Mapping[str, object]
    # --- traceability envelope (see project memory: object traceability is load-bearing)
    parent_ids: tuple[RecordId, ...] = ()
    source: str = "unknown"
    trace_id: Optional[str] = None

    @classmethod
    def new(
        cls,
        *,
        tenant_id: TenantId,
        kind: Kind,
        record_id: RecordId,
        payload: Mapping[str, object],
        parent_ids: tuple[RecordId, ...] = (),
        source: str = "unknown",
        trace_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> "LedgerRecord":
        """Build a *version-0* record. Persisting it via ``put(expected_version=0)``
        promotes it to version 1, so a stored record always has ``version >= 1``
        and version 0 unambiguously means "not yet persisted."
        """

        stamp = now or utc_now()
        return cls(
            record_id=record_id,
            tenant_id=tenant_id,
            kind=kind,
            version=0,
            created_at=stamp,
            updated_at=stamp,
            payload=dict(payload),
            parent_ids=tuple(parent_ids),
            source=source,
            trace_id=trace_id,
        )

    def with_payload(
        self,
        payload: Mapping[str, object],
        *,
        now: Optional[datetime] = None,
    ) -> "LedgerRecord":
        """Return a copy carrying a new payload and a bumped ``updated_at``.

        Version is intentionally *not* bumped here -- versioning is the store's job
        (it owns the source of truth), so the caller hands ``put`` the version it
        read and the store decides the next one. This keeps version monotonicity a
        property of the ledger, not of whoever happens to hold a record object.
        """

        return replace(self, payload=dict(payload), updated_at=now or utc_now())


@dataclass(frozen=True, slots=True)
class Lease:
    """A single-holder, time-boxed claim on a resource within a tenant.

    Identity is the opaque ``token``: only the holder of the token can renew or
    release. ``expires_at`` is absolute UTC so expiry is decidable by comparison
    against an injected ``now`` -- the substrate never sleeps to test expiry, and
    neither do its tests.
    """

    tenant_id: TenantId
    resource_id: str
    holder: str
    token: str
    acquired_at: datetime
    expires_at: datetime
    # --- fencing token (multi-host hazard fix; see docs 11 §5.2) ------------
    # ``token`` proves *ownership* but is a random uuid -- it carries no notion of
    # order, so a stalled holder that wakes after its lease lapsed cannot be told
    # apart from the live holder by token alone. ``fence`` is a *monotonically
    # increasing* integer minted at acquire time: every successful acquire of a
    # given resource gets a strictly larger fence than every prior acquire of that
    # resource. A protected resource (a WORM writer, a DB row) rejects any write
    # carrying a fence <= the highest it has already seen (see ``fencing.py`` and
    # the ``StaleFenceToken`` exception). It is an ADDITIVE field with a default of
    # 0, so every existing ``Lease(...)`` construction stays valid and the
    # in-memory / SQLite reference backends -- which do not fence -- simply leave it
    # at 0. Only a multi-host backend (Postgres) mints a real fence. This is an
    # interface-compatible strengthening, NOT a Protocol method change (docs 11
    # §5.2: "additive strengthening, not a Protocol change").
    fence: int = 0

    def is_expired(self, *, now: Optional[datetime] = None) -> bool:
        """True once wall-clock has passed ``expires_at``.

        Expiry is ``>=`` (a lease that expires exactly now is expired) so that a
        zero-TTL lease is never considered live -- there is no instant at which it
        could be safely treated as held.
        """

        return (now or utc_now()) >= self.expires_at


def require_tenant(record: Optional[LedgerRecord], tenant_id: TenantId) -> Optional[LedgerRecord]:
    """Fail closed: return ``record`` only if it belongs to ``tenant_id``.

    Used on read paths so a mismatched tenant is indistinguishable from "absent."
    A backend that filters by tenant in its query never reaches this, but it is a
    cheap defence-in-depth check for stores that key more loosely.
    """

    if record is None:
        return None
    if record.tenant_id != tenant_id:
        return None
    return record


# --- the contract ----------------------------------------------------------


@runtime_checkable
class StateStore(Protocol):
    """Tenant-scoped, versioned, lease-aware ledger -- the seam every workstream shares.

    Implementations must satisfy ``run_state_store_contract`` (see
    ``conformance.py``). The contract -- not this docstring -- is the spec; if a
    sentence here and a conformance sub-test disagree, the test wins and this text
    is the bug.

    Method contract summary:

    * ``put(record, expected_version)`` -- create or update. The store validates
      ``expected_version`` against what it holds (0 to create) and returns the
      stored record with its new version and ``updated_at``. ``VersionConflict`` on
      mismatch. Tenant + kind + record_id together identify a row.
    * ``get`` / ``list`` -- tenant-scoped reads. ``get`` returns ``None`` for absent
      *or* cross-tenant. ``list`` returns only the asking tenant's records of a kind,
      in a stable (created_at, record_id) order.
    * ``delete(expected_version)`` -- version-checked removal; ``VersionConflict`` on
      mismatch, ``TenantScopeViolation`` if the row exists under another tenant.
    * lease methods -- single-holder expiring claims; see ``Lease`` and the lease
      exceptions for the precise semantics. All take an optional ``now`` so expiry
      is testable without sleeping.
    * ``close`` -- release backend resources. Idempotent.
    """

    def put(self, record: LedgerRecord, *, expected_version: Version) -> LedgerRecord:
        ...

    def get(self, tenant_id: TenantId, kind: Kind, record_id: RecordId) -> Optional[LedgerRecord]:
        ...

    def list(self, tenant_id: TenantId, kind: Kind) -> tuple[LedgerRecord, ...]:
        ...

    def delete(self, tenant_id: TenantId, kind: Kind, record_id: RecordId, *, expected_version: Version) -> None:
        ...

    def acquire_lease(
        self,
        tenant_id: TenantId,
        resource_id: str,
        *,
        holder: str,
        ttl_seconds: float,
        now: Optional[datetime] = None,
    ) -> Lease:
        ...

    def renew_lease(self, token: str, *, ttl_seconds: float, now: Optional[datetime] = None) -> Lease:
        ...

    def release_lease(self, token: str) -> None:
        ...

    def get_lease(self, tenant_id: TenantId, resource_id: str, *, now: Optional[datetime] = None) -> Optional[Lease]:
        ...

    def close(self) -> None:
        ...
