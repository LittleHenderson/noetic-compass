"""EYE-ACT-1: the Unity Eye ACTING inside the live HELM loop (switch HELM_EYE_ACT, default OFF).

Pre-registration: docs/working/helm_eye_act_v1/PREREGISTRATION_EYE_ACT_V1.precode.md (sha256 0d731774..., written and
hashed before this file), amendment A1 (the stock source). Owner's word (2026-10-21): "want the Eye to act inside real
HELM, GO!". Status: ENGINEERED-NOT-VALIDATED until the sealed exam reads; the Eye's acting stays NOT LICENSED (spec 7.38).

What the Eye may do, and nothing else (the involuntary rule, U1/U1b):
  * READ (a sweep): re-derive the wide book from the user's own witnessed batches with the book's own writer, and fold
    the verified stock from the loop's own trace; compare with the live state. A sweep changes nothing.
  * ACT (modes ACT / CONCERT): put back a re-derived state through the loop's routines (eye_restore_book /
    eye_restore_stock), ledgered as AUTONOMIC with its trigger and the digests before and after. It never adds a fact,
    a number, a recipe or a capacity: where the sources support nothing, the value stays unlearned and HELM asks.
  * HOLD (every mode): a question that would use a flagged object is held; HELM says what failed and asks.
  * CONCERT: before every question the loop REQUESTS a look and the Eye REPLIES in the same turn.

Watched in v1: the wide book (loop.wide_book) and the wide stock (loop.wide_stock) only. Standard library, exact
Fractions, 0 learned parameters.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

MODES = ("HOLD", "ACT", "CONCERT")
SWEEP_EVERY = 4                 # pre-registration 1.3: a sweep at the first turn, then after every 4 turns
HOLD_STATUS = "CLARIFY_EYE_HOLD"
VERSION = "eye_act_v1"


def mode_from(word: Any) -> Optional[str]:
    """`HOLD` / `ACT` / `CONCERT` (any case) turn the Eye on in that mode; anything else is OFF (None)."""
    if not isinstance(word, str):
        return None
    w = word.strip().upper()
    return w if w in MODES else None


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def _stock_text(stock: Dict[str, Tuple[Any, str]]) -> Dict[str, List[Optional[str]]]:
    return {n: [None if q is None else str(Fraction(q)), u] for n, (q, u) in sorted(stock.items())}


# ===================================================================== the sources (the user's own words only)
def rederive_book(book: Any) -> Any:
    """A FRESH wide book from the live book's witness log, replayed in order by the book's own writer (the same steps
    as WideRecipeBook.replay, which returns only a digest). Rows the writer refuses stay refused."""
    import helm_brain_wide as W
    fresh = W.WideRecipeBook()
    for row in book.witness_log:
        stock = {k: ((Fraction(v[0]) if v[0] is not None else None), v[1]) for k, v in row["stock_before"].items()}
        fresh.witness(row["product"], stock, Fraction(row["made"]) if row.get("made") else 0, row["ran_out"])
    return fresh


def verified_stock(loop: Any) -> Dict[str, Tuple[Optional[Fraction], str]]:
    """Amendment A1: a fold over the loop's own trace in tick order.
    (1) a tick that ended STOCK_RECORDED: the `stock_on_hand (wide)` record at that tick (the full held stock);
    (2) `stock_withdrawn (wide)`: drop the named ingredients;
    (3) a tick that ended INVENTORY_RECORDED (the licensed path took the stock): HELM's own reader on that tick's user
        text. Question-time `stock_on_hand (wide)` records are never a source."""
    import helm_wide_turn as WT
    status: Dict[int, str] = {}
    user_text: Dict[int, str] = {}
    for r in loop.trace:
        if r.get("station") == "S6 next":
            status[r["tick"]] = r.get("loop_status")
        elif r.get("station") == "user" and "text" in r and r["tick"] not in user_text:
            user_text[r["tick"]] = r["text"]
    held: Dict[str, Tuple[Optional[Fraction], str]] = {}
    last_tick = None
    for r in loop.trace:
        t = r.get("tick")
        if r.get("station") == "S2 Bias ^5" and r.get("what") == "stock_on_hand (wide)" \
                and status.get(t) == "STOCK_RECORDED":
            held = {n: ((Fraction(v[0]) if v[0] is not None else None), v[1]) for n, v in r["stock"].items()}
        elif r.get("station") == "S2 Bias ^5" and r.get("what") == "stock_withdrawn (wide)":
            for n in r.get("withdrawn", []):
                held.pop(n, None)
        elif r.get("station") == "S6 next" and r.get("loop_status") in WT.STOCK_DONE and t != last_tick:
            last_tick = t
            reading = WT.read_wide(user_text.get(t, ""))
            if reading.get("status") == "STOCK":
                held.update(reading["stock"])
    return held


# ===================================================================== the Eye
class UnityEyeAct:
    """One Eye per loop. Its only store is its own append-only ledger."""

    def __init__(self, mode: str):
        if mode not in MODES:
            raise ValueError("unknown Eye mode: %r" % (mode,))
        self.mode = mode
        self.ledger: List[Dict[str, Any]] = []
        self.turns_since_sweep: Optional[int] = None
        self.flags: Dict[str, Dict[str, Any]] = {}      # object -> finding still unresolved (held)

    # ------------------------------------------------------------- ledger
    def _log(self, kind: str, tick: int, **fields: Any) -> Dict[str, Any]:
        e = {"kind": kind, "tick": tick, "seq": len(self.ledger)}
        e.update(fields)
        e = json.loads(_canon(e))
        self.ledger.append(e)
        return e

    def bytes_held(self) -> int:
        return len(_canon(self.ledger).encode("utf-8"))

    # ------------------------------------------------------------- the read
    def sweep(self, loop: Any, tick: int, why: str = "CADENCE") -> Dict[str, Any]:
        """Re-derive and compare. Changes nothing in the loop (only the Eye's ledger grows)."""
        book = loop.wide_book
        live_stock = dict(getattr(loop, "wide_stock", {}) or {})
        before = (book.learned_digest(), _sha(_stock_text(live_stock)), loop._store_writes())
        findings: List[Dict[str, Any]] = []
        fresh = rederive_book(book)
        if fresh.learned_digest() != book.learned_digest():
            cells = []
            for p in sorted(set(book.recipes) | set(fresh.recipes)):
                a_live = (book.recipes.get(p) or {}).get("a", {})
                a_src = (fresh.recipes.get(p) or {}).get("a", {})
                for n in sorted(set(a_live) | set(a_src)):
                    if a_live.get(n) != a_src.get(n):
                        cells.append({"product": p, "ingredient": n,
                                      "live": None if a_live.get(n) is None else str(a_live.get(n)),
                                      "source": None if a_src.get(n) is None else str(a_src.get(n))})
            findings.append({"code": "BOOK_DIFFERS", "object": "book", "cells": cells,
                             "live_digest": book.learned_digest(), "source_digest": fresh.learned_digest()})
        vs = verified_stock(loop)
        for n in sorted(set(live_stock) | set(vs)):
            if n not in vs:
                findings.append({"code": "SOURCE_MISSING", "object": "stock:" + n, "ingredient": n,
                                 "live": _stock_text({n: live_stock[n]})[n]})
            elif n not in live_stock or tuple(live_stock[n]) != tuple(vs[n]):
                findings.append({"code": "STOCK_DIFFERS", "object": "stock:" + n, "ingredient": n,
                                 "live": _stock_text({n: live_stock[n]})[n] if n in live_stock else None,
                                 "source": _stock_text({n: vs[n]})[n]})
        after = (book.learned_digest(), _sha(_stock_text(dict(getattr(loop, "wide_stock", {}) or {}))),
                 loop._store_writes())
        self.turns_since_sweep = 0
        rep = {"tick": tick, "why": why, "findings": findings, "pure": before == after,
               "fresh": fresh, "verified_stock": vs}
        self._log("SWEEP", tick, why=why, findings=[{k: v for k, v in f.items()} for f in findings],
                  pure=before == after, live_digest=before[0])
        return rep

    # ------------------------------------------------------------- the act
    def act(self, loop: Any, rep: Dict[str, Any], tick: int) -> None:
        """HOLD: flag every finding. ACT / CONCERT: restore BOOK_DIFFERS and STOCK_DIFFERS through the loop's routines,
        then re-check; SOURCE_MISSING is always held, never removed (amendment A1)."""
        live_objects = set()
        for f in rep["findings"]:
            live_objects.add(f["object"])
            if self.mode == "HOLD" or f["code"] == "SOURCE_MISSING":
                self.flags[f["object"]] = f
                continue
            if f["code"] == "BOOK_DIFFERS":
                d0 = loop.wide_book.learned_digest()
                loop.eye_restore_book(rep["fresh"], tick)
                d1 = loop.wide_book.learned_digest()
                ok = d1 == rederive_book(loop.wide_book).learned_digest() == f["source_digest"]
                self._log("AUTONOMIC", tick, action="RESTORE_BOOK", trigger="BOOK_DIFFERS", cells=f["cells"],
                          digest_before=d0, digest_after=d1, verified=ok)
                if not ok:
                    self.flags["book"] = f
                else:
                    self.flags.pop("book", None)
            elif f["code"] == "STOCK_DIFFERS":
                n = f["ingredient"]
                s0 = _sha(_stock_text(dict(loop.wide_stock)))
                loop.eye_restore_stock(n, rep["verified_stock"].get(n), tick)
                s1 = _sha(_stock_text(dict(loop.wide_stock)))
                ok = tuple(loop.wide_stock.get(n, ())) == tuple(rep["verified_stock"].get(n, ()))
                self._log("AUTONOMIC", tick, action="RESTORE_STOCK", trigger="STOCK_DIFFERS", ingredient=n,
                          digest_before=s0, digest_after=s1, verified=ok)
                if not ok:
                    self.flags[f["object"]] = f
                else:
                    self.flags.pop(f["object"], None)
        for obj in list(self.flags):               # a held object the latest sweep no longer finds is cleared
            if obj not in live_objects:
                self._log("CLEARED", tick, object=obj)
                self.flags.pop(obj)

    # ------------------------------------------------------------- the turn hook (called by the loop)
    def before_turn(self, loop: Any, text: str, tick: int) -> Optional[Tuple[str, str]]:
        """Runs before the loop handles a turn. Returns (status, message) to hold the turn, or None to let it run."""
        import helm_wide_turn as WT
        is_question = WT.read_wide(text.strip(), last_topic=loop.last_topic).get("status") == "QUESTION"
        due = self.turns_since_sweep is None or self.turns_since_sweep >= SWEEP_EVERY
        if self.mode == "CONCERT" and is_question:
            self._log("REQUEST", tick, what="look at the objects this answer will use")
            rep = self.sweep(loop, tick, why="REQUEST")
            self.act(loop, rep, tick)
            self._log("REPLY", tick, findings=len(rep["findings"]), held=sorted(self.flags))
        elif due:
            rep = self.sweep(loop, tick, why="CADENCE")
            self.act(loop, rep, tick)
        self.turns_since_sweep = (self.turns_since_sweep or 0) + 1
        if is_question and self.flags:
            held = sorted(self.flags)
            self._log("HOLD", tick, held=held)
            names = sorted({f.get("ingredient") or "the recipe book" for f in self.flags.values()})
            what = " and ".join(names) if len(names) < 3 else ", ".join(names[:-1]) + " and " + names[-1]
            return (HOLD_STATUS, "Before I work that out: something I hold about %s failed my own check, so I won't "
                                 "count on it. Please tell me again how things stand. I didn't guess." % what)
        return None
