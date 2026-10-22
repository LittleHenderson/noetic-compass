"""corpus_v2.py -- mouth v2's corpus and lessons (A-TALK-7 H4, A-TALK-8 I1), built on mouth_llm.py's write / key stages.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
The owner asked for a corpus of everyday vocabulary at three reading levels (5th grade, 10th grade, college), the
working words of 30 professions, formal and informal speech, story form, and conversation styles (barbershop, intimate,
curious, jovial ...). This file makes it, in stages, all AI-written and all checked:
  vocab    one family writes each word list; a second family keeps only the words that fit (prompts for the writers)
  persons  person lines (off-topic, small talk, about HELM, I-don't-know) for a fixed grid of style x level x
           profession x form; a second, held-out round for the exam
  write    every NEW input gets HELM's reply from anthropic, openai and deepseek, in the input's style and level
  key      every new reply is checked by the two other families (mouth_llm.stage_key)
  assemble the lessons: rule check (incl. the sense check), two other-family keys, none failing; up to 3 per input
v1's 1,083 inputs keep their ids (m00000..m01082) and their written lines and keys (copied from mouth_v1/llm); they are
styled "plain" (register A) or "warm" (register f) at level grade10, as v1's writer brief described them.

    python corpus_v2.py vocab | persons | persons_exam | write [families] | key [families] | assemble
CLAIM STATUS: ENGINEERED-NOT-VALIDATED. SYNTHETIC_ONLY, LLM_WRITTEN_ONLY.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import sys
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mouth_llm as MM  # noqa: E402
import mouth_lessons as ML  # noqa: E402

llm_ct = MM.llm_ct
OUT = MM.OUT                                        # mouth_v2/llm
V1 = os.path.join(os.path.dirname(HERE), "mouth_v1", "llm")
NEW_FAMILIES = ("anthropic", "openai", "deepseek")  # google: no free quota left today (A-TALK-6 G2); its v1 lines stay
PERSON_WRITERS = ("openai", "deepseek")
PERSON_COUNTS = {"OFF": 2000, "SMALL": 500, "SELF": 400, "WORLD": 400}
EXAM_PERSON_COUNTS = {"OFF": 300, "SMALL": 60, "SELF": 60, "WORLD": 60}
NEW_FACTS = 600
NEW_FACT_INDEX = 60_000
STORY_SHARE = 0.2
SPEC_BATCH = 60
KEEP_PER_INPUT = 3

STYLE_TEXT = {
    "plain": "plain and matter-of-fact",
    "warm": "warm and kind",
    "formal": "formal and polite, complete sentences",
    "casual": "relaxed and informal, contractions welcome",
    "barbershop": "easy barbershop banter: relaxed, friendly, a little playful, like regulars chatting",
    "intimate": "gentle and close, like talking quietly with someone you trust",
    "curious": "curious and interested, eager to hear more",
    "jovial": "cheerful and good-humoured",
    "storyteller": "a little narrative, like someone who enjoys telling and hearing stories",
    "professional": "clear and businesslike, like a colleague at work",
}
LEVEL_TEXT = {"grade5": "simple words a 5th grader knows", "grade10": "everyday words a 10th grader uses",
              "college": "richer, more precise words a college graduate uses"}

BRIEF_VOCAB = """Write a word list. Return ONLY a JSON list of lowercase single words (no phrases, no names of people or
places, no numbers, no months, nothing about food or cooking). {what}"""
BRIEF_VOCAB_CHECK = """Here is a word list meant to be: {what}. Return ONLY a JSON list of the words from it that truly
fit that description (lowercase, exactly as given). Leave out any word that does not fit, is a name, a number, a month,
or is about food or cooking."""

BRIEF_PERSONS2 = """You are writing lines one person might type to a chat assistant. For each spec, write ONE line that
fits it. Return ONLY a JSON list of {"id": "<id>", "text": "<the line>"}.
Situations:
- OFF: the person tells the assistant something about their life, work, day, people, places, news or hobbies. A
  statement, not a question. Not about cooking, food, recipes or ingredients. form "line": 6 to 25 words. form "story":
  a short story of 2 to 4 sentences, at most 60 words.
- SMALL: greetings, thanks, check-ins, short pauses. 1 to 6 words.
- SELF: a question about the assistant itself (what it is, what it can do, whether it remembers, whether it is a person).
- WORLD: a question about the outside world nobody told the assistant (results, capitals, weather, opening hours, prices).
  Not about cooking.
Each spec gives a "style" (how the person talks), a "level" (their vocabulary) and sometimes a "profession" (the person
works as one; let their work show naturally in OFF lines, using some of its words). "words" are optional hints you may
use. Never use these made-up names: Oxley, Carrow, Bramlow and similar invented town or person names. Vary topics and
wording widely; no two lines alike."""

BRIEF_WRITE2 = MM.BRIEF_WRITE + """
7. Each item also has a "style" and a "level". Write in that style and with that vocabulary level, while keeping every
   rule above (style shows in word choice and warmth, never in an opinion or a new fact). Use only everyday words and
   the words in the item's content; for OFF, ask ONE short question that uses the person's own word.
Styles: """ + "; ".join(f"{k} = {v}" for k, v in STYLE_TEXT.items()) + """.
Levels: """ + "; ".join(f"{k} = {v}" for k, v in LEVEL_TEXT.items()) + "."


def _save(name, obj):
    MM._save(name, obj)


def _load(name, default=None):
    return MM._load(name, default)


# ----------------------------------------------------------------------------------------------- vocab
VOCAB_SPECS = ([("level-" + lv, "about 500 common everyday English words a person at this level uses in conversation: "
                 + LEVEL_TEXT[lv]) for lv in ML.LEVELS] +
               [("profession-" + p, f"about 25 words a {p} uses at work every day (tools, tasks, places, people)")
                for p in ML.PROFESSIONS] +
               [("level-" + lv + "-more", "about 1,500 MORE common everyday English words a person at this level uses in "
                 "conversation, beyond the most basic ones (verbs, nouns, adjectives, adverbs of daily life: home, family, "
                 "work, school, weather, health, travel, feelings, hobbies, time): " + LEVEL_TEXT[lv]) for lv in ML.LEVELS] +
               [("irregular-forms", "the past tense and past participle forms of the 200 most common irregular English "
                 "verbs (for example went, gone, heard, gave, given, kept, took, taken), as single words")])


def vocab_lists() -> Dict[str, List[str]]:
    """Every finished word list (one file per list in llm/vocab_parts/, so lists can be made in parallel)."""
    d = os.path.join(OUT, "vocab_parts")
    out = dict((_load("vocab.json") or {}).get("lists", {}))
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        out[n[:-5]] = json.load(open(os.path.join(d, n), encoding="utf-8"))["words"]
    return out


def stage_vocab(part: str = "0/1") -> None:
    """part "k/n": this process makes lists k, k+n, k+2n, ... (several processes may run at once)."""
    k0, n = (int(x) for x in part.split("/"))
    done = vocab_lists()
    os.makedirs(os.path.join(OUT, "vocab_parts"), exist_ok=True)
    for k, (name, what) in enumerate(VOCAB_SPECS):
        if k % n != k0 or name in done:
            continue
        writer, checker = ("deepseek", "openai") if k % 2 == 0 else ("openai", "deepseek")
        text, _ = llm_ct.run_cli(writer, BRIEF_VOCAB.format(what=what), f"vocab-{name}")
        words = sorted({w.strip().lower() for w in llm_ct.parse_reply(text) or [] if isinstance(w, str) and w.strip().isalpha()})
        text, _ = llm_ct.run_cli(checker, BRIEF_VOCAB_CHECK.format(what=what) + "\n\nWORDS:\n" + json.dumps(words),
                                 f"vocab-check-{name}")
        ok = {w.strip().lower() for w in llm_ct.parse_reply(text) or [] if isinstance(w, str)}
        banned = ML.NAMES | ML.NUMBERS | ML.MONTHS
        kept = sorted(w for w in words if w in ok and w not in banned)
        _save(os.path.join("vocab_parts", name + ".json"), {"name": name, "what": what, "writer": writer,
                                                            "checker": checker, "written": len(words), "words": kept})
        print(name, writer, len(words), "->", checker, "kept", len(kept), flush=True)


# ----------------------------------------------------------------------------------------------- persons
def _specs(counts: Dict[str, int], prefix: str, seed: str) -> List[Dict[str, Any]]:
    """A fixed grid: styles and levels dealt in turn; about half carry a profession; a fifth of OFF lines are stories."""
    rnd = random.Random(seed)
    out = []
    for sit, n in counts.items():
        for i in range(n):
            spec = {"id": f"{prefix}{sit[:2].lower()}{i:04d}", "situation": sit, "style": ML.STYLES[i % len(ML.STYLES)],
                    "level": ML.LEVELS[(i // len(ML.STYLES)) % len(ML.LEVELS)], "form": "line"}
            if rnd.random() < 0.5:
                spec["profession"] = ML.PROFESSIONS[rnd.randrange(len(ML.PROFESSIONS))]
            if sit == "OFF" and rnd.random() < STORY_SHARE:
                spec["form"] = "story"
            out.append(spec)
    return out


def _hints(spec, lists, rnd) -> List[str]:
    pool = list(lists.get("level-" + spec["level"], []))
    if spec.get("profession"):
        pool += lists.get("profession-" + spec["profession"], []) * 2
    return sorted(set(rnd.sample(pool, min(10, len(pool))))) if pool else []


def _write_persons(specs: List[Dict[str, Any]], name: str, families=PERSON_WRITERS) -> None:
    """Each fixed batch of SPEC_BATCH specs belongs to one writer family (in turn); one process per family may run at
    the same time, each saving its own file <name>_<family>.json."""
    lists = vocab_lists()
    for fam in families:
        own = name[:-5] + "_" + fam + ".json"
        got: Dict[str, str] = (_load(own) or {}).get("lines", {})
        for b in range(0, len(specs), SPEC_BATCH):
            if PERSON_WRITERS[(b // SPEC_BATCH) % len(PERSON_WRITERS)] != fam:
                continue
            rnd = random.Random(name + str(b))
            batch = [dict(s, words=_hints(s, lists, rnd)) for s in specs[b:b + SPEC_BATCH] if s["id"] not in got]
            if not batch:
                continue
            text, _ = llm_ct.run_cli(fam, BRIEF_PERSONS2 + "\n\nSPECS:\n" + json.dumps(batch, ensure_ascii=False),
                                     f"{name[:-5]}-{b // SPEC_BATCH}")
            for it in llm_ct.parse_reply(text) or []:
                if isinstance(it, dict) and it.get("id") and isinstance(it.get("text"), str):
                    got[it["id"]] = it["text"].strip()
            print(name, b // SPEC_BATCH, fam, sum(1 for s in batch if s["id"] in got), "of", len(batch), flush=True)
            _save(own, {"specs": specs, "lines": got})


def stage_persons(families=PERSON_WRITERS) -> None:
    _write_persons(_specs(PERSON_COUNTS, "p", "persons-v2"), "persons_v2.json", families)


def stage_persons_exam(families=PERSON_WRITERS) -> None:
    _write_persons(_specs(EXAM_PERSON_COUNTS, "x", "persons-exam-v2"), "persons_exam_v2.json", families)


def person_ok(spec: Dict[str, Any], text: str) -> bool:
    words = text.split()
    if not text or "^" in text or ML.ht.RECIPE_SPEAK_RX.search(text):
        return False
    if {w.lower() for w in ML._words(text)} & ML.NAMES:          # A-TALK-8 I1: no made-up world name in a chat line
        return False
    sit = spec["situation"]
    if sit == "OFF":
        return "?" not in text and len(words) <= (ML.STORY_MAX_WORDS if spec["form"] == "story" else 30)
    if sit == "SMALL":
        return len(words) <= 6
    return len(words) <= 30 and ("?" in text or ML.ht.is_question(text))


def person_inputs(name: str) -> List[Dict[str, Any]]:
    specs, lines = [], {}
    for fam in PERSON_WRITERS:
        doc = _load(name[:-5] + "_" + fam + ".json") or {"specs": [], "lines": {}}
        specs = specs or doc["specs"]
        lines.update(doc["lines"])
    out, seen = [], set()
    for s in specs:
        t = lines.get(s["id"])
        if not t or t.lower() in seen or not person_ok(s, t):
            continue
        seen.add(t.lower())
        x = ML.styled(ML.line_input(s["situation"], t, f"v2:{s['id']}"), s["style"], s["level"], s.get("profession"), s["form"])
        out.append(dict(x, id=s["id"]))
    return out


# ----------------------------------------------------------------------------------------------- inputs
def v1_inputs() -> List[Dict[str, Any]]:
    """v1's inputs with their v1 ids, styled plain / warm at grade10 (v1's brief: register A plain, f warm)."""
    xs = json.load(open(os.path.join(V1, "inputs.json"), encoding="utf-8"))
    return [ML.styled(x, "warm" if x["tone"][1] == "|f" else "plain", "grade10") for x in xs]


def new_fact_inputs(n: int, first_index: int, prefix: str) -> List[Dict[str, Any]]:
    out = []
    for i, x in enumerate(ML.fact_inputs(n, first_index=first_index)):
        out.append(dict(ML.styled(x, ML.STYLES[i % len(ML.STYLES)], ML.LEVELS[(i // len(ML.STYLES)) % len(ML.LEVELS)]),
                        id=f"{prefix}{i:04d}"))
    return out


def all_inputs() -> List[Dict[str, Any]]:
    return v1_inputs() + new_fact_inputs(NEW_FACTS, NEW_FACT_INDEX, "f") + person_inputs("persons_v2.json")


def writer_view(x: Dict[str, Any]) -> Dict[str, Any]:
    v = MM_writer_view(x)
    v["style"], v["level"] = x["style"]
    if x.get("profession"):
        v["person_works_as"] = x["profession"]
    return v


MM_writer_view = MM.writer_view


def _copy_v1() -> None:
    """v1's written lines and keys (same ids), copied once."""
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(V1):
        if (name.startswith("written_") or name.startswith("keys_")) and name.endswith(".json") \
                and not os.path.exists(os.path.join(OUT, name)):
            shutil.copyfile(os.path.join(V1, name), os.path.join(OUT, name))


def stage_write(families: Tuple[str, ...] = NEW_FAMILIES) -> None:
    _copy_v1()
    MM.inputs, MM.writer_view, MM.BRIEF_WRITE = all_inputs, writer_view, BRIEF_WRITE2
    MM.stage_write(families)


def stage_rewrite(families: Tuple[str, ...] = NEW_FAMILIES) -> None:
    """Every NEW reply that still breaks a rule goes back once to its own family with the reason (tag fix2-<fam>-k)."""
    xs = {x["id"]: x for x in _load("inputs.json")}
    for fam in families:
        doc = _load(f"written_{fam}.json") or {"lines": {}, "calls": []}
        written = doc["lines"]
        rdir = os.path.join(OUT, "replies")
        for name in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
            if name.startswith(f"fix2-{fam}-") and name.endswith(".txt"):
                llm_ct._take(open(os.path.join(rdir, name), encoding="utf-8").read(), written)
        redo = [dict(writer_view(x), refused_because=ML.rule_check(x, written.get(x["id"], ""))[1],
                     your_reply=written.get(x["id"], "")) for x in xs.values()
                if not x["id"].startswith("m") and not ML.rule_check(x, written.get(x["id"], ""))[0]]
        size = 95 if fam in MM.SMALL_BATCH_FAMILIES else 190
        for b in range(0, len(redo), size):
            tag = f"fix2-{fam}-{b // size}"
            if os.path.exists(os.path.join(rdir, tag + ".txt")):
                continue
            text, meta = llm_ct.run_cli(fam, BRIEF_WRITE2 + "\n\nREWRITE these items (each was refused for the reason "
                                        "given):\n" + json.dumps(redo[b:b + size], ensure_ascii=False), tag)
            doc.setdefault("calls", []).append(meta)
            llm_ct._take(text, written)
        print(fam, "refused before", len(redo), "still refused",
              sum(1 for x in xs.values() if not x["id"].startswith("m") and not ML.rule_check(x, written.get(x["id"], ""))[0]),
              flush=True)
        _save(f"written_{fam}.json", doc)


def stage_ingest_keys(families: Tuple[str, ...] = ("anthropic",)) -> None:
    """File-mode checks: read every replies/key-<fam>-*.txt into keys_<fam>.json (v1's keys kept; nothing is deleted)."""
    for fam in families:
        doc = _load(f"keys_{fam}.json") or {"family": fam, "keys": {}, "calls": []}
        rdir = os.path.join(OUT, "replies")
        n = 0
        for name in sorted(os.listdir(rdir)):
            if name.startswith(f"key-{fam}-") and name.endswith(".txt"):
                for it in llm_ct.parse_reply(open(os.path.join(rdir, name), encoding="utf-8").read()) or []:
                    if isinstance(it, dict) and it.get("id") and isinstance(it.get("pass"), bool):
                        doc["keys"][it["id"]] = {"pass": it["pass"], "why": it.get("why")}
                        n += 1
        _save(f"keys_{fam}.json", doc)
        print(fam, "keys read", n, "total", len(doc["keys"]), flush=True)


OPINION_WHY = ("opinion", "judg", "evaluat", "feeling", "glad", "happy", "praise", "lovely", "nice", "sounds")


def stage_rekey_opinion(families: Tuple[str, ...] = NEW_FAMILIES) -> None:
    """A-TALK-11 L4: every key that failed a lesson for opinion / judgement / feeling is judged again by the same family
    under the new key brief (opinions allowed, advice and made-up facts not). Re-runnable: a file-mode family is
    completed by re-running after its replies (tags rekey-<fam>-k)."""
    xs = {x["id"]: x for x in _load("inputs.json")}
    lines = {f: (_load(f"written_{f}.json") or {"lines": {}})["lines"] for f in MM.FAMILIES}
    for fam in families:
        doc = _load(f"keys_{fam}.json")
        keys = doc["keys"]
        todo = []
        for kid, v in keys.items():
            if v["pass"] or not any(w in (v.get("why") or "").lower() for w in OPINION_WHY):
                continue
            writer, iid = kid.split(":", 1)
            if iid in xs and iid in lines.get(writer, {}):
                vw = MM.writer_view(xs[iid])
                todo.append({"id": kid, "situation": vw["situation"], "content": vw["content"], "reply": lines[writer][iid]})
        todo.sort(key=lambda t: t["id"])
        size = 190 if fam in MM.SMALL_BATCH_FAMILIES else 380
        n = 0
        for b in range(0, len(todo), size):
            text, meta = llm_ct.run_cli(fam, MM.BRIEF_KEY + "\n\nITEMS:\n" + json.dumps(todo[b:b + size], ensure_ascii=False),
                                        f"rekey-{fam}-{b // size}")
            for it in llm_ct.parse_reply(text) or []:
                if isinstance(it, dict) and it.get("id") in keys and isinstance(it.get("pass"), bool):
                    keys[it["id"]] = {"pass": it["pass"], "why": it.get("why"), "rekey": "A-TALK-11"}
                    n += 1
        _save(f"keys_{fam}.json", doc)
        print(fam, "opinion fails to re-judge", len(todo), "re-judged", n,
              "now pass", sum(1 for t in todo if keys[t["id"]]["pass"]), flush=True)


def stage_key(families: Tuple[str, ...] = NEW_FAMILIES) -> None:
    MM.stage_key(families)


# ----------------------------------------------------------------------------------------------- assemble
def stage_assemble(families=None) -> Dict[str, Any]:
    xs = {x["id"]: x for x in _load("inputs.json")}
    keys = {k: (_load(f"keys_{k}.json") or {"keys": {}})["keys"] for k in MM.FAMILIES}
    counts = {"written": 0, "rule_ok": 0, "kept": 0, "key_fail": 0, "key_missing": 0, "over_cap": 0}
    per: Dict[str, List[Dict[str, Any]]] = {}
    # A-TALK-10 K9: openai's few rewritten lines were rewritten while anthropic's key prompts were built, so an anthropic
    # key may belong to the old text; those lines are left out
    stale = set()
    rdir = os.path.join(OUT, "replies")
    for name in os.listdir(rdir):
        if name.startswith("fix2-openai-") and name.endswith(".txt"):
            stale |= {"openai:" + it["id"] for it in llm_ct.parse_reply(open(os.path.join(rdir, name), encoding="utf-8").read())
                      or [] if isinstance(it, dict) and it.get("id")}
    counts["stale_rewrite"] = len(stale)
    for fam in MM.FAMILIES:
        for iid, line in (_load(f"written_{fam}.json") or {"lines": {}})["lines"].items():
            x = xs.get(iid)
            if x is None or f"{fam}:{iid}" in stale:
                continue
            counts["written"] += 1
            if not ML.rule_check(x, line)[0]:
                continue
            counts["rule_ok"] += 1
            ks = [keys[k][f"{fam}:{iid}"] for k in MM.FAMILIES if k != fam and f"{fam}:{iid}" in keys[k]]
            if len(ks) < 2:
                counts["key_missing"] += 1
                continue
            if not all(k["pass"] for k in ks):
                counts["key_fail"] += 1
                continue
            per.setdefault(iid, []).append({
                "input_key": x["input_key"], "situation": x["situation"], "tone": list(x["tone"]), "style": x["style"],
                "profession": x.get("profession"), "form": x.get("form", "line"), "input_text": x["input_text"],
                "target": line, "source": "LLM_WRITTEN", "writer": fam, "reading": x.get("reading"),
                "person_line": x.get("person_line")})
    rows = []
    for iid, rs in per.items():
        rs = sorted({r["target"].strip().lower(): r for r in rs}.values(), key=lambda r: hashlib.sha256(
            (iid + r["writer"]).encode()).hexdigest())                       # distinct wordings only, fixed order
        counts["over_cap"] += max(0, len(rs) - KEEP_PER_INPUT)
        rows += rs[:KEEP_PER_INPUT]
    counts["kept"] = len(rows)
    for x in xs.values():
        t = ML.template_line(x)
        if t:
            rows.append({"input_key": x["input_key"], "situation": x["situation"], "tone": list(x["tone"]),
                         "style": x["style"], "input_text": x["input_text"], "target": t, "source": "TEMPLATE",
                         "writer": "rule", "reading": x.get("reading"), "person_line": x.get("person_line")})
    rows = ML.cap_templates(ML.lesson_templates_ok(rows))        # A-TALK-9 J2
    train, dev = ML.split(rows)
    for name, part in (("rows_mouth_train.jsonl", train), ("rows_mouth_dev.jsonl", dev)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
            for r in part:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    rec = {"counts": counts, "train": len(train), "dev": len(dev), "inputs": len(xs),
           "by_style": {s: sum(1 for r in rows if r["style"][0] == s and r["source"] == "LLM_WRITTEN") for s in ML.STYLES},
           "by_situation": {s: sum(1 for r in rows if r["situation"] == s and r["source"] == "LLM_WRITTEN")
                            for s in ML.SITUATIONS},
           "templates": sum(1 for r in rows if r["source"] == "TEMPLATE")}
    _save("MOUTH_LESSONS_RECORD_V2.json", rec)
    print(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    fams = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    stage = {"vocab": stage_vocab, "persons": stage_persons, "persons_exam": stage_persons_exam, "write": stage_write,
             "key": stage_key, "rewrite": stage_rewrite, "rekey_opinion": stage_rekey_opinion, "ingest_keys": stage_ingest_keys, "assemble": stage_assemble}[sys.argv[1]]
    if sys.argv[1] == "vocab":
        stage_vocab(sys.argv[2] if len(sys.argv) > 2 else "0/1")
    else:
        stage(fams) if fams else stage()
