"""English word-pieces, learned from scratch on the allowed INPUT text only. Standard library only.

In plain words: a word the model knows well is one piece ("flour"); a rarer word is cut into a start piece and
continuation pieces ("cinna", "##mon"). The list of pieces is built from our own training inputs by counting, with
no borrowed tokenizer. Digits are always single characters, so no number ever becomes one memorized piece.
Exactly ENGLISH_PIECES pieces are kept; if the text cannot fill them, the rest are reserved placeholders (counted).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List

ENGLISH_PIECES = 8000
MAX_PIECE = 10
PRETOKEN_RX = re.compile(r"[a-z]+|\d|[^\sa-z\d]")


def normalize(text: str) -> str:
    t = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t.lower()).strip()


def pretokens(text: str) -> List[str]:
    return PRETOKEN_RX.findall(normalize(text))


def build_pieces(texts: Iterable[str], size: int = ENGLISH_PIECES) -> Dict[str, object]:
    """Deterministic piece list: every character seen (start and continuation form), then whole words by frequency,
    then frequent start / continuation fragments, ties broken by the string itself."""
    words = Counter()
    for t in texts:
        words.update(w for w in pretokens(t))
    chars = set()
    for w in words:
        chars.add(w[0])
        chars.update("##" + c for c in w[1:])
    pieces = sorted(chars)
    if len(pieces) > size:
        raise ValueError("more distinct characters than pieces")
    budget_words = int((size - len(pieces)) * 0.75)
    ranked_words = [w for w, _c in sorted(words.items(), key=lambda kv: (-kv[1], kv[0])) if len(w) > 1]
    chosen = set(pieces)
    for w in ranked_words[:budget_words]:
        if w not in chosen:
            chosen.add(w)
            pieces.append(w)
    frag = Counter()
    for w, c in words.items():          # fragments of EVERY word, so unseen human words can still be cut
        if len(w) < 3:
            continue
        for k in range(2, min(MAX_PIECE, len(w)) + 1):
            frag[w[:k]] += c
        for i in range(1, len(w) - 1):
            s = w[i:i + MAX_PIECE]
            for k in range(2, len(s) + 1):
                frag["##" + s[:k]] += c
    for f, _c in sorted(frag.items(), key=lambda kv: (-kv[1], kv[0])):
        if len(pieces) >= size:
            break
        if f not in chosen:
            chosen.add(f)
            pieces.append(f)
    reserved = 0
    while len(pieces) < size:
        pieces.append("[unused_%d]" % reserved)
        reserved += 1
    return {"pieces": pieces, "reserved_placeholders": reserved, "distinct_words": len(words),
            "characters": len(chars)}


class WordPiece:
    def __init__(self, pieces: List[str]):
        self.pieces = list(pieces)
        self.index = {p: i for i, p in enumerate(self.pieces)}

    def word(self, w: str) -> List[str]:
        """Greedy longest match; a word that cannot be covered is the single unknown marker None."""
        if w in self.index:
            return [w]
        out, i = [], 0
        while i < len(w):
            j = min(len(w), i + MAX_PIECE)
            found = None
            while j > i:
                cand = w[i:j] if i == 0 else "##" + w[i:j]
                if cand in self.index:
                    found = cand
                    break
                j -= 1
            if found is None:
                return [None]
            out.append(found)
            i = j
        return out

    def encode(self, text: str) -> List[object]:
        out: List[object] = []
        for w in pretokens(text):
            out.extend(self.word(w))
        return out
