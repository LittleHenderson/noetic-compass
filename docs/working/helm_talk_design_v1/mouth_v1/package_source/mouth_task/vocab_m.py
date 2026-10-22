"""mouth_task/vocab_m.py -- the CTT's vocabulary with the mouth direction [M] (A-TALK-4 W2, W3). Standard library only.

[M] is appended at the END of the vocabulary, so every existing id (specials, CAS tokens, English pieces) is unchanged
and the CUBE TRAIN weights load with one extra row in the shared embedding and the output bias.
Mouth source: [M] + the tone tag (a state token, ^C, a register token) + [SEP] + the input words as English pieces.
Mouth target: the reply as English pieces + [EOS]. The pieces are lower case; `detokenize` puts back the capitals
(sentence starts, "I", and the names the input carries) and the spacing.
"""
from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

from helm_cas_translator.vocab import EOS, SEP, UNK, Vocab  # noqa: F401  (re-exported for the tests)
from helm_cas_translator.wordpiece import pretokens

M_TOKEN = "[M]"
STATE_DOMAIN = "^C"
TONE_STATES = tuple("^%d" % i for i in range(10))
REGISTERS = ("|T", "|A", "|f", "|E")


def base(path: str) -> Vocab:
    return Vocab.load(path)


class VocabM:
    """The base vocabulary plus [M] at the end (ids unchanged)."""

    def __init__(self, v: Vocab):
        self.base = v
        self.tokens = list(v.tokens) + [M_TOKEN]
        self.id = dict(v.id)
        self.m_id = len(v.tokens)
        self.id[M_TOKEN] = self.m_id
        self.cas_lo, self.cas_hi = v.cas_lo, v.cas_hi
        self.wp = v.wp

    def __len__(self) -> int:
        return len(self.tokens)

    def english_ids(self, text: str) -> List[int]:
        return self.base.english_ids(text)

    def encode_mouth_source(self, situation: str, tone: Tuple[str, str], input_text: str) -> List[int]:
        state, register = tone
        if state not in TONE_STATES or register not in REGISTERS:
            raise ValueError("tone tag %r is not a state token and a register" % (tone,))
        return [self.m_id, self.id[state], self.id[STATE_DOMAIN], self.id[register], SEP] + self.english_ids(input_text)

    def encode_mouth_target(self, text: str) -> List[int]:
        return self.english_ids(text) + [EOS]


def load(path: str) -> VocabM:
    return VocabM(Vocab.load(path))


# ----------------------------------------------------------------------------------------------- back to text
NO_SPACE_BEFORE = {".", ",", "?", "!", ";", ":", ")", "%"}
NO_SPACE_AFTER = {"(", "$"}


def detokenize(tokens: Sequence[str], names: Dict[str, str]) -> str:
    """English piece tokens ("en:..." strings) -> a sentence: pieces joined into words, punctuation attached, an
    apostrophe joined to both neighbours ("don ' t" -> "don't"), capitals on sentence starts, "I", and every word in
    `names` (lower-case word -> its written form, from the input)."""
    words: List[str] = []
    for t in tokens:
        p = t[3:] if t.startswith("en:") else t
        if p.startswith("##") and words:
            words[-1] += p[2:]
        else:
            words.append(p)
    out = ""
    glue_next = False
    for w in words:
        if not out:
            out = w
        elif w == "'" or glue_next or w in NO_SPACE_BEFORE:
            out += w
        elif out[-1:] in NO_SPACE_AFTER:
            out += w
        else:
            out += " " + w
        glue_next = w == "'"
    toks = re.split(r"(\s+)", out)
    fixed, start = [], True
    for tok in toks:
        if not tok or tok.isspace():
            fixed.append(tok)
            continue
        core = re.match(r"^([a-z0-9']+)(.*)$", tok)
        if core:
            word, rest = core.group(1), core.group(2)
            if word in names:
                word = names[word]
            elif word == "i" or word.startswith("i'"):
                word = "I" + word[1:]
            elif start:
                word = word[:1].upper() + word[1:]
            tok = word + rest
        fixed.append(tok)
        start = bool(re.search(r"[.!?]$", tok))
    return "".join(fixed)


def input_words(text: str) -> List[str]:
    """The words of an input as the lock counts them (the word-piece pre-tokens that are words or digits)."""
    return [w for w in pretokens(text) if re.fullmatch(r"[a-z]+|\d", w)]
