"""Operator-readable status for the durable state ledger -- pure, dark-safe, additive.

The strangler-fig migration (``migration.py`` + ``api/state_ledger_bootstrap.py``) moves
the live CAS Harness off its process-global dicts and onto a durable ``StateStore`` ledger,
behind two flags, in deliberate phases:

1. ``NC_STATE_LEDGER_ENABLED=true`` installs a :class:`LedgerMirror` into both live services
   -- dual-write + shadow-compare every read against the ledger -- but the DICTS still serve
   every read.
2. The operator then WATCHES zero-divergence evidence accumulate on real traffic.
3. (separate workstream: live durable-backend tests.)
4. Only then ``NC_STATE_LEDGER_READ_AUTHORITY=true`` moves reads onto the ledger.

Steps 1/2/4 all need one question answered cheaply and honestly: *what posture am I in, and
how many shadow-compares have run, with how many divergences?* This module is that answer. It
is a single pure function over the handle the lifespan stashes on ``app.state.state_ledger``
(a :class:`StateLedgerHandle`, or ``None`` for the dark default) -- no app, no I/O, no globals
-- so it is directly unit-testable and safe to call from anywhere.

Dark-by-default is preserved here, not merely respected: when the handle is ``None`` (no mirror
installed -- production today) the function reports ``{"posture": "dark"}`` and touches nothing.
It reads only counters the mirror already maintains; it never mutates state and never changes
what serves reads. It is observation, not behaviour.

This module is dependency-light on purpose: it imports nothing from
``api/state_ledger_bootstrap.py`` (which imports this package), so re-exporting it from the
package ``__init__`` cannot create an import cycle. It reads the handle structurally (by
attribute) rather than against the concrete dataclass type, which keeps it decoupled and makes
it trivial to test with a tiny stand-in handle.
"""

from __future__ import annotations

from typing import Any, Optional

# The three honest postures the rollout can be in. Stable string constants so callers
# (an endpoint, a dashboard, a test) can compare against names rather than reading the
# narrative docstring. These map one-to-one onto the migration's phases:
#   dark                              -> no mirror installed (production default; Phase 0)
#   enabled_shadow_dict_authoritative -> mirror live, dual-write + shadow-compare,
#                                        DICTS still authoritative (Phases 1-2: the
#                                        zero-divergence watch)
#   enabled_ledger_read_authoritative -> Phase-3 flip applied; the LEDGER serves reads
POSTURE_DARK = "dark"
POSTURE_ENABLED_SHADOW = "enabled_shadow_dict_authoritative"
POSTURE_ENABLED_READ_AUTHORITY = "enabled_ledger_read_authoritative"


def ledger_status(handle: Optional[Any]) -> dict[str, object]:
    """Return a plain dict describing the live state-ledger posture for an operator.

    ``handle`` is whatever the lifespan stashed on ``app.state.state_ledger``: a
    :class:`StateLedgerHandle` when the ledger is enabled, or ``None`` for the dark
    default. The function is pure -- it derives everything from the handle and never
    mutates anything.

    Dark path (``handle is None``): production's default and the byte-for-byte-unchanged
    posture. Returns exactly ``{"posture": "dark"}`` and reads nothing further -- there is
    no mirror, so there are no counts to report, and inventing a "0 divergences" here would
    be a fabricated measurement (no shadow-compare ever ran). Honest silence instead.

    Enabled path (handle present): reports

        {
          "posture": "enabled_shadow_dict_authoritative"
                     | "enabled_ledger_read_authoritative",
          "audit_count": <int>,          # distributed-audit records rehydrated on startup
          "fleet_counts": {<str>: <int>},# fleet record counts rehydrated on startup
          "divergence_tally": {          # the live watch numbers (mirror.tally())
            "reads_compared": <int>,     # Phase-2 shadow-compare odometer
            "reads_served": <int>,       # Phase-3 authoritative-read odometer
            "divergences_found": <int>,
            "last_divergence": <small detail dict> | None,
          },
        }

    The posture distinguishes whether the Phase-3 read-authority flip has been applied
    (``read_authority`` on the handle): with it, the ledger serves reads; without it, the
    dicts still serve reads and the mirror is only shadow-comparing. ``divergence_tally``
    is read from the mirror's bounded counters (:meth:`LedgerMirror.tally`), so it is the
    real measured count -- never a hopeful zero. If a handle is somehow missing its mirror
    or the mirror lacks a ``tally`` (defensive only -- the real handle always carries a
    fully-formed mirror), the tally degrades to ``None`` rather than raising, because a
    status endpoint must never be the thing that breaks.
    """

    if handle is None:
        # Dark by default: no mirror, nothing measured, nothing to touch.
        return {"posture": POSTURE_DARK}

    read_authority = bool(getattr(handle, "read_authority", False))
    posture = (
        POSTURE_ENABLED_READ_AUTHORITY if read_authority else POSTURE_ENABLED_SHADOW
    )

    mirror = getattr(handle, "mirror", None)
    tally_fn = getattr(mirror, "tally", None)
    divergence_tally: Optional[dict[str, object]] = (
        tally_fn() if callable(tally_fn) else None
    )

    return {
        "posture": posture,
        "audit_count": getattr(handle, "audit_count", 0),
        "fleet_counts": dict(getattr(handle, "fleet_counts", {}) or {}),
        "divergence_tally": divergence_tally,
    }
