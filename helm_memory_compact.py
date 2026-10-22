"""helm_memory_compact.py -- HELM memory compaction v1: rule capsules, behind ONE switch, default OFF.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Today HELM's chat memory (helm_memory.HELMConversationalMemory) keeps the last `max_turns` turns in working memory
and drops the oldest silently (the JSONL ledger on disk keeps the text). With the switch HELM_MEMORY_COMPACT ON, a turn
that would be dropped is COMPACTED instead:

  1. the verbatim turn records are written to a COLD copy first and its sha256 is checked;
  2. a CAPSULE is written: one CCE sentence the language skin round-trips (spec 7.31), its CAS notation that the
     compiler accepts, 1..8 CLUES copied verbatim from the turns, pointers to the cubes the turns wrote, the
     BREADCRUMB (cold path + sha256 + turn ids), a MASS, and a RECEIPT (sha256 over the capsule);
  3. the capsule is filed in the Atlas (the owner's RPA) under the session's current thread node, on the POSSIBILITY
     side; the verbatim turns leave working memory.

A capsule never holds a number. Cubes and the recipe brain's coefficients are never compacted; a capsule only points
at them. Recall is FETCH FIRST: a question that matches clues fetches the cold copy, checks the digest, and answers
EXACT; only when the copy is missing or damaged does HELM rebuild from the capsule, run the fit check F1..F4, and
ask ONE refresh question that quotes a clue and invents nothing (caps: 2 per thread, 1 per item; a "no" ends it).
A rebuilt memory is NEVER presented as EXACT (M1's failed gate H8, spec 7.43, kept as hard gate HG-H8).
Strengthening (after the person agrees) is four appends: mass up by a frozen step, clues grow from the person's own
words, the bound cubes' provenance moves to CHECKED, the item moves to the FACT side of its Atlas node. Content never
changes. The Unity Eye here is REPORT-ONLY: `eye_report()` lists flags; `eye_writes` is always 0.

Design: docs/working/helm_memory_compaction_v1/DESIGN_MEMORY_COMPACTION_V1.md sections 3-6 (spec 7.115).
Owner's word (2026-10-21): "Override the census floor. Start build v1 of memory compaction now: rule capsules, behind
HELM_MEMORY_COMPACT default OFF, FIX FIRST tests, 0 USD, and fix the user_facts [:20] slip with a test in the same build."

SWITCH: HELM_MEMORY_COMPACT, default OFF. OFF = helm_memory behaves exactly as before (the FIFO drop). ON = this module.
CLAIM STATUS: ENGINEERED-NOT-VALIDATED. Nothing here is scored; TEACH-1 (the pre-code, sha256 7eef0edc...) is the exam.
Standard library only; the compiler, the CCE skin and the Atlas are imported from the repository when present. When
one of them is missing, NO capsule is written and the turn stays verbatim (working memory grows past the budget and the
Eye report says why); nothing is ever dropped silently.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
COMPILER_ROOT = os.path.join(HERE, "noetic-compass-scaffold", "noetic-compass")
LANGUAGE_V3_DIR = os.path.join(HERE, "docs", "working", "noetic_council", "language_v3")
ATLAS_DIR = os.path.join(HERE, "docs", "working", "noetic_council", "continuity_build_v2")

#: Frozen numbers of the design (DESIGN 3.1, 4.1, 4.4; pre-code 2). Not learned, not tuned.
LABELS = ("EXACT", "RECONSTRUCTED", "UNKNOWN")
ACTIVE_TAIL = 2                 # the last turns of the active thread are never compacted
MAX_CLUES = 8
MIN_CLUE_LETTERS = 4
REFRESH_CAP_PER_THREAD = 2
REFRESH_CAP_PER_ITEM = 1
MASS_STEP = 1
SEARCHLIGHT_RADII = (1, 2, 4, 8)
SEARCHLIGHT_CAP = 15
CAPSULES_PER_THREAD_NODE = 8    # how many capsules hang under one Atlas thread node before a new node is opened
WHICH_ONE_AT = 3                # three or more candidates: ask which, never guess
DOMAIN = "C"                    # conversation memory lives in the Cognitive domain (DESIGN 3.1)

STOP_WORDS = {
    "the", "this", "that", "these", "those", "with", "from", "have", "has", "had", "were", "was", "there", "their",
    "about", "what", "tell", "something", "number", "topic", "into", "onto", "over", "under", "when", "then", "than",
    "them", "they", "your", "yours", "mine", "ours", "said", "says", "just", "very", "also", "some", "more", "most",
    "like", "want", "need", "know", "think", "thing", "things", "still", "ever", "every", "each", "many", "much",
    "does", "done", "doing", "being", "been", "will", "would", "could", "should", "please", "thanks", "thank",
    "hello", "okay", "yeah", "well", "really", "maybe", "again", "here", "where", "which", "while", "because",
    "remember", "remind", "told", "tells", "talk", "talked", "talking", "mean", "means",
}
#: Number words are never clue words: a capsule never holds a number (DESIGN 3.1); numbers stay in the cubes and the
#: verbatim cold copy. TEACH-1 FIX FIRST 2026-10-21 (number words such as "twelve" were reaching capsule clues).
NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
    "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty",
    "seventy", "eighty", "ninety", "hundred", "thousand", "million", "dozen", "half", "quarter", "third", "fourth",
    "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "once", "twice", "first", "second",
}
#: Turns that ASK about memory hold no memory of their own: recall never serves them, and a capsule made only of them
#: is kind "question" and is skipped by recall (TEACH-1 FIX FIRST 2026-10-21: quiz questions were served as answers).
MEMORY_QUERY_INTENTS = {"QUERY_MEMORY_RECALL", "QUERY_MEMORY_COUNT", "USER_KNOWLEDGE_QUERY", "SESSION_SUMMARY"}
NEGATIVE_ANSWER_RX = re.compile(r"\b(?:no|nope|not|don'?t remember|do not remember|can'?t remember|wrong|never)\b", re.I)

#: CCE frame per turn intent (the verb frame picks the Noetic; GRAMMAR_CCE_v0_1 section 2). The person is `you`.
FRAME_BY_INTENT = {
    "USER_NARRATIVE": 5, "USER_KNOWLEDGE_QUERY": 5,
    "USER_AFFECT": 4, "CREATIVE_HUMOR": 4,
    "USER_PREFERENCE": 2,
    "INVENTORY_DECLARATION": 1, "INVENTORY_QUERY": 1, "RECIPE_FOUNDATION_LOOP": 1,
}
DEFAULT_FRAME = 1


class CompactRefused(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


# ----------------------------------------------------------------------------------------------- the switch
def compact_on(value: Optional[bool] = None) -> bool:
    """The switch. An explicit argument wins; else HELM_MEMORY_COMPACT = 1 / ON / TRUE / YES turns it on; default OFF."""
    if value is not None:
        return bool(value)
    raw = (os.environ.get("HELM_MEMORY_COMPACT") or "").strip().upper()
    return raw in {"1", "ON", "TRUE", "YES"}


# ----------------------------------------------------------------------------------------------- tools (optional)
_TOOLS: Dict[str, Any] = {}


def _tools() -> Dict[str, Any]:
    """The compiler, the CCE skin and the Atlas, imported once from the repository. Missing ones are None."""
    if _TOOLS:
        return _TOOLS
    import sys
    compiler = cce = atlas_mod = None
    try:
        if COMPILER_ROOT not in sys.path:
            sys.path.insert(0, COMPILER_ROOT)
        from api.notation import compiler as _c  # type: ignore
        compiler = _c
    except Exception:
        compiler = None
    try:
        if LANGUAGE_V3_DIR not in sys.path:
            sys.path.insert(0, LANGUAGE_V3_DIR)
        import cce as _cce  # type: ignore
        cce = _cce
    except Exception:
        cce = None
    try:
        if ATLAS_DIR not in sys.path:
            sys.path.insert(0, ATLAS_DIR)
        import atlas as _atlas  # type: ignore
        atlas_mod = _atlas
    except Exception:
        atlas_mod = None
    _TOOLS.update({"compiler": compiler, "cce": cce, "atlas": atlas_mod})
    return _TOOLS


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cube_faces_digest(store: Any) -> str:
    """One sha256 over every cube's faces (HG-CUBE: memory work never changes a face). Provenance is not included."""
    rows = []
    for node_id in sorted(getattr(store, "nodes", {}).keys()):
        node = store.nodes[node_id]
        faces = {k: f.to_dict() for k, f in sorted(node.faces.items())}
        rows.append([node_id, faces, node.core.to_dict() if hasattr(node.core, "to_dict") else str(node.core)])
    return _sha(_canon(rows))


def read_cold(path: str) -> List[Dict[str, Any]]:
    """The verbatim turn records of a cold copy (one JSON object per line)."""
    with open(path, "rb") as fh:
        return read_cold_bytes(fh.read())


def read_cold_bytes(data: bytes) -> List[Dict[str, Any]]:
    """The same, from bytes already in hand (a copy fetched back from the cloud tier)."""
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def content_words(text: str) -> List[str]:
    """Words copied verbatim from the text, in order, lower-cased, letters only, at least MIN_CLUE_LETTERS long,
    not a stop word, not a number word, no digits. These are the only words a clue may be made of."""
    seen = set()
    out = []
    for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", text):
        lw = w.lower().strip("'-")
        if len(lw) < MIN_CLUE_LETTERS or lw in STOP_WORDS or lw in NUMBER_WORDS or lw in seen:
            continue
        seen.add(lw)
        out.append(lw)
    return out


# ----------------------------------------------------------------------------------------------- the capsule
@dataclass
class Capsule:
    capsule_id: str
    cas: Dict[str, Any]              # sentence, notation, compiles, round_trip, compiler
    clues: List[str]
    binds: Dict[str, List[str]]      # cubes: [ids]; coefficients: [(recipe, ingredient)] -- v1 binds no cell
    crumb: Dict[str, Any]            # cold_path, sha256, turn_ids
    mass: Dict[str, int]             # value, confirmed
    receipt: str
    atlas: Dict[str, Any] = field(default_factory=dict)   # node (thread CONTEXT id), node_id (capsule node), side
    kind: str = "statement"          # "question" when every turn of the window asked about memory (recall skips it)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _receipt_of(capsule_id: str, cas: Dict[str, Any], clues: List[str], binds: Dict[str, Any], crumb: Dict[str, Any],
                mass: Dict[str, int]) -> str:
    return _sha(_canon({"capsule_id": capsule_id, "cas": cas, "clues": clues, "binds": binds,
                        "crumb": {"sha256": crumb["sha256"], "turn_ids": crumb["turn_ids"]}, "mass": mass}))


# ----------------------------------------------------------------------------------------------- the compactor
class Compactor:
    """Compaction, fetch-first recall, the refresh loop, fit check, strengthening, Atlas filing, Eye report."""

    def __init__(self, memory: Any, cold_dir: Optional[str] = None, brain: Any = None) -> None:
        self.memory = memory
        self.brain = brain
        self.cold_dir = cold_dir or os.path.join(memory.storage_dir, "cold", memory.session_id)
        self.capsules: List[Capsule] = []
        self.receipts: List[Dict[str, Any]] = []
        self.eye_writes = 0
        self._eye_flags: List[Dict[str, Any]] = []
        self.coefficient_digest_checks: List[Dict[str, Any]] = []
        self._turn_counter = max([t.turn_id for t in memory.turns] or [0])
        self._asked_per_thread: Dict[str, int] = {}
        self._asked_per_item: Dict[str, int] = {}
        self._declined: set = set()
        self._strengthened: set = set()
        self._pinned: Dict[str, List[str]] = {}
        self._thread_count = 0
        self._capsules_in_thread = 0
        self.atlas = None
        self._anchor: Optional[str] = None
        # the cloud tier (A-TEACH2-5 L3/L4): None = no cloud. `moved` maps a capsule id to its cloud key once its
        # original left the device after the read-back check.
        self.cloud: Any = None
        self.moved: Dict[str, str] = {}
        self.moved_records: Dict[str, str] = {}       # capsule id -> cloud key of the Eye's moved record (A-TEACH2-8)
        self.moved_folds: Dict[str, str] = {}         # fold name -> cloud key of the Eye's fold record (A-TEACH2-9)
        # A-TEACH2-10: on the size-limit path (set by helm_cube_osc.attach) clue words come from EVERY line of a batch;
        # plain compaction keeps the first-8 rule
        self.clue_every_line = False
        tools = _tools()
        if tools["atlas"] is not None:
            self.atlas = tools["atlas"].Atlas(atlas_id="memory", max_depth=1)
            self.atlas.add_node("session", "CONTEXT", {"session": memory.session_id})
            self._anchor = "session"
        else:
            self._flag("NO_TOOLS", "atlas module missing; capsules cannot be filed")

    # ---------------------------------------------------------------- bookkeeping
    def next_turn_id(self) -> int:
        self._turn_counter += 1
        return self._turn_counter

    def _flag(self, kind: str, detail: str, capsule_id: Optional[str] = None) -> None:
        self._eye_flags.append({"kind": kind, "detail": detail, "capsule_id": capsule_id})

    def eye_report(self) -> List[Dict[str, Any]]:
        """The Unity Eye, report-only: what it would flag. It writes nothing (eye_writes stays 0)."""
        flags = list(self._eye_flags)
        seen: Dict[Tuple[str, ...], str] = {}
        for cap in self.capsules:
            key = tuple(sorted(cap.clues))
            if key in seen:
                flags.append({"kind": "DUPLICATE_CLUES", "detail": f"same clues as {seen[key]}", "capsule_id": cap.capsule_id})
            else:
                seen[key] = cap.capsule_id
            if not cap.binds["cubes"] and not cap.binds["coefficients"]:
                flags.append({"kind": "UNBOUND_CLUE", "detail": "capsule binds no cube and no coefficient", "capsule_id": cap.capsule_id})
        for cid in self._declined:
            flags.append({"kind": "DECLINED", "detail": "refresh declined; item is UNKNOWN", "capsule_id": cid})
        return flags

    def _check_brain(self, when: str) -> None:
        if self.brain is None or not hasattr(self.brain, "learned_digest"):
            return
        before = getattr(self, "_brain_digest0", None)
        now = self.brain.learned_digest()
        if before is None:
            self._brain_digest0 = now
            before = now
        self.coefficient_digest_checks.append({"when": when, "equal": now == before})
        if now != before:
            self._flag("COEFFICIENT_CHANGED", f"learned digest changed during {when}")

    def _receipt(self, kind: str, capsule_id: str, receipt: str, extra: Optional[Dict[str, Any]] = None) -> None:
        row = {"kind": kind, "capsule_id": capsule_id, "receipt": receipt}
        if extra:
            row.update(extra)
        self.receipts.append(row)

    # ---------------------------------------------------------------- the Atlas
    def _thread_node(self) -> Optional[str]:
        if self.atlas is None:
            return None
        if self._capsules_in_thread >= CAPSULES_PER_THREAD_NODE or self._thread_count == 0:
            self._thread_count += 1
            node_id = f"thread-{self._thread_count:04d}"
            self.atlas.add_node(node_id, "CONTEXT", {"thread": self._thread_count, "session": self.memory.session_id})
            previous = self._anchor
            self._anchor = node_id
            self._capsules_in_thread = 0
            if previous is not None:
                self.atlas.add_edge(node_id, previous, "before")
        self._capsules_in_thread += 1
        return self._anchor

    def _file(self, cap: Capsule) -> None:
        if self.atlas is None:
            cap.atlas = {"node": None, "node_id": None, "side": "possibility"}
            return
        thread = self._thread_node()
        node_id = f"capsule:{cap.capsule_id}"
        self.atlas.add_node(node_id, "POSSIBILITY", {"clues": list(cap.clues), "receipt": cap.receipt})
        self.atlas.add_edge(thread, node_id, "holds", cross_kind_declared=True)
        cap.atlas = {"node": thread, "node_id": node_id, "side": "possibility"}

    def _capsule_index(self) -> List[Tuple[str, List[str], str]]:
        """(name, clue words, kind) of every capsule. On the Eye's path this reads the index; nothing is fetched."""
        if hasattr(self.capsules, "clue_index"):
            return self.capsules.clue_index()
        return [(c.capsule_id, c.clues, c.kind) for c in self.capsules]

    def _capsule(self, capsule_id: str) -> Optional[Capsule]:
        """One capsule by name. On the Eye's path a moved capsule is fetched back and checked (A-TEACH2-8)."""
        if hasattr(self.capsules, "get"):
            return self.capsules.get(capsule_id)
        return next((c for c in self.capsules if c.capsule_id == capsule_id), None)

    def _searchlight(self, wanted: set) -> Tuple[List[Capsule], int, bool]:
        """Read the anchor first, then widen over the radii; cap the candidates. Returns (hits, radius, beyond).
        Hits are capsules; on the Eye's path only the hits are fetched (a moved capsule that cannot be fetched now is
        left out of the hits and noted in `self._away`)."""
        names, radius, beyond = self._searchlight_names(wanted)
        self._away = []
        hits = []
        for cid in names:
            cap = self._capsule(cid)
            if cap is not None:
                hits.append(cap)
            elif getattr(self.capsules, "last_status", None) == "AWAY":
                self._away.append(cid)
        return hits, radius, beyond

    def _searchlight_names(self, wanted: set) -> Tuple[List[str], int, bool]:
        order = [cid for cid, _c, _k in self._capsule_index()]
        known = set(order)
        order += [w for w in sorted(wanted) if w not in known]     # folded capsules found by the Eye (A-TEACH2-9)
        if self.atlas is None or self._anchor is None:
            return [c for c in order if c in wanted][:SEARCHLIGHT_CAP], 0, True
        by_node = {f"capsule:{cid}": cid for cid in order}
        for radius in SEARCHLIGHT_RADII:
            frontier = [self._anchor]
            seen = {self._anchor}
            reach = []
            for _ in range(radius):
                nxt = []
                for n in frontier:
                    for e in self.atlas.neighbours(n):
                        if e.to_node_id not in seen:
                            seen.add(e.to_node_id)
                            nxt.append(e.to_node_id)
                            if e.to_node_id in by_node:
                                reach.append(by_node[e.to_node_id])
                frontier = nxt
                if not frontier:
                    break
            hits = [c for c in reach if c in wanted][:SEARCHLIGHT_CAP]
            if hits:
                return hits, radius, False
        return [c for c in order if c in wanted][:SEARCHLIGHT_CAP], SEARCHLIGHT_RADII[-1], True

    # ---------------------------------------------------------------- compaction
    def housekeep(self) -> List[Capsule]:
        """Bring working memory under its budget by compacting the oldest turns, never the active tail.
        The involuntary tier's job by design; in v1 a plain routine. Writes nothing to any cube or coefficient."""
        self._check_brain("housekeep")
        mem = self.memory
        written: List[Capsule] = []
        while len(mem.turns) > mem.max_turns:
            excess = len(mem.turns) - mem.max_turns
            candidates = mem.turns[: max(0, len(mem.turns) - ACTIVE_TAIL)]
            if not candidates:
                break
            window = candidates[:excess]
            try:
                cap = self._compact(window)
            except CompactRefused as exc:
                self._flag("NO_CAPSULE", f"{exc.code}: turns stay verbatim, budget exceeded")
                break
            written.append(cap)
            ids = set(cap.crumb["turn_ids"])
            mem.turns = [t for t in mem.turns if t.turn_id not in ids]
        self._check_brain("housekeep.end")
        return written

    def _compact(self, turns: List[Any], dry_run: bool = False) -> Capsule:
        """Write one capsule for `turns`. dry_run=True builds the same capsule (to measure its size, A-TEACH2-6 W1)
        but writes nothing: no cold copy, no Atlas node, no receipt, not added to `capsules`."""
        tools = _tools()
        if tools["compiler"] is None or tools["cce"] is None:
            raise CompactRefused("TOOLS_MISSING", "compiler or CCE skin not importable")
        records = [asdict(t) for t in turns]
        turn_ids = [t.turn_id for t in turns]
        capsule_id = f"cap-{self.memory.session_id}-{turn_ids[0]:06d}-{turn_ids[-1]:06d}"
        # 1. clues, verbatim words only; a turn that asked about memory gives clues only if nothing else does
        stated = [t for t in turns if t.intent not in MEMORY_QUERY_INTENTS]
        kind = "statement" if stated else "question"
        clues: List[str] = []
        every = self.clue_every_line
        for t in (stated or turns):
            for w in content_words(t.user_raw_text):
                if w not in clues:
                    clues.append(w)
                if not every and len(clues) >= MAX_CLUES:
                    break
            if not every and len(clues) >= MAX_CLUES:
                break
        if not clues:
            raise CompactRefused("NO_CLUES", "no verbatim content word to clue by")
        # 2. the CCE sentence(s) and the CAS notation
        frames: List[int] = []
        for t in turns:
            n = FRAME_BY_INTENT.get(t.intent, DEFAULT_FRAME)
            if n == 2 and getattr(t, "valence", "NEUTRAL") == "NEGATIVE":
                n = 3
            if n not in frames:
                frames.append(n)
        idea = " ".join(clues[:MAX_CLUES]).replace('"', "")      # the sentence uses the first 8 (A-TEACH2-10 C2)
        sentences = [self._sentence(n, idea) for n in frames]
        sentence = " ".join(sentences)
        notation = " + ".join(f"^{n}^{DOMAIN}" for n in frames)
        compiles, compiler_name = self._compiles(notation)
        round_trip = self._round_trips(sentence)
        if not compiles or not round_trip:
            raise CompactRefused("CAS_NOT_VERIFIED", f"compiles={compiles} round_trip={round_trip}")
        cas = {"sentence": sentence, "notation": notation, "compiles": compiles, "round_trip": round_trip,
               "compiler": compiler_name}
        # 3. binds: cubes the turns wrote or read, plus user-fact cubes by the memory module's own id rule
        cubes: List[str] = []
        store = getattr(self.memory.context, "cube_store", None)
        for t in turns:
            for cid in list(t.cubes_written) + list(t.cubes_read):
                if cid not in cubes:
                    cubes.append(cid)
            cleaned = t.user_raw_text.strip().rstrip(".").strip()
            if store is not None and cleaned:
                fid = "fact_" + hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
                if fid in getattr(store, "nodes", {}) and fid not in cubes:
                    cubes.append(fid)
        binds = {"cubes": cubes, "coefficients": []}
        # 4. the cold copy first, then its digest
        cold_path = os.path.join(self.cold_dir, f"{capsule_id}.jsonl")
        payload = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records).encode("utf-8")
        if dry_run:
            crumb = {"cold_path": cold_path, "sha256": _sha(payload), "turn_ids": turn_ids}
            mass = {"value": len(turn_ids), "confirmed": 0}
            node = f"thread-{max(self._thread_count, 1):04d}" if self.atlas is not None else None
            return Capsule(capsule_id=capsule_id, cas=cas, clues=clues, binds=binds, crumb=crumb, mass=mass,
                           receipt=_receipt_of(capsule_id, cas, clues, binds, crumb, mass), kind=kind,
                           atlas={"node": node, "node_id": f"capsule:{capsule_id}" if node else None,
                                  "side": "possibility"})
        os.makedirs(self.cold_dir, exist_ok=True)
        with open(cold_path, "wb") as fh:
            fh.write(payload)
        with open(cold_path, "rb") as fh:
            digest = _sha(fh.read())
        if digest != _sha(payload):
            raise CompactRefused("COLD_WRITE_FAILED", "digest after write differs")
        crumb = {"cold_path": cold_path, "sha256": digest, "turn_ids": turn_ids}
        mass = {"value": len(turn_ids), "confirmed": 0}
        receipt = _receipt_of(capsule_id, cas, clues, binds, crumb, mass)
        cap = Capsule(capsule_id=capsule_id, cas=cas, clues=clues, binds=binds, crumb=crumb, mass=mass, receipt=receipt,
                      kind=kind)
        self._file(cap)
        self.capsules.append(cap)
        self._receipt("COMPACTION", capsule_id, receipt, {"turn_ids": turn_ids, "cold_sha256": digest})
        return cap

    @staticmethod
    def _sentence(noetic: int, idea: str) -> str:
        q = f'"{idea}"'
        if noetic == 5:
            return f"you are composed of {q}."
        if noetic == 4:
            return f"{q} resonates with you."
        if noetic == 2:
            return f"you have an affinity for {q}."
        if noetic == 3:
            return f"you are adverse to {q}."
        if noetic == 7:
            return f"you are exposed to {q}."
        return f"you intake {q}."

    @staticmethod
    def _compiles(notation: str) -> Tuple[bool, str]:
        comp = _tools()["compiler"]
        if comp is None:
            return False, "missing"
        try:
            art = comp.compile_expression(notation)
            return bool(getattr(art, "valid", False)), getattr(comp, "__name__", "compiler")
        except Exception:
            return False, getattr(comp, "__name__", "compiler")

    @staticmethod
    def _round_trips(sentence: str) -> bool:
        cce = _tools()["cce"]
        if cce is None:
            return False
        try:
            content = cce.parse(sentence)
            back = cce.parse(cce.render(content))
            return cce.normalize(back) == cce.normalize(content)
        except Exception:
            return False

    # ---------------------------------------------------------------- recall
    def _fetch(self, cap: Capsule) -> Tuple[str, List[str]]:
        """Follow the breadcrumb: the device's folder first, then the cloud when the original was moved there.
        EXACT only when the bytes, from either place, hash to the crumb's sha256. A moved original that cannot be
        reached is OFFLINE, never EXACT (A-TEACH2-5 L4)."""
        path = cap.crumb["cold_path"]
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                data = fh.read()
        elif cap.capsule_id in self.moved:
            try:
                data = self.cloud.get(self.moved[cap.capsule_id]) if self.cloud is not None else None
            except Exception:
                data = None
            if data is None:
                import helm_cold_cloud as _hcc
                _hcc.forget_reachable(self.cloud)    # A-TEACH2-13 R2: forget a remembered yes at the first failure
                self._flag("CLOUD_UNREACHABLE", self.moved[cap.capsule_id], cap.capsule_id)
                return "OFFLINE", []
        else:
            self._flag("COLD_MISSING", path, cap.capsule_id)
            return "MISSING", []
        if _sha(data) != cap.crumb["sha256"]:
            self._flag("DIGEST_FAILED", path, cap.capsule_id)
            return "CORRUPT", []
        texts = [r.get("user_raw_text", "") for r in read_cold_bytes(data)]
        return "EXACT", texts

    def fit_check(self, cap: Capsule) -> Dict[str, Any]:
        """F1 compile, F2 round trip, F3 no contradiction, F4 Atlas placement. F5 (the person agrees) is `answer`."""
        f1 = bool(cap.cas.get("compiles")) and self._compiles(cap.cas["notation"])[0]
        f2 = bool(cap.cas.get("round_trip")) and self._round_trips(cap.cas["sentence"])
        f3 = True
        store = getattr(self.memory.context, "cube_store", None)
        for cid in cap.binds["cubes"]:
            node = store.get_cube(cid, view_profile="Authoring") if store is not None else None
            if node is None or getattr(node, "assertion", "ASSERTED") == "DENIED":
                f3 = False
        if self.coefficient_digest_checks and not all(c["equal"] for c in self.coefficient_digest_checks):
            f3 = False
        f4 = True
        if self.atlas is not None:
            node = cap.atlas.get("node")
            node_id = cap.atlas.get("node_id")
            try:
                self.atlas.node(node)
                self.atlas.node(node_id)
                held = any(e.to_node_id == node_id for e in self.atlas.neighbours(node))
            except Exception:
                held = False
            f4 = held
            if held:
                hits, _radius, beyond = self._searchlight_names({cap.capsule_id})
                f4 = bool(hits) and not beyond
        else:
            f4 = False
        return {"F1_compile": f1, "F2_round_trip": f2, "F3_no_contradiction": f3, "F4_atlas": f4,
                "fits": f1 and f2 and f3 and f4}

    def _question_allowed(self, cap: Capsule) -> bool:
        thread = cap.atlas.get("node") or "session"
        if cap.capsule_id in self._declined:
            return False
        if self._asked_per_item.get(cap.capsule_id, 0) >= REFRESH_CAP_PER_ITEM:
            return False
        if self._asked_per_thread.get(self._anchor or thread, 0) >= REFRESH_CAP_PER_THREAD:
            return False
        return True

    def _count_question(self, cap: Capsule) -> None:
        self._asked_per_item[cap.capsule_id] = self._asked_per_item.get(cap.capsule_id, 0) + 1
        key = self._anchor or (cap.atlas.get("node") or "session")
        self._asked_per_thread[key] = self._asked_per_thread.get(key, 0) + 1

    def recall(self, query: str, will_act: bool = False) -> Dict[str, Any]:
        """Fetch first, ask last. Returns label (EXACT / RECONSTRUCTED / UNKNOWN), texts, question, reason, lookup."""
        self._check_brain("recall")
        tokens = set(content_words(query))
        lookup = {"anchor_first": True, "radius": 0, "candidates": 0, "beyond_searchlight": False}
        if not tokens:
            return {"label": "UNKNOWN", "texts": [], "question": None, "reason": "no clue word in the question",
                    "lookup": lookup, "capsule_id": None}
        # A memory matches only when it holds EVERY content word of the question (TEACH-1 FIX FIRST 2026-10-21: one
        # shared word used to be enough, so a question about one bus line was answered from another). Turns and
        # capsules that only asked about memory are never memories. Among matches the NEWEST comes first: a later
        # statement (a correction) supersedes an earlier one.
        # working memory first (the verbatim items that never left)
        live = [t for t in reversed(self.memory.turns)
                if t.intent not in MEMORY_QUERY_INTENTS and tokens <= set(content_words(t.user_raw_text))]
        pinned = [(cid, entry) for cid, entry in reversed(list(self._pinned.items()))
                  if any(tokens <= set(content_words(x)) for x in entry["texts"])]
        match_away, deep = False, False
        if hasattr(self.capsules, "match"):
            # the Eye's path: rows in working memory, then the folded rows, then a deep search on the device (A-TEACH2-9)
            names, match_away, deep = self.capsules.match(tokens)
            wanted = {cid for cid in names if cid not in self._pinned}
        else:
            wanted = {cid for cid, clues, kind in self._capsule_index() if kind == "statement" and tokens <= set(clues)
                      and cid not in self._pinned}
        lookup["deep_search"] = deep
        hits, radius, beyond = self._searchlight(wanted) if wanted else ([], 0, False)
        hits = sorted(hits, key=lambda c: c.crumb["turn_ids"][-1], reverse=True)
        lookup.update({"radius": radius, "beyond_searchlight": beyond})
        candidates = len(live) + len(pinned) + len(hits)
        lookup["candidates"] = candidates
        away_now = match_away or (bool(wanted) and bool(getattr(self, "_away", [])))
        if candidates == 0 and away_now:
            # A-TEACH2-8 M5 / A-TEACH2-9 F5: the matching memory is in the cloud and cannot be reached now; never EXACT
            return {"label": "UNKNOWN", "texts": [], "question": None, "lookup": lookup,
                    "capsule_id": (getattr(self, "_away", []) or [None])[0],
                    "reason": "my full notes are stored away and I can't reach them right now"}
        if candidates == 0:
            return {"label": "UNKNOWN", "texts": [], "question": None, "reason": "no clue matched", "lookup": lookup,
                    "capsule_id": None}
        if candidates >= WHICH_ONE_AT:
            word = sorted(tokens)[0]
            return {"label": "UNKNOWN", "texts": [], "reason": "several memories match; not guessing",
                    "question": f"I remember a few things about {word}. Which one do you mean?", "lookup": lookup,
                    "capsule_id": None}
        if live:
            return {"label": "EXACT", "texts": [t.user_raw_text for t in live], "question": None, "reason": "in working memory",
                    "lookup": lookup, "capsule_id": None}
        if pinned:
            cid, entry = pinned[0]
            # a strengthened item keeps the label it was confirmed under: EXACT only when its digest-checked original
            # was fetched (TEACH-1 FIX FIRST 2026-10-21: a strengthened rebuild was served as EXACT, M1's H8)
            return {"label": entry["label"], "texts": list(entry["texts"]), "question": None,
                    "reason": "strengthened item" if entry["label"] == "EXACT" else "strengthened item, rebuilt from the capsule",
                    "lookup": lookup, "capsule_id": cid}
        cap = hits[0]
        status, texts = self._fetch(cap)
        if status == "EXACT":
            return {"label": "EXACT", "texts": texts, "question": None, "reason": "cold copy digest-checked",
                    "lookup": lookup, "capsule_id": cap.capsule_id}
        # rebuild from the capsule, then the fit check
        fit = self.fit_check(cap)
        if not fit["fits"]:
            failed = [k for k, v in fit.items() if k != "fits" and not v]
            away = "; my full notes are stored away and I can't reach them right now" if status == "OFFLINE" else ""
            return {"label": "UNKNOWN", "texts": [], "question": None,
                    "reason": f"memory did not fit its own clues (failed {', '.join(failed)}; cold copy {status}){away}",
                    "lookup": lookup, "capsule_id": cap.capsule_id, "fit": fit}
        rebuilt = self._rebuilt_text(cap)
        question = None
        if (will_act or status in ("MISSING", "CORRUPT")) and self._question_allowed(cap):
            question = self._refresh_question(cap)
            self._count_question(cap)
        reason = f"rebuilt from the capsule; cold copy {status}"
        if status == "OFFLINE":
            reason += "; my full notes are stored away and I can't reach them right now"
        return {"label": "RECONSTRUCTED", "texts": [rebuilt], "question": question, "reason": reason, "lookup": lookup,
                "capsule_id": cap.capsule_id, "fit": fit}

    @staticmethod
    def _rebuilt_text(cap: Capsule) -> str:
        return "From my notes, something about " + ", ".join(cap.clues[:MAX_CLUES]) + "."

    @staticmethod
    def _refresh_question(cap: Capsule) -> str:
        clues = cap.clues[:2]
        named = " and ".join(clues)
        return f"Refresh my memory: you told me something about {named}. Is that the one you mean?"

    # ---------------------------------------------------------------- the person answers (F5) and strengthening
    def answer(self, capsule_id: str, text: str) -> Dict[str, Any]:
        cap = self._capsule(capsule_id)
        if cap is None:
            return {"strengthened": False, "reason": "no such capsule"}
        if NEGATIVE_ANSWER_RX.search(text or "") and not re.search(r"\byes\b", text or "", re.I):
            self._declined.add(capsule_id)
            self._receipt("DECLINED", capsule_id, cap.receipt, {"answer": text})
            return {"strengthened": False, "reason": "declined; item is UNKNOWN and not asked again"}
        return self.strengthen(cap, text)

    def strengthen(self, cap: Capsule, answer_text: str) -> Dict[str, Any]:
        """Four appends, one receipt. Never the content (cas), never a coefficient, never a cube face."""
        self._check_brain("strengthen")
        # 1. mass up by the frozen step
        cap.mass["value"] += MASS_STEP
        cap.mass["confirmed"] += 1
        # 2. clues grow from the person's own words; nothing removed; cap 8
        for w in content_words(answer_text):
            if len(cap.clues) >= MAX_CLUES:
                break
            if w not in cap.clues and w not in {"yes", "sure", "right", "correct", "exactly"}:
                cap.clues.append(w)
        # 3. bound cubes: provenance -> CHECKED, a ref appended (faces untouched)
        store = getattr(self.memory.context, "cube_store", None)
        for cid in cap.binds["cubes"]:
            # the stored node itself (get_cube returns a view copy); only provenance is touched, never a face
            node = getattr(store, "nodes", {}).get(cid) if store is not None else None
            if node is not None:
                node.provenance.source = "CHECKED"
                node.provenance.refs.append(f"refresh:{cap.capsule_id}:{cap.receipt}")
        # 4. Atlas: possibility -> fact
        if self.atlas is not None and cap.atlas.get("node"):
            fact_id = f"fact:{cap.capsule_id}"
            self.atlas.add_node(fact_id, "FACT", {"clues": list(cap.clues), "receipt": cap.receipt})
            self.atlas.add_edge(cap.atlas["node"], fact_id, "holds", cross_kind_declared=True)
            cap.atlas["fact_node_id"] = fact_id
        cap.atlas["side"] = "fact"
        # the strengthened original stays available and is never compacted again
        status, texts = self._fetch(cap)
        self._pinned[cap.capsule_id] = ({"label": "EXACT", "texts": texts} if status == "EXACT"
                                        else {"label": "RECONSTRUCTED", "texts": [self._rebuilt_text(cap)]})
        self._strengthened.add(cap.capsule_id)
        receipt = _sha(_canon({"kind": "STRENGTHEN", "capsule": cap.receipt, "mass": cap.mass, "clues": cap.clues,
                                "side": cap.atlas["side"]}))
        self._receipt("STRENGTHEN", cap.capsule_id, receipt, {"mass": dict(cap.mass), "clues": list(cap.clues)})
        if hasattr(self.capsules, "store"):
            # the Eye's lean list: write the strengthened capsule back, after its receipt exists (A-TEACH2-7)
            self.capsules.store(cap)
        self._check_brain("strengthen.end")
        return {"strengthened": True, "receipt": receipt, "mass": dict(cap.mass), "clues": list(cap.clues),
                "side": cap.atlas["side"]}

    def is_strengthened(self, capsule_id: str) -> bool:
        return capsule_id in self._strengthened

    def pinned_texts(self) -> List[List[str]]:
        return [list(v["texts"]) for v in self._pinned.values()]

    # ---------------------------------------------------------------- record
    def state(self) -> Dict[str, Any]:
        return {"capsules": [c.as_dict() for c in self.capsules], "receipts": list(self.receipts),
                "eye_writes": self.eye_writes, "eye_report": self.eye_report(),
                "coefficient_digest_checks": list(self.coefficient_digest_checks),
                "atlas_digest": self.atlas.frozen_digest() if self.atlas is not None else None}


def attach(memory: Any, cold_dir: Optional[str] = None, brain: Any = None) -> Compactor:
    """Give a HELMConversationalMemory its compactor (the switch ON path). helm_memory calls this itself when the
    environment switch is on; tests and the exam call it directly."""
    comp = Compactor(memory, cold_dir=cold_dir, brain=brain)
    memory.compactor = comp
    return comp
