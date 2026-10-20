"""HELM UI v0 -- a small local web server around HELM's own chat turn.

Run:  python helm_ui/server.py          (then open http://127.0.0.1:8765)

What it does:
- POST /turn     one user sentence -> HELM's plain-English reply, the record it rests on, and the loop's status word.
                 The ONLY path that can change HELM's state. It calls helm_chat's own turn function (imported, not copied).
- GET  /state    what HELM knows now (stock, recipes, your facts), the last self-check, the pairing table, wiring.
- GET  /eye/scan the Unity Eye's self-scan (U3 scanner) on a built test copy of HELM's state. Read-only, in a
                 separate process; it never touches this chat session.
- GET  /history  this session's turns with their records.

Fail soft: a part that cannot load is reported as "not wired"; no panel ever shows invented numbers.
Tool actions (write files, run commands, git, cloud jobs) are switched OFF in this window unless HELM_UI_ALLOW_TOOLS=1.
Standard library + FastAPI/uvicorn (already installed). Binds 127.0.0.1 only.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

UI_DIR = Path(__file__).resolve().parent
REPO = UI_DIR.parent
STATIC = UI_DIR / "static"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CODEX_DAY = Path(os.environ.get("HELM_UI_CODEX_DAY", r"C:\Users\wakil\Documents\Codex\2026-10-19"))
U3_DIR = CODEX_DAY / "u3_t1"
RB_I3_READING = CODEX_DAY / "rb_i3" / "READING.json"
W4_READING = CODEX_DAY / "r1_wave4" / "run_c39_r1w4_20261019" / "R1_W4_READING.json"
W5_READING = CODEX_DAY / "r1_wave5" / "run_c40_r1w5_20261019" / "R1_W5_READING.json"
U3_READING = U3_DIR / "runs" / "MERGED_READING.json"
EYE_RUNNER = UI_DIR / "eye_runner.py"

HOST = "127.0.0.1"
PORT = int(os.environ.get("HELM_UI_PORT", "8765"))

FOUNDATIONS = [("F1", "Unity"), ("F2", "Wisdom"), ("F3", "Vitality"), ("F4", "Connection"),
               ("F5", "Agency"), ("F6", "Structure"), ("F7", "Purpose")]
FACULTIES = ["CURIOSITY", "PONDERING", "IMAGINATION", "VERIFY", "ASKING", "INTEGRATION", "CONSOLIDATE"]

#: The loop's status words, said plainly. The exact word is always shown next to it.
STATUS_PLAIN = {
    "INVENTORY_RECORDED": "Stock noted",
    "SUCCESS_EVALUATED": "Worked it out from what you have",
    "WITNESS_ADMITTED": "Learned from your batch",
    "REPAIRED_RETEACH_NEEDED": "Needs re-teaching",
    "UNDETERMINED_CLARIFY": "Not known yet, asked you for more",
    "BRAIN_UNDETERMINED": "Not known yet",
    "CONFLICT_UNDETERMINED": "Two records disagree, not decided",
    "CLARIFY_BATCH_NOT_USABLE": "That batch can't be used to learn",
    "CLARIFY_NOT_A_STOCK": "Didn't read that as stock",
    "CLARIFY_NOT_CCE": "Couldn't check that sentence",
    "CLARIFY_REFUSAL": "Declined: not a recipe question",
    "CLARIFY_ROUND_TRIP_FAILED": "Reading didn't check out, asked again",
    "CLARIFY_STOCK_NOT_RECORDED": "Stock not saved",
    "CLARIFY_UNKNOWN_PRODUCT": "Doesn't know that product",
    "STATED_RECIPE_NOT_TAKEN": "Won't take a recipe on your word alone",
    "VERIFIED_NO_RECIPE_CONTENT": "Checked, nothing to act on",
    "READ_COMPLETED": "Looked it up in the store",
    "READ_WROTE_REFUSED": "A read tried to write, refused",
    "REFUSE_NOT_VERIFIED": "Refused: no checker",
    "REFUSE_RECEIPT_INCONSISTENT": "Refused: records didn't agree",
    "AGENTIC_PLAN_EXECUTED": "Tool plan ran",
    "AGENTIC_PLAN_CLAMPED": "Tool plan stopped",
}
#: helm_chat's own route names, said plainly (used when the reply did not go through the recipe loop).
INTENT_PLAIN = {
    "INVENTORY_DECLARATION": "Stock noted",
    "RECIPE_FOUNDATION_LOOP": "Recipe check",
    "USER_NARRATIVE": "Noted something about you",
    "USER_AFFECT": "Noted how you feel",
    "USER_PREFERENCE": "Noted a preference",
    "USER_KNOWLEDGE_QUERY": "Told you what it knows about you",
    "QUERY_MEMORY_RECALL": "Looked through this session",
    "QUERY_MEMORY_COUNT": "Counted what you told it",
    "SESSION_SUMMARY": "Summed up the session",
    "REQUEST_EXPLANATION": "Explained its last step",
    "GENERAL_CONVERSATION": "Said hello",
    "GENERAL_KNOWLEDGE_INQUIRY": "Declined to guess without data",
    "CREATIVE_HUMOR": "Told a joke",
    "STUDY_HYPOTHESIS": "Wrote down a study idea (not checked)",
    "STUDY_REFUSAL": "Refused: nothing physical to study",
    "INVENTORY_QUERY": "Listed the stock",
    "AGENTIC_GOAL": "Tool request",
}
#: Commands that belong to the terminal chat only (they quit or flip modes in helm_chat's REPL).
TERMINAL_ONLY = {"exit": "This window stays open. Close the tab when you are done.",
                 "quit": "This window stays open. Close the tab when you are done.",
                 "q": "This window stays open. Close the tab when you are done.",
                 "mode": "The record under each reply already shows the technical view."}
READ_ONLY_COMMANDS = ("help", "dials", "history")

#: The project's status markers (feedback_result_status_color_scale). Never upgraded here.
MARK = {"WIN": "\u2705", "STRONG": "\U0001F7E9", "PARTIAL": "\U0001F7E8", "WEAK": "\U0001F7E7",
        "FAILED": "\U0001F7E5", "NULL": "\u2B1C", "METHOD": "\U0001F527", "OWNER": "\U0001F512"}


#: The Unity Eye's own four dial presets (UnityEyeSupervisor.modulate_dial_for_attempt, attempts 1-4).
DIAL_PRESETS = {"CONSERVATIVE": 1, "BALANCED": 2, "EXPLORATORY": 3, "OUT_OF_THE_BOX": 4}
#: Ranges as CreativityDial's setters enforce them (shown on the sliders; the setters still decide).
DIAL_RANGES = {"K": {"min": 1, "max": 32, "step": 1}, "rho": {"min": -4.0, "max": 1.0, "step": 0.1},
               "R": {"options": [1, 2, 4, 8]}, "ponder": {"min": 0, "max": 100, "step": 1},
               "sigma": {"min": 0.0, "max": 1.0, "step": 0.01}}
_PRESET_CACHE: Dict[int, Dict[str, Any]] = {}
PLAN_RUNNER = UI_DIR / "plan_runner.py"


def _preset_values(attempt: int) -> Dict[str, Any]:
    """Values of one preset, read by applying the Eye's own preset law to a fresh supervisor (no copy of numbers)."""
    if attempt not in _PRESET_CACHE:
        import helm_agentic_executor as ax
        d = ax.UnityEyeSupervisor().modulate_dial_for_attempt(attempt)
        _PRESET_CACHE[attempt] = {"K": d.breadth_K, "rho": str(d.curvature_rho), "R": d.search_radius_R,
                                  "ponder": d.idle_ponder_budget, "sigma": str(d.valve_novelty_sigma)}
    return _PRESET_CACHE[attempt]


def run_plan(text: str, timeout: int = 60) -> Dict[str, Any]:
    """Run the prerequisite planner in its own process. Plans and asks the gate; never runs a tool."""
    text = (text or "").strip()[:2000]
    if not text:
        return {"ok": False, "reason": "Nothing was typed."}
    if not PLAN_RUNNER.is_file() or not (REPO / "docs" / "working" / "noetic_council" / "prereq_planner").is_dir():
        return {"ok": False, "wired": False, "reason": "not wired: prereq_planner not found"}
    try:
        proc = subprocess.run([sys.executable, "-I", str(PLAN_RUNNER), text], capture_output=True, text=True,
                              timeout=timeout, encoding="utf-8")
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": f"the planner did not finish in {timeout} s"}
    if proc.returncode != 0:
        return {"ok": False, "reason": "the planner failed", "detail": proc.stderr[-800:]}
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"ok": False, "reason": "planner output was not JSON", "detail": proc.stdout[-400:]}


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _jsonable(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=str))


class _ToolsOff:
    """Stands in for AgenticExecutionEngine.execute_dag in the browser: plans are made, nothing is run."""

    def __call__(self, dag: Any, valve_aperture: Any = None) -> Dict[str, Any]:
        steps = list(getattr(dag, "steps", {}).values())
        first = steps[0].step_id if steps else "plan"
        return {"goal": getattr(dag, "goal", ""), "all_steps_completed": False, "steps_total": len(steps),
                "steps_completed": 0, "tools_off_in_ui": True,
                "execution_log": [{"step_id": first, "status": "CLAMPED_HALT", "gate_code": "UI_TOOLS_OFF",
                                   "reason": "tool actions are switched off in the browser window "
                                             "(use python helm_chat.py in a terminal)",
                                   "missing_prerequisites": ["HELM_UI_ALLOW_TOOLS=1"]}]}


class HelmBridge:
    """One HELM chat session behind a lock. Reads are pure; only turn() calls HELM's turn function."""

    def __init__(self, session_dir: Optional[str] = None, allow_tools: Optional[bool] = None):
        self.lock = threading.Lock()
        self.wiring: Dict[str, str] = {}
        self.records: Dict[int, Dict[str, Any]] = {}
        self.eye_last: Optional[Dict[str, Any]] = None
        self.allow_tools = (os.environ.get("HELM_UI_ALLOW_TOOLS") == "1") if allow_tools is None else allow_tools
        self.session = None
        self.session_dir = Path(session_dir or os.environ.get("HELM_UI_SESSION_DIR", UI_DIR / "sessions"))
        try:
            import helm_chat  # HELM's own chat module: its turn function is used as-is
            with contextlib.redirect_stdout(io.StringIO()):
                self.session = helm_chat.HELMConversationalSession(
                    mode="everyday", session_id=f"helm-ui-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}")
            mem = self.session.memory  # helm_memory makes the folder on the first logged turn
            mem.storage_dir = str(self.session_dir)
            mem.session_file = str(self.session_dir / f"{mem.session_id}.jsonl")
            self.wiring["chat"] = "wired"
        except Exception as exc:  # fail soft
            self.wiring["chat"] = f"not wired: {type(exc).__name__}: {exc}"
        if self.session is not None and not self.allow_tools:
            for eng in (getattr(self.session, "engine", None), getattr(self.session.loop, "agentic_engine", None)):
                if eng is not None:
                    eng.execute_dag = _ToolsOff()
        self.wiring["tools"] = "on" if self.allow_tools else "off in this window"
        self.wiring["eye_scan"] = ("wired (synthetic test copy, separate process)" if (U3_DIR / "eye_scan.py").is_file()
                                   else f"not wired: {U3_DIR} not found")
        self.wiring["eye_live_session"] = "not wired (the self-check does not read this chat yet)"
        self.wiring["pairing_table"] = ("wired (read from the RB-I3 run record)" if RB_I3_READING.is_file()
                                        else f"not wired: {RB_I3_READING} not found")
        self.wiring["pairing_live_session"] = "not wired (the chat has no idle drive loop)"

    # ------------------------------------------------------------------ the one write path
    def turn(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"ok": False, "kind": "error", "reply": "Nothing was typed.", "recorded": False}
        if self.session is None:
            return {"ok": False, "kind": "not_wired", "recorded": False,
                    "reply": "HELM's chat module did not load, so nothing was said.", "detail": self.wiring.get("chat")}
        low = text.lower()
        if low in TERMINAL_ONLY:
            return {"ok": True, "kind": "note", "reply": TERMINAL_ONLY[low], "recorded": False}
        with self.lock:
            s = self.session
            if low in READ_ONLY_COMMANDS:
                buf = io.StringIO()
                try:
                    with contextlib.redirect_stdout(buf):
                        s.handle_turn(text)
                except Exception as exc:  # a terminal command that fails inside helm_chat is reported, not raised
                    return {"ok": False, "kind": "note", "recorded": False,
                            "reply": f"The terminal command '{low}' failed inside helm_chat: {type(exc).__name__}: {exc}"}
                return {"ok": True, "kind": "note", "reply": buf.getvalue().strip(), "recorded": False}
            before_last = s.memory.turns[-1] if s.memory.turns else None
            n0 = len(s.loop.trace)
            buf = io.StringIO()
            t0 = time.time()
            error = None
            try:
                with contextlib.redirect_stdout(buf):
                    s.handle_turn(text)
            except SystemExit:
                error = "SystemExit refused"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                traceback.print_exc()
            last = s.memory.turns[-1] if s.memory.turns else None
            if last is None or last is before_last:
                return {"ok": False, "kind": "error", "recorded": False,
                        "reply": "Something went wrong inside HELM on that turn, and nothing was recorded.",
                        "detail": error or buf.getvalue().strip()[-600:]}
            trace = _jsonable(s.loop.trace[n0:])
            rec = self._record(last, trace, time.time() - t0)
            self.records[last.turn_id] = rec
            return {"ok": True, "kind": "reply", "recorded": True, "reply": last.helm_response, "record": rec,
                    "state": self._state_locked()}

    def _record(self, turn: Any, trace: List[Dict[str, Any]], wall: float) -> Dict[str, Any]:
        t = asdict(turn)
        loop = None
        if trace:
            nxt = next((r for r in reversed(trace) if r.get("station") == "S6 next"), {})
            eng = next((r for r in trace if r.get("station") == "English in"), {})
            ccf = next((r for r in trace if r.get("checked_form")), {})
            status = nxt.get("loop_status")
            stations: List[str] = []
            for r in trace:
                st = r.get("station")
                if st and st not in stations:
                    stations.append(st)
            rpm = next((r.get("verdict") for r in trace if r.get("station") == "S5 RPM link"
                        and isinstance(r.get("verdict"), dict)), None)
            valve = next((r.get("valve") for r in trace if r.get("station") == "S4 operating point"
                          and isinstance(r.get("valve"), dict)), None)
            loop = {"status": status, "status_plain": STATUS_PLAIN.get(status, status), "next": nxt.get("next"),
                    "checked_form": eng.get("checked_form") or ccf.get("checked_form"),
                    "stations": stations, "receipt_hash": nxt.get("receipt_hash"),
                    "rpm_gate": None if rpm is None else {k: rpm.get(k) for k in
                                                          ("verdict", "code", "can_proceed", "gap", "reason")},
                    "valve": None if valve is None else {k: valve.get(k) for k in
                                                         ("inflow_entropy", "aperture_sigma", "backpressure",
                                                          "gate_interlock", "status", "reason", "rule")},
                    "records": trace}
        intent = t.get("intent")
        status_word = (loop or {}).get("status") or intent
        plain = (loop or {}).get("status_plain") or INTENT_PLAIN.get(intent, (intent or "").replace("_", " ").lower())
        return {"turn_id": t["turn_id"], "time_utc": t["timestamp_utc"], "you_said": t["user_raw_text"],
                "resolved_text": t["resolved_text"] if t["resolved_text"] != t["user_raw_text"] else None,
                "route": intent, "status_word": status_word, "status_plain": plain, "gate": t["gate_code"],
                "receipt_hash": t["receipt_hash"], "cubes_written": t["cubes_written"], "cubes_read": t["cubes_read"],
                "operation": t["operation"], "duration_s": t["duration_seconds"], "wall_s": round(wall, 3),
                "went_through_recipe_loop": loop is not None, "loop": loop,
                "tools_off": (not self.allow_tools) and intent == "AGENTIC_GOAL",
                "session_file": Path(self.session.memory.session_file).name if self.session else None}

    # ------------------------------------------------------------------ pure reads
    def state(self) -> Dict[str, Any]:
        with self.lock:
            return self._state_locked()

    def _state_locked(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"wiring": dict(self.wiring), "eye_last": self.eye_last}
        s = self.session
        if s is None:
            out["knows"] = None
        else:
            from helm_brain_canonical import frac_text
            loop, brain = s.loop, s.loop.brain
            stock = [{"name": k, "amount": frac_text(v), "unit": loop.units.get(k)} for k, v in loop.stock.items()]
            recipes = []
            for p in brain.products:
                try:
                    req = brain.requirements(p)
                except Exception:
                    req = {}
                recipes.append({"product": p, "needs": [{"ingredient": k, "per_unit": v} for k, v in req.items()]})
            try:
                prov = brain.provenance()
            except Exception:
                prov = {}
            ctx = s.memory.context
            out["knows"] = {"stock": stock, "out_of": sorted(loop.declared_absent), "recipes": recipes,
                            "your_facts": list(ctx.user_facts),
                            "prefers_short_answers": bool(ctx.user_preferences.get("concise", False)),
                            "turns": len(s.memory.turns),
                            "brain": {"name": prov.get("brain"), "claim_ceiling": prov.get("claim_ceiling")}}
        out["dials"] = self._dials_locked()
        out["pairing"] = pairing_from_record()
        out["claims"] = claims_on_screen()
        return _jsonable(out)

    def history(self) -> List[Dict[str, Any]]:
        with self.lock:
            if self.session is None:
                return []
            rows = []
            for t in self.session.memory.turns:
                rows.append({"turn_id": t.turn_id, "you_said": t.user_raw_text, "reply": t.helm_response,
                             "record": self.records.get(t.turn_id) or {"turn_id": t.turn_id, "route": t.intent,
                                                                        "gate": t.gate_code,
                                                                        "receipt_hash": t.receipt_hash}})
            return _jsonable(rows)

    # ------------------------------------------------------------------ the five search dials (planner only)
    def _eye(self):
        eng = getattr(self.session, "engine", None) if self.session is not None else None
        return getattr(eng, "eye", None)

    def dials(self) -> Dict[str, Any]:
        with self.lock:
            return self._dials_locked()

    def _dials_locked(self) -> Dict[str, Any]:
        eye = self._eye()
        if eye is None or not hasattr(eye, "dial"):
            return {"wired": False, "reason": "not wired: the session has no Unity Eye supervisor with a dial"}
        d = eye.dial
        vals = {"K": d.breadth_K, "rho": str(d.curvature_rho), "R": d.search_radius_R,
                "ponder": d.idle_ponder_budget, "sigma": str(d.valve_novelty_sigma)}
        mode = "CUSTOM"
        for name, attempt in DIAL_PRESETS.items():
            if _preset_values(attempt) == vals:
                mode = name
        return {"wired": True, "values": vals, "mode": mode, "presets": list(DIAL_PRESETS),
                "ranges": DIAL_RANGES, "source": "helm_agentic_executor.UnityEyeSupervisor.dial "
                                                  "(helm_creativity_dial.CreativityDial setters)",
                "used_by": "the tool planner's search only (decompose_goal); recipe answers do not read these dials"}

    def set_dials(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            eye = self._eye()
            if eye is None or not hasattr(eye, "dial"):
                return {"ok": False, "wired": False, "reason": "not wired"}
            try:
                if payload.get("preset"):
                    preset = str(payload["preset"]).upper()
                    if preset not in DIAL_PRESETS:
                        raise ValueError(f"unknown preset {payload['preset']!r}")
                    eye.modulate_dial_for_attempt(DIAL_PRESETS[preset])   # the Eye's own preset law
                else:
                    d = eye.dial
                    setters = {"K": d.set_breadth, "rho": d.set_curvature, "R": d.set_search_radius,
                               "ponder": d.set_idle_ponder, "sigma": d.set_valve_saliency}
                    for key, fn in setters.items():
                        if key in payload:
                            fn(payload[key])          # CreativityDial validates every range itself
            except (ValueError, TypeError, ArithmeticError) as exc:
                return {"ok": False, "error": str(exc), **self._dials_locked()}
            return {"ok": True, **self._dials_locked()}

    # ------------------------------------------------------------------ the prerequisite planner (dry run)
    def plan(self, text: str) -> Dict[str, Any]:
        return run_plan(text)

    def eye_scan(self, world: str = "clean") -> Dict[str, Any]:
        rep = run_eye_scan(world)
        with self.lock:
            if rep.get("ok"):
                self.eye_last = rep
        return rep


# ---------------------------------------------------------------------- read-only helpers
def run_eye_scan(world: str = "clean", timeout: int = 90) -> Dict[str, Any]:
    """Run the U3 scanner in its own process (its imports must not mix with this session's modules)."""
    if not (U3_DIR / "eye_scan.py").is_file():
        return {"ok": False, "wired": False, "reason": f"not wired: {U3_DIR} not found"}
    if world not in ("clean", "fault"):
        return {"ok": False, "wired": True, "reason": "world must be 'clean' or 'fault'"}
    try:
        proc = subprocess.run([sys.executable, "-I", str(EYE_RUNNER), "--codex-day", str(CODEX_DAY), "--world", world],
                              capture_output=True, text=True, timeout=timeout, encoding="utf-8")
    except subprocess.TimeoutExpired:
        return {"ok": False, "wired": True, "reason": f"self-scan did not finish in {timeout} s"}
    if proc.returncode != 0:
        return {"ok": False, "wired": True, "reason": "self-scan failed", "detail": proc.stderr[-800:]}
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"ok": False, "wired": True, "reason": "self-scan output was not JSON", "detail": proc.stdout[-400:]}


def pairing_from_record(seed: str = "11") -> Dict[str, Any]:
    d = _read_json(RB_I3_READING)
    if not d:
        return {"wired": False, "reason": f"not wired: {RB_I3_READING} not readable"}
    try:
        lv = d["learned_vs_true"][f"A_STATIONARY|{seed}"]
        att = d["R6_R7_attention_EYE_A"][["11", "29", "47"].index(seed)]
        grid = []
        for fid, fname in FOUNDATIONS:
            row = []
            for fac in FACULTIES:
                ok, tries = (int(x) for x in lv["final_table"].get(f"{fid}|{fac}", "0/0").split("/"))
                row.append({"faculty": fac, "worked": ok, "tries": tries,
                            "eye_best": lv["argmax"].get(fid) == fac, "true_best": lv["true_key_end"].get(fid) == fac})
            grid.append({"id": fid, "name": fname, "cells": row})
        steps = {fid: int(att["tally"][fid].split("/")[1]) for fid, _ in FOUNDATIONS}
        return {"wired": True,
                "source": f"rb_i3/READING.json (RB-I3 run record, family A_STATIONARY, seed {seed}, end of life)",
                "status_word": d.get("status_word"), "test_verdict": d.get("test_verdict"),
                "claim_ceiling": d.get("claim_ceiling"), "match": lv.get("match"), "noisy": lv.get("noisy"),
                "faculties": FACULTIES, "grid": grid,
                "attention": {"what": "share of the life's attention steps that landed on each desire "
                                      "(the live point itself is never written into a record)",
                              "steps": steps, "total": sum(steps.values()),
                              "steps_in_conversation": att.get("steps_in_conversation"),
                              "min_coord": att.get("min_coord"), "open_simplex": att.get("min_coord_positive")}}
    except Exception as exc:
        return {"wired": False, "reason": f"not wired: record shape not understood ({type(exc).__name__})"}


def claims_on_screen() -> List[Dict[str, Any]]:
    """Status words of what is on screen, read from the run records. Markers follow the project's scale."""
    claims: List[Dict[str, Any]] = []
    try:
        import helm_english_in
        reader_status = helm_english_in.CLAIM_STATUS
    except Exception:
        reader_status = None
    claims.append({"panel": "Conversation", "mark": MARK["NULL"], "word": reader_status or "not wired",
                   "ceiling": "SYNTHETIC_ONLY",
                   "plain": "HELM's chat path is built and wired; it has not been validated on real use."})
    u3 = _read_json(U3_READING)
    if u3:
        claims.append({"panel": "Self-check", "mark": MARK["STRONG"], "word": u3.get("status_word"),
                       "status": u3.get("claim_status"), "ceiling": u3.get("claim_ceiling"),
                       "plain": "U3-T1: on test copies the scan found every planted fault and raised no false alarm.",
                       "source": "u3_t1/runs/MERGED_READING.json"})
    w4 = _read_json(W4_READING)
    if w4:
        claims.append({"panel": "Self-check", "mark": MARK["STRONG"], "word": w4.get("eye_scan_word"),
                       "status": w4.get("claim_status"), "verdict": w4.get("test_verdict"),
                       "ceiling": w4.get("claim_ceiling"), "plain": w4.get("claim_template"),
                       "not_licensed": w4.get("not_licensed"),
                       "source": "r1_wave4/run_c39_r1w4_20261019/R1_W4_READING.json"})
    w5 = _read_json(W5_READING)
    if w5:
        claims.append({"panel": "Attention", "mark": MARK["STRONG"], "word": w5.get("status_word"),
                       "status": w5.get("claim_status_if_licensed") if w5.get("word_licensed") else "NOT LICENSED",
                       "verdict": w5.get("test_verdict"), "ceiling": w5.get("claim_ceiling"),
                       "plain": w5.get("claim_template"), "not_licensed": w5.get("not_licensed"),
                       "source": "r1_wave5/run_c40_r1w5_20261019/R1_W5_READING.json"})
    claims.append({"panel": "Live wiring", "mark": MARK["NULL"], "word": "NOT WIRED",
                   "plain": "The self-check and the pairing table are not yet connected to this chat session."})
    return claims


# ---------------------------------------------------------------------- the web app
def create_app(bridge: Optional[HelmBridge] = None):
    from fastapi import Body, FastAPI
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="HELM UI v0", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.bridge = bridge or HelmBridge()

    @app.post("/turn")
    def post_turn(payload: Dict[str, Any] = Body(...)):
        return JSONResponse(app.state.bridge.turn(str(payload.get("text", ""))))

    @app.get("/state")
    def get_state():
        return JSONResponse(app.state.bridge.state())

    @app.get("/eye/scan")
    def get_eye_scan(world: str = "clean"):
        return JSONResponse(app.state.bridge.eye_scan(world))

    @app.get("/history")
    def get_history():
        return JSONResponse(app.state.bridge.history())

    @app.get("/dials")
    def get_dials():
        return JSONResponse(app.state.bridge.dials())

    @app.post("/dials")
    def post_dials(payload: Dict[str, Any] = Body(...)):
        res = app.state.bridge.set_dials(payload)
        return JSONResponse(res, status_code=200 if res.get("ok") else 422)

    @app.post("/plan")
    def post_plan(payload: Dict[str, Any] = Body(...)):
        return JSONResponse(app.state.bridge.plan(str(payload.get("text", ""))))

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    return app


def main() -> None:
    import uvicorn
    print(f"HELM UI v0 on http://{HOST}:{PORT}  (tool actions {'ON' if os.environ.get('HELM_UI_ALLOW_TOOLS') == '1' else 'off'})",
          flush=True)
    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
