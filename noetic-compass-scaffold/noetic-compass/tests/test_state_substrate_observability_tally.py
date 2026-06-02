"""Tests for the bounded observability tally added to ``LedgerMirror``.

These lock the *new* operator-facing accounting on the strangler-fig seam without
disturbing the divergence-log behaviour the sacred suite
(``test_state_substrate_migration.py``) already pins. The tally is the cheap, O(1)
counterpart to the full divergence log -- the number an operator watches during the
Phase-2 zero-divergence window:

* ``reads_compared`` counts EVERY shadow-compare attempt, agreements included (the
  Phase-2 denominator a divergence count is meaningless without);
* ``reads_served`` counts EVERY authoritative read the ledger serves under read-authority
  (``read_payload`` / ``read_all_payloads``), one tick per read operation -- the Phase-3
  denominator that climbs once ``reads_compared`` freezes at the read-authority flip;
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
        "reads_served": 0,
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


# --------------------------------------------------------------------------
# reads_served -- the Phase-3 (read-authority) odometer
# --------------------------------------------------------------------------
#
# reads_compared answers "how many shadow-compares ran" while the dicts are authoritative.
# It necessarily FREEZES the moment read-authority flips, because the live read sites stop
# shadow-comparing and start serving from the ledger (read_payload / read_all_payloads).
# reads_served is that phase's denominator: the number an operator watches to confirm the
# ledger is actively serving reads, paired with divergences_found == 0. Without it, the
# status surface would look dead exactly when the ledger took over.


def test_reads_served_counts_authoritative_reads_separately_from_shadow_compares():
    # The two odometers track different read paths and never cross-contaminate: a
    # shadow-compare bumps reads_compared only; an authoritative read bumps reads_served only.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")

    mirror.shadow_compare("run", "run-1", {"status": "RUNNING"})
    assert mirror.tally()["reads_compared"] == 1
    assert mirror.tally()["reads_served"] == 0

    assert mirror.read_payload("run", "run-1") == {"status": "RUNNING"}
    tally = mirror.tally()
    assert tally["reads_served"] == 1
    assert tally["reads_compared"] == 1, "authoritative read must not touch the shadow odometer"


def test_reads_served_stays_zero_through_pure_shadow_traffic():
    # Phase-2 posture: only shadow-compares run. reads_served must stay flat at 0 so an
    # operator reading it knows the ledger is NOT yet serving any authoritative read.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"x": 1}, source="svc")
    for _ in range(5):
        mirror.shadow_compare("run", "run-1", {"x": 1})
    tally = mirror.tally()
    assert tally["reads_compared"] == 5
    assert tally["reads_served"] == 0


def test_reads_served_counts_one_per_list_read_not_per_row():
    # read_all_payloads is ONE authoritative read operation however many rows it returns;
    # the operator watch needs a climbing denominator, not a per-row tally.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"x": 1}, source="svc")
    mirror.mirror_put("run", "run-2", {"x": 2}, source="svc")
    mirror.mirror_put("run", "run-3", {"x": 3}, source="svc")

    payloads = mirror.read_all_payloads("run")
    assert len(payloads) == 3
    assert mirror.tally()["reads_served"] == 1, "one read operation, not three rows"


def test_reads_served_counts_an_authoritative_miss():
    # A read that finds no record is still a serve: the ledger authoritatively answered
    # "no such record" (mirrors how shadow_compare counts its missing-record attempt).
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    assert mirror.read_payload("run", "absent") is None
    assert mirror.tally()["reads_served"] == 1


def test_reads_served_does_not_count_a_failed_authoritative_read():
    # An authoritative read is fail-loud: StateStoreError propagates (the request fails)
    # and must NOT tick reads_served -- a read the ledger could not answer is not a serve.
    mirror = LedgerMirror(_BrokenStore())
    raised = False
    try:
        mirror.read_payload("run", "run-1")
    except StateStoreError:
        raised = True
    assert raised, "read_payload must propagate StateStoreError (fail-loud), not swallow it"
    assert mirror.tally()["reads_served"] == 0


def test_reads_served_is_cumulative_throughput_not_reset_by_clear():
    # Like reads_compared, reads_served is cumulative throughput, not a divergence detail.
    # Clearing divergences must leave it untouched.
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    mirror.mirror_put("run", "run-1", {"x": 1}, source="svc")
    mirror.read_payload("run", "run-1")
    mirror.read_all_payloads("run")
    assert mirror.tally()["reads_served"] == 2

    mirror.clear_divergences()
    assert mirror.tally()["reads_served"] == 2, "clear_divergences must not reset the read odometer"
