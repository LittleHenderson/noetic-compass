"""The full vocabulary (specials + CAS tokens + English pieces) and the encoders. Standard library only.

Id space, in order: 8 specials, the CAS-side tokens of cas_vocab (CAS ids), then exactly 8,000 English word-pieces
(English ids). The output side of directions A and N may only use CAS ids and [EOS] (grammar_lock enforces it), so
the model can never write an English piece, a digit or a name.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence, Tuple

from . import cas_vocab, slots as slotmod
from .wordpiece import ENGLISH_PIECES, WordPiece, normalize

SPECIALS = ["[PAD]", "[BOS]", "[EOS]", "[UNK]", "[SEP]", "[A]", "[N]", "[B]"]
PAD, BOS, EOS, UNK, SEP = 0, 1, 2, 3, 4
DIRECTION_ID = {"A": 5, "N": 6, "B": 7}
EN_PREFIX = "en:"


class Vocab:
    def __init__(self, english_pieces: Sequence[str]):
        if len(english_pieces) != ENGLISH_PIECES:
            raise ValueError("exactly %d English pieces are required" % ENGLISH_PIECES)
        self.cas = cas_vocab.cas_tokens()
        self.tokens = list(SPECIALS) + list(self.cas) + [EN_PREFIX + p for p in english_pieces]
        self.id = {t: i for i, t in enumerate(self.tokens)}
        self.cas_lo = len(SPECIALS)
        self.cas_hi = self.cas_lo + len(self.cas)          # CAS ids are [cas_lo, cas_hi)
        self.wp = WordPiece(list(english_pieces))
        self.input_only_ids = {self.id[t] for t in cas_vocab.INPUT_ONLY}

    def __len__(self) -> int:
        return len(self.tokens)

    @classmethod
    def load(cls, path: str) -> "Vocab":
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        v = cls(doc["english_pieces"])
        if doc.get("cas_tokens") != v.cas:
            raise ValueError("vocabulary file was built with a different CAS token list")
        return v

    def dump(self) -> Dict[str, object]:
        return {"schema": "ctt.vocab/1", "cas_vocab_version": cas_vocab.VOCAB_VERSION, "specials": SPECIALS,
                "cas_tokens": self.cas, "english_pieces": [t[len(EN_PREFIX):] for t in self.tokens[self.cas_hi:]],
                "size": len(self.tokens)}

    def cas_id(self, tok: str) -> int:
        return self.id[tok]

    def english_ids(self, text: str) -> List[int]:
        out = []
        for p in self.wp.encode(text):
            out.append(UNK if p is None else self.id[EN_PREFIX + p])
        return out

    # ------------------------------------------------------------------ source side
    def encode_source(self, direction: str, text: str, context: Optional[List[Tuple[str, str]]] = None
                      ) -> Tuple[List[int], Dict[str, object]]:
        """[dir] + dialogue records + [SEP] + the sentence with slot tags. Returns (ids, slots). Never truncates."""
        sl = slotmod.find_slots(text, direction)
        ids = [DIRECTION_ID[direction]]
        for kind, piece in context or []:
            ids.extend([self.id[piece]] if kind == "CAS" else self.english_ids(piece))
        ids.append(SEP)
        for kind, piece in slotmod.tagged_units(text, sl):
            if kind == "TAG":
                ids.append(self.id[piece])
            else:
                ids.extend(self.english_ids(piece))
        return ids, sl

    # ------------------------------------------------------------------ target side
    def encode_target(self, toks: Sequence[str]) -> List[int]:
        return [self.id[t] for t in toks] + [EOS]

    def decode_target(self, ids: Sequence[int]) -> List[str]:
        out = []
        for i in ids:
            if i == EOS:
                break
            out.append(self.tokens[i])
        return out


def context_units(records: Sequence[Dict[str, object]]) -> List[Tuple[str, str]]:
    """Dialogue records -> source units. Each record: {"kind": TOPIC|ASKED|STOCK|ABSENT, "name": str,
    "amount": str|None, "unit": str|None, "code": str|None}; record k gets the tag ⟦ck⟧ (k = 1..8)."""
    out: List[Tuple[str, str]] = []
    for k, r in enumerate(list(records)[:8], start=1):
        out.append(("CAS", "⟦c%d⟧" % k))
        out.append(("CAS", str(r["kind"])))
        if r.get("code"):
            out.append(("CAS", str(r["code"])))
        if r.get("amount") is not None:
            out.append(("TEXT", str(r["amount"])))
            if r.get("unit"):
                out.append(("TEXT", str(r["unit"])))
            out.append(("CAS", "·"))
        out.append(("CAS", "Ω_"))
        out.append(("TEXT", normalize(str(r.get("name") or ""))))
    return out
