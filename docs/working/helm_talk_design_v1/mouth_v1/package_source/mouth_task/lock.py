"""mouth_task/lock.py -- the mouth's writing lock: words, never facts (A-TALK-4 W4). Standard library only.

The CTT spells a rare word from small pieces ("oxley" = o ##x ##le ##y), and the same small pieces build ordinary words,
so a lock on single pieces could not stop an invented name. This lock works on WHOLE words: the mouth may only finish
a word that is in the frozen everyday-word list (FUNCTION_WORDS, published in the package) or in its own input, each
spelled exactly as the vocabulary splits it; punctuation pieces between words; [EOS] only at a word end after at least
one word. Never a CAS token. So a name, a number or a month the input does not hold cannot be written at all.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Optional, Set

from .vocab_m import input_words

PUNCT = (".", ",", "?", "!", "'", ";", ":", "-")
EOS = "[EOS]"


def allowed_words(function_words: Iterable[str], input_text: str) -> Set[str]:
    return {w for w in function_words} | set(input_words(input_text))


class _Node:
    __slots__ = ("kids", "end")

    def __init__(self) -> None:
        self.kids: Dict[str, "_Node"] = {}
        self.end = False


class MouthAutomaton:
    def __init__(self, vocab, words: Iterable[str]) -> None:
        self.root = _Node()
        for w in words:
            pieces = vocab.wp.word(w)
            if not pieces or None in pieces:
                continue
            n = self.root
            for p in pieces:
                n = n.kids.setdefault("en:" + p, _Node())
            n.end = True
        self.start_tokens: FrozenSet[str] = frozenset(self.root.kids)
        self.punct = frozenset("en:" + p for p in PUNCT if ("en:" + p) in vocab.id)
        self.node: Optional[_Node] = None          # None = between words
        self.words = 0
        self.ended = False
        self.dead = False
        self._cache: Dict[int, FrozenSet[str]] = {}

    def allowed(self) -> FrozenSet[str]:
        if self.ended or self.dead:
            return frozenset()
        n = self.node
        if n is None:
            out = set(self.start_tokens)
            if self.words:
                out |= self.punct | {EOS}
            return frozenset(out)
        key = id(n)
        got = self._cache.get(key)
        if got is None:
            out = {t for t in n.kids if t.startswith("en:##")}
            if n.end:
                out |= self.start_tokens | self.punct | {EOS}
            got = self._cache[key] = frozenset(out)
        return got

    def step(self, tok: str) -> None:
        if tok not in self.allowed():
            self.dead = True
            return
        if tok == EOS:
            self.ended = True
            return
        if tok in self.punct:
            self.node = None
            return
        if tok.startswith("en:##"):
            self.node = self.node.kids[tok]
        else:
            self.node = self.root.kids[tok]
            self.words += 1
