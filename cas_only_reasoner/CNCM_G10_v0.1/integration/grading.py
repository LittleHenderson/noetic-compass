"""The task-difficulty grading for the multi-domain long-horizon
episode - every axis DISCLOSED with its justification, the raw band
disclosed next to the floor, and the novel-research caveat verbatim.

The D10 grade rests on the NOVEL-RESEARCH floor (the discovery leg:
machine-generated, machine-proved theorems absent from every fixture),
not on the DI band (which is honestly D8). Anyone quoting the D10 must
quote the caveat with it.
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

NOVEL_RESEARCH_CAVEAT = (
    "the novel-research floor rests on the discovery leg: theorems "
    "novel TO THIS MACHINE (absent from every fixture, "
    "machine-generated, proved by the trusted checker) and trivial to "
    "human mathematics - discovery-by-exhaustive-search at v0.1 scale. "
    "The DI band without the floor is D8 and is disclosed alongside.")


def grading() -> Dict:
    graded = grade_task(AXES, novel_research=True)
    graded["caveat"] = NOVEL_RESEARCH_CAVEAT
    return graded
