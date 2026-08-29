"""The task-difficulty grading for the multi-domain long-horizon
episode - every axis DISCLOSED with its justification.

AUDIT RECORD (2026-08-28, adversarial, REFUTED): the v1 grading
claimed the D10 novel-research floor via the discovery leg. The audit
found the flagship theorem was a disguised input (both sides
hand-authored into the space; the underlying law taught to the machine
as an executable axiom the novelty gate never read) and that CRQS
section 4 reserves the floor for research WITH NO KNOWN ANSWER. The
floor claim is WITHDRAWN. The honest grade is the DI band: D8.
"""

from __future__ import annotations

import os
import sys
from typing import Dict

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_CRQS = os.path.join(_CAS_ONLY, "CRQS_v0.1")
if _CRQS not in sys.path:
    sys.path.insert(0, _CRQS)

from crqs.difficulty import grade_task  # noqa: E402

AXES: Dict[str, int] = {
    "depth": 4,        # multi-board chains: parse->kernel->tool->proof;
                       # enumerate->test->prove
    "branching": 2,    # kernel alternatives; no 3-candidate segment here
    "memory": 4,       # durable store across REAL process boundaries,
                       # tamper-evident, plus strategy memory
    "recursion": 2,    # subgoal structure; no deep RPM chain here
    "novelty": 3,      # machine-novel theorems; unseen composition
    "uncertainty": 3,  # typed NEEDS_INFORMATION, blocked goals,
                       # honest CANNOT routing
    "learning": 3,     # strategy-driven budgeted repair, structural
                       # held-out fixture
    "environment": 3,  # tool loop with typed fault machinery
    "adversarial": 2,  # tamper-refusal legs; modest within-episode
}

WITHDRAWN_FLOOR_RECORD = (
    "the v1 D10 novel-research floor claim was REFUTED by adversarial "
    "audit (2026-08-28): the discovery leg is verified identity search "
    "over a partly hand-authored space, with the flagship identity a "
    "one-step instance of a taught axiom - not research with no known "
    "answer (CRQS section 4). The floor is WITHDRAWN; the grade is the "
    "DI band, D8. The negative stays on the record.")


def grading() -> Dict:
    graded = grade_task(AXES, novel_research=False)
    graded["caveat"] = WITHDRAWN_FLOOR_RECORD
    return graded
