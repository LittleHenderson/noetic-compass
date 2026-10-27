"""Clean the public corpus, fix speaker direction, and tag each turn into one of the 24 situations.

Inputs: data/public_corpus/public_turns.jsonl (114,678 pairs)
Output: data/public_corpus/public_turns_clean.jsonl and data/mouth_train_public.jsonl (trainer format)

Rules:
- drop crude/mocking replies and anything with a link, code or assistant boilerplate;
- drop OASST1 rows whose reply is a question back at the user (threading artefacts);
- DailyDialog has no speaker labels: use the question mark to decide who spoke first;
- EmpatheticDialogues: the situation is the user turn; emotion drives the tag;
- tag with keyword rules, balanced by a per-situation cap so one tag cannot swamp training.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN = HERE / "data" / "public_corpus" / "public_turns.jsonl"
OUT_CLEAN = HERE / "data" / "public_corpus" / "public_turns_clean.jsonl"
OUT_MOUTH = HERE / "data" / "mouth_train_public.jsonl"

CRUDE = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|asshole\w*|bastard\w*|piss\w*|crap\w*|dick\w*|vomit\w*|puke\w*|"
                   r"stupid|idiot\w*|moron\w*|shut up|screw you|go to hell)\b", re.I)
URL = re.compile(r"https?://|www\.", re.I)
CODE = re.compile(r"[{}<>`|]|;\s*$")
BOILER = ("as an ai", "language model", "chatgpt", "openai", "i cannot help with that")
QUESTION_BACK = re.compile(r"^(can you|could you|would you|will you|do you|did you|what|why|how|when|where|who)\b", re.I)

RULES = [
    ("GREETING", re.compile(r"\b(hello|hi|hey|morning|good evening|howdy|greetings)\b", re.I)),
    ("FAREWELL", re.compile(r"\b(bye|goodbye|see you|talk later|goodnight|good night|later)\b", re.I)),
    ("THANKS", re.compile(r"\b(thanks?|thank you|appreciate|cheers)\b", re.I)),
    ("APOLOGY", re.compile(r"\b(sorry|apolog|my fault|my mistake|excuse me)\b", re.I)),
    ("CONGRATS", re.compile(r"\b(congrat\w*|well done|great job|good news|we did it|got the job|passed)\b", re.I)),
    ("CONDOLENCE", re.compile(r"\b(died|passed away|funeral|loss of|condolence|grief|bereave)\b", re.I)),
    ("EMPATHY", re.compile(r"\b(tired|exhausted|sad|angry|upset|lonely|depress\w*|anxious|worried|stressed|"
                          r"rough day|awful|terrible|hate|hurt|scared|afraid|frustrat\w*)\b", re.I)),
    ("ENCOURAGE", re.compile(r"\b(can'?t do|give up|too hard|stuck|failing|not good enough|never finish)\b", re.I)),
    ("REASSURANCE", re.compile(r"\b(is it ruined|did i break|am i in trouble|lost the work|should i worry)\b", re.I)),
    ("PLAYFUL", re.compile(r"\b(joke|funny|laugh|pun|silly|humou?r)\b", re.I)),
    ("CLARIFY", re.compile(r"\b(what do you mean|which one|the other one|not sure what|explain that|"
                          r"can you clarify)\b", re.I)),
    ("CONFIRM", re.compile(r"\b(is that right|understood|got it|agreed|correct\?|right\?)\b", re.I)),
    ("CORRECT", re.compile(r"\b(no,? i meant|that'?s wrong|not what i|actually it|i said)\b", re.I)),
    ("HEDGE", re.compile(r"\b(are you sure|how sure|confident|certain\?|reliable)\b", re.I)),
    ("REFUSE_POLITE", re.compile(r"\b(make up|guess the|without checking|skip the|delete the|bypass)\b", re.I)),
    ("STATUS", re.compile(r"\b(where are we|status|how far|what'?s left|are we done|progress)\b", re.I)),
    ("PLAN", re.compile(r"\b(what should we do|next step|plan|where do we start|order of)\b", re.I)),
    ("WARN", re.compile(r"\b(risk|danger|what could go wrong|safe\?|careful)\b", re.I)),
    ("SUGGEST", re.compile(r"\b(recommend|suggest|what would you do|any ideas|options)\b", re.I)),
    ("EXPLAIN", re.compile(r"\b(why|how does|explain|reason|walk me through|what does that mean)\b", re.I)),
    ("ASK", re.compile(r"\?$")),
]

EMOTION_TAG = {"sad": "EMPATHY", "afraid": "EMPATHY", "angry": "EMPATHY", "anxious": "EMPATHY",
               "joyful": "SMALLTALK", "excited": "SMALLTALK", "happy": "SMALLTALK", "content": "SMALLTALK",
               "faithful": "SMALLTALK", "proud": "CONGRATS", "impressed": "CONGRATS", "grateful": "THANKS",
               "lonely": "EMPATHY", "devastated": "CONDOLENCE", "guilty": "APOLOGY", "embarrassed": "APOLOGY",
               "nostalgic": "SMALLTALK", "hopeful": "ENCOURAGE", "terrified": "EMPATHY", "disgusted": "EMPATHY",
               "surprised": "SMALLTALK", "anticipating": "PLAN", "prepared": "PLAN", "confident": "REASSURANCE",
               "ashamed": "APOLOGY", "caring": "EMPATHY", "apprehensive": "EMPATHY", "trusting": "SMALLTALK",
               "annoyed": "EMPATHY", "jealous": "EMPATHY", "furious": "EMPATHY", "disappointed": "EMPATHY",
               "sadness": "EMPATHY", "anger": "EMPATHY", "fear": "EMPATHY", "happiness": "SMALLTALK"}


def clean(t: str) -> str:
    return " ".join((t or "").split())


def ok_text(t: str) -> bool:
    if not t or CRUDE.search(t) or URL.search(t) or CODE.search(t):
        return False
    low = t.lower()
    if any(b in low for b in BOILER):
        return False
    if len(t) > 400:
        return False
    letters = sum(c.isalpha() or c.isspace() for c in t)
    if letters / max(1, len(t)) < 0.80:      # ASCII art, tables and symbol soup
        return False
    n = len(t.split())
    return 2 <= n <= 70


def tag_of(user: str, reply: str, emotion: str | None) -> str:
    if emotion:
        e = emotion.strip().lower()
        if e in EMOTION_TAG:
            return EMOTION_TAG[e]
    for name, rx in RULES:
        if rx.search(user):
            return name
    if reply.endswith("?"):
        return "CLARIFY"
    return "SMALLTALK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-per-tag", type=int, default=7000)
    a = ap.parse_args()
    rows = []
    for line in open(IN, encoding="utf-8"):
        r = json.loads(line)
        src = r.get("source")
        user, reply = clean(r.get("user")), clean(r.get("reply"))
        if not ok_text(user) or not ok_text(reply) or user.lower() == reply.lower():
            continue
        if src == "oasst1" and QUESTION_BACK.match(reply):
            continue                      # threading artefact: the "reply" is another question
        if src == "dailydialog":
            if user.endswith("?"):
                pass
            elif reply.endswith("?"):
                user, reply = reply, user  # the question is the user turn
            else:
                continue                  # no signal about direction: skip rather than guess
        tag = tag_of(user, reply, r.get("emotion"))
        rows.append({"situation": tag, "user": user, "reply": reply, "context": r.get("context") or [],
                     "source": src, "licence": r.get("licence"), "synthetic": bool(r.get("synthetic"))})
    by_tag = Counter(r["situation"] for r in rows)
    kept, seen = [], Counter()
    for r in rows:
        if kept and seen[r["situation"]] >= a.cap_per_tag:
            continue
        kept.append(r)
        seen[r["situation"]] += 1
    OUT_CLEAN.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    tone = [["^1", "|A"], ["^1", "|f"]]
    mouth = [{"situation": r["situation"], "tone": tone[i % 2], "input_text": r["user"], "target": r["reply"],
              "style": None, "context": r["context"][-2:] if r["context"] else None,
              "source": r["source"]} for i, r in enumerate(kept)]
    OUT_MOUTH.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in mouth), encoding="utf-8")
    stats = {"input": sum(1 for _ in open(IN, encoding="utf-8")), "kept": len(kept),
             "by_source": dict(Counter(r["source"] for r in kept)),
             "by_tag": dict(Counter(r["situation"] for r in kept)),
             "dropped_crude_or_bad": None, "mouth_file": str(OUT_MOUTH)}
    (HERE / "data" / "public_corpus" / "public_turns_clean_stats.json").write_text(json.dumps(stats, indent=1),
                                                                                 encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("kept", "by_source", "by_tag")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
