"""mouth_llm.py -- the mouth's AI-written lessons (A-TALK-4 W6). Exam side.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Three AI model families (Anthropic's Claude through helper agents, OpenAI's Codex, Google's Gemini; tools the owner
already pays for or free tiers: 0 USD) do three jobs:
  persons  each family writes person lines for the line situations (off-topic remarks, small talk, questions about
           HELM, questions about the world);
  write    each family writes HELM's reply to EVERY input (so each input has up to three different wordings);
  key      each reply is checked by the two OTHER families: no fact beyond the input, no opinion, fits the situation,
           and for a fact situation, states the same fact.
A reply becomes a lesson only when the rule check (mouth_lessons.rule_check) and both keys pass. The owner writes
nothing. DeepSeek is not used unless the owner OKs its cost (A-TALK-4 W6).

    python mouth_llm.py persons | write | key | assemble        (outputs in mouth_v1/llm/)
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mouth_lessons as ML  # noqa: E402  (puts cube_train/ and the repository root on the path)
import llm_ct  # noqa: E402

OUT = os.path.join(HERE, "llm")
llm_ct.OUT = OUT                                    # the reused runner writes prompts and replies here
llm_ct.GEMINI_MODEL = "gemini-2.5-flash"            # gemini-3-flash-preview hit its daily free quota (HTTP 429) on
                                                    # 2026-10-22; 2.5-flash still answered; same family, model recorded
FAMILIES = ("anthropic", "openai", "google", "deepseek")    # deepseek: the owner's words "IF YOU NEED USE DEEPSEEK AS
                                                            # WELL" (2026-10-22)
SMALL_BATCH_FAMILIES = ("deepseek",)                        # its API answers at most 8,192 tokens: half-size batches
PERSON_COUNTS = {"OFF": 100, "SMALL": 30, "SELF": 20, "WORLD": 20}
FACT_INPUTS = 600
WRITE_BATCH = 190
KEY_BATCH = 380
HELM_FACTS = ("HELM is a computer program, not a person. In a chat it keeps what the person tells it: the conversation, "
              "up to twenty things the person says about themselves, and the kitchen amounts the person gives. It cannot "
              "look anything up and knows only what it was told in the chat. It has no opinions of its own.")

BRIEF_PERSONS = """You are writing lines that one person might type to a chat assistant. Write natural, varied, everyday
lines, the way real people type (some casual, some with small typos are fine, mostly correct). Return ONLY a JSON list of
objects {"situation": "<OFF|SMALL|SELF|WORLD>", "text": "<the line>"}.
- OFF: the person tells the assistant something about their life, their day, people they know, places, news, hobbies.
  A statement, not a question. Not about cooking, food, recipes or ingredients. 6 to 25 words. Vary the topics widely.
- SMALL: greetings, thanks, check-ins, short pauses ("hey", "thanks a lot", "how's your day", "ok cool"). 1 to 6 words.
- SELF: a question about the assistant itself (what it is, what it can do, whether it remembers, whether it is a person).
- WORLD: a question about the outside world that nobody told the assistant (sports results, capitals, weather tomorrow,
  opening hours, prices). Not about cooking.
Write exactly the counts asked for. No numbering, no extra text."""

BRIEF_WRITE = """You are writing the replies of HELM, a chat assistant. """ + HELM_FACTS + """
For each item, write ONE reply HELM could say. Sound like a calm, friendly person talking, not a form. Vary your wording
from item to item; do not reuse the same sentence shape again and again. Return ONLY a JSON list of {"id": "<id>",
"text": "<reply>"}.
HARD RULES (a reply that breaks one is thrown away):
1. Never add a fact. Every name, number and month in your reply must appear in the item's content. No new places,
   people, dates, numbers or claims about the world.
2. Opinions, feelings and reactions are welcome, as a person would have them ("Love that!", "Oof, that's rough",
   "I like that idea"). But no advice: never "you should", "you need to", "you must".
3. One to three short sentences. No lists, no headings, no symbols such as ^ or |.
4. Never mention recipes, ingredients, stock, inventory or food unless the item's content mentions them.
5. Follow the situation:
   - ANSWER: the person asked about something they told HELM earlier; tell it back plainly with the exact value
     (the content gives the fact). No question.
   - SAYBACK: HELM repeats the fact it just heard so the person can check it, with the exact value. No question.
   - ASK: HELM asks whether the fact is still true. Exactly ONE question, ending with "?", with the exact value.
   - SMALL: a short friendly reply to the person's small talk. Nothing else.
   - SELF: answer the person's question about HELM truthfully, using only the facts about HELM above.
   - OFF: react briefly to what the person said (no opinion, no facts), then ask exactly ONE question about it, using
     the person's own words for any name or place.
   - WORLD: say plainly that HELM does not know, because nobody has told it. No guessing.
6. "register" A means plain and matter-of-fact; "register" f means warm."""

BRIEF_KEY = """You are checking replies written for HELM, a chat assistant. """ + HELM_FACTS + """
For each item you get the situation, the content HELM was given, and the reply. Decide PASS or FAIL. Return ONLY a JSON
list of {"id": "<id>", "pass": true|false, "why": "<short reason when false>"}.
FAIL when ANY of these is true:
1. The reply states a fact, name, number, month, place or claim that is not in the content.
2. The reply gives advice ("you should", "you need to", "you must"). Opinions, feelings and reactions are ALLOWED
   and are never a reason to fail.
3. The reply does not fit the situation: ANSWER/SAYBACK must state the content's fact with its exact value and ask
   nothing; ASK must ask exactly one question about whether that fact is still true; SMALL must be a short friendly
   reply; SELF must be truthful about HELM; OFF must react without opinion and ask exactly one question about what the
   person said; WORLD must say HELM does not know.
4. For ANSWER, SAYBACK, ASK: the reply's fact differs from the content's fact in any way (thing, value, month, place).
Be strict. Judge each reply on its own."""


def _save(name: str, obj: Any) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)


def _load(name: str, default: Any = None) -> Any:
    p = os.path.join(OUT, name)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else default


# ----------------------------------------------------------------------------------------------- persons
def stage_persons(families: Tuple[str, ...] = FAMILIES) -> None:
    for fam in families:
        ask = "\n".join(f"- {k}: {n} lines" for k, n in PERSON_COUNTS.items())
        text, meta = llm_ct.run_cli(fam, BRIEF_PERSONS + "\n\nCOUNTS:\n" + ask, f"persons-{fam}")
        lines = []
        for item in llm_ct.parse_reply(text) or []:
            if isinstance(item, dict) and item.get("situation") in ML.LINE_SITUATIONS and isinstance(item.get("text"), str):
                lines.append({"situation": item["situation"], "text": item["text"].strip()})
        _save(f"persons_{fam}.json", {"family": fam, "lines": lines, "call": meta})
        print(fam, meta.get("status") or meta.get("returncode"), len(lines), flush=True)


EXAM_PERSON_COUNTS = {"OFF": 60, "SMALL": 15, "SELF": 10, "WORLD": 15}


def stage_persons_exam(families: Tuple[str, ...] = FAMILIES) -> None:
    """A-TALK-5 F2: a second, held-out round of person lines for the mouth's exam; never in the lessons."""
    for fam in families:
        ask = "\n".join(f"- {k}: {n} lines" for k, n in EXAM_PERSON_COUNTS.items())
        text, meta = llm_ct.run_cli(fam, BRIEF_PERSONS + "\n\nCOUNTS:\n" + ask + "\n\nUse topics and wordings different "
                                    "from any list you may have written before.", f"persons-exam-{fam}")
        lines = [{"situation": it["situation"], "text": it["text"].strip()} for it in llm_ct.parse_reply(text) or []
                 if isinstance(it, dict) and it.get("situation") in ML.LINE_SITUATIONS and isinstance(it.get("text"), str)]
        _save(f"persons_exam_{fam}.json", {"family": fam, "lines": lines, "call": meta})
        print(fam, meta.get("status") or meta.get("returncode"), len(lines), flush=True)


def _person_ok(sit: str, text: str) -> bool:
    if not text or len(text.split()) > 30 or ML.ht.RECIPE_SPEAK_RX.search(text) or "^" in text:
        return False
    if sit == "OFF":
        return "?" not in text and ML.ht.classify(text) == "OFF"
    if sit == "SMALL":
        return len(text.split()) <= 6
    return "?" in text or ML.ht.is_question(text)


def inputs() -> List[Dict[str, Any]]:
    """Every input: FACT_INPUTS readings + every family's person lines that pass the rule (deduplicated)."""
    out = ML.fact_inputs(FACT_INPUTS)
    seen = set()
    for fam in FAMILIES:
        doc = _load(f"persons_{fam}.json", {"lines": []})
        for k, ln in enumerate(doc["lines"]):
            t = ln["text"]
            if t.lower() in seen or not _person_ok(ln["situation"], t):
                continue
            seen.add(t.lower())
            out.append(dict(ML.line_input(ln["situation"], t, f"person:{fam}:{k}"), person_family=fam))
    for i, x in enumerate(out):
        x["id"] = f"m{i:05d}"
    return out


def writer_view(x: Dict[str, Any]) -> Dict[str, Any]:
    v = {"id": x["id"], "situation": x["situation"], "register": x["tone"][1].lstrip("|")}
    if x["situation"] in ML.FACT_SITUATIONS:
        r = x["reading"]
        v["content"] = {"thing": r["thing"], "slot_words": r["slot"], "value": r["value"], "replaces": r.get("replaces")}
    else:
        v["content"] = {"person_said": x["person_line"]}
    return v


# ----------------------------------------------------------------------------------------------- write
def stage_write(families: Tuple[str, ...] = FAMILIES) -> None:
    xs = inputs()
    _save("inputs.json", xs)
    for fam in families:
        prev = _load(f"written_{fam}.json") or {}
        written: Dict[str, str] = dict(prev.get("lines", {}))
        calls = list(prev.get("calls", []))
        # rewrites answered after the run (file-mode helpers) replace the refused lines they answer
        rdir = os.path.join(OUT, "replies")
        for name in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
            if name.startswith(f"rewrite-{fam}-") and name.endswith(".txt"):
                llm_ct._take(open(os.path.join(rdir, name), encoding="utf-8").read(), written)
        size = WRITE_BATCH // 2 if fam in SMALL_BATCH_FAMILIES else WRITE_BATCH
        for b in range(0, len(xs), size):
            batch = [x for x in xs[b:b + size] if x["id"] not in written]
            if not batch:
                continue
            tag = f"write-{fam}-{b // size}"
            text, meta = llm_ct.run_cli(fam, BRIEF_WRITE + "\n\nITEMS:\n" + json.dumps([writer_view(x) for x in batch],
                                                                                      ensure_ascii=False), tag)
            calls.append(meta)
            llm_ct._take(text, written)
            if meta.get("status") == "pending":
                continue
            redo = [dict(writer_view(x), refused_because=ML.rule_check(x, written.get(x["id"], ""))[1],
                         your_reply=written.get(x["id"], "")) for x in batch if not ML.rule_check(x, written.get(x["id"], ""))[0]]
            if redo:
                text, meta = llm_ct.run_cli(fam, BRIEF_WRITE + "\n\nREWRITE these items (each was refused for the reason "
                                            "given):\n" + json.dumps(redo, ensure_ascii=False), "re" + tag)
                calls.append(meta)
                llm_ct._take(text, written)
            print(fam, tag, "written", sum(1 for x in batch if x["id"] in written), "rule-ok",
                  sum(1 for x in batch if ML.rule_check(x, written.get(x["id"], ""))[0]), flush=True)
        _save(f"written_{fam}.json", {"family": fam, "lines": written, "calls": calls})


# ----------------------------------------------------------------------------------------------- key
def stage_key(keyers: Tuple[str, ...] = FAMILIES) -> None:
    xs = {x["id"]: x for x in _load("inputs.json")}
    for keyer in keyers:
        keys: Dict[str, Dict[str, Any]] = (_load(f"keys_{keyer}.json") or {}).get("keys", {})
        items = []
        for fam in FAMILIES:
            if fam == keyer:
                continue
            for iid, line in (_load(f"written_{fam}.json") or {"lines": {}})["lines"].items():
                kid = f"{fam}:{iid}"
                if kid in keys or iid not in xs or not ML.rule_check(xs[iid], line)[0]:
                    continue
                v = writer_view(xs[iid])
                items.append({"id": kid, "situation": v["situation"], "content": v["content"], "reply": line})
        calls = list((_load(f"keys_{keyer}.json") or {}).get("calls", []))
        size = KEY_BATCH // 2 if keyer in SMALL_BATCH_FAMILIES else KEY_BATCH
        start = len([c for c in calls if str(c.get("tag", "")).startswith(f"key-{keyer}-")])
        for b in range(0, len(items), size):
            batch = items[b:b + size]
            tag = f"key-{keyer}-{start + b // size}"
            text, meta = llm_ct.run_cli(keyer, BRIEF_KEY + "\n\nITEMS:\n" + json.dumps(batch, ensure_ascii=False), tag)
            calls.append(meta)
            for it in llm_ct.parse_reply(text) or []:
                if isinstance(it, dict) and it.get("id") and isinstance(it.get("pass"), bool):
                    keys[it["id"]] = {"pass": it["pass"], "why": it.get("why")}
            print(keyer, tag, "keyed", sum(1 for x in batch if x["id"] in keys), flush=True)
        _save(f"keys_{keyer}.json", {"family": keyer, "keys": keys, "calls": calls})


# ----------------------------------------------------------------------------------------------- assemble
def stage_assemble() -> Dict[str, Any]:
    xs = {x["id"]: x for x in _load("inputs.json")}
    keys = {k: (_load(f"keys_{k}.json") or {"keys": {}})["keys"] for k in FAMILIES}
    rows, counts = [], {"written": 0, "rule_ok": 0, "kept": 0, "key_fail": 0, "key_missing": 0}
    for fam in FAMILIES:
        for iid, line in (_load(f"written_{fam}.json") or {"lines": {}})["lines"].items():
            x = xs.get(iid)
            if x is None:
                continue
            counts["written"] += 1
            if not ML.rule_check(x, line)[0]:
                continue
            counts["rule_ok"] += 1
            ks = [keys[k][f"{fam}:{iid}"] for k in FAMILIES if k != fam and f"{fam}:{iid}" in keys[k]]
            if len(ks) < 2:                     # at least two other families must have keyed it; none may fail it
                counts["key_missing"] += 1
                continue
            if not all(k["pass"] for k in ks):
                counts["key_fail"] += 1
                continue
            counts["kept"] += 1
            rows.append({"input_key": x["input_key"], "situation": x["situation"], "tone": list(x["tone"]),
                         "input_text": x["input_text"], "target": line, "source": "LLM_WRITTEN", "writer": fam,
                         "keyed_by": [k for k in FAMILIES if k != fam and f"{fam}:{iid}" in keys[k]], "reading": x.get("reading"),
                         "person_line": x.get("person_line")})
    for x in xs.values():
        t = ML.template_line(x)
        if t:
            rows.append({"input_key": x["input_key"], "situation": x["situation"], "tone": list(x["tone"]),
                         "input_text": x["input_text"], "target": t, "source": "TEMPLATE", "writer": "rule",
                         "reading": x.get("reading"), "person_line": x.get("person_line")})
    rows = ML.cap_templates(rows)
    train, dev = ML.split(rows)
    for name, part in (("rows_mouth_train.jsonl", train), ("rows_mouth_dev.jsonl", dev)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
            for r in part:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    rec = {"counts": counts, "train": len(train), "dev": len(dev),
           "by_situation": {s: sum(1 for r in rows if r["situation"] == s and r["source"] == "LLM_WRITTEN") for s in ML.SITUATIONS},
           "templates": sum(1 for r in rows if r["source"] == "TEMPLATE"), "inputs": len(xs)}
    _save("MOUTH_LESSONS_RECORD.json", rec)
    print(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    fams = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else FAMILIES
    stage = {"persons": stage_persons, "persons_exam": stage_persons_exam, "write": stage_write, "key": stage_key,
             "assemble": stage_assemble}[sys.argv[1]]
    stage() if sys.argv[1] == "assemble" else stage(fams)
