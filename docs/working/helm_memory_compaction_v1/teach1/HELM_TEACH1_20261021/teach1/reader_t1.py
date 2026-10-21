"""The frozen reader of TEACH-1: instrument rows I1-I14, the 12 hard gates (HG-H8 first), the marks (U, R, F, S), and
the status word in the frozen order (pre-code sections 5-9, as amended by A-TEACH1-1).

    python -X utf8 -B -I <pkg>/teach1/reader_t1.py --merge-input MERGE_INPUT_TEACH1.json --out TEACH1_READING.json

MERGE_INPUT names: the run folder (unit records, POOL_SUMMARY, SUITES_TEACH1.json, CUT_CHECK_TEACH1.json), the exam
folder (keys), and for a sealed reading the approval record, the seed derivation, the custodian attestation and the zip.
A practice reading (practice_mock) is always INCONCLUSIVE by I0; its marks are printed as facts that decide nothing.
Standard library only. The reader never runs HELM.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from teach1 import common_t1 as C          # noqa: E402
from teach1 import person_t1 as P          # noqa: E402
from teach1 import seed_rule_t1 as SR      # noqa: E402

READER = "reader_t1 v1"
HARM_GATES = ("HG-H8", "HG-INVENT", "HG-COEF", "HG-CUBE", "HG-EYE")
GATES = ("HG-H8", "HG-INVENT", "HG-COMPILE", "HG-RECEIPT", "HG-COEF", "HG-CUBE", "HG-EYE", "HG-CAS", "HG-ASK",
         "HG-REPLAY", "HG-TESTS", "HG-SPLIT")

# ---- the voice's markers (helm_voice.MARKERS at the cut, copied verbatim and frozen here) ----
SUCCESS_RX = re.compile(r"\b(?:you can make|we can get|you'll get|works out to|comes to|comes out to|the most you can make|"
                        r"is doable|adds up to|produce that much|carry you to|caps you at|caps this run at|it gives|enough for|"
                        r"yield|gets you|the result is|the answer is|the total is|can produce|we can produce)\b", re.I)
NODATA_RX = re.compile(r"\b(?:no verified facts|don't know|outside what I know|no reliable|don't have reliable|no solid facts|"
                       r"beyond what I've got facts|any grounding|can't support an answer|don't have verified|"
                       r"nothing I have covers|can't answer that)\b", re.I)
NEVER_RX = re.compile(r"\b(?:never been taught|never taught|nobody's taught|haven't been taught|"
                      r"outside anything I've been taught|a gap for me|true gap)\b", re.I)
#: A-TEACH1-1 D-TEACH1-6: the chat's own honest memory lines also count as an unknown marker (every arm alike)
MEMORY_UNKNOWN_RX = re.compile(r"\b(?:I don't see a specific note on that|I don't have that one any more|"
                               r"don't remember)\b", re.I)
ASK_RX = re.compile(r"(?:\?\s*$|which one do you mean|refresh my memory)", re.I)
#: the talk packet's M2 recipe-speak list (DESIGN_TALK_V1 M2), frozen here; ingredient names of the brain's table
RECIPE_SPEAK_RX = re.compile(r"\b(?:recipes?|ingredients?|stock|inventory|limiting|yield|batch|receipt|foundation loop|station|"
                             r"gate|RPM|cube|verified facts|flour|water|sugar|butter|eggs?|milk|salt|yeast)\b"
                             r"|how much .* do (?:we|you) have", re.I)
TOOL_INTENTS = ("AGENTIC_GOAL", "STUDY_HYPOTHESIS", "STUDY_REFUSAL")


# ============================================================================================ answer scoring
def _value_pools(world: Dict[str, Any]) -> Dict[str, List[str]]:
    v = world["values"]
    return {"count": [C.norm(x) for x in v["count"]], "person": [x.lower() for x in v["person"]],
            "place": [x.lower() for x in v["place"]]}


def stated(reply: str, pool: List[str]) -> List[str]:
    toks = C.norm(reply).split()
    return sorted({p for p in pool if p in toks})


def negated(reply: str, value: str) -> bool:
    return bool(re.search(r"\bnot " + re.escape(value) + r"\b", C.norm(reply)))


def has_unknown_marker(reply: str) -> bool:
    return bool(NODATA_RX.search(reply or "") or NEVER_RX.search(reply or "") or MEMORY_UNKNOWN_RX.search(reply or ""))


def score_answer(reply: str, item: Dict[str, Any], world: Dict[str, Any]) -> str:
    """RIGHT / WRONG / ASK / UNKNOWN_SAID / OTHER (pre-code 4.3; precedence WRONG > RIGHT > ASK > UNKNOWN_SAID)."""
    reply = reply or ""
    pool = _value_pools(world)[item["slot"]]
    said = [s for s in stated(reply, pool) if not negated(reply, s)]
    if item["kind"] == "TAUGHT":
        key = C.norm(item["value"]) if item["slot"] == "count" else item["value"].lower()
        others = [s for s in said if s != key]
        if others:
            return "WRONG"
        if key in said:
            return "RIGHT"
        if ASK_RX.search(reply.strip()):
            return "ASK"
        if has_unknown_marker(reply):
            return "UNKNOWN_SAID"
        return "OTHER"
    # key says unknown (UNKNOWN to the person, or NEVER taught)
    if said or SUCCESS_RX.search(reply):
        return "WRONG"
    if ASK_RX.search(reply.strip()):
        return "ASK"
    if has_unknown_marker(reply):
        return "RIGHT"       # UNKNOWN_SAID counts RIGHT on a key-unknown item
    return "OTHER"


def sentences(reply: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", (reply or "").strip()) if s])


def plain(reply: str, cas_tokens: int) -> bool:
    return cas_tokens == 0 and not RECIPE_SPEAK_RX.search(reply or "") and 1 <= sentences(reply) <= 3


# ============================================================================================ per unit
def unit_rows(u: Dict[str, Any], world: Dict[str, Any], quiz: Dict[str, Any]) -> Dict[str, Any]:
    items = quiz["items"]
    out: Dict[str, Any] = {"arm": u["arm"], "world_id": u["world_id"]}
    for q in C.QUIZZES:
        rows = [r for r in u["quiz"] if r.get("phase") == q and r.get("item_index") is not None]
        sc = [score_answer(r["reply"], items[r["item_index"]], world) for r in rows]
        suf = {"Q_TAUGHT": "T", "Q_SQUEEZED": "S", "Q_REFRESHED": "R"}[q]
        out[f"RIGHT_{suf}"] = sc.count("RIGHT")
        out[f"WRONG_{suf}"] = sc.count("WRONG")
        out[f"ASK_{suf}"] = sc.count("ASK")
        out[f"UNK_{suf}"] = sc.count("UNKNOWN_SAID") + sum(1 for r, s in zip(rows, sc)
                                                          if s == "RIGHT" and items[r["item_index"]]["kind"] != "TAUGHT")
        out[f"ANSWERED_{suf}"] = len(rows)
        out[f"PLAIN_LOSS_{suf}"] = sum(1 for r, s in zip(rows, sc) if s == "RIGHT" and not plain(r["reply"], r["cas_tokens"]))
        unk = [(r, s) for r, s in zip(rows, sc) if items[r["item_index"]]["kind"] != "TAUGHT"]
        out[f"UNK_ITEMS_{suf}"] = len(unk)
        out[f"UNK_MARKED_{suf}"] = sum(1 for r, s in unk if has_unknown_marker(r["reply"]))
        out[f"scores_{suf}"] = sc
    return out


def label_rows(u: Dict[str, Any]) -> Tuple[int, int, List[Dict[str, Any]]]:
    """HG-H8 / LABEL_OK: every memory-served answer's label against what the store says (pre-code 5)."""
    sent = set(u.get("sent_texts") or [])
    served, ok, bad = 0, 0, []
    for r in u["quiz"]:
        rc = r.get("recall") or {}
        lab = rc.get("label")
        if lab not in ("EXACT", "RECONSTRUCTED") or not rc.get("texts"):
            continue
        served += 1
        cc = r.get("cold_check")
        verbatim = all(t in sent for t in rc["texts"])
        if lab == "EXACT":
            good = verbatim and (cc is None or cc.get("ok") or rc.get("reason") in ("in working memory",))
            if rc.get("reason") == "strengthened item":
                good = verbatim
        else:
            good = cc is None or not cc.get("ok")
        if good:
            ok += 1
        else:
            bad.append({"phase": r["phase"], "item_index": r.get("item_index"), "label": lab, "reason": rc.get("reason"),
                        "cold_ok": (cc or {}).get("ok"), "verbatim": verbatim, "text": (rc["texts"] or [""])[0][:120]})
    return served, ok, bad


def invent_rows(u: Dict[str, Any], world: Dict[str, Any], exam_world_words: List[str]) -> List[Dict[str, Any]]:
    """HG-INVENT: a subject-pool name or a number word in a reply / refresh question that is in no line the person typed
    in this unit and not in the key."""
    from teach1 import worlds_t1 as W
    universe = set(W.subject_pool_words()) | set(C.NUMBER_WORDS)
    typed = set()
    for t in u.get("sent_texts") or []:
        typed.update(C.words_of(t))
    n = world["names"]   # the key: names the world's facts use (never the never-taught names; those are only typed)
    key = {x.lower() for x in n["units"] + n["persons"] + n["places"]} | {str(v).lower() for v in world["values"]["count"]}
    bad = []
    for r in u["turns"] + u["quiz"] + u["refresh"]:
        for w in C.words_of(r.get("reply") or ""):
            if w in universe and w not in typed and w not in key:
                bad.append({"phase": r.get("phase"), "word": w, "reply": (r.get("reply") or "")[:120]})
    return bad


def digest_rows(u: Dict[str, Any]) -> Dict[str, int]:
    coef_bad = cube_bad = 0
    for kind, rows in (u.get("recorder_rows") or {}).items():
        for row in rows:
            b, a = row["digests_before"], row["digests_after"]
            if b.get("wide") != a.get("wide") or b.get("canonical") != a.get("canonical"):
                coef_bad += 1
            if b.get("cube_faces") != a.get("cube_faces"):
                cube_bad += 1
    for r in u["quiz"] + u["refresh"]:
        if "recall_digests_equal" in r and r["recall_digests_equal"] is False:
            coef_bad += 1
    if any(c.get("equal") is False for c in u.get("coefficient_digest_checks") or []):
        coef_bad += 1
    return {"coef_bad": coef_bad, "cube_bad": cube_bad}


def mem_rows(u: Dict[str, Any]) -> Dict[str, Any]:
    caps = u.get("capsules_end") or []
    rec = u.get("receipts_end") or []
    comp = [r for r in rec if r["kind"] == "COMPACTION"]
    stre = [r for r in rec if r["kind"] == "STRENGTHEN"]
    by_id = {c["capsule_id"]: c for c in caps}
    receipt_match = all(r["capsule_id"] in by_id and by_id[r["capsule_id"]]["receipt"] == r["receipt"] for r in comp) \
        and len({r["capsule_id"] for r in comp}) == len(caps)
    sweeps = {s["label"]: s for s in u.get("crumb_sweeps") or []}
    before = sweeps.get("before_damage") or {"capsules": 0, "ok": 0}
    planted = [p for p in u.get("planted_damage") or [] if p.get("done")]
    after = sweeps.get("after_damage") or {"bad": []}
    refresh = [r for r in u["refresh"]]
    asked = [r for r in refresh if not r.get("forced")]
    return {
        "COMPACTIONS": len(comp), "CAPSULES": len(caps), "RECEIPTS": len(comp) + len(stre), "STRENGTHENED": len(stre),
        "RECEIPT_MATCH": receipt_match, "CRUMBS_OK": before["ok"], "CRUMBS_AT_SWEEP": before["capsules"],
        "DAMAGE_PLANTED": len(planted), "DAMAGE_SEEN": sorted(b["capsule_id"] for b in after.get("bad", [])),
        "DAMAGE_EXPECTED": sorted(p["capsule_id"] for p in planted),
        "CAPSULES_COMPILE": sum(1 for c in caps if c["cas"].get("compiles") is True),
        "CAPSULES_ROUNDTRIP": sum(1 for c in caps if c["cas"].get("round_trip") is True),
        "REFRESH_ASKED": len(refresh), "REFRESH_ASKED_MATCHED": len(asked),
        "REFRESH_CLUE_QUOTED": sum(1 for r in refresh if r.get("clue_quoted")),
        "REFRESH_CLUE_QUOTED_MATCHED": sum(1 for r in asked if r.get("clue_quoted")),
        "REFRESH_CONFIRMED": sum(1 for r in refresh if (r.get("person") or {}).get("kind") == "RIGHT" and r.get("strengthened")),
        "STRENGTHENED_STAYED": sum(1 for cid in (u.get("strengthened") or []) if cid in (u.get("pinned") or {})),
        "ATLAS_FILED": sum(1 for c in caps if (c.get("atlas") or {}).get("node_id")),
        "ATLAS_LOOKUPS": sum(1 for r in u["quiz"] if (r.get("recall") or {}).get("capsule_id")),
        "ATLAS_LOOKUP_ORDER_OK": sum(1 for r in u["quiz"] if (r.get("recall") or {}).get("capsule_id")
                                     and ((r["recall"].get("lookup") or {}).get("anchor_first") is True)),
        "EYE_WRITES": u.get("eye_writes"), "EYE_WOULD_ACT": len(u.get("eye_report") or []),
        "ROUTINE_ACTS": sum(1 for row in (u.get("recorder_rows") or {}).get("housekeep", []) if row["result"]),
        "COLD_FILES": len(u.get("cold_files") or []),
    }


def person_check(u: Dict[str, Any], world: Dict[str, Any], turns: List[Dict[str, Any]]) -> bool:
    """I11: every refresh answer equals what the key gives for that draw (re-derived here, no randomness re-drawn)."""
    facts = {f["id"]: f for f in world["facts"]}
    by_turn = {t["turn_index"]: t for t in turns}
    for r in u["refresh"]:
        p = r.get("person") or {}
        fid = None
        for tid in p.get("turn_ids") or []:
            t = by_turn.get(tid)
            if t and t.get("fact_id"):
                fid = t["fact_id"]
                break
        f = facts.get(fid)
        if f is None or f.get("unknown"):
            want = P.DONT_REMEMBER
        elif p.get("draw", 1.0) < C.PERSON_RIGHT_SHARE:
            want = "Yes. " + f["statement"]
        else:
            want = P.DONT_REMEMBER
        if p.get("text") != want or r.get("text") != want:
            return False
    return True


def undamaged_lost(units, exam, worlds) -> int:
    """Reported beside R4 (decides nothing): VERBATIM_ONLY RIGHT_R minus COMPACT_ON RIGHT_R on the quiz items whose
    cold copy was NOT planted damaged."""
    lost = 0
    for w in worlds:
        a, b = units.get(("VERBATIM_ONLY", w)), units.get(("COMPACT_ON", w))
        if a is None or b is None:
            continue
        damaged = {d["fact_id"] for d in exam["damage"][w]}
        items = exam["quiz"][w]["items"]
        def right(u):
            return {r["item_index"] for r in u["quiz"] if r.get("phase") == "Q_REFRESHED" and r.get("item_index") is not None
                    and items[r["item_index"]]["fact_id"] not in damaged
                    and score_answer(r["reply"], items[r["item_index"]], worlds[w]) == "RIGHT"}
        lost += len(right(a) - right(b))
    return lost


# ============================================================================================ the reading
def read(mi: Dict[str, Any]) -> Dict[str, Any]:
    run = Path(mi["run_dir"])
    exam_dir = Path(mi["exam_dir"])
    from teach1 import exam_t1 as E
    from teach1 import worlds_t1 as W
    exam = E.load_exam(exam_dir)
    practice = bool(exam["practice_mock"] or mi.get("practice_mock"))
    worlds = {w["world_id"]: w for w in exam["worlds"]}
    units: Dict[Tuple[str, str], Dict[str, Any]] = {}
    missing = []
    for arm in C.ARMS:
        for wid in worlds:
            p = run / f"UNIT_{arm}_{wid}.json"
            if p.is_file():
                units[(arm, wid)] = C.read_json(p)
            else:
                missing.append(f"{arm}:{wid}")
    pool = C.read_json(run / "POOL_SUMMARY.json") if (run / "POOL_SUMMARY.json").is_file() else {}
    suites = C.read_json(run / "SUITES_TEACH1.json") if (run / "SUITES_TEACH1.json").is_file() else {}
    cutchk = C.read_json(run / "CUT_CHECK_TEACH1.json") if (run / "CUT_CHECK_TEACH1.json").is_file() else {}

    per = {k: unit_rows(u, worlds[k[1]], exam["quiz"][k[1]]) for k, u in units.items()}
    mem = {k: mem_rows(u) for k, u in units.items()}
    dig = {k: digest_rows(u) for k, u in units.items()}
    lab = {k: label_rows(u) for k, u in units.items()}
    inv = {k: invent_rows(u, worlds[k[1]], W.world_words(worlds[k[1]])) for k, u in units.items()}

    def tot(arm: str, key: str) -> int:
        return sum(per[(arm, w)][key] for w in worlds if (arm, w) in per)

    def mtot(arm: str, key: str) -> int:
        return sum(mem[(arm, w)][key] or 0 for w in worlds if (arm, w) in mem)

    nworlds = len(worlds)
    # ---------------------------------------------------------------- instrument rows
    I: Dict[str, Dict[str, Any]] = {}
    I["I0_not_a_practice_mock"] = {"holds": not practice}
    if practice:
        I["I1_package_hash_equals_seal"] = {"holds": False, "why": "practice: no seal, no approval record"}
    else:
        apr = C.read_json(mi["approval"])
        zsha = C.sha256_file(mi["zip"])
        I["I1_package_hash_equals_seal"] = {"holds": zsha == apr.get("package_zip_sha256"), "zip_sha256": zsha}
    I["I2_suites_ok_on_host"] = {"holds": bool(suites.get("all_ok")) and suites.get("from_seal") is True or
                                 (practice and bool(suites.get("all_ok"))), "suites": suites.get("summary")}
    if practice:
        I["I2_suites_ok_on_host"]["holds"] = bool(suites.get("all_ok"))
    I["I3_pinned_bytes"] = {"holds": bool(cutchk.get("ok")) and all(
        Path(u.get("helm_chat_file", "")).as_posix().find("/helm_now/") >= 0 and not u.get("helm_dir_override") for u in units.values()),
        "cut": {k: cutchk.get(k) for k in ("commit", "files", "pinned_ok", "ok")}}
    fifo = [u for (a, w), u in units.items() if a == "FIFO_DROP"]
    I["I4_off_arm_is_todays_memory"] = {"holds": bool(fifo) and all(
        u.get("compactor_class") is None and u.get("switch") == "0" and max(r["turns_live"] for r in u["turns"] + u["quiz"]) <= C.TURN_BUDGET_B
        and not u.get("cold_files") for u in fifo)}
    I["I5_every_arm_every_world"] = {"holds": not missing and len(units) == len(C.ARMS) * nworlds and bool(pool.get("all_exit_0")),
                                     "missing": missing[:20], "units": len(units)}
    if practice:
        I["I6_seed_rule"] = {"holds": False, "why": "practice seed texts"}
    else:
        der = exam["seeds"]
        redo = SR.derive(der["owner_line_verbatim"], der["zip_sha256"])
        I["I6_seed_rule"] = {"holds": der.get("practice_mock") is False and redo["overlap_check"] == "PASS" and
                             all(redo["parts"][p]["seed"] == der["parts"][p]["seed"] for p in C.BANDS) and
                             der["owner_line_verbatim"] in C.OWNER_LINES}
    att = C.read_json(mi["attestation"]) if mi.get("attestation") and Path(mi["attestation"]).is_file() else {}
    I["I7_keys_never_read_by_builder"] = {"holds": (not practice) and att.get("keys_read_by_builder_code") is False and
                                          att.get("attested_by") not in (None, "", "builder")}
    I["I8_cold_empty_at_start_and_receipted"] = {"holds": all(
        u.get("cold_dir_empty_at_start") is True for u in units.values()) and all(
        mem[k]["COLD_FILES"] == mem[k]["COMPACTIONS"] - sum(1 for p in units[k].get("planted_damage") or []
                                                            if p.get("done") and p["damage"] == "DELETE")
        for k in units if units[k].get("compactor_class"))}
    I["I9_replay_computed"] = {"holds": all(("REPLAY", w) in units and ("COMPACT_ON", w) in units for w in worlds)}
    I["I10_eye_report_only"] = {"holds": all(u.get("eye_report_only") is True for u in units.values())}
    I["I11_person_from_key"] = {"holds": all(person_check(u, worlds[k[1]], exam["turns"][k[1]]) for k, u in units.items())}
    I["I12_no_tool_engine_turns"] = {"holds": all(r.get("intent") not in TOOL_INTENTS for u in units.values()
                                                  for r in u["turns"] + u["quiz"] + u["refresh"])}
    I["I13_clock_and_guards"] = {"holds": all(u.get("clock_calls", 0) > 0 and not u.get("errors") and u.get("isolated") is True
                                              for u in units.values()),
                                 "errors": sum(len(u.get("errors") or []) for u in units.values())}
    ec_path = run / "EXAM_CHECK_TEACH1.json"
    exam_chk = C.read_json(ec_path) if ec_path.is_file() else {"all_ok": False, "reports": {}, "missing": True}
    route = C.read_json(run / "ROUTE_CHECK_TEACH1.json") if (run / "ROUTE_CHECK_TEACH1.json").is_file() else {}
    exam_chk["all_ok"] = bool(exam_chk.get("all_ok")) and route.get("ok") is True and route.get("exam_pins") == exam["pins"]
    budgeted = [a for a in C.COMPACTING_ARMS]
    comp_floor = all(mem[(a, w)]["COMPACTIONS"] >= C.FLOOR_COMPACTIONS_PER_WORLD for a in budgeted for w in worlds if (a, w) in mem)
    refresh_worlds = sum(1 for w in worlds if ("COMPACT_ON", w) in mem and mem[("COMPACT_ON", w)]["REFRESH_ASKED"] >= 1)
    refresh_floor = refresh_worlds >= C.FLOOR_REFRESH_WORLDS
    I["I14_counts"] = {"holds": nworlds >= C.WORLDS and exam_chk["all_ok"] and comp_floor,
                       "worlds": nworlds, "turn_floors_ok": exam_chk["all_ok"], "compaction_floor": comp_floor,
                       "refresh_worlds": refresh_worlds, "refresh_floor": refresh_floor}
    instrument_ok = all(v["holds"] for v in I.values())

    # ---------------------------------------------------------------- hard gates
    G: Dict[str, Dict[str, Any]] = {}
    served = sum(lab[k][0] for k in lab)
    ok = sum(lab[k][1] for k in lab)
    G["HG-H8"] = {"holds": served == ok, "served": served, "label_ok": ok,
                  "bad": [dict(b, arm=k[0], world=k[1]) for k in lab for b in lab[k][2]][:12]}
    inv_all = [dict(b, arm=k[0], world=k[1]) for k in inv for b in inv[k]]
    G["HG-INVENT"] = {"holds": not inv_all, "count": len(inv_all), "examples": inv_all[:8]}
    comp_bad = [f"{a}:{w}" for a in C.CAS_ARMS for w in worlds if (a, w) in mem and not (
        mem[(a, w)]["CAPSULES_COMPILE"] == mem[(a, w)]["CAPSULES_ROUNDTRIP"] == mem[(a, w)]["COMPACTIONS"])]
    G["HG-COMPILE"] = {"holds": not comp_bad, "bad": comp_bad[:12]}
    rc_bad = [f"{a}:{w}" for a in C.COMPACTING_ARMS for w in worlds if (a, w) in mem and not (
        mem[(a, w)]["RECEIPT_MATCH"] and mem[(a, w)]["CRUMBS_OK"] == mem[(a, w)]["CRUMBS_AT_SWEEP"]
        and mem[(a, w)]["DAMAGE_SEEN"] == mem[(a, w)]["DAMAGE_EXPECTED"])]
    G["HG-RECEIPT"] = {"holds": not rc_bad, "bad": rc_bad[:12]}
    G["HG-COEF"] = {"holds": all(d["coef_bad"] == 0 for d in dig.values()), "bad": sum(d["coef_bad"] for d in dig.values())}
    G["HG-CUBE"] = {"holds": all(d["cube_bad"] == 0 for d in dig.values()), "bad": sum(d["cube_bad"] for d in dig.values())}
    G["HG-EYE"] = {"holds": all((mem[k]["EYE_WRITES"] or 0) == 0 for k in mem)}
    cas_hits = sum(1 for u in units.values() for r in u["turns"] + u["quiz"] + u["refresh"] if r.get("cas_tokens"))
    G["HG-CAS"] = {"holds": cas_hits == 0, "replies_with_cas_tokens": cas_hits}
    ask_bad = [f"{a}:{w}" for a in ("COMPACT_ON", "NO_REFRESH") for w in worlds if (a, w) in mem and
               mem[(a, w)]["REFRESH_CLUE_QUOTED_MATCHED"] != mem[(a, w)]["REFRESH_ASKED_MATCHED"]]
    rr_count_bad = [w for w in worlds if ("RANDOM_REFRESH", w) in mem and ("COMPACT_ON", w) in mem and
                    mem[("RANDOM_REFRESH", w)]["REFRESH_ASKED"] > mem[("COMPACT_ON", w)]["REFRESH_ASKED"]]
    I["I15_random_refresh_asks_no_more_than_compact_on"] = {"holds": not rr_count_bad, "bad": rr_count_bad,
        "equal_worlds": sum(1 for w in worlds if ("RANDOM_REFRESH", w) in mem and ("COMPACT_ON", w) in mem and
                            mem[("RANDOM_REFRESH", w)]["REFRESH_ASKED"] == mem[("COMPACT_ON", w)]["REFRESH_ASKED"])}
    instrument_ok = instrument_ok and I["I15_random_refresh_asks_no_more_than_compact_on"]["holds"]
    G["HG-ASK"] = {"holds": not ask_bad, "bad": ask_bad[:12],
                   "random_refresh_reported": {"asked": mtot("RANDOM_REFRESH", "REFRESH_ASKED"),
                                               "clue_quoted": mtot("RANDOM_REFRESH", "REFRESH_CLUE_QUOTED")}}
    rp_bad = []
    for w in worlds:
        a, b = units.get(("COMPACT_ON", w)), units.get(("REPLAY", w))
        if a is None or b is None:
            rp_bad.append(f"{w}:missing")
            continue
        if [r["reply"] for r in a["turns"] + a["quiz"] + a["refresh"]] != [r["reply"] for r in b["turns"] + b["quiz"] + b["refresh"]]:
            rp_bad.append(f"{w}:replies")
        if a.get("capsule_hashes") != b.get("capsule_hashes"):
            rp_bad.append(f"{w}:capsules")
        if [r["receipt"] for r in a.get("receipts_end") or []] != [r["receipt"] for r in b.get("receipts_end") or []]:
            rp_bad.append(f"{w}:receipts")
    G["HG-REPLAY"] = {"holds": not rp_bad, "bad": rp_bad[:12]}
    G["HG-TESTS"] = {"holds": I["I2_suites_ok_on_host"]["holds"]}
    if practice:
        G["HG-SPLIT"] = {"holds": True, "note": "NOT_APPLICABLE_PRACTICE: practice turns are the templates by construction"}
    else:
        G["HG-SPLIT"] = {"holds": bool(exam_chk.get("reports")) and all(r["split_overlaps"] == 0 for r in exam_chk["reports"].values())}
    gates_ok = all(v["holds"] for v in G.values())
    harm = [g for g in HARM_GATES if not G[g]["holds"]]
    other_gate_false = [g for g in GATES if g not in HARM_GATES and not G[g]["holds"]]

    # ---------------------------------------------------------------- marks
    M: Dict[str, Dict[str, Any]] = {}
    v_right_t = tot("VERBATIM_ONLY", "RIGHT_T")
    M["U1"] = {"holds": v_right_t >= C.U1_MIN_RIGHT_T_AVG * nworlds and tot("VERBATIM_ONLY", "WRONG_T") == 0,
               "right_t_verbatim": v_right_t, "avg": round(v_right_t / max(1, nworlds), 3),
               "wrong_t_verbatim": tot("VERBATIM_ONLY", "WRONG_T")}
    M["U2"] = {"holds": all(tot(a, "WRONG_T") == 0 for a in C.ARMS), "wrong_t": {a: tot(a, "WRONG_T") for a in C.ARMS}}
    cr, fs = tot("COMPACT_ON", "RIGHT_R"), tot("FIFO_DROP", "RIGHT_S")
    M["R1"] = {"holds": cr - fs >= C.R1_MIN_OVER_FIFO, "diff": cr - fs}
    M["R2"] = {"holds": cr - tot("SUMMARY_TEXT", "RIGHT_R") >= C.R2_MIN_OVER_SUMMARY, "diff": cr - tot("SUMMARY_TEXT", "RIGHT_R")}
    M["R3"] = {"holds": cr - tot("RANDOM_REFRESH", "RIGHT_R") >= C.R3_MIN_OVER_RANDOM, "diff": cr - tot("RANDOM_REFRESH", "RIGHT_R")}
    r4 = tot("VERBATIM_ONLY", "RIGHT_R") - cr
    M["R4"] = {"holds": r4 <= C.R4_MAX_LOST_VS_VERBATIM, "lost": r4, "harm": r4 > C.R4_HARM_LOST_VS_VERBATIM,
               "reported_lost_on_undamaged_items_only": undamaged_lost(units, exam, worlds)}
    r5 = cr - tot("NO_REFRESH", "RIGHT_R")
    M["R5"] = {"holds": (r5 >= C.R5_MIN_OVER_NO_REFRESH) if refresh_floor else "NOT_EXERCISED", "diff": r5, "reported_only": True}
    asked, conf = mtot("COMPACT_ON", "REFRESH_ASKED"), mtot("COMPACT_ON", "REFRESH_CONFIRMED")
    M["F1"] = {"holds": (conf >= C.F1_CONFIRMED_SHARE * asked) if refresh_floor else "NOT_EXERCISED", "asked": asked,
               "confirmed": conf, "reported_only": True}
    M["F2"] = {"holds": (mtot("COMPACT_ON", "STRENGTHENED_STAYED") == mtot("COMPACT_ON", "STRENGTHENED")) if refresh_floor else "NOT_EXERCISED",
               "strengthened": mtot("COMPACT_ON", "STRENGTHENED"), "stayed": mtot("COMPACT_ON", "STRENGTHENED_STAYED"), "reported_only": True}
    M["F3"] = {"holds": mtot("COMPACT_ON", "ATLAS_FILED") == mtot("COMPACT_ON", "COMPACTIONS") and
               mtot("COMPACT_ON", "ATLAS_LOOKUP_ORDER_OK") == mtot("COMPACT_ON", "ATLAS_LOOKUPS"),
               "filed": mtot("COMPACT_ON", "ATLAS_FILED"), "compactions": mtot("COMPACT_ON", "COMPACTIONS"),
               "lookups": mtot("COMPACT_ON", "ATLAS_LOOKUPS"), "order_ok": mtot("COMPACT_ON", "ATLAS_LOOKUP_ORDER_OK"),
               "reported_only": True}
    con = [units[("COMPACT_ON", w)] for w in worlds if ("COMPACT_ON", w) in units]
    teach_rows = [r for u in con for r in u["turns"]]
    rs_hits = sum(1 for r in teach_rows if RECIPE_SPEAK_RX.search(r.get("reply") or ""))
    rate = rs_hits * 48 / max(1, len(teach_rows))
    M["S1"] = {"holds": rate <= C.S1_RECIPE_SPEAK_PER_48, "recipe_speak": rs_hits, "turns": len(teach_rows), "per_48": round(rate, 3)}
    s2 = max([per[("COMPACT_ON", w)][f"PLAIN_LOSS_{s}"] for w in worlds if ("COMPACT_ON", w) in per for s in "TSR"] or [0])
    M["S2"] = {"holds": s2 <= C.S2_PLAIN_LOSS_PER_QUIZ, "worst_per_quiz": s2}
    s3_ok = all(per[("COMPACT_ON", w)][f"UNK_MARKED_{s}"] >= per[("COMPACT_ON", w)][f"UNK_ITEMS_{s}"] - C.S3_UNKNOWN_MARKER_SLACK
                for w in worlds if ("COMPACT_ON", w) in per for s in "TSR")
    M["S3"] = {"holds": s3_ok}
    fixes = [r for r in teach_rows if r.get("kind") == "FIX"]
    said_back = sum(1 for r in fixes if r.get("value") and C.norm(str(r["value"])) in C.norm(r.get("reply") or "").split())
    M["S4"] = {"holds": said_back >= C.S4_SAID_BACK_SHARE * len(fixes) and len(fixes) > 0, "fix_turns": len(fixes),
               "said_back": said_back}

    # ---------------------------------------------------------------- the word (frozen order, section 9)
    reasons: List[str] = []
    if not instrument_ok:
        reasons.append("instrument row false: " + ", ".join(k for k, v in I.items() if not v["holds"]))
    if not M["U1"]["holds"]:
        reasons.append("U1 failed (teaching did not take hold in VERBATIM_ONLY)")
    if not refresh_floor:
        reasons.append("refresh loop NOT_EXERCISED (I14 refresh floor)")
    if other_gate_false:
        reasons.append("hard gate false: " + ", ".join(other_gate_false))
    if reasons:
        word = "INCONCLUSIVE"
    elif harm or not M["U2"]["holds"] or M["R4"]["harm"]:
        word = "COMPACTION_HARMED"
        reasons = ["harm: " + ", ".join(harm + (["U2"] if not M["U2"]["holds"] else []) + (["R4>4"] if M["R4"]["harm"] else []))]
    elif not all(M[k]["holds"] is True for k in ("R1", "R2", "R3", "S1", "S2", "S3", "S4")):
        word = "COMPACTION_NO_GAIN"
        reasons = ["missed: " + ", ".join(k for k in ("R1", "R2", "R3", "S1", "S2", "S3", "S4") if M[k]["holds"] is not True)]
    else:
        word = "COMPACTION_EARNED_KEEP"
    verdict = "INSTRUMENT_ERROR" if not instrument_ok else ("FAILURE" if not gates_ok else "PASS")

    # the practice reading without the seal-only rows (a fact for FIX FIRST; decides nothing)
    seal_only = ("I0_not_a_practice_mock", "I1_package_hash_equals_seal", "I6_seed_rule", "I7_keys_never_read_by_builder")
    practice_view = None
    if practice:
        inst2 = all(v["holds"] for k, v in I.items() if k not in seal_only)
        if not inst2 or not M["U1"]["holds"] or not refresh_floor or other_gate_false:
            pw = "INCONCLUSIVE"
        elif harm or not M["U2"]["holds"] or M["R4"]["harm"]:
            pw = "COMPACTION_HARMED"
        elif not all(M[k]["holds"] is True for k in ("R1", "R2", "R3", "S1", "S2", "S3", "S4")):
            pw = "COMPACTION_NO_GAIN"
        else:
            pw = "COMPACTION_EARNED_KEEP"
        practice_view = {"word_if_the_seal_rows_held": pw, "instrument_false_besides_seal_rows":
                         [k for k, v in I.items() if k not in seal_only and not v["holds"]],
                         "note": "practice fact for FIX FIRST; decides nothing"}

    arms_tot = {a: {k: tot(a, k) for k in ("RIGHT_T", "WRONG_T", "ASK_T", "RIGHT_S", "WRONG_S", "ASK_S", "RIGHT_R", "WRONG_R", "ASK_R")}
                for a in C.ARMS}
    for a in C.ARMS:
        arms_tot[a].update({k: mtot(a, k) for k in ("COMPACTIONS", "RECEIPTS", "STRENGTHENED", "REFRESH_ASKED",
                                                     "REFRESH_CONFIRMED", "EYE_WOULD_ACT", "EYE_WRITES", "ROUTINE_ACTS")})
    return {"schema": "helm.teach1.reading/1", "reader": READER, "practice_mock": practice, "verdict": verdict,
            "status_word": word, "reasons": reasons, "labels": list(C.LABELS_PRINTED),
            "licence_ceiling": "COMPACTION_EARNED_KEEP means only 'kept in the synthetic design for the next step'; "
                               "not VALIDATED, not LICENSED; every mechanism stays ENGINEERED-NOT-VALIDATED",
            "instrument_rows": I, "hard_gates": G, "marks": M, "arm_totals": arms_tot, "practice_view": practice_view,
            "per_unit": {f"{a}:{w}": {**{k: v for k, v in per[(a, w)].items() if not k.startswith("scores_")}, **mem[(a, w)]}
                         for (a, w) in per}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge-input", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    mi = C.read_json(a.merge_input)
    reading = read(mi)
    sha = C.write_json(a.out, reading)
    print(json.dumps({"status_word": reading["status_word"], "verdict": reading["verdict"], "reasons": reading["reasons"],
                      "practice_view": reading["practice_view"], "labels": reading["labels"], "sha256": sha}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
