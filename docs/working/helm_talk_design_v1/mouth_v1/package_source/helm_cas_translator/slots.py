"""Slot finder: which spans of the user's sentence the translator may point at. Pure, deterministic, stdlib only.

In plain words: before the model sees a sentence, every amount and every candidate word gets a numbered tag
(⟦q1⟧ for the first amount, ⟦n1⟧ for the first word that could be a name). The model answers with tags, never with
the amount or the word itself. A filler outside this module copies the tagged span back. The same word always gets
the same tag (so "flour ... ran out of flour" is one tag).

Amounts are only the forms HELM's reader accepts: digits (with decimals, p/q fractions, thousands commas) and the
reader's number words one..ten and half. Anything else ("twelve", "a dozen") is not an amount slot, so the model
cannot point at it, and HELM asks instead.

Direction "N" (notation): name slots are identifier-like words (letters/digits joined by underscores, e.g.
verification_73) and quoted strings; amounts are plain decimal numbers.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

MAX_Q, MAX_N = 16, 32

#: the reader's number words (ALIAS_WIDE_LEXICON_v0_1.json number_words, frozen); copied by value so this module
#: imports nothing from HELM. tests_ctt/test_slots.py checks the copy against the reader's file.
NUMBER_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "half")

NUM_RX = re.compile(r"(?<![\w.,/])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?(?:/\d+)?|\.\d+)(?![\w/])")
NUMWORD_RX = re.compile(r"(?<![\w'])(%s)(?![\w'])" % "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)), re.I)
WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*[A-Za-z]|[A-Za-z]")
IDENT_RX = re.compile(r"(?<![\w])[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+(?![\w])")
QUOTED_RX = re.compile(r"[\"“]([A-Za-z][A-Za-z0-9_]*)[\"”]")
NOTATION_NUM_RX = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w])")

#: closed list of words that are never a name slot (function words, pronouns, common verbs)
STOPWORDS = frozenset("""
a an the and or but of in on to for with from by at up about as into onto over under than then too also so if
is are was were be been being am do does did done have has had having get got gets getting can could will would
shall should may might must we i you he she they it its it's this that these those there here my our your their
me us him her them what which who whom whose when where why how not no yes ok okay please thanks thank hi hey hello
just only still now some any all more much many most less few lot lots each every both either neither one's
let let's oh well right sure yeah yep nope um uh like really very quite pretty kind sort maybe perhaps
""".split())


def _spans_q(text: str, direction: str) -> List[Tuple[int, int, str]]:
    if direction == "N":
        return [(m.start(1), m.end(1), m.group(1)) for m in NOTATION_NUM_RX.finditer(text)]
    out = [(m.start(1), m.end(1), m.group(1)) for m in NUM_RX.finditer(text)]
    out += [(m.start(1), m.end(1), m.group(1)) for m in NUMWORD_RX.finditer(text)]
    return sorted(out)


def _spans_n(text: str, direction: str, taken: List[Tuple[int, int]]) -> List[Tuple[int, int, str]]:
    def free(a, b):
        return not any(x < b and a < y for x, y in taken)
    if direction == "N":
        # identifier-like words and quoted strings first (they get the low tag numbers), then plain words
        prim = [(m.start(), m.end(), m.group(0)) for m in IDENT_RX.finditer(text)]
        prim += [(m.start(1), m.end(1), m.group(1)) for m in QUOTED_RX.finditer(text)]
        prim = sorted(s for s in prim if free(s[0], s[1]))
        sec = [(m.start(), m.end(), m.group(0)) for m in WORD_RX.finditer(text)
               if m.group(0).lower() not in STOPWORDS and free(m.start(), m.end())
               and not any(a < m.end() and m.start() < b for a, b, _w in prim)]
        return prim + sec
    out = []
    for m in WORD_RX.finditer(text):
        w = m.group(0)
        if w.lower() in STOPWORDS or not free(m.start(), m.end()):
            continue
        out.append((m.start(), m.end(), w))
    return out


def find_slots(text: str, direction: str = "A") -> Dict[str, object]:
    """Return {"q": {tag: {start,end,said}}, "n": {tag: {...}}, "spans": [(start, end, tag)]} for one sentence.
    Tags are numbered by first occurrence; the same surface (case-folded for words) reuses its tag; slots beyond
    the caps are left untagged (the model cannot point at them)."""
    text = text or ""
    q, n, spans = {}, {}, []
    seen_q: Dict[str, str] = {}
    for a, b, said in _spans_q(text, direction):
        key = said.lower()
        tag = seen_q.get(key)
        if tag is None:
            if len(q) >= MAX_Q:
                continue
            tag = "⟦q%d⟧" % (len(q) + 1)
            seen_q[key] = tag
            q[tag] = {"start": a, "end": b, "said": said}
        spans.append((a, b, tag))
    seen_n: Dict[str, str] = {}
    for a, b, word in _spans_n(text, direction, [(s[0], s[1]) for s in spans]):
        key = word if direction == "N" else word.lower()
        tag = seen_n.get(key)
        if tag is None:
            if len(n) >= MAX_N:
                continue
            tag = "⟦n%d⟧" % (len(n) + 1)
            seen_n[key] = tag
            n[tag] = {"start": a, "end": b, "said": word}
        spans.append((a, b, tag))
    spans.sort()
    return {"q": q, "n": n, "spans": spans}


def tagged_units(text: str, slots: Dict[str, object]) -> List[Tuple[str, str]]:
    """The sentence as a list of (kind, piece): ("TAG", "⟦q1⟧") before each tagged span, ("TEXT", "...") between.
    The tagged span's own text stays in the input (the model sees the number and the word)."""
    out: List[Tuple[str, str]] = []
    pos = 0
    for a, b, tag in slots["spans"]:
        if a > pos:
            out.append(("TEXT", text[pos:a]))
        out.append(("TAG", tag))
        out.append(("TEXT", text[a:b]))
        pos = b
    if pos < len(text):
        out.append(("TEXT", text[pos:]))
    return out
