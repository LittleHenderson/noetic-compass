"""The eleven arms of TEACH-2 as switch sets over `helm_chat.HELMConversationalSession.handle_turn` (pre-code section 3
as amended by A-TEACH2-3, -15 T4 and -18 P5), and the unit driver: one fresh process per (arm, world), the chat driven
line by line exactly as a person would, replies captured from standard output, the chat's own memory record read after
every turn, transparent recorders (they deep-copy results and change nothing), the frozen clock, the socket guard, the
scripted person answering refresh questions from the key, and a stand-in cloud with an offline window.

Every arm's variant is set up here, on the exam side; HELM files are the same bytes in every arm:
  VERBATIM_ONLY  the cut's Compactor, budget 10,000 (nothing compacts); no cube        (TEACH-1 VERBATIM_ONLY)
  QUOTE_ONLY     the cut's Compactor, budget 12; no cube                                (TEACH-1 COMPACT_ON)
  FIFO_DROP      no compactor, budget 12                                                (today's helm_memory)
  TABLE          no compactor, budget 12; CubeOsc TABLE with the exam's rule reader    (a plain dict)
  TABLE_OSC      no compactor, budget 12; CubeOsc TABLE_OSC with the CTT's rounds      (reported)
  CUBE_OSC       helm_cube_osc.attach(OSC, the CTT's three copies) at the frozen limits, stand-in cloud
  REPLAY         CUBE_OSC again, fresh process
  ONE_READER     attach(ONE_READER, the rule reader) at the limits
  CTT_ONLY       attach(CTT_ONLY, the CTT) at the limits
  EYE_OFF        CUBE_OSC with the Eye's lean records, move-off and folding off (a plain capsule list)   (reported)
  FIRST8         CUBE_OSC with clue words from the first lines only (clue_every_line off)                 (reported)
Raw records only; every score and word comes from the frozen reader (reader_t2.py).
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import common_t2 as C
from . import person_t2 as P

STDOUT_KEEP = 4000


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
    """No network in a unit. `ssl` and `http.client` are imported first: `ssl` subclasses `socket.socket` at import
    time (HELM's direct cloud client imports it), and nothing in them opens a connection until asked to."""
    import http.client  # noqa: F401
    import socket
    import ssl  # noqa: F401

    def _deny(*a, **k):
        raise RuntimeError("NETWORK_FORBIDDEN_IN_TEACH2_UNIT")
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
        wrapped.teach2_recorder = True   # type: ignore[attr-defined]
        setattr(obj, name, wrapped)


def brain_digest(loop) -> Dict[str, Optional[str]]:
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


def _reading_dict(r) -> Optional[Dict[str, Any]]:
    if r is None:
        return None
    return {"thing": r.thing, "slot": sorted(r.slot), "value": r.value, "replaces": r.replaces}


# ============================================================================================ the unit
class Unit:
    def __init__(self, arm: str, world: Dict[str, Any], plan: List[Dict[str, Any]], turns: List[Dict[str, Any]],
                 quiz: Dict[str, Any], damage: List[Dict[str, Any]], offline_phase: str, seeds: Dict[str, Any],
                 scratch: Path, limits: Optional[Dict[str, Any]] = None, helm_dir_override: Optional[str] = None,
                 ctt_python: Optional[str] = None) -> None:
        if arm not in C.ARMS:
            raise ValueError(arm)
        self.arm, self.world, self.plan, self.turns, self.quiz, self.damage = arm, world, plan, turns, quiz, damage
        self.offline_phase, self.seeds, self.limits = offline_phase, seeds, limits
        self.scratch = Path(scratch)
        self.helm_dir_override = helm_dir_override
        self.ctt_python = ctt_python
        self.set = C.ARM_SET[arm]
        self.cube_arm = arm in C.CUBE_ARMS
        if self.cube_arm and not limits:
            raise C.PinRefused(f"{arm} needs the frozen limits (LIMITS_TEACH2.json) first")
        self.rec: Dict[str, Any] = {"schema": "helm.teach2.unit/1", "arm": arm, "world_id": world["world_id"],
                                    "practice_mock": bool(seeds.get("practice_mock")), "turns": [], "quiz": [],
                                    "refresh": [], "errors": [], "phase_marks": {}, "offline_phase": offline_phase,
                                    "limits_used": limits if self.cube_arm else None}

    # ------------------------------------------------------------------ set-up
    def start(self) -> None:
        os.environ["HELM_MEMORY_COMPACT"] = self.set["compact"]
        os.environ["HELM_SESSION_DIR"] = str(self.scratch / "sessions")
        for k in ("HELM_WIDE_BRAIN", "HELM_CUBE_OSC", "HELM_EYE_ACT"):
            os.environ.pop(k, None)
        self.client = None
        if self.arm in C.CTT_ARMS:
            # the serving process starts before the guards: it is a separate, audited process (A-TEACH2-18 P2)
            from . import ctt_client
            self.client = ctt_client.CTTClient(self.scratch / "ctt_audit.json", with_twin=self.arm == "CUBE_OSC",
                                               python=self.ctt_python)
        self.clock = install_frozen_clock()
        netguard()
        if self.helm_dir_override:
            os.environ["TEACH2_HELM_DIR"] = self.helm_dir_override
        self.helm = C.import_helm_now(check=not self.helm_dir_override)
        hc, hmc, hco, hcc = (self.helm[k] for k in ("helm_chat", "helm_memory_compact", "helm_cube_osc", "helm_cold_cloud"))
        base_arm = "CUBE_OSC" if self.arm == "REPLAY" else self.arm
        session_id = f"teach2-{self.world['world_id']}-{base_arm}"
        with contextlib.redirect_stdout(io.StringIO()):
            self.session = hc.HELMConversationalSession(mode="everyday", session_id=session_id)
        mem = self.session.memory
        mem.max_turns = self.set["budget"]
        cold = str(self.scratch / "cold")
        brain = getattr(self.session.loop, "wide_book", None)
        self.comp, self.osc, self.cloud = None, None, None
        if self.set["compact"] == "1":
            self.comp = hmc.Compactor(mem, cold_dir=cold, brain=brain)
            mem.compactor = self.comp
        elif getattr(mem, "compactor", None) is not None:
            raise C.PinRefused(f"{self.arm} unit found a compactor attached with the switch off")
        reader = None
        if self.arm in C.RULE_ARMS:
            from .teach2_rule_reader import rule_read
            reader = rule_read
        proposers = self.client.proposers(hco) if self.client is not None else None
        mode = self.set["mode"]
        if self.cube_arm:
            self.cloud = hcc.FakeCloud(online=True)
            lim = int(self.limits["working_limit_bytes"])
            self.osc = hco.attach(mem, mode=mode, proposers=proposers, reader=reader, limit_bytes=lim,
                                  local_limit_bytes=int(self.limits["device_limit_bytes"]), cloud=self.cloud,
                                  cloud_prefix=f"teach/{session_id}/")
            self.comp = mem.compactor
            if self.set.get("eye_off"):
                self.comp.capsules = []                       # a plain list: no lean records, no move-off, no folding
            if self.set.get("first8"):
                self.comp.clue_every_line = False             # clue words from the first lines only
        elif mode in ("TABLE", "TABLE_OSC"):
            self.osc = hco.CubeOsc(mem, mode=mode, proposers=proposers, sweep=False, reader=reader)
            mem.cube_osc = self.osc
        if self.comp is not None:
            self.r_house = Recorder(self.comp, "housekeep", self.digests)
            self.r_recall = Recorder(self.comp, "recall", self.digests)
            self.r_answer = Recorder(self.comp, "answer", self.digests)
        if self.osc is not None:
            self.r_osc_answer = Recorder(self.osc, "answer", self.digests)
            self.r_observe = Recorder(self.osc, "observe", self.digests)
        # A-TEACH2-19 K4: the truth an answer label is checked against is taken AT THE MOMENT OF THE ANSWER (inside the
        # call), before the chat records the question as a new line (which can drop or fade the source line)
        self.recall_truth: List[Any] = []
        self.osc_truth: List[Any] = []
        if self.comp is not None:
            rec_recall = self.comp.recall

            def recall_with_truth(*a, **k):
                res = rec_recall(*a, **k)
                cid = (res.get("answer_capsule_id") or res.get("capsule_id")) if isinstance(res, dict) else None
                self.recall_truth.append(self.copy_state(cid) if cid else None)
                return res
            self.comp.recall = recall_with_truth
        if self.osc is not None:
            rec_answer = self.osc.answer

            def answer_with_truth(*a, **k):
                res = rec_answer(*a, **k)
                self.osc_truth.append(self._cube_truth(res))
                return res
            self.osc.answer = answer_with_truth
        # every say-back line (HG-SAYBACK): a transparent wrapper on the module's renderer
        self.saybacks: List[Dict[str, Any]] = []
        original_say_back = hco.say_back
        saybacks = self.saybacks
        cas_tokens = self.helm["helm_voice"].cas_tokens

        def say_back_rec(r):
            line = original_say_back(r)
            saybacks.append({"line": line, "reading": _reading_dict(r), "cas_tokens": len(cas_tokens(line))})
            return line
        hco.say_back = say_back_rec
        self.person = P.ScriptedPerson(self.world, self.turns, self.seeds["PERSON"])
        self.sent: List[str] = []
        self.branch_snapshots: List[List[str]] = []
        self.table_text: Dict[Any, str] = {}
        self.bytes_log: List[Dict[str, Any]] = []
        self.rec.update({"session_id": session_id, "budget": self.set["budget"], "switch": self.set["compact"],
                         "cube_mode": mode, "eye_off": bool(self.set.get("eye_off")), "first8": bool(self.set.get("first8")),
                         "compactor_class": type(self.comp).__name__ if self.comp else None,
                         "capsule_list_class": type(self.comp.capsules).__name__ if self.comp else None,
                         "clue_every_line": getattr(self.comp, "clue_every_line", None) if self.comp else None,
                         "proposers": [getattr(p, "name", type(p).__name__) for p in (proposers or [])],
                         "proposers_are_ctt": [bool(getattr(p, "is_ctt", False)) for p in (proposers or [])],
                         "reader": "teach2_rule_reader.rule_read" if reader else None,
                         "helm_now_dir": str(C.helm_now_dir()), "helm_dir_override": self.helm_dir_override,
                         "helm_chat_file": hc.__file__, "frozen_clock": {"start": self.clock["start"], "tick": self.clock["tick"]},
                         "digests_start": self.digests(), "eye_report_only": True,
                         "cold_dir_empty_at_start": not os.path.isdir(cold) or not os.listdir(cold)})

    def digests(self) -> Dict[str, Any]:
        hmc = self.helm["helm_memory_compact"]
        store = getattr(self.session.memory.context, "cube_store", None)
        d = brain_digest(self.session.loop)
        d["cube_faces"] = hmc.cube_faces_digest(store) if store is not None else None
        return d

    # ------------------------------------------------------------------ plain reads of the memory (no HELM method)
    def working_bytes(self) -> int:
        """The working-memory byte count of A-TEACH2-2 B8 for every arm: the cube oscillator's own count on the
        size-limit path; elsewhere live user lines + capsules' canonical JSON (the same rule)."""
        if self.cube_arm and self.osc is not None:
            return self.osc.working_bytes()
        hmc = self.helm["helm_memory_compact"]
        total = sum(len(t.user_raw_text.encode("utf-8")) for t in self.session.memory.turns)
        for cap in (self.comp.capsules if self.comp else []):
            total += len(hmc._canon(cap.as_dict()))
        return total

    def _compactions(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for r in (self.comp.receipts if self.comp else []):
            if r.get("kind") == "COMPACTION":
                out[r["capsule_id"]] = {"turn_ids": list(r.get("turn_ids") or []), "cold_sha256": r.get("cold_sha256")}
        return out

    def copy_state(self, capsule_id: Optional[str]) -> Dict[str, Any]:
        """Where the capsule's verbatim original is and whether it checks: the device folder, else the stand-in cloud's
        stored bytes (read from its dict, never through its API), and whether the cloud is online now."""
        info = self._compactions().get(capsule_id or "")
        if info is None:
            return {"capsule_id": capsule_id, "known": False, "ok": False, "where": None, "reachable": False}
        hmc = self.helm["helm_memory_compact"]
        path = os.path.join(self.comp.cold_dir, f"{capsule_id}.jsonl")
        if os.path.isfile(path):
            ok = C.sha256_file(path) == info["cold_sha256"]
            return {"capsule_id": capsule_id, "known": True, "ok": ok, "where": "device", "reachable": True,
                    "turn_ids": info["turn_ids"]}
        key = (getattr(self.comp, "moved", {}) or {}).get(capsule_id)
        if key and self.cloud is not None and key in self.cloud.objects:
            ok = hmc._sha(self.cloud.objects[key]) == info["cold_sha256"]
            return {"capsule_id": capsule_id, "known": True, "ok": ok, "where": "cloud", "reachable": bool(self.cloud.online),
                    "turn_ids": info["turn_ids"]}
        return {"capsule_id": capsule_id, "known": True, "ok": False, "where": "missing", "reachable": False,
                "turn_ids": info["turn_ids"]}

    def turn_state(self, turn_id: Optional[int], text: Optional[str] = None) -> Dict[str, Any]:
        """Whether a person's line is fetchable word for word right now: live, or in a capsule whose original checks
        and can be reached (the truth HG-H8 / HG-OFFLINE compare a label against)."""
        if turn_id is None:
            return {"turn_id": None, "exact_now": False, "where": None}
        if any(t.turn_id == turn_id and (text is None or t.user_raw_text == text) for t in self.session.memory.turns):
            return {"turn_id": turn_id, "exact_now": True, "where": "live"}
        if text is not None:        # A-TEACH2-21 R1: a table arm keeps no capsules; a line not live is gone
            return {"turn_id": turn_id, "exact_now": False, "where": "dropped"}
        cid = next((c for c, i in self._compactions().items() if turn_id in i["turn_ids"]), None)
        cs = self.copy_state(cid)
        return {"turn_id": turn_id, "exact_now": bool(cs["ok"] and cs["reachable"]), "where": cs["where"],
                "capsule_id": cid, "copy_ok": cs["ok"], "reachable": cs["reachable"]}

    def _cube_truth(self, oa) -> Optional[Dict[str, Any]]:
        """The truth behind a cube or table answer, taken inside the answer call (K4)."""
        if not isinstance(oa, dict):
            return None
        if oa.get("source_turn") is not None:
            return self.turn_state(oa.get("source_turn"))
        if oa.get("operation") == "TABLE_LOOKUP":
            # A-TEACH2-20 D3: a table answer names no source line; find it from the entry its own words name
            keys = [k for k in self.osc.table_src
                    if f"{k[0].capitalize()}, {' '.join(sorted(k[1]))}: {self.osc.table[k]}." in (oa.get("text") or "")]
            if len(keys) == 1:
                return self.turn_state(self.osc.table_src[keys[0]], self.table_text.get(keys[0]))
            return {"turn_id": None, "exact_now": False, "where": "unknown", "matches": len(keys)}
        return None

    def store_branches(self) -> List[Dict[str, Any]]:
        store = getattr(self.session.memory.context, "cube_store", None)
        if store is None:
            return []
        return [{"branch_id": b.branch_id, "source": b.source_node_id, "target": b.target_node_id,
                 "predicate": b.predicate, "commonality": dict(b.commonality or {}),
                 "provenance_refs": list(b.provenance_refs)} for b in store.branches]

    # ------------------------------------------------------------------ one line to the chat
    def say(self, text: str, phase: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        hv = self.helm["helm_voice"]
        before = self.digests()
        buf = io.StringIO()
        n_recall = len(self.r_recall.rows) if self.comp else 0
        n_house = len(self.r_house.rows) if self.comp else 0
        n_oans = len(self.r_osc_answer.rows) if self.osc else 0
        n_obs = len(self.r_observe.rows) if self.osc else 0
        n_say = len(self.saybacks)
        n_flags = len(self.comp._eye_flags) if self.comp else 0
        err = None
        try:
            with contextlib.redirect_stdout(buf):
                self.session.handle_turn(text)
        except SystemExit as exc:
            err = f"SystemExit:{exc}"
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
        self.sent.append(text)
        mem = self.session.memory
        t = mem.turns[-1] if mem.turns and mem.turns[-1].user_raw_text == text else None
        reply = t.helm_response if t is not None else buf.getvalue().strip()
        wb = self.working_bytes()
        row = {"phase": phase, "text": text, "intent": t.intent if t is not None else None,
               "turn_id": t.turn_id if t is not None else None, "reply": reply, "stdout": buf.getvalue()[:STDOUT_KEEP],
               "error": err, "cas_tokens": len(hv.cas_tokens(reply or "")), "turns_live": len(mem.turns),
               "user_facts": len(mem.context.user_facts), "working_bytes": wb,
               "cloud_online": None if self.cloud is None else bool(self.cloud.online),
               "capsules": len(self._compactions()) if self.comp else None,
               "housekeeps_this_turn": (len(self.r_house.rows) - n_house) if self.comp else 0,
               "digests_before": before, "digests_after": self.digests()}
        row.update(meta)
        if self.comp and len(self.r_recall.rows) > n_recall:
            rc = self.r_recall.rows[-1]["result"]
            row["recall"] = rc
            row["recall_digests_equal"] = self.r_recall.rows[-1]["digests_equal"]
            row["copy_state"] = self.recall_truth[-1] if self.recall_truth else None
        if self.osc is not None and len(self.r_osc_answer.rows) > n_oans:
            # the chat calls CubeOsc.answer twice per memory turn (test, then speak); the last result is the one spoken
            oa = self.r_osc_answer.rows[-1]["result"]
            row["cube_answer"] = oa
            truth = self.osc_truth[-1] if self.osc_truth else None
            if truth is not None:
                row["cube_source_state"] = truth
        if self.osc is not None and len(self.r_observe.rows) > n_obs:
            row["observe"] = [r["result"] for r in self.r_observe.rows[n_obs:]]
            for ob in row["observe"]:          # A-TEACH2-21 R1: the person's line behind every table entry
                rd = ob.get("reading") if isinstance(ob, dict) and ob.get("stored") == "table" else None
                if rd:
                    self.table_text[(rd["thing"], frozenset(rd["slot"]))] = text
        row["saybacks"] = self.saybacks[n_say:]
        if self.osc is not None:
            row["limit_flag"] = getattr(self.osc, "_last_limit_flag", None)
        row["flags_raised"] = [f["kind"] for f in self.comp._eye_flags[n_flags:]] if self.comp else []
        self.branch_snapshots.append([b["branch_id"] for b in self.store_branches()])
        self.bytes_log.append({"phase": phase, "turn_id": row["turn_id"], "working_bytes": wb,
                               "limit_flag": row.get("limit_flag"), "flags_raised": row["flags_raised"]})
        if err:
            self.rec["errors"].append({"phase": phase, "text": text, "error": err})
        return row

    # ------------------------------------------------------------------ phases
    def teach(self) -> None:
        hco = self.helm["helm_cube_osc"]
        for t in self.turns:
            row = self.say(t["text"], "TEACH", {"turn_index": t["turn_index"], "kind": t["kind"], "fact_id": t["fact_id"],
                                                 "value": t.get("value"), "not_value": t.get("not_value"),
                                                 "trap_role": t.get("trap_role"), "label": t.get("label")})
            if self.client is not None and self.arm == "CUBE_OSC":
                row["twin"] = self.client.twin(hco, t["text"])          # A5-s1, reported only (A-TEACH2-18 P3)
            self.rec["turns"].append(row)

    def _answer_refresh(self, phase: str, pos: int, cid: str, question: str) -> Dict[str, Any]:
        info = self._compactions().get(cid) or {"turn_ids": []}
        ans = self.person.answer(list(info["turn_ids"]), cid)
        n_str = len(self.comp._strengthened)
        row = self.say(ans["text"], phase, {"refresh_answer_for": cid, "quiz_pos": pos, "person": ans, "question": question})
        row["strengthened"] = self.comp.is_strengthened(cid)
        row["strengthened_delta"] = len(self.comp._strengthened) - n_str
        row["clue_quoted"] = bool(re.search(r"something about \w+", question or ""))
        self.rec["refresh"].append(row)
        return row

    def quiz_phase(self, phase: str) -> None:
        if self.cloud is not None:
            self.cloud.online = phase != self.offline_phase              # the planted offline window (A-TEACH2-15 T3)
        items, order = self.quiz["items"], self.quiz["orders"][phase]
        for pos, idx in enumerate(order):
            it = items[idx]
            row = self.say(it["question"], phase, {"quiz_pos": pos, "item_index": idx, "fact_id": it["fact_id"],
                                                    "kind": it["kind"], "slot": it["slot"], "value": it["value"],
                                                    "not_value": it.get("not_value")})
            self.rec["quiz"].append(row)
            rc = row.get("recall") or {}
            if self.comp and isinstance(rc, dict) and rc.get("question") and rc.get("capsule_id"):
                self._answer_refresh(phase, pos, rc["capsule_id"], rc["question"])
        self.rec["phase_marks"][phase] = {"working_bytes": self.working_bytes(), "turns_live": len(self.session.memory.turns)}
        if self.cloud is not None:
            self.cloud.online = True

    def crumb_sweep(self, label: str) -> Dict[str, Any]:
        rows = {cid: self.copy_state(cid) for cid in self._compactions()}
        bad = [{"capsule_id": c, "where": s["where"]} for c, s in rows.items() if not s["ok"]]
        out = {"label": label, "capsules": len(rows), "ok": len(rows) - len(bad), "bad": bad}
        self.rec.setdefault("crumb_sweeps", []).append(out)
        return out

    def plant_damage(self) -> None:
        planted = []
        if self.comp:
            turn_of = {}
            for t in self.turns:
                if t["kind"] in ("FACT", "TRAP") and t["fact_id"] and (t["kind"] == "FACT" or t.get("trap_role") == "FIRST"):
                    turn_of.setdefault(t["fact_id"], t["turn_index"])
            sent_turn = {r["turn_index"]: r.get("turn_id") for r in self.rec["turns"]}
            for d in self.damage:
                tid = sent_turn.get(turn_of.get(d["fact_id"]))
                cid = next((c for c, i in self._compactions().items() if tid in i["turn_ids"]), None)
                path = os.path.join(self.comp.cold_dir, f"{cid}.jsonl") if cid else None
                row = {"fact_id": d["fact_id"], "damage": d["damage"], "turn_id": tid, "capsule_id": cid, "done": False,
                       "where": None}
                if path and os.path.isfile(path):
                    if d["damage"] == "DELETE":
                        os.remove(path)
                    else:
                        with open(path, "ab") as fh:
                            fh.write(b"\n{\"planted\": \"damage\"}\n")
                    row["done"], row["where"] = True, "device"
                elif cid:
                    row["where"] = self.copy_state(cid)["where"]     # moved to the cloud: the device rule leaves it
                planted.append(row)
        self.rec["planted_damage"] = planted

    def finish(self) -> Dict[str, Any]:
        rec = self.rec
        hmc = self.helm["helm_memory_compact"]
        rec["sent_texts"] = list(self.sent)
        rec["digests_end"] = self.digests()
        rec["user_facts_end"] = list(self.session.memory.context.user_facts)
        rec["turns_live_end"] = [t.user_raw_text for t in self.session.memory.turns]
        rec["branches_end"] = self.store_branches()
        rec["branch_snapshots"] = self.branch_snapshots
        rec["bytes_log"] = self.bytes_log
        store = getattr(self.session.memory.context, "cube_store", None)
        rec["thing_provenance"] = {nid: n.provenance.source for nid, n in (store.nodes.items() if store else [])
                                   if nid.startswith("thing_")}
        if self.comp:
            rec["receipts_end"] = list(self.comp.receipts)
            rec["compactions"] = self._compactions()
            rec["eye_writes"] = self.comp.eye_writes
            rec["eye_report"] = self.comp.eye_report()
            rec["coefficient_digest_checks"] = list(self.comp.coefficient_digest_checks)
            rec["pinned"] = {k: list(v) if isinstance(v, (list, tuple)) else v for k, v in self.comp._pinned.items()}
            rec["strengthened"] = sorted(self.comp._strengthened)
            rec["declined"] = sorted(self.comp._declined)
            rec["moved_to_cloud"] = dict(getattr(self.comp, "moved", {}) or {})
            rec["moved_records"] = dict(getattr(self.comp, "moved_records", {}) or {})
            rec["moved_folds"] = dict(getattr(self.comp, "moved_folds", {}) or {})
            caps = self.comp.capsules
            rec["stored_rows"] = caps.stored() if hasattr(caps, "stored") else [c.as_dict() for c in caps]
            rec["stored_rows_sha256"] = C.sha256_obj(rec["stored_rows"])
            eye = getattr(caps, "eye", None)
            rec["eye_log"] = list(eye.log) if eye is not None else []
            rec["eye_held"] = sorted(eye.held) if eye is not None else []
            rec["recorder_rows"] = {"housekeep": self.r_house.rows, "answer": self.r_answer.rows}
            cold_dir = self.comp.cold_dir
            rec["cold_files"] = sorted(os.listdir(cold_dir)) if os.path.isdir(cold_dir) else []
            folds = {}
            for n in rec["cold_files"]:
                if n.endswith(".fold.json"):
                    folds[n] = Path(cold_dir, n).read_text(encoding="utf-8")
            if self.cloud is not None:
                for k, v in self.cloud.objects.items():
                    if k.endswith(".fold.json"):
                        folds["cloud:" + k] = v.decode("utf-8", "replace")
            rec["fold_records"] = folds
            rec["cloud_objects"] = sorted(self.cloud.objects) if self.cloud is not None else []
            rec["cloud_deletes"] = self.cloud.deletes if self.cloud is not None else 0
        if self.osc is not None:
            rec["osc_log"] = list(self.osc.log)
            rec["batch_log"] = list(getattr(self.osc, "batch_log", []))
            rec["table_end"] = {f"{k[0]}|{' '.join(sorted(k[1]))}": v for k, v in self.osc.table.items()}
            rec["s2_records"] = self.osc.s2_records()
            rec["store_writes_from_shadow"] = self.osc.store_writes_from_shadow
            rec["osc_recorder_rows"] = {"answer": self.r_osc_answer.rows}
        rec["saybacks"] = self.saybacks
        if self.client is not None:
            rec["ctt"] = self.client.close()
            rec["twin_log"] = self.client.twin_log
        rec["ledger_file"] = self.session.memory.session_file
        rec["clock_calls"] = self.clock["state"]["calls"]
        return rec

    def run(self) -> Dict[str, Any]:
        self.start()
        try:
            self.teach()
            self.rec["phase_marks"]["after_teach"] = {"working_bytes": self.working_bytes(),
                                                      "turns_live": len(self.session.memory.turns)}
            self.quiz_phase("Q_TAUGHT")
            self.crumb_sweep("before_damage")
            self.plant_damage()
            self.crumb_sweep("after_damage")
            self.quiz_phase("Q_SQUEEZED")
            self.quiz_phase("Q_REFRESHED")
        except Exception as exc:          # a crash is a recorded error (I13), never a silent pass
            self.rec["errors"].append({"phase": "UNIT", "error": f"{type(exc).__name__}: {exc}"})
        return self.finish()
