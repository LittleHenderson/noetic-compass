"""mouth_task/ear_lessons.py -- the ear learns the mouth's own sentences (A-TALK-7 H2, the owner's Q1 a).

A checked fact line the mouth was taught ("Carrow had five colonies in September.") becomes an ear lesson in the ear's
own [B] form: the truth "thing | slot words found in the line | value | old value or -" and its pointer target
(cube_task.target.encode_target). The slot words are only those the line itself contains, because a natural sentence
need not repeat every slot word. A line without the thing or the value gives no lesson. Standard library.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from cube_task import target

WORD_RX = re.compile(r"[a-z]+|\d+")


def ear_row(line: str, reading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    have = set(WORD_RX.findall(line.lower()))
    thing, value, rep = reading["thing"], reading["value"], reading.get("replaces")
    if thing not in have or value not in have:
        return None
    slot = [w for w in reading["slot"] if w in have]
    if not slot:
        return None
    truth = "%s | %s | %s | %s" % (thing, " ".join(slot), value, rep if rep and rep in have else "-")
    tgt = target.encode_target(line, truth)
    if tgt is None:
        return None
    return {"direction": "B", "family": "mouth", "kind": "FACT", "stratum": "EAR_M", "text": line, "truth": truth,
            "target": tgt}
