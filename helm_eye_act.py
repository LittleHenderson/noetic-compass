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
    """The compactor's capsule list on the size-limit path, run by the Eye. In working memory it holds lean records (or
    a full capsule the Eye refused to shrink) and, for capsules the Eye moved off (A-TEACH2-8), only an index row:
    name, clue words, the first 16 characters of the receipt. Iterating yields the capsules in working memory; a moved
    capsule is reached by `get(name)` (device folder first, then the cloud). Every read is a rebuild plus a receipt
    check; a record that fails is held."""

    def __init__(self, eye: CapsuleEye) -> None:
        self.eye = eye
        self._rows: List[Dict[str, Any]] = []          # {"lean": row} | {"full": capsule dict} | {"cold": index row}
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
        for i, r in enumerate(self._rows):
            if self._rid(r) == capsule_id:
                return i
        return -1

    def ids(self) -> List[str]:
        return [self._rid(r) for r in self._rows]

    def cold_ids(self) -> List[str]:
        return [self._rid(r) for r in self._rows if "cold" in r]

    def index_rows(self) -> List[Dict[str, Any]]:
        return [r["cold"] for r in self._rows if "cold" in r]

    def clue_index(self) -> List[Tuple[str, List[str], str]]:
        """(name, clue words, kind) for every capsule, in working memory or moved off. Nothing is fetched."""
        out = []
        for r in self._rows:
            if "lean" in r:
                out.append((r["lean"]["id"], r["lean"]["c"], r["lean"].get("k", "statement")))
            elif "full" in r:
                out.append((r["full"]["capsule_id"], r["full"]["clues"], r["full"].get("kind", "statement")))
            else:
                out.append((r["cold"]["id"], r["cold"]["c"], r["cold"].get("k", "statement")))
        return out

    def turn_ids_of(self, capsule_id: str) -> List[int]:
        r = self._rows[self._pos(capsule_id)]
        row = r.get("lean") or r.get("cold")
        if row is not None:
            return list(row["ids"]) if "ids" in row else CapsuleEye._id_range(capsule_id)
        return list(r["full"]["crumb"]["turn_ids"])

    def record_path(self, capsule_id: str) -> str:
        return os.path.join(self.eye.comp.cold_dir, f"{capsule_id}.lean.json")

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
        self._rows.append(self._lean_or_full(cap, len(self._rows), "SHRINK"))

    def store(self, cap: Any) -> None:
        """Write a changed capsule back into working memory (strengthening appends clues and mass; its content never
        changes). A moved capsule comes back; its device copy of the record is removed (the cloud never deletes)."""
        i = self._pos(cap.capsule_id)
        if i < 0:
            return
        was_cold = "cold" in self._rows[i]
        self._rows[i] = self._lean_or_full(cap, i, "STORE")
        if was_cold:
            path = self.record_path(cap.capsule_id)
            if os.path.isfile(path):
                os.remove(path)
            self.eye.comp.moved_records.pop(cap.capsule_id, None)
            self.eye._log("MOVE_BACK", cap.capsule_id)

    def _hold(self, capsule_id: str, row: Any) -> None:
        self.last_status = "HELD"
        if capsule_id not in self.eye.held:
            self.eye.held.add(capsule_id)
            self.eye._log("HOLD", capsule_id, digest=_sha(row))
            self.eye.comp._flag("LEAN_REBUILD_MISMATCH", "the rebuilt capsule does not match its receipt; held",
                                capsule_id)

    def _capsule_from_record(self, rec: Dict[str, Any], i: int, capsule_id: str) -> Any:
        if "id" in rec:                                 # a lean record
            cap = self.eye.rebuild(rec, i)
            if cap is None or not self.eye.matches_receipt(cap):
                self._hold(capsule_id, rec)
                return None
            return cap
        return self._full_from(rec)                     # a full capsule the Eye refused to shrink

    def _get(self, i: int) -> Any:
        r = self._rows[i]
        if "full" in r:
            return self._full_from(r["full"])
        return self._capsule_from_record(r["lean"], i, r["lean"]["id"])

    # ---------------------------------------------------------------- moving off and fetching back (A-TEACH2-8)
    def _load_record(self, capsule_id: str) -> Optional[bytes]:
        path = self.record_path(capsule_id)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                return fh.read()
        comp = self.eye.comp
        key = comp.moved_records.get(capsule_id)
        if key is None:
            self.last_status = "MISSING"
            return None
        try:
            data = comp.cloud.get(key) if comp.cloud is not None else None
        except Exception:
            data = None
        if data is None:
            self.last_status = "AWAY"
        return data

    def get(self, capsule_id: str, record_only: bool = False) -> Any:
        """One capsule by name: rebuilt from working memory, or fetched back (device folder, then the cloud) and checked
        against its index row and its receipt. None when held, unreachable or missing (see `last_status`)."""
        self.last_status = "OK"
        i = self._pos(capsule_id)
        if i < 0:
            self.last_status = "MISSING"
            return None
        r = self._rows[i]
        if "cold" not in r:
            if record_only:
                return r.get("lean") or r.get("full")
            return self._get(i)
        idx = r["cold"]
        data = self._load_record(capsule_id)
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

    def move_off(self, capsule_id: str) -> bool:
        """M3: write the record to the device folder, read it back byte for byte, then keep only an index row."""
        import helm_memory_compact as hmc
        i = self._pos(capsule_id)
        r = self._rows[i]
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
        payload = hmc._canon(rec)
        path = self.record_path(capsule_id)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(payload)
            with open(path, "rb") as fh:
                ok = fh.read() == payload
        except OSError:
            ok = False
        if not ok:
            self.eye._log("MOVE_OFF_FAILED", capsule_id, digest=_sha(rec))
            return False
        self._rows[i] = {"cold": idx}
        self.eye._log("MOVE_OFF", capsule_id, digest=_sha(rec), index_digest=_sha(idx))
        return True

    def move_off_oldest_until(self, done: Any) -> None:
        """M1: move the oldest capsules still in working memory off it until `done()` or none is left."""
        for cid in [self._rid(r) for r in self._rows if "cold" not in r]:
            if done():
                return
            self.move_off(cid)

    # ---------------------------------------------------------------- the list surface
    def __iter__(self):
        """The capsules in working memory (moved ones are reached by name through `get`)."""
        for i in range(len(self._rows)):
            if "cold" in self._rows[i]:
                continue
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
        """What working memory holds: lean rows, full capsules the Eye refused to shrink, and index rows."""
        return [r.get("lean") or r.get("full") or r["cold"] for r in self._rows]

    def size_of(self, cap: Any) -> int:
        import helm_memory_compact as hmc
        return len(hmc._canon(self.eye.shrink(cap)))

    def stored_bytes(self) -> int:
        import helm_memory_compact as hmc
        return sum(len(hmc._canon(r)) for r in self.stored())
