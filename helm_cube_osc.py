"""helm_cube_osc.py -- HELM cube oscillation v2, built ON the existing Cube Node Schema v0.1 and the unified cube store
(docs/working/noetic_council/cube_store/: cube.py, store.py, operations.py). Behind ONE switch, default OFF.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
When the person tells HELM a plain fact ("The Oxley line ran eight buses in September."):
  1. PROPOSE: three proposer copies read the line into (thing, slot, value, replaces); all three must agree.
  2. CHECK: the brain side checks the reading -- the thing and the value are words the person typed (nothing invented);
     a replaced value is the current one; there is a second node for the fact to point at; the notation compiles.
  3. SAY BACK: the brain side writes the reading back in plain English (a renderer, not a parser).
  4. RE-READ: the proposers read the say-back line; the same reading = one agreeing round.
Kept after 2 agreeing rounds within 3; rounds 4-6 are a SHADOW, reported only, never stored.
A kept fact is written the way the Cube Node Schema says:
  - THINGS ARE CUBES: each named thing ("Oxley", "September", "Halden") is one cube with the schema's six faces --
    face_1 technical (its name), face_2 context, face_3 analogy or metaphor, face_4 mapping, face_5 decomposition,
    face_6 recomposition. Faces 2-6 stay "unknown" with an explanation until taught; nothing is invented (schema §3).
  - FACTS ARE BRANCHES: one `contains` branch from the thing to the other node, whose COMMONALITY says what the two
    nodes have in common -- the Oxley line and September share "eight buses" (kind "buses line", referent "eight").
  - A correction is a newer branch; the older one stays in the branch table as the history.
  - ANSWERS GO THROUGH THE THREE OPERATIONS: LIST_PARTS (what a thing holds), FIND_SHARED_PART (what two things have
    in common), REACHED_VIA (how two things are related). Each answer names the operation it ran.
Each thing also has an Atlas CONTEXT node; each kept fact a POSSIBILITY node; a confirmation adds a FACT node.
Fading ladder (every 4 turns): S0 whole line -> S1 v1 capsule -> S2 a lean record. Exact-fraction mass.

NO PARSER INSIDE HELM (SPEC_CUBE_STORE_UNIFIED: "no new parser"; A-TEACH2-4 R5). Readings come only from the proposer
interface -- the CTT once retrained (owner line `CUBE TRAIN at 3 USD`, not yet typed). `StandInProposer` is for tests and
is NOT the CTT. The exam's baseline reader lives on the exam side (docs/working/helm_cube_oscillation_v1/
teach2_rule_reader.py) and reaches HELM only through the `reader` argument of the ONE_READER and TABLE arms.

Design: docs/working/helm_cube_oscillation_v1/ (DESIGN; pre-code f7b6183b...; A-TEACH2-1..4); spec 7.125.
SWITCH: HELM_CUBE_OSC, default OFF. Modes: OSC, ONE_READER, CTT_ONLY, TABLE, TABLE_OSC, ONE_STEP_FADE.
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

import helm_memory_compact as hmc

_CUBE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "working", "noetic_council", "cube_store")
if os.path.isdir(_CUBE_DIR) and _CUBE_DIR not in sys.path:
    sys.path.insert(0, _CUBE_DIR)

MODES = ("OSC", "ONE_READER", "CTT_ONLY", "TABLE", "TABLE_OSC", "ONE_STEP_FADE")
ROUND_CAP = 3
KEEP_AGREEING = 2
SHADOW_LAST_ROUND = 6
SWEEP_EVERY = 4
ACTIVE_TAIL = 2
S_IMPORTANCE = Fraction(1, 2)
DECAY = Fraction(19, 20)
THETA_S1 = Fraction(1, 5)
THETA_S2 = Fraction(1, 50)
#: A-TEACH2-5 / A-TEACH2-6: keep every line until working memory passes the limit, then fade the oldest unprotected
#: lines in batches (16, widened by 16 until the capsule is smaller than its lines) down to 90 % of the limit. When the
#: device's cold folder passes its own limit, the oldest originals move to the cloud tier (helm_cold_cloud).
WORKING_LIMIT_BYTES = 53370
LOCAL_COLD_LIMIT_BYTES = 50 * 1024 * 1024
BATCH_LINES = 16
LIMIT_TARGET = Fraction(9, 10)
AWAY = "My full notes are stored away and I can't reach them right now"
PLAIN_INTENTS = {"GENERAL_KNOWLEDGE_INQUIRY", "GENERAL_CONVERSATION", "REFRESH_ANSWER"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"}
#: number words a VALUE may be (cardinals; "one" is left out because it is also a pronoun -- build deviation D-BUILD-2)
VALUE_NUMBERS = {"zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                 "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
                 "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "dozen"}
UNTAUGHT = "Not taught in this conversation; never filled by a guess (Cube_Node_Schema_v0.1 section 3)."
_WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _words(text: str) -> set:
    return {m.group(0).strip("'-").lower() for m in _WORD_RX.finditer(text or "")}


# ----------------------------------------------------------------------------------------------- the switch
def cube_osc_mode(value: Optional[str] = None) -> Optional[str]:
    """None = OFF (default). 1 / ON / OSC -> OSC; any listed mode by name."""
    raw = (value if value is not None else os.environ.get("HELM_CUBE_OSC") or "").strip().upper()
    if raw in {"1", "ON", "TRUE", "YES", "OSC"}:
        return "OSC"
    return raw if raw in MODES else None


# ----------------------------------------------------------------------------------------------- the reading
@dataclass(frozen=True)
class Reading:
    thing: str
    slot: FrozenSet[str]
    value: str
    replaces: Optional[str] = None


def say_back(r: Reading) -> str:
    """The brain side's plain say-back line (a renderer, not a parser). No CAS token; only the reading's own words."""
    def say(w: str) -> str:            # a name keeps its capital, a number word stays lower case
        return w if w in VALUE_NUMBERS else w.capitalize()
    line = f"{r.thing.capitalize()} {' '.join(sorted(r.slot))}: {say(r.value)}."
    if r.replaces:
        line += f" This replaces {say(r.replaces)}."
    return line


class StandInProposer:
    """A TEST STAND-IN for one proposer copy. NOT the CTT. Never used in an exam arm under test."""

    is_ctt = False

    def __init__(self, fn: Callable[[str], Optional[Reading]]) -> None:
        self.fn = fn

    def propose(self, text: str) -> Optional[Reading]:
        return self.fn(text)


def target_string(r: Optional[Reading]) -> str:
    """The CTT's output format for a reading (A-CUBE-TRAIN-1): `<thing> | <slot words, sorted> | <value> | <replaces
    or ->`, or `NONE`. The training rows are written with this, so rows and adapter cannot disagree."""
    if r is None:
        return "NONE"
    return f"{r.thing} | {' '.join(sorted(r.slot))} | {r.value} | {r.replaces or '-'}"


def reading_from_ctt(output: str, line: str) -> Optional[Reading]:
    """The CTT adapter (A-CUBE-TRAIN-1 A4): a CTT output becomes a Reading, or None. Refused: `NONE`; anything not in
    the four-field format; an empty field; an empty slot; any word (thing, slot, value, replaces) that is not a word of
    the person's line (nothing invented)."""
    parts = [p.strip() for p in (output or "").split("|")]
    if len(parts) != 4 or not all(parts):
        return None
    thing, slot_text, value, replaces = (p.lower() for p in parts)
    slot = frozenset(slot_text.split())
    line_words = _words(line)
    words = {thing, value} | set(slot) | ({replaces} if replaces != "-" else set())
    if not slot or any(len(w.split()) != 1 for w in (thing, value, replaces)) or not words <= line_words:
        return None
    return Reading(thing, slot, value, None if replaces == "-" else replaces)


class CTTProposer:
    """One proposer copy backed by the CTT: `serve(line) -> raw output` (the model runs in its own process), then the
    adapter. Never raises: a serving error is no reading."""

    is_ctt = True

    def __init__(self, serve: Callable[[str], str], name: str = "CTT") -> None:
        self.serve, self.name = serve, name

    def propose(self, text: str) -> Optional[Reading]:
        try:
            return reading_from_ctt(self.serve(text), text)
        except Exception:
            return None


def _target_and_kind(r: Reading) -> Tuple[Optional[str], str]:
    """The second node of the fact and the commonality kind (A-TEACH2-4 R2)."""
    if r.value in VALUE_NUMBERS:
        months = sorted(w for w in r.slot if w in MONTHS)
        target = months[0] if months else None
    else:
        target = r.value
    kind = " ".join(sorted(w for w in r.slot if w != target))
    return target, kind


def _names_in(text: str) -> set:
    """Capitalised words after the first word that are not months: the things a question names (no parsing)."""
    toks = [m.group(0).strip("'-") for m in _WORD_RX.finditer(text or "")]
    return {w.lower() for w in toks[1:] if w[:1].isupper() and len(w) >= 3 and w.lower() not in MONTHS}


def thing_id(name: str) -> str:
    return "thing_" + name


# ----------------------------------------------------------------------------------------------- the oscillator
class CubeOsc:
    def __init__(self, memory: Any, mode: str = "OSC", proposers: Optional[List[Any]] = None, sweep: bool = True,
                 cold_dir: Optional[str] = None, reader: Optional[Callable[[str], Optional[Reading]]] = None,
                 limit_bytes: Optional[int] = None, local_limit_bytes: Optional[int] = None,
                 cloud_prefix: Optional[str] = None) -> None:
        if mode not in MODES:
            raise ValueError(mode)
        self.memory, self.mode, self.reader = memory, mode, reader
        self.proposers = list(proposers or [])
        self.uses_store = mode in ("OSC", "ONE_READER", "CTT_ONLY", "ONE_STEP_FADE")
        self.limit_bytes, self.local_limit_bytes = limit_bytes, local_limit_bytes
        self.cloud_prefix = cloud_prefix or f"teach/{memory.session_id}/"
        self.batch_log: List[Dict[str, Any]] = []
        self._last_limit_flag: Optional[str] = None
        # the per-4-turn sweep runs only on the ladder path (no limit); with a limit it is retired (A-TEACH2-5 L1)
        self.sweep_on = bool(sweep) and mode in ("OSC", "ONE_READER", "CTT_ONLY") and limit_bytes is None
        self.table: Dict[Tuple[str, FrozenSet[str]], str] = {}
        self.table_src: Dict[Tuple[str, FrozenSet[str]], int] = {}
        # A-TEACH2-22 F1b: the person's line behind each table entry (line numbers repeat without a compactor)
        self.table_text: Dict[Tuple[str, FrozenSet[str]], str] = {}
        self.log: List[Dict[str, Any]] = []
        self.fade_moves: List[Dict[str, Any]] = []
        self.store_writes_from_shadow = 0
        self.tick = 0
        self.items: Dict[int, Dict[str, Any]] = {}
        self._s2: Dict[str, Dict[str, Any]] = {}
        self._sweeps = 0
        comp = getattr(memory, "compactor", None)
        self.cold_dir = cold_dir or (getattr(comp, "cold_dir", None) or os.path.join(memory.storage_dir, "cold"))
        self.atlas = None
        if self.uses_store:
            atlas_mod = hmc._tools()["atlas"]
            if atlas_mod is not None:
                self.atlas = atlas_mod.Atlas(atlas_id="cube_osc", max_depth=1)

    # ---------------------------------------------------------------- the store, the schema's way
    def _store(self):
        return getattr(self.memory.context, "cube_store", None)

    def _ensure_thing(self, name: str, turn_id: int) -> str:
        """A thing is a schema cube: core + six faces; face_1 names it; faces 2-6 unknown with an explanation."""
        import helm_memory as hm
        store = self._store()
        nid = thing_id(name)
        if nid in store.nodes:
            return nid
        faces = {"face_1": hm.Face(availability="populated", human_text=name.capitalize(),
                                   structured={"canonical_name": name})}
        for i in range(2, 7):
            faces[f"face_{i}"] = hm.Face(availability="unknown", human_text=UNTAUGHT)
        store.write_cube(hm.CubeNode(node_id=nid, core=hm.Core(label=name.capitalize(), kind="instance",
                                                               identity_statement=f"A thing the person named on turn {turn_id}."),
                                     faces=faces, revision=1, turn_index=turn_id,
                                     provenance=hm.Provenance(source="USER_SAID"), assertion="ASSERTED",
                                     valence="NEUTRAL"))
        if self.atlas is not None:
            try:
                self.atlas.node(f"thing:{name}")
            except Exception:
                self.atlas.add_node(f"thing:{name}", "CONTEXT", {"thing": name, "cube": nid})
        return nid

    def _latest_branch(self, thing: str, target: str, kind: str):
        store = self._store()
        if store is None:
            return None
        hits = [b for b in store.branches if b.source_node_id == thing_id(thing) and b.target_node_id == thing_id(target)
                and (b.commonality or {}).get("kind") == kind]
        return hits[-1] if hits else None

    def _current(self, r: Reading) -> Optional[str]:
        if not self.uses_store:
            return self.table.get((r.thing, r.slot))
        target, kind = _target_and_kind(r)
        b = self._latest_branch(r.thing, target, kind) if target else None
        return b.commonality.get("referent") if b is not None else None

    def write_reading(self, r: Reading, turn: Any) -> Dict[str, Any]:
        """Write one kept reading: TABLE modes into a plain dict; store modes as schema cubes + one branch."""
        if not self.uses_store:
            self.table[(r.thing, r.slot)] = r.value
            self.table_src[(r.thing, r.slot)] = turn.turn_id
            self.table_text[(r.thing, r.slot)] = turn.user_raw_text
            return {"stored": "table"}
        import helm_memory as hm
        target, kind = _target_and_kind(r)
        src = self._ensure_thing(r.thing, turn.turn_id)
        tgt = self._ensure_thing(target, turn.turn_id)
        com = {"kind": kind, "referent": r.value}
        if r.value in VALUE_NUMBERS:
            com["amount"] = r.value
        if r.replaces:
            com["replaces"] = r.replaces
        bid = "br_" + hashlib.sha256(f"{src}|{tgt}|{kind}|{turn.turn_id}".encode("utf-8")).hexdigest()[:12]
        store = self._store()
        store.write_branch(hm.Branch(branch_id=bid, context_id=store.context_id, source_node_id=src, predicate="contains",
                                     target_node_id=tgt, commonality=com, provenance_refs=[f"turn:{turn.turn_id}"]))
        for nid in (src, tgt):
            if nid not in turn.cubes_written:
                turn.cubes_written.append(nid)          # the v1 capsule of this turn then binds these cubes
        if self.atlas is not None:
            self.atlas.add_node(f"fact:{bid}", "POSSIBILITY", {"branch": bid, "kind": kind, "turn_id": turn.turn_id})
            self.atlas.add_edge(f"thing:{r.thing}", f"fact:{bid}", "holds", cross_kind_declared=True)
        return {"stored": "branch", "branch_id": bid, "source": src, "target": tgt}

    def confirm(self, thing: str) -> None:
        """The person confirmed: a new revision of the thing's cube with provenance CHECKED, and an Atlas FACT node."""
        store = self._store()
        node = store.nodes.get(thing_id(thing)) if store is not None else None
        if node is None:
            return
        new = copy.deepcopy(node)
        new.revision = node.revision + 1
        new.provenance.source = "CHECKED"
        store.write_cube(new)
        if self.atlas is not None:
            fid = f"confirmed:{thing}:r{new.revision}"
            self.atlas.add_node(fid, "FACT", {"thing": thing})
            self.atlas.add_edge(f"thing:{thing}", fid, "holds", cross_kind_declared=True)

    # ---------------------------------------------------------------- the rounds
    def _unanimous(self, text: str) -> Optional[Reading]:
        if not self.proposers:
            return None
        props = [p.propose(text) for p in self.proposers]
        if any(p is None for p in props) or len(set(props)) != 1:
            return None
        return props[0]

    def check(self, r: Reading, text: str) -> Tuple[bool, str]:
        words = _words(text)
        if r.thing not in words or r.value not in words:
            return False, "a word of the reading is not in the person's line"
        target, _kind = _target_and_kind(r)
        if self.uses_store and not target:
            return False, "the fact has no second node to point at"
        if r.replaces is not None:
            cur = self._current(r)
            if cur is not None and cur != r.replaces:
                return False, "the replaced value is not the current value"
        if not hmc.Compactor._compiles("^1^C")[0]:
            return False, "the capsule notation does not compile"
        return True, ""

    def _round(self, text: str) -> Tuple[bool, Optional[Reading], str]:
        r = self._unanimous(text)
        if r is None:
            return False, None, "proposers split or silent"
        ok, why = self.check(r, text)
        if not ok:
            return False, r, why
        again = self._unanimous(say_back(r))
        return (again == r), r, ("" if again == r else "the say-back read differently")

    def observe(self, turn: Any) -> Dict[str, Any]:
        text = turn.user_raw_text
        row: Dict[str, Any] = {"turn_id": turn.turn_id, "mode": self.mode, "kept": False, "rounds": 0,
                               "agreeing_rounds": 0, "check_failed": None}
        if self.mode in ("ONE_READER", "TABLE"):
            r = self.reader(text) if self.reader is not None else None
            if r is not None:
                ok, why = (True, "") if self.mode == "TABLE" else self.check(r, text)
                if ok:
                    row.update(self.write_reading(r, turn), kept=True, reading=_rd(r))
                else:
                    row["check_failed"] = why
        elif self.mode == "CTT_ONLY":
            r = self._unanimous(text)
            if r is not None and _target_and_kind(r)[0]:
                row.update(self.write_reading(r, turn), kept=True, reading=_rd(r))
        else:   # OSC, ONE_STEP_FADE, TABLE_OSC
            agree, reading = 0, None
            for k in range(1, ROUND_CAP + 1):
                ok, r, why = self._round(text)
                row["rounds"] = k
                if ok:
                    agree += 1
                    reading = r
                elif r is not None and why not in ("", "the say-back read differently"):
                    row["check_failed"] = why       # the brain-side check refused the proposal
                if agree >= KEEP_AGREEING:
                    break
            row["agreeing_rounds"] = agree
            if agree >= KEEP_AGREEING and reading is not None:
                row.update(self.write_reading(reading, turn), kept=True, reading=_rd(reading))
            else:
                shadow_at = None
                for k in range(ROUND_CAP + 1, SHADOW_LAST_ROUND + 1):   # reported only; nothing stored
                    ok, r, _ = self._round(text)
                    if ok:
                        agree += 1
                        if agree >= KEEP_AGREEING:
                            shadow_at = k
                            row["shadow_value"] = r.value
                            break
                row["shadow_agree_at"] = shadow_at
        self.log.append(row)
        return row

    # ---------------------------------------------------------------- answering, through the three operations
    def _things(self) -> List[str]:
        store = self._store()
        return sorted(n for n in (store.nodes if store is not None else {}) if n.startswith("thing_"))

    def answer(self, question: str) -> Optional[Dict[str, Any]]:
        q = _words(question) | set(hmc.content_words(question))
        q_names = _names_in(question)
        q_months = q & MONTHS          # A-TEACH2-22 F1a: a month the question names must be the fact's month
        if not self.uses_store:
            return self._answer_table(q, q_months)
        import operations
        store = self._store()
        scored = []
        for nid in self._things():
            rec = operations.list_parts(store, nid, view_profile="Authoring")
            for p in rec.output or []:
                com = p.get("commonality") or {}
                if "kind" not in com:
                    continue
                src, tgt = nid[len("thing_"):], p["node_id"][len("thing_"):]
                named = [n for n in (src, tgt) if n in q]
                if not named or any(n not in (src, tgt) for n in q_names):
                    continue        # a thing the question names that is not part of this fact rules the fact out
                kind_words = set(com["kind"].split())
                if q_months and not ((kind_words | {tgt}) & q_months):
                    continue        # the question names a month this fact does not hold
                ov = len(kind_words & q)
                if ov < min(2, len(kind_words)):
                    continue
                scored.append((ov + len(named), src, tgt, com, p["branch_id"], rec.cubes_read))
        if not scored:
            return None
        best = max(s[0] for s in scored)
        top = [s for s in scored if s[0] == best]
        if len(top) >= hmc.WHICH_ONE_AT:
            return {"label": "UNKNOWN", "value": None, "operation": "LIST_PARTS", "question": True,
                    "text": f"I remember a few things about {top[0][1].capitalize()}. Which one do you mean?"}
        _, src, tgt, com, bid, cubes_read = top[-1]
        if "amount" in com:
            value = com["amount"]
        else:
            value = src if (tgt in q and src not in q) else com.get("referent", tgt)
        turn_id = self._branch_turn(bid)
        if turn_id is not None and turn_id in self.items:
            self.items[turn_id]["uses"] += 1
            self.items[turn_id]["last"] = self.tick
        status = self._words_status(turn_id) if turn_id is not None else "MISSING"
        label = "EXACT" if status == "EXACT" else "RECONSTRUCTED"
        phrase = f"{src.capitalize()}, {com['kind']}, {tgt.capitalize()}" + (f": {com['amount']}" if "amount" in com else "")
        if label == "EXACT":
            text = f"You told me: {phrase}."
        elif status == "OFFLINE":
            text = f"{AWAY}, but my notes say: {phrase}."
        else:
            text = f"I don't have your exact words any more, but my notes say: {phrase}."
        return {"label": label, "value": value, "text": text, "operation": "LIST_PARTS", "cubes_read": cubes_read,
                "branch_id": bid, "source_turn": turn_id, "question": False}

    def _answer_table(self, q: set, q_months: set = frozenset()) -> Optional[Dict[str, Any]]:
        scored = []
        for (thing, slot), value in self.table.items():
            if q_months and not (slot & q_months):
                continue            # A-TEACH2-22 F1a
            if thing in q and len(slot & q) >= min(2, len(slot)):
                scored.append((len(slot & q), thing, slot, value, self.table_src[(thing, slot)]))
        if not scored:
            return None
        _, thing, slot, value, src = max(scored, key=lambda s: s[0])
        line = self.table_text.get((thing, slot))
        live = any(t.turn_id == src and (line is None or t.user_raw_text == line) for t in self.memory.turns)
        # A-TEACH2-22 F1b: EXACT only while that very line is live (or, with a compactor, its original checks)
        label = "EXACT" if (live or (getattr(self.memory, "compactor", None) is not None and self._words_fetchable(src)))             else "RECONSTRUCTED"
        return {"label": label, "value": value, "operation": "TABLE_LOOKUP", "question": False,
                "text": f"You told me: {thing.capitalize()}, {' '.join(sorted(slot))}: {value}."}

    def common(self, a: str, b: str) -> Dict[str, Any]:
        """FIND_SHARED_PART: what two things have in common (their shared constituents)."""
        import operations
        rec = operations.find_shared_part(self._store(), thing_id(a), thing_id(b), view_profile="Authoring")
        shared = sorted(x.lower() for x in (rec.output or []))
        return {"operation": rec.operation, "shared": shared, "cubes_read": rec.cubes_read}

    def related(self, a: str, b: str) -> Dict[str, Any]:
        """REACHED_VIA: how two things are related (direct, via another node, or absent)."""
        import operations
        rec = operations.reached_via(self._store(), thing_id(a), thing_id(b), view_profile="Authoring")
        return {"operation": rec.operation, "output": rec.output, "cubes_read": rec.cubes_read}

    def _branch_turn(self, bid: str) -> Optional[int]:
        for b in self._store().branches:
            if b.branch_id == bid:
                for ref in b.provenance_refs:
                    if ref.startswith("turn:"):
                        return int(ref.split(":", 1)[1])
        return None

    def _words_fetchable(self, turn_id: int) -> bool:
        return self._words_status(turn_id) == "EXACT"

    def _words_status(self, turn_id: int) -> str:
        """EXACT when the person's line is live or its original hashes right (device or cloud); else MISSING,
        CORRUPT or OFFLINE (moved to the cloud, which cannot be reached now)."""
        if any(t.turn_id == turn_id for t in self.memory.turns):
            return "EXACT"
        comp = getattr(self.memory, "compactor", None)
        if comp is not None and hasattr(comp.capsules, "find_by_turn"):
            # the Eye's path: find the capsule by its line number (rows, then folded rows), then fetch only that one
            cid = comp.capsules.find_by_turn(turn_id)
            if cid is None:
                return "OFFLINE" if comp.capsules.last_status == "AWAY" else "MISSING"
            cap = comp.capsules.get(cid)
            if cap is None:
                return "OFFLINE" if comp.capsules.last_status == "AWAY" else "MISSING"
            return comp._fetch(cap)[0]
        cap = next((c for c in (comp.capsules if comp else []) if turn_id in c.crumb["turn_ids"]), None)
        return comp._fetch(cap)[0] if cap is not None else "MISSING"

    # ---------------------------------------------------------------- the ladder
    def _mass(self, item: Dict[str, Any]) -> Fraction:
        f = 1 + (1 + item["uses"]).bit_length() - 1
        return S_IMPORTANCE * f * DECAY ** (self.tick - item["last"])

    def _protected(self, turn_id: int) -> bool:
        """A turn that wrote the current branch of a fact whose thing is not yet CHECKED is never faded (B8)."""
        store = self._store()
        if store is None or not self.uses_store:
            return False
        latest: Dict[Tuple[str, str, str], Any] = {}
        for b in store.branches:
            if "kind" in (b.commonality or {}):
                latest[(b.source_node_id, b.target_node_id, b.commonality["kind"])] = b
        for b in latest.values():
            node = store.nodes.get(b.source_node_id)
            if f"turn:{turn_id}" in b.provenance_refs and (node is None or node.provenance.source != "CHECKED"):
                return True
        return False

    def on_turn(self, turn: Any) -> None:
        self.tick += 1
        self.items[turn.turn_id] = {"turn_id": turn.turn_id, "uses": 0, "last": self.tick}
        if turn.intent in PLAIN_INTENTS:
            self.observe(turn)
        if self.sweep_on and self.tick % SWEEP_EVERY == 0:
            self.sweep()
        if self.limit_bytes is not None:
            self.fade_to_limit()
        if self.local_limit_bytes is not None:
            self.move_cold()

    # ---------------------------------------------------------------- the size limit (A-TEACH2-5 L1/L2, A-TEACH2-6)
    def _limit_flag(self, kind: str, detail: str) -> None:
        if self._last_limit_flag != kind:          # one flag per stretch, not one per turn
            self.memory.compactor._flag(kind, detail)
        self._last_limit_flag = kind

    def _runs(self) -> List[List[Any]]:
        """Runs of consecutive old lines that may fade: never the last 2, never a line holding an unconfirmed fact."""
        runs: List[List[Any]] = [[]]
        for t in self.memory.turns[: max(0, len(self.memory.turns) - ACTIVE_TAIL)]:
            if self._protected(t.turn_id):
                runs.append([])
            else:
                runs[-1].append(t)
        return [r for r in runs if r]

    @staticmethod
    def _capsule_bytes(comp: Any, cap: Any) -> int:
        """What a capsule would cost as stored: the Eye's lean record when the Eye runs the capsules, else in full."""
        if hasattr(comp.capsules, "size_of"):
            return comp.capsules.size_of(cap)
        return len(hmc._canon(cap.as_dict()))

    @staticmethod
    def _stored_bytes_of(comp: Any, cap: Any) -> int:
        if hasattr(comp.capsules, "stored"):
            row = next((r for r in comp.capsules.stored() if r.get("id", r.get("capsule_id")) == cap.capsule_id), None)
            if row is not None:
                return len(hmc._canon(row))
        return len(hmc._canon(cap.as_dict()))

    def fade_to_limit(self) -> None:
        """Every line stays word for word until working memory passes the limit. Then the oldest unprotected lines
        become one capsule per batch -- 16 lines, widened by 16 until the capsule is smaller than its lines -- until
        memory is at or under 90 % of the limit. A batch that cannot save space is not written (BATCH_NO_GAIN). If
        memory is still over 90 % after the batches, the Eye moves the oldest capsules off working memory, keeping
        only an index row each (A-TEACH2-8 M1)."""
        comp = getattr(self.memory, "compactor", None)
        if comp is None or self.working_bytes() <= self.limit_bytes:
            return
        target = self.limit_bytes * LIMIT_TARGET
        flag = self._fade_batches(comp, target)
        if self.working_bytes() > target and hasattr(comp.capsules, "move_off_oldest_until"):
            comp.capsules.move_off_oldest_until(lambda: self.working_bytes() <= target)
        if self.working_bytes() > target and hasattr(comp.capsules, "fold_until"):
            comp.capsules.fold_until(lambda: self.working_bytes() <= target)      # A-TEACH2-9: rows upon rows
        if self.working_bytes() > target:
            kind, detail = flag or ("OVER_LIMIT_INDEX", "over the limit with every capsule moved off; the index and "
                                                        "the protected lines remain")
            self._limit_flag(kind, detail)
        else:
            self._last_limit_flag = None

    def _fade_batches(self, comp: Any, target: Any) -> Optional[Tuple[str, str]]:
        while self.working_bytes() > target:
            runs = self._runs()
            if not runs:
                return ("OVER_LIMIT_PROTECTED", "over the limit; every old line is protected")
            written = False
            for run in runs:
                n = min(BATCH_LINES, len(run))
                while True:
                    batch = run[:n]
                    line_bytes = sum(len(t.user_raw_text.encode("utf-8")) for t in batch)
                    try:
                        dry = comp._compact(batch, dry_run=True)
                    except hmc.CompactRefused:
                        break
                    if self._capsule_bytes(comp, dry) < line_bytes:
                        before = self.working_bytes()
                        cap = comp._compact(batch)
                        ids = set(cap.crumb["turn_ids"])
                        self.memory.turns = [t for t in self.memory.turns if t.turn_id not in ids]
                        self.batch_log.append({"capsule_id": cap.capsule_id, "lines": len(batch), "widest": n == len(run),
                                               "line_bytes": line_bytes, "capsule_bytes": self._stored_bytes_of(comp, cap),
                                               "bytes_before": before, "bytes_after": self.working_bytes(),
                                               "receipt": cap.receipt})
                        written = True
                        break
                    if n >= len(run):
                        break
                    n = min(n + BATCH_LINES, len(run))
                if written:
                    break
            if not written:
                return ("BATCH_NO_GAIN", "over the limit; no batch of the old lines would save space")
        return None

    # ---------------------------------------------------------------- the cloud tier (A-TEACH2-5 L3-L6, A-TEACH2-8 M4)
    def _lean_path(self) -> bool:
        comp = getattr(self.memory, "compactor", None)
        return comp is not None and hasattr(comp.capsules, "fold_record_path")

    def _cold_units(self) -> List[Tuple[str, str, List[str]]]:
        """The files in the device's cold folder, grouped, oldest first: ("capsule", name, [original, record]) and
        ("fold", name, [fold record]). On the Eye's path the folder is listed, so folded capsules are included."""
        comp = getattr(self.memory, "compactor", None)
        if comp is None:
            return []
        if not self._lean_path():
            return [("capsule", c.capsule_id, [c.crumb["cold_path"]]) for c in comp.capsules]
        try:
            names = sorted(os.listdir(comp.cold_dir))
        except OSError:
            return []
        caps: Dict[str, List[str]] = {}
        folds: List[Tuple[str, str, List[str]]] = []
        for n in names:
            path = os.path.join(comp.cold_dir, n)
            if n.endswith(".fold.json"):
                folds.append(("fold", n[: -len(".fold.json")], [path]))
            elif n.endswith(".lean.json"):
                caps.setdefault(n[: -len(".lean.json")], []).append(path)
            elif n.endswith(".jsonl"):
                caps.setdefault(n[: -len(".jsonl")], []).insert(0, path)
        return [("capsule", cid, caps[cid]) for cid in sorted(caps)] + folds

    def local_cold_bytes(self) -> int:
        """Bytes in the device's cold folder: verbatim originals, the Eye's moved records and fold records."""
        return sum(os.path.getsize(f) for _k, _n, files in self._cold_units() for f in files if os.path.isfile(f))

    def _upload(self, cloud: Any, key: str, data: bytes, check: Callable[[bytes], bool]) -> bool:
        import helm_cold_cloud as hcc
        try:
            cloud.put(key, data)
            back = cloud.get(key)
        except Exception:
            back = None
        if back is None:
            hcc.forget_reachable(cloud)              # A-TEACH2-13 R2: forget a remembered yes at the first failure
        return back is not None and check(back)

    def move_cold(self) -> None:
        """When the device's cold folder passes its limit, MOVE the oldest capsule's files to the cloud: its verbatim
        original (checked by its fingerprint) and, if the Eye moved the capsule off working memory, its record (checked
        byte for byte). Both are uploaded and read back before either is removed locally (receipt MOVED_TO_CLOUD).
        Unreachable cloud or a failed check: the local copies stay (MOVE_FAILED). Nothing is ever deleted in the cloud."""
        comp = getattr(self.memory, "compactor", None)
        if comp is None or self.local_cold_bytes() <= self.local_limit_bytes:
            return
        cloud = comp.cloud
        import helm_cold_cloud as hcc
        if not hcc.is_reachable(cloud):              # A-TEACH2-13: a recent yes is remembered (no call)
            self._limit_flag("MOVE_FAILED", "local cold folder over its limit; the cloud cannot be reached")
            return
        for kind, name, files in self._cold_units():
            if self.local_cold_bytes() <= self.local_limit_bytes:
                break
            files = [f for f in files if os.path.isfile(f)]
            if not files:
                continue
            moves = []
            if kind == "fold":
                with open(files[0], "rb") as fh:
                    data = fh.read()
                key = self.cloud_prefix + os.path.basename(files[0])
                if not self._upload(cloud, key, data, lambda b: b == data):
                    self._limit_flag("MOVE_FAILED", f"read-back check failed for {key}; the local copy stays")
                    return
                os.remove(files[0])
                comp.moved_folds[name] = key
                comp._receipt("MOVED_TO_CLOUD", name, hmc._sha(data), {"key": key, "bytes": len(data)})
                continue
            cap = comp._capsule(name)
            if cap is None:
                continue
            for f in files:
                with open(f, "rb") as fh:
                    data = fh.read()
                key = self.cloud_prefix + os.path.basename(f)
                original = f.endswith(".jsonl")
                check = (lambda b: hmc._sha(b) == cap.crumb["sha256"]) if original else (lambda b, d=data: b == d)
                if not self._upload(cloud, key, data, check):
                    self._limit_flag("MOVE_FAILED", f"read-back check failed for {key}; the local copies stay")
                    return
                moves.append(("original" if original else "record", f, key, len(data)))
            for what, f, key, _n in moves:
                os.remove(f)
                (comp.moved if what == "original" else comp.moved_records)[name] = key
            comp._receipt("MOVED_TO_CLOUD", name, cap.receipt,
                          {"key": next((m[2] for m in moves if m[0] == "original"), comp.moved.get(name)),
                           "record_key": next((m[2] for m in moves if m[0] == "record"), None),
                           "sha256": cap.crumb["sha256"], "bytes": sum(m[3] for m in moves)})
        self._last_limit_flag = None

    def sweep(self) -> None:
        self._sweeps += 1
        comp = getattr(self.memory, "compactor", None)
        if comp is None:
            return
        tail = {t.turn_id for t in self.memory.turns[-ACTIVE_TAIL:]}
        for t in list(self.memory.turns):
            item = self.items.get(t.turn_id)
            if item is None or t.turn_id in tail or self._protected(t.turn_id):
                continue
            if self._mass(item) < THETA_S1:
                try:
                    cap = comp._compact([t])
                except hmc.CompactRefused:
                    continue
                self.memory.turns = [x for x in self.memory.turns if x.turn_id != t.turn_id]
                self.fade_moves.append({"sweep": self._sweeps, "item": t.turn_id, "from": "S0", "to": "S1",
                                        "receipt": cap.receipt})
        for cap in list(comp.capsules):
            if cap.capsule_id in self._s2 or getattr(cap, "kind", "statement") != "statement":
                continue
            ids = cap.crumb["turn_ids"]
            if any(self._protected(i) for i in ids):
                continue
            items = [self.items[i] for i in ids if i in self.items]
            if not items or max(self._mass(i) for i in items) >= THETA_S2:
                continue
            side = os.path.join(self.cold_dir, f"{cap.capsule_id}.s2.json")
            payload = json.dumps({"sentence": cap.cas.get("sentence")}, sort_keys=True).encode("utf-8")
            os.makedirs(self.cold_dir, exist_ok=True)
            with open(side, "wb") as fh:
                fh.write(payload)
            with open(side, "rb") as fh:
                if hmc._sha(fh.read()) != hmc._sha(payload):
                    continue
            # the breadcrumb is kept lean: the cold path is rebuilt from the capsule id and the cold folder (D-BUILD-3)
            rec = {"capsule_id": cap.capsule_id, "notation": cap.cas.get("notation"), "clues": list(cap.clues),
                   "cubes": list(cap.binds.get("cubes", [])),
                   "crumb": {"sha256": cap.crumb["sha256"], "turn_ids": list(cap.crumb["turn_ids"])},
                   "side_sha256": hmc._sha(payload)}
            rec["receipt"] = hmc._sha(hmc._canon(rec))
            self._s2[cap.capsule_id] = rec
            self.fade_moves.append({"sweep": self._sweeps, "item": cap.capsule_id, "from": "S1", "to": "S2",
                                    "receipt": rec["receipt"]})

    def stage_of(self, turn_id: int) -> Optional[str]:
        if any(t.turn_id == turn_id for t in self.memory.turns):
            return "S0"
        comp = getattr(self.memory, "compactor", None)
        cap = next((c for c in (comp.capsules if comp else []) if turn_id in c.crumb["turn_ids"]), None)
        if cap is None:
            return None
        return "S2" if cap.capsule_id in self._s2 else "S1"

    def s2_records(self) -> List[Dict[str, Any]]:
        return list(self._s2.values())

    def working_bytes(self) -> int:
        """Live turns' user text + S1 capsules' canonical JSON + S2 records' canonical JSON (A-TEACH2-2 B8)."""
        total = sum(len(t.user_raw_text.encode("utf-8")) for t in self.memory.turns)
        comp = getattr(self.memory, "compactor", None)
        if comp is not None and hasattr(comp.capsules, "stored_bytes"):
            return total + comp.capsules.stored_bytes()        # what is stored: the Eye's lean records
        for cap in (comp.capsules if comp else []):
            total += len(hmc._canon(self._s2[cap.capsule_id] if cap.capsule_id in self._s2 else cap.as_dict()))
        return total


def _rd(r: Reading) -> Dict[str, Any]:
    return {"thing": r.thing, "slot": sorted(r.slot), "value": r.value, "replaces": r.replaces}


def attach(memory: Any, mode: str = "OSC", proposers: Optional[List[Any]] = None, sweep: bool = True,
           reader: Optional[Callable[[str], Optional[Reading]]] = None,
           limit_bytes: Optional[int] = WORKING_LIMIT_BYTES, local_limit_bytes: Optional[int] = LOCAL_COLD_LIMIT_BYTES,
           cloud: Any = None, cloud_prefix: Optional[str] = None) -> CubeOsc:
    """Give a HELMConversationalMemory its cube oscillator (the switch ON path). The v1 compactor is attached too when
    missing, because a faded batch is v1's capsule. Defaults are the owner's: keep every line until 53,370 bytes, then
    fade in batches; move originals to `cloud` past 50 MB on the device. limit_bytes=None keeps the old ladder path."""
    if getattr(memory, "compactor", None) is None:
        hmc.attach(memory)
    if limit_bytes is not None:
        memory.max_turns = max(memory.max_turns, 10 ** 9)      # the turn budget no longer drops or compacts
        # the Eye runs the capsules on this path: lean records, rebuilt and receipt-checked on every read (A-TEACH2-7)
        import helm_eye_act as hea
        comp = memory.compactor
        if not isinstance(comp.capsules, hea.LeanCapsules):
            lean = hea.LeanCapsules(hea.CapsuleEye(comp))
            for cap in comp.capsules:
                lean.append(cap)
            comp.capsules = lean
    else:
        local_limit_bytes = None
    memory.compactor.cloud = cloud
    memory.compactor.clue_every_line = limit_bytes is not None     # A-TEACH2-10: clue words from every line
    osc = CubeOsc(memory, mode=mode, proposers=proposers, sweep=sweep, reader=reader, limit_bytes=limit_bytes,
                  local_limit_bytes=local_limit_bytes, cloud_prefix=cloud_prefix)
    memory.cube_osc = osc
    return osc
