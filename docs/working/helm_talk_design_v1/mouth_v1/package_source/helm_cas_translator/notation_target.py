"""The A-notation target language: CAS expressions in the compiler's own token language. Stdlib only.

The tokens are those of cas_vocab categories 1-6 (never the input-only nesting tags or CAS-Ohm), plus amount and
word slots. The lock keeps brackets balanced; the compiler, the recipe grammar and the round trip (outside this
module) decide everything else.

render() turns a filled token list into compiler source text in the SDG's own style (`2*^7^C|f + 1.5*^5^P`), so the
SDG recipe grammar (sdg_bridge_v2.grammar.parse_recipe) can read it.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, Sequence

from . import cas_vocab as cv

EOS = "[EOS]"
OPEN = {"(": ")", "{": "}", "_{": "}", "[": "]", "⟨": "⟩", "Φ⟨": "⟩", "|⟨": "⟩"}
CLOSE = {")", "}", "]", "⟩"}
_cats = dict(cv.CATEGORIES)
BASE = frozenset(t for name in ("1_state_literals", "2_register_multiplicity", "3_operators", "4_recipes",
                                "5_meta_logic", "6_cognitive_fractals_and_nesting")
                 for t in _cats[name]) - frozenset(cv.INPUT_ONLY)
MAX_LEN = 128
DIGITS = frozenset(str(d) for d in range(10))

SPACED = {"+", "-", "=", "→", "←", "↔", "∘", "×", "÷", "/", "∪", "∩", "∖", "∈", "∉", "⊂", "⊆", "⊃", "⊇"}
WORDS = set(cv.META_KEYWORDS[:4])            # let fn use export


class Automaton:
    def __init__(self, q_ok: FrozenSet[str], n_ok: FrozenSet[str]):
        self.base = BASE | q_ok | n_ok
        self.stack: List[str] = []
        self.n = 0
        self.dead = False
        self.ended = False
        self.in_string = False

    def allowed(self) -> FrozenSet[str]:
        if self.dead or self.ended:
            return frozenset()
        if self.n >= MAX_LEN:
            return frozenset({EOS}) if not self.stack and not self.in_string else frozenset()
        out = set(t for t in self.base if t not in CLOSE)
        if not self.stack or self.stack[-1] != "Φ⟨":
            out -= DIGITS                       # digits only inside a fractal sequence Φ⟨1:2:3⟩, never amounts
        if self.stack:
            out.add(OPEN[self.stack[-1]])
        elif self.n > 0 and not self.in_string:
            out.add(EOS)
        return frozenset(out)

    def step(self, tok: str) -> None:
        if tok not in self.allowed():
            self.dead = True
            return
        if tok == EOS:
            self.ended = True
            return
        self.n += 1
        if tok == '"':
            self.in_string = not self.in_string
        elif tok in OPEN:
            self.stack.append(tok)
        elif tok in CLOSE:
            self.stack.pop()


def render(tokens: Sequence[str], fill: Dict[str, str]) -> str:
    """Compiler source text. Slot tags are replaced by `fill[tag]` (the user's own span)."""
    out: List[str] = []
    for i, t in enumerate(tokens):
        s = fill[t] if t in fill else t
        if t in SPACED:
            out.append(" " + s + " ")
        elif t == ",":
            out.append(", ")
        elif t == ";":
            out.append("; ")
        elif t in WORDS:
            out.append(s + " ")
        else:
            out.append(s)
    text = "".join(out)
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()
