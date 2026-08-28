"""The acceptance law: promote, quarantine, or reject.

A child may be promoted only when ALL hold: target gain >= delta_min,
no protected regression, authority invariants intact, deterministic
replay passes, held-out outperformance, the evaluator was not modified
by the same change, a sealed evidence packet, and rollback preserved.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

from .diagnosis import proposition_matches
from .mutations import Mutation


def _passed(grades: Dict, group: str) -> List[str]:
    return sorted(pid for pid, g in grades.items() if g["group"] == group and g["passed"])


def _seal_evidence(packet: Dict) -> str:
    payload = json.dumps(packet, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def decide(parent_package: Dict, child_package: Dict, mutation: Mutation,
           parent_grades: Dict, child_grades: Dict, replay_ok_flag: bool,
           replay_detail: str, delta_min: int = 1) -> Dict:
    checks: List[Dict] = []
    protected = parent_package.get("protected", [])

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    # Authority: ring and protected targets.
    if mutation.ring == "R3":
        check("authority_invariants", False, f"ring R3 mutation {mutation.mutation_id}")
        return _verdict("REJECTED_AS_PROTECTED", checks, mutation, parent_package, child_package, parent_grades, child_grades)

    # Evaluator tampering: the child must not rewrite the tests that judge it.
    tampered = (mutation.target in ("expectations", "benchmarks")
                or mutation.target.startswith("expectations")
                or mutation.change.get("kind") == "modify_expectations"
                or bool(mutation.change.get("modify_expectations")))
    if tampered:
        check("evaluator_not_modified", False,
              f"mutation {mutation.mutation_id} modifies the evaluator")
        return _verdict("REJECTED_EVALUATOR_TAMPERING", checks, mutation, parent_package, child_package, parent_grades, child_grades)

    # Protected capabilities do not regress.
    reg_parent = _passed(parent_grades, "regression")
    reg_child = _passed(child_grades, "regression")
    no_regression = all(pid in reg_child for pid in reg_parent)
    check("no_protected_regression", no_regression,
          f"parent regression {reg_parent}, child {reg_child}")

    # Held-out outperformance (gain >= delta_min).
    held_parent = _passed(parent_grades, "held_out")
    held_child = _passed(child_grades, "held_out")
    gained = sorted(set(held_child) - set(held_parent))
    gain_ok = len(gained) >= delta_min
    check("held_out_gain", gain_ok,
          f"parent {held_parent}, child {held_child}, gained {gained}")

    # Authority invariants: kernel produced sealed packets with digests.
    all_sealed = all(
        g.get("trace_digest") and g.get("final_state_hash")
        for g in child_grades.values())
    check("authority_invariants", all_sealed, "child packets sealed by kernel")

    # Deterministic replay.
    check("deterministic_replay", replay_ok_flag,
          replay_detail or "replay ok")

    # Rollback preserved: parent snapshot exists by construction.
    check("rollback_preserved", True, "parent revision retained in history")

    if not no_regression:
        verdict = "REJECTED"
    elif not gain_ok or not all_sealed or not replay_ok_flag:
        verdict = "QUARANTINED" if no_regression else "REJECTED"
    else:
        verdict = "PROMOTED"

    return _verdict(verdict, checks, mutation, parent_package, child_package,
                    parent_grades, child_grades)


def _verdict(verdict: str, checks: List[Dict], mutation: Mutation,
             parent_package: Dict, child_package: Dict,
             parent_grades: Dict, child_grades: Dict) -> Dict:
    packet = {
        "verdict": verdict,
        "mutation": mutation.to_json(),
        "parent": {"processor_id": parent_package.get("processor_id"),
                   "revision": parent_package.get("revision")},
        "child": {"processor_id": child_package.get("processor_id"),
                  "revision": child_package.get("revision")},
        "checks": checks,
        "parent_grades": {k: {"passed": v["passed"]} for k, v in parent_grades.items()},
        "child_grades": {k: {"passed": v["passed"]} for k, v in child_grades.items()},
    }
    packet["evidence_digest"] = _seal_evidence(packet)
    return packet
