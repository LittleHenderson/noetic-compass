"""Teaching turns of TEACH-2 (pre-code 4.2, A-TEACH2-18 P6): the checker of a turn file, and the rule-written PRACTICE turns.
TEACH-1's turns_t1.py with the TRAP kind added (keyed like a FACT: the keyers name the true value) and TEACH-2's floors.

The sealed exam's turns are `LLM_WRITTEN` by at least three AI model families and keyed by another family
(contract/WRITER_BRIEF_TEACH2.md, contract/KEY_FORMAT_TEACH2.md). This file never writes an exam turn. It:
  - checks a turn file against the floors (32 per world, >= 18 FACT, exactly 4 TRAP, >= 2 small talk, >= 2 corrections),
    every fact stated, the word cap,
    the forbidden phrases (the chat's own trigger patterns, so that every fact flows through working memory and not
    through a side branch of the chat: TEACH-1 D-TEACH1-2), the eight-word split against the generator's templates and the
    practice turns (HG-SPLIT), the writer labels and the two keys;
  - writes the builder's PRACTICE turns by rule (label RULE_WRITTEN_PRACTICE), which the reader refuses in a sealed reading.
"""
from __future__ import annotations

import random
import re
from typing import Any, Callable, Dict, List, Optional

from . import common_t2 as C
from . import worlds_t2 as W

#: the chat's own trigger patterns (helm_chat.handle_turn at the cut), as forbidden phrases in a teaching turn (TEACH-1 D-TEACH1-2)
FORBIDDEN = {
    "narrative_family": r"\b(my grandfather|my grandmother|my dad|my father|my mother|my brother|my sister|my family|my friend|my cousin)\b",
    "narrative_self": r"\b(i live in|i work at|i grew up in|i enjoy|i like|i love|i own|i have a|i used to|i am a|i'm a)\b",
    "narrative_trade": r"\b(kept bees|keeps bees|beekeeping|beekeeper|farmer|gardener|carpenter)\b",
    "preference": r"\b(remember that i prefer|i prefer|prefer short answers|keep (?:your )?answers? (?:short|concise|brief))\b",
    "affect": r"\b(i'm feeling|i am feeling|i feel|i'm tired|i am tired)\b",
    "memory_recall": r"\b(remember what i said|what i said about|what did i say about|my preference|what did i say)\b",
    "memory_count": r"\b(how many things have i told you|how many facts|how much do you know about me)\b",
    "knowledge_query": r"\b(what do you know about me|who am i|what have i told you|what do you remember about me|tell me about myself|what do you know so far)\b",
    "summary": r"\b(what did we just do|previous result|last result|what was accomplished|summary)\b",
    "explanation": r"\b(explain it back to me|in your own words|walk me through|explain what you|why did you)\b",
    "humor": r"\b(tell me a joke|make me laugh|say something funny)\b",
    "study": r"\b(study|investigate|explore|learn about|formulate a recipe for|model the physics of)\b",
    # (the chat's agentic, kitchen and mood rules are checked by asking HELM itself: route_check, TEACH-1 D-TEACH1-2)
    "brain_food": r"\b(flour|water|sugar|butter|eggs?|milk|salt|yeast|bread|frosting|meringue|starter)\b",
    "commands": r"^(exit|quit|q|help|dials|history|mode)$",
    "cas_token": r"\^\d|\bNoetic\b|\bCAS\b",
}
KEYED_KINDS = ("FACT", "FIX", "RESTATE", "UNKNOWN", "TRAP")
KINDS = KEYED_KINDS + ("SMALL",)

#: the practice small talk (rule-written; never the exam; each line carries at least one clue word so it compacts)
PRACTICE_SMALL = ("Okay, back to my notes.", "Thanks, that's helpful.", "Give me a second, I'm looking for my notes.",
                  "Right, where was I.", "This is quite a lot to keep straight.", "Okay, moving on.",
                  "Sorry, lost my thread for a moment.", "Anyway, let me carry on.")
PRACTICE_PREFIX = ("", "By the way, ", "Oh, and ", "One more thing: ", "Also, ", "Let me add that ")
PRACTICE_RESTATE = "As I said before, "


def _lower_first(s: str) -> str:
    """Lower the first letter only when the line opens with "The" or "Not" (TEACH-2 practice fix: TEACH-1's version
    lowered every first letter, so "Elowen" became "elowen" and "I" became "i" after a prefix)."""
    return s[:1].lower() + s[1:] if s.startswith(("The ", "Not ")) else s


def practice_turns(world: Dict[str, Any], plan: List[Dict[str, Any]], seed) -> List[Dict[str, Any]]:
    """The builder's rule-written turns for one world: the plan's slots with light templated variation."""
    rng = random.Random(f"{seed}:practice-turns:{world['world_id']}")
    out = []
    for s in plan:
        kind = s["kind"]
        if kind == "SMALL":
            text = PRACTICE_SMALL[(s["small_index"] + rng.randrange(len(PRACTICE_SMALL))) % len(PRACTICE_SMALL)]
        elif kind == "RESTATE":
            text = PRACTICE_RESTATE + _lower_first(s["text"])
        elif kind == "UNKNOWN":
            text = rng.choice(("", "Honestly, ")) + (s["text"] if not rng.random() < 0.5 else _lower_first(s["text"]))
            text = text[:1].upper() + text[1:]
        elif kind == "FIX":
            text = s["text"]
        elif kind == "TRAP":
            pre = rng.choice(("",) + PRACTICE_PREFIX[1:3]) if s.get("trap_role") == "FIRST" else PRACTICE_RESTATE
            text = pre + (_lower_first(s["text"]) if pre and s["text"].startswith(("The ", "Not ")) else s["text"])
        else:
            pre = rng.choice(PRACTICE_PREFIX)
            text = pre + (_lower_first(s["text"]) if pre else s["text"])
        out.append({"turn_index": s["turn_index"], "kind": kind, "fact_id": s["fact_id"], "text": text,
                    "value": s.get("value"), "not_value": s.get("not_value"), "trap_role": s.get("trap_role"),
                    "label": "RULE_WRITTEN_PRACTICE",
                    "writer": {"vendor": "rule", "model": "turns_t2.practice_turns", "version": C.PACKAGE_VERSION},
                    "keyed": "PLAN"})
    return out


def forbidden_hits(text: str) -> List[str]:
    low = (text or "").lower().strip()
    return [name for name, rx in FORBIDDEN.items() if re.search(rx, low, re.I)]


def split_hashes(worlds: List[Dict[str, Any]], extra_texts: List[str] = (), trap_texts: List[str] = ()) -> Dict[str, str]:
    """sha256 of every eight-word window of every generator template instance (statements, questions, unknown lines,
    corrections) of the given worlds, of the practice small talk, and of the extra texts; plus every whole text."""
    out: Dict[str, str] = {}

    def add(text: str, src: str) -> None:
        out[C.sha256_bytes(" ".join(C.words_of(text)).encode("utf-8"))] = f"{src}:whole"
        for g in C.ngrams(text):
            out[C.sha256_bytes(g.encode("utf-8"))] = src
    for w in worlds:
        for f in w["facts"]:
            add(f["statement"], f"{w['world_id']}:{f['id']}:statement")
            add(f["question"], f"{w['world_id']}:{f['id']}:question")
            add(f["unknown_statement"], f"{w['world_id']}:{f['id']}:unknown")
            if f.get("fix"):
                add(f["fix"]["first_statement"], f"{w['world_id']}:{f['id']}:first")
                add(f["fix"]["correction"], f"{w['world_id']}:{f['id']}:fix")
    for t in trap_texts:
        add(t, "trap_canonical")
    for s in PRACTICE_SMALL + W.WAVE7_NOISE:
        add(s, "small_talk")
    for t in extra_texts:
        add(t, "practice_turn")
    return out


def check_turns(world: Dict[str, Any], turns: List[Dict[str, Any]], *, sealed: bool, split: Dict[str, str],
                routed: Optional[Callable[[str], bool]] = None) -> Dict[str, Any]:
    """The checker. `sealed` demands LLM_WRITTEN labels with a named writer and two keys on FACT / FIX. `routed(text)`
    (optional) says whether HELM's recipe reader would claim the line (the custodian's dry check, a fresh loop)."""
    problems: List[str] = []
    kinds = [t.get("kind") for t in turns]
    n = len(turns)
    keyed = sum(1 for t in turns if t.get("kind") in KEYED_KINDS and t.get("fact_id"))
    small = kinds.count("SMALL")
    fixes = kinds.count("FIX")
    facts_n = kinds.count("FACT")
    traps = kinds.count("TRAP")
    if n != C.TEACHING_TURNS:
        problems.append(f"turns {n} != {C.TEACHING_TURNS}")
    if facts_n < C.FLOOR_FACT_TURNS:
        problems.append(f"FACT turns {facts_n} < {C.FLOOR_FACT_TURNS}")
    if traps != C.PLAN_COUNTS["TRAP"]:
        problems.append(f"TRAP turns {traps} != {C.PLAN_COUNTS['TRAP']}")
    if small < C.FLOOR_SMALL_TURNS:
        problems.append(f"small talk {small} < {C.FLOOR_SMALL_TURNS}")
    if fixes < C.FLOOR_FIX_TURNS:
        problems.append(f"corrections {fixes} < {C.FLOOR_FIX_TURNS}")
    fact_ids = {f["id"] for f in world["facts"]}
    anchors = {f["id"]: f.get("anchor_words") or [] for f in world["facts"]}
    stated = {t.get("fact_id") for t in turns if t.get("kind") in ("FACT", "UNKNOWN")
              or (t.get("kind") == "TRAP" and t.get("trap_role") == "FIRST")}
    missing = sorted(fact_ids - stated)
    if missing:
        problems.append(f"facts never stated: {missing}")
    per_turn = []
    overlaps = 0
    for t in turns:
        text = t.get("text") or ""
        row: Dict[str, Any] = {"turn_index": t.get("turn_index"), "kind": t.get("kind"), "problems": []}
        if t.get("kind") not in KINDS:
            row["problems"].append("unknown kind")
        if len(text.split()) > C.MAX_TURN_WORDS:
            row["problems"].append(f"over {C.MAX_TURN_WORDS} words")
        if not text.strip():
            row["problems"].append("empty")
        hits = forbidden_hits(text)
        if hits:
            row["problems"].append("forbidden: " + ", ".join(hits))
        if t.get("kind") in KEYED_KINDS and "?" in text:
            row["problems"].append("a keyed turn is a question")
        if t.get("kind") in KEYED_KINDS and t.get("fact_id") not in fact_ids:
            row["problems"].append("fact id not in this world")
        if routed is not None:
            why = routed(t)
            if why:
                row["problems"].append("route: " + why)
        if t.get("kind") in KEYED_KINDS and t.get("fact_id") in anchors:
            low = set(C.words_of(text))
            miss = [w for w in anchors[t["fact_id"]] if w not in low]
            if miss:
                row["problems"].append("anchor words missing: " + ", ".join(miss))
        if sealed:
            whole = C.sha256_bytes(" ".join(C.words_of(text)).encode("utf-8"))
            grams = {C.sha256_bytes(g.encode("utf-8")) for g in C.ngrams(text)}
            hit = [split[h] for h in grams if h in split] + ([split[whole]] if whole in split else [])
            if hit:
                overlaps += 1
                row["problems"].append("split overlap: " + "; ".join(sorted(set(hit))[:3]))
            if t.get("label") != "LLM_WRITTEN" or not (t.get("writer") or {}).get("model"):
                row["problems"].append("not LLM_WRITTEN with a named writer")
            if t.get("kind") in KEYED_KINDS:
                if not (t.get("key1") and t.get("key2")):
                    row["problems"].append("keyed turn lacks two keys")
                elif t.get("keyed") != "AGREE":
                    row["problems"].append("keys disagree (UNDETERMINED): rewrite the turn")
                k1, k2 = t.get("key1") or {}, t.get("key2") or {}
                fams = {(t.get("writer") or {}).get("vendor"), k1.get("vendor"), k2.get("vendor")}
                if len(fams) < 3 or None in fams:
                    row["problems"].append("writer, key 1 and key 2 must be three different model families")
        per_turn.append(row)
    family_share_ok = True
    if sealed:
        fams: Dict[str, int] = {}
        for t in turns:
            v = (t.get("writer") or {}).get("vendor") or "?"
            fams[v] = fams.get(v, 0) + 1
        if len(fams) < 3:
            problems.append(f"fewer than three writer families: {sorted(fams)}")
        if fams and max(fams.values()) > n / 2:
            problems.append("one family wrote more than half of the turns")
            family_share_ok = False
    bad_turns = [r for r in per_turn if r["problems"]]
    return {"world_id": world["world_id"], "turns": n, "keyed": keyed, "small": small, "fixes": fixes, "facts": facts_n,
            "traps": traps, "problems": problems,
            "bad_turns": bad_turns, "split_overlaps": overlaps, "family_share_ok": family_share_ok,
            "ok": not problems and not bad_turns}
