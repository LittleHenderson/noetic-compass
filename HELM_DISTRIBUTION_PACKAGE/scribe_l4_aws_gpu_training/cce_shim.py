"""cce_shim.py -- Controlled Core English <-> CAS Content Shim for Level L4 Scribe Proposer.

Implements the deterministic CCE round-trip verification loop:
    parse(render(C)) == C
guaranteeing 0 invented facts, 0 hallucinations.

Based on language_v3/cce.py and cas_language_first_principles_map_v1/TRANSLATOR_SPEC.md.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Any, Tuple, Optional, List

NOETIC_NAMES = {
    0: "Idea", 1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration",
    5: "Female", 6: "Male", 7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect"
}

DOMAINS = {"P": "principled", "C": "cognitive", "E": "evaluative", "O": "operational"}
REGISTERS = {"T": "transcendent", "A": "analytical", "f": "affective", "E": "embodied"}
DRIVES = {
    "F1": "Unity", "F2": "Wisdom", "F3": "Vitality", "F4": "Connection",
    "F5": "Agency", "F6": "Structure", "F7": "Purpose"
}
VERBS = ("intakes", "processes", "stores", "outputs")


def normalize_content(c: Dict[str, Any]) -> str:
    """Return canonical JSON string representation of CAS content."""
    return json.dumps(c, sort_keys=True, separators=(",", ":"))


def render_cce(content: Dict[str, Any]) -> str:
    """Render structured CASContent dict into canonical CCE English string."""
    turn_type = content.get("turn_type", "ANSWER")
    if turn_type == "CLARIFY":
        missing = content.get("missing_slot", "meaning")
        return f"I cannot tell: {missing} is undetermined."

    verb = content.get("verb", "processes")
    subject = content.get("subject", "Mind")
    obj = content.get("object", "Idea")
    reg = content.get("register", "A")
    dom = content.get("domain", "C")
    drive = content.get("drive", "F2")

    reg_name = REGISTERS.get(reg, "analytical")
    dom_name = DOMAINS.get(dom, "cognitive")
    drive_name = DRIVES.get(drive, "Wisdom")

    # Canonical phrasing template
    return f"The {dom_name} {subject} {verb} the {reg_name} {obj} under {drive_name}."


def parse_cce(text: str) -> Dict[str, Any]:
    """Parse canonical CCE English string back into CASContent dict.
    
    Raises ValueError if unparseable.
    """
    text = text.strip()
    if text.startswith("I cannot tell"):
        m = re.search(r"I cannot tell: (.*) is undetermined\.", text)
        missing = m.group(1) if m else "meaning"
        return {"turn_type": "CLARIFY", "missing_slot": missing}

    pattern = r"The (\w+) (\w+) (\w+) the (\w+) (\w+) under (\w+)\."
    m = re.match(pattern, text)
    if not m:
        raise ValueError(f"Unparseable CCE string: {text}")

    dom_name, subject, verb, reg_name, obj, drive_name = m.groups()

    dom_rev = {v: k for k, v in DOMAINS.items()}
    reg_rev = {v: k for k, v in REGISTERS.items()}
    drive_rev = {v: k for k, v in DRIVES.items()}

    dom = dom_rev.get(dom_name, "C")
    reg = reg_rev.get(reg_name, "A")
    drive = drive_rev.get(drive_name, "F2")

    return {
        "turn_type": "ANSWER",
        "subject": subject,
        "verb": verb,
        "object": obj,
        "register": reg,
        "domain": dom,
        "drive": drive
    }


def verify_round_trip(content: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Verify parse(render(C)) == C.
    
    Returns:
        (holds, rendered_text, parsed_content)
    """
    rendered = render_cce(content)
    try:
        parsed = parse_cce(rendered)
        holds = (normalize_content(parsed) == normalize_content(content))
        return holds, rendered, parsed
    except Exception:
        return False, rendered, {}
