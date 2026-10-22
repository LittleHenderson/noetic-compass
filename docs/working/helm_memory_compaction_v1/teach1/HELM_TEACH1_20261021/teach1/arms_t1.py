"""The seven arms of TEACH-1 as switch sets over `helm_chat.HELMConversationalSession.handle_turn` (pre-code section 3),
and the unit driver: one fresh process per (arm, world), the chat driven line by line exactly as a person would, replies
captured from standard output, the chat's own memory record read after every turn, transparent recorders on the
compactor's `housekeep` / `recall` / `answer` (they deep-copy results and change nothing), the frozen clock
(D-TEACH1-5), the socket guard, and the scripted person answering refresh questions from the key.

Arm variants (exam-side subclasses of the cut's Compactor; HELM files are the same bytes in every arm):
  COMPACT_ON / REPLAY / VERBATIM_ONLY  the cut's Compactor as shipped (VERBATIM_ONLY: budget 10,000, nothing compacts)
  FIFO_DROP                            no compactor (switch OFF): today's helm_memory
  SUMMARY_TEXT                         TextNoteCompactor: the same clues, breadcrumb and receipt; a plain-English note
                                       instead of a CAS expression; no compile, no round trip, no F1-F4 (D-TEACH1-4)
  NO_REFRESH                           NoRefreshCompactor: never asks (fetch-first stays)
  RANDOM_REFRESH                       RandomRefreshCompactor: asks about a random eligible item instead of the matched
                                       one, the same number of questions as COMPACT_ON asked in that world
Raw records only; every score and word comes from the frozen reader (reader_t1.py).
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import random
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import common_t1 as C
from . import person_t1 as P

STDOUT_KEEP = 4000
PHASES = ("TEACH",) + C.QUIZZES


# ============================================================================================ guards
def install_frozen_clock() -> Dict[str, Any]:
    """time.time() counts up from a fixed start; time.gmtime() is one fixed instant. Installed before HELM imports."""
    state = {"t": C.FROZEN_CLOCK_START, "calls": 0}
    real_time, real_gmtime = time.time, time.gmtime

    def ftime():
        state["t"] += C.FROZEN_CLOCK_TICK
        state["calls"] += 1
        return state["t"]

    def fgmtime(secs=None):
        return time.struct_time(C.FROZEN_CLOCK_UTC)
    time.time = ftime
    time.gmtime = fgmtime
    return {"installed": True, "start": C.FROZEN_CLOCK_START, "tick": C.FROZEN_CLOCK_TICK, "state": state,
            "real": (real_time, real_gmtime)}


def netguard() -> None:
    import socket

    def _deny(*a, **k):
        raise RuntimeError("NETWORK_FORBIDDEN_IN_TEACH1_UNIT")
    socket.socket = _deny          # type: ignore[assignment]
    socket.create_connection = _deny  # type: ignore[assignment]


# ============================================================================================ recorders (transparent)
class Recorder:
    """Wraps one bound method by attribute assignment on the instance; stores a deep copy of each result plus the
    digests taken before and after; returns the ORIGINAL object. Changes no input and no output."""

    def __init__(self, obj, name: str, digests) -> None:
        self.obj, self.name, self.digests = obj, name, digests
        self.original = getattr(obj, name)
        self.rows: List[Dict[str, Any]] = []
        original, rows, dg = self.original, self.rows, digests

        def wrapped(*a, **k):
            before = dg()
            res = original(*a, **k)
            after = dg()
            try:
                snap = copy.deepcopy(res)
            except Exception:
                snap = repr(res)
            if name == "housekeep":
                snap = [c.capsule_id for c in res]
            rows.append({"args": [repr(x)[:200] for x in a], "result": snap, "digests_before": before,
                         "digests_after": after, "digests_equal": before == after})
            return res
        wrapped.teach1_recorder = True   # type: ignore[attr-defined]
        setattr(obj, name, wrapped)


def brain_digest(loop) -> Dict[str, Optional[str]]:
    """The brain's learned state: the wide book's own learned_digest() and a canonical digest of the reference brain's
    requirement tables (HG-COEF: equal before and after every memory action)."""
    out: Dict[str, Optional[str]] = {"wide": None, "canonical": None}
    wb = getattr(loop, "wide_book", None)
    if wb is not None and hasattr(wb, "learned_digest"):
        out["wide"] = wb.learned_digest()
    b = getattr(loop, "brain", None)
    if b is not None and hasattr(b, "products") and hasattr(b, "requirements"):
        try:
            out["canonical"] = C.sha256_obj({p: b.requirements(p) for p in sorted(b.products)})
        except Exception as exc:  # pragma: no cover
            out["canonical"] = "ERROR:" + type(exc).__name__
    return out


# ============================================================================================ the arm variants
def make_variants(hmc):
    class NoRefreshCompactor(hmc.Compactor):
        ARM = "NO_REFRESH"

        def _question_allowed(self, cap) -> bool:
            return False

    class RandomRefreshCompactor(hmc.Compactor):
        ARM = "RANDOM_REFRESH"

        def __init__(self, *a, rng: random.Random, **k) -> None:
            super().__init__(*a, **k)
            self.rng = rng
            self.random_log: List[Dict[str, Any]] = []
            self.max_asks = 0          # = the number COMPACT_ON asked in this world (pre-code 3); set by the unit

        def _eligible(self):
            return [c for c in self.capsules if c.capsule_id not in self._declined
                    and self._asked_per_item.get(c.capsule_id, 0) < hmc.REFRESH_CAP_PER_ITEM
                    and not self.is_strengthened(c.capsule_id)
                    and getattr(c, "kind", "statement") == "statement"]

        def recall(self, query: str, will_act: bool = False) -> Dict[str, Any]:
            res = super().recall(query, will_act)
            if res.get("question") and res.get("capsule_id"):
                cid0 = res["capsule_id"]
                self._asked_per_item[cid0] = self._asked_per_item.get(cid0, 1) - 1
                key = self._anchor or "session"
                self._asked_per_thread[key] = self._asked_per_thread.get(key, 1) - 1
                pool = self._eligible()
                if len(self.random_log) >= self.max_asks:
                    res["answer_capsule_id"] = cid0
                    res["question"] = None          # the arm's question budget is spent: answer, ask nothing
                    res["random_budget_spent"] = True
                elif pool:
                    r = self.rng.choice(pool)
                    res["answer_capsule_id"] = cid0     # the capsule the ANSWER came from (the reader's H8 check)
                    res["capsule_id"] = r.capsule_id    # the capsule the QUESTION is about (the chat waits for its answer)
                    res["question"] = self._refresh_question(r)
                    res["random_instead_of"] = cid0
                    self._count_question(r)
                    self.random_log.append({"instead_of": cid0, "asked": r.capsule_id, "forced": False})
            return res

        def forced_ask(self) -> Optional[Dict[str, Any]]:
            pool = self._eligible()
            if not pool or len(self.random_log) >= self.max_asks:
                return None
            r = self.rng.choice(pool)
            self._count_question(r)
            self.random_log.append({"instead_of": None, "asked": r.capsule_id, "forced": True})
            return {"capsule_id": r.capsule_id, "question": self._refresh_question(r)}

    class TextNoteCompactor(hmc.Compactor):
        """SUMMARY_TEXT: the mechanism-free baseline. The same clues, cold copy, breadcrumb, binds, mass and receipt as
        the cut's _compact; a rule-written plain-English note stands where the CAS expression would; no compiler, no
        round trip, and the fit check is skipped (F1-F4 None, fits True)."""
        ARM = "SUMMARY_TEXT"

        def _compact(self, turns):
            records = [asdict(t) for t in turns]
            turn_ids = [t.turn_id for t in turns]
            capsule_id = f"cap-{self.memory.session_id}-{turn_ids[0]:06d}-{turn_ids[-1]:06d}"
            stated = [t for t in turns if t.intent not in hmc.MEMORY_QUERY_INTENTS]   # the cut's own rule
            kind = "statement" if stated else "question"
            clues: List[str] = []
            for t in (stated or turns):
                for w in hmc.content_words(t.user_raw_text):
                    if w not in clues:
                        clues.append(w)
                    if len(clues) >= hmc.MAX_CLUES:
                        break
                if len(clues) >= hmc.MAX_CLUES:
                    break
            if not clues:
                raise hmc.CompactRefused("NO_CLUES", "no verbatim content word to clue by")
            note = "A note about: " + ", ".join(clues) + "."
            cas = {"sentence": None, "notation": None, "compiles": None, "round_trip": None, "compiler": None, "note": note}
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
            os.makedirs(self.cold_dir, exist_ok=True)
            cold_path = os.path.join(self.cold_dir, f"{capsule_id}.jsonl")
            payload = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records).encode("utf-8")
            with open(cold_path, "wb") as fh:
                fh.write(payload)
            with open(cold_path, "rb") as fh:
                digest = hmc._sha(fh.read())
            if digest != hmc._sha(payload):
                raise hmc.CompactRefused("COLD_WRITE_FAILED", "digest after write differs")
            crumb = {"cold_path": cold_path, "sha256": digest, "turn_ids": turn_ids}
            mass = {"value": len(turn_ids), "confirmed": 0}
            receipt = hmc._receipt_of(capsule_id, cas, clues, binds, crumb, mass)
            cap = hmc.Capsule(capsule_id=capsule_id, cas=cas, clues=clues, binds=binds, crumb=crumb, mass=mass,
                              receipt=receipt, kind=kind)
            self._file(cap)
            self.capsules.append(cap)
            self._receipt("COMPACTION", capsule_id, receipt, {"turn_ids": turn_ids, "cold_sha256": digest})
            return cap

        def fit_check(self, cap) -> Dict[str, Any]:
            return {"F1_compile": None, "F2_round_trip": None, "F3_no_contradiction": None, "F4_atlas": None, "fits": True}

        @staticmethod
        def _rebuilt_text(cap) -> str:
            return "From my notes, something about " + ", ".join(cap.clues) + "."

    return {"NO_REFRESH": NoRefreshCompactor, "RANDOM_REFRESH": RandomRefreshCompactor, "SUMMARY_TEXT": TextNoteCompactor}


# ============================================================================================ the unit
def capsule_hash(cap_dict: Dict[str, Any]) -> str:
    """sha256 over a capsule without its machine-bound cold path (HG-REPLAY compares these)."""
    d = copy.deepcopy(cap_dict)
    d.get("crumb", {}).pop("cold_path", None)
    return C.sha256_obj(d)


class Unit:
    def __init__(self, arm: str, world: Dict[str, Any], plan: List[Dict[str, Any]], turns: List[Dict[str, Any]],
                 quiz: Dict[str, Any], damage: List[Dict[str, Any]], seeds: Dict[str, Any], scratch: Path,
                 compact_on_asks: Optional[Dict[str, int]] = None, helm_dir_override: Optional[str] = None) -> None:
        if arm not in C.ARMS:
            raise ValueError(arm)
        self.arm, self.world, self.plan, self.turns, self.quiz, self.damage, self.seeds = arm, world, plan, turns, quiz, damage, seeds
        self.scratch = Path(scratch)
        self.compact_on_asks = compact_on_asks or {}
        self.helm_dir_override = helm_dir_override
        self.rec: Dict[str, Any] = {"schema": "helm.teach1.unit/1", "arm": arm, "world_id": world["world_id"],
                                    "practice_mock": bool(seeds.get("practice_mock")), "turns": [], "quiz": [],
                                    "refresh": [], "errors": [], "phase_marks": {}}

    # ------------------------------------------------------------------ set-up
    def start(self) -> None:
        sw = C.ARM_SWITCH[self.arm]
        os.environ["HELM_MEMORY_COMPACT"] = sw["HELM_MEMORY_COMPACT"]
        os.environ["HELM_SESSION_DIR"] = str(self.scratch / "sessions")
        os.environ.pop("HELM_WIDE_BRAIN", None)
        self.clock = install_frozen_clock()
        netguard()
        if self.helm_dir_override:
            os.environ["TEACH1_HELM_DIR"] = self.helm_dir_override
        self.helm = C.import_helm_now(check=not self.helm_dir_override)
        hc, hmc = self.helm["helm_chat"], self.helm["helm_memory_compact"]
        base_arm = "COMPACT_ON" if self.arm == "REPLAY" else self.arm
        session_id = f"teach1-{self.world['world_id']}-{base_arm}"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.session = hc.HELMConversationalSession(mode="everyday", session_id=session_id)
        self.session.memory.max_turns = sw["budget"]
        self.comp = None
        if self.arm != "FIFO_DROP":
            variants = make_variants(hmc)
            cold = str(self.scratch / "cold")
            brain = getattr(self.session.loop, "wide_book", None)
            if self.arm in variants:
                cls = variants[self.arm]
                if self.arm == "RANDOM_REFRESH":
                    rng = random.Random(f"{self.seeds['RANDOM_REFRESH']}:random:{self.world['world_id']}")
                    self.comp = cls(self.session.memory, cold_dir=cold, brain=brain, rng=rng)
                    self.comp.max_asks = int(self.compact_on_asks.get(self.world["world_id"], 0))
                else:
                    self.comp = cls(self.session.memory, cold_dir=cold, brain=brain)
            else:
                self.comp = hmc.Compactor(self.session.memory, cold_dir=cold, brain=brain)
            self.session.memory.compactor = self.comp
            self.r_house = Recorder(self.comp, "housekeep", self.digests)
            self.r_recall = Recorder(self.comp, "recall", self.digests)
            self.r_answer = Recorder(self.comp, "answer", self.digests)
        else:
            if getattr(self.session.memory, "compactor", None) is not None:
                raise C.PinRefused("FIFO_DROP unit found a compactor attached")
        self.person = P.ScriptedPerson(self.world, self.turns, self.seeds["PERSON"])
        self.sent: List[str] = []
        self.rec.update({"session_id": session_id, "budget": sw["budget"], "switch": sw["HELM_MEMORY_COMPACT"],
                         "compactor_class": type(self.comp).__name__ if self.comp else None,
                         "helm_now_dir": str(C.helm_now_dir()), "helm_dir_override": self.helm_dir_override,
                         "helm_chat_file": hc.__file__, "frozen_clock": {"start": self.clock["start"], "tick": self.clock["tick"]},
                         "digests_start": self.digests(), "eye_report_only": True,
                         "cold_dir_empty_at_start": not os.path.isdir(str(self.scratch / "cold")) or not os.listdir(str(self.scratch / "cold"))})

    def digests(self) -> Dict[str, Any]:
        hmc = self.helm["helm_memory_compact"]
        store = getattr(self.session.memory.context, "cube_store", None)
        d = brain_digest(self.session.loop)
        d["cube_faces"] = hmc.cube_faces_digest(store) if store is not None else None
        return d

    # ------------------------------------------------------------------ one line to the chat
    def say(self, text: str, phase: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        hv = self.helm["helm_voice"]
        before = self.digests()
        buf = io.StringIO()
        n_recall = len(self.r_recall.rows) if self.comp else 0
        n_house = len(self.r_house.rows) if self.comp else 0
        err = None
        try:
            with contextlib.redirect_stdout(buf):
                self.session.handle_turn(text)
        except SystemExit as exc:  # never: "exit" is never sent
            err = f"SystemExit:{exc}"
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
        self.sent.append(text)
        t = self.session.memory.turns[-1] if self.session.memory.turns else None
        reply = t.helm_response if t is not None and t.user_raw_text == text else buf.getvalue().strip()
        row = {"phase": phase, "text": text, "intent": t.intent if t is not None and t.user_raw_text == text else None,
               "reply": reply, "stdout": buf.getvalue()[:STDOUT_KEEP], "error": err,
               "cas_tokens": len(hv.cas_tokens(reply or "")),
               "turns_live": len(self.session.memory.turns), "user_facts": len(self.session.memory.context.user_facts),
               "capsules": len(self.comp.capsules) if self.comp else None,
               "receipts": len(self.comp.receipts) if self.comp else None,
               "housekeeps_this_turn": (len(self.r_house.rows) - n_house) if self.comp else 0,
               "digests_before": before, "digests_after": self.digests()}
        row.update(meta)
        if self.comp and len(self.r_recall.rows) > n_recall:
            row["recall"] = self.r_recall.rows[-1]["result"]
            row["recall_digests_equal"] = self.r_recall.rows[-1]["digests_equal"]
        if err:
            self.rec["errors"].append({"phase": phase, "text": text, "error": err})
        return row

    # ------------------------------------------------------------------ phases
    def teach(self) -> None:
        for t in self.turns:
            row = self.say(t["text"], "TEACH", {"turn_index": t["turn_index"], "kind": t["kind"], "fact_id": t["fact_id"],
                                                 "value": t.get("value"), "not_value": t.get("not_value"), "label": t.get("label")})
            self.rec["turns"].append(row)

    def _capsule(self, cid: str):
        return next((c for c in self.comp.capsules if c.capsule_id == cid), None)

    def _cold_check(self, cid: Optional[str]) -> Optional[Dict[str, Any]]:
        cap = self._capsule(cid) if cid else None
        if cap is None:
            return None
        path = cap.crumb["cold_path"]
        exists = os.path.isfile(path)
        sha = C.sha256_file(path) if exists else None
        return {"exists": exists, "file_sha256": sha, "crumb_sha256": cap.crumb["sha256"], "ok": exists and sha == cap.crumb["sha256"],
                "turn_ids": list(cap.crumb["turn_ids"]), "clues": list(cap.clues), "strengthened": self.comp.is_strengthened(cid)}

    def _answer_refresh(self, phase: str, pos: int, cid: str, question: str, forced: bool = False) -> Dict[str, Any]:
        cap = self._capsule(cid)
        ans = self.person.answer(list(cap.crumb["turn_ids"]) if cap else [], cid)
        n_str = len(self.comp._strengthened)
        row = self.say(ans["text"], phase, {"refresh_answer_for": cid, "quiz_pos": pos, "person": ans, "forced": forced,
                                            "question": question})
        row["strengthened"] = self.comp.is_strengthened(cid)
        row["strengthened_delta"] = len(self.comp._strengthened) - n_str
        row["clue_quoted"] = any(c in (question or "").lower() for c in (cap.clues if cap else []))
        self.rec["refresh"].append(row)
        return row

    def quiz_phase(self, phase: str) -> None:
        items, order = self.quiz["items"], self.quiz["orders"][phase]
        for pos, idx in enumerate(order):
            it = items[idx]
            row = self.say(it["question"], phase, {"quiz_pos": pos, "item_index": idx, "fact_id": it["fact_id"],
                                                    "kind": it["kind"], "slot": it["slot"], "value": it["value"],
                                                    "not_value": it.get("not_value")})
            rc = row.get("recall") or {}
            row["cold_check"] = self._cold_check(rc.get("answer_capsule_id") or rc.get("capsule_id")) if self.comp else None
            self.rec["quiz"].append(row)
            if self.comp and rc.get("question") and rc.get("capsule_id"):
                self._answer_refresh(phase, pos, rc["capsule_id"], rc["question"])
        if self.arm == "RANDOM_REFRESH" and phase == "Q_SQUEEZED":
            want = int(self.compact_on_asks.get(self.world["world_id"], 0))
            have = len(self.comp.random_log)
            while have < want:
                q = self.comp.forced_ask()
                if q is None:
                    break
                self.rec["quiz"].append({"phase": phase, "forced_question": q, "text": None, "reply": q["question"],
                                         "cas_tokens": len(self.helm["helm_voice"].cas_tokens(q["question"]))})
                self._answer_refresh(phase, -1, q["capsule_id"], q["question"], forced=True)
                have += 1

    def crumb_sweep(self, label: str) -> Dict[str, Any]:
        if not self.comp:
            return {"label": label, "capsules": 0, "ok": 0, "bad": []}
        bad = []
        for c in self.comp.capsules:
            chk = self._cold_check(c.capsule_id)
            if not chk["ok"]:
                bad.append({"capsule_id": c.capsule_id, "exists": chk["exists"]})
        out = {"label": label, "capsules": len(self.comp.capsules), "ok": len(self.comp.capsules) - len(bad), "bad": bad}
        self.rec.setdefault("crumb_sweeps", []).append(out)
        return out

    def plant_damage(self) -> None:
        planted = []
        if self.comp:
            turn_of = {}
            for t in self.turns:
                if t["kind"] == "FACT" and t["fact_id"]:
                    turn_of.setdefault(t["fact_id"], t["turn_index"])
            for d in self.damage:
                tid = turn_of.get(d["fact_id"])
                cap = next((c for c in self.comp.capsules if tid in c.crumb["turn_ids"]), None)
                row = {"fact_id": d["fact_id"], "damage": d["damage"], "turn_index": tid,
                       "capsule_id": cap.capsule_id if cap else None, "done": False}
                if cap is not None and os.path.isfile(cap.crumb["cold_path"]):
                    if d["damage"] == "DELETE":
                        os.remove(cap.crumb["cold_path"])
                    else:
                        with open(cap.crumb["cold_path"], "ab") as fh:
                            fh.write(b"\n{\"planted\": \"damage\"}\n")
                    row["done"] = True
                planted.append(row)
        self.rec["planted_damage"] = planted

    def finish(self) -> Dict[str, Any]:
        rec = self.rec
        rec["sent_texts"] = list(self.sent)
        rec["digests_end"] = self.digests()
        rec["user_facts_end"] = list(self.session.memory.context.user_facts)
        rec["turns_live_end"] = [t.user_raw_text for t in self.session.memory.turns]
        if self.comp:
            st = self.comp.state()
            rec["capsules_end"] = st["capsules"]
            rec["capsule_hashes"] = {c["capsule_id"]: capsule_hash(c) for c in st["capsules"]}
            rec["receipts_end"] = st["receipts"]
            rec["eye_writes"] = st["eye_writes"]
            rec["eye_report"] = st["eye_report"]
            rec["coefficient_digest_checks"] = st["coefficient_digest_checks"]
            rec["atlas_digest"] = st["atlas_digest"]
            rec["pinned"] = {k: list(v) for k, v in self.comp._pinned.items()}
            rec["strengthened"] = sorted(self.comp._strengthened)
            rec["declined"] = sorted(self.comp._declined)
            rec["recorder_rows"] = {"housekeep": self.r_house.rows, "answer": self.r_answer.rows}
            rec["random_log"] = getattr(self.comp, "random_log", None)
            cold_dir = str(self.scratch / "cold")
            rec["cold_files"] = sorted(os.listdir(cold_dir)) if os.path.isdir(cold_dir) else []
        rec["ledger_file"] = self.session.memory.session_file
        rec["clock_calls"] = self.clock["state"]["calls"]
        return rec

    def run(self) -> Dict[str, Any]:
        self.start()
        self.teach()
        self.rec["phase_marks"]["after_teach"] = {"capsules": len(self.comp.capsules) if self.comp else None,
                                                  "turns_live": len(self.session.memory.turns)}
        self.quiz_phase("Q_TAUGHT")
        self.crumb_sweep("before_damage")
        self.plant_damage()
        self.crumb_sweep("after_damage")
        self.quiz_phase("Q_SQUEEZED")
        self.quiz_phase("Q_REFRESHED")
        return self.finish()
