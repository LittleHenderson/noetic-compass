"""teach2_rule_reader.py -- the hand-written rule reader of the TEACH-2 exam (A-TEACH2-2 B2, A-TEACH2-3).

EXAM SIDE ONLY (A-TEACH2-4 R5: no parser inside HELM). It is the reader of the TABLE and ONE_READER baselines and of
the test stand-in proposer. It is not the CTT and it never runs inside HELM's own pipeline.
General rules, no subject template; a line it cannot read gives no reading (the honest default).
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

import helm_memory_compact as hmc
from helm_cube_osc import MONTHS, VALUE_NUMBERS, Reading

#: A-TEACH2-2 B2 discourse words, plus "replaces" (the say-back's own word; build deviation D-BUILD-1)
DISCOURSE = {"correction", "actually", "sorry", "meant", "honestly", "also", "more", "said", "before", "earlier",
             "instead", "like", "just", "really", "think", "replaces"}
#: A-TEACH2-3 openers: a capitalised first word in this list is not a name
OPENERS = {"the", "this", "that", "there", "then", "these", "those", "our", "my", "your", "one", "also", "and", "but",
           "so", "oh", "okay", "ok", "by", "let", "back", "in", "on", "at", "for", "from", "after", "during", "last",
           "next", "every", "each", "honestly", "correction", "actually", "sorry", "yes", "well", "anyway", "right",
           "just", "now", "around", "about", "over", "since", "when", "as", "it", "we", "they", "he", "she", "i"}
WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _tokens(text: str) -> List[Tuple[str, int]]:
    return [(m.group(0).strip("'-"), m.start()) for m in WORD_RX.finditer(text or "")]


def _is_name(word: str, first: bool) -> bool:
    low = word.lower()
    if not word[:1].isupper() or len(word) < 3 or low in MONTHS or low in VALUE_NUMBERS:
        return False
    if first and (low in hmc.STOP_WORDS or low in DISCOURSE or low in OPENERS):
        return False
    return True


def rule_read(text: str) -> Optional[Reading]:
    toks = _tokens(text)
    if not toks:
        return None
    words = [w for w, _ in toks]
    low = [w.lower() for w in words]
    names: List[str] = []
    for i, w in enumerate(words):
        first = i == 0 or text[:toks[i][1]].rstrip().endswith(":")
        if _is_name(w, first) and low[i] not in names:
            names.append(low[i])
    replaced: List[str] = []
    for i, w in enumerate(low):
        prev = low[i - 1] if i >= 1 else ""
        prev2 = " ".join(low[i - 2:i]) if i >= 2 else ""
        nxt = low[i + 1] if i + 1 < len(low) else ""
        if prev in {"not", "replaces"} or prev2 == "instead of" or (prev == "said" and nxt == "before"):
            if w in VALUE_NUMBERS or w in names:
                replaced.append(w)
    numbers = [w for w in low if w in VALUE_NUMBERS and w not in replaced]
    if not names:
        return None
    thing = names[0]
    if numbers:
        if len(numbers) != 1:
            return None
        value = numbers[0]
    else:
        others = [n for n in names[1:] if n not in replaced]
        if not others:
            return None
        value = others[-1]
    reps = [r for r in replaced if r != value]
    replaces = reps[0] if reps else None
    slot = frozenset(w for w in hmc.content_words(text) if w not in {thing, value, replaces} and w not in DISCOURSE
                     and w not in names)
    if not slot:
        return None
    return Reading(thing=thing, slot=slot, value=value, replaces=replaces)
