"""rc0_coordinator.py -- the atomic Bias transaction coordinator (RC-0 requirement 5).

The CJT never mutates authoritative Bias state directly. It emits BiasUpdateIntent
objects; ONLY this coordinator validates and applies them, atomically: either the whole
batch commits and produces the tick's B_{t+1} set, or the whole batch is rejected and
B_{t+1} = B_t (rollback). Every commit and rejection is sealed into the trace.

BiasState is a frozen dataclass, so even buggy code cannot setattr its way past this --
a direct write raises FrozenInstanceError. This mirrors the CNCM kernel's atomic
state-owner rule.
"""
from __future__ import annotations

import dataclasses
import hashlib

from rc0_types import (BiasState, BiasUpdateIntent, Governance, RegionRecord, RPMState)
from rc_canonical import canonical  # RC-0.4: exact-type encoder; default=str is dead

ALLOWED_FIELDS = ("rpm", "record", "memory", "substrate")
FIELD_TYPES = {"rpm": RPMState, "record": RegionRecord, "memory": tuple, "substrate": tuple}


class TransactionCoordinator:
    """Owns the authoritative expert_id -> BiasState map."""

    def __init__(self, initial: dict):
        for k, v in initial.items():
            if not isinstance(v, BiasState):
                raise TypeError(f"initial state for {k!r} must be a BiasState")
        self._states = dict(initial)
        self.trace = []

    def get(self, expert_id: str) -> BiasState:
        return self._states[expert_id]

    def expert_ids(self):
        return tuple(sorted(self._states.keys()))

    def commit(self, intents, tick: int):
        """Validate then apply a batch of intents ATOMICALLY. Returns 'COMMITTED' or
        raises ValueError with the rejection reason (in which case NOTHING applied)."""
        staged = {}
        # ---- validate every intent BEFORE applying any ----
        for it in intents:
            if not isinstance(it, BiasUpdateIntent):
                raise ValueError(f"REJECTED: not a BiasUpdateIntent: {type(it).__name__}")
            if it.expert_id not in self._states:
                raise ValueError(f"REJECTED: unknown expert {it.expert_id!r}")
            if it.fld not in ALLOWED_FIELDS:
                raise ValueError(f"REJECTED: field {it.fld!r} is not intent-updatable "
                                 f"(allowed: {ALLOWED_FIELDS}; governance changes are owner-only)")
            if not isinstance(it.new_value, FIELD_TYPES[it.fld]):
                raise ValueError(f"REJECTED: {it.fld} must be {FIELD_TYPES[it.fld].__name__}, "
                                 f"got {type(it.new_value).__name__}")
            cur = staged.get(it.expert_id, self._states[it.expert_id])
            staged[it.expert_id] = dataclasses.replace(cur, **{it.fld: it.new_value})
        # ---- apply atomically ----
        self._states.update(staged)
        self.trace.append({
            "tick": tick, "event": "COMMIT",
            "intents": [{"expert": i.expert_id, "field": i.fld, "reason": i.reason}
                        for i in intents],
        })
        return "COMMITTED"

    def seal(self) -> str:
        """Seal the trace: canonical-JSON SHA-256 digest (deterministic replay check)."""
        return hashlib.sha256(canonical(self.trace).encode("utf-8")).hexdigest()
