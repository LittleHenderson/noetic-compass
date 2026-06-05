"""Per-tenant ownership of evidence traces -- the isolation primitive for evidence routes.

The evidence routes (``api/routes/evidence.py``) serve a trace by ``trace_id`` alone. Today that
is fine: in the legacy shared-secret posture there is exactly one trust boundary, so any
authenticated caller may read any trace. Once per-account identity is turned on
(``settings.accounts_enabled``), that is a cross-tenant leak: tenant B must not be able to read,
verify, or anchor a trace that tenant A produced.

This module is the ownership ledger that closes that gap. It records, per (tenant, trace), the
fact "this tenant owns this trace," and answers the one question the route guard asks: "does this
tenant own this trace?" The isolation is NOT enforced here by a hand-rolled tenant comparison --
it is enforced by the :class:`StateStore`'s mandatory tenant partitioning. A record written under
tenant A's id is simply invisible to ``store.get(tenant_B, ...)`` (the store returns ``None`` for a
cross-tenant read, indistinguishable from "absent"; see
``api/services/production/state_substrate/interface.py``). So ``tenant_owns_trace`` is a thin,
honest read over that partitioning, not a second, drift-prone access-control mechanism.

Every record carries the project's traceability envelope (``created_at`` / ``version`` / ``source``
/ ``trace_id``): every object knows where it came from. The ledger's optimistic-concurrency
contract (``put(expected_version=0)`` to create, ``VersionConflict`` if it already exists) is
handled here so a duplicate ownership write is idempotent, never an error: recording ownership of a
trace that is already owned by the same tenant is a no-op.

These are pure functions over a ``StateStore``; they do not know about FastAPI, requests, or
settings. The route layer decides WHEN to consult them (only in account mode); this module only
provides the read and the write.
"""

from __future__ import annotations

from typing import Optional

from api.services.production.state_substrate.interface import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

# The record ``kind`` under which evidence ownership rows live in the ledger. A distinct kind keeps
# these rows from colliding with account/session/run rows that share the same store, and makes the
# ownership namespace greppable.
EVIDENCE_OWNERSHIP_KIND = "evidence_ownership"

# Default provenance for an ownership record minted by the CAS Harness audit flow. Recorded in the
# traceability envelope's ``source`` so a row can be traced to the subsystem that wrote it.
_DEFAULT_SOURCE = "cas_harness_audit"


def record_evidence_ownership(
    store: StateStore,
    *,
    tenant_id: str,
    account_id: str,
    trace_id: str,
    source: str = _DEFAULT_SOURCE,
) -> None:
    """Record that ``tenant_id`` (via ``account_id``) owns the evidence trace ``trace_id``.

    Writes a tenant-scoped :class:`LedgerRecord` under :data:`EVIDENCE_OWNERSHIP_KIND` keyed by
    ``trace_id``. The payload carries ``account_id`` and ``trace_id`` so the owning account is
    recoverable for audit; the row's tenant partition is what enforces isolation.

    Idempotent by construction. The ledger's create contract is ``put(expected_version=0)``; a row
    that already exists for ``(tenant_id, trace_id)`` would make that raise
    :class:`VersionConflict`. We therefore read first: if a row is already present for this tenant
    and trace, recording ownership again is a no-op (the fact is already true), so we return without
    re-writing and without raising. This makes "the audit ran twice / the hook fired twice" safe.

    Note the asymmetry that keeps this a SECURITY primitive, not a footgun: a pre-existing row is
    only found when it was written under THIS ``tenant_id`` (the store scopes the read by tenant).
    If some other tenant somehow held the same ``trace_id``, this tenant's ``get`` returns ``None``
    and we would attempt a create under this tenant -- which is correct: ownership is per-tenant, and
    one tenant's record never satisfies or overwrites another's.
    """
    existing = store.get(tenant_id, EVIDENCE_OWNERSHIP_KIND, trace_id)
    if existing is not None:
        # Already recorded for this tenant: idempotent no-op. Ownership is a fact, not a counter --
        # re-asserting it changes nothing, so we do not bump the version or rewrite the payload.
        return

    record = LedgerRecord.new(
        tenant_id=tenant_id,
        kind=EVIDENCE_OWNERSHIP_KIND,
        record_id=trace_id,
        payload={"account_id": account_id, "trace_id": trace_id},
        source=source,
        trace_id=trace_id,
    )
    try:
        store.put(record, expected_version=0)
    except VersionConflict:
        # A concurrent writer created the row between our get and our put. The post-condition we
        # care about -- "this tenant owns this trace" -- now holds either way, so the conflict is
        # benign: another caller won the race to assert the same fact. Swallow it (idempotent),
        # never surface it to a security-critical caller as a failure.
        return


def tenant_owns_trace(
    store: StateStore,
    *,
    tenant_id: str,
    trace_id: str,
) -> bool:
    """Return whether ``tenant_id`` owns the evidence trace ``trace_id``.

    The isolation check. Leans entirely on the store's mandatory tenant partitioning: ``get``
    returns the row only when it exists AND belongs to ``tenant_id``; a cross-tenant trace returns
    ``None`` (indistinguishable from absent, on purpose -- one tenant must not even learn another's
    trace exists). So ``True`` means "owned by this tenant," and ``False`` covers both "no such
    trace" and "exists, but owned by a different tenant" with the same answer.
    """
    return store.get(tenant_id, EVIDENCE_OWNERSHIP_KIND, trace_id) is not None


__all__ = [
    "EVIDENCE_OWNERSHIP_KIND",
    "record_evidence_ownership",
    "tenant_owns_trace",
]
