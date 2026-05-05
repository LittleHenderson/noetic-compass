"""CAS-as-Belief-Substrate (CABS).

A belief store that uses CAS framework primitives to lock in claims as
factually correct after enough evidence + structural sanity checks pass.

Public API:

* :class:`Belief` — the dataclass.
* :class:`BeliefStore` — the high-level façade (open with a path or default).
* :func:`lock_rule` — pure ``Belief -> bool`` lock decision.
* :func:`derive_claim_key` — deterministic claim key from (text, expression).
* :class:`Observation` — one timestamped reinforcement event.
* :func:`compute_vibration`, :func:`reinforce`, :func:`apply_decay` —
  ^4 Vibration scoring helpers.
* :func:`bump_rhythm`, :data:`MIN_RHYTHM_FOR_LOCK` — ^7 Rhythm helpers.
* :func:`check_rpm_chain`, :class:`RPMResult` — RPM gate.
* :func:`run_inversion_scan`, :class:`InversionScanResult`,
  :data:`ALL_AXES` — 7-axis inversion scan.
"""

from .belief import Belief
from .belief_store import (
    BeliefStore,
    VIBRATION_LOCK_THRESHOLD,
    derive_claim_key,
    lock_rule,
)
from .inversion_gate import (
    ALL_AXES,
    InversionScanResult,
    PLACEHOLDER_AXES,
    run_inversion_scan,
)
from .rhythm import MIN_RHYTHM_FOR_LOCK, bump_rhythm, has_rhythm_for_lock
from .rpm_gate import RPMResult, check_rpm_chain
from .vibration import (
    DEFAULT_HALF_LIFE_DAYS,
    Observation,
    apply_decay,
    compute_vibration,
    reinforce,
)

__all__ = [
    "ALL_AXES",
    "Belief",
    "BeliefStore",
    "DEFAULT_HALF_LIFE_DAYS",
    "InversionScanResult",
    "MIN_RHYTHM_FOR_LOCK",
    "Observation",
    "PLACEHOLDER_AXES",
    "RPMResult",
    "VIBRATION_LOCK_THRESHOLD",
    "apply_decay",
    "bump_rhythm",
    "check_rpm_chain",
    "compute_vibration",
    "derive_claim_key",
    "has_rhythm_for_lock",
    "lock_rule",
    "reinforce",
    "run_inversion_scan",
]
