"""The grounding rail: English meaning -> kernel reasoning -> English.

CCB-L1 calls the UNCHANGED CAS-RRK kernel with a typed problem packet
built from the parsed meaning and the semantic CMB facts. The kernel's
typed verdict is decoded back into English. This is the only crossing
between language and reasoning, and it flows one way.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

_KERNEL_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "CAS_RRK_v0.1"))
if _KERNEL_ROOT not in sys.path:
    sys.path.insert(0, _KERNEL_ROOT)

from kernel.kernel import CAS_RRK  # noqa: E402


def answer_question(meaning: Dict, facts: List[Dict],
                    rules: List[Dict]) -> Dict:
    """Run a parsed question through the kernel and decode the verdict."""
    if meaning.get("pred") != "question":
        raise ValueError("answer_question expects a question meaning")
    inner = meaning["args"][0]
    problem = {
        "problem_id": "l1_grounding",
        "description": "English-grounded question answered by the kernel",
        "propositions": list(facts),
        "rules": list(rules),
        "goal": {
            "goal_id": "g_l1", "parent_goal_id": None, "kind": "question",
            "desired_outcome": inner,
            "requirements": {"knowledge": [], "capability": []},
            "status": "ACTIVE",
        },
        "alternatives": [inner],
    }
    packet = CAS_RRK(problem, run_id="ccb_l1", seed=0).run()
    return {"kernel_packet": packet, "meaning": inner}


def decode_verdict(kernel_packet: Dict, inner: Dict) -> str:
    status = kernel_packet.get("terminal_status")
    if status == "CONCLUDED" and kernel_packet.get("conclusion"):
        return f"yes, the {inner['args'][0]} is {inner['args'][1]}."
    if status == "NEEDS_INFORMATION":
        return f"i do not know whether the {inner['args'][0]} is " \
               f"{inner['args'][1]}."
    if status == "CONFLICT_UNRESOLVED":
        return "the facts conflict; i cannot answer."
    return f"the machine halted with {status}."
