"""mouth_task/roundtrip.py -- is the ear's read-back of a mouth line the same fact? (A-TALK-6 G5, A-TALK-7 H3)

The ear reads a fact line back as "thing | slot words | value | old value or -". The read-back counts as the same fact
when thing, value and the months among the slot words match the reading the mouth was given. For ANSWER and SAYBACK
the old value (`replaces`) must match too; an ASK question asks whether the new value still holds and need not repeat
the old one, so for ASK the old value is not compared (the owner's word, Q2). Slot wording may vary. Standard library.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .names import MONTHS


def same_fact(reading_str: Optional[str], reading: Dict[str, Any], situation: str) -> bool:
    if not reading_str or reading_str == "NONE":
        return False
    parts = [p.strip() for p in reading_str.split("|")]
    if len(parts) != 4:
        return False
    thing, slot, value, rep = parts
    months = {w for w in reading["slot"] if w in MONTHS}
    got_months = {w for w in slot.split() if w in MONTHS}
    if thing != reading["thing"] or value != reading["value"] or got_months != months:
        return False
    if situation == "ASK":
        return True
    return (rep if rep != "-" else None) == reading.get("replaces")
