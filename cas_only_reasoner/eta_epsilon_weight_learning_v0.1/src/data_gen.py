"""Phase 2 data: mechanical active/passive role-binding generator.

No language model labels anything. Gold roles are set by the template.
Every example carries a content hash. Lexical split holds out nouns and
verbs so the test set uses unseen vocabulary."""
from __future__ import annotations

import hashlib
import random

NOUNS = ["cat", "dog", "fox", "hen", "bird", "wolf", "lion", "bear",
         "mouse", "frog", "duck", "goat"]
VERBS_PAST = ["chased", "bit", "followed", "watched", "kicked",
              "caught", "licked", "pushed"]

# lexical split: last 3 nouns + last 2 verbs are TEST-ONLY vocabulary
TEST_NOUNS = set(NOUNS[-3:])
TEST_VERBS = set(VERBS_PAST[-2:])


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def make_example(a: str, b: str, verb: str, voice: str) -> dict:
    if voice == "active":
        text = f"the {a} {verb} the {b}."
        surface = [a, b]              # agent is surface[0]
        agent_is_first = True
    else:
        text = f"the {b} was {verb} by the {a}."
        surface = [b, a]              # agent (a) is surface[1]
        agent_is_first = False
    return {"text": text, "verb": verb, "agent": a, "patient": b,
            "voice": voice, "surface_nouns": surface,
            "agent_is_surface_first": agent_is_first,
            "label": 1 if agent_is_first else 0,
            "hash": _hash(text)}


def generate(seed: int = 20260830):
    rng = random.Random(seed)
    train, test = [], []
    for a in NOUNS:
        for b in NOUNS:
            if a == b:
                continue
            for verb in VERBS_PAST:
                for voice in ("active", "passive"):
                    ex = make_example(a, b, verb, voice)
                    uses_test_vocab = (a in TEST_NOUNS or b in TEST_NOUNS
                                       or verb in TEST_VERBS)
                    (test if uses_test_vocab else train).append(ex)
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


if __name__ == "__main__":
    tr, te = generate()
    print(f"train {len(tr)}  test {len(te)}")
    print("train balance (agent_is_first):",
          round(sum(e['label'] for e in tr) / len(tr), 3))
    print("test  balance:",
          round(sum(e['label'] for e in te) / len(te), 3))
    print("example active :", tr[0]['text'], "->", tr[0]['agent'])
    print("example passive:",
          next(e for e in tr if e['voice'] == 'passive')['text'])
