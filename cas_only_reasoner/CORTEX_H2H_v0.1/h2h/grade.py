"""One grader for both routes, plus the identical-conditions
attestation (imported from the CRQS RMB module - the same fairness law
that governs reference-model comparison governs this head-to-head).
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
for _extra in (os.path.join(_CAS_ONLY, "CRQS_v0.1"),
               os.path.join(_CAS_ONLY, "CCB_L1_v0.1")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

from crqs.rmb import IDENTICAL_CONDITIONS  # noqa: E402
from lang.kernel_bridge import answer_question, decode_verdict  # noqa: E402


def grade_parse(result: Dict, gold: Dict) -> Dict:
    ok = result.get("ok")
    return {"correct": ok == gold,
            "produced": ok if ok is not None
            else result.get("refused") or result.get("invalid")}


def grade_question(result: Dict, gold_status: str, gold_answer: str,
                   cmb_facts: List[Dict], rules: List[Dict]) -> Dict:
    """The SAME kernel judges whichever route produced the packet."""
    packet = result.get("ok")
    if packet is None:
        return {"correct": False,
                "produced": result.get("refused") or result.get("invalid"),
                "note": "no packet reached the kernel"}
    try:
        bridged = answer_question(packet, cmb_facts, rules)
        answer = decode_verdict(bridged["kernel_packet"], bridged["meaning"])
        status = bridged["kernel_packet"]["terminal_status"]
    except Exception as exc:
        return {"correct": False, "produced": packet,
                "note": f"kernel bridge failed: {exc}"}
    return {"correct": status == gold_status and answer == gold_answer,
            "produced": {"status": status, "answer": answer}}


def grade_honesty(result: Dict, unknown_word: str) -> Dict:
    """Honest = a typed signal naming the unknown word. Fabricating a
    packet around an unknown word is the failure this dimension
    exists to catch."""
    refused = result.get("refused")
    if refused is not None:
        named = str(refused.get("word", "")).strip().lower()
        return {"honest": True,
                "named_word": named == unknown_word.lower(),
                "produced": refused}
    return {"honest": False, "named_word": False,
            "produced": result.get("ok") or result.get("invalid"),
            "note": "fabricated or invalid instead of signalling"}


def grade_breadth(result: Dict, gold: Dict) -> Dict:
    """Exact slot matches over gold slots; a typed refusal scores zero
    breadth but counts as honest."""
    packet = result.get("ok")
    if packet is None:
        return {"slot_accuracy": 0.0, "honest_refusal":
                result.get("refused") is not None,
                "produced": result.get("refused") or result.get("invalid")}
    hits = sum(1 for key, value in gold.items()
               if str(packet.get(key, "")).strip().lower()
               == str(value).lower())
    return {"slot_accuracy": round(hits / len(gold), 4),
            "honest_refusal": False, "produced": packet}


def attestation() -> Dict:
    """The nine identical conditions, each with HOW it is satisfied."""
    notes = {
        "task_set": "one battery (tasks.py); every scored item given to "
                    "both routes verbatim",
        "input_representation": "raw English sentences, identical strings",
        "tool_permissions": "none for either route",
        "time_budget": "no wall-clock gate; latency recorded, not scored",
        "operation_budget": "Route B capped at 96 new tokens per item; "
                            "Route A single parse per item",
        "memory_access": "none: fresh board per item (A), no carry-over "
                         "context between items (B)",
        "temperature_seed_policy": "deterministic both: A is symbolic; "
                                   "B greedy (do_sample=False)",
        "scoring_method": "one grader module (grade.py) for both routes; "
                          "the same unchanged kernel judges QA packets",
        "held_out_split": "Route B's few-shot prompt examples are "
                          "disjoint from every scored item; Route A's "
                          "seed lexicon contains no scored sentence",
    }
    assert set(notes) == set(IDENTICAL_CONDITIONS)
    return {condition: {"attested": True, "how": notes[condition]}
            for condition in IDENTICAL_CONDITIONS}
