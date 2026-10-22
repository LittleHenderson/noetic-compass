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
import os
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


# ===================================================================== the capsule watch (A-TEACH2-7)
# Owner's word (2026-10-22): "put the Eye in charge of this part ... Shrink the capsule: don't save what can be rebuilt
# ... A rebuilt capsule must match its receipt." The same Eye and the same words as above, on a second watched object:
# HELM's memory capsules on the size-limit path (HELM_CUBE_OSC with a limit; OFF by default).
#   ACT  -- shrink: store a lean record in place of the full capsule, then rebuild it at once and check its receipt;
#           a capsule that does not rebuild faithfully stays full (LEAN_REFUSED). Nothing is lost.
#   READ -- every use of a capsule rebuilds it from the lean record and checks the receipt.
#   HOLD -- a lean record whose rebuild does not match its receipt is never offered to anything (LEAN_REBUILD_MISMATCH).
# The Eye never changes a clue, a cube, a mass, a receipt or a fingerprint. Acting stays NOT LICENSED (spec 7.38).
LEAN_TEMPLATE = 1               # Compactor._sentence as built on 2026-10-21; a new template needs a new number
THREAD_SIZE = 8                 # helm_memory_compact.CAPSULES_PER_THREAD_NODE


class CapsuleEye:
    def __init__(self, comp: Any) -> None:
        self.comp = comp
        self.log: List[Dict[str, Any]] = []
        self._checks: Dict[Tuple[str, str], Tuple[bool, str, bool]] = {}   # same text -> same check result
        self.held: set = set()

    def _log(self, kind: str, capsule_id: str, **fields: Any) -> None:
        row = {"kind": kind, "capsule_id": capsule_id, "version": VERSION}
        row.update(fields)
        self.log.append(row)

    @staticmethod
    def _frames(notation: str) -> List[int]:
        return [int(part.strip()[1]) for part in notation.split("+")]

    @staticmethod
    def _id_range(capsule_id: str) -> List[int]:
        first, last = capsule_id.rsplit("-", 2)[1:]
        return list(range(int(first), int(last) + 1))

    @staticmethod
    def _sentence(frames: List[int], clues: List[str]) -> str:
        import helm_memory_compact as hmc
        idea = " ".join(clues).replace('"', "")
        return " ".join(hmc.Compactor._sentence(n, idea) for n in frames)

    def _original_clue_count(self, cap: Any) -> int:
        """How many clues the capsule had when written: its CAS sentence was made from exactly those."""
        frames = self._frames(cap.cas["notation"])
        for k in range(len(cap.clues), 0, -1):
            if self._sentence(frames, cap.clues[:k]) == cap.cas["sentence"]:
                return k
        return len(cap.clues)

    def shrink(self, cap: Any) -> Dict[str, Any]:
        """The lean record: only what cannot be rebuilt (A-TEACH2-7 E1)."""
        row: Dict[str, Any] = {"id": cap.capsule_id, "n": self._frames(cap.cas["notation"]), "t": LEAN_TEMPLATE,
                               "c": list(cap.clues), "h": cap.crumb["sha256"], "b": list(cap.binds["cubes"]),
                               "m": [cap.mass["value"], cap.mass["confirmed"]], "r": cap.receipt}
        if cap.binds.get("coefficients"):
            row["x"] = list(cap.binds["coefficients"])
        if cap.kind != "statement":
            row["k"] = cap.kind
        n0 = self._original_clue_count(cap)
        if n0 != len(cap.clues):
            row["n0"] = n0
        if list(cap.crumb["turn_ids"]) != self._id_range(cap.capsule_id):
            row["ids"] = list(cap.crumb["turn_ids"])
        return row

    def _checked(self, notation: str, sentence: str) -> Tuple[bool, str, bool]:
        import helm_memory_compact as hmc
        key = (notation, sentence)
        if key not in self._checks:
            compiles, name = hmc.Compactor._compiles(notation)
            self._checks[key] = (compiles, name, hmc.Compactor._round_trips(sentence))
        return self._checks[key]

    def rebuild(self, row: Dict[str, Any], index: int) -> Any:
        """The full capsule from a lean record (A-TEACH2-7 E2). A template other than LEAN_TEMPLATE: None."""
        import helm_memory_compact as hmc
        if row.get("t") != LEAN_TEMPLATE:
            return None
        try:
            cid = row["id"]
            n0 = row.get("n0", len(row["c"]))
            frames = [int(n) for n in row["n"]]
            sentence = self._sentence(frames, row["c"][:n0])
            notation = " + ".join(f"^{n}^{hmc.DOMAIN}" for n in frames)
            compiles, name, round_trip = self._checked(notation, sentence)
            cas = {"sentence": sentence, "notation": notation, "compiles": compiles, "round_trip": round_trip,
                   "compiler": name}
            turn_ids = list(row["ids"]) if "ids" in row else self._id_range(cid)
            crumb = {"cold_path": os.path.join(self.comp.cold_dir, f"{cid}.jsonl"), "sha256": row["h"],
                     "turn_ids": turn_ids}
            mass = {"value": row["m"][0], "confirmed": row["m"][1]}
        except (KeyError, ValueError, TypeError, IndexError):
            return None
        atlas: Dict[str, Any] = {"node": None, "node_id": None, "side": "possibility"}
        if self.comp.atlas is not None:
            atlas = {"node": f"thread-{index // THREAD_SIZE + 1:04d}", "node_id": f"capsule:{cid}",
                     "side": "possibility"}
        if mass["confirmed"] > 0:
            atlas["side"] = "fact"
            if self.comp.atlas is not None:
                atlas["fact_node_id"] = f"fact:{cid}"
        return hmc.Capsule(capsule_id=cid, cas=cas, clues=list(row["c"]),
                           binds={"cubes": list(row["b"]), "coefficients": list(row.get("x", []))},
                           crumb=crumb, mass=mass, receipt=row["r"], atlas=atlas, kind=row.get("k", "statement"))

    def matches_receipt(self, cap: Any) -> bool:
        """E3: the receipt recomputed from the capsule as it was at compaction (original clues; mass = its lines)."""
        import helm_memory_compact as hmc
        n0 = self._original_clue_count(cap)
        mass0 = {"value": len(cap.crumb["turn_ids"]), "confirmed": 0}
        if hmc._receipt_of(cap.capsule_id, cap.cas, cap.clues[:n0], cap.binds, cap.crumb, mass0) != cap.receipt:
            return False
        if cap.mass["confirmed"] == 0:
            return cap.mass == mass0 and n0 == len(cap.clues)
        # strengthened: the mass and the grown clues must be the ones its latest STRENGTHEN receipt recorded
        rows = [r for r in self.comp.receipts if r["kind"] == "STRENGTHEN" and r["capsule_id"] == cap.capsule_id]
        return bool(rows) and rows[-1]["mass"] == cap.mass and rows[-1]["clues"] == list(cap.clues)


class LeanCapsules:
    """The compactor's capsule list on the size-limit path, run by the Eye. It stores lean records (or a full capsule
    the Eye refused to shrink); every read is a rebuild plus a receipt check."""

    def __init__(self, eye: CapsuleEye) -> None:
        self.eye = eye
        self._rows: List[Dict[str, Any]] = []          # {"lean": row} or {"full": capsule dict}

    @staticmethod
    def _full_from(d: Dict[str, Any]) -> Any:
        import helm_memory_compact as hmc
        return hmc.Capsule(**json.loads(json.dumps(d)))

    def _lean_or_full(self, cap: Any, index: int, act: str) -> Dict[str, Any]:
        row = self.eye.shrink(cap)
        back = self.eye.rebuild(row, index)
        if back is not None and back.as_dict() == cap.as_dict() and self.eye.matches_receipt(back):
            self.eye._log(act, cap.capsule_id, digest=_sha(row))
            return {"lean": row}
        self.eye._log("LEAN_REFUSED", cap.capsule_id, digest=_sha(cap.as_dict()))
        return {"full": json.loads(json.dumps(cap.as_dict()))}

    def append(self, cap: Any) -> None:
        self._rows.append(self._lean_or_full(cap, len(self._rows), "SHRINK"))

    def store(self, cap: Any) -> None:
        """Write a changed capsule back (strengthening appends clues and mass; its content never changes)."""
        for i, r in enumerate(self._rows):
            rid = r["lean"]["id"] if "lean" in r else r["full"]["capsule_id"]
            if rid == cap.capsule_id:
                self._rows[i] = self._lean_or_full(cap, i, "STORE")
                return

    def _get(self, i: int) -> Any:
        r = self._rows[i]
        if "full" in r:
            return self._full_from(r["full"])
        row = r["lean"]
        cap = self.eye.rebuild(row, i)
        if cap is None or not self.eye.matches_receipt(cap):
            rid = str(row.get("id"))
            if rid not in self.eye.held:
                self.eye.held.add(rid)
                self.eye._log("HOLD", rid, digest=_sha(row))
                self.eye.comp._flag("LEAN_REBUILD_MISMATCH", "the rebuilt capsule does not match its receipt; held", rid)
            return None
        return cap

    def __iter__(self):
        for i in range(len(self._rows)):
            cap = self._get(i)
            if cap is not None:
                yield cap

    def __len__(self) -> int:
        return len(self._rows)

    def __bool__(self) -> bool:
        return bool(self._rows)

    def __getitem__(self, i: int) -> Any:
        return list(self)[i]

    def stored(self) -> List[Dict[str, Any]]:
        """The records as stored (lean rows, or the full capsules the Eye refused to shrink)."""
        return [r["lean"] if "lean" in r else r["full"] for r in self._rows]

    def size_of(self, cap: Any) -> int:
        import helm_memory_compact as hmc
        return len(hmc._canon(self.eye.shrink(cap)))

    def stored_bytes(self) -> int:
        import helm_memory_compact as hmc
        return sum(len(hmc._canon(r)) for r in self.stored())
