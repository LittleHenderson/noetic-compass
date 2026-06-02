"""Tests for the pure ``ledger_status`` function -- the load-bearing observability surface.

``ledger_status`` is the one operator question answered cheaply and honestly: *what posture
am I in, and how many shadow-compares have run with how many divergences?* It is a pure
function over the handle the lifespan stashes on ``app.state.state_ledger`` (a
:class:`StateLedgerHandle` or ``None``), so it is tested here with no app spin-up at all.

What is locked:

* DARK PATH (``handle is None`` -- production's default): returns exactly
  ``{"posture": "dark"}`` and nothing else. No fabricated "0 divergences", no other keys.
* ENABLED, dict-authoritative: posture ``enabled_shadow_dict_authoritative`` +
  audit_count / fleet_counts / the real divergence_tally read off the mirror.
* ENABLED, ledger-read-authoritative: posture ``enabled_ledger_read_authoritative`` when the
  Phase-3 flip was applied (handle.read_authority True).
* the tally reported is the REAL measured count from the live mirror (never a hopeful zero),
  and it tracks shadow-compares performed after the handle was built.
* structural (duck-typed) read of the handle: a minimal stand-in with the same attributes
  works, and a degenerate handle missing its mirror degrades the tally to None rather than
  raising (a status surface must never be the thing that breaks).

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_ledger_observability_status.py -q
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.services.production.state_substrate import (
    InMemoryStateStore,
    LedgerMirror,
    POSTURE_DARK,
    POSTURE_ENABLED_READ_AUTHORITY,
    POSTURE_ENABLED_SHADOW,
    ledger_status,
)
from api.state_ledger_bootstrap import StateLedgerHandle


def _enabled_handle(*, read_authority: bool) -> StateLedgerHandle:
    """A real handle around a real in-memory-backed mirror (no app, no I/O)."""
    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    if read_authority:
        mirror.enable_ledger_reads()
    return StateLedgerHandle(
        store=store,
        mirror=mirror,
        audit_count=2,
        fleet_counts={"run": 3, "worker": 5},
        read_authority=read_authority,
    )


# --------------------------------------------------------------------------
# dark path -- the sacred default
# --------------------------------------------------------------------------


def test_none_handle_reports_dark_and_nothing_else():
    # Production's default posture: no mirror installed. Must be honest silence, not a
    # fabricated zero-divergence reading (no compare ever ran to measure).
    status = ledger_status(None)
    assert status == {"posture": POSTURE_DARK}
    # Specifically: no counts are invented on the dark path.
    assert "divergence_tally" not in status
    assert "audit_count" not in status


# --------------------------------------------------------------------------
# enabled paths -- posture + real tally
# --------------------------------------------------------------------------


def test_enabled_shadow_posture_when_read_authority_off():
    handle = _enabled_handle(read_authority=False)
    status = ledger_status(handle)

    assert status["posture"] == POSTURE_ENABLED_SHADOW
    assert status["audit_count"] == 2
    assert status["fleet_counts"] == {"run": 3, "worker": 5}
    # Fresh mirror: real measured zero (a compare path exists and reported 0), not a guess.
    assert status["divergence_tally"] == {
        "reads_compared": 0,
        "reads_served": 0,
        "divergences_found": 0,
        "last_divergence": None,
    }


def test_enabled_read_authority_posture_when_flip_applied():
    handle = _enabled_handle(read_authority=True)
    status = ledger_status(handle)
    assert status["posture"] == POSTURE_ENABLED_READ_AUTHORITY
    assert status["audit_count"] == 2


def test_status_surfaces_reads_served_odometer_under_read_authority():
    # The Phase-3 watch: once read-authority is flipped, reads_compared freezes and the
    # operator watches reads_served climb (paired with divergences_found == 0). The status
    # surface must expose that odometer so the window does not look dead after the flip.
    handle = _enabled_handle(read_authority=True)
    mirror = handle.mirror
    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")

    # Authoritative reads -- exactly what the live get_* / list_* serve under read-authority.
    mirror.read_payload("run", "run-1")
    mirror.read_all_payloads("run")

    tally = ledger_status(handle)["divergence_tally"]
    assert tally["reads_served"] == 2
    assert tally["reads_compared"] == 0, "no shadow-compare runs under read-authority"
    assert tally["divergences_found"] == 0


def test_tally_reflects_real_shadow_compares_after_build():
    handle = _enabled_handle(read_authority=False)
    mirror = handle.mirror
    mirror.mirror_put("run", "run-1", {"status": "RUNNING"}, source="svc")

    # One clean compare + one mismatch -> the status tally must show the real numbers.
    assert mirror.shadow_compare("run", "run-1", {"status": "RUNNING"}) is None
    mirror.shadow_compare("run", "run-1", {"status": "DONE"})  # payload_mismatch

    tally = ledger_status(handle)["divergence_tally"]
    assert tally["reads_compared"] == 2
    assert tally["divergences_found"] == 1
    assert tally["last_divergence"]["reason"] == "payload_mismatch"
    assert tally["last_divergence"]["record_id"] == "run-1"


def test_fleet_counts_is_a_copy_not_the_handle_dict():
    # Defensive: the returned dict must not alias the handle's, so a caller mutating the
    # status can't corrupt startup-observability state.
    handle = _enabled_handle(read_authority=False)
    status = ledger_status(handle)
    status["fleet_counts"]["run"] = 999
    assert handle.fleet_counts["run"] == 3


# --------------------------------------------------------------------------
# structural / defensive behaviour
# --------------------------------------------------------------------------


def test_status_reads_handle_structurally_with_a_stand_in():
    # ledger_status duck-types the handle -- a minimal object with the same attributes
    # drives it exactly like the real dataclass (keeps callers/tests decoupled).
    @dataclass
    class _StandIn:
        mirror: Any
        audit_count: int
        fleet_counts: dict
        read_authority: bool

    store = InMemoryStateStore()
    mirror = LedgerMirror(store)
    stand_in = _StandIn(
        mirror=mirror, audit_count=7, fleet_counts={"run": 1}, read_authority=False
    )
    status = ledger_status(stand_in)
    assert status["posture"] == POSTURE_ENABLED_SHADOW
    assert status["audit_count"] == 7
    assert status["divergence_tally"]["reads_compared"] == 0


def test_status_degrades_tally_to_none_when_handle_has_no_usable_mirror():
    # A degenerate handle (no mirror / no tally) must not make the status endpoint raise;
    # the tally degrades to None instead. A status surface must never be what breaks.
    @dataclass
    class _NoMirror:
        mirror: Any = None
        audit_count: int = 0
        fleet_counts: dict = None  # type: ignore[assignment]
        read_authority: bool = False

    status = ledger_status(_NoMirror())
    assert status["posture"] == POSTURE_ENABLED_SHADOW
    assert status["divergence_tally"] is None
    # None fleet_counts coerces to an empty dict rather than propagating None.
    assert status["fleet_counts"] == {}
