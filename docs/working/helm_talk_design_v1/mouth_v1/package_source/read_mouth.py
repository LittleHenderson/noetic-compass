"""read_mouth.py -- the frozen reader of MOUTH TRAIN (A-TALK-4 W7, A-TALK-5 F1/F2). Standard library only.

Two steps. `read_host` runs on the GPU host at the end of run_mouth.py: the instrument rows, the hard gate (no new
fact), the ear's own gates (CUBE TRAIN's frozen rule on the new weights), the fallback mark (at most 1 in 1,000, over at
least 1,000 exam replies), the round trip (>= 95 %), VARIED (every one of the varied inputs gets >= 3 distinct wordings
over 5 turns, among the lines the guard passed). `read_final` runs on the laptop after the AI raters (SOUNDS-HUMAN: blind
raters of three families prefer the mouth to the template on >= 60 % of pairs; TONE reported) and prints the word in
the frozen order: INCONCLUSIVE > MOUTH_HARMED > MOUTH_NO_GAIN > MOUTH_EARNED_KEEP.
Labels printed with every word: SYNTHETIC_ONLY, LLM_WRITTEN_ONLY, AI_RATED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

LABELS = ("SYNTHETIC_ONLY", "LLM_WRITTEN_ONLY", "AI_RATED")


def read_host(inst: Dict[str, bool], audits: Dict[str, List[str]], body: Optional[Dict[str, Any]],
              fz: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"schema": "mouth-train.host-reading/1", "instrument": dict(inst), "audits": audits,
                           "labels": list(LABELS)}
    if body is None:
        out.update(host_word="INCONCLUSIVE", why="the run stopped before the exam")
        return out
    recs = body["records"]
    exam = [r for r in recs if r["split"] == "EXAM"]
    n = len(exam)
    fallbacks = sum(1 for r in exam if not r["guard_ok"])
    new_words = sum(1 for r in recs if r.get("new_word"))
    facts = [r for r in exam if r["situation"] in ("ANSWER", "SAYBACK", "ASK") and r["guard_ok"]]
    rt_ok = sum(1 for r in facts if r.get("round_trip"))
    varied: Dict[str, set] = {}
    for r in recs:
        if r["split"] == "VARIED" and r["guard_ok"]:
            varied.setdefault(r["id"].rsplit("#", 1)[0], set()).add(r["text"])
    want_varied = fz["varied_inputs"]
    varied_ok = sum(1 for k in varied if len(varied[k]) >= 3)
    ear = body["ear"]
    inst = dict(inst, I6_exam_at_least_1000=n >= fz["exam_min_replies"])
    out["instrument"] = inst
    marks = {
        "G-NO-NEW-FACT": {"holds": new_words == 0, "lines_with_a_word_outside_the_lock": new_words},
        "EAR-GATES": {"holds": all(ear["gates"].values()), "gates": ear["gates"], "vote": ear["vote"],
                      "keep_old": ear["keep_old"]},
        "F-FALLBACK": {"holds": n >= fz["exam_min_replies"] and fallbacks * fz["fallback_per"] <= n * fz["fallback_max"],
                       "fallbacks": fallbacks, "replies": n, "rate": round(fallbacks / max(1, n), 6),
                       "mark": "at most %d in %d" % (fz["fallback_max"], fz["fallback_per"]),
                       "mostly_template": fallbacks > n / 2,
                       "why_counts": _count([r["guard_why"] for r in exam if not r["guard_ok"]]),
                       "other_copies_reported": body.get("other_copy_fallbacks")},
        "G-ROUNDTRIP": {"holds": len(facts) > 0 and rt_ok >= fz["roundtrip_min"] * len(facts), "same_fact": rt_ok,
                        "fact_replies": len(facts)},
        "VARIED": {"holds": varied_ok == want_varied, "inputs_with_3_or_more_wordings": varied_ok, "of": want_varied},
    }
    out["marks"] = marks
    out["finals_sha256"] = body["finals_sha256"]
    out["dev_reported"] = {"replies": sum(1 for r in recs if r["split"] == "DEV"),
                           "guard_ok": sum(1 for r in recs if r["split"] == "DEV" and r["guard_ok"])}
    if not all(inst.values()):
        word = "INCONCLUSIVE"
    elif not marks["G-NO-NEW-FACT"]["holds"] or not marks["EAR-GATES"]["holds"]:
        word = "MOUTH_HARMED"
    elif not all(marks[k]["holds"] for k in ("F-FALLBACK", "G-ROUNDTRIP", "VARIED")):
        word = "MOUTH_NO_GAIN"
    else:
        word = "AWAITING_RATERS"
    out["host_word"] = word
    return out


def _count(xs):
    out: Dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


def read_final(host: Dict[str, Any], ratings: List[Dict[str, Any]], fz: Dict[str, Any]) -> Dict[str, Any]:
    """`ratings`: one row per (pair, rater family): {"pair": id, "family": f, "prefers": "MOUTH"|"TEMPLATE"}; the
    pair's verdict is the majority of the three families (blind: the raters never see which line is which)."""
    by: Dict[str, List[str]] = {}
    for r in ratings:
        by.setdefault(r["pair"], []).append(r["prefers"])
    pairs = [v for v in by.values() if len(v) >= 3]
    mouth_wins = sum(1 for v in pairs if v.count("MOUTH") > len(v) / 2)
    sh = {"holds": len(pairs) >= fz["rater_min_pairs"] and mouth_wins >= fz["sounds_human_min"] * len(pairs),
          "mouth_preferred": mouth_wins, "pairs": len(pairs)}
    out = dict(host, schema="mouth-train.reading/1")
    out["marks"] = dict(host.get("marks") or {}, **{"SOUNDS-HUMAN": sh})
    word = host["host_word"]
    if word == "AWAITING_RATERS":
        word = "MOUTH_EARNED_KEEP" if sh["holds"] else "MOUTH_NO_GAIN"
    out["status_word"] = word
    return out
