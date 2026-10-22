"""rate_mouth.py -- SOUNDS-HUMAN, the AI raters of MOUTH TRAIN (A-TALK-4 W7, A-TALK-6 G8). Laptop, after the download.
Written before any MOUTH TRAIN result existed (2026-10-22, while job c59 was training).

    python -X utf8 -B rate_mouth.py pairs <MOUTH_EXAM_OUTPUTS.json> <MOUTH_HOST_READING.json>
    python -X utf8 -B rate_mouth.py rate [families]
    python -X utf8 -B rate_mouth.py read <MOUTH_HOST_READING.json>

Pairs: every EXAM reply of the speaker (A4-s1) that passed the guard, beside today's template line for the same input.
A pair whose two lines are the same text (ignoring case and spaces) is left out and counted, because no rater can prefer
one of two equal lines. Each pair is shown as line A and line B in an order fixed by sha256(pair id); the rater is not
told which line is HELM's mouth and which is the template (blind). Raters: anthropic, openai, deepseek (Google has no
quota, A-TALK-6 G8). A pair is the mouth's win when at least two of the three families prefer the mouth's line; the frozen
reader read_mouth.read_final turns the rows into SOUNDS-HUMAN (>= 60 % of >= 300 pairs) and the final word.
Labels: AI_RATED, SYNTHETIC_ONLY, LLM_WRITTEN_ONLY.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "package_source"))
import mouth_lessons as ML  # noqa: E402
import llm_ct  # noqa: E402

OUT = os.path.join(HERE, "rate")
llm_ct.OUT = OUT
RATERS = ("anthropic", "openai", "deepseek")
BATCH = {"anthropic": 150, "openai": 150, "deepseek": 75}

BRIEF = """You are judging two replies a chat assistant could give. For each item you get what the person said or the fact
the assistant was given, and two replies, A and B. Both replies are meant to say the same thing. Decide which one sounds
more like a natural, friendly person talking (clear, warm, not robotic, not stiff), while still being correct for the
situation. You must choose A or B for every item. Return ONLY a JSON list of {"id": "<id>", "better": "A"|"B"}."""


def _save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)


def _load(name, default=None):
    p = os.path.join(OUT, name)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else default


def _norm(s):
    return " ".join((s or "").lower().split())


def pairs(outputs_path, reading_path):
    exam = {json.loads(l)["input_key"]: json.loads(l)
            for l in open(os.path.join(HERE, "package_source", "data", "mouth_exam.jsonl"), encoding="utf-8") if l.strip()}
    recs = json.load(open(outputs_path, encoding="utf-8"))
    recs = recs["records"] if isinstance(recs, dict) else recs
    rows, same = [], 0
    for r in recs:
        if r["split"] != "EXAM" or not r["guard_ok"]:
            continue
        x = exam[r["id"].rsplit("#", 1)[0]]
        t = ML.template_line(x)
        if not t:
            continue
        if _norm(t) == _norm(r["text"]):
            same += 1
            continue
        mouth_is_a = int(hashlib.sha256(r["id"].encode()).hexdigest(), 16) % 2 == 0
        content = x["input_text"] if x["situation"] not in ML.FACT_SITUATIONS else (
            "fact: " + json.dumps(x["reading"], sort_keys=True))
        rows.append({"id": r["id"], "situation": x["situation"], "content": content if not x.get("person_line") else x["person_line"],
                     "A": r["text"] if mouth_is_a else t, "B": t if mouth_is_a else r["text"], "mouth": "A" if mouth_is_a else "B"})
    _save("PAIRS.json", {"pairs": rows, "left_out_same_text": same,
                         "host_reading_sha256": hashlib.sha256(open(reading_path, "rb").read()).hexdigest()})
    print(json.dumps({"pairs": len(rows), "left_out_same_text": same}))


def rate(fams):
    rows = _load("PAIRS.json")["pairs"]
    for fam in fams:
        got = (_load(f"ratings_{fam}.json") or {}).get("ratings", {})
        items = [{"id": r["id"], "situation": r["situation"], "content": r["content"], "A": r["A"], "B": r["B"]}
                 for r in rows if r["id"] not in got]
        for b in range(0, len(items), BATCH[fam]):
            batch = items[b:b + BATCH[fam]]
            text, meta = llm_ct.run_cli(fam, BRIEF + "\n\nITEMS:\n" + json.dumps(batch, ensure_ascii=False), f"rate-{fam}-{b // BATCH[fam]}")
            for it in llm_ct.parse_reply(text) or []:
                if isinstance(it, dict) and it.get("better") in ("A", "B"):
                    got[it["id"]] = it["better"]
            print(fam, b // BATCH[fam], "rated", sum(1 for x in batch if x["id"] in got), "of", len(batch), flush=True)
        _save(f"ratings_{fam}.json", {"family": fam, "ratings": got})


def read(reading_path):
    from read_mouth import read_final
    fz = json.load(open(os.path.join(HERE, "package_source", "FROZEN_MOUTH.json"), encoding="utf-8"))
    host = json.load(open(reading_path, encoding="utf-8"))
    rows = {r["id"]: r for r in _load("PAIRS.json")["pairs"]}
    ratings = []
    for fam in RATERS:
        for pid, better in ((_load(f"ratings_{fam}.json") or {}).get("ratings", {})).items():
            if pid in rows:
                ratings.append({"pair": pid, "family": fam, "prefers": "MOUTH" if better == rows[pid]["mouth"] else "TEMPLATE"})
    final = read_final(host, ratings, fz)
    final["raters"] = list(RATERS)
    final["left_out_same_text"] = _load("PAIRS.json")["left_out_same_text"]
    _save("MOUTH_TRAIN_READING.json", final)
    print(json.dumps({"status_word": final["status_word"], "SOUNDS-HUMAN": final["marks"]["SOUNDS-HUMAN"]}, indent=1))


if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "pairs":
        pairs(sys.argv[2], sys.argv[3])
    elif stage == "rate":
        rate(tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else RATERS)
    else:
        read(sys.argv[2])
