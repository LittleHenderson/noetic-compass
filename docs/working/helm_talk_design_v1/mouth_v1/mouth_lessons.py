"""mouth_lessons.py -- the mouth's lessons (A-TALK-4 W3-W6). Exam side, not inside HELM.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
The CTT has only ever learned to READ. These are the lessons that teach it to WRITE. Each lesson is an input (what HELM
knows or what the person said, plus the situation and a tone tag) and a line of English HELM could say. The lines are
written by AI models of three families and checked twice: first by rule (here: no name, number or month that is not in
the input; no opinion; no CAS token; one to three sentences; the situation's shape), then by two OTHER families (the
key). Template lines are capped at 10 % of the rows, so the mouth does not learn to parrot them (the owner's objection,
A-TALK-4). Synthetic only (Q1 a): the facts come from the made-up worlds of TEACH-1's generator; the person lines are
AI-written.

Situations (W1): ANSWER, SAYBACK, ASK (from a reading); SMALL, SELF, OFF, WORLD (from a person's line).
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import hashlib
import os
import random
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CUBE_TRAIN = os.path.join(ROOT, "docs", "working", "helm_cube_oscillation_v1", "cube_train")
for p in (CUBE_TRAIN, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import rows_ct as R  # noqa: E402  (puts TEACH-1's package on the path; the generator's truth reading)
import helm_cube_osc as hco  # noqa: E402
import helm_talk as ht  # noqa: E402
import helm_voice  # noqa: E402
from teach1 import worlds_t1 as W  # noqa: E402

FACT_SITUATIONS = ("ANSWER", "SAYBACK", "ASK")
LINE_SITUATIONS = ("SMALL", "SELF", "OFF", "WORLD")
SITUATIONS = FACT_SITUATIONS + LINE_SITUATIONS
FACT_BAND = R.TRAIN_BAND               # the worlds are not secret (A-CUBE-TRAIN-1 A3); fresh indices, never CUBE TRAIN's
FIRST_INDEX = 30_000
TEMPLATE_SHARE = 0.10
DEV_SHARE = 15                         # percent of inputs held out whole
MAX_WORDS = 40
NAMES = {w.lower() for w in W.PERSONS + W.PLACES}
NUMBERS = set(W.NUMBERS) | {"one", "zero", "twenty", "thirty", "hundred", "dozen", "once", "twice"}
MONTHS = set(W.MONTHS) | {"may"}
NODATA_RX = re.compile(r"\b(?:don't know|do not know|not sure|no idea|can't say|nobody has told me|haven't been told|"
                       r"no way to know|don't have that)\b", re.I)
_WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*|\d+")


def _words(text: str) -> List[str]:
    return [w.strip("'-") for w in _WORD_RX.findall(text or "")]


# ----------------------------------------------------------------------------------------------- tone (W3)
def tone(situation: str, text: str) -> Tuple[str, str]:
    """The frozen v1 tone rule (A-TALK-4 W3): register |f for small talk and for a line with a feeling or good-news
    cue, else |A; the state token is ^1 ("paying attention") for every row in v1. Mapping replies to the 40 states is
    v2 and needs a check against the canonical Noetic definitions first."""
    if situation == "SMALL" or (situation == "OFF" and (ht.STRAIN_RX.search(text or "") or ht.GOOD_RX.search(text or ""))):
        return "^1", "|f"
    return "^1", "|A"


# ----------------------------------------------------------------------------------------------- inputs (W3)
def _reading_dict(r) -> Dict[str, Any]:
    return {"thing": r.thing, "slot": sorted(r.slot), "value": r.value, "replaces": r.replaces}


def input_text(situation: str, reading: Optional[Dict[str, Any]] = None, person_line: Optional[str] = None) -> str:
    """The content side of the mouth's input, as plain words (the CTT reads it as English pieces after [M], the
    situation word and the tone tag)."""
    if reading is not None:
        t = f"{situation.lower()} {reading['thing']} {' '.join(reading['slot'])} {reading['value']}"
        return t + (f" replaces {reading['replaces']}" if reading.get("replaces") else "")
    return f"{situation.lower()} {person_line}"


def fact_inputs(n: int, first_index: int = FIRST_INDEX) -> List[Dict[str, Any]]:
    """`n` readings from fresh made-up worlds (the generator's truth), dealt in turn to ANSWER, SAYBACK and ASK; a
    corrected fact gives a reading that replaces the old value."""
    out: List[Dict[str, Any]] = []
    index = first_index
    while len(out) < n:
        world = W.build_world(FACT_BAND, index, W.TEMPLATES[index % 2])
        for f in world["facts"]:
            if f["unknown"] or len(out) >= n:
                continue
            if f.get("fix"):
                r = R.truth_reading(f, f["fix"]["correction"], f["value"], f["fix"]["first_value"])
            else:
                r = R.truth_reading(f, f["statement"], f["value"], None)
            if r is None:
                continue
            sit = FACT_SITUATIONS[len(out) % 3]
            rd = _reading_dict(r)
            out.append({"situation": sit, "reading": rd, "input_text": input_text(sit, rd), "world_index": index,
                        "fact_id": f["id"], "tone": tone(sit, ""), "input_key": f"{index}:{f['id']}:{sit}"})
        index += 1
    return out


def line_input(situation: str, person_line: str, key: str) -> Dict[str, Any]:
    return {"situation": situation, "person_line": person_line, "input_text": input_text(situation, person_line=person_line),
            "tone": tone(situation, person_line), "input_key": key}


# ----------------------------------------------------------------------------------------------- the rule check
def _input_words(inp: Dict[str, Any]) -> set:
    return {w.lower() for w in _words(inp["input_text"])}


def rule_check(inp: Dict[str, Any], line: str) -> Tuple[bool, str]:
    """W4/W5 by rule: words, never facts. True only when every check holds."""
    sit = inp["situation"]
    text = (line or "").strip()
    if not text:
        return False, "empty"
    words = _words(text)
    if len(words) > MAX_WORDS:
        return False, "too long"
    if helm_voice.cas_tokens(text):
        return False, "CAS token"
    if not 1 <= helm_voice.sentence_count(text) <= 3:
        return False, "sentences"
    if ht.OPINION_RX.search(text):
        return False, "opinion"
    have = _input_words(inp)
    for w in words:
        lw = w.lower()
        if lw.isdigit() and lw not in have:
            return False, f"digit {w} not in input"
        if (lw in NAMES or lw in NUMBERS or lw in MONTHS) and lw not in have:
            return False, f"{w} not in input"
    # a capitalised word after a sentence's first word that is not in the input is an invented name
    for sent in re.split(r"(?<=[.!?])\s+", text):
        toks = _words(sent)
        for w in toks[1:]:
            if w[:1].isupper() and w != "I" and w.lower() not in have and w.lower() not in ("i'm", "i'll", "i've", "i'd"):
                return False, f"name {w} not in input"
    for m in ht.RECIPE_SPEAK_RX.finditer(text):
        if m.group(0).lower() not in have:
            return False, "recipe-speak"
    q = text.count("?")
    if sit in FACT_SITUATIONS:
        r = inp["reading"]
        low = {w.lower() for w in words}
        if r["value"] not in low or r["thing"] not in low:
            return False, "the reading's value or thing missing"
        if sit == "ASK" and (q != 1 or not text.endswith("?")):
            return False, "ASK must be one question at the end"
        if sit in ("ANSWER", "SAYBACK") and q:
            return False, "no question in an answer"
    elif sit == "OFF":
        if q != 1:
            return False, "OFF needs exactly one question"
    elif sit == "WORLD":
        if not NODATA_RX.search(text):
            return False, "WORLD must say it does not know"
    return True, ""


# ----------------------------------------------------------------------------------------------- rows
def cap_templates(rows: List[Dict[str, Any]], share: float = TEMPLATE_SHARE, seed: str = "mouth-cap") -> List[Dict[str, Any]]:
    llm = [r for r in rows if r.get("source") != "TEMPLATE"]
    tmpl = [r for r in rows if r.get("source") == "TEMPLATE"]
    keep = int(share * len(llm) / (1.0 - share))
    random.Random(seed).shuffle(tmpl)
    return llm + tmpl[:keep]


def split(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Hold inputs out whole: an input's every row goes to DEV when sha256(input_key) mod 100 < DEV_SHARE."""
    def dev(r):
        return int(hashlib.sha256(r["input_key"].encode("utf-8")).hexdigest(), 16) % 100 < DEV_SHARE
    return [r for r in rows if not dev(r)], [r for r in rows if dev(r)]


def template_line(inp: Dict[str, Any]) -> Optional[str]:
    """Today's template for the situation (A-TALK-2/-3, helm_cube_osc) -- used only as a capped share of rows and as the
    fallback when the guard rejects the mouth."""
    sit = inp["situation"]
    if sit in FACT_SITUATIONS:
        r = inp["reading"]
        rd = hco.Reading(r["thing"], frozenset(r["slot"]), r["value"], r.get("replaces"))
        if sit == "SAYBACK":
            return hco.say_back(rd)
        target, kind = hco._target_and_kind(rd)
        phrase = f"{r['thing'].capitalize()}, {kind}, {(target or '').capitalize()}"
        return f"You told me: {phrase}: {r['value']}." if sit == "ANSWER" else f"You told me {phrase}: {r['value']}. {ht.ASK_TAIL}"
    line = inp["person_line"]
    if sit == "SMALL":
        return ht.SMALL_REPLIES[ht.small_kind(line) or "pause"]
    if sit == "SELF":
        return ht.self_reply(line)
    if sit == "WORLD":
        return ht.WORLD_REPLY
    return ht.off_react(line) + " " + ht.off_question(line)
