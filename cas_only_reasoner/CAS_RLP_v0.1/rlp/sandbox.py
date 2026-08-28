"""Sandbox evaluation: run descendants through the UNCHANGED kernel.

The kernel is imported from CAS_RRK_v0.1 as a library. RLP never
modifies it; it composes new content and asks the same oracle to judge.
"""

from __future__ import annotations

import copy
import os
import sys
from typing import Dict, List, Tuple

_KERNEL_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "CAS_RRK_v0.1"))
if _KERNEL_ROOT not in sys.path:
    sys.path.insert(0, _KERNEL_ROOT)

from kernel.kernel import CAS_RRK, replay  # noqa: E402


def build_problem(task: Dict, parameters: Dict) -> Dict:
    problem = copy.deepcopy(task)
    problem.setdefault("available_actions", {})
    if parameters:
        problem["constitution"] = dict(parameters)
    return problem


def run_task(task: Dict, parameters: Dict) -> Dict:
    problem = build_problem(task, parameters)
    constitution = dict(parameters) if parameters else None
    return CAS_RRK(problem, constitution=constitution,
                   run_id="rlp_sandbox", seed=0).run()


def run_suite(package: Dict) -> Tuple[Dict, Dict]:
    """Run every task; return (results, expectations_used)."""
    parameters = package.get("parameters", {})
    expectations = package.get("expectations", {})
    results: Dict[str, Dict] = {}
    for group in ("regression", "held_out"):
        for task in package.get("tasks", {}).get(group, []):
            results[task["problem_id"]] = run_task(task, parameters)
    return results, expectations


def grade(package: Dict, results: Dict) -> Dict:
    """Compare results against expectations, per group."""
    expectations = package.get("expectations", {})
    grades: Dict[str, Dict] = {}
    for problem_id, packet in results.items():
        exp = expectations.get(problem_id, {})
        status_ok = packet.get("terminal_status") == exp.get("status")
        concl = packet.get("conclusion")
        exp_concl = exp.get("conclusion")
        concl_ok = (concl == exp_concl)
        grades[problem_id] = {
            "group": _group_of(package, problem_id),
            "passed": status_ok and concl_ok,
            "expected": exp,
            "actual_status": packet.get("terminal_status"),
            "actual_conclusion": concl,
            "trace_digest": packet.get("trace_digest"),
            "final_state_hash": packet.get("final_state_hash"),
        }
    return grades


def _group_of(package: Dict, problem_id: str) -> str:
    for group in ("regression", "held_out"):
        for task in package.get("tasks", {}).get(group, []):
            if task.get("problem_id") == problem_id:
                return group
    return "unknown"


def replay_ok(package: Dict, results: Dict) -> Tuple[bool, str]:
    """Acceptance-law check: at least one child task replays exactly."""
    parameters = package.get("parameters", {})
    for task in package.get("tasks", {}).get("held_out", []) or \
            package.get("tasks", {}).get("regression", []):
        problem = build_problem(task, parameters)
        packet = run_task(task, parameters)
        ok, mismatches, _ = replay(problem, packet["trace"],
                                   "rlp_sandbox", 0)
        if not ok:
            return False, mismatches[0] if mismatches else "replay failed"
        return True, ""
    return True, ""
