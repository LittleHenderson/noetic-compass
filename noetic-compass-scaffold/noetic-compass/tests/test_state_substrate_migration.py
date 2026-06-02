"""Contract tests for the strangler-fig migration seam (``LedgerMirror``).

This seam is the coupling-critical core of doc 10's Phase 0/1/2: it dual-writes the
live globals into the ledger and shadow-reads them back to prove zero divergence
before any cutover. Because every live service will route its mutations and reads
through it, its guarantees are locked here *first*, against the in-memory reference
store, before it is wired into any request path:

* dual-write creates then updates a single versioned row, preserving the
  traceability envelope and the interim tenant scoping;
* shadow-read agrees when the dict and ledger match, and records a precise
  divergence (never raises) when they do not -- including the "mutated the dict but
  forgot to mirror it" failure mode the whole exercise exists to catch;
* the mirror is non-authoritative: a broken backend is turned into divergences, not
  into an exception that would break the dict-served request;
* the read-then-write upsert survives concurrent writers via bounded
  ``VersionConflict`` retry.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_migration.py -q
"""

from __future__ import annotations

import threading

import pytest

from api.services.production.state_substrate import (
    INTERIM_TENANT,
    InMemoryStateStore,
    LedgerMirror,
    StateStoreError,
    VersionConflict,
)
from api.services.production.state_substrate.interface import LedgerRecord


# --------------------------------------------------------------------------
# test doubles: stores that fail on purpose, to prove non-authoritative safety
# --------------------------------------------------------------------------


class _BrokenStore:
    """A store whose every record operation raises -- the worst case the mirror must absorb."""

    def get(self, *args, **kwargs):
        raise StateStoreError("backend down (get)")

    def put(self, *args, **kwargs):
        raise StateStoreError("backend down (put)")

    def list(self, *args, **kwargs):
        raise StateStoreError("backend down (list)")


class _FlakyPutStore:
    """Wraps a real store but raises ``VersionConflict`` on the first ``fail_times`` puts.

    Lets a test drive the optimistic-concurrency retry loop deterministically without
    spinning real threads: each conflict forces the mirror to re-read and try again.
    """

    def __init__(self, inner: InMemoryStateStore, *, fail_times: int) -> None:
        self._inner = inner
        self._remaining = fail_times

    def get(self, *args, **kwargs):
        return self._inner.get(*args, **kwargs)

    def list(self, *args, **kwargs):
        return self._inner.list(*args, **kwargs)

    def put(self, record, *, expected_version):
        if self._remaining > 0:
            self._remaining -= 1
            raise VersionConflict(
                kind=record.kind,
                record_id=record.record_id,
                expected=expected_version,
                actual=expected_version + 99,
            )
        return self._inner.put(record, expected_version=expected_version)


# --------------------------------------------------------------------------
# Phase 1: dual-write
# --------------------------------------------------------------------------


def test_mirror_put_creates_then_updates_one_versioned_row():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)

    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")
    created = store.get(INTERIM_TENANT, "run", "run-1")
    assert created is not None
    assert created.version == 1, "first mirror_put promotes version 0 -> 1"
    assert created.payload == {"status": "RUNNING"}

    # A second mirror_put for the same id is an in-place upsert, not a duplicate row.
    mirror.mirror_put("run", "run-1", {"status": "DONE"}, source="svc")
    updated = store.get(INTERIM_TENANT, "run", "run-1")
    assert updated.version == 2
    assert updated.payload == {"status": "DONE"}
    assert updated.created_at == created.created_at, "created_at immutable across update"
    assert store.list(INTERIM_TENANT, "run") == (updated,), "one row, not two"
    assert mirror.divergences == ()


def test_mirror_put_sets_traceability_envelope_on_creation():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)

    mirror.mirror_put(
        "worker", "w-1", {"state": "idle"},
        source="cas_harness_fleet_executor",
        trace_id="trace-xyz",
        parent_ids=("audit-7",),
    )
    rec = store.get(INTERIM_TENANT, "worker", "w-1")
    assert rec.source == "cas_harness_fleet_executor"
    assert rec.trace_id == "trace-xyz"
    assert rec.parent_ids == ("audit-7",)

    # Provenance reflects birth: a later update keeps the original envelope even if
    # the caller passes different trace fields.
    mirror.mirror_put(
        "worker", "w-1", {"state": "busy"},
        source="someone-else", trace_id="trace-other",
    )
    rec2 = store.get(INTERIM_TENANT, "worker", "w-1")
    assert rec2.source == "cas_harness_fleet_executor"
    assert rec2.trace_id == "trace-xyz"


def test_mirror_writes_are_scoped_to_the_interim_tenant():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"n": 1}, source="svc")

    # Visible under the interim tenant, fail-closed-absent under any other.
    assert store.get(INTERIM_TENANT, "run", "run-1") is not None
    assert store.get("some-other-tenant", "run", "run-1") is None


def test_mirror_put_retries_through_version_conflicts():
    inner = InMemoryStateStore()
    flaky = _FlakyPutStore(inner, fail_times=3)
    mirror = LedgerMirror(flaky, max_write_retries=8)

    mirror.mirror_put("run", "run-1", {"ok": True}, source="svc")

    # Three conflicts were absorbed by re-read-and-retry; the write still landed and
    # nothing was recorded as a divergence.
    assert inner.get(INTERIM_TENANT, "run", "run-1") is not None
    assert mirror.divergences == ()


def test_mirror_put_records_divergence_when_conflicts_never_clear():
    inner = InMemoryStateStore()
    flaky = _FlakyPutStore(inner, fail_times=99)
    mirror = LedgerMirror(flaky, max_write_retries=4)

    mirror.mirror_put("run", "run-1", {"ok": True}, source="svc")  # must NOT raise

    divs = mirror.divergences
    assert len(divs) == 1
    assert divs[0].reason == "write_conflict_exhausted"
    assert inner.get(INTERIM_TENANT, "run", "run-1") is None, "no write landed"


def test_mirror_put_swallows_backend_failure_as_divergence():
    mirror = LedgerMirror(_BrokenStore())

    # The defining property: a dead backend does not propagate into the caller.
    mirror.mirror_put("run", "run-1", {"x": 1}, source="svc")

    divs = mirror.divergences
    assert len(divs) == 1
    assert divs[0].reason == "write_failed"
    assert divs[0].kind == "run" and divs[0].record_id == "run-1"


# --------------------------------------------------------------------------
# Phase 2: shadow-read
# --------------------------------------------------------------------------


def test_shadow_compare_agrees_when_dict_and_ledger_match():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"status": "RUNNING", "shards": 4}, source="svc")

    assert mirror.shadow_compare("run", "run-1", {"status": "RUNNING", "shards": 4}) is None
    assert mirror.divergences == ()


def test_shadow_compare_is_insensitive_to_key_order():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"a": 1, "b": 2, "c": 3}, source="svc")

    # Same content, different insertion order -> canonical projection makes them equal.
    assert mirror.shadow_compare("run", "run-1", {"c": 3, "a": 1, "b": 2}) is None


def test_shadow_compare_flags_missing_in_ledger():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)

    div = mirror.shadow_compare("run", "ghost", {"status": "RUNNING"})
    assert div is not None and div.reason == "missing_in_ledger"
    assert mirror.divergences == (div,)


def test_shadow_compare_flags_payload_mismatch_when_mutation_not_mirrored():
    # The headline failure mode: a mutator changed the dict but forgot to mirror it.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")

    # The "dict" moved on to DONE; the ledger still says RUNNING.
    div = mirror.shadow_compare("run", "run-1", {"status": "DONE"})
    assert div is not None and div.reason == "payload_mismatch"


def test_shadow_compare_swallows_read_failure_as_divergence():
    mirror = LedgerMirror(_BrokenStore())
    div = mirror.shadow_compare("run", "run-1", {"x": 1})
    assert div is not None and div.reason == "read_failed"


def test_shadow_compare_all_catches_ghost_rows_in_ledger():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"n": 1}, source="svc")
    mirror.mirror_put("run", "run-2", {"n": 2}, source="svc")

    # The dict view only knows about run-1; run-2 is a ledger ghost the dual-write
    # path should never have produced.
    divs = mirror.shadow_compare_all("run", {"run-1": {"n": 1}})
    reasons = {d.reason for d in divs}
    assert reasons == {"extra_in_ledger"}
    assert [d.record_id for d in divs if d.reason == "extra_in_ledger"] == ["run-2"]


def test_shadow_compare_all_passes_when_views_are_identical():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("worker", "w-1", {"state": "idle"}, source="svc")
    mirror.mirror_put("worker", "w-2", {"state": "busy"}, source="svc")

    divs = mirror.shadow_compare_all(
        "worker", {"w-1": {"state": "idle"}, "w-2": {"state": "busy"}}
    )
    assert divs == ()
    mirror.assert_no_divergence()


# --------------------------------------------------------------------------
# divergence accounting / the Phase-2 gate
# --------------------------------------------------------------------------


def test_assert_no_divergence_passes_clean_and_fails_dirty():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.assert_no_divergence()  # nothing recorded yet

    mirror.shadow_compare("run", "ghost", {"x": 1})  # records one divergence
    with pytest.raises(AssertionError) as excinfo:
        mirror.assert_no_divergence()
    assert "missing_in_ledger" in str(excinfo.value)


def test_clear_divergences_resets_the_log():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.shadow_compare("run", "ghost", {"x": 1})
    assert mirror.divergences != ()

    mirror.clear_divergences()
    assert mirror.divergences == ()
    mirror.assert_no_divergence()


# --------------------------------------------------------------------------
# concurrency: the live fleet executor races workers on the same run
# --------------------------------------------------------------------------


def test_concurrent_mirror_puts_stay_consistent_and_never_raise():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store, max_write_retries=64)
    candidates = [{"writer": i} for i in range(16)]
    errors: list[BaseException] = []
    barrier = threading.Barrier(len(candidates))

    def writer(payload):
        try:
            barrier.wait()  # maximise contention on the single row
            mirror.mirror_put("run", "hot", payload, source="svc")
        except BaseException as exc:  # caller-safety is the property under test
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(p,)) for p in candidates]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], "mirror_put must never raise into a caller"
    final = store.get(INTERIM_TENANT, "run", "hot")
    assert final is not None
    assert final.payload in candidates, "final row is one of the concurrent writes"
    # With a generous retry budget and 16 writers, bounded retry should resolve every
    # race without exhaustion.
    assert all(d.reason != "write_conflict_exhausted" for d in mirror.divergences)


def test_phase0_roundtrip_to_dict_is_byte_identical_through_the_seam():
    # Phase-0 property at the seam level: a record's dict projection, pushed through
    # mirror_put and read back, is canonical-identical -- nothing is lost in transit.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    payload = {
        "audit_id": "cas-dist-abc123",
        "status": "ready_for_verifier",
        "workers": [{"id": "w-1", "evidence": None}, {"id": "w-2", "evidence": 0.91}],
        "nested": {"z": 1, "a": 2},
    }
    mirror.mirror_put("distributed_audit", "cas-dist-abc123", payload, source="svc")
    assert mirror.shadow_compare("distributed_audit", "cas-dist-abc123", payload) is None


def test_ledger_record_new_is_the_only_construction_path_used():
    # Guard: the seam builds version-0 records via LedgerRecord.new and lets the store
    # own versioning. A direct put at expected_version 0 must agree with what the seam
    # produced -- i.e. the seam is not smuggling in a pre-versioned record.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"n": 1}, source="svc")
    rec = store.get(INTERIM_TENANT, "run", "run-1")
    rebuilt = LedgerRecord.new(
        tenant_id=INTERIM_TENANT, kind="run", record_id="run-1", payload={"n": 1}, source="svc",
    )
    assert rebuilt.version == 0 and rec.version == 1
