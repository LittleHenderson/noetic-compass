"""Durable run/worker/tenant state substrate -- the ledger the public product needs.

The public CAS Harness today keeps its run, worker, fleet, and fragment state in
process-global dictionaries (``_DISTRIBUTED_AUDITS``, ``_WORKERS``, ``_FLEET_RUNS``,
``_FRAGMENT_REFS``). That is fine for a single process that never restarts and
serves one tenant. It is fatal for a public product: the state vanishes on restart,
cannot be shared across hosts, and is not partitioned by customer. Fleet-scale,
queue/resume, observability, billing, tenant isolation, and compliance all sit on
top of that state -- so none of them can be made real until the state itself is
durable, multi-host-ready, and tenant-scoped.

This package is that foundation. Unlike the single-file interface *scaffolds* that
are this subpackage's siblings (``../fleet_scale.py``, ``../billing.py``, etc. --
import-isolated Protocol/ABC sketches with clearly-labelled in-memory stubs), the
code here is **real, tested infrastructure**:

* ``StateStore`` (in ``interface``) -- the tenant-scoped, version-checked,
  lease-aware ledger contract every record goes through.
* ``InMemoryStateStore`` (in ``memory_store``) -- a fast, thread-safe **reference**
  implementation. It passes the full conformance suite and is the executable
  specification a durable backend is diffed against. It is **not durable**: state is
  lost on process exit, and it says so.
* ``run_state_store_contract`` (in ``conformance``) -- the shared, backend-agnostic
  contract. Every backend (in-memory now; SQLite, Postgres/Redis later) must pass
  the *same* assertions, which is what makes "swap the backend, keep the behaviour"
  a checked fact rather than a hope.

Honesty boundary -- which durability claims are honest:

* In-memory: behaviourally complete, **non-durable**. "Survives restart"? No.
* SQLite (forthcoming ``sqlite_store``): durable on a **single host** (WAL + fsync);
  its tests must prove survival across a close/reopen of the same file.
* Postgres/Redis (forthcoming): durable across **hosts**; adds distributed lease
  semantics behind the identical interface.

A deployment may make exactly the durability claim its chosen backend's tests earn
-- no more. Picking ``InMemoryStateStore`` and calling the product "durable" would be
the same dishonesty this whole program exists to refuse.

Not yet wired in: this substrate is not yet substituted for the live global dicts.
That cutover is a deliberate, phased migration spelled out in
``docs/working/production_readiness/10_state_substrate_migration.md`` -- it touches
the request-handling path, so it lands behind tests and a kill/validate gate, not in
one risky sweep.
"""

from __future__ import annotations

from .conformance import run_state_store_contract
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
    new_record_id,
    require_tenant,
    utc_now,
)
from .memory_store import InMemoryStateStore
from .migration import INTERIM_TENANT, Divergence, LedgerMirror

__all__ = [
    # interface
    "StateStore",
    "LedgerRecord",
    "Lease",
    "TenantId",
    "RecordId",
    "Kind",
    "Version",
    "StateStoreError",
    "VersionConflict",
    "TenantScopeViolation",
    "LeaseHeld",
    "LeaseExpired",
    "UnknownLease",
    "require_tenant",
    "utc_now",
    "new_record_id",
    # reference backend
    "InMemoryStateStore",
    # contract
    "run_state_store_contract",
    # strangler-fig migration seam (docs 10: dual-write / shadow-read)
    "LedgerMirror",
    "Divergence",
    "INTERIM_TENANT",
]
