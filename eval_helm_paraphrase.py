"""HELM paraphrase-robustness evaluation.

The behavioural baseline used one wording per intent. This asks the harder question: does HELM recognise the SAME
intent when it is worded differently, and does it answer correctly each time? Every variant gets a fresh session.

Scoring is per-variant correctness against an explicit expected behaviour; distinctness is reported as information
(one distinct reply across paraphrase variants means the answer is a template, not a composition).

    python eval_helm_paraphrase.py [--json out.json]
"""
from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import helm_chat as hc  # noqa: E402


def one_reply(turn, pre=()):
    s = hc.HELMConversationalSession(mode="everyday", session_id="para_probe")
    out = ""
    for t in list(pre) + [turn]:
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn(t)
        out = f.getvalue()
    lines = [l for l in out.splitlines() if l.strip().startswith("HELM:")]
    return (lines[-1][6:].strip() if lines else out.strip()[-300:])


def low(s):
    return s.lower()


FAMILIES = {
    "greeting": {
        "pre": (),
        "variants": ["Hello there.", "Hi, how are you?", "Good morning.", "Hey.", "Greetings."],
        "ok": lambda r: low(r).startswith("hello"),
    },
    "affect": {
        "pre": (),
        "variants": ["I feel tired today.", "I am exhausted.", "Feeling pretty low right now.",
                     "I had a rough day.", "I'm worn out this week."],
        "ok": lambda r: ("sorry" in low(r)) or ("hear you" in low(r)) or ("hear that" in low(r)),
    },
    "preference": {
        "pre": (),
        "variants": ["I prefer short answers.", "Please keep it brief.", "Keep your replies concise.",
                     "Short answers please.", "I like concise replies."],
        "ok": lambda r: ("noted" in low(r)) or ("prefer" in low(r)) or ("brief" in low(r)) or ("concise" in low(r)),
    },
    "recipe_valid": {
        "pre": (),
        "variants": ["Can we bake a batch with 10 Flour and 8 Water?",
                     "We have 10 Flour and 8 Water, can we bake?",
                     "With 10 Flour and 8 Water, how much can we produce?",
                     "Do we have enough to bake a batch with 10 Flour and 8 Water?",
                     "Given 10 Flour and 8 Water, what can we make?"],
        "ok": lambda r: ("units" in low(r)) or ("produce" in low(r)) or ("batch" in low(r)),
    },
    "recipe_missing": {
        "pre": (),
        "variants": ["Can we bake a batch with 10 Flour and no Water?",
                     "We have 10 Flour but no Water, can we bake?",
                     "With 10 Flour and 0 Water, how much can we produce?",
                     "Do we have enough to bake with just 10 Flour?",
                     "Bake a batch from 10 Flour without Water."],
        "ok": lambda r: ("water" in low(r)) and (("need" in low(r)) or ("can't" in low(r)) or ("cannot" in low(r))
                                                 or ("missing" in low(r)) or ("absent" in low(r))),
    },
    "recall": {
        "pre": ("My grandfather kept bees in the south of France.",),
        "variants": ["What did I tell you about my grandfather?", "What do you remember about my grandfather?",
                     "Tell me what I said about my grandfather.", "Recall anything about my grandfather.",
                     "What was it about my grandfather?"],
        "ok": lambda r: ("bee" in low(r)) or ("france" in low(r)),
    },
    "ood": {
        "pre": (),
        "variants": ["What is the capital of Portugal?", "Which city is Portugal's capital?",
                     "Portugal's capital city is what?", "Name Portugal's capital.",
                     "Tell me the capital of Portugal."],
        "ok": lambda r: "lisbon" not in low(r),
    },
}


def main() -> int:
    rows = []
    for fam, spec in FAMILIES.items():
        replies = [one_reply(v, spec["pre"]) for v in spec["variants"]]
        correct = [bool(spec["ok"](r)) for r in replies]
        rows.append({"family": fam, "variants": len(replies), "correct": sum(correct),
                     "distinct": len(set(replies)),
                     "wrong_wording": [v for v, c in zip(spec["variants"], correct) if not c],
                     "replies": replies})
        print(f"{fam}: correct {sum(correct)}/{len(replies)}, distinct replies {len(set(replies))}", flush=True)
        for v, r, c in zip(spec["variants"], replies, correct):
            if not c:
                print(f"   FAIL [{v[:44]}] -> {r[:110]}", flush=True)
    total = sum(r["correct"] for r in rows)
    of = sum(r["variants"] for r in rows)
    out = {"families": rows, "correct": total, "of": of, "score": round(total / of, 4),
           "mean_distinct_fraction": round(sum(r["distinct"] / r["variants"] for r in rows) / len(rows), 4)}
    print(json.dumps({"correct": total, "of": of, "score": out["score"],
                      "mean_distinct_fraction": out["mean_distinct_fraction"]}, indent=1))
    if "--json" in sys.argv:
        p = Path(sys.argv[sys.argv.index("--json") + 1])
        p.write_text(json.dumps(out, indent=1), encoding="utf-8")
        print("written", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
