"""Store-agnostic CONCURRENCY stress harness for :class:`StateStore`.

Where ``conformance.py`` proves a backend agrees with the reference *behaviour*
one call at a time, this module proves the substrate's **safety invariants hold
under genuinely concurrent access**: many threads hammering one store at once.
Like the conformance suite it is parametrised by a factory
(``Callable[[], StateStore]``) and raises ``AssertionError`` on the first violated
invariant, so the *same* ``run_state_store_stress`` runs against any backend --
the in-memory reference store now; ``SqliteStateStore`` / Postgres later -- with
no edits.

What this harness asserts (concurrency-safety, not durability):

* **No lost updates under version contention.** Threads read-modify-write a shared
  counter using optimistic concurrency. Because a read and the following ``put``
  are two *separate* Protocol calls, they are NOT atomic together even on a store
  whose every single call is atomic -- so racing writers collide and the store
  must reject the stale one with ``VersionConflict``. The harness counts only the
  ``put`` calls that actually committed and asserts the final counter equals that
  count exactly: nothing was silently clobbered, nothing double-counted.
* **Exactly one lease holder.** Threads race -- released together by a
  ``threading.Barrier`` so the contention is real, not staggered -- to acquire the
  same ``(tenant, resource)`` lease. The harness asserts that at no instant do two
  threads sit inside the lease's critical section, across many rounds.
* **Clean lease handoff.** Over repeated acquire -> work -> release rounds, every
  round has exactly one winner and the resource is always re-acquirable; it never
  ends up wedged (held by nobody yet un-leasable) or double-held.
* **Tenant isolation under concurrency.** Threads writing the same ``record_id``
  under different tenants never observe each other's payloads.

Honest scope boundary -- what this harness does **not** and **cannot** test:

* **Crash / kill-mid-write durability is OUT OF SCOPE here.** Surviving a process
  kill between the in-memory mutation and a durable flush is a property only a
  *durable* backend can demonstrate, and only by being killed and reopened against
  real storage. An in-memory store has nothing to survive to -- so this harness
  does not fake it. The hook is named (``assert_crash_durability``) and left as an
  explicit ``NotImplementedError`` for the durable backends (SQLite reopen test,
  etc.); calling it on the in-memory store is a category error, and it says so
  rather than pretending. Declared vs verified is sacred; a stub is a stub.

The invariants asserted here are *correctness* invariants, never timing ones: the
harness deliberately makes no assertion about how fast anything runs or how many
conflicts occur, only that the surviving state is consistent. That keeps it
deterministic and non-flaky regardless of how the OS scheduler interleaves the
threads.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

from .interface import (
    Kind,
    LeaseHeld,
    LedgerRecord,
    StateStore,
    TenantId,
    VersionConflict,
)

# A factory that yields a fresh store. Same shape conformance.py uses, so a
# backend already wired for the contract suite needs no extra plumbing here.
StoreFactory = Callable[[], StateStore]


@dataclass
class _AtomicCounter:
    """A trivially-correct thread-safe counter.

    Used as the harness's OWN source of truth for "how many puts actually
    committed" -- deliberately independent of the store under test, so the
    no-lost-updates assertion compares the store's final state against a count the
    store had no hand in producing.
    """

    _value: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def increment(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


def run_state_store_stress(
    make_store: StoreFactory,
    *,
    threads: int = 8,
    iterations: int = 50,
) -> None:
    """Hammer ONE store (built from ``make_store``) from ``threads`` workers.

    Constructs a single store, runs every concurrency invariant against it, and
    returns cleanly iff every invariant held. Raises ``AssertionError`` -- naming
    the violated invariant and the expected-vs-actual values -- on the first
    failure. Mirrors ``run_state_store_contract``'s factory-in / assert-out shape
    so the two suites are interchangeable at the call site.

    Args:
        make_store: zero-arg factory producing a fresh ``StateStore``.
        threads: number of concurrent worker threads to contend with. Must be >= 2
            -- a stress harness with one thread proves nothing about concurrency.
        iterations: per-thread repetitions of each contended operation. Cheap
            (dict-sized) work, so this stays well under a second even at high
            counts; it exists to widen the window for a real interleaving, not to
            measure throughput.
    """

    if threads < 2:
        raise AssertionError(
            f"stress harness needs >= 2 threads to exercise concurrency, got {threads}"
        )
    if iterations < 1:
        raise AssertionError(f"iterations must be >= 1, got {iterations}")

    store = make_store()
    try:
        _no_lost_updates_under_version_contention(
            store, threads=threads, iterations=iterations
        )
        _exactly_one_lease_holder(store, threads=threads, iterations=iterations)
        _tenant_isolation_under_concurrency(
            store, threads=threads, iterations=iterations
        )
    finally:
        store.close()


# --- invariant 1: no lost updates -----------------------------------------


def _no_lost_updates_under_version_contention(
    store: StateStore,
    *,
    threads: int,
    iterations: int,
) -> None:
    """Optimistic-concurrency safety proof: NO update is silently lost.

    Every thread runs ``iterations`` read-modify-write cycles against ONE shared
    record. A cycle re-reads the current record, builds a payload with the counter
    bumped by one, and tries ``put`` with ``expected_version`` set to the version
    it just read. Because read and put are separate Protocol calls, two threads can
    read the same version and both attempt to write version+1; the store lets
    exactly one win and raises ``VersionConflict`` on the loser. The loser does NOT
    drop its increment -- it loops, re-reads the now-newer version, and retries
    until its write commits.

    CRITICAL (the whole point): this loop must treat ``VersionConflict`` as
    "re-read and retry," never assume the read-modify-write was atomic. If it
    assumed atomicity it would lose the racing writer's increment and this very
    assertion would catch it.

    The harness counts each *successful* ``put`` in its own atomic counter. After
    all threads join:
        final payload counter == successful commits   (no write lost or doubled)
        final version == successful commits + initial version
    """

    tenant: TenantId = "tenant-stress"
    kind: Kind = "counter"
    record_id = "shared-counter"

    # Seed the record at version 1 (counter == 0). initial_version is whatever the
    # store assigns the first put, asserted rather than assumed so this stays valid
    # against any backend that honours "create -> version 1".
    seeded = store.put(
        LedgerRecord.new(
            tenant_id=tenant,
            kind=kind,
            record_id=record_id,
            payload={"counter": 0},
            source="stress.no_lost_updates",
        ),
        expected_version=0,
    )
    initial_version = seeded.version
    assert initial_version == 1, (
        "no-lost-updates setup expected create to yield version 1, "
        f"store yielded {initial_version}"
    )

    committed = _AtomicCounter()
    # Cap retries generously: with T threads each doing N increments, a single
    # increment can in the worst case lose the race to (T-1) other in-flight
    # writers before winning, but never indefinitely. This bound only guards
    # against a buggy store that NEVER lets a writer through (livelock); it is far
    # above any legitimate contention level and is asserted, not silently swallowed.
    max_attempts_per_increment = 1000 * threads

    def worker() -> None:
        for _ in range(iterations):
            attempts = 0
            while True:
                attempts += 1
                assert attempts <= max_attempts_per_increment, (
                    "no-lost-updates: a single increment exceeded "
                    f"{max_attempts_per_increment} attempts -- the store is not "
                    "letting optimistic writers through (livelock / never grants a "
                    "winning put)"
                )
                current = store.get(tenant, kind, record_id)
                assert current is not None, (
                    "no-lost-updates: the shared record vanished mid-run -- a "
                    "concurrent writer must never delete it"
                )
                read_version = current.version
                next_counter = int(current.payload["counter"]) + 1
                try:
                    store.put(
                        current.with_payload({"counter": next_counter}),
                        expected_version=read_version,
                    )
                except VersionConflict:
                    # Correct, expected outcome of a genuine race: someone committed
                    # between our read and our put. Re-read, recompute, retry. We do
                    # NOT count this as a commit and we do NOT keep our stale value.
                    continue
                else:
                    committed.increment()
                    break

    _run_workers(threads, worker)

    expected_total = threads * iterations
    successful = committed.value
    assert successful == expected_total, (
        "no-lost-updates: harness counted "
        f"{successful} successful commits but expected {expected_total} "
        "(threads * iterations) -- a thread gave up an increment it should have "
        "retried"
    )

    final = store.get(tenant, kind, record_id)
    assert final is not None, "no-lost-updates: final record unexpectedly absent"
    final_counter = int(final.payload["counter"])
    final_version = final.version

    assert final_counter == successful, (
        "LOST UPDATE DETECTED: final payload counter "
        f"{final_counter} != {successful} successful commits. The store let a "
        "stale writer clobber a committed update instead of raising VersionConflict."
    )
    assert final_version == successful + initial_version, (
        "no-lost-updates: final version "
        f"{final_version} != successful commits ({successful}) + initial version "
        f"({initial_version}). Version count and commit count disagree -- the store "
        "bumped version without persisting, or persisted without bumping."
    )


# --- invariant 2 + 3: exactly one lease holder, clean handoff -------------


@dataclass
class _CriticalSection:
    """Tracks how many threads are inside the lease-protected region at once.

    The single source of truth for the mutual-exclusion assertion. Guarded by its
    OWN lock (not the store's), so it is an independent witness: it observes how
    many lease holders the store actually let in, and screams if that is ever more
    than one.
    """

    _inside: int = 0
    _max_seen: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def enter(self) -> None:
        with self._lock:
            self._inside += 1
            if self._inside > self._max_seen:
                self._max_seen = self._inside
            # The invariant, checked while holding the witness lock so the read of
            # _inside is consistent: a correct store admits exactly one holder.
            assert self._inside == 1, (
                "LEASE MUTUAL EXCLUSION VIOLATED: "
                f"{self._inside} threads hold the same lease simultaneously "
                "(expected exactly 1). The store handed out a second live lease on "
                "a resource that was already leased."
            )

    def leave(self) -> None:
        with self._lock:
            self._inside -= 1
            assert self._inside >= 0, (
                "lease critical-section underflow -- leave() called without a "
                "matching enter(); harness bookkeeping bug"
            )

    @property
    def max_seen(self) -> int:
        with self._lock:
            return self._max_seen


def _exactly_one_lease_holder(
    store: StateStore,
    *,
    threads: int,
    iterations: int,
) -> None:
    """Single-holder lease proof: never two holders, and handoff stays clean.

    Determinism strategy -- TWO ``threading.Barrier`` rendezvous per round bracket
    the contention so "exactly one winner" is a real, non-flaky property rather than
    a timing accident. The naive single-barrier design (race, then each winner
    releases immediately) does NOT give one winner per round: the winner frees the
    lease mid-round, so a slower thread acquires it *after* the release and also
    "wins" -- every thread serialises through acquire/release and the per-round count
    is nondeterministic. Mutual exclusion still holds there, but the count is
    meaningless. Holding the lease across a second rendezvous fixes that.

    Each round:
      1. **Phase-1 rendezvous** -- all threads meet at the barrier, then each makes
         exactly ONE ``acquire_lease`` attempt on the SAME (tenant, resource).
      2. Exactly one wins with a ``Lease``; every other thread MUST see ``LeaseHeld``
         (it lost the race -- a correct, expected loss). The winner enters a critical
         section guarded by an independent ``_CriticalSection`` witness that asserts
         ``inside == 1``, and -- crucially -- does NOT release yet.
      3. **Phase-2 rendezvous** -- all threads meet again. Because the winner still
         holds the lease here, every loser necessarily made its attempt *while the
         winner held it*, so the round provably had exactly one holder.
      4. Only now does the winner leave the section and ``release_lease``, freeing the
         resource for the next round. (The phase-2 release happens-before the next
         round's phase-1 acquire via the barrier, so sections never overlap across
         rounds either.)

    Across all rounds the harness asserts:
      * the witness never saw more than one thread inside  (mutual exclusion);
      * the total number of distinct winners equals the number of rounds and every
        round produced exactly one winner  (clean handoff: no wedged resource, no
        double-hold, no round with zero or two winners).

    A long TTL is used so a winner's lease never expires mid-critical-section; this
    isolates the *contention* invariant from the (separately-tested) expiry path.
    """

    tenant: TenantId = "tenant-lease"
    resource = "shard-contended"
    rounds = iterations

    section = _CriticalSection()
    winners_per_round = [_AtomicCounter() for _ in range(rounds)]
    # Barrier spanning exactly the racing threads; every round all of them meet
    # here before anyone is allowed to touch the lease.
    barrier = threading.Barrier(threads)

    # TTL comfortably longer than the whole run so no lease lapses underneath a
    # holder; expiry is exercised by the conformance suite, not muddled in here.
    ttl_seconds = 3600.0

    def worker(worker_index: int) -> None:
        holder = f"worker-{worker_index}"
        try:
            for round_index in range(rounds):
                # --- Phase-1 rendezvous -------------------------------------
                # All threads meet here, then each makes exactly ONE acquire
                # attempt at (nearly) the same instant -- the contention is real,
                # not staggered. If a peer already failed and aborted the barrier,
                # wait() raises BrokenBarrierError and we stop racing so the real
                # failure propagates from the thread that aborted.
                barrier.wait()

                lease = None
                try:
                    lease = store.acquire_lease(
                        tenant,
                        resource,
                        holder=holder,
                        ttl_seconds=ttl_seconds,
                    )
                except LeaseHeld:
                    # Lost the race this round. Correct and expected: exactly the
                    # losers land here. We must NOT `continue` -- every thread,
                    # winner or loser, has to reach the phase-2 barrier below or
                    # the rendezvous would deadlock (parties would never all meet).
                    lease = None

                if lease is not None:
                    # Won the race -> sole holder. Record the win and enter the
                    # critical section, but do NOT release yet: holding across the
                    # phase-2 barrier is what makes "exactly one winner" true.
                    winners_per_round[round_index].increment()
                    section.enter()

                # --- Phase-2 rendezvous -------------------------------------
                # All threads meet again. Because the winner still holds the lease
                # here, every loser provably made its attempt WHILE the winner held
                # it -> the round had exactly one holder, deterministically.
                barrier.wait()

                if lease is not None:
                    # Only now release, freeing the resource for the next round.
                    # The next round's phase-1 barrier happens-after this release,
                    # so critical sections never overlap across rounds either.
                    section.leave()
                    store.release_lease(lease.token)
        except threading.BrokenBarrierError:
            # A sibling thread failed an invariant and aborted the barrier. Exit
            # quietly: the originating exception is the one worth reporting, and it
            # is already captured on that thread's future. Swallowing this here
            # only prevents a secondary, less-informative error.
            return
        except BaseException:
            # Any genuine failure on THIS thread (e.g. the mutual-exclusion assert
            # inside section.enter()): abort the barrier so peers parked at either
            # rendezvous wake immediately instead of deadlocking, then re-raise so
            # _run_workers surfaces it.
            barrier.abort()
            raise

    _run_workers(threads, worker, pass_index=True)

    assert section.max_seen <= 1, (
        "LEASE MUTUAL EXCLUSION VIOLATED: at peak "
        f"{section.max_seen} threads held the same lease at once (expected <= 1)."
    )

    # Clean-handoff ledger: every round must have had exactly one winner. A round
    # with zero winners would mean the resource wedged (held but unreleasable); a
    # round with two would mean a double-hold the witness might race past.
    for round_index, counter in enumerate(winners_per_round):
        winners = counter.value
        assert winners == 1, (
            "lease handoff broken at round "
            f"{round_index}: {winners} winners (expected exactly 1). "
            "Zero => resource wedged / never re-acquirable; >1 => double-hold."
        )

    total_winners = sum(c.value for c in winners_per_round)
    assert total_winners == rounds, (
        "lease handoff broken: "
        f"{total_winners} total winners across {rounds} rounds (expected one per "
        "round). Acquire/release accounting is inconsistent."
    )


# --- invariant 4: tenant isolation under concurrency ----------------------


def _tenant_isolation_under_concurrency(
    store: StateStore,
    *,
    threads: int,
    iterations: int,
) -> None:
    """Concurrent writers on the SAME record_id under different tenants stay isolated.

    Each thread owns a distinct tenant but they all write the same ``kind`` /
    ``record_id``. They run their read-modify-write loops simultaneously. If the
    store leaked across tenants, a thread would read a counter another tenant
    incremented (or overwrite it). After the run, every tenant's record must hold
    exactly its OWN ``iterations`` increments and carry its own marker -- proof the
    concurrent writes never crossed the tenant boundary.
    """

    kind: Kind = "isolated"
    record_id = "same-id-across-tenants"
    tenants: list[TenantId] = [f"tenant-iso-{i}" for i in range(threads)]

    # Seed one record per tenant under the shared id.
    for tenant in tenants:
        store.put(
            LedgerRecord.new(
                tenant_id=tenant,
                kind=kind,
                record_id=record_id,
                payload={"counter": 0, "owner": tenant},
                source="stress.tenant_isolation",
            ),
            expected_version=0,
        )

    def worker(worker_index: int) -> None:
        tenant = tenants[worker_index]
        for _ in range(iterations):
            while True:
                current = store.get(tenant, kind, record_id)
                assert current is not None, (
                    f"tenant-isolation: tenant {tenant!r} lost its record mid-run"
                )
                # A write must never see another tenant's marker. If isolation broke,
                # 'owner' would read as some other tenant's id.
                assert current.payload["owner"] == tenant, (
                    "TENANT ISOLATION VIOLATED: tenant "
                    f"{tenant!r} read a record owned by "
                    f"{current.payload['owner']!r} -- a concurrent writer under a "
                    "different tenant leaked across the tenant boundary."
                )
                next_counter = int(current.payload["counter"]) + 1
                try:
                    store.put(
                        current.with_payload({"counter": next_counter, "owner": tenant}),
                        expected_version=current.version,
                    )
                except VersionConflict:
                    # Per-tenant self-contention only (one writer per tenant here, so
                    # this should be rare), but handle it correctly regardless.
                    continue
                else:
                    break

    _run_workers(threads, worker, pass_index=True)

    for tenant in tenants:
        final = store.get(tenant, kind, record_id)
        assert final is not None, (
            f"tenant-isolation: tenant {tenant!r} record absent after run"
        )
        assert final.payload["owner"] == tenant, (
            "TENANT ISOLATION VIOLATED (post-run): tenant "
            f"{tenant!r} record ended up owned by {final.payload['owner']!r}."
        )
        assert int(final.payload["counter"]) == iterations, (
            "TENANT ISOLATION VIOLATED (post-run): tenant "
            f"{tenant!r} counter is {final.payload['counter']}, expected "
            f"{iterations} (its own increments only). A cross-tenant write either "
            "added to or clobbered this tenant's count."
        )


# --- crash-durability: explicitly OUT OF SCOPE for this harness ------------


def assert_crash_durability(make_store: StoreFactory) -> None:
    """OUT OF SCOPE here -- hook reserved for *durable* backends only.

    Crash / kill-mid-write durability (does committed state survive the process
    being killed between the mutation and a durable flush, and reappear on reopen?)
    is a property the in-memory reference store structurally CANNOT have: there is
    nothing it survives *to*. Demonstrating it requires a durable backend, a real
    kill, and a reopen against the same storage -- precisely the test
    ``test_state_substrate_sqlite.py`` will own once ``SqliteStateStore`` lands.

    This function exists to name that boundary honestly rather than fake it. It
    raises ``NotImplementedError`` so no caller can mistake "the stress suite
    passed" for "durability was verified." Declared vs verified is sacred; a stub
    is a stub, and this one says so out loud.
    """

    raise NotImplementedError(
        "crash-durability is not verifiable on a non-durable store and is "
        "deliberately NOT faked here. The durable backends (SQLite reopen test, "
        "etc.) own this assertion; the in-memory reference store has no persisted "
        "state to survive a crash, so calling it here is a category error."
    )


# --- shared worker runner --------------------------------------------------


def _run_workers(
    threads: int,
    worker: Callable[..., None],
    *,
    pass_index: bool = False,
) -> None:
    """Run ``worker`` on ``threads`` threads and re-raise the first failure.

    A ``ThreadPoolExecutor`` is used so an ``AssertionError`` (or any exception)
    raised inside a worker is captured on its future and re-raised here on the main
    thread -- otherwise a violated invariant would die silently in a background
    thread and the harness would wrongly "pass." ``future.result()`` is what turns
    a background assertion failure into a real test failure.

    When ``pass_index`` is true each worker receives its 0-based thread index (used
    to give a thread a distinct holder name / tenant); otherwise it is called with
    no arguments.
    """

    with ThreadPoolExecutor(max_workers=threads) as pool:
        if pass_index:
            futures = [pool.submit(worker, i) for i in range(threads)]
        else:
            futures = [pool.submit(worker) for _ in range(threads)]
        # Surface the first exception. Collecting results (not just waiting) is what
        # propagates a worker-thread AssertionError to the caller.
        for future in futures:
            future.result()
