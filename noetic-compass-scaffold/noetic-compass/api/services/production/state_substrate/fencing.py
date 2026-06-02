"""Resource-side fencing-token guard -- the half of the §5.2 fix that lives at the
point of effect, not at the lock.

The single most important multi-host hazard (docs 11 §5.2) is the
*dead-but-not-expired holder*: a worker acquires a lease, stalls (GC pause, VM
freeze, disk stall) past its TTL, the store correctly hands the lease to a newer
holder, and then the stalled worker *wakes up still believing it holds the lease*
and tries to act. No acquire-time SQL or ``SET NX`` can prevent this -- the lease
*was* validly reassigned; the old holder's belief is simply stale.

The fix has two halves, and this module is the second one:

1. **Mint side (the store).** ``PostgresStateStore.acquire_lease`` stamps a
   *monotonically increasing* ``fence`` into every ``Lease`` it returns (a Postgres
   ``BIGINT`` sequence value). Every successful acquire of a given resource gets a
   strictly larger fence than every prior acquire of that resource. See
   ``postgres_store.py`` and ``Lease.fence`` in ``interface.py``.
2. **Check side (the resource) -- this module.** The *protected resource* (a WORM
   writer, a database row, an external API) remembers the highest fence it has ever
   acted on and **rejects any operation carrying a fence that is not strictly
   greater** than that high-water mark. When stalled Host A wakes and tries to write
   with fence ``42`` but live Host B already wrote with fence ``43``, the resource
   rejects A's fence-42 write as stale.

Per Kleppmann ("How to do distributed locking"): a lock/lease service alone cannot
prevent a paused holder from acting after its lease lapses; **only a fencing token
checked by the protected resource** can. Fencing is *a property of the resource,
not of the lock* -- which is precisely why this guard is backend-agnostic and lives
beside (not inside) any particular ``StateStore``. A SQLite-backed resource, a
Postgres row, and an S3 object-lock writer can all use the same guard.

This module is pure logic with **no database dependency**, so it is fully unit
testable without a live Postgres (see ``tests/test_state_substrate_postgres.py``).
That matters: the mint side can only be verified against a real Postgres, but the
check side -- the part that actually stops the stale write -- is verifiable here and
now, deterministically.
"""

from __future__ import annotations

import threading

from .interface import StaleFenceToken

# A fence below this is never legitimate: the store mints fences from a sequence
# that starts at 1, and a default/unfenced ``Lease`` carries fence 0. A resource
# that has seen nothing yet sits at this sentinel so the very first real fence
# (>= 1) is accepted.
_NO_FENCE_SEEN = 0


def reject_stale_fence(highest_seen: int, incoming: int) -> int:
    """Pure fencing check: accept ``incoming`` iff it is strictly greater than
    ``highest_seen``; otherwise raise :class:`StaleFenceToken`.

    Returns the new high-water mark (``incoming``) on acceptance, so a caller that
    threads the value functionally can do ``highest = reject_stale_fence(highest, f)``.

    Strictly-greater (``>``), not ``>=``: re-presenting the *same* fence must be
    rejected, because two distinct operations carrying the identical fence would
    mean the monotonicity guarantee was violated upstream (two acquires minted the
    same number) -- and honouring both would defeat the entire point. A stalled
    holder re-presenting its old, equal-or-lower fence is exactly the attack this
    refuses.

    This function is intentionally free of any lock or storage: it is the
    *decision*, isolated, so it can be reasoned about and tested in isolation.
    :class:`FencingGuard` wraps it with a thread-safe, stateful high-water mark for
    the common in-process case.
    """

    if incoming > highest_seen:
        return incoming
    raise StaleFenceToken(highest_seen=highest_seen, incoming=incoming)


class FencingGuard:
    """A thread-safe, stateful fencing high-water mark for one protected resource.

    Wraps :func:`reject_stale_fence` with a remembered high-water mark and a lock,
    so a resource can simply call ``guard.check(lease.fence)`` before each effectful
    operation. Acceptance advances the high-water mark; rejection raises
    :class:`StaleFenceToken` and leaves the mark unchanged.

    One guard instance corresponds to one protected resource (one WORM stream, one
    row, one external endpoint). Sharing a single guard across unrelated resources
    would serialise their fences against each other and spuriously reject legitimate
    writes -- so construct one guard per resource, exactly as you would mint fences
    per resource on the store side.

    Honesty boundary: this guard is an **in-process** high-water mark. It protects a
    resource whose effect-point is reached from a single process (or whose
    high-water mark is itself persisted by the resource). A resource shared across
    hosts must persist its high-water mark in the same store it writes to (e.g. a
    ``fence`` column the write is conditioned on, ``WHERE incoming_fence >
    stored_fence``), so the check is atomic with the effect. ``FencingGuard`` is the
    reference semantics for that check; a cross-host resource implements the *same*
    rule transactionally at its own effect-point. This class does not, by itself,
    make a multi-host resource safe -- it states, executably, the rule such a
    resource must enforce.
    """

    __slots__ = ("_highest_seen", "_lock")

    def __init__(self, *, highest_seen: int = _NO_FENCE_SEEN) -> None:
        # Start below the first legitimate fence (sequence starts at 1) so the first
        # real fence is accepted. A caller restoring a persisted high-water mark may
        # seed it explicitly.
        self._highest_seen = highest_seen
        self._lock = threading.RLock()

    @property
    def highest_seen(self) -> int:
        """The highest fence this guard has accepted so far (its high-water mark)."""

        with self._lock:
            return self._highest_seen

    def check(self, incoming: int) -> int:
        """Accept ``incoming`` iff strictly greater than the high-water mark.

        On acceptance, advance the high-water mark and return it. On rejection,
        raise :class:`StaleFenceToken` and leave the high-water mark untouched -- a
        rejected stale write must not move the mark (it never happened).
        """

        with self._lock:
            new_high = reject_stale_fence(self._highest_seen, incoming)
            self._highest_seen = new_high
            return new_high
