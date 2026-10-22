"""cube_task/read.py -- the frozen reader of the CUBE TRAIN result (pre-code §6–§9). Stdlib only.

score_copy: per copy, how many DEV rows it read right (the filled reading equals the truth), wrong (a different
reading), none (no reading: NONE where a fact was true, an unfinished or malformed answer), and invented (a filled word
that is not a word of the line -- impossible with pointers, still counted). A truth of NONE answered NONE is right.
unanimous: the three copies' answers when all three are the same complete answer, else None.
status_word: INCONCLUSIVE (an instrument row false) > TRAIN_NOT_READY (a gate false) > TRAIN_READY.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from . import target

WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _words(text: str) -> set:
    return {w.lower().strip("'-") for w in WORD_RX.findall(text or "")}


def score_copy(rows: Sequence[Dict[str, Any]], outputs: Sequence[Optional[List[str]]]) -> Dict[str, int]:
    c = {"rows": len(rows), "right": 0, "wrong": 0, "none": 0, "invented": 0, "fact_rows": 0, "fact_right": 0,
         "fact_wrong": 0, "trap_rows": 0, "trap_wrong": 0}
    for r, out in zip(rows, outputs):
        filled = target.fill(out, r["text"]) if out else None
        is_fact = r["truth"] != target.NONE
        c["fact_rows"] += is_fact
        c["trap_rows"] += r.get("kind") == "TRAP"
        if filled is not None and filled != target.NONE:
            words = set(filled.replace("|", " ").split()) - {target.DASH}
            if not words <= _words(r["text"]):
                c["invented"] += 1
        if filled is None or (filled == target.NONE and is_fact):
            c["none"] += 1
        elif filled == r["truth"]:
            c["right"] += 1
            c["fact_right"] += is_fact
        else:
            c["wrong"] += 1
            c["fact_wrong"] += is_fact
            c["trap_wrong"] += r.get("kind") == "TRAP"
    return c


def unanimous(answers: Sequence[Optional[List[str]]]) -> Optional[List[str]]:
    if not answers or any(a is None for a in answers):
        return None
    first = list(answers[0])
    return first if all(list(a) == first for a in answers[1:]) else None


def status_word(reading: Dict[str, Any]) -> str:
    if not all(reading["instrument"].values()):
        return "INCONCLUSIVE"
    if not all(reading["gates"].values()):
        return "TRAIN_NOT_READY"
    return "TRAIN_READY"


def gates(vote_sdg: Dict[str, int], vote_llm: Dict[str, int], copies: Dict[str, Dict[str, int]],
          keep_old: Dict[str, Dict[str, float]], g: Dict[str, float]) -> Dict[str, bool]:
    """The four frozen gates from the unanimous-vote counts on DEV-SDG and DEV-LLM, the per-copy counts, and the
    before/after exact-match rates on the kept CAS validation rows."""
    def rate(n, d):
        return n / d if d else 0.0
    return {
        "G-INVENT": all(c["invented"] == 0 for c in copies.values()),
        "G-CONFIDENT-WRONG": (rate(vote_sdg["wrong"], vote_sdg["rows"]) <= g["confident_wrong_sdg_max"]
                              and rate(vote_llm["wrong"], vote_llm["rows"]) <= g["confident_wrong_llm_max"]
                              and rate(vote_sdg["trap_wrong"] + vote_llm["trap_wrong"],
                                       vote_sdg["trap_rows"] + vote_llm["trap_rows"]) <= g["confident_wrong_trap_max"]),
        "G-EXERCISED": (rate(vote_sdg["fact_right"], vote_sdg["fact_rows"]) >= g["exercised_sdg_min"]
                        and rate(vote_llm["fact_right"], vote_llm["fact_rows"]) >= g["exercised_llm_min"]),
        "G-KEEP-OLD": all(v["before"] - v["after"] <= g["keep_old_max_drop"] for v in keep_old.values()),
    }
