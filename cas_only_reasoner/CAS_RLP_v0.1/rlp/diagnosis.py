"""Fault diagnosis: locate the first failing stage from a sealed trace.

The diagnoser reads ONLY the kernel evidence packet and the expected
outcome. It never sees the intended repair - it classifies the fault
class, and the mutation proposer turns that class into candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FaultRecord:
    stage: str                  # inference | knowledge | unknown
    classification: str         # overgeneral_rule | missing_rule |
                                # wrong_conclusion | status_mismatch
    guilty_rules: List[str]
    detail: str
    problem_id: str = ""


def proposition_matches(actual: Optional[Dict], expected: Optional[Dict]) -> bool:
    if actual is None or expected is None:
        return actual == expected
    return (actual.get("pred") == expected.get("pred")
            and list(actual.get("args", [])) == list(expected.get("args", [])))


def diagnose(packet: Dict, expectation: Dict) -> Optional[FaultRecord]:
    """Compare one episode against its expectation; None means no fault."""
    problem_id = packet.get("problem_id", "")
    expected_status = expectation.get("status")
    expected_conclusion = expectation.get("conclusion")

    if packet.get("terminal_status") == expected_status and \
            proposition_matches(packet.get("conclusion"), expected_conclusion):
        return None

    actual_conclusion = packet.get("conclusion")
    proof = packet.get("proof") or {}
    rules = list(proof.get("rules_used", []))

    # The machine concluded something the expectation forbids: the rule
    # that produced it fired where it should not have.
    if expected_conclusion is None and actual_conclusion is not None:
        return FaultRecord(
            stage="inference",
            classification="overgeneral_rule",
            guilty_rules=rules,
            detail=(f"concluded {actual_conclusion} but expectation "
                    f"requires no conclusion; rules {rules or 'facts only'}"),
            problem_id=problem_id,
        )
    if expected_conclusion is not None and not proposition_matches(
            actual_conclusion, expected_conclusion):
        return FaultRecord(
            stage="inference",
            classification="wrong_conclusion",
            guilty_rules=rules,
            detail=(f"concluded {actual_conclusion}, expected "
                    f"{expected_conclusion}; rules {rules or 'facts only'}"),
            problem_id=problem_id,
        )
    if expected_status == "CONCLUDED" and actual_conclusion is None:
        return FaultRecord(
            stage="knowledge",
            classification="missing_rule",
            guilty_rules=[],
            detail=(f"no conclusion reached; expected {expected_conclusion}; "
                    "knowledge or rule missing"),
            problem_id=problem_id,
        )
    return FaultRecord(
        stage="unknown",
        classification="status_mismatch",
        guilty_rules=rules,
        detail=(f"status {packet.get('terminal_status')} != "
                f"{expected_status}"),
        problem_id=problem_id,
    )
