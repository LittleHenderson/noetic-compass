"""^7 Rhythm tracking for the CAS-as-Belief-Substrate.

Authoritative definition (from CLAUDE.md): **^7 Rhythm — the rate and pattern
a Mind is exposed to an Idea, entraining/conditioning it.** Operationally, we
track the exposure count: every observation of the same claim bumps the
counter by one. The lock rule requires ``rhythm_count >= 3`` so that a single
fluky observation cannot drive a claim into the locked set.

Future extension (not required for v1): tracking the *pattern* of exposure —
inter-observation intervals — to distinguish steady drip from burst-and-silence.
The infrastructure here keeps the door open by routing through a dedicated
function rather than mutating belief fields ad-hoc.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .belief import Belief


# Minimum exposures required before a belief is eligible to lock. Tunable but
# documented; the lock rule pulls this constant rather than hard-coding 3 in
# multiple places.
MIN_RHYTHM_FOR_LOCK: int = 3


def bump_rhythm(
    belief: Belief,
    evidence_strength: float,
    *,
    now: datetime | None = None,
) -> Belief:
    """Return a new ``Belief`` with rhythm_count incremented by 1.

    ``evidence_strength`` is accepted for symmetry with the rest of the
    pipeline (the belief store passes the same strength to vibration and
    rhythm) and for forward compatibility with weighted rhythm. v1 simply
    increments the counter and refreshes ``last_reinforced``.

    The input belief is not mutated. ``now`` defaults to ``datetime.now()``.
    """
    if evidence_strength <= 0:
        raise ValueError(
            f"evidence_strength must be > 0, got {evidence_strength!r}"
        )
    when = now if now is not None else datetime.now()
    return replace(
        belief,
        rhythm_count=belief.rhythm_count + 1,
        last_reinforced=when,
    )


def has_rhythm_for_lock(belief: Belief) -> bool:
    """True iff the belief has enough exposures to be lock-eligible."""
    return belief.rhythm_count >= MIN_RHYTHM_FOR_LOCK
