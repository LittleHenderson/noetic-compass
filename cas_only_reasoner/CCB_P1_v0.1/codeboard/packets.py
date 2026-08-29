"""CCB-P1: the CodeLessonPacket - typed, provenance-bearing.

The anti-authority law: a packet carrying 'verified', 'promote',
'examiner', 'tests', 'protected', or 'threshold' is refused typed -
teacher confidence is not correctness, and a proposal to touch the
evaluator is EVALUATOR CONTAMINATION, a permanent battery row."""

from __future__ import annotations

from typing import Dict, List

from .sandbox import static_gate
from .spec import SKILLS, validate_spec

FORBIDDEN_FIELDS = ("verified", "promote", "promotion", "examiner",
                    "tests", "protected", "threshold", "authority",
                    "sandbox_override", "effects_allowed")

REQUIRED_FIELDS = ("lesson_id", "skill_id", "teacher_model",
                   "teacher_revision", "explanation", "provenance")


def validate_packet(packet: Dict) -> List[str]:
    defects: List[str] = []
    if not isinstance(packet, dict):
        return ["packet is not an object"]
    for field in FORBIDDEN_FIELDS:
        if field in packet:
            defects.append(
                f"forbidden authority field {field!r} - the teacher "
                f"may not mark code verified or touch the examiner "
                f"(evaluator contamination)")
    for field in REQUIRED_FIELDS:
        if packet.get(field) in (None, ""):
            defects.append(f"missing {field!r}")
    skill_id = packet.get("skill_id")
    if skill_id not in SKILLS:
        defects.append(f"unknown skill {skill_id!r}")
        return defects
    kind = SKILLS[skill_id]["kind"]
    if kind == "algorithm":
        code = packet.get("implementation")
        if not isinstance(code, str) or not code.strip():
            defects.append("an algorithm lesson needs "
                           "'implementation' (python source)")
        else:
            defects.extend(static_gate(code))
        alternative = packet.get("alternative")
        if alternative is not None:
            if not isinstance(alternative, str):
                defects.append("'alternative' must be python source")
            else:
                defects.extend(
                    f"alternative: {d}"
                    for d in static_gate(alternative))
        bug = packet.get("common_bug")
        if not isinstance(bug, str) or not bug.strip():
            defects.append("an algorithm lesson needs 'common_bug' "
                           "(a buggy python variant)")
        else:
            defects.extend(f"common_bug: {d}"
                           for d in static_gate(bug))
    if kind in ("tracing", "testing", "repair"):
        strategy = packet.get("strategy")
        if not isinstance(strategy, str) or not strategy.strip():
            defects.append(f"a {kind} lesson needs 'strategy' "
                           f"(the method, in plain English)")
    return defects
