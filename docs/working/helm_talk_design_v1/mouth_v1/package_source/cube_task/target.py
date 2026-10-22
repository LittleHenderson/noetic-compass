"""cube_task/target.py -- the cube task's target language, filler and grammar lock (A-CUBE-TRAIN-5). Stdlib only.

In plain words: the CTT never writes a word. For a teaching line it answers with POINTERS to the line's own tagged
words (the slot finder's ⟦n…⟧ / ⟦q…⟧ tags), in a fixed shape:
    <thing> | <slot word> <slot word> ... | <value> | <replaced value or ->        or   NONE
The filler (outside the model) copies each pointed-at word back from the line and writes the string form HELM's
adapter reads ("oxley | buses line september | eight | -"). The grammar lock lets the model write only that shape.
Direction special: the reserved [B] of the CTT vocabulary.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Sequence

from helm_cas_translator import slots as slotmod

DIRECTION = "B"
SEP, DASH, NONE, EOS = "|", "-", "NONE", "[EOS]"


def _slots(text: str) -> Dict[str, object]:
    return slotmod.find_slots(text, DIRECTION)


def tag_of_word(text: str) -> Dict[str, str]:
    """lower-case word -> its slot tag in this line (amount slots first, then word slots)."""
    sl = _slots(text)
    out: Dict[str, str] = {}
    for kind in ("q", "n"):
        for tag, rec in sl[kind].items():
            out.setdefault(str(rec["said"]).lower(), tag)
    return out


def word_of_tag(text: str) -> Dict[str, str]:
    sl = _slots(text)
    return {tag: str(rec["said"]).lower() for kind in ("q", "n") for tag, rec in sl[kind].items()}


def _tag_key(tag: str):
    return (tag[1], int(tag[2:-1]))


def encode_target(text: str, truth: str) -> Optional[List[str]]:
    """The pointer tokens for a truth string, or None when a word of it has no tag in the line (the row is dropped)."""
    if truth.strip() == NONE:
        return [NONE]
    parts = [p.strip() for p in truth.split("|")]
    if len(parts) != 4:
        return None
    thing, slot_text, value, rep = parts
    tags = tag_of_word(text)
    need = [thing, value] + slot_text.split() + ([rep] if rep != DASH else [])
    if any(w not in tags for w in need):
        return None
    if not tags[thing].startswith("⟦n"):
        return None
    slot_tags = sorted({tags[w] for w in slot_text.split()}, key=_tag_key)
    return [tags[thing], SEP] + slot_tags + [SEP, tags[value], SEP, tags[rep] if rep != DASH else DASH]


def fill(tokens: Sequence[str], text: str) -> Optional[str]:
    """Pointer tokens -> the string form HELM's adapter reads, copying each word from the line; None if malformed."""
    toks = list(tokens)
    if toks == [NONE]:
        return NONE
    groups: List[List[str]] = [[]]
    for t in toks:
        if t == SEP:
            groups.append([])
        else:
            groups[-1].append(t)
    if len(groups) != 4 or len(groups[0]) != 1 or not groups[1] or len(groups[2]) != 1 or len(groups[3]) != 1:
        return None
    words = word_of_tag(text)
    try:
        thing = words[groups[0][0]]
        slot = sorted({words[t] for t in groups[1]})
        value = words[groups[2][0]]
        rep = DASH if groups[3][0] == DASH else words[groups[3][0]]
    except KeyError:
        return None
    return f"{thing} | {' '.join(slot)} | {value} | {rep}"


def canonical(tokens: Sequence[str], text: str) -> Optional[List[str]]:
    """The answer in one standard order (slot pointers sorted), so equal readings compare equal; None if malformed."""
    filled = fill(tokens, text)
    return None if filled is None else encode_target(text, filled)


class Automaton:
    """The grammar lock for direction [B]: allowed() -> the tokens that may come next; step(tok)."""

    def __init__(self, q_ok: FrozenSet[str], n_ok: FrozenSet[str]):
        self.q_ok, self.n_ok = frozenset(q_ok), frozenset(n_ok)
        self.state = 0
        self.used: set = set()
        self.ended = False
        self.dead = False

    def allowed(self) -> FrozenSet[str]:
        if self.ended or self.dead:
            return frozenset()
        s = self.state
        if s == 0:
            return frozenset({NONE}) | self.n_ok
        if s in (1, 4):
            return frozenset({SEP})
        if s == 2:
            return self.n_ok
        if s == 3:
            return (self.n_ok - self.used) | frozenset({SEP})
        if s == 5:
            return self.q_ok | self.n_ok
        if s == 6:
            return frozenset({SEP})
        if s == 7:
            return self.q_ok | self.n_ok | frozenset({DASH})
        return frozenset({EOS})                         # s == 9 (after NONE) or s == 8 (after replaces)

    def step(self, tok: str) -> None:
        if tok not in self.allowed():
            self.dead = True
            return
        if tok == EOS:
            self.ended = True
            return
        s = self.state
        if s == 0:
            self.state = 9 if tok == NONE else 1
        elif s == 1:
            self.state = 2
        elif s == 2:
            self.used.add(tok)
            self.state = 3
        elif s == 3:
            if tok == SEP:
                self.state = 5
            else:
                self.used.add(tok)
        elif s == 5:
            self.state = 6
        elif s == 6:
            self.state = 7
        elif s == 7:
            self.state = 8


def automaton_for(text: str) -> Automaton:
    sl = _slots(text)
    return Automaton(frozenset(sl["q"]), frozenset(sl["n"]))


def accepts(text: str, tokens: Sequence[str]) -> bool:
    a = automaton_for(text)
    for t in list(tokens) + [EOS]:
        a.step(t)
        if a.dead:
            return False
    return a.ended
