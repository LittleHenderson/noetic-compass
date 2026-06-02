"""The strangler-fig seam: dual-write the live globals into the ledger, *darkly*.

The live CAS Harness keeps its run/worker/audit/fragment state in process-global
dicts (``_DISTRIBUTED_AUDITS``, ``_WORKERS``, ``_FLEET_RUNS``, ``_FRAGMENT_REFS``).
Those dicts are still authoritative and still serve every request. This module is
the mechanism that lets the durable ``StateStore`` ledger run *alongside* them --
written to on every mutation, read back and compared on every read -- without the
ledger ever deciding anything. That is the whole strangler-fig discipline from
``docs/working/production_readiness/10_state_substrate_migration.md``:

* **Phase 1 (dual-write).** Every place the live code mutates a dict, it also calls
  :meth:`LedgerMirror.mirror_put`. Reads still come from the dict. The ledger is a
  shadow copy nobody trusts yet.
* **Phase 2 (shadow-read).** Every place the live code reads a dict, it also calls
  :meth:`LedgerMirror.shadow_compare` and records any disagreement. The proof
  obligation for cutover is **zero divergence** across the real test suites
  (:meth:`assert_no_divergence`).
* **Phase 3 (cutover).** Once the ledger provably mirrors the dicts (Phase 2) and the
  dicts are survivable (rehydrate-on-startup), read-authority moves onto the ledger:
  :meth:`enable_ledger_reads` flips the :meth:`read_from_ledger` switch and the live
  ``get_*`` / ``list_*`` reconstruct records from the store via :meth:`read_payload` /
  :meth:`read_all_payloads` instead of the dicts. The switch is **dark by default**
  (production installs no mirror, so it can never engage), **reversible**
  (:meth:`disable_ledger_reads`; the dual-write keeps the dicts current for instant
  rollback), and **fail-closed** (no mirror, no ledger reads). This module is the
  mechanism; *enabling* it in a durable deployment -- and Phase 4, deleting the dicts --
  remain separate gated steps, and multi-host durability is still workstream 11.

Why "non-authoritative" is load-bearing, not a hedge
----------------------------------------------------
A shadow that can break the thing it shadows is worse than no shadow. So
:meth:`mirror_put` never lets a ledger failure escape into the request path: a
``StateStoreError`` from the backend is swallowed and *recorded as a divergence*,
because a record we failed to mirror is exactly a place the ledger and the dict
disagree -- and surfacing that disagreement is the point. The dict-served response
is unaffected either way. (Programming errors -- a non-serialisable payload, a bug
in this seam -- are deliberately *not* swallowed: during Phases 1-2 the mirror runs
against :class:`InMemoryStateStore` in tests, where a raised bug should fail loudly
and get fixed, and in production the mirror is simply not installed.)

What divergence actually catches
--------------------------------
Two real failure modes, both of which must be zero before cutover is honest:

1. **A mutator that changed the dict but forgot to mirror it.** The ledger row goes
   stale; the next :meth:`shadow_compare` at a read site flags ``payload_mismatch``
   (or ``missing_in_ledger`` if the record was never mirrored at all).
2. **A round-trip that silently loses a field.** Comparison is done on a canonical
   JSON projection of both payloads, so a field that does not survive serialisation
   shows up as a mismatch rather than passing unnoticed.

The interim single tenant
--------------------------
There is no honest per-customer ``tenant_id`` in the system today: the JWT carries
only ``sub`` + ``api_key`` and mints no tenant claim. So every mirrored record is
written under one literal tenant, :data:`INTERIM_TENANT`. This is a **seam, not a
boundary**: it is exactly as tenant-blind as the global dicts it shadows -- no more
honest, no less. Workstream 06 (tenant isolation) turns that literal into a real
claim with a one-line edit, at which point the ledger's mandatory tenant scoping
starts doing real work. Until then, do not read ``tenant_id="default"`` as a
multi-tenant guarantee; it is a placeholder with a known upgrade path.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional

from .interface import (
    Kind,
    LedgerRecord,
    RecordId,
    StateStore,
    StateStoreError,
    TenantId,
    Version,
    VersionConflict,
    utc_now,
)

# The single tenant every mirrored record is written under during Phases 0-2.
# See the module docstring: a seam, not a multi-tenant boundary.
INTERIM_TENANT: TenantId = "default"


def _canonical(payload: Mapping[str, object]) -> str:
    """Project a payload to a backend-agnostic canonical string for comparison.

    Both the dict's payload and the ledger's stored payload go through *this exact
    function* before they are compared, which is what makes :meth:`shadow_compare`
    independent of how a given backend stores the bytes:

    * ``sort_keys=True`` makes key order irrelevant (a dict and a JSON-reparsed dict
      must compare equal even though their iteration order may differ).
    * ``default=str`` gives any non-JSON-native value (a stray ``datetime``, say) a
      deterministic textual form. Because it is applied symmetrically to both sides,
      it can never manufacture a *false* match or a *false* mismatch -- a field that
      is genuinely equal stays equal, a field that genuinely differs still differs.
    """

    return json.dumps(payload, sort_keys=True, default=str)


@dataclass(frozen=True, slots=True)
class Divergence:
    """One recorded disagreement between a live dict and the shadow ledger.

    A divergence is never raised in the request path -- it is *appended* to the
    mirror's log so the Phase-2 gate (:meth:`LedgerMirror.assert_no_divergence`) can
    fail the build if the two views of the world ever drift apart. ``reason`` is a
    short stable tag (see the call sites) and ``detail`` is human-readable context.
    """

    kind: Kind
    record_id: RecordId
    reason: str
    detail: str = ""
    at: datetime = field(default_factory=utc_now)

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        suffix = f" -- {self.detail}" if self.detail else ""
        return f"[{self.reason}] {self.kind}/{self.record_id}{suffix}"


class LedgerMirror:
    """Non-authoritative dual-write / shadow-read bridge from the live dicts to a ``StateStore``.

    Construct one per live service (or one shared instance) around any ``StateStore``
    -- :class:`InMemoryStateStore` during Phases 0-2, a durable backend at cutover.
    The mirror holds no state of its own beyond a divergence log; the ledger is the
    store passed in.

    Thread-safety: the divergence log is guarded by a lock, and the dual-write upsert
    relies on the store's own optimistic concurrency (``expected_version``) plus a
    bounded retry, so concurrent callers cannot corrupt the shadow copy. The live
    fleet executor races multiple workers on the same run, so this is not optional.
    """

    def __init__(self, store: StateStore, *, max_write_retries: int = 8) -> None:
        self._store = store
        self._max_retries = max_write_retries
        self._divergences: list[Divergence] = []
        self._lock = threading.Lock()
        # Phase 3 read-authority switch. Dark by default: while False, the live
        # services serve every read from their dicts and merely *shadow-compare*
        # the ledger (Phase 2). Flipping it to True makes the ledger the read
        # authority -- see enable_ledger_reads / read_payload below. It is a plain
        # bool, not a lock-guarded one, because it is flipped once at cutover (or
        # in a test), never raced per-request.
        self._read_from_ledger = False

    # --- Phase 1: dual-write ------------------------------------------------

    def mirror_put(
        self,
        kind: Kind,
        record_id: RecordId,
        payload: Mapping[str, object],
        *,
        source: str,
        trace_id: Optional[str] = None,
        parent_ids: tuple[RecordId, ...] = (),
    ) -> None:
        """Upsert ``payload`` into the shadow ledger; never raise into the caller.

        Read-then-write upsert against the store's optimistic concurrency: read the
        current version, write at that version, and retry on :class:`VersionConflict`
        (another thread updated the row between our read and write -- the honest
        response is re-read-and-retry, not blind clobber). A ``StateStoreError`` that
        survives the retries, or any other backend failure, is recorded as a
        divergence and swallowed: the live dict already served the request, and a
        ledger we could not write to is precisely a divergence we want on the books.

        The traceability envelope (``source`` / ``trace_id`` / ``parent_ids``) is set
        when the record is first created (version 0 -> 1) and preserved across later
        updates -- provenance reflects where a record was born, so creation sites must
        be mirrored too, not only mutation sites.
        """

        for _ in range(self._max_retries):
            try:
                existing = self._store.get(INTERIM_TENANT, kind, record_id)
                if existing is None:
                    record = LedgerRecord.new(
                        tenant_id=INTERIM_TENANT,
                        kind=kind,
                        record_id=record_id,
                        payload=payload,
                        parent_ids=parent_ids,
                        source=source,
                        trace_id=trace_id,
                    )
                    self._store.put(record, expected_version=0)
                else:
                    self._store.put(
                        existing.with_payload(payload),
                        expected_version=existing.version,
                    )
                return
            except VersionConflict:
                # Lost the race; re-read and retry against the new version.
                continue
            except StateStoreError as exc:
                self._record(kind, record_id, "write_failed", repr(exc))
                return
        # Retries exhausted: persistent contention we could not win. Honest to log it
        # rather than loop forever or pretend the write landed.
        self._record(
            kind, record_id, "write_conflict_exhausted",
            f"gave up after {self._max_retries} attempts",
        )

    # --- Phase 2: shadow-read ----------------------------------------------

    def shadow_compare(
        self,
        kind: Kind,
        record_id: RecordId,
        dict_payload: Mapping[str, object],
    ) -> Optional[Divergence]:
        """Compare the live dict's payload against the ledger's; record any mismatch.

        Returns the :class:`Divergence` it recorded, or ``None`` when the ledger
        agrees. Three ways to disagree: the ledger read fails (``read_failed``), the
        ledger has no such record though the dict does (``missing_in_ledger``), or the
        canonical payloads differ (``payload_mismatch``). Like :meth:`mirror_put`, a
        backend read failure is turned into a divergence rather than raised, so a
        shadow read can never break the request that triggered it.
        """

        try:
            existing = self._store.get(INTERIM_TENANT, kind, record_id)
        except StateStoreError as exc:
            return self._record(kind, record_id, "read_failed", repr(exc))
        if existing is None:
            return self._record(
                kind, record_id, "missing_in_ledger",
                "dict holds this record; ledger has none",
            )
        want = _canonical(dict_payload)
        got = _canonical(existing.payload)
        if want != got:
            return self._record(
                kind, record_id, "payload_mismatch",
                f"dict={want} ledger={got}",
            )
        return None

    def shadow_compare_all(
        self,
        kind: Kind,
        dict_payloads: Mapping[RecordId, Mapping[str, object]],
    ) -> tuple[Divergence, ...]:
        """Compare the *entire* dict view of a ``kind`` against the ledger's view.

        Stronger than per-record :meth:`shadow_compare`: it also catches records the
        ledger has but the dict does not (``extra_in_ledger``) -- a ghost the dual-write
        path should never produce. This is the list-level Phase-2 gate: prove the
        ledger's set of rows for a kind is *exactly* the dict's set, payloads included.
        """

        found: list[Divergence] = []
        for record_id, payload in dict_payloads.items():
            div = self.shadow_compare(kind, record_id, payload)
            if div is not None:
                found.append(div)
        try:
            ledger_ids = {rec.record_id for rec in self._store.list(INTERIM_TENANT, kind)}
        except StateStoreError as exc:
            found.append(self._record(kind, "*", "list_failed", repr(exc)))
            return tuple(found)
        for ghost_id in ledger_ids - set(dict_payloads):
            found.append(
                self._record(
                    kind, ghost_id, "extra_in_ledger",
                    "ledger holds this record; dict has none",
                )
            )
        return tuple(found)

    # --- Phase 3: read-authority cutover -----------------------------------

    @property
    def read_from_ledger(self) -> bool:
        """Whether the ledger is the read authority (Phase 3) or just a shadow (Phase 2).

        The live read sites gate on this: ``_STATE_MIRROR is not None and
        _STATE_MIRROR.read_from_ledger``. Because a service with no mirror installed
        can never satisfy the first half, production -- which installs no mirror -- is
        *structurally* pinned to dict-authority. You cannot read from a ledger that is
        not there; the cutover is impossible to enable by accident.
        """

        return self._read_from_ledger

    def enable_ledger_reads(self) -> None:
        """Make the ledger the read authority. The deliberate Phase-3 flip.

        Precondition the caller owns: the ledger must already mirror the dicts (Phase 2
        proved zero divergence) and must be durable enough to *be* the truth. This
        method does not re-check that -- it is the lever, not the gate. After this, the
        live ``get_*`` / ``list_*`` reconstruct records from this store instead of the
        dicts. Reversible: :meth:`disable_ledger_reads` returns to dict-authority, and
        the dual-write keeps the dicts current the whole time so rollback is instant.
        """

        self._read_from_ledger = True

    def disable_ledger_reads(self) -> None:
        """Return read-authority to the dicts. The Phase-3 rollback lever."""

        self._read_from_ledger = False

    def read_payload(self, kind: Kind, record_id: RecordId) -> Optional[Mapping[str, object]]:
        """Authoritative single read: the ledger's stored payload for one record, or ``None``.

        This is the read counterpart of :meth:`mirror_put`, and it is deliberately the
        *opposite* of :meth:`shadow_compare` about failure. A shadow read swallows a
        ``StateStoreError`` (the dict already answered; the failure is only a divergence
        to log). An authoritative read **must not** hide a backend failure: when the
        ledger *is* the truth, a read that cannot reach it has to fail the request, not
        fabricate an answer. So ``StateStoreError`` propagates here by design.
        """

        record = self._store.get(INTERIM_TENANT, kind, record_id)
        return None if record is None else record.payload

    def read_all_payloads(self, kind: Kind) -> dict[RecordId, Mapping[str, object]]:
        """Authoritative list read: every stored payload of a ``kind``, keyed by record id.

        Backs the live ``list_*`` calls under read-authority. Like :meth:`read_payload`,
        a backend failure propagates rather than being swallowed.
        """

        return {rec.record_id: rec.payload for rec in self._store.list(INTERIM_TENANT, kind)}

    # --- divergence accounting ---------------------------------------------

    @property
    def divergences(self) -> tuple[Divergence, ...]:
        """Every divergence recorded so far, in detection order (snapshot copy)."""

        with self._lock:
            return tuple(self._divergences)

    def assert_no_divergence(self) -> None:
        """The Phase-2 cutover gate: raise if the ledger ever disagreed with a dict.

        A clean pass across the live service's real test suite is the evidence that
        the shadow ledger faithfully mirrors the authoritative dicts -- the
        precondition for making the ledger authoritative in Phase 3.
        """

        divs = self.divergences
        if divs:
            body = "\n".join(f"  - {d}" for d in divs)
            raise AssertionError(
                f"ledger mirror recorded {len(divs)} divergence(s):\n{body}"
            )

    def clear_divergences(self) -> None:
        """Forget recorded divergences (e.g. between phases of a multi-stage test)."""

        with self._lock:
            self._divergences.clear()

    # --- internals ----------------------------------------------------------

    def _record(self, kind: Kind, record_id: RecordId, reason: str, detail: str = "") -> Divergence:
        divergence = Divergence(kind=kind, record_id=record_id, reason=reason, detail=detail)
        with self._lock:
            self._divergences.append(divergence)
        return divergence
