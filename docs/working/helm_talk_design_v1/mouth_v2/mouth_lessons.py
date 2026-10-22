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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "package_source"))
from mouth_task import check as MCHECK  # noqa: E402

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
OWN_NAMES = {"helm"}                   # HELM's own name is not a fact about the world (a SELF reply may say it)

# v2 (A-TALK-7 H4): the owner's styles, reading levels and professions; style words ride outside the input
STYLES = ("plain", "warm", "formal", "casual", "barbershop", "intimate", "curious", "jovial", "storyteller", "professional")
WARM_STYLES = ("warm", "intimate", "jovial", "barbershop")
LEVELS = ("grade5", "grade10", "college")
PROFESSIONS = ("nurse", "electrician", "plumber", "carpenter", "teacher", "lawyer", "accountant", "software developer",
               "truck driver", "farmer", "mechanic", "barber", "firefighter", "pilot", "pharmacist", "librarian", "architect",
               "musician", "photographer", "journalist", "real-estate agent", "construction worker", "dentist",
               "veterinarian", "social worker", "graphic designer", "lab scientist", "coach", "retail cashier", "hairstylist")
WORLD_NOUNS = ("yard", "line", "buses", "colonies", "queens", "depot", "honey", "market")   # the generator's own nouns
STORY_MAX_WORDS = 60


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


def tone_v2(situation: str, style: str, text: str = "") -> Tuple[str, str]:
    """A-TALK-7 H4: register |f for the warm styles and small talk, |A otherwise; state ^1 as in v1."""
    if situation == "SMALL" or style in WARM_STYLES:
        return "^1", "|f"
    return "^1", "|A"


def styled(x: Dict[str, Any], style: str, level: str, profession: Optional[str] = None,
           form: str = "line") -> Dict[str, Any]:
    """An input with its style part (A-TALK-7 H4): style and level reach the mouth's source; profession and form
    only guide the writers."""
    return dict(x, style=[style, level], profession=profession, form=form, tone=list(tone_v2(x["situation"], style)))


def word_forms(w: str) -> set:
    """A-TALK-9 J1: a word and its regular forms (+s, +es, +ed, +d, +ing, +er, +ly; a final "e" dropped before +ing)."""
    out = {w, w + "s", w + "es", w + "ed", w + "ing", w + "er", w + "ly", w + "est"}
    if w.endswith("e"):
        out |= {w + "d", w[:-1] + "ing", w + "r", w + "st", w[:-1] + "y"}
    if len(w) >= 3 and w[-1] not in "aeiouwxy" and w[-2] in "aeiou" and w[-3] not in "aeiou":
        d = w + w[-1]                                    # A-TALK-10 K1: stop -> stopped, stopping
        out |= {d + "ed", d + "ing", d + "er", d + "est"}
    if w.endswith("y") and len(w) >= 3 and w[-2] not in "aeiou":
        out |= {w[:-1] + "ies", w[:-1] + "ied", w[:-1] + "ier", w[:-1] + "iest", w[:-1] + "ily"}
    return out


CONTRACTION_PARTS = ("doesn", "didn", "isn", "wasn", "aren", "weren", "hasn", "haven", "hadn", "couldn", "wouldn",
                     "shouldn", "won", "can", "t", "s", "re", "ve", "ll", "d", "m")      # A-TALK-9 J1, fixed list


def lesson_templates_ok(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A-TALK-9 J2: the off-topic template can build broken English, so its lines are not lessons (fallback only)."""
    return [r for r in rows if not (r.get("source") == "TEMPLATE" and r["situation"] == "OFF")]


def function_words(rows: List[Dict[str, Any]], min_seen: int = 2, vocab: Optional[List[str]] = None) -> List[str]:
    """A-TALK-7 H1 F1 + A-TALK-9 J1: every word seen in >= min_seen checked LLM-written lessons (outside the row's own
    input), plus the vetted vocabulary lists and their regular forms; minus fact words (names, numbers, months) and the
    world's own nouns. Nothing else is removed."""
    seen: Dict[str, int] = {}
    banned = NAMES | NUMBERS | MONTHS | set(WORLD_NOUNS)
    extra = set()
    for v in vocab or []:
        extra |= word_forms(v.lower())
    for r in rows:
        if r.get("source") != "LLM_WRITTEN":
            continue
        have = {w.lower() for w in _words(r["input_text"])}
        for w in {w.lower() for w in re.findall(r"[A-Za-z]+", r["target"])}:
            if w not in have:
                seen[w] = seen.get(w, 0) + 1
    keep = {w for w, c in seen.items() if c >= min_seen} | extra | set(CONTRACTION_PARTS)
    return sorted(w for w in keep if w not in banned and w.isalpha())


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
    ok, why = MCHECK.sense_ok(text)             # v2 (A-TALK-7 H1 F3): the guard's sense check, layer 1
    if not ok:
        return False, why
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
            if (w[:1].isupper() and w != "I" and re.sub(r"'s$", "", w.lower()) not in have and w.lower() not in ("i'm", "i'll", "i've", "i'd")
                    and w.lower() not in OWN_NAMES):
                return False, f"name {w} not in input"
    for m in ht.RECIPE_SPEAK_RX.finditer(text):
        if m.group(0).lower() not in have:
            return False, "recipe-speak"
    q = text.count("?")
    if sit in FACT_SITUATIONS:
        r = inp["reading"]
        low = {re.sub(r"'s$", "", w.lower()) for w in words}          # A-TALK-10 K2: "Longmoor's" states longmoor
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
