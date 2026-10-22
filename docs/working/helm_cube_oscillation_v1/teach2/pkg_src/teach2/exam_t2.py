"""The exam carrier of TEACH-2: worlds (with keys), the teaching plan (with TRAP lines), the quizzes, the planted damage,
the offline quiz per world, the seeds.

`build_exam(seeds, out_dir, practice)` writes one folder the units read:
    WORLDS.json   the 16 keyed worlds (worlds_t2.build_all at the WORLD seed)
    PLAN.json     the 32 teaching slots per world (worlds_t2.teaching_plan at the WORLD and TRAP seeds)
    TURNS.json    the teaching turns per world: PRACTICE = rule-written here; SEALED = the LLM-written file the
                  custodian drops in (contract/KEY_FORMAT_TEACH2.md), checked by turns_t2.check_turns
    QUIZ.json     16 keyed questions per world and three orders (QUIZ seed)
    DAMAGE.json   the two cold copies damaged per world (WORLD stream)
    OFFLINE.json  the quiz phase per world in which the stand-in cloud is offline (QUIZ seed; A-TEACH2-15 T3)
    SEEDS.json    the derivation (seed_rule_t2) or the practice texts, `practice_mock` set
    PINS.json     the sha256 of every file above
The builder runs this only in practice mode. The custodian runs it from the sealed zip after the owner's line.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from . import common_t2 as C
from . import turns_t2 as T
from . import worlds_t2 as W

FILES = ("WORLDS.json", "PLAN.json", "TURNS.json", "QUIZ.json", "DAMAGE.json", "OFFLINE.json", "SEEDS.json")


def build_exam(seeds: Dict[str, Any], out_dir, *, practice: bool, turns_file: Optional[str] = None,
               count: int = C.WORLDS) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ws, qs, ts = seeds["WORLD"], seeds["QUIZ"], seeds["TRAP"]
    worlds = W.build_all(ws, count)
    plan = {w["world_id"]: W.teaching_plan(w, ws, ts) for w in worlds}
    quiz = {w["world_id"]: {"items": W.quiz_items(w, qs), "orders": W.quiz_orders(w, qs)} for w in worlds}
    damage = {w["world_id"]: W.damage_plan(w, quiz[w["world_id"]]["items"], ws) for w in worlds}
    offline = {w["world_id"]: W.offline_quiz(w, qs) for w in worlds}
    if practice:
        turns = {w["world_id"]: T.practice_turns(w, plan[w["world_id"]], ws) for w in worlds}
    else:
        if not turns_file:
            raise SystemExit("REFUSED: a sealed exam needs the LLM-written turn file (--turns)")
        turns = C.read_json(turns_file)
    seeds_doc = dict(seeds)
    seeds_doc["practice_mock"] = bool(practice)
    docs = {"WORLDS.json": {"schema": "helm.teach2.worlds/1", "practice_mock": practice, "worlds": worlds},
            "PLAN.json": {"schema": "helm.teach2.plan/1", "practice_mock": practice, "plan": plan},
            "TURNS.json": {"schema": "helm.teach2.turns/1", "practice_mock": practice, "turns": turns,
                           "label": "RULE_WRITTEN_PRACTICE" if practice else "LLM_WRITTEN"},
            "QUIZ.json": {"schema": "helm.teach2.quiz/1", "practice_mock": practice, "quiz": quiz},
            "DAMAGE.json": {"schema": "helm.teach2.damage/1", "practice_mock": practice, "damage": damage},
            "OFFLINE.json": {"schema": "helm.teach2.offline/1", "practice_mock": practice, "offline_quiz": offline},
            "SEEDS.json": seeds_doc}
    pins = {}
    for name, doc in docs.items():
        pins[name] = C.write_json(out / name, doc)
    C.write_json(out / "PINS.json", {"schema": "helm.teach2.pins/1", "practice_mock": practice, "pins": pins})
    return {"out": str(out), "pins": pins, "worlds": len(worlds)}


def load_exam(exam_dir) -> Dict[str, Any]:
    d = Path(exam_dir)
    pins = C.read_json(d / "PINS.json")["pins"]
    docs = {name: C.load_doc(d / name, pins[name]) for name in FILES}
    return {"dir": str(d), "pins": pins, "worlds": docs["WORLDS.json"]["worlds"], "plan": docs["PLAN.json"]["plan"],
            "turns": docs["TURNS.json"]["turns"], "turns_label": docs["TURNS.json"]["label"],
            "quiz": docs["QUIZ.json"]["quiz"], "damage": docs["DAMAGE.json"]["damage"],
            "offline": docs["OFFLINE.json"]["offline_quiz"], "seeds": docs["SEEDS.json"],
            "practice_mock": any(docs[n].get("practice_mock") for n in FILES)}


def check_exam(exam: Dict[str, Any], routed=None, route_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Every world's turn file against the floors and the split (turns_t2.check_turns); TRAP canonical lines join the
    split; counts for I14."""
    worlds = exam["worlds"]
    sealed = not exam["practice_mock"]
    traps = [s["text"] for slots in exam["plan"].values() for s in slots if s["kind"] == "TRAP"]
    split = T.split_hashes(worlds, trap_texts=traps) if sealed else {}
    reports = {}
    for w in worlds:
        rr = (route_report or {}).get(w["world_id"]) or {}
        fn = routed
        if route_report is not None:
            def fn(t, rr=rr):
                return rr.get(str(t.get("turn_index")))
        reports[w["world_id"]] = T.check_turns(w, exam["turns"][w["world_id"]], sealed=sealed, split=split, routed=fn)
    return {"worlds": len(worlds), "worlds_floor": len(worlds) >= C.WORLDS, "sealed": sealed,
            "all_ok": all(r["ok"] for r in reports.values()), "reports": reports}
