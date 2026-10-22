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
LEAN_TEMPLATE = 2               # A-TEACH2-10: the sentence from the FIRST 8 clue words (template 1: from all of them;
                                # the same sentence for 8 words or fewer). A new template needs a new number.
SENTENCE_WORDS = 8              # helm_memory_compact.MAX_CLUES
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
    def _sentence(frames: List[int], clues: List[str], template: int = LEAN_TEMPLATE) -> str:
        import helm_memory_compact as hmc
        idea = " ".join(clues if template == 1 else clues[:SENTENCE_WORDS]).replace('"', "")
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
        if row.get("t") not in (1, LEAN_TEMPLATE):
            return None
        try:
            cid = row["id"]
            n0 = row.get("n0", len(row["c"]))
            frames = [int(n) for n in row["n"]]
            sentence = self._sentence(frames, row["c"][:n0], row["t"])
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


FOLD_SIZE = 8                   # A-TEACH2-9 F1/F2: 8 rows fold into one (8 capsules = one Atlas thread node)
FOLD_WORD_CAP = 48              # A-TEACH2-9 F3: clue words kept per folded row; the rest stay in the fold record


class LeanCapsules:
    """The compactor's capsule list on the size-limit path, run by the Eye.

    Working memory holds, per capsule position: a lean record (or a full capsule the Eye refused to shrink), or, once the
    Eye moved the capsule off (A-TEACH2-8), an index row (name, clue words, 16 receipt characters). Old index rows are
    FOLDED (A-TEACH2-9): 8 index rows -> one level-1 row, 8 level-k rows -> one level-(k+1) row; a folded row keeps at
    most 48 clue words, its line-number range and 16 characters of its fold record's sha256; the folded rows themselves
    go to `<cold>/<fold>.fold.json`. Iterating yields the capsules in working memory; any capsule is reached by name
    through `get` (device folder first, then the cloud). Every read is a rebuild plus a check; a failure is held."""

    def __init__(self, eye: CapsuleEye) -> None:
        self.eye = eye
        self._rows: Dict[int, Dict[str, Any]] = {}     # position -> {"lean"} | {"full"} | {"cold": index row}
        self._next = 0
        self._folds: List[Dict[str, Any]] = []         # folded rows in working memory, oldest first per level
        self._fold_numbers: Dict[int, int] = {}        # level -> folds made so far (names)
        self.last_status = "OK"                        # of the latest get(): OK / HELD / AWAY / MISSING

    # ---------------------------------------------------------------- names and rows
    @staticmethod
    def _rid(r: Dict[str, Any]) -> str:
        if "lean" in r:
            return r["lean"]["id"]
        if "full" in r:
            return r["full"]["capsule_id"]
        return r["cold"]["id"]

    def _pos(self, capsule_id: str) -> int:
        for p, r in self._rows.items():
            if self._rid(r) == capsule_id:
                return p
        return -1

    def ids(self) -> List[str]:
        """Names of the capsules that have a row in working memory (not the folded ones)."""
        return [self._rid(self._rows[p]) for p in sorted(self._rows)]

    def cold_ids(self) -> List[str]:
        return [self._rid(self._rows[p]) for p in sorted(self._rows) if "cold" in self._rows[p]]

    def index_rows(self) -> List[Dict[str, Any]]:
        return [self._rows[p]["cold"] for p in sorted(self._rows) if "cold" in self._rows[p]]

    def fold_rows(self) -> List[Dict[str, Any]]:
        return list(self._folds)

    @staticmethod
    def _row_turns(capsule_id: str, row: Dict[str, Any]) -> List[int]:
        if "ids" in row:
            return list(row["ids"])
        if "crumb" in row:
            return list(row["crumb"]["turn_ids"])
        return CapsuleEye._id_range(capsule_id)

    def clue_index(self) -> List[Tuple[str, List[str], str]]:
        """(name, clue words, kind) for every capsule row in working memory. Folded rows are matched by `match`."""
        out = []
        for p in sorted(self._rows):
            r = self._rows[p]
            if "lean" in r:
                out.append((r["lean"]["id"], r["lean"]["c"], r["lean"].get("k", "statement")))
            elif "full" in r:
                out.append((r["full"]["capsule_id"], r["full"]["clues"], r["full"].get("kind", "statement")))
            else:
                out.append((r["cold"]["id"], r["cold"]["c"], r["cold"].get("k", "statement")))
        return out

    def turn_ids_of(self, capsule_id: str) -> List[int]:
        p = self._pos(capsule_id)
        if p >= 0:
            r = self._rows[p]
            return self._row_turns(capsule_id, r.get("lean") or r.get("cold") or r["full"])
        leaf = self._leaf_for(capsule_id)
        return self._row_turns(capsule_id, leaf) if leaf else []

    def record_path(self, capsule_id: str) -> str:
        return os.path.join(self.eye.comp.cold_dir, f"{capsule_id}.lean.json")

    def fold_record_path(self, fold_name: str) -> str:
        return os.path.join(self.eye.comp.cold_dir, f"{fold_name}.fold.json")

    # ---------------------------------------------------------------- shrink, store, hold
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
        self._rows[self._next] = self._lean_or_full(cap, self._next, "SHRINK")
        self._next += 1

    def store(self, cap: Any) -> None:
        """Write a changed capsule back into working memory (strengthening appends clues and mass; its content never
        changes). A moved or folded capsule comes back; its device copy of the record is removed (the cloud keeps its
        copy; a fold record keeps listing it, and `get` looks in working memory first)."""
        p = self._pos(cap.capsule_id)
        if p >= 0:
            was_cold = "cold" in self._rows[p]
        else:
            leaf = self._leaf_for(cap.capsule_id)
            if leaf is None:
                return
            p, was_cold = int(leaf["i"]), True
        self._rows[p] = self._lean_or_full(cap, p, "STORE")
        if was_cold:
            path = self.record_path(cap.capsule_id)
            if os.path.isfile(path):
                os.remove(path)
            self.eye.comp.moved_records.pop(cap.capsule_id, None)
            self.eye._log("MOVE_BACK", cap.capsule_id)

    def _hold(self, name: str, row: Any) -> None:
        self.last_status = "HELD"
        if name not in self.eye.held:
            self.eye.held.add(name)
            self.eye._log("HOLD", name, digest=_sha(row))
            self.eye.comp._flag("LEAN_REBUILD_MISMATCH", "a record does not match what working memory kept; held", name)

    def _capsule_from_record(self, rec: Dict[str, Any], i: int, capsule_id: str) -> Any:
        if "id" in rec:                                 # a lean record
            cap = self.eye.rebuild(rec, i)
            if cap is None or not self.eye.matches_receipt(cap):
                self._hold(capsule_id, rec)
                return None
            return cap
        return self._full_from(rec)                     # a full capsule the Eye refused to shrink

    def _get(self, p: int) -> Any:
        r = self._rows[p]
        if "full" in r:
            return self._full_from(r["full"])
        return self._capsule_from_record(r["lean"], p, r["lean"]["id"])

    # ---------------------------------------------------------------- reading files back (device, then cloud)
    def _read(self, path: str, key: Optional[str]) -> Optional[bytes]:
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                return fh.read()
        if key is None:
            self.last_status = "MISSING"
            return None
        comp = self.eye.comp
        try:
            data = comp.cloud.get(key) if comp.cloud is not None else None
        except Exception:
            data = None
        if data is None:
            self.last_status = "AWAY"
        return data

    def load_fold(self, fold_name: str, row: Optional[Dict[str, Any]] = None,
                  device_only: bool = False) -> Optional[Dict[str, Any]]:
        """A fold record, checked against the 16 characters its row kept. None when held, away or missing."""
        import helm_memory_compact as hmc
        row = row or next((r for r in self._folds if r["f"] == fold_name), None)
        if row is None:
            self.last_status = "MISSING"
            return None
        path = self.fold_record_path(fold_name)
        key = None if device_only else self.eye.comp.moved_folds.get(fold_name)
        data = self._read(path, key)
        if data is None:
            return None
        try:
            rec = json.loads(data.decode("utf-8"))
        except ValueError:
            rec = None
        if rec is None or hmc._sha(data)[:16] != row["q"] or rec.get("f") != fold_name:
            self._hold(fold_name, row)
            return None
        return rec

    def _leaves(self, fold_row: Dict[str, Any], want: Any, away: List[str], device_only: bool = False):
        """Index rows inside a folded row, opening only the folded rows `want(row)` accepts."""
        rec = self.load_fold(fold_row["f"], fold_row, device_only=device_only)
        if rec is None:
            if self.last_status == "AWAY":
                away.append(fold_row["f"])
            return
        for m in rec["members"]:
            if "f" in m:
                if want(m):
                    yield from self._leaves(m, want, away, device_only)
            else:
                yield m

    def _leaf_for(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        first = CapsuleEye._id_range(capsule_id)[0]
        away: List[str] = []
        for fr in self._folds:
            if fr["t"][0] <= first <= fr["t"][1]:
                for leaf in self._leaves(fr, lambda m: m["t"][0] <= first <= m["t"][1], away):
                    if leaf["id"] == capsule_id:
                        return leaf
        if away:
            self.last_status = "AWAY"
        return None

    def find_by_turn(self, turn_id: int) -> Optional[str]:
        """The name of the capsule holding a line number: rows in working memory first, then the folded rows."""
        for p in sorted(self._rows):
            r = self._rows[p]
            cid = self._rid(r)
            if turn_id in self._row_turns(cid, r.get("lean") or r.get("cold") or r["full"]):
                return cid
        away: List[str] = []
        for fr in self._folds:
            if fr["t"][0] <= turn_id <= fr["t"][1]:
                for leaf in self._leaves(fr, lambda m: m["t"][0] <= turn_id <= m["t"][1], away):
                    if turn_id in self._row_turns(leaf["id"], leaf):
                        return leaf["id"]
        if away:
            self.last_status = "AWAY"
        return None

    def match(self, tokens: set) -> Tuple[List[str], bool, bool]:
        """A-TEACH2-9 F5: names of statement capsules whose clue words hold every question word, from the rows in
        working memory, then the folded rows that hold every word, then (only if nothing matched) a deep search of the
        fold records on the device. Returns (names, any_away, deep)."""
        found = [cid for cid, clues, kind in self.clue_index() if kind == "statement" and tokens <= set(clues)]
        away: List[str] = []
        hot = set(self.ids())
        holds = (lambda m: tokens <= set(m["c"]))
        for fr in self._folds:
            if holds(fr):
                found += [leaf["id"] for leaf in self._leaves(fr, holds, away)
                          if leaf.get("k", "statement") == "statement" and holds(leaf) and leaf["id"] not in hot]
        deep = False
        if not found:
            deep = True
            for fr in self._folds:
                found += [leaf["id"] for leaf in self._leaves(fr, lambda m: True, [], device_only=True)
                          if leaf.get("k", "statement") == "statement" and holds(leaf) and leaf["id"] not in hot]
        if not found and self._folds and self.eye.comp.moved_folds:
            # A-TEACH2-11: nothing in working memory or on the device; read the fold records in the cloud when it can be
            # reached (each read checked by load_fold; nothing kept). Offline: say the notes are stored away.
            cloud = self.eye.comp.cloud
            try:
                reachable = cloud is not None and bool(cloud.available())
            except Exception:
                reachable = False
            if reachable:
                for fr in self._folds:
                    found += [leaf["id"] for leaf in self._leaves(fr, lambda m: True, away)
                              if leaf.get("k", "statement") == "statement" and holds(leaf) and leaf["id"] not in hot]
            else:
                away.append("cloud")
        seen: set = set()
        names = [c for c in found if not (c in seen or seen.add(c))]
        return names, bool(away), deep

    def get(self, capsule_id: str, record_only: bool = False) -> Any:
        """One capsule by name: rebuilt from working memory, or fetched back (device folder, then the cloud) and checked
        against its index row and its receipt. None when held, unreachable or missing (see `last_status`)."""
        self.last_status = "OK"
        p = self._pos(capsule_id)
        if p >= 0:
            r = self._rows[p]
            if "cold" not in r:
                if record_only:
                    return r.get("lean") or r.get("full")
                return self._get(p)
            idx, i = r["cold"], p
        else:
            idx = self._leaf_for(capsule_id)
            if idx is None:
                if self.last_status == "OK":
                    self.last_status = "MISSING"
                return None
            i = int(idx["i"])
        self.last_status = "OK"
        data = self._read(self.record_path(capsule_id), self.eye.comp.moved_records.get(capsule_id))
        if data is None:
            return None
        try:
            rec = json.loads(data.decode("utf-8"))
        except ValueError:
            self._hold(capsule_id, idx)
            return None
        rid = rec.get("id", rec.get("capsule_id"))
        clues = rec.get("c", rec.get("clues"))
        receipt = str(rec.get("r", rec.get("receipt", "")))
        if rid != capsule_id or clues != idx["c"] or not receipt.startswith(idx["q"]):
            self._hold(capsule_id, idx)
            return None
        if record_only:
            return rec
        return self._capsule_from_record(rec, i, capsule_id)

    # ---------------------------------------------------------------- moving off (A-TEACH2-8)
    def move_off(self, capsule_id: str) -> bool:
        """Write the record to the device folder, read it back byte for byte, then keep only an index row."""
        import helm_memory_compact as hmc
        p = self._pos(capsule_id)
        r = self._rows[p]
        if "cold" in r:
            return True
        rec = r.get("lean") or r["full"]
        lean = "lean" in r
        idx: Dict[str, Any] = {"id": capsule_id, "c": list(rec["c"] if lean else rec["clues"]),
                               "q": str(rec["r"] if lean else rec["receipt"])[:16]}
        kind = rec.get("k") if lean else rec.get("kind")
        if kind and kind != "statement":
            idx["k"] = kind
        ids = rec.get("ids") if lean else rec["crumb"]["turn_ids"]
        if ids and list(ids) != CapsuleEye._id_range(capsule_id):
            idx["ids"] = list(ids)
        if not self._write(self.record_path(capsule_id), hmc._canon(rec)):
            self.eye._log("MOVE_OFF_FAILED", capsule_id, digest=_sha(rec))
            return False
        self._rows[p] = {"cold": idx}
        self.eye._log("MOVE_OFF", capsule_id, digest=_sha(rec), index_digest=_sha(idx))
        return True

    @staticmethod
    def _write(path: str, payload: bytes) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(payload)
            with open(path, "rb") as fh:
                return fh.read() == payload
        except OSError:
            return False

    def move_off_oldest_until(self, done: Any) -> None:
        """Move the oldest capsules still in working memory off it until `done()` or none is left."""
        for cid in [self._rid(self._rows[p]) for p in sorted(self._rows) if "cold" not in self._rows[p]]:
            if done():
                return
            self.move_off(cid)

    # ---------------------------------------------------------------- folding (A-TEACH2-9)
    @staticmethod
    def _capped_words(members: List[Dict[str, Any]]) -> List[str]:
        count: Dict[str, int] = {}
        last: Dict[str, int] = {}
        for n, m in enumerate(members):
            for w in m["c"]:
                count[w] = count.get(w, 0) + 1
                last[w] = n
        return sorted(count, key=lambda w: (-count[w], -last[w], w))[:FOLD_WORD_CAP]

    def _fold(self, level: int, members: List[Dict[str, Any]]) -> bool:
        import helm_memory_compact as hmc
        number = self._fold_numbers.get(level, 0) + 1
        name = f"fold-{level}-{number:04d}"
        if level == 1:
            spans = [self._row_turns(m["id"], m) for m in members]
            t = [min(s[0] for s in spans), max(s[-1] for s in spans)]
        else:
            t = [min(m["t"][0] for m in members), max(m["t"][1] for m in members)]
        payload = hmc._canon({"f": name, "lv": level, "members": members})
        if not self._write(self.fold_record_path(name), payload):
            self.eye._log("FOLD_FAILED", name, level=level)
            return False
        row = {"f": name, "lv": level, "c": self._capped_words(members), "t": t, "q": hmc._sha(payload)[:16]}
        self._fold_numbers[level] = number
        self._folds.append(row)
        self.eye._log("FOLD", name, level=level, members=len(members), digest=hmc._sha(payload))
        return True

    def fold_once(self) -> bool:
        """Fold the oldest 8 index rows into a level-1 row; else the oldest 8 rows of the lowest level that has 8."""
        cold = [p for p in sorted(self._rows) if "cold" in self._rows[p]]
        if len(cold) >= FOLD_SIZE:
            take = cold[:FOLD_SIZE]
            members = [dict(self._rows[p]["cold"], i=p) for p in take]
            if not self._fold(1, members):
                return False
            for p in take:
                del self._rows[p]
            return True
        for level in sorted({r["lv"] for r in self._folds}):
            rows = [r for r in self._folds if r["lv"] == level]
            if len(rows) >= FOLD_SIZE:
                take = rows[:FOLD_SIZE]
                if not self._fold(level + 1, take):
                    return False
                names = {r["f"] for r in take}
                self._folds = [r for r in self._folds if r["f"] not in names]
                return True
        return False

    def fold_until(self, done: Any) -> None:
        while not done():
            if not self.fold_once():
                return

    # ---------------------------------------------------------------- the list surface
    def __iter__(self):
        """The capsules with a full or lean row in working memory (others are reached by name through `get`)."""
        for p in sorted(self._rows):
            if "cold" in self._rows[p]:
                continue
            cap = self._get(p)
            if cap is not None:
                yield cap

    def __len__(self) -> int:
        return self._next

    def __bool__(self) -> bool:
        return self._next > 0

    def __getitem__(self, i: int) -> Any:
        return list(self)[i]

    def stored(self) -> List[Dict[str, Any]]:
        """What working memory holds: lean rows, full capsules the Eye refused to shrink, index rows, folded rows."""
        rows = [self._rows[p].get("lean") or self._rows[p].get("full") or self._rows[p]["cold"]
                for p in sorted(self._rows)]
        return rows + list(self._folds)

    def size_of(self, cap: Any) -> int:
        import helm_memory_compact as hmc
        return len(hmc._canon(self.eye.shrink(cap)))

    def stored_bytes(self) -> int:
        import helm_memory_compact as hmc
        return sum(len(hmc._canon(r)) for r in self.stored())
