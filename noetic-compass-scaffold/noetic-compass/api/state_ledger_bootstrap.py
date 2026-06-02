"""Operational enable for the durable state ledger -- dark by default, two-flag phased.

The durable state substrate (``api/services/production/state_substrate/``) and its
strangler-fig seam (``...state_substrate/migration.py``) ship the *mechanism* for moving
the public CAS Harness off its process-global dicts (``_DISTRIBUTED_AUDITS``, ``_WORKERS``,
``_FLEET_RUNS``, ``_FRAGMENT_REFS``) and onto a durable ``StateStore`` ledger. That seam is
shipped DARK: with no :class:`LedgerMirror` installed, the dicts are authoritative, the
ledger is never written or read, and production behaviour is byte-for-byte unchanged. The
migration tests prove that property; it is sacred.

This module is the *operational counterpart* to that mechanism: it lets an operator turn the
ledger ON in a real deployment, deliberately and reversibly, without disturbing the
dark-by-default invariant when the flags are unset. All the wiring lives here as small, pure,
directly-testable functions so the lifespan in ``api/main.py`` stays thin and the test suite
never has to spin the whole app.

Why dark-by-default is preserved, not merely respected
------------------------------------------------------
:func:`install_state_ledger` keys entirely off ``settings.state_ledger_enabled``. When that
flag is False (its default, and production's posture) the function installs no mirror and
returns ``None`` -- the exact state every existing test asserts. The serving path stays
*structurally* pinned to the dicts: with no mirror, the live ``get_*`` / ``list_*`` read sites
(which gate on ``_STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger``) cannot consult
a ledger that is not there. You cannot enable durability by accident; you have to set the flag.

Why two separate flags (this separation is load-bearing)
--------------------------------------------------------
The enable is split across two flags that map onto the migration's phases:

* ``state_ledger_enabled`` brings Phases 1-2 live: it installs a :class:`SqliteStateStore` +
  :class:`LedgerMirror` into BOTH live services and rehydrates the dicts from the durable file
  on startup. Dual-write and shadow-compare are now running against real traffic -- but the
  DICTS REMAIN THE READ AUTHORITY. This is the posture in which an operator earns
  *zero-divergence evidence on production traffic* (the migration's Phase-2 proof obligation)
  before trusting the ledger to answer anything.

* ``state_ledger_read_authority`` performs the Phase-3 flip: only when this is ALSO set does
  install additionally call :meth:`LedgerMirror.enable_ledger_reads`, moving READ authority onto
  the ledger. Keeping it a distinct flag is the whole point -- it lets a deployment run the
  mirror live and accumulate real-traffic divergence evidence for as long as it wants before
  ever changing what serves reads. Defaulting it off keeps the cutover an explicit, separate
  act, never a side effect of merely enabling durability.

Both flags default False, so an unconfigured deployment is fully dark.

Why install fails loud, never falls back silently
--------------------------------------------------
If the operator set ``state_ledger_enabled=True`` and the install cannot complete (an
unwritable ledger path, a store error, a rehydrate failure), :func:`install_state_ledger` lets
the error propagate so startup fails loudly. Silently degrading to dict-only serving while the
operator believes the durable ledger is on would be a declared-vs-verified violation of exactly
the kind this program exists to refuse: the deployment would be making a durability claim its
running state has not earned. A failed startup an operator can see and fix is the honest
outcome. If the install fails *partway* (the mirror was set on one service before a later step
threw), it is unwound on both services before re-raising, so a failed startup never leaves a
half-installed mirror behind to mislead the next request or the next test.
"""

from __future__ import annotations

from dataclasses import dataclass

from api.services import cas_harness_distributed_audits as da
from api.services import cas_harness_fleet_executor as fe
from api.services.production.state_substrate import LedgerMirror, StateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


@dataclass(frozen=True, slots=True)
class StateLedgerHandle:
    """What an enabled install produced, carried from startup to shutdown.

    Returned by :func:`install_state_ledger` only when the ledger is enabled; ``None`` stands
    for the dark default. The lifespan stashes it on startup and hands it back to
    :func:`teardown_state_ledger` on shutdown so the same ``store`` gets closed and the same
    mirror gets uninstalled. ``audit_count`` / ``fleet_counts`` record what rehydrate restored
    from the durable file (honest startup observability -- how much pre-restart state came
    back), and ``read_authority`` records whether the Phase-3 flip was applied.
    """

    store: StateStore
    mirror: LedgerMirror
    audit_count: int
    fleet_counts: dict[str, int]
    read_authority: bool


def install_state_ledger(settings) -> StateLedgerHandle | None:
    """Install + rehydrate the durable ledger per the two flags, or stay dark.

    Dark path: when ``settings.state_ledger_enabled`` is False (the default, production's
    posture), install nothing and return ``None``. No mirror is set on either service, so the
    serving path stays structurally pinned to the dicts -- byte-for-byte the current behaviour.

    Enabled path: build a :class:`SqliteStateStore` on ``settings.state_ledger_path``, wrap it in
    one :class:`LedgerMirror`, install that single mirror into BOTH live services (they partition
    the one store by record ``kind``, so they coexist in it), and rehydrate each service's dicts
    from the durable file so a restarted process serves the state it served before. When
    ``settings.state_ledger_read_authority`` is ALSO set, apply the Phase-3 flip
    (:meth:`LedgerMirror.enable_ledger_reads`) so the ledger becomes the read authority; otherwise
    reads still come from the dicts (Phase 1-2: dual-write + shadow-compare only).

    Fail-loud: any error from constructing the store, installing the mirror, or rehydrating
    propagates -- startup must fail visibly rather than degrade to dict-only serving while the
    operator believes durability is on. If the failure lands after the mirror was set on one
    service, both mirrors are cleared before the error re-raises so no half-installed mirror is
    left behind.
    """

    if not settings.state_ledger_enabled:
        # The dark default: no mirror installed, ledger untouched, dicts authoritative.
        return None

    # Construct the durable store first. If the path is unwritable or the file is corrupt,
    # this raises before any mirror is installed -- the cleanest possible failure point.
    store = SqliteStateStore(settings.state_ledger_path)
    mirror = LedgerMirror(store)

    # From here a mirror may already be set on a service when a later step throws, so any
    # failure must uninstall both mirrors (and close the store) before re-raising. Otherwise a
    # failed startup would leave the seam half-wired -- a worse state than either fully dark or
    # fully enabled.
    try:
        da.set_state_mirror(mirror)
        fe.set_state_mirror(mirror)
        audit_count = da.rehydrate_from_ledger(store)
        fleet_counts = fe.rehydrate_from_ledger(store)
        if settings.state_ledger_read_authority:
            # Phase 3: the deliberate, separately-flagged read-authority flip.
            mirror.enable_ledger_reads()
    except BaseException:
        # Unwind a partial install so a failed startup never leaves a half-installed mirror.
        # Uninstalling the mirror on both services is the load-bearing post-condition; closing
        # the store is best-effort and must never mask the original startup error (which has to
        # surface so the operator sees and fixes the real cause).
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        try:
            store.close()
        except Exception:
            pass
        raise

    return StateLedgerHandle(
        store=store,
        mirror=mirror,
        audit_count=audit_count,
        fleet_counts=fleet_counts,
        read_authority=settings.state_ledger_read_authority,
    )


def teardown_state_ledger(handle: StateLedgerHandle | None) -> None:
    """Uninstall the mirror from both services and close the store; restore the dark state.

    The dark-path counterpart: when ``handle`` is ``None`` (the ledger was never enabled) there
    is nothing to undo. When a handle is present, clear the mirror on BOTH services -- returning
    the serving path to the dicts -- and close the durable store. Defensive about close so a
    backend that errors on close still leaves both mirrors uninstalled (the more important
    invariant: no mirror must outlive shutdown and leak into the next process or test).
    """

    if handle is None:
        return

    da.set_state_mirror(None)
    fe.set_state_mirror(None)
    try:
        handle.store.close()
    except Exception:
        # Closing the store is best-effort: the load-bearing post-condition is that no mirror
        # remains installed (already done above). SqliteStateStore.close is itself idempotent,
        # so this guard only covers a backend that raises on an already-degraded handle.
        pass
