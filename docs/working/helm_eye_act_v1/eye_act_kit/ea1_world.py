"""EYE-ACT-1 exam worlds and plants (PREREGISTRATION_EYE_ACT_V1.precode.md section 2). Standard library only.

A world is a seeded script of plain-English turns for the live loop, with made-up words only:
  teaching turns (one per support ingredient: that ingredient runs out first), one stock turn, probe P1, [plant],
  probe P2, three "Thanks." turns, probe P3.
Every number is an exact integer in cups; the stock is chosen so ONE ingredient limits (a strict minimum), so every
plant changes the unbroken answer (no VOID by construction; the runner still checks it).
"""
from __future__ import annotations

import hashlib
import random
from fractions import Fraction
from typing import Any, Dict, List

KINDS = ("CLEAN", "F1_TAMPER_COEFF", "F2_TAMPER_STOCK", "F3_SLIPPED_LESSON", "F4_LOST_SOURCE")
ONSET = ("b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "br", "gl", "pr", "sk", "tr", "zw")
NUCLEUS = ("a", "e", "i", "o", "u", "ai", "ou", "ee")
CODA = ("", "n", "m", "r", "l", "sh", "k", "x")
THANKS = "Thanks."


def rng_for(seed_text: str) -> random.Random:
    return random.Random(int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16))


def made_up_word(rng: random.Random, taken: set) -> str:
    while True:
        w = "".join(rng.choice(ONSET) + rng.choice(NUCLEUS) for _ in range(rng.choice((1, 2)))) + rng.choice(CODA)
        if 4 <= len(w) <= 9 and w not in taken:
            taken.add(w)
            return w


def cups(n: int) -> str:
    return "%d cup%s" % (n, "" if n == 1 else "s")


def make_world(seed_text: str, kind: str) -> Dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(kind)
    rng = rng_for(seed_text)
    taken: set = set()
    product = made_up_word(rng, taken)
    k = rng.choice((2, 3))
    ings = [made_up_word(rng, taken) for _ in range(k)]
    a = {n: rng.randint(1, 4) for n in ings}
    teach = []
    for r in ings:                                   # one batch per ingredient; r runs out, every other has spare
        m = rng.randint(1, 4)
        amounts = {n: (m * a[n] if n == r else m * a[n] + rng.randint(1, 3)) for n in ings}
        parts = ["%s %s" % (cups(amounts[n]), n) for n in ings]
        teach.append("We made %d batch%s of %s from %s, and the %s ran out first."
                     % (m, "" if m == 1 else "es", product, " and ".join([", ".join(parts[:-1]), parts[-1]])
                        if len(parts) > 2 else " and ".join(parts), r))
    while True:                                      # a strict single limiting ingredient
        stock = {n: rng.randint(5, 40) for n in ings}
        ratios = {n: Fraction(stock[n], a[n]) for n in ings}
        low = min(ratios.values())
        lim = [n for n in ings if ratios[n] == low]
        if len(lim) == 1:
            break
    sparts = ["%s %s" % (cups(stock[n]), n) for n in ings]
    stock_turn = "We have %s." % (" and ".join([", ".join(sparts[:-1]), sparts[-1]]) if len(sparts) > 2
                                  else " and ".join(sparts))
    ask = "How many %s can we make?" % product
    turns = teach + [stock_turn, ask, ask, THANKS, THANKS, THANKS, ask]
    p1 = len(teach) + 1                              # index of P1 in turns (0-based)
    return {"seed": seed_text, "kind": kind, "product": product, "ingredients": ings,
            "requirements": {n: a[n] for n in ings}, "stock": stock, "limiting": lim[0],
            "key_value": str(low), "turns": turns, "probes": {"P1": p1, "P2": p1 + 1, "P3": p1 + 5},
            "plant_after": p1}


# ===================================================================== plants (out of band, between P1 and P2)
def plant(loop: Any, world: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the world's fault to the live loop. Returns a record of what was changed. F3 is a write through the book's
    writer with its conflict refusal and memory check bypassed for that one write (its row is logged admitted)."""
    kind, p, c = world["kind"], world["product"], world["limiting"]
    book = loop.wide_book
    if kind == "CLEAN":
        return {"kind": kind}
    if kind in ("F1_TAMPER_COEFF", "F4_LOST_SOURCE"):
        old = book.recipes[p]["a"][c]
        book.recipes[p]["a"][c] = old * 2
        rec = {"kind": kind, "cell": c, "old": str(old), "new": str(old * 2)}
        if kind == "F4_LOST_SOURCE":
            before = len(book.witness_log)
            book.witness_log[:] = [w for w in book.witness_log if w.get("ran_out") != [c]]
            book.recipes[p]["lessons"][:] = [x for x in book.recipes[p]["lessons"] if x.get("ran_out") != c]
            rec["rows_deleted"] = before - len(book.witness_log)
        return rec
    if kind == "F2_TAMPER_STOCK":
        q, u = loop.wide_stock[c]
        loop.wide_stock[c] = (q / 2, u)
        return {"kind": kind, "ingredient": c, "old": str(q), "new": str(q / 2)}
    if kind == "F3_SLIPPED_LESSON":
        r = book.recipes[p]
        old = r["a"][c]
        new = old * 2
        book._seed += 1
        base = {n: (str(new) if n == c else str(r["a"][n] * 2 + 1)) for n in r["support"]}
        r["a"][c] = new
        r["lessons"].append({"seed": book._seed, "made": "1", "ran_out": c, "stock_base": dict(base)})
        book.witness_log.append({"seed": book._seed, "product": p, "made": "1", "ran_out": [c],
                                 "stock_before": {n: [v, "cup"] for n, v in base.items()},
                                 "admitted": True, "reason": "ADMITTED"})
        return {"kind": kind, "cell": c, "old": str(old), "new": str(new), "write": True}
    raise ValueError(kind)


def scored_seed(owner_line: str, zip_sha256: str, kind: str, i: int) -> str:
    """Pre-registration section 7: neither the operator nor the builder picks the scored worlds."""
    return hashlib.sha256(("%s:%s:%s:%d" % (owner_line, zip_sha256, kind, i)).encode("utf-8")).hexdigest()
