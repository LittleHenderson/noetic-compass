"""Concurrency stress tests for the in-memory reference ``StateStore``.

Where ``test_state_substrate_memory.py`` proves the reference backend satisfies
the single-threaded behavioural contract, this file proves it holds the
substrate's *safety invariants under genuinely concurrent access*: no lost
updates under optimistic-concurrency contention, exactly-one lease holder with
clean handoff, and tenant isolation while many threads write at once.

The work is intentionally backend-agnostic. ``run_state_store_stress`` takes a
store *factory* (the same shape ``run_state_store_contract`` uses), so the SAME
function will later be pointed at ``SqliteStateStore`` (durable, single-host) and
any future Postgres/Redis backend with no edits -- store-agnostic by design.

These tests assert correctness invariants only, never timings, so they are
deterministic and non-flaky regardless of how the OS schedules the threads. They
do NOT (and cannot) test crash/kill-mid-write durability on the in-memory store --
that is a durable-backend property, surfaced as an explicit out-of-scope hook in
``stress.assert_crash_durability``.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_stress.py -q
"""

from __future__ import annotations

import pytest

from api.services.production.state_substrate import InMemoryStateStore
from api.services.production.state_substrate.stress import (
    assert_crash_durability,
    run_state_store_stress,
)


def test_inmemory_survives_concurrency_stress():
    # Headline assertion: under 8 threads x 50 iterations of contended reads,
    # version-checked writes, racing lease acquisitions, and cross-tenant writes,
    # every substrate safety invariant holds. A returned-clean call means no lost
    # update, no double lease holder, and no tenant leak was observed.
    #
    # NOTE: the SAME run_state_store_stress(...) call will later be handed a
    # SqliteStateStore factory (durable, single-host) -- the harness is
    # store-agnostic, exactly like run_state_store_contract.
    run_state_store_stress(InMemoryStateStore, threads=8, iterations=50)


def test_inmemory_survives_high_contention_stress():
    # Crank the contention up: more threads than typical core counts and more
    # iterations, to widen the interleaving window for a real race. Still well
    # under a second of wall-clock (the per-op work is dict-sized). If optimistic
    # concurrency or lease exclusion were subtly wrong, higher contention is where
    # it surfaces.
    run_state_store_stress(InMemoryStateStore, threads=16, iterations=100)


def test_lease_mutual_exclusion_isolated():
    # A focused, lower-iteration run kept as a named regression anchor for the
    # lease single-holder invariant specifically. run_state_store_stress asserts
    # the mutual-exclusion + clean-handoff invariants internally (barrier-raced
    # acquisitions + an independent critical-section witness asserting inside==1);
    # isolating it here makes a lease-exclusion regression easy to pinpoint.
    run_state_store_stress(InMemoryStateStore, threads=8, iterations=25)


def test_single_thread_is_rejected_as_non_stress():
    # The harness refuses a degenerate 1-thread "stress" run: a single thread
    # proves nothing about concurrency, so asking for it is a usage error, not a
    # pass.
    with pytest.raises(AssertionError):
        run_state_store_stress(InMemoryStateStore, threads=1, iterations=10)


def test_crash_durability_is_out_of_scope_for_inmemory():
    # Honesty boundary, asserted rather than narrated: the in-memory store has no
    # persisted state to survive a crash, so the crash-durability hook must refuse
    # to run here (NotImplementedError) instead of fabricating a pass. The durable
    # backends (SQLite reopen test) own the real durability proof. A stub is a stub.
    with pytest.raises(NotImplementedError):
        assert_crash_durability(InMemoryStateStore)
