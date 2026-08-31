"""baselines.py -- the two REGISTERED deterministic surface baselines.

B0 (floor): class-blind co-occurrence heuristic. Reads passage text, question
text, and the closed candidate set. It never classifies a clause -- it only
matches entity names and surface positions. Registered as the FLOOR row.

B1 (ceiling): the full deterministic surface-grammar parser (owner audit
2026-08-31 section 6). Reads ONLY passage text and question text; parses every
sentence with the public grammar; derives the answer from the recovered trace.
The task is exactly surface-solvable, so B1's expected accuracy is 1.00 -- it is
reported as the TASK CEILING, which fixes the honest meaning of any neural
result: a positive S3 says task-aligned labels help a frozen encoder reach a
surface-computable function; it never says CAS supplies information absent from
the language.

Neither function reads seed_trace, idea_labels, CAS profiles, or hidden states.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from independent_roundtrip_checker import _G, _Q, _derive_answer  # public grammar


def split_sentences(text: str):
    return [s for s in re.split(r"(?<=\.)\s+", text) if s]


def _parse_question(question: str):
    hits = [(qt, m) for qt, rx in _Q if (m := rx.match(question))]
    return hits[0] if len(hits) == 1 else (None, None)


def _entities_in_order(sentence: str, candidates):
    found = []
    for e in candidates:
        m = re.search(rf"\b{re.escape(e)}\b", sentence)
        if m:
            found.append((m.start(), e))
    return [e for _, e in sorted(found)]


def b0_answer(text: str, question: str, candidates):
    """Class-blind floor: entity co-occurrence + surface ordinal for Q_PART."""
    qtype, m = _parse_question(question)
    if qtype is None:
        return None
    sents = split_sentences(text)
    if qtype in ("Q_ATTRACT", "Q_AVERT"):
        mind = m.group(1)
        for s in sents:
            if re.search(rf"\b{re.escape(mind)}\b", s):
                for e in _entities_in_order(s, candidates):
                    if e != mind:
                        return e
        return None
    if qtype == "Q_PART":
        k, idea = int(m.group(1)), m.group(2)
        for s in sents:
            if re.search(rf"\b{re.escape(idea)}\b", s):
                others = [e for e in _entities_in_order(s, candidates) if e != idea]
                if len(others) >= k:
                    return others[k - 1]
        return None
    a, mind = m.group(1), m.group(2)                   # Q_TRIGGER
    for s in sents:
        if (re.search(rf"\b{re.escape(a)}\b", s)
                and re.search(rf"\b{re.escape(mind)}\b", s)):
            others = [e for e in _entities_in_order(s, candidates)
                      if e not in (a, mind)]
            if others:
                return others[0]
    return None


def b1_answer(text: str, question: str):
    """Full surface-grammar parser: passage text + question text ONLY."""
    trace = []
    for s in split_sentences(text):
        hits = [mapper(m) for _cls, _fam, rx, mapper in _G if (m := rx.match(s))]
        if len(hits) != 1:
            return None
        trace.append(hits[0])
    qtype, m = _parse_question(question)
    if qtype is None:
        return None
    return _derive_answer(qtype, m, trace)


def score_split(records, which: str):
    """Per-question-type + overall accuracy of B0 or B1 over records."""
    per = {}
    for rec in records:
        if which == "B0":
            pred = b0_answer(rec["text"], rec["question"], rec["candidates"])
        else:
            pred = b1_answer(rec["text"], rec["question"])
        qt = rec["question_type"]
        n_ok, n = per.get(qt, (0, 0))
        per[qt] = (n_ok + (1 if pred == rec["answer"] else 0), n + 1)
    overall_ok = sum(v[0] for v in per.values())
    overall_n = sum(v[1] for v in per.values())
    return {"overall": overall_ok / overall_n,
            "correct": overall_ok, "total": overall_n,
            "per_question_type": {qt: {"accuracy": ok / n, "correct": ok, "total": n}
                                  for qt, (ok, n) in sorted(per.items())}}
