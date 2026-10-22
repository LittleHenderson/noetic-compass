"""The frozen reader of TEACH-2: instrument rows I0-I21, the hard gates (TEACH-1's twelve, HG-H8 first, plus HG-WRONG-CUBE,
HG-REVISION, HG-NUMBER, HG-FADE, HG-SAYBACK, HG-OFFLINE, HG-HOLD, HG-LIMIT), the marks (U1-U2, C1-C4, S-SPACE), and the
status word in the frozen order (pre-code f7b6183b... sections 5-9 as amended by A-TEACH2-15, -18 and -19).

    python -X utf8 -B -I <pkg>/teach2/reader_t2.py --merge-input MERGE_INPUT_TEACH2.json --out TEACH2_READING.json

MERGE_INPUT names: the run folder (unit records, POOL_SUMMARY, LIMITS_TEACH2.json, SUITES_TEACH2.json,
CUT_CHECK_TEACH2.json, EXAM_CHECK / ROUTE_CHECK), the exam folder (keys), and for a sealed reading the approval record,
the custodian attestation and the zip. A practice reading (practice_mock) is always INCONCLUSIVE by I0; its marks are
printed as facts that decide nothing. Standard library only. The reader never runs HELM.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from teach2 import common_t2 as C          # noqa: E402
from teach2 import person_t2 as P          # noqa: E402
from teach2 import seed_rule_t2 as SR      # noqa: E402

READER = "reader_t2 v1 (A-TEACH2-19 K1-K4)"
HARM_GATES = ("HG-H8", "HG-INVENT", "HG-COEF", "HG-CUBE", "HG-EYE", "HG-WRONG-CUBE", "HG-REVISION", "HG-OFFLINE",
              "HG-HOLD")
GATES = ("HG-H8", "HG-INVENT", "HG-COMPILE", "HG-RECEIPT", "HG-COEF", "HG-CUBE", "HG-EYE", "HG-CAS", "HG-ASK",
         "HG-REPLAY", "HG-TESTS", "HG-SPLIT", "HG-WRONG-CUBE", "HG-REVISION", "HG-NUMBER", "HG-FADE", "HG-SAYBACK",
         "HG-OFFLINE", "HG-HOLD", "HG-LIMIT")
UNDER_TEST = ("CUBE_OSC", "REPLAY")                       # A-TEACH2-19 K1-K3
LIMIT_FLAGS = ("OVER_LIMIT_PROTECTED", "BATCH_NO_GAIN", "OVER_LIMIT_INDEX")
FULL_CAPSULE_ARMS = ("QUOTE_ONLY", "VERBATIM_ONLY", "EYE_OFF")

# ---- the voice's markers (TEACH-1's reader_t1 copies, frozen) ----
SUCCESS_RX = re.compile(r"\b(?:you can make|we can get|you'll get|works out to|comes to|comes out to|the most you can make|"
                        r"is doable|adds up to|produce that much|carry you to|caps you at|caps this run at|it gives|enough for|"
                        r"yield|gets you|the result is|the answer is|the total is|can produce|we can produce)\b", re.I)
NODATA_RX = re.compile(r"\b(?:no verified facts|don't know|outside what I know|no reliable|don't have reliable|no solid facts|"
                       r"beyond what I've got facts|any grounding|can't support an answer|don't have verified|"
                       r"nothing I have covers|can't answer that)\b", re.I)
NEVER_RX = re.compile(r"\b(?:never been taught|never taught|nobody's taught|haven't been taught|"
                      r"outside anything I've been taught|a gap for me|true gap)\b", re.I)
MEMORY_UNKNOWN_RX = re.compile(r"\b(?:I don't see a specific note on that|I don't have that one any more|"
                               r"don't remember|can't reach them right now)\b", re.I)
ASK_RX = re.compile(r"(?:\?\s*$|which one do you mean|refresh my memory)", re.I)
RECIPE_SPEAK_RX = re.compile(r"\b(?:recipes?|ingredients?|stock|inventory|limiting|yield|batch|receipt|foundation loop|station|"
                             r"gate|RPM|cube|verified facts|flour|water|sugar|butter|eggs?|milk|salt|yeast)\b"
                             r"|how much .* do (?:we|you) have", re.I)
TOOL_INTENTS = ("AGENTIC_GOAL", "STUDY_HYPOTHESIS", "STUDY_REFUSAL")
CAS_TOKEN_RX = re.compile(r"\^\d")


# ============================================================================================ answer scoring
def _value_pools(world: Dict[str, Any]) -> Dict[str, List[str]]:
    v = world["values"]
    return {"count": [C.norm(x) for x in v["count"]], "person": [x.lower() for x in v["person"]],
            "place": [x.lower() for x in v["place"]]}


def stated(reply: str, pool: List[str]) -> List[str]:
    toks = C.norm(reply).split()
    return sorted({p for p in pool if p in toks})


def replaced(reply: str, value: str) -> bool:
    """The current-value rule (pre-code 5, Q1 a; A-TEACH2-19 K4): `value` is marked as a replaced value."""
    t, v = C.norm(reply), re.escape(value)
    pats = (rf"\bnot {v}\b", rf"\binstead of {v}\b", rf"\bearlier i said {v}\b", rf"\bused to be {v}\b",
            rf"\breplaced {v}\b", rf"\breplaces {v}\b", rf"\bwas {v} before\b", rf"\b{v} was replaced\b")
    return any(re.search(p, t) for p in pats)


def has_unknown_marker(reply: str) -> bool:
    return bool(NODATA_RX.search(reply or "") or NEVER_RX.search(reply or "") or MEMORY_UNKNOWN_RX.search(reply or ""))


def score_answer(reply: str, item: Dict[str, Any], world: Dict[str, Any]) -> str:
    """RIGHT / WRONG / ASK / UNKNOWN_SAID / OTHER (precedence WRONG > RIGHT > ASK > UNKNOWN_SAID)."""
    reply = reply or ""
    pool = _value_pools(world)[item["slot"]]
    said = [s for s in stated(reply, pool) if not replaced(reply, s)]
    if item["kind"] == "TAUGHT":
        key = C.norm(item["value"]) if item["slot"] == "count" else item["value"].lower()
        if [s for s in said if s != key]:
            return "WRONG"
        if key in said:
            return "RIGHT"
        if ASK_RX.search(reply.strip()):
            return "ASK"
        if has_unknown_marker(reply):
            return "UNKNOWN_SAID"
        return "OTHER"
    if said or SUCCESS_RX.search(reply):
        return "WRONG"
    if ASK_RX.search(reply.strip()):
        return "ASK"
    if has_unknown_marker(reply):
        return "RIGHT"
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
        out[f"UNK_{suf}"] = sc.count("UNKNOWN_SAID")
        out[f"ANSWERED_{suf}"] = len(rows)
        out[f"PLAIN_LOSS_{suf}"] = sum(1 for r, s in zip(rows, sc) if s == "RIGHT" and not plain(r["reply"], r["cas_tokens"]))
        unk = [r for r in rows if items[r["item_index"]]["kind"] != "TAUGHT"]
        out[f"UNK_ITEMS_{suf}"] = len(unk)
        out[f"UNK_MARKED_{suf}"] = sum(1 for r in unk if has_unknown_marker(r["reply"]))
        out[f"BYTES_{suf}"] = (u.get("phase_marks") or {}).get(q, {}).get("working_bytes")
    return out


def answer_rows(u: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every quiz answer served from memory, with its label and the truth the unit recorded at that moment (K4)."""
    out = []
    sent = set(u.get("sent_texts") or [])
    for r in u["quiz"]:
        ca = r.get("cube_answer")
        if isinstance(ca, dict) and ca.get("label") in ("EXACT", "RECONSTRUCTED"):
            st = r.get("cube_source_state") or {}
            out.append({"phase": r["phase"], "item_index": r.get("item_index"), "via": "cube", "label": ca["label"],
                        "exact_now": bool(st.get("exact_now")), "where": st.get("where"),
                        "capsule_id": st.get("capsule_id"), "cloud_online": r.get("cloud_online"), "verbatim": True})
            continue
        rc = r.get("recall")
        if not isinstance(rc, dict) or rc.get("label") not in ("EXACT", "RECONSTRUCTED") or not rc.get("texts"):
            continue
        cs = r.get("copy_state") or {}
        verbatim = all(t in sent for t in rc["texts"])
        if rc.get("reason") == "in working memory":
            exact_now = True
        elif rc.get("reason") == "strengthened item":
            exact_now = verbatim
        else:
            exact_now = bool(cs.get("ok") and cs.get("reachable"))
        out.append({"phase": r["phase"], "item_index": r.get("item_index"), "via": "capsule", "label": rc["label"],
                    "exact_now": exact_now, "where": cs.get("where"), "capsule_id": cs.get("capsule_id") or rc.get("capsule_id"),
                    "cloud_online": r.get("cloud_online"), "verbatim": verbatim, "reason": rc.get("reason")})
    return out


def label_check(rows: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]], int]:
    """HG-H8: EXACT right iff exact now (and verbatim); RECONSTRUCTED right iff not exact now. HG-OFFLINE count."""
    ok, bad, offline = 0, [], 0
    for a in rows:
        good = (a["exact_now"] and a["verbatim"]) if a["label"] == "EXACT" else not a["exact_now"]
        if a["label"] == "EXACT" and a.get("where") == "cloud" and a.get("cloud_online") is False:
            offline += 1
            good = False
        if good:
            ok += 1
        else:
            bad.append(a)
    return len(rows), ok, bad, offline


def invent_rows(u: Dict[str, Any], world: Dict[str, Any]) -> List[Dict[str, Any]]:
    from teach2 import worlds_t2 as W
    universe = set(W.subject_pool_words()) | set(C.NUMBER_WORDS)
    typed = set()
    for t in u.get("sent_texts") or []:
        typed.update(C.words_of(t))
    n = world["names"]
    key = {x.lower() for x in n["units"] + n["persons"] + n["places"]} | {str(v).lower() for v in world["values"]["count"]}
    bad = []
    for r in u["turns"] + u["quiz"] + u["refresh"]:
        for w in C.words_of(r.get("reply") or ""):
            if w in universe and w not in typed and w not in key:
                bad.append({"phase": r.get("phase"), "word": w, "reply": (r.get("reply") or "")[:120]})
    return bad


def digest_rows(u: Dict[str, Any]) -> Dict[str, int]:
    coef_bad = cube_bad = 0
    rows = [row for rows in (u.get("recorder_rows") or {}).values() for row in rows]
    rows += [row for row in (u.get("osc_recorder_rows") or {}).get("answer", [])]
    for row in rows:
        b, a = row["digests_before"], row["digests_after"]
        if b.get("wide") != a.get("wide") or b.get("canonical") != a.get("canonical"):
            coef_bad += 1
        if b.get("cube_faces") != a.get("cube_faces"):
            cube_bad += 1
    for r in u["quiz"] + u["refresh"]:
        if r.get("recall_digests_equal") is False:
            coef_bad += 1
    if any(c.get("equal") is False for c in u.get("coefficient_digest_checks") or []):
        coef_bad += 1
    return {"coef_bad": coef_bad, "cube_bad": cube_bad}


# ---- cubes (A-TEACH2-19 K4)
def turn_facts(u: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """turn id -> (phase, kind, fact id) for every line the person typed in this unit."""
    out = {}
    for r in u["turns"]:
        if r.get("turn_id") is not None:
            out[r["turn_id"]] = {"phase": "TEACH", "kind": r.get("kind"), "fact_id": r.get("fact_id")}
    for r in u["refresh"]:
        if r.get("turn_id") is not None:
            p = r.get("person") or {}
            out[r["turn_id"]] = {"phase": "REFRESH", "kind": "REFRESH_" + str(p.get("kind")),
                                 "fact_id": p.get("fact_id") if p.get("kind") == "RIGHT" else None}
    for r in u["quiz"]:
        if r.get("turn_id") is not None:
            out[r["turn_id"]] = {"phase": r["phase"], "kind": "QUIZ", "fact_id": None}
    return out


def current_branches(u: Dict[str, Any]) -> List[Dict[str, Any]]:
    latest: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for b in u.get("branches_end") or []:
        com = b.get("commonality") or {}
        if "kind" in com:
            latest[(b["source"], b["target"], com["kind"])] = b
    return list(latest.values())


def _prov_turn(b: Dict[str, Any]) -> Optional[int]:
    for ref in b.get("provenance_refs") or []:
        if str(ref).startswith("turn:"):
            return int(str(ref).split(":", 1)[1])
    return None


def cube_rows(u: Dict[str, Any], world: Dict[str, Any]) -> Dict[str, Any]:
    facts = {f["id"]: f for f in world["facts"]}
    tf = turn_facts(u)
    wrong, trap_wrong, mismatch = [], 0, 0
    for b in current_branches(u):
        tid = _prov_turn(b)
        info = tf.get(tid) or {}
        f = facts.get(info.get("fact_id"))
        com = b.get("commonality") or {}
        got = str(com.get("amount") or com.get("referent") or "").lower()
        why = None
        if f is None or info.get("kind") in ("SMALL", "UNKNOWN", "QUIZ") or f.get("unknown"):
            why = "no keyed fact behind the line"
        elif got != str(f["value"]).lower():
            why = f"value {got} != key {str(f['value']).lower()}"
        if why:
            wrong.append({"branch_id": b["branch_id"], "turn_id": tid, "kind": info.get("kind"),
                          "fact_id": info.get("fact_id"), "why": why})
            trap_wrong += info.get("kind") == "TRAP"
        if f is not None and b["source"] != "thing_" + str(f.get("unit", "")).lower():
            mismatch += 1
    teach_ids = {t for t, i in tf.items() if i["phase"] == "TEACH"}
    stored = sum(1 for b in u.get("branches_end") or [] if _prov_turn(b) in teach_ids)
    snaps = u.get("branch_snapshots") or []
    rev_ok = all(snaps[i] == snaps[i + 1][:len(snaps[i])] for i in range(len(snaps) - 1)) and \
        len({b["branch_id"] for b in u.get("branches_end") or []}) == len(u.get("branches_end") or [])
    rounds = [r.get("rounds", 0) for r in u.get("osc_log") or []]
    return {"CUBES_STORED": stored, "CUBES_WRONG": len(wrong), "CUBES_TRAP_WRONG": trap_wrong,
            "CUBES_THING_MISMATCH": mismatch, "WRONG_LIST": wrong[:10], "REVISION_OK": rev_ok,
            "ROUNDS_MAX": max(rounds or [0]), "ROUNDS_HIST": {str(k): rounds.count(k) for k in sorted(set(rounds))},
            "AGREE_RATE": round(sum(1 for r in u.get("osc_log") or [] if r.get("kept")) / max(1, len(rounds)), 4),
            "SHADOW_AGREE": sum(1 for r in u.get("osc_log") or [] if r.get("shadow_agree_at")),
            "SHADOW_WRITES": u.get("store_writes_from_shadow") or 0}


# ---- memory rows
_NUM_WORDS = set(C.NUMBER_WORDS)


def _scan_numbers(obj: Any, keys=("c", "clues", "sentence", "notation")) -> List[str]:
    """HG-NUMBER (K4): number words or digit runs inside clue lists, CAS sentences and notations (^n removed)."""
    hits: List[str] = []

    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, list):
            for y in x:
                yield from strings(y)
        elif isinstance(x, dict):
            for y in x.values():
                yield from strings(y)

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in keys:
                    for s in strings(v):
                        t = CAS_TOKEN_RX.sub(" ", s).lower()
                        hits.extend(w for w in re.findall(r"[a-z]+|\d+", t) if w in _NUM_WORDS or w.isdigit())
                else:
                    walk(v)
        elif isinstance(x, list):
            for y in x:
                walk(y)
    walk(obj)
    return hits


def mem_rows(u: Dict[str, Any], limit: Optional[int]) -> Dict[str, Any]:
    comp = u.get("compactions") or {}
    rec = u.get("receipts_end") or []
    stre = [r for r in rec if r["kind"] == "STRENGTHEN"]
    sweeps = {s["label"]: s for s in u.get("crumb_sweeps") or []}
    before = sweeps.get("before_damage") or {"capsules": 0, "ok": 0}
    after = sweeps.get("after_damage") or {"bad": []}
    planted = [p for p in u.get("planted_damage") or [] if p.get("done")]
    refresh = list(u["refresh"])
    stored = u.get("stored_rows") or []
    full = [r for r in stored if isinstance(r, dict) and "cas" in r]
    # HG-NUMBER
    folds = []
    for txt in (u.get("fold_records") or {}).values():
        try:
            folds.append(json.loads(txt))
        except ValueError:
            folds.append({"c": [txt]})
    numbers = _scan_numbers(stored) + _scan_numbers(u.get("s2_records") or []) + _scan_numbers(folds)
    # HG-FADE
    eye = u.get("eye_log") or []
    batches = u.get("batch_log") or []
    fade_bad = [b["capsule_id"] for b in batches if b["capsule_id"] not in comp]
    fade_bad += [e.get("capsule_id") for e in eye if e["kind"] in ("MOVE_OFF", "FOLD") and not e.get("digest")]
    unconfirmed = {k for k, v in (u.get("thing_provenance") or {}).items() if v != "CHECKED"}
    capsule_turns = {t for c in comp.values() for t in c["turn_ids"]}
    faded_protected = [b["branch_id"] for b in current_branches(u)
                       if b["source"] in unconfirmed and _prov_turn(b) in capsule_turns]
    # HG-LIMIT (K4: an over-limit stretch is explained by a limit flag raised in that stretch)
    limit_bad = 0
    if limit is not None:
        explained = False
        for row in u.get("bytes_log") or []:
            if row["working_bytes"] <= limit:
                explained = False
                continue
            if any(f in LIMIT_FLAGS for f in row.get("flags_raised") or []):
                explained = True
            if not explained:
                limit_bad += 1
    held = set(u.get("eye_held") or []) | {e.get("capsule_id") for e in eye if e["kind"] == "HOLD"}
    return {
        "COMPACTIONS": len(comp), "BATCHES": len(batches), "MOVED_OFF": sum(1 for e in eye if e["kind"] == "MOVE_OFF"),
        "FOLDS": sum(1 for e in eye if e["kind"] == "FOLD"), "CLOUD_MOVES": len(u.get("moved_to_cloud") or {}),
        "RECEIPTS": len(rec), "STRENGTHENED": len(stre),
        "CRUMBS_OK": before["ok"], "CRUMBS_AT_SWEEP": before["capsules"], "DAMAGE_PLANTED": len(planted),
        "DAMAGE_SEEN": sorted(b["capsule_id"] for b in after.get("bad", [])),
        "DAMAGE_EXPECTED": sorted(p["capsule_id"] for p in planted),
        "FULL_CAPSULES": len(full), "CAPSULES_COMPILE": sum(1 for c in full if c["cas"].get("compiles") is True),
        "CAPSULES_ROUNDTRIP": sum(1 for c in full if c["cas"].get("round_trip") is True),
        "REFRESH_ASKED": len(refresh), "REFRESH_CLUE_QUOTED": sum(1 for r in refresh if r.get("clue_quoted")),
        "REFRESH_CONFIRMED": sum(1 for r in refresh if (r.get("person") or {}).get("kind") == "RIGHT" and r.get("strengthened")),
        "EYE_WRITES": u.get("eye_writes"), "EYE_WOULD_ACT": len(u.get("eye_report") or []),
        "NUMBER_HITS": len(numbers), "NUMBER_EXAMPLES": numbers[:6], "FADE_BAD": fade_bad[:10],
        "FADED_PROTECTED": len(faded_protected), "LIMIT_UNEXPLAINED": limit_bad, "HELD": sorted(h for h in held if h),
        "PEAK_BYTES": max([b["working_bytes"] for b in u.get("bytes_log") or []] or [0]),
        "COLD_FILES": len(u.get("cold_files") or []), "CLOUD_DELETES": u.get("cloud_deletes") or 0,
        "LIMIT_FLAGS_RAISED": sorted({f for b in u.get("bytes_log") or [] for f in b.get("flags_raised") or []}),
    }


def sayback_bad(u: Dict[str, Any]) -> List[Dict[str, Any]]:
    bad = []
    for s in u.get("saybacks") or []:
        r = s.get("reading") or {}
        allowed = {r.get("thing"), r.get("value"), r.get("replaces"), "this", "replaces"} | set(r.get("slot") or [])
        extra = [w for w in C.words_of(s["line"]) if w not in allowed]
        if s.get("cas_tokens") or extra:
            bad.append({"line": s["line"], "cas_tokens": s.get("cas_tokens"), "extra": extra[:4]})
    return bad


def person_check(u: Dict[str, Any], world: Dict[str, Any], turns: List[Dict[str, Any]]) -> bool:
    """I11: every refresh answer equals what the key gives for that draw (re-derived, no randomness re-drawn)."""
    facts = {f["id"]: f for f in world["facts"]}
    by_turn = {t["turn_index"]: t for t in turns}
    sent_turn = {r.get("turn_id"): r.get("turn_index") for r in u["turns"]}
    for r in u["refresh"]:
        p = r.get("person") or {}
        fid = None
        for tid in p.get("turn_ids") or []:
            t = by_turn.get(sent_turn.get(tid))
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


def right_r_undamaged(u, exam, world) -> int:
    w = world["world_id"]
    damaged = {d["fact_id"] for d in exam["damage"][w]}
    items = exam["quiz"][w]["items"]
    return sum(1 for r in u["quiz"] if r.get("phase") == "Q_REFRESHED" and r.get("item_index") is not None
               and items[r["item_index"]]["fact_id"] not in damaged
               and score_answer(r["reply"], items[r["item_index"]], world) == "RIGHT")


# ============================================================================================ the reading
def read(mi: Dict[str, Any]) -> Dict[str, Any]:
    run = Path(mi["run_dir"])
    exam_dir = Path(mi["exam_dir"])
    from teach2 import exam_t2 as E
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
    suites = C.read_json(run / "SUITES_TEACH2.json") if (run / "SUITES_TEACH2.json").is_file() else {}
    cutchk = C.read_json(run / "CUT_CHECK_TEACH2.json") if (run / "CUT_CHECK_TEACH2.json").is_file() else {}
    limits = C.read_json(run / "LIMITS_TEACH2.json") if (run / "LIMITS_TEACH2.json").is_file() else {}
    lim = limits.get("working_limit_bytes")

    per = {k: unit_rows(u, worlds[k[1]], exam["quiz"][k[1]]) for k, u in units.items()}
    mem = {k: mem_rows(u, lim if k[0] in C.CUBE_ARMS else None) for k, u in units.items()}
    cub = {k: cube_rows(u, worlds[k[1]]) for k, u in units.items() if k[0] in C.CUBE_ARMS}
    dig = {k: digest_rows(u) for k, u in units.items()}
    ans = {k: answer_rows(u) for k, u in units.items()}
    lab = {k: label_check(v) for k, v in ans.items()}
    inv = {k: invent_rows(u, worlds[k[1]]) for k, u in units.items()}
    sbk = {k: sayback_bad(u) for k, u in units.items()}

    def tot(arm: str, key: str) -> int:
        return sum(per[(arm, w)][key] or 0 for w in worlds if (arm, w) in per)

    def mtot(arm: str, key: str) -> int:
        return sum(mem[(arm, w)][key] or 0 for w in worlds if (arm, w) in mem)

    def ctot(arm: str, key: str) -> int:
        return sum(cub[(arm, w)][key] or 0 for w in worlds if (arm, w) in cub)

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
    I["I2_suites_ok_on_host"] = {"holds": bool(suites.get("all_ok")) and (practice or suites.get("from_seal") is True),
                                 "suites": suites.get("summary")}
    I["I3_pinned_bytes"] = {"holds": bool(cutchk.get("helm_cut_ok")) and all(
        Path(u.get("helm_chat_file", "")).as_posix().find("/helm_now/") >= 0 and not u.get("helm_dir_override") for u in units.values()),
        "cut": {k: cutchk.get(k) for k in ("commit", "files", "pinned_ok", "helm_cut_ok")}}
    fifo = [u for (a, w), u in units.items() if a == "FIFO_DROP"]
    I["I4_off_arm_is_todays_memory"] = {"holds": bool(fifo) and all(
        u.get("compactor_class") is None and u.get("switch") == "0" and u.get("cube_mode") is None and
        max(r["turns_live"] for r in u["turns"] + u["quiz"]) <= C.TURN_BUDGET_B and not u.get("cold_files") for u in fifo)}
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
    I["I8_cold_empty_at_start"] = {"holds": all(u.get("cold_dir_empty_at_start") is True for u in units.values())}
    I["I9_replay_computed"] = {"holds": all(("REPLAY", w) in units and ("CUBE_OSC", w) in units for w in worlds)}
    I["I10_eye_report_only"] = {"holds": all(u.get("eye_report_only") is True for u in units.values())}
    I["I11_person_from_key"] = {"holds": all(person_check(u, worlds[k[1]], exam["turns"][k[1]]) for k, u in units.items())}
    I["I12_no_tool_engine_turns"] = {"holds": all(r.get("intent") not in TOOL_INTENTS for u in units.values()
                                                  for r in u["turns"] + u["quiz"] + u["refresh"])}
    I["I13_clock_and_guards"] = {"holds": all(u.get("clock_calls", 0) > 0 and not u.get("errors") and u.get("isolated") is True
                                              for u in units.values()),
                                 "errors": sum(len(u.get("errors") or []) for u in units.values()),
                                 "examples": [e for u in units.values() for e in u.get("errors") or []][:4]}
    exam_chk = C.read_json(run / "EXAM_CHECK_TEACH2.json") if (run / "EXAM_CHECK_TEACH2.json").is_file() else {"all_ok": False, "reports": {}}
    route = C.read_json(run / "ROUTE_CHECK_TEACH2.json") if (run / "ROUTE_CHECK_TEACH2.json").is_file() else {}
    exam_ok = bool(exam_chk.get("all_ok")) and route.get("ok") is True and route.get("exam_pins") == exam["pins"]
    I["I14_counts"] = {"holds": nworlds >= C.WORLDS and exam_ok, "worlds": nworlds, "turn_floors_and_route_ok": exam_ok}
    I["I15_arm_settings"] = {"holds": all(
        (u.get("cube_mode") == C.ARM_SET[k[0]]["mode"]) and
        (all(u.get("proposers_are_ctt") or [False]) if k[0] in C.CTT_ARMS else not u.get("proposers")) and
        ((u.get("reader") is not None) == (k[0] in C.RULE_ARMS)) and
        ((u.get("capsule_list_class") == "list") if k[0] == "EYE_OFF" else True) and
        ((u.get("clue_every_line") is False) if k[0] == "FIRST8" else True)
        for k, u in units.items())}
    I["I16_ctt_weights_pinned"] = {"holds": bool((cutchk.get("ctt") or {}).get("ok")),
                                   "weights": (cutchk.get("ctt") or {}).get("weights")}
    I["I17_round_cap"] = {"holds": all(c["ROUNDS_MAX"] <= C.ROUND_CAP for c in cub.values()) and
                          all(c["SHADOW_WRITES"] == 0 for c in cub.values())}
    stored = ctot("CUBE_OSC", "CUBES_STORED")
    I["I18_oscillation_exercised"] = {"holds": stored >= C.I18_MIN_CUBES, "cubes_stored": stored, "floor": C.I18_MIN_CUBES}
    b, mo = mtot("CUBE_OSC", "BATCHES"), mtot("CUBE_OSC", "MOVED_OFF")
    I["I19_memory_exercised"] = {"holds": b >= C.I19_MIN_BATCHES and mo >= C.I19_MIN_MOVED_OFF, "batches": b, "moved_off": mo}
    ctt_bad = {f"{a}:{w}": (u.get("ctt") or {}).get("violations") for (a, w), u in units.items()
               if a in C.CTT_ARMS and ((u.get("ctt") or {}).get("violations") or not u.get("ctt"))}
    I["I20_ctt_audits_clean"] = {"holds": not ctt_bad, "bad": dict(list(ctt_bad.items())[:6])}
    redo_lim = None
    if all(("VERBATIM_ONLY", w) in units for w in worlds):
        vb = [int(units[("VERBATIM_ONLY", w)]["phase_marks"]["Q_REFRESHED"]["working_bytes"]) for w in worlds]
        redo_lim = int(statistics.median(vb) // 2 // C.LIMIT_ROUND_TO) * C.LIMIT_ROUND_TO
    used_ok = all((units[(a, w)].get("limits_used") or {}).get("working_limit_bytes") == lim
                  for (a, w) in units if a in C.CUBE_ARMS)
    I["I21_limits_by_the_rule"] = {"holds": redo_lim is not None and redo_lim == lim == limits.get("device_limit_bytes") and used_ok,
                                   "recomputed": redo_lim, "file": lim}
    instrument_ok = all(v["holds"] for v in I.values())

    # ---------------------------------------------------------------- hard gates
    G: Dict[str, Dict[str, Any]] = {}
    served = sum(lab[k][0] for k in lab)
    ok = sum(lab[k][1] for k in lab)
    G["HG-H8"] = {"holds": served == ok, "served": served, "label_ok": ok,
                  "bad": [dict(b, arm=k[0], world=k[1]) for k in lab for b in lab[k][2]][:12]}
    inv_all = [dict(b, arm=k[0], world=k[1]) for k in inv for b in inv[k]]
    G["HG-INVENT"] = {"holds": not inv_all, "count": len(inv_all), "examples": inv_all[:8]}
    comp_bad = [f"{a}:{w}" for (a, w), m in mem.items() if a in FULL_CAPSULE_ARMS and
                not (m["CAPSULES_COMPILE"] == m["CAPSULES_ROUNDTRIP"] == m["FULL_CAPSULES"])]
    G["HG-COMPILE"] = {"holds": not comp_bad, "bad": comp_bad[:12]}
    rc_bad = [f"{a}:{w}" for (a, w), m in mem.items() if units[(a, w)].get("compactor_class") and not (
        m["CRUMBS_OK"] == m["CRUMBS_AT_SWEEP"] and m["DAMAGE_SEEN"] == m["DAMAGE_EXPECTED"])]
    G["HG-RECEIPT"] = {"holds": not rc_bad, "bad": rc_bad[:12]}
    G["HG-COEF"] = {"holds": all(d["coef_bad"] == 0 for d in dig.values()), "bad": sum(d["coef_bad"] for d in dig.values())}
    G["HG-CUBE"] = {"holds": all(d["cube_bad"] == 0 for d in dig.values()), "bad": sum(d["cube_bad"] for d in dig.values())}
    G["HG-EYE"] = {"holds": all((m["EYE_WRITES"] or 0) == 0 for m in mem.values())}
    cas_hits = sum(1 for u in units.values() for r in u["turns"] + u["quiz"] + u["refresh"] if r.get("cas_tokens"))
    G["HG-CAS"] = {"holds": cas_hits == 0, "replies_with_cas_tokens": cas_hits}
    ask_bad = [f"{a}:{w}" for (a, w), m in mem.items() if m["REFRESH_CLUE_QUOTED"] != m["REFRESH_ASKED"]]
    G["HG-ASK"] = {"holds": not ask_bad, "bad": ask_bad[:12]}
    rp_bad = []
    for w in worlds:
        a, b2 = units.get(("CUBE_OSC", w)), units.get(("REPLAY", w))
        if a is None or b2 is None:
            rp_bad.append(f"{w}:missing")
            continue
        if [r["reply"] for r in a["turns"] + a["quiz"] + a["refresh"]] != [r["reply"] for r in b2["turns"] + b2["quiz"] + b2["refresh"]]:
            rp_bad.append(f"{w}:replies")
        if a.get("stored_rows_sha256") != b2.get("stored_rows_sha256"):
            rp_bad.append(f"{w}:stored_rows")
        if [r["receipt"] for r in a.get("receipts_end") or []] != [r["receipt"] for r in b2.get("receipts_end") or []]:
            rp_bad.append(f"{w}:receipts")
        if [(x["branch_id"], x["commonality"]) for x in a.get("branches_end") or []] != \
                [(x["branch_id"], x["commonality"]) for x in b2.get("branches_end") or []]:
            rp_bad.append(f"{w}:branches")
    G["HG-REPLAY"] = {"holds": not rp_bad, "bad": rp_bad[:12]}
    G["HG-TESTS"] = {"holds": I["I2_suites_ok_on_host"]["holds"]}
    if practice:
        G["HG-SPLIT"] = {"holds": True, "note": "NOT_APPLICABLE_PRACTICE: practice turns are the templates by construction"}
    else:
        G["HG-SPLIT"] = {"holds": bool(exam_chk.get("reports")) and all(r["split_overlaps"] == 0 for r in exam_chk["reports"].values())}
    wc = {a: ctot(a, "CUBES_WRONG") for a in C.CUBE_ARMS}
    G["HG-WRONG-CUBE"] = {"holds": all(wc[a] == 0 for a in UNDER_TEST), "cubes_wrong": wc,
                          "trap_wrong": {a: ctot(a, "CUBES_TRAP_WRONG") for a in C.CUBE_ARMS},
                          "examples": [dict(x, arm=k[0], world=k[1]) for k, c in cub.items() if k[0] in UNDER_TEST
                                       for x in c["WRONG_LIST"]][:8]}
    G["HG-REVISION"] = {"holds": all(cub[k]["REVISION_OK"] for k in cub if k[0] in UNDER_TEST),
                        "reported_other_arms_ok": {a: all(cub[k]["REVISION_OK"] for k in cub if k[0] == a) for a in C.CUBE_ARMS}}
    nb = {f"{a}:{w}": m["NUMBER_EXAMPLES"] for (a, w), m in mem.items() if m["NUMBER_HITS"]}
    G["HG-NUMBER"] = {"holds": not nb, "bad": dict(list(nb.items())[:6])}
    fb = {f"{a}:{w}": {"fade_bad": m["FADE_BAD"], "faded_protected": m["FADED_PROTECTED"]}
          for (a, w), m in mem.items() if a in C.CUBE_ARMS and (m["FADE_BAD"] or m["FADED_PROTECTED"])}
    G["HG-FADE"] = {"holds": not fb, "bad": dict(list(fb.items())[:6])}
    sb = {f"{a}:{w}": v[:3] for (a, w), v in sbk.items() if v}
    G["HG-SAYBACK"] = {"holds": not sb, "bad": dict(list(sb.items())[:6])}
    off = sum(lab[k][3] for k in lab)
    G["HG-OFFLINE"] = {"holds": off == 0, "exact_while_offline": off}
    held_hits = []
    for k, rows in ans.items():
        held = set(mem[k]["HELD"])
        held_hits += [f"{k[0]}:{k[1]}:{a.get('capsule_id')}" for a in rows if a.get("capsule_id") in held]
    G["HG-HOLD"] = {"holds": not held_hits, "bad": held_hits[:8]}
    lb = {f"{a}:{w}": m["LIMIT_UNEXPLAINED"] for (a, w), m in mem.items() if a in C.CUBE_ARMS and m["LIMIT_UNEXPLAINED"]}
    G["HG-LIMIT"] = {"holds": not lb, "unexplained_turns": dict(list(lb.items())[:8]), "limit": lim}
    gates_ok = all(v["holds"] for v in G.values())
    harm = [g for g in HARM_GATES if not G[g]["holds"]]
    other_gate_false = [g for g in GATES if g not in HARM_GATES and not G[g]["holds"]]

    # ---------------------------------------------------------------- marks
    M: Dict[str, Dict[str, Any]] = {}
    v_right_t = tot("VERBATIM_ONLY", "RIGHT_T")
    M["U1"] = {"holds": v_right_t >= C.U1_MIN_RIGHT_T_AVG * nworlds and tot("VERBATIM_ONLY", "WRONG_T") == 0,
               "right_t_verbatim": v_right_t, "avg": round(v_right_t / max(1, nworlds), 3),
               "wrong_t_verbatim": tot("VERBATIM_ONLY", "WRONG_T")}
    M["U2"] = {"holds": all(tot(a, "WRONG_T") == 0 for a in UNDER_TEST), "applies_to": list(UNDER_TEST),
               "wrong_t_every_arm_reported": {a: tot(a, "WRONG_T") for a in C.ARMS}}
    cr = tot("CUBE_OSC", "RIGHT_R")
    M["C1"] = {"holds": cr - tot("QUOTE_ONLY", "RIGHT_R") >= C.C1_MIN_OVER_QUOTE, "diff": cr - tot("QUOTE_ONLY", "RIGHT_R")}
    tr, tw, cw = tot("TABLE", "RIGHT_R"), tot("TABLE", "WRONG_R"), tot("CUBE_OSC", "WRONG_R")
    M["C2"] = {"holds": (cr - tr >= C.C2_MIN_OVER_TABLE) or (cr == tr and tw - cw >= C.C2_MIN_FEWER_WRONG),
               "right_diff": cr - tr, "wrong_table": tw, "wrong_cube_osc": cw,
               "table_osc_reported": {"right_r": tot("TABLE_OSC", "RIGHT_R"), "wrong_r": tot("TABLE_OSC", "WRONG_R")}}
    rival_wrong = wc["ONE_READER"] + wc["CTT_ONLY"]
    best_rival = max(tot("ONE_READER", "RIGHT_R"), tot("CTT_ONLY", "RIGHT_R"))
    M["C3"] = {"holds": (rival_wrong >= C.C3_MIN_WRONG_ELSEWHERE and G["HG-WRONG-CUBE"]["holds"]) or
               (cr - best_rival >= C.C3_MIN_OVER_ONE), "rival_cubes_wrong": rival_wrong, "right_over_best_rival": cr - best_rival}
    c4 = sum(right_r_undamaged(units[("VERBATIM_ONLY", w)], exam, worlds[w]) - right_r_undamaged(units[("CUBE_OSC", w)], exam, worlds[w])
             for w in worlds if ("VERBATIM_ONLY", w) in units and ("CUBE_OSC", w) in units)
    M["C4"] = {"holds": c4 <= C.C4_MAX_LOST_VS_VERBATIM, "lost": c4, "harm": c4 > C.C4_HARM_LOST_VS_VERBATIM,
               "scored_on": "undamaged quiz items only (A-TEACH1-2's rule)"}
    bc, bv = tot("CUBE_OSC", "BYTES_R"), tot("VERBATIM_ONLY", "BYTES_R")
    num, den = C.S_SPACE_SHARE
    M["S-SPACE"] = {"holds": bc * den <= bv * num and G["HG-LIMIT"]["holds"], "bytes_cube_osc": bc, "bytes_verbatim": bv,
                    "part_a": bc * den <= bv * num, "part_b_hg_limit": G["HG-LIMIT"]["holds"],
                    "eye_off_reported": tot("EYE_OFF", "BYTES_R"), "first8_reported": tot("FIRST8", "BYTES_R")}

    # ---------------------------------------------------------------- the word (frozen order, section 9)
    reasons: List[str] = []
    if not instrument_ok:
        reasons.append("instrument row false: " + ", ".join(k for k, v in I.items() if not v["holds"]))
    if not M["U1"]["holds"]:
        reasons.append("U1 failed (teaching did not take hold in VERBATIM_ONLY)")
    if other_gate_false:
        reasons.append("hard gate false: " + ", ".join(other_gate_false))
    if reasons:
        word = "INCONCLUSIVE"
    elif harm or not M["U2"]["holds"] or M["C4"]["harm"]:
        word = "CUBES_HARMED"
        reasons = ["harm: " + ", ".join(harm + (["U2"] if not M["U2"]["holds"] else []) + (["C4>4"] if M["C4"]["harm"] else []))]
    elif not all(M[k]["holds"] is True for k in ("C1", "C2", "C3", "S-SPACE")):
        word = "CUBES_NO_GAIN"
        reasons = ["missed: " + ", ".join(k for k in ("C1", "C2", "C3", "S-SPACE") if M[k]["holds"] is not True)]
    else:
        word = "CUBES_EARNED_KEEP"
    verdict = "INSTRUMENT_ERROR" if not instrument_ok else ("FAILURE" if not gates_ok else "PASS")

    seal_only = ("I0_not_a_practice_mock", "I1_package_hash_equals_seal", "I6_seed_rule", "I7_keys_never_read_by_builder")
    practice_view = None
    if practice:
        inst2 = all(v["holds"] for k, v in I.items() if k not in seal_only)
        if not inst2 or not M["U1"]["holds"] or other_gate_false:
            pw = "INCONCLUSIVE"
        elif harm or not M["U2"]["holds"] or M["C4"]["harm"]:
            pw = "CUBES_HARMED"
        elif not all(M[k]["holds"] is True for k in ("C1", "C2", "C3", "S-SPACE")):
            pw = "CUBES_NO_GAIN"
        else:
            pw = "CUBES_EARNED_KEEP"
        practice_view = {"word_if_the_seal_rows_held": pw, "instrument_false_besides_seal_rows":
                         [k for k, v in I.items() if k not in seal_only and not v["holds"]],
                         "note": "practice fact for FIX FIRST; decides nothing"}
    arms_tot = {a: {k: tot(a, k) for k in ("RIGHT_T", "WRONG_T", "ASK_T", "RIGHT_S", "WRONG_S", "ASK_S", "RIGHT_R", "WRONG_R",
                                           "ASK_R", "BYTES_R")} for a in C.ARMS}
    for a in C.ARMS:
        arms_tot[a].update({k: mtot(a, k) for k in ("COMPACTIONS", "BATCHES", "MOVED_OFF", "FOLDS", "CLOUD_MOVES",
                                                     "REFRESH_ASKED", "REFRESH_CONFIRMED", "EYE_WOULD_ACT", "EYE_WRITES")})
        if a in C.CUBE_ARMS:
            arms_tot[a].update({k: ctot(a, k) for k in ("CUBES_STORED", "CUBES_WRONG", "CUBES_TRAP_WRONG", "CUBES_THING_MISMATCH",
                                                         "SHADOW_AGREE")})
    return {"schema": "helm.teach2.reading/1", "reader": READER, "practice_mock": practice, "verdict": verdict,
            "status_word": word, "reasons": reasons, "labels": list(C.LABELS_PRINTED),
            "licence_ceiling": "CUBES_EARNED_KEEP means only 'kept in the synthetic design for the next step'; not "
                               "VALIDATED, not LICENSED; every mechanism stays ENGINEERED-NOT-VALIDATED; the Eye's acting "
                               "stays NOT LICENSED",
            "limits": limits, "instrument_rows": I, "hard_gates": G, "marks": M, "arm_totals": arms_tot,
            "practice_view": practice_view,
            "per_unit": {f"{a}:{w}": {**per[(a, w)], **{k: v for k, v in mem[(a, w)].items() if not isinstance(v, list)},
                                      **({k: v for k, v in cub[(a, w)].items() if k not in ("WRONG_LIST",)}
                                         if (a, w) in cub else {})}
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
