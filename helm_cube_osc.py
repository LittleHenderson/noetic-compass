"""helm_cube_osc.py -- HELM cube oscillation v2: a taught fact becomes a cube at its thing's Atlas node only after
the proposer and the brain side agree in rounds; memories fade step by step into CAS. Behind ONE switch, default OFF.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
When the person tells HELM a plain fact ("The Oxley line ran eight buses in September."):
  1. PROPOSE: three proposer copies read the line into (thing, slot, value, replaces); all three must agree.
  2. CHECK: the brain side checks the reading against what HELM holds -- the thing and the value are words the person
     actually typed (nothing invented); a replaced value is the cube's current value; the capsule notation compiles.
  3. SAY BACK: the brain side writes the reading back in plain English ("Oxley buses line september: eight.").
  4. RE-READ: the proposers read the say-back line; the same reading = one agreeing round.
Keep the fact as a cube after 2 agreeing rounds within 3. Otherwise no cube: the person's words stay and HELM asks
later. Rounds 4-6 are tried in a SHADOW for the report only and never stored (the owner: "WE MAY NEED MORE THAN 3
ROUNDS"). A correction is a new cube revision; the history is kept. Each thing has one Atlas CONTEXT node; each kept
revision is a POSSIBILITY node under it; a confirmation adds a FACT node.
Fading ladder (every 4 turns): S0 whole line -> S1 v1 capsule (cold copy, breadcrumb, receipt) -> S2 a small record
(notation, clues, cube pointer, breadcrumb; the capsule sentence moved to a cold side file). Exact-fraction mass.

The proposer here is an INTERFACE. `StandInProposer` is for tests and is NOT the CTT; the real CTT adapter comes with
the retraining step (owner line `CUBE TRAIN at 3 USD`, not yet typed). Without a proposer the OSC arm stores nothing.

Design: docs/working/helm_cube_oscillation_v1/ (DESIGN, pre-code f7b6183b..., A-TEACH2-1..3); spec 7.125.
SWITCH: HELM_CUBE_OSC, default OFF. Modes: OSC, ONE_READER, CTT_ONLY, TABLE, TABLE_OSC, ONE_STEP_FADE.
CLAIM STATUS: ENGINEERED-NOT-VALIDATED. Standard library only (the cube store, the compiler and the Atlas through the
repository modules helm_memory and helm_memory_compact already load).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

import helm_memory_compact as hmc

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
PLAIN_INTENTS = {"GENERAL_KNOWLEDGE_INQUIRY", "GENERAL_CONVERSATION", "REFRESH_ANSWER"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"}
#: A-TEACH2-2 B2 discourse words, plus "replaces" (the say-back's own word; build deviation D-BUILD-1)
DISCOURSE = {"correction", "actually", "sorry", "meant", "honestly", "also", "more", "said", "before", "earlier",
             "instead", "like", "just", "really", "think", "replaces"}
#: A-TEACH2-3 openers: a capitalised first word in this list is not a name
OPENERS = {"the", "this", "that", "there", "then", "these", "those", "our", "my", "your", "one", "also", "and", "but",
           "so", "oh", "okay", "ok", "by", "let", "back", "in", "on", "at", "for", "from", "after", "during", "last",
           "next", "every", "each", "honestly", "correction", "actually", "sorry", "yes", "well", "anyway", "right",
           "just", "now", "around", "about", "over", "since", "when", "as", "it", "we", "they", "he", "she", "i"}
#: number words a VALUE may be (cardinals; "one" is left out because it is also a pronoun -- build deviation D-BUILD-2)
VALUE_NUMBERS = {"zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                 "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
                 "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "dozen"}
WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


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


def _tokens(text: str) -> List[Tuple[str, int]]:
    return [(m.group(0).strip("'-"), m.start()) for m in WORD_RX.finditer(text or "")]


def _is_name(word: str, first: bool) -> bool:
    low = word.lower()
    if not word[:1].isupper() or len(word) < 3 or low in MONTHS or low in VALUE_NUMBERS:
        return False
    if first and (low in hmc.STOP_WORDS or low in DISCOURSE or low in OPENERS):
        return False
    return True


def rule_read(text: str) -> Optional[Reading]:
    """The hand-written rule reader (A-TEACH2-2 B2, A-TEACH2-3). General rules, no subject template. None = cannot read."""
    toks = _tokens(text)
    if not toks:
        return None
    words = [w for w, _ in toks]
    low = [w.lower() for w in words]
    names: List[str] = []
    for i, w in enumerate(words):
        first = i == 0 or text[:toks[i][1]].rstrip().endswith(":")
        if _is_name(w, first) and low[i] not in names:
            names.append(low[i])
    # replaced values: after "not", after "instead of", after "replaces", or X in "said X before"
    replaced: List[str] = []
    for i, w in enumerate(low):
        prev = low[i - 1] if i >= 1 else ""
        prev2 = " ".join(low[i - 2:i]) if i >= 2 else ""
        nxt = low[i + 1] if i + 1 < len(low) else ""
        if prev in {"not", "replaces"} or prev2 == "instead of" or (prev == "said" and nxt == "before"):
            if w in VALUE_NUMBERS or w in names:
                replaced.append(w)
    numbers = [w for w in low if w in VALUE_NUMBERS and w not in replaced]
    if not names:
        return None
    thing = names[0]
    if numbers:
        if len(set(numbers)) != 1 or len(numbers) != 1:
            return None
        value = numbers[0]
    else:
        others = [n for n in names[1:] if n not in replaced]
        if not others:
            return None
        value = others[-1]
    reps = [r for r in replaced if r != value]
    replaces = reps[0] if reps else None
    slot = frozenset(w for w in hmc.content_words(text) if w not in {thing, value, replaces} and w not in DISCOURSE
                     and w not in names)
    if not slot:
        return None
    return Reading(thing=thing, slot=slot, value=value, replaces=replaces)


def say_back(r: Reading) -> str:
    """The brain side's plain say-back line (A-TEACH2-2 B4). No CAS token; only the reading's own words."""
    line = f"{r.thing.capitalize()} {' '.join(sorted(r.slot))}: {r.value}."
    if r.replaces:
        line += f" This replaces {r.replaces}."
    return line


class StandInProposer:
    """A TEST STAND-IN for one proposer copy. NOT the CTT. Never used in an exam arm."""

    is_ctt = False

    def __init__(self, fn: Callable[[str], Optional[Reading]]) -> None:
        self.fn = fn

    def propose(self, text: str) -> Optional[Reading]:
        return self.fn(text)


# ----------------------------------------------------------------------------------------------- the oscillator
class CubeOsc:
    def __init__(self, memory: Any, mode: str = "OSC", proposers: Optional[List[Any]] = None, sweep: bool = True,
                 cold_dir: Optional[str] = None) -> None:
        if mode not in MODES:
            raise ValueError(mode)
        self.memory, self.mode = memory, mode
        self.proposers = list(proposers or [])
        self.uses_store = mode in ("OSC", "ONE_READER", "CTT_ONLY", "ONE_STEP_FADE")
        self.sweep_on = bool(sweep) and mode in ("OSC", "ONE_READER", "CTT_ONLY")
        self.table: Dict[Tuple[str, FrozenSet[str]], str] = {}
        self.table_src: Dict[Tuple[str, FrozenSet[str]], int] = {}
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

    # ---------------------------------------------------------------- cubes
    @staticmethod
    def node_id(thing: str, slot: FrozenSet[str]) -> str:
        return "teach_" + hashlib.sha256((thing + "|" + " ".join(sorted(slot))).encode("utf-8")).hexdigest()[:12]

    def _store(self):
        return getattr(self.memory.context, "cube_store", None)

    def cube_for(self, thing: str, slot: FrozenSet[str]):
        if not self.uses_store or self._store() is None:
            return None
        return self._store().nodes.get(self.node_id(thing, slot))

    def _current(self, thing: str, slot: FrozenSet[str]) -> Optional[str]:
        if self.uses_store:
            c = self.cube_for(thing, slot)
            return c.faces["face_1"].human_text if c is not None else None
        return self.table.get((thing, slot))

    def _write(self, r: Reading, turn: Any) -> Dict[str, Any]:
        if not self.uses_store:
            self.table[(r.thing, r.slot)] = r.value
            self.table_src[(r.thing, r.slot)] = turn.turn_id
            return {"stored": "table"}
        import helm_memory as hm  # the cube classes, as helm_memory imports them
        store = self._store()
        nid = self.node_id(r.thing, r.slot)
        prev = store.nodes.get(nid)
        rev = (prev.revision + 1) if prev is not None else 1
        hist = list(prev.faces["face_1"].structured.get("history", [])) if prev is not None else []
        hist.append([rev, r.value, turn.turn_id])
        faces = {f"face_{i}": hm.Face(availability="populated" if i == 1 else "unknown",
                                      human_text=r.value if i == 1 else "No decomposition.",
                                      structured={"thing": r.thing, "slot": sorted(r.slot), "value": r.value,
                                                  "history": hist} if i == 1 else {})
                 for i in range(1, 7)}
        node = hm.CubeNode(node_id=nid, core=hm.Core(label=f"{r.thing}: {' '.join(sorted(r.slot))}", kind="instance",
                                                     identity_statement="A fact the person taught HELM in conversation."),
                           faces=faces, revision=rev, turn_index=turn.turn_id,
                           provenance=hm.Provenance(source="USER_SAID"), assertion="ASSERTED", valence="NEUTRAL")
        store.write_cube(node)
        if nid not in turn.cubes_written:
            turn.cubes_written.append(nid)           # the v1 capsule of this turn then binds the cube
        if self.atlas is not None:
            thing_node = f"thing:{r.thing}"
            try:
                self.atlas.node(thing_node)
            except Exception:
                self.atlas.add_node(thing_node, "CONTEXT", {"thing": r.thing})
            rev_node = f"cube:{nid}:r{rev}"
            self.atlas.add_node(rev_node, "POSSIBILITY", {"value": r.value, "turn_id": turn.turn_id})
            self.atlas.add_edge(thing_node, rev_node, "holds", cross_kind_declared=True)
        return {"stored": "cube", "node_id": nid, "revision": rev}

    def confirm(self, node_id: str) -> None:
        """The person confirmed: provenance CHECKED and a FACT node beside the revision (Atlas kinds never change)."""
        node = self._store().nodes.get(node_id)
        if node is None:
            return
        node.provenance.source = "CHECKED"
        if self.atlas is not None:
            thing = node.faces["face_1"].structured["thing"]
            fid = f"fact:{node_id}:r{node.revision}"
            self.atlas.add_node(fid, "FACT", {"value": node.faces["face_1"].human_text})
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
        words = {w.lower() for w, _ in _tokens(text)}
        if r.thing not in words or r.value not in words:
            return False, "a word of the reading is not in the person's line"
        if r.replaces is not None:
            cur = self._current(r.thing, r.slot)
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
            r = rule_read(text)
            if r is not None:
                ok, why = (True, "") if self.mode == "TABLE" else self.check(r, text)
                if ok:
                    row.update(self._write(r, turn), kept=True, reading=_rd(r))
                else:
                    row["check_failed"] = why
        elif self.mode == "CTT_ONLY":
            r = self._unanimous(text)
            if r is not None:
                row.update(self._write(r, turn), kept=True, reading=_rd(r))
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
                row.update(self._write(reading, turn), kept=True, reading=_rd(reading))
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

    # ---------------------------------------------------------------- answering
    def answer(self, question: str) -> Optional[Dict[str, Any]]:
        q = {w.lower() for w, _ in _tokens(question)} | set(hmc.content_words(question))
        if self.uses_store:
            store = self._store()
            entries = []
            for nid, node in (store.nodes.items() if store is not None else []):
                st = node.faces["face_1"].structured if "face_1" in node.faces else {}
                if not nid.startswith("teach_") or not st:
                    continue
                entries.append((st["thing"], frozenset(st["slot"]), node.faces["face_1"].human_text,
                                st["history"][-1][2], nid))
        else:
            entries = [(t, s, v, self.table_src[(t, s)], None) for (t, s), v in self.table.items()]
        scored = []
        for thing, slot, value, src, nid in entries:
            if thing not in q:
                continue
            ov = len(slot & q)
            if ov >= min(2, len(slot)):
                scored.append((ov, thing, slot, value, src, nid))
        if not scored:
            return None
        best = max(s[0] for s in scored)
        top = [s for s in scored if s[0] == best]
        if len(top) >= hmc.WHICH_ONE_AT:
            return {"label": "UNKNOWN", "value": None, "text": f"I remember a few things about {top[0][1].capitalize()}. Which one do you mean?",
                    "question": True, "node_id": None}
        _, thing, slot, value, src, nid = top[-1]
        for item in self.items.values():
            if item["turn_id"] == src:
                item["uses"] += 1
                item["last"] = self.tick
        label = "EXACT" if self._words_fetchable(src) else "RECONSTRUCTED"
        phrase = f"{thing.capitalize()} {' '.join(sorted(slot))}: {value}"
        text = (f"You told me {phrase}." if label == "EXACT"
                else f"I don't have your exact words any more, but my notes say {phrase}.")
        return {"label": label, "value": value, "text": text, "thing": thing, "slot": sorted(slot), "node_id": nid,
                "source_turn": src, "question": False}

    def _words_fetchable(self, turn_id: int) -> bool:
        if any(t.turn_id == turn_id for t in self.memory.turns):
            return True
        comp = getattr(self.memory, "compactor", None)
        if comp is None:
            return False
        cap = next((c for c in comp.capsules if turn_id in c.crumb["turn_ids"]), None)
        return cap is not None and comp._fetch(cap)[0] == "EXACT"

    # ---------------------------------------------------------------- the ladder
    def _mass(self, item: Dict[str, Any]) -> Fraction:
        n = item["uses"]
        f = 1 + (1 + n).bit_length() - 1
        age = self.tick - item["last"]
        return S_IMPORTANCE * f * DECAY ** age

    def _protected(self, turn_id: int) -> bool:
        """A-TEACH2-2 B8: a turn that wrote a cube revision not yet confirmed or superseded is never faded."""
        store = self._store()
        if store is None or not self.uses_store:
            return False
        for nid, node in store.nodes.items():
            st = node.faces["face_1"].structured if nid.startswith("teach_") and "face_1" in node.faces else None
            if st and st["history"][-1][2] == turn_id and node.provenance.source != "CHECKED":
                return True
        return False

    def on_turn(self, turn: Any) -> None:
        self.tick += 1
        self.items[turn.turn_id] = {"turn_id": turn.turn_id, "uses": 0, "last": self.tick}
        if turn.intent in PLAIN_INTENTS:
            self.observe(turn)
        if self.sweep_on and self.tick % SWEEP_EVERY == 0:
            self.sweep()

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
            # the breadcrumb is kept lean: the cold path is rebuilt from the capsule id and the cold folder, so the S2
            # record keeps only the capsule id, the cold copy's sha256 and the turn ids (build deviation D-BUILD-3)
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
        """A-TEACH2-2 B8: live turns' user text + S1 capsules' canonical JSON + S2 records' canonical JSON."""
        total = sum(len(t.user_raw_text.encode("utf-8")) for t in self.memory.turns)
        comp = getattr(self.memory, "compactor", None)
        for cap in (comp.capsules if comp else []):
            total += len(hmc._canon(self._s2[cap.capsule_id] if cap.capsule_id in self._s2 else cap.as_dict()))
        return total


def _rd(r: Reading) -> Dict[str, Any]:
    return {"thing": r.thing, "slot": sorted(r.slot), "value": r.value, "replaces": r.replaces}


def attach(memory: Any, mode: str = "OSC", proposers: Optional[List[Any]] = None, sweep: bool = True) -> CubeOsc:
    """Give a HELMConversationalMemory its cube oscillator (the switch ON path). The v1 compactor is attached too when
    missing, because the ladder's S1 step is v1's capsule."""
    if getattr(memory, "compactor", None) is None:
        hmc.attach(memory)
    osc = CubeOsc(memory, mode=mode, proposers=proposers, sweep=sweep)
    memory.cube_osc = osc
    return osc
