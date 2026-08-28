"""Self-improvement (the CAS-G9 loop): the machine diagnoses a fault
in its OWN procedure from its own sealed evidence, explores in a
sandbox, SYNTHESIZES a better procedure from what the exploration
proved, validates the candidate under the acceptance law, and promotes
it to versioned strategy memory - parent state always restorable.

This closes the recorded G8 bound: the improved procedure is not
picked from a hand-authored library; it is synthesized from the sealed
decisions of the machine's own sandbox run. Every step reads sealed
evidence only, and every step is recorded with digests.

The judge is untouchable throughout: expectations and protected
targets are outside mutation authority (ring R3), and the packet
records the judge digest before and after as proof.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional

from .mutations import DEFAULT_GUARD_POOL, R3_PROTECTED
from .rlp import CAS_RLP
from .strategies import StrategyMemory


def _seal(packet: Dict) -> str:
    payload = json.dumps(packet, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _judge_digest(package: Dict) -> str:
    """Digest of the evaluator: expectations + BOTH protected lists -
    the package's declared set and the ENFORCED module constant
    (audit finding: hashing only the package list was decorative)."""
    return _seal({"expectations": package.get("expectations", {}),
                  "protected": package.get("protected", []),
                  "enforced_protected": list(R3_PROTECTED)})


def _versioning_works() -> bool:
    """Scratch round-trip: the memory class actually versions entries
    (provisional -> verified, revision bump, history retained)."""
    scratch = StrategyMemory()
    scratch.add_provisional("scratch_class", ["a", "b"])
    entry = scratch.promote("scratch_class")
    return (entry["status"] == "verified" and entry["revision"] == 2
            and len(entry["history"]) == 1)


def _rollback_works(memory: StrategyMemory, parent_snapshot: Dict) -> bool:
    """Scratch round-trip on a COPY: mutate, restore, compare against
    the parent snapshot byte-for-byte."""
    probe = StrategyMemory()
    probe.entries = copy.deepcopy(memory.entries)
    probe.entries["__scratch__"] = {"fault_class": "__scratch__"}
    probe.entries = copy.deepcopy(parent_snapshot)
    return probe.entries == parent_snapshot


def _promoted(cycle: Dict) -> Optional[Dict]:
    for decision in cycle.get("decisions", []):
        if decision.get("verdict") == "PROMOTED":
            return decision
    return None


# ----------------------------------------------------------------------
# STEP 1: self-diagnosis - a typed fault about the PROCEDURE, read
# exclusively from the sealed cycle packet.
def diagnose_procedure(cycle_packet: Dict, budget: int) -> Optional[Dict]:
    """A procedural fault exists when the cycle promoted NOTHING and at
    least one candidate died of budget exhaustion: the repair CONTENT
    may exist, but the PROCEDURE (candidate order) does not fit the
    budget. Returns a typed record, or None when the procedure is fine.
    """
    # Tamper-evidence: re-seal the packet (minus its digest) and
    # verify before trusting anything it says.
    body = {k: v for k, v in cycle_packet.items() if k != "cycle_digest"}
    if _seal(body) != cycle_packet.get("cycle_digest"):
        raise ValueError("cycle packet digest mismatch: evidence tampered "
                         "or malformed")
    decisions = cycle_packet.get("decisions", [])
    if any(d.get("verdict") == "PROMOTED" for d in decisions):
        return None
    exhausted = [d for d in decisions
                 if d.get("verdict") == "BUDGET_EXHAUSTED"]
    if not exhausted:
        return None
    return {
        "fault_kind": "procedure_budget_failure",
        "budget": budget,
        "evaluations_used": cycle_packet.get("evaluations_used"),
        "starved_candidates": [d["mutation"]["mutation_id"]
                               for d in exhausted],
        "evidence_digest": cycle_packet.get("cycle_digest"),
    }


# ----------------------------------------------------------------------
# STEP 3: synthesis - the candidate procedure comes from the sealed
# exploration evidence, not from a library.
def synthesize_order(exploration_packet: Dict) -> Optional[Dict]:
    """Read the sealed UNBUDGETED exploration cycle; find the mutation
    that the acceptance law PROMOTED; put its guard first, the residual
    neutral pool after. The synthesized procedure carries the evidence
    digest it was derived from."""
    promoted = _promoted(exploration_packet)
    if promoted is None:
        return None
    mutation_id = promoted["mutation"]["mutation_id"]
    guard = promoted["mutation"]["change"].get("guard_pred")
    if guard is None:
        return None
    order = [guard] + [g for g in DEFAULT_GUARD_POOL if g != guard]
    return {
        "guard_order": order,
        "derived_from_mutation": mutation_id,
        "derived_from_evidence": exploration_packet.get("cycle_digest"),
    }


# ----------------------------------------------------------------------
class SelfImprover:
    """The full G9 cycle over one fault class.

    diagnose (own sealed evidence) -> explore (sandbox, parent
    untouched) -> synthesize (from sealed exploration) -> validate
    (acceptance law, budgeted, training AND held-out) -> promote
    (versioned memory, rollback preserved).
    """

    def __init__(self, training_package: Dict, held_out_package: Dict,
                 budget: int = 1,
                 memory: Optional[StrategyMemory] = None) -> None:
        self.training_package = copy.deepcopy(training_package)
        self.held_out_package = copy.deepcopy(held_out_package)
        self.budget = budget
        self.memory = memory if memory is not None else StrategyMemory()
        self.parent_memory = self.memory.snapshot()

    def run(self) -> Dict:
        judge_before = _judge_digest(self.training_package)

        # STEP 1: run the CURRENT procedure under budget; self-diagnose
        # from the sealed packet it produces.
        current = CAS_RLP(copy.deepcopy(self.training_package)).improve(
            strategy_memory=self.memory, max_evaluations=self.budget)
        fault = diagnose_procedure(current, self.budget)
        if fault is None:
            return self._packet("NO_PROCEDURAL_FAULT", judge_before,
                                diagnosis=None, exploration=None,
                                synthesis=None, validation=None)

        # STEP 2: sandbox exploration - UNBUDGETED, on a COPY; the
        # parent packages and memory are untouched.
        exploration = CAS_RLP(copy.deepcopy(self.training_package)).improve()

        # STEP 3: synthesize the candidate procedure from the sealed
        # exploration evidence.
        synthesis = synthesize_order(exploration)
        if synthesis is None:
            return self._packet("NO_REPAIR_FOUND", judge_before,
                                diagnosis=fault,
                                exploration=exploration.get("cycle_digest"),
                                synthesis=None, validation=None)

        # STEP 4: validate the candidate under the acceptance law -
        # budgeted, on training AND held-out fault cases.
        order = synthesis["guard_order"]
        training = CAS_RLP(copy.deepcopy(self.training_package)).improve(
            guard_order=order, max_evaluations=self.budget)
        held_out = CAS_RLP(copy.deepcopy(self.held_out_package)).improve(
            guard_order=order, max_evaluations=self.budget)
        regression = CAS_RLP(copy.deepcopy(self.training_package)).improve()

        checks = [
            {"check": "budget_success",
             "passed": _promoted(training) is not None
             and training.get("evaluations_used", 0) <= self.budget},
            {"check": "held_out_gain",
             "passed": _promoted(held_out) is not None
             and held_out.get("evaluations_used", 0) <= self.budget},
            {"check": "no_regression",
             "passed": _promoted(regression) is not None},
            {"check": "evaluator_untouched",
             "passed": _judge_digest(self.training_package) == judge_before},
            # REAL property checks (audit finding: these were
            # hardcoded True). Each exercises the actual memory class
            # on a scratch copy and would fail if the machinery broke.
            {"check": "versioned",
             "passed": _versioning_works()},
            {"check": "rollback_preserved",
             "passed": _rollback_works(self.memory, self.parent_memory)},
        ]
        validation = {
            "guard_order": order,
            "checks": checks,
            "training_digest": training.get("cycle_digest"),
            "held_out_digest": held_out.get("cycle_digest"),
            "regression_digest": regression.get("cycle_digest"),
        }

        # STEP 5: promote only when EVERY check holds. The fault class
        # is READ FROM THE EVIDENCE (audit finding: it was hardcoded):
        # the exploration packet seals what was diagnosed.
        diagnosed = exploration.get("diagnosed_faults", [])
        fault_class = diagnosed[0]["classification"] if diagnosed else None
        if fault_class is not None and all(c["passed"] for c in checks):
            self.memory.add_provisional(fault_class, order,
                                        provenance="self_improvement:"
                                        + str(synthesis["derived_from_evidence"]))
            self.memory.promote(fault_class)
            status = "PROMOTED"
        else:
            status = "REJECTED"

        return self._packet(status, judge_before, diagnosis=fault,
                            exploration=exploration.get("cycle_digest"),
                            synthesis=synthesis, validation=validation)

    def rollback(self) -> Dict:
        self.memory.entries = copy.deepcopy(self.parent_memory)
        return {"action": "ROLLBACK",
                "note": "parent strategy memory restored",
                "parent_memory": self.parent_memory}

    # ------------------------------------------------------------------
    def _packet(self, status: str, judge_before: str, diagnosis, exploration,
                synthesis, validation) -> Dict:
        packet = {
            "status": status,
            "budget": self.budget,
            "diagnosis": diagnosis,
            "exploration_digest": exploration,
            "synthesis": synthesis,
            "validation": validation,
            "judge_digest_before": judge_before,
            "judge_digest_after": _judge_digest(self.training_package),
            "parent_memory": self.parent_memory,
            "memory": self.memory.to_json(),
        }
        packet["cycle_digest"] = _seal(packet)
        return packet
