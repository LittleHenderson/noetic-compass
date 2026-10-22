"""mouth_task/names.py -- which words of the mouth's input are written with a capital (A-TALK-4 W3). Standard library.

The CTT's pieces are lower case, so the capitals come back from the input: for a reading, its thing, a value or an old
value that is a name, and every month; for a person's line, every word the person wrote with a capital somewhere other
than at the start of a sentence (a sentence's first word could be an ordinary word, so it is used only when the same
word is capitalised mid-sentence elsewhere). "I" is handled by the detokenizer.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, Optional

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def names_for(reading: Optional[Dict[str, object]] = None, person_line: Optional[str] = None,
              number_words: Iterable[str] = ()) -> Dict[str, str]:
    out: Dict[str, str] = {}
    nums = set(number_words)
    if reading:
        for w in [reading.get("thing"), reading.get("value"), reading.get("replaces")] + list(reading.get("slot") or []):
            if not w:
                continue
            w = str(w).lower()
            if w in MONTHS or (w not in nums and w == reading.get("thing")) or \
                    (w not in nums and w in (reading.get("value"), reading.get("replaces"))):
                out[w] = w.capitalize()
    if person_line:
        for sent in re.split(r"(?<=[.!?])\s+", person_line.strip()):
            toks = WORD_RX.findall(sent)
            for t in toks[1:]:
                if t[:1].isupper() and t != "I":
                    out[t.lower()] = t
        for m in MONTHS:
            if re.search(r"\b%s\b" % m, person_line.lower()):
                out[m] = m.capitalize()
    return out
