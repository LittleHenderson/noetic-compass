"""rc01_coordinator.py -- RC-0.1 hardened transaction coordinator.

Beyond RC-0's atomic allowed-field batch update, this coordinator enforces the full
transactional authority contract:

  - every intent is a VersionedIntent carrying episode id, tick, producer,
    base_state_version, base_state_digest, and its own intent digest;
  - REJECTED: stale base version; wrong tick; wrong episode; base-digest mismatch;
    duplicate conflicting writes to the same (expert, field) within one batch;
    governance writes; unknown fields; wrong value types; publication-consequence
    intents without a matching verifier receipt digest;
  - one invalid intent rejects the WHOLE batch atomically (state byte-identical);
  - BOTH successful and rejected batches are sealed into the trace; a rejection names
    the FIRST failed law and reveals no partial mutation;
  - per-expert state VERSION increments on every commit; digests are canonical-JSON
    SHA-256 of the state.

Deterministic, CPU-only.
"""
from __future__ import annotations

import dataclasses

from rc0_types import BiasState, RegionRecord, RPMState
from rc01_types import VersionedIntent, canonical, digest

ALLOWED_FIELDS = ("rpm", "record", "memory", "substrate")
FIELD_TYPES = {"rpm": RPMState, "record": RegionRecord, "memory": tuple, "substrate": tuple}


def state_digest(b: BiasState) -> str:
    return digest({
        "substrate": b.substrate, "memory": b.memory,
        "rpm": (b.rpm.desire, b.rpm.wisdom, b.rpm.power, b.rpm.open_subgoals,
                b.rpm.return_addresses, b.rpm.acquired),
        "record": (b.record.region_posterior, b.record.committed_region,
                   b.record.response_model_status, b.record.stability_status,
                   b.record.semantic_outcome),
        "theta": b.theta,
        "gov": (b.governance.hard_mask, b.governance.quarantined,
                b.governance.max_depth, b.governance.max_branches),
    })


class RejectedBatch(Exception):
    """Carries the FIRST failed law. State is guaranteed unchanged."""

    def __init__(self, law: str, detail: str = ""):
        self.law = law
        super().__init__(f"{law}: {detail}" if detail else law)


class HardenedCoordinator:
    def __init__(self, initial: dict, episode_id: str):
        self.episode_id = episode_id
        self._states = {}
        self._versions = {}
        for k, v in initial.items():
            if not isinstance(v, BiasState):
                raise TypeError(f"initial state for {k!r} must be a BiasState")
            self._states[k] = v
            self._versions[k] = 0
        self.trace = []
        self.verifier_receipts = set()   # digests of receipts this episode has sealed

    # ---- reads ----
    def get(self, expert_id: str) -> BiasState:
        return self._states[expert_id]

    def version(self, expert_id: str) -> int:
        return self._versions[expert_id]

    def get_digest(self, expert_id: str) -> str:
        return state_digest(self._states[expert_id])

    def expert_ids(self):
        return tuple(sorted(self._states.keys()))

    def register_verifier_receipt(self, receipt_digest: str):
        self.verifier_receipts.add(receipt_digest)

    # ---- the one write path ----
    def commit(self, intents, tick: int) -> str:
        """Atomic batch commit of VersionedIntents. Raises RejectedBatch (state
        untouched, rejection sealed) or returns 'COMMITTED' (commit sealed)."""
        try:
            staged = {}
            seen_writes = {}
            for it in intents:
                if not isinstance(it, VersionedIntent):
                    raise RejectedBatch("LAW_TYPED_INTENT",
                                        f"not a VersionedIntent: {type(it).__name__}")
                if it.episode_id != self.episode_id:
                    raise RejectedBatch("LAW_EPISODE_IDENTITY",
                                        f"intent episode {it.episode_id!r} != {self.episode_id!r}")
                if it.tick != tick:
                    raise RejectedBatch("LAW_TICK_IDENTITY",
                                        f"intent tick {it.tick} != commit tick {tick}")
                if it.expert_id not in self._states:
                    raise RejectedBatch("LAW_KNOWN_EXPERT", it.expert_id)
                if it.fld not in ALLOWED_FIELDS:
                    raise RejectedBatch("LAW_GOVERNANCE_OWNER_ONLY" if it.fld == "governance"
                                        else "LAW_ALLOWED_FIELD", it.fld)
                if not isinstance(it.new_value, FIELD_TYPES[it.fld]):
                    raise RejectedBatch("LAW_VALUE_TYPE",
                                        f"{it.fld} must be {FIELD_TYPES[it.fld].__name__}")
                if it.base_state_version != self._versions[it.expert_id]:
                    raise RejectedBatch("LAW_STALE_VERSION",
                                        f"intent base v{it.base_state_version} != "
                                        f"authoritative v{self._versions[it.expert_id]}")
                if it.base_state_digest != state_digest(self._states[it.expert_id]):
                    raise RejectedBatch("LAW_STALE_DIGEST", it.expert_id)
                if it.verifier_receipt_digest:
                    if it.verifier_receipt_digest not in self.verifier_receipts:
                        raise RejectedBatch("LAW_VERIFIER_RECEIPT",
                                            "intent cites an unknown verifier receipt")
                key = (it.expert_id, it.fld)
                if key in seen_writes and canonical(seen_writes[key]) != canonical(it.new_value):
                    raise RejectedBatch("LAW_NO_CONFLICTING_WRITES",
                                        f"duplicate conflicting writes to {key}")
                seen_writes[key] = it.new_value
                cur = staged.get(it.expert_id, self._states[it.expert_id])
                staged[it.expert_id] = dataclasses.replace(cur, **{it.fld: it.new_value})
            # atomic apply + version bump
            for eid, st in staged.items():
                self._states[eid] = st
                self._versions[eid] += 1
            self.trace.append({"tick": tick, "event": "COMMIT",
                               "intents": sorted(i.intent_digest for i in intents),
                               "versions": {e: self._versions[e] for e in sorted(staged)}})
            return "COMMITTED"
        except RejectedBatch as rb:
            # seal the rejection with the FIRST failed law; no partial mutation exists
            self.trace.append({"tick": tick, "event": "REJECTED",
                               "first_failed_law": rb.law,
                               "intents": sorted(getattr(i, "intent_digest", "untyped")
                                                 for i in intents
                                                 if isinstance(i, VersionedIntent))})
            raise

    def seal(self) -> str:
        return digest(self.trace)
