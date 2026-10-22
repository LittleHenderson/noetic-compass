"""The A-world target language: grammar, prefix automaton (for the grammar lock), parser and builder. Stdlib only.

    target := ANSWER item+ | WITNESS Ω_ N MADE Q wstock+ RAN_OUT Ω_ N | CLARIFY code arg* | NOT_MINE
    item   := STOCK Q · Ω_ R | ABSENT Ω_ R | TOPIC Ω_ R | ADD Q · Ω_ C
    wstock := STOCK Q · Ω_ N           R := N | C       arg := N | Q | C (at most 4)
    Q := ⟦q1⟧..⟦q16⟧   N := ⟦n1⟧..⟦n32⟧   C := ⟦c1⟧..⟦c8⟧

Frozen in PREREGISTRATION_CTT.md section 3.3. At most 12 items.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Sequence

from . import cas_vocab as cv

Q = frozenset(cv.SLOTS_Q)
N = frozenset(cv.SLOTS_N)
C = frozenset(cv.SLOTS_C)
CODES = frozenset(cv.CLARIFY_CODES)
ITEM_HEADS = frozenset({"STOCK", "ABSENT", "TOPIC", "ADD"})
EOS = "[EOS]"
MAX_ITEMS = 12
MAX_ARGS = 4

# Each item head expands to a fixed sequence of classes.
EXPAND = {
    "STOCK": ["Q", "·", "Ω_", "R"],
    "ABSENT": ["Ω_", "R"],
    "TOPIC": ["Ω_", "R"],
    "ADD": ["Q", "·", "Ω_", "C"],
}


class Automaton:
    """Prefix automaton. allowed() gives the set of next tokens (strings, EOS included when the prefix may end)."""

    def __init__(self, q_ok: FrozenSet[str] = Q, n_ok: FrozenSet[str] = N, c_ok: FrozenSet[str] = C):
        self.q_ok, self.n_ok, self.c_ok = q_ok, n_ok, c_ok
        self.mode = "START"
        self.queue: List[str] = []
        self.items = 0
        self.args = 0
        self.dead = False
        self.ended = False

    def _cls(self, name: str) -> FrozenSet[str]:
        if name == "Q":
            return self.q_ok
        if name == "N":
            return self.n_ok
        if name == "C":
            return self.c_ok
        if name == "R":
            return self.n_ok | self.c_ok
        return frozenset({name})

    def allowed(self) -> FrozenSet[str]:
        if self.dead or self.ended:
            return frozenset()
        if self.queue:
            return self._cls(self.queue[0])
        if self.mode == "START":
            return frozenset({"ANSWER", "WITNESS", "CLARIFY", "NOT_MINE"})
        if self.mode == "NOT_MINE":
            return frozenset({EOS})
        if self.mode == "CLARIFY":
            return CODES
        if self.mode == "ARGS":
            return (self.n_ok | self.q_ok | self.c_ok | {EOS}) if self.args < MAX_ARGS else frozenset({EOS})
        if self.mode == "ANSWER_FIRST":
            return ITEM_HEADS
        if self.mode == "ANSWER_MORE":
            return (ITEM_HEADS | {EOS}) if self.items < MAX_ITEMS else frozenset({EOS})
        if self.mode == "W_FIRST":
            return frozenset({"STOCK"})
        if self.mode == "W_MORE":
            return frozenset({"STOCK", "RAN_OUT"}) if self.items < MAX_ITEMS else frozenset({"RAN_OUT"})
        if self.mode == "W_END":
            return frozenset({EOS})
        return frozenset()

    def step(self, tok: str) -> None:
        if tok not in self.allowed():
            self.dead = True
            return
        if tok == EOS:
            self.ended = True
            return
        if self.queue:
            self.queue.pop(0)
            if not self.queue and self.mode == "W_HEAD":
                self.mode = "W_FIRST"
            return
        m = self.mode
        if m == "START":
            if tok == "ANSWER":
                self.mode = "ANSWER_FIRST"
            elif tok == "WITNESS":
                self.mode = "W_HEAD"
                self.queue = ["Ω_", "N", "MADE", "Q"]
            elif tok == "CLARIFY":
                self.mode = "CLARIFY"
            else:
                self.mode = "NOT_MINE"
        elif m == "CLARIFY":
            self.mode = "ARGS"
        elif m == "ARGS":
            self.args += 1
        elif m in ("ANSWER_FIRST", "ANSWER_MORE"):
            self.items += 1
            self.mode = "ANSWER_MORE"
            self.queue = list(EXPAND[tok])
        elif m in ("W_FIRST", "W_MORE"):
            if tok == "STOCK":
                self.items += 1
                self.mode = "W_MORE"
                self.queue = ["Q", "·", "Ω_", "N"]
            else:
                self.mode = "W_END"
                self.queue = ["Ω_", "N"]


def is_complete(tokens: Sequence[str]) -> bool:
    a = Automaton()
    for t in list(tokens) + [EOS]:
        a.step(t)
        if a.dead:
            return False
    return a.ended


def parse(tokens: Sequence[str]) -> Optional[Dict[str, object]]:
    """Structured target, or None if the sequence is not in the grammar. Slot tags are kept as tags."""
    toks = list(tokens)
    if not is_complete(toks):
        return None
    head = toks[0]
    if head == "NOT_MINE":
        return {"kind": "NOT_MINE"}
    if head == "CLARIFY":
        return {"kind": "CLARIFY", "code": toks[1], "args": toks[2:]}
    if head == "WITNESS":
        out = {"kind": "WITNESS", "product": toks[2], "made": toks[4], "stocks": [], "ran_out": toks[-1]}
        i = 5
        while toks[i] == "STOCK":
            out["stocks"].append((toks[i + 1], toks[i + 4]))
            i += 5
        return out
    items, i = [], 1
    while i < len(toks):
        h = toks[i]
        if h == "STOCK":
            items.append({"op": "STOCK", "q": toks[i + 1], "ref": toks[i + 4]})
            i += 5
        elif h == "ADD":
            items.append({"op": "ADD", "q": toks[i + 1], "ref": toks[i + 4]})
            i += 5
        else:
            items.append({"op": h, "ref": toks[i + 2]})
            i += 3
    return {"kind": "ANSWER", "items": items}


def build(struct: Dict[str, object]) -> List[str]:
    """Inverse of parse (used by the data builder). parse(build(s)) == s is tested."""
    k = struct["kind"]
    if k == "NOT_MINE":
        return ["NOT_MINE"]
    if k == "CLARIFY":
        return ["CLARIFY", struct["code"]] + list(struct.get("args") or [])
    if k == "WITNESS":
        out = ["WITNESS", "Ω_", struct["product"], "MADE", struct["made"]]
        for q, n in struct["stocks"]:
            out += ["STOCK", q, "·", "Ω_", n]
        return out + ["RAN_OUT", "Ω_", struct["ran_out"]]
    out = ["ANSWER"]
    for it in struct["items"]:
        if it["op"] in ("STOCK", "ADD"):
            out += [it["op"], it["q"], "·", "Ω_", it["ref"]]
        else:
            out += [it["op"], "Ω_", it["ref"]]
    return out
