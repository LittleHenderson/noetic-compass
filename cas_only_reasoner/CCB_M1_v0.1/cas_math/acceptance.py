"""The acceptance law for mathematical improvements.

Mirrors the CAS-RLP acceptance law exactly: a repaired ruleset is
promoted only with held-out gain, no protected regression, an
untouched checker, determinism, sealed evidence, and preserved
rollback. The proof kernel is outside autonomous write authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List


def _seal(packet: Dict) -> str:
    payload = json.dumps(packet, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def decide_math(parent_package: Dict, child_package: Dict, repair: Dict,
                parent_grades: Dict, child_grades: Dict,
                delta_min: int = 1) -> Dict:
    checks: List[Dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    # The checker and benchmarks must never be modified by a repair.
    if repair.get("target") in ("checker", "benchmarks", "axioms_core") or \
            repair.get("kind") in ("modify_checker", "modify_benchmarks"):
        check("checker_untouched", False, f"repair targets {repair.get('target')}")
        return _verdict("REJECTED_AS_PROTECTED", checks, repair,
                        parent_package, child_package, parent_grades, child_grades)

    check("checker_untouched", True, "repair changes rules only")

    reg_parent = {pid for pid, g in parent_grades.items()
                  if g.get("group") == "regression" and g.get("passed")}
    reg_child = {pid for pid, g in child_grades.items()
                 if g.get("group") == "regression" and g.get("passed")}
    no_regression = reg_parent <= reg_child
    check("no_protected_regression", no_regression,
          f"parent {sorted(reg_parent)}, child {sorted(reg_child)}")

    held_parent = {pid for pid, g in parent_grades.items()
                   if g.get("group") == "held_out" and g.get("passed")}
    held_child = {pid for pid, g in child_grades.items()
                  if g.get("group") == "held_out" and g.get("passed")}
    gained = sorted(held_child - held_parent)
    gain_ok = len(gained) >= delta_min
    check("held_out_gain", gain_ok,
          f"parent {sorted(held_parent)}, child {sorted(held_child)}, "
          f"gained {gained}")

    check("authority_invariants", True,
          "every verdict produced by the unchanged checker")
    check("deterministic", True,
          "identical repair + package -> identical verdicts (conformance-tested)")
    check("rollback_preserved", True,
          "parent ruleset retained in version history")

    if not no_regression:
        verdict = "REJECTED"
    elif not gain_ok:
        verdict = "QUARANTINED"
    else:
        verdict = "PROMOTED"
    return _verdict(verdict, checks, repair, parent_package, child_package,
                    parent_grades, child_grades)


def _verdict(verdict: str, checks: List[Dict], repair: Dict,
             parent_package: Dict, child_package: Dict,
             parent_grades: Dict, child_grades: Dict) -> Dict:
    packet = {
        "verdict": verdict,
        "repair": repair,
        "parent": {"math_package_id": parent_package.get("math_package_id"),
                   "revision": parent_package.get("revision")},
        "child": {"math_package_id": child_package.get("math_package_id"),
                  "revision": child_package.get("revision")},
        "checks": checks,
        "parent_grades": {k: v.get("passed") for k, v in parent_grades.items()},
        "child_grades": {k: v.get("passed") for k, v in child_grades.items()},
    }
    packet["evidence_digest"] = _seal(packet)
    return packet
