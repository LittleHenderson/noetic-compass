"""^4 Vibration scoring for the CAS-as-Belief-Substrate.

Authoritative definition (from CLAUDE.md): **^4 Vibration — the degree to
which an Idea resonates with the Mind, its impression.** Operationally, we
treat this as a saturating real in [0, 1] that grows on observation and decays
without reinforcement.

Two operations:

* **Reinforcement.** When a new observation arrives, vibration grows
  asymptotically toward 1.0. Each observation contributes
  ``evidence_strength * (1 - current)``: small evidence on a fresh belief
  produces large jumps; the same evidence on a near-saturated belief produces
  small jumps.
* **Decay.** Without reinforcement, vibration decays exponentially with a
  half-life of 30 days by default. Decay is applied lazily — at the moment
  vibration is read or recomputed — by passing the elapsed wall-clock time and
  the previous timestamp to :func:`apply_decay`.

The two together compose a stateless ``compute_vibration(observations, now)``
that walks a list of timestamped observations, applying decay between each
adjacent pair, then reinforcement at each observation, and a final decay step
to ``now``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta


# Half-life of 30 days. After 30 days without reinforcement, vibration halves.
DEFAULT_HALF_LIFE_DAYS: float = 30.0


@dataclass(frozen=True)
class Observation:
    """A single timestamped observation of a claim.

    `evidence_strength` should be in (0, 1]. Typical values: 0.5 for a chat
    session restatement, 1.0 for a cited authoritative source. Values <= 0
    raise; values > 1 are clamped at the call site of :func:`reinforce`.
    """

    timestamp: datetime
    evidence_strength: float

    def __post_init__(self) -> None:  # pragma: no cover - dataclass guard
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"timestamp must be datetime, got {type(self.timestamp).__name__}"
            )
        if self.evidence_strength <= 0:
            raise ValueError(
                f"evidence_strength must be > 0, got {self.evidence_strength!r}"
            )


def apply_decay(
    current: float,
    elapsed: timedelta,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Exponentially decay ``current`` over ``elapsed`` time.

    ``new = current * (1/2) ** (elapsed_days / half_life_days)``.
    Negative elapsed clamps to 0 (timestamps in the future do not retroactively
    increase vibration). half_life_days must be > 0.
    """
    if half_life_days <= 0:
        raise ValueError(
            f"half_life_days must be > 0, got {half_life_days!r}"
        )
    if not (0.0 <= current <= 1.0):
        raise ValueError(f"current must be in [0, 1], got {current!r}")
    elapsed_days = max(0.0, elapsed.total_seconds() / 86400.0)
    if elapsed_days == 0.0:
        return current
    factor = math.pow(0.5, elapsed_days / half_life_days)
    return current * factor


def reinforce(current: float, evidence_strength: float) -> float:
    """Add a single observation's contribution to a vibration value.

    new = current + evidence_strength * (1 - current), clamped to [0, 1].
    Saturates as current approaches 1: the marginal contribution of additional
    evidence shrinks. Negative evidence is rejected.
    """
    if not (0.0 <= current <= 1.0):
        raise ValueError(f"current must be in [0, 1], got {current!r}")
    if evidence_strength <= 0:
        raise ValueError(
            f"evidence_strength must be > 0, got {evidence_strength!r}"
        )
    eff = min(evidence_strength, 1.0)
    bumped = current + eff * (1.0 - current)
    return min(1.0, max(0.0, bumped))


def compute_vibration(
    observations: list[Observation],
    now: datetime,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Replay ``observations`` to compute the current vibration at ``now``.

    Algorithm (decay-then-reinforce, then final decay-to-now):

    * start at 0.0
    * for each observation in chronological order:
        * decay from the previous timestamp to this observation's timestamp
        * reinforce by ``evidence_strength``
    * decay from the last observation's timestamp to ``now``

    Empty observations list returns 0.0 regardless of ``now``.
    """
    if not observations:
        return 0.0
    sorted_obs = sorted(observations, key=lambda o: o.timestamp)
    value = 0.0
    last_t = sorted_obs[0].timestamp
    for obs in sorted_obs:
        elapsed = obs.timestamp - last_t
        value = apply_decay(value, elapsed, half_life_days)
        value = reinforce(value, obs.evidence_strength)
        last_t = obs.timestamp
    final_elapsed = now - last_t
    if final_elapsed.total_seconds() > 0:
        value = apply_decay(value, final_elapsed, half_life_days)
    return value
