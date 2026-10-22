"""mouth_task/check.py -- the guard on every mouth line (A-TALK-4 W5), frozen copies of HELM's own rules so the package
runs without HELM. Standard library only.

Copied by value (the source files' sha256 are recorded in FROZEN_MOUTH.json):
  helm_voice.py  CAS_NOTATION_RX, CAS_JARGON_RX, sentence_count            (sha256 9a5d918f...)
  helm_talk.py   OPINION_RX, RECIPE_SPEAK_RX                               (sha256 dc64b802...)
  mouth_lessons  the situation shapes and the word rule (no name, number or month that is not in the input)
A line that fails any check is never spoken; the template is (the fallback, A-TALK-5 F1).
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, Optional, Set, Tuple

CAS_NOTATION_RX = re.compile(
    r"\^\d|[ΩΘΛκι]|\bF[1-7]\b|\|[TAfE]\b|\b[PCEO][0-9]\b|\bCO-\d\b|\bG-[A-Z]+\b|"
    r"\b(?:RPM|RPA|ASOM|CJT|CCE|UNDETERMINED|CLARIFY|REFUSE_CLAIM|GATE_[A-Z_]+|A0|D[1-7]|W[1-7])\b")
CAS_JARGON_RX = re.compile(
    r"\b(?:noetic\w*|lacuna\w*|stoichiometr\w*|registers?|operators?|entropy|aperture|valve|receipts?|40-digit|"
    r"decimal precision|limiting reagent|topological|admissib\w*|simplex|cognitive states?|pathways?|"
    r"prerequisite gate|novelty|kahn)\b", re.I)
OPINION_RX = re.compile(r"\b(?:i think|i believe|i feel that|i like|i love|i hate|in my opinion|you should|"
                        r"that'?s (?:good|bad|great|terrible|wrong|right|awful|wonderful)|that is (?:good|bad|great|terrible|"
                        r"wrong|right|awful|wonderful))\b", re.I)
RECIPE_SPEAK_RX = re.compile(r"\b(?:recipes?|ingredients?|stock|inventory|limiting|yield|batch|receipt|foundation loop|station|"
                             r"gate|RPM|cube|verified facts|flour|water|sugar|butter|eggs?|milk|salt|yeast)\b"
                             r"|how much .* do (?:we|you) have", re.I)
NODATA_RX = re.compile(r"\b(?:don't know|do not know|not sure|no idea|can't say|nobody has told me|haven't been told|"
                       r"no way to know|don't have that)\b", re.I)
FACT_SITUATIONS = ("ANSWER", "SAYBACK", "ASK")
WORD_RX = re.compile(r"[a-z]+|\d+")


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()])


def cas_tokens(text: str):
    return [m.group(0) for m in CAS_NOTATION_RX.finditer(text)] + [m.group(0) for m in CAS_JARGON_RX.finditer(text)]


SMALL_WORDS = frozenset("a an the to of in on at and or but is are was were be been it its i you me my your we our "
                        "that this these those for with do did does so not no yes he she they them his her their "
                        "has have had as by from what how".split())


def sense_ok(line: str) -> Tuple[bool, str]:
    """Sense check, layer 1 (A-TALK-7 H1 F3), frozen: a line fails when a word appears twice in a row ("bat bat") or a
    content word (not in SMALL_WORDS) appears three or more times."""
    words = re.findall(r"[a-z']+|\d+", (line or "").lower())
    for a, b in zip(words, words[1:]):
        if a == b:
            return False, "sense: '%s' twice in a row" % a
    counts: Dict[str, int] = {}
    for w in words:
        if w not in SMALL_WORDS:
            counts[w] = counts.get(w, 0) + 1
            if counts[w] >= 3:
                return False, "sense: '%s' three times" % w
    return True, ""


def check(situation: str, input_text: str, line: str, fact_words: Set[str],
          reading: Optional[Dict[str, object]] = None) -> Tuple[bool, str]:
    """`fact_words` = every name, number word and month of the subject pools (published in the package)."""
    text = (line or "").strip()
    if not text:
        return False, "empty"
    ok, why = sense_ok(text)
    if not ok:
        return False, why
    have = set(WORD_RX.findall(input_text.lower()))
    words = WORD_RX.findall(text.lower())
    if cas_tokens(text):
        return False, "CAS token"
    if not 1 <= sentence_count(text) <= 3:
        return False, "sentences"
    if OPINION_RX.search(text):
        return False, "opinion"
    for w in words:
        if (w.isdigit() or w in fact_words) and w not in have:
            return False, f"{w} not in input"
    for m in RECIPE_SPEAK_RX.finditer(text):
        if m.group(0).lower() not in have:
            return False, "recipe-speak"
    q = text.count("?")
    if situation in FACT_SITUATIONS:
        r = reading or {}
        if str(r.get("value")) not in words or str(r.get("thing")) not in words:
            return False, "the reading's value or thing missing"
        if situation == "ASK" and (q != 1 or not text.endswith("?")):
            return False, "ASK must be one question at the end"
        if situation != "ASK" and q:
            return False, "no question in an answer"
    elif situation == "OFF" and q != 1:
        return False, "OFF needs exactly one question"
    elif situation == "WORLD" and not NODATA_RX.search(text):
        return False, "WORLD must say it does not know"
    return True, ""


def only_allowed_words(line: str, allowed: Iterable[str]) -> bool:
    """The lock's promise, re-checked on the finished line: every word is an allowed word."""
    a = set(allowed)
    return all(w in a for w in WORD_RX.findall((line or "").lower()))
