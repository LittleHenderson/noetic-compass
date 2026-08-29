"""The MathLessonPacket schema: BILINGUAL lessons.

The FORMAL channel is authoritative (infix text parsed into CAS-Math
IR and checked exactly); the language channel teaches accessibility
and is never a validity source. Typed defects, never silent coercion.
The anti-authority law lives here too: a packet carrying 'verified',
'promote', or any other authority field is refused typed.
"""

from __future__ import annotations

from typing import Dict, List

from .graph import SKILLS
from .mathir import MathParseError, parse_equation, parse_expr

FORBIDDEN_FIELDS = ("verified", "promote", "promotion", "checker",
                    "protected", "threshold", "authority",
                    "memory_write")

REQUIRED_FIELDS = ("lesson_id", "skill_id", "teacher_model",
                   "teacher_revision", "explanation",
                   "worked_examples", "common_mistake", "provenance")


def validate_packet(packet: Dict) -> List[str]:
    defects: List[str] = []
    if not isinstance(packet, dict):
        return ["packet is not an object"]
    for field in FORBIDDEN_FIELDS:
        if field in packet:
            defects.append(
                f"forbidden authority field {field!r} - the teacher "
                f"may not mark content verified, touch the checker, "
                f"or move the promotion threshold")
    for field in REQUIRED_FIELDS:
        if packet.get(field) in (None, "", []):
            defects.append(f"missing {field!r}")
    skill_id = packet.get("skill_id")
    if skill_id not in SKILLS:
        defects.append(f"unknown skill {skill_id!r}")
        return defects
    kind = SKILLS[skill_id]["kind"]

    examples = packet.get("worked_examples") or []
    if not isinstance(examples, list) or len(examples) < 2:
        defects.append("worked_examples must be a list of at least "
                       "2 items")
    elif kind == "equation_solving":
        # an equation lesson's examples are CONDITIONAL equations
        # WITH their solutions - verified later by exact substitution
        # (live finding: the teacher rightly offered '3*(x+2)=15',
        # true only at x=3; demanding identities was OUR defect)
        for example in examples:
            if not isinstance(example, dict) or not all(
                    k in example for k in ("equation", "variable",
                                           "solution")):
                defects.append(f"example {example!r} must be an "
                               f"object with equation, variable, "
                               f"solution")
                continue
            try:
                parse_equation(example["equation"])
                parse_expr(str(example["solution"]))
            except MathParseError as exc:
                defects.append(f"example {example!r} does not parse: "
                               f"{exc}")
    else:
        for example in examples:
            if not isinstance(example, str):
                defects.append(f"example {example!r} is not a string")
                continue
            try:
                parse_equation(example)
            except MathParseError as exc:
                defects.append(f"example {example!r} does not parse: "
                               f"{exc}")

    mistake = packet.get("common_mistake")
    if isinstance(mistake, str):
        try:
            parse_equation(mistake)
        except MathParseError as exc:
            defects.append(f"common_mistake {mistake!r} does not "
                           f"parse: {exc}")
    elif mistake is not None:
        defects.append("common_mistake must be an equation string")

    if kind == "rewrite_rule":
        rule = packet.get("formal_rule")
        if not isinstance(rule, str):
            defects.append("a rewrite_rule lesson needs "
                           "'formal_rule' (an identity over "
                           "metavariables, e.g. "
                           "'a * (b + c) = a * b + a * c')")
        else:
            try:
                parse_equation(rule)
            except MathParseError as exc:
                defects.append(f"formal_rule does not parse: {exc}")
    if kind == "equation_solving":
        method = packet.get("method")
        allowed = ("expand", "collect", "isolate")
        if not isinstance(method, list) or not method \
                or any(step not in allowed for step in method):
            defects.append(f"an equation_solving lesson needs "
                           f"'method': an ordered list from "
                           f"{allowed}")
    return defects
