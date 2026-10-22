"""rows_ct.py -- the CUBE TRAIN rows (PREREGISTRATION_CUBE_TRAIN §4.1, A-CUBE-TRAIN-1 A1-A3). Exam side, not inside HELM.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Training lines for teaching HELM's CTT to read a fact out of a teaching line. Each row is one input line and its
target: `<thing> | <slot words> | <value> | <replaces or ->` (written by HELM's own `target_string`), or `NONE`.
The worlds come from TEACH-1's generator (the same two made-up subjects); the targets come from the GENERATOR'S OWN
TRUTH (the fact it wrote), never from the exam's rule reader, so the CTT does not learn to copy the baseline.
Every word of a target is a word of its line (the copy rule); a row that would break it is dropped.

Kinds: FACT (a statement, sometimes with a short prefix or as a restatement), FIRST (a first statement that a later
correction fixes: labelled with the value it states), FIX (a correction: the new value, replacing the old), TRAP (a
statement with one decoy, labelled with the truth), SAYBACK (HELM's own say-back line of a truth reading), UNKNOWN
("I don't remember ..." -> NONE), SMALL (small talk -> NONE).
Bands are fixed (A-CUBE-TRAIN-1 A3): TRAIN worlds 2,050,000,000 + i, DEV worlds 2,051,000,000 + i.
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import os
import random
import sys
from typing import Any, Dict, List, Optional, Set

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TEACH1_PKG = os.path.join(ROOT, "docs", "working", "helm_memory_compaction_v1", "teach1", "HELM_TEACH1_20261021")
for p in (TEACH1_PKG, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import helm_cube_osc as hco  # noqa: E402  (target_string, say_back, Reading -- HELM's own format)
from teach1 import turns_t1 as T  # noqa: E402
from teach1 import worlds_t1 as W  # noqa: E402

TRAIN_BAND = 2_050_000_000
DEV_BAND = 2_051_000_000
TRAIN_ROWS, TRAIN_SAYBACK = 40_000, 6_000
DEV_ROWS, DEV_SAYBACK = 2_000, 300
TRAPS_PER_WORLD = 4
#: A-TEACH2-2 B2's discourse list (never a slot word)
DISCOURSE = {"correction", "actually", "sorry", "meant", "honestly", "also", "more", "said", "before", "earlier",
             "instead", "like", "just", "really", "think"}
SMALL_LINES = tuple(T.PRACTICE_SMALL) + ("Hold on, let me check that.", "Where was I again.", "Okay, next one.",
                                          "That reminds me of something else.")
NOT_PREFIX = "Not that it matters much, but "


def _words(text: str) -> Set[str]:
    return {w.lower().strip("'-") for w in hco._WORD_RX.findall(text or "")}


def _lower_the(text: str) -> str:
    """Lower the first letter only when the line opens with "The" (a name keeps its capital)."""
    return "t" + text[1:] if text.startswith("The ") else text


def truth_reading(fact: Dict[str, Any], line: str, value: str, replaces: Optional[str]) -> Optional[hco.Reading]:
    """A-CUBE-TRAIN-1 A2: the generator's truth for `line`, or None when the copy rule cannot hold."""
    thing = fact["unit"].lower()
    val = value.lower()
    rep = replaces.lower() if replaces else None
    in_line = _words(line)
    base = set(W.content_words(fact["statement"])) - {thing, val} - ({rep} if rep else set()) - DISCOURSE
    slot = frozenset(w for w in base if w in in_line)
    if not slot:
        return None
    month = (fact.get("month") or "").lower()
    if month and month not in in_line:
        return None
    r = hco.Reading(thing, slot, val, rep)
    target_words = {thing, val} | set(slot) | ({rep} if rep else set())
    if not target_words <= in_line:
        return None
    return r


def _trap_line(fact: Dict[str, Any], world: Dict[str, Any], rng: random.Random) -> str:
    s = fact["statement"]
    frames = ["not", "other"] + (["number"] if fact["kind"] == "count" else [])
    frame = rng.choice(frames)
    if frame == "not":
        return NOT_PREFIX + _lower_the(s)
    if frame == "number":
        decoy = rng.choice([n for n in W.NUMBERS if n != fact["value"]])
        return s[:-1] + f", up from {decoy} the month before."
    unit = rng.choice([u for u in world["names"]["units"] if u != fact["unit"]])
    month = rng.choice([m for m in W.MONTHS if m != fact.get("month")]).capitalize()
    return s[:-1] + f", while {unit} was quiet in {month}."


def world_rows(seed: int, index: int, rng: random.Random) -> List[Dict[str, Any]]:
    """All non-say-back rows of one world."""
    world = W.build_world(seed, index, W.TEMPLATES[index % 2])
    out: List[Dict[str, Any]] = []

    def add(kind: str, fact: Optional[Dict[str, Any]], line: str, value: Optional[str], replaces: Optional[str],
            truth_value: Optional[str] = None) -> None:
        if value is None:
            out.append({"kind": kind, "input": line, "target": "NONE", "world_seed": seed, "world_index": index,
                        "fact_id": fact["id"] if fact else None})
            return
        r = truth_reading(fact, line, value, replaces)
        if r is None:
            return
        out.append({"kind": kind, "input": line, "target": hco.target_string(r), "world_seed": seed,
                    "world_index": index, "fact_id": fact["id"], "truth_value": (truth_value or value).lower()})

    known = []
    for f in world["facts"]:
        if f["unknown"]:
            add("UNKNOWN", f, f["unknown_statement"], None, None)
            continue
        if f.get("fix"):
            prefix = rng.choice(T.PRACTICE_PREFIX)
            add("FIRST", f, prefix + (_lower_the(f["fix"]["first_statement"]) if prefix else f["fix"]["first_statement"]),
                f["fix"]["first_value"], None)
            add("FIX", f, f["fix"]["correction"], f["value"], f["fix"]["first_value"])
            continue
        known.append(f)
        prefix = rng.choice(T.PRACTICE_PREFIX + (T.PRACTICE_RESTATE,))
        add("FACT", f, prefix + (_lower_the(f["statement"]) if prefix else f["statement"]), f["value"], None)
    for f in rng.sample(known, min(TRAPS_PER_WORLD, len(known))):
        add("TRAP", f, _trap_line(f, world, rng), f["value"], None, truth_value=f["value"])
    for line in rng.sample(SMALL_LINES, 4):
        add("SMALL", None, line, None, None)
    return out


def build_rows(band: int, n_total: int, n_sayback: int, exclude: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """`n_total` rows from the band's worlds, `n_sayback` of them HELM's say-back lines of truth readings; deterministic."""
    rng = random.Random(f"cube-train:{band}")
    exclude = exclude or set()
    base: List[Dict[str, Any]] = []
    index = 0
    while len(base) < n_total - n_sayback:
        for row in world_rows(band, index, rng):
            if row["input"] not in exclude and len(base) < n_total - n_sayback:
                base.append(row)
        index += 1
    readable = [r for r in base if r["target"] != "NONE"]
    say: List[Dict[str, Any]] = []
    k = 0
    while len(say) < n_sayback:
        src = readable[rng.randrange(len(readable))]
        reading = hco.reading_from_ctt(src["target"], src["input"])
        line = hco.say_back(reading)
        k += 1
        if line in exclude:
            continue
        say.append({"kind": "SAYBACK", "input": line, "target": hco.target_string(reading), "world_seed": band,
                    "world_index": src["world_index"], "fact_id": src["fact_id"], "truth_value": reading.value})
    rows = base + say
    rng.shuffle(rows)
    return rows


def build_dev(train: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """DEV rows from the DEV band, never sharing an input line with TRAIN."""
    return build_rows(DEV_BAND, DEV_ROWS, DEV_SAYBACK, exclude={r["input"] for r in train})
