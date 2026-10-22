"""Builder tool: A-TALK-2 B8 -- the builder's own sample lines (BUILDER_SAMPLE, never exam text) through HELM's chat with
HELM_TALK OFF and ON (and HELM_TALK_ASK ON for the asking flow), every reply counted against M1, M2, M7, opinion, one
question back, kept word for word, and nothing saved. Facts about the builder's lines; they license nothing.

    python -X utf8 -B docs/working/helm_talk_design_v1/build_v1/sample_talk_v1.py   (from the repository root)
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "SAMPLE_TALK_V1_20261022.json"

SAMPLE = {
    "SMALL": ["hi", "hey there", "good morning", "thanks", "thank you so much", "how are you", "ok"],
    "SELF": ["are you a robot?", "do you remember what I tell you?", "what can you do?", "who are you?"],
    "OFF": ["My sister is moving to Denver next month.", "I'm feeling tired today.", "The weather has been strange lately.",
            "We went hiking at Mount Tam on Saturday.", "My dog Biscuit chewed up a shoe.", "I feel run down this week.",
            "Work was a long day."],
    "WORLD": ["who won the game last night?", "what's the capital of Portugal?", "when does the store open?"],
}
ASK_FLOW = ["We have 12 cups of flour.", "My neighbour keeps asking about my flour.", "yes"]


def run(on: bool, ask: bool, lines):
    for k in ("HELM_TALK", "HELM_TALK_ASK", "HELM_CUBE_OSC", "HELM_MEMORY_COMPACT", "HELM_EYE_ACT"):
        os.environ.pop(k, None)
    if on:
        os.environ["HELM_TALK"] = "1"
    if ask:
        os.environ["HELM_TALK_ASK"] = "1"
    import helm_chat as hc
    import helm_talk as ht
    import helm_voice
    rows = []
    with contextlib.redirect_stdout(io.StringIO()):
        s = hc.HELMConversationalSession(mode="everyday", session_id=f"sample-{int(on)}{int(ask)}")
    for kind, line in lines:
        facts_before = list(s.memory.context.user_facts)
        stock_before = dict(s.loop.stock)
        with contextlib.redirect_stdout(io.StringIO()):
            s.handle_turn(line)
        t = s.memory.turns[-1]
        r = t.helm_response
        rows.append({"kind": kind, "line": line, "reply": r, "intent": t.intent, "talk": t.entities.get("talk"),
                     "cas_tokens": len(helm_voice.cas_tokens(r)), "recipe_speak": bool(ht.RECIPE_SPEAK_RX.search(r)),
                     "sentences": helm_voice.sentence_count(r), "opinion": bool(ht.OPINION_RX.search(r)),
                     "questions": r.count("?"), "kept_verbatim": line.strip().rstrip(".") in s.memory.context.user_facts,
                     "user_facts_changed": s.memory.context.user_facts != facts_before,
                     "stock_changed": dict(s.loop.stock) != stock_before})
    return rows


def summary(rows):
    out = {}
    for kind in list(SAMPLE) + ["ASK"]:
        rs = [r for r in rows if r["kind"] == kind]
        if not rs:
            continue
        out[kind] = {"lines": len(rs), "cas_token_replies": sum(r["cas_tokens"] > 0 for r in rs),
                     "recipe_speak_replies": sum(r["recipe_speak"] for r in rs),
                     "over_3_sentences": sum(r["sentences"] > 3 for r in rs), "opinion_replies": sum(r["opinion"] for r in rs),
                     "exactly_one_question": sum(r["questions"] == 1 for r in rs),
                     "kept_verbatim": sum(r["kept_verbatim"] for r in rs),
                     "saved_something": sum(r["user_facts_changed"] or r["stock_changed"] for r in rs),
                     "tool_engine_turns": sum(r["intent"] == "AGENTIC_GOAL" for r in rs)}
    return out


def main():
    lines = [(k, x) for k, xs in SAMPLE.items() for x in xs]
    with tempfile.TemporaryDirectory() as d:
        os.environ["HELM_SESSION_DIR"] = d
        off = run(False, False, lines)
        on = run(True, False, lines)
        ask = run(True, True, [("ASK", x) for x in ASK_FLOW])
    doc = {"schema": "helm.talk.sample/1", "label": "BUILDER_SAMPLE", "note": "the builder's own lines; facts that license nothing",
           "summary_off": summary(off), "summary_on": summary(on), "ask_flow": ask, "off": off, "on": on}
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"summary_off": doc["summary_off"], "summary_on": doc["summary_on"]}, indent=1))
    for a, b in zip(off, on):
        print(f"[{a['kind']}] {a['line']}\n   OFF: {a['reply'][:150]}\n   ON : {b['reply'][:150]}")
    for r in ask:
        print(f"[ASK] {r['line']}\n   ON : {r['reply'][:150]}")


if __name__ == "__main__":
    main()
