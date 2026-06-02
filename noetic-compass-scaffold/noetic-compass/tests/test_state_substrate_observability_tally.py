"""Tests for the bounded observability tally added to ``LedgerMirror``.

These lock the *new* operator-facing accounting on the strangler-fig seam without
disturbing the divergence-log behaviour the sacred suite
(``test_state_substrate_migration.py``) already pins. The tally is the cheap, O(1)
counterpart to the full divergence log -- the number an operator watches during the
Phase-2 zero-divergence window:

* ``reads_compared`` counts EVERY shadow-compare attempt, agreements included (the
  denominator a divergence count is meaningless without);
* ``divergences_found`` counts divergences from every source -- shadow-read mismatches
  AND ``mirror_put`` write failures -- consistent with the existing divergence log;
* ``last_divergence`` retains only a small detail (kind / record_id / reason / at) for
  the most recent divergence, never payloads, never a growing list;
* the counters only ever do work when ``shadow_compare`` / a divergence actually fires,
  so a mirror that is never called (and, in production, never installed) stays at zero --
  the dark-path invariant at the counter level.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_observability_tally.py -q
"""

from __future__ import annotations

from api.services.production.state_substrate import (
    InMemoryStateStore,
    LedgerMirror,
    StateStoreError,
)


class _BrokenStore:
    """Every operation raises -- to drive the ``mirror_put`` write-failure divergence path."""

    def get(self, *args, **kwargs):
        raise StateStoreError("backend down (get)")

    def put(self, *args, **kwargs):
        raise StateStoreError("backend down (put)")

    def list(self, *args, **kwargs):
        raise StateStoreError("backend down (list)")


def test_fresh_mirror_tally_is_all_zero_and_no_last_divergence():
    # A mirror nobody has called yet has done no work: the dark-path invariant at the
    # counter level (a never-called mirror -- and production installs none -- stays zero).
    mirror = LedgerMirror(InMemoryStateStore())
    assert mirror.tally() == {
        "reads_compared": 0,
        "divergences_found": 0,
        "last_divergence": None,
    }


def test_reads_compared_counts_every_compare_including_agreements():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")

    # Three clean compares (all agree): reads_compared climbs, divergences stay 0.
    for _ in range(3):
        assert mirror.shadow_compare("run", "run-1", {"status": "RUNNING"}) is None

    tally = mirror.tally()
    assert tally["reads_compared"] == 3
    assert tally["divergences_found"] == 0
    assert tally["last_divergence"] is None
    # The mirror_put above did NOT count as a compare.
    assert mirror.divergences == ()


def test_divergence_increments_count_and_records_last_detail():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")

    # One clean compare, then one mismatch (dict moved to DONE, ledger still RUNNING).
    assert mirror.shadow_compare("run", "run-1", {"status": "RUNNING"}) is None
    div = mirror.shadow_compare("run", "run-1", {"status": "DONE"})
    assert div is not None and div.reason == "payload_mismatch"

    tally = mirror.tally()
    assert tally["reads_compared"] == 2, "both compares counted"
    assert tally["divergences_found"] == 1
    last = tally["last_divergence"]
    assert last == {
        "kind": "run",
        "record_id": "run-1",
        "reason": "payload_mismatch",
        "at": div.at.isoformat(),
    }
    # last_divergence carries NO payload detail -- pointer, not snapshot.
    assert "detail" not in last and "payload" not in last


def test_last_divergence_tracks_the_most_recent_only():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)

    first = mirror.shadow_compare("run", "ghost-1", {"x": 1})  # missing_in_ledger
    second = mirror.shadow_compare("worker", "ghost-2", {"y": 2})  # missing_in_ledger
    assert first is not None and second is not None

    tally = mirror.tally()
    assert tally["divergences_found"] == 2
    # Only the most recent is retained as the detail.
    assert tally["last_divergence"]["record_id"] == "ghost-2"
    assert tally["last_divergence"]["kind"] == "worker"


def test_tally_counts_write_failures_from_mirror_put_too():
    # Divergences are not only shadow-read mismatches: a write that fails the backend is
    # also recorded. The tally must reflect every source, matching the divergence log.
    mirror = LedgerMirror(_BrokenStore())
    mirror.mirror_put("run", "run-1", {"x": 1}, source="svc")  # records write_failed

    tally = mirror.tally()
    # mirror_put is not a compare, so reads_compared stays 0 ...
    assert tally["reads_compared"] == 0
    # ... but the divergence was counted, consistent with the log.
    assert tally["divergences_found"] == 1
    assert tally["last_divergence"]["reason"] == "write_failed"
    assert len(mirror.divergences) == 1


def test_clear_divergences_resets_divergence_tally_but_not_the_odometer():
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.shadow_compare("run", "ghost", {"x": 1})  # 1 compare, 1 divergence
    assert mirror.tally()["divergences_found"] == 1

    mirror.clear_divergences()
    after = mirror.tally()
    # Divergence half is reset and consistent with the cleared log ...
    assert after["divergences_found"] == 0
    assert after["last_divergence"] is None
    assert mirror.divergences == ()
    # ... but reads_compared is cumulative throughput and is NOT reset by clearing.
    assert after["reads_compared"] == 1


def test_tally_count_matches_divergence_log_length():
    # Cross-check: the counter and the existing log can never silently disagree.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.shadow_compare("run", "g1", {"x": 1})
    mirror.shadow_compare("run", "g2", {"x": 1})
    mirror.shadow_compare("run", "g3", {"x": 1})

    assert mirror.tally()["divergences_found"] == len(mirror.divergences) == 3
