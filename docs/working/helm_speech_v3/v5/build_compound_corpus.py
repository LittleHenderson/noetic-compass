"""Build compound (mixture) and absence training rows from deliberate templates.

Concatenating triggers produced ungrammatical turns ("Hey so I need a hand talk later"), so each compound is written as
a template with slots. Components and weights are explicit; every row is guard-checked.

    python build_compound_corpus.py
"""
from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mouth_task import check   # noqa: E402

OUT = HERE / "data" / "mouth_train_compounds.jsonl"

SLOTS = {
    "emotion": ["exhausted", "worn down", "stressed", "low", "anxious", "drained"],
    "task": ["report", "invoice", "deck", "review", "handover", "budget"],
    "day": ["Friday", "Monday", "tomorrow", "the end of the week"],
    "choice": ["take the offer", "move the meeting", "say yes", "push it back", "ask for more time"],
    "thing": ["file", "version", "date", "number", "branch"],
    "transport": ["train", "bus", "call", "meeting"],
    "problem": ["cancelled", "delayed", "moved", "double-booked"],
    "relation": ["father", "aunt", "uncle", "friend"],
    "relation2": ["funeral", "hospital", "service", "family"],
    "number": ["figure", "total", "score", "percentage"],
    "risk": ["the unverified inputs", "the cost", "the stale state", "the missing check"],
    "action": ["check the smallest piece", "pin the inputs", "run the check", "keep a control"],
    "step": ["the final check", "the export", "the review", "the upload"],
    "item": ["order", "batch", "delivery", "shipment"],
}

TEMPLATES = [
    # components, user, reply, weights
    (("EMPATHY", "PLAN"), "I'm {emotion} but I still need to finish the {task} by {day}.",
     "That sounds draining. What's the smallest step on the {task} you could take today?", (0.6, 0.4)),
    (("EMPATHY", "SUGGEST"), "I'm {emotion} and I don't know whether to {choice}.",
     "That's a lot to carry. What would make the {choice} feel lighter?", (0.6, 0.4)),
    (("EMPATHY", "STATUS"), "I'm {emotion}, and the {task} is still sitting there.",
     "I hear you. Let's look at where the {task} actually stands before anything else.", (0.5, 0.5)),
    (("THANKS", "CLARIFY"), "Thanks, that helps — which {thing} did you mean?",
     "Glad it helped. I meant the {thing} we discussed; is that the one?", (0.5, 0.5)),
    (("APOLOGY", "EXPLAIN"), "Sorry I'm late — the {transport} was {problem}.",
     "No harm done. Thanks for saying why.", (0.5, 0.5)),
    (("CLARIFY", "HEDGE"), "I think it's the {thing}, but I'm not sure.",
     "Want me to confirm the {thing} before we go any further?", (0.6, 0.4)),
    (("PLAN", "STATUS"), "We still need to {task}; where are we on it?",
     "One step left: {step}. The rest is done.", (0.6, 0.4)),
    (("CONGRATS", "THANKS"), "We shipped the {task} — thanks for the help.",
     "That's excellent news. Glad I could help with the {task}.", (0.5, 0.5)),
    (("CONDOLENCE", "ENCOURAGE"), "I lost my {relation} and I can't focus on the {task}.",
     "I'm very sorry. There's no rush — one small thing at a time, and the {task} can wait.", (0.6, 0.4)),
    (("REFUSE_POLITE", "EXPLAIN"), "Just make up the {number} — why not?",
     "I won't invent a {number}. An estimate I can label as a bound is different.", (0.5, 0.5)),
    (("WARN", "SUGGEST"), "Is the {item} risky, and what would you do?",
     "The risk is {risk}. I'd {action} first.", (0.5, 0.5)),
    (("REASSURANCE", "PLAN"), "Did I break the {item}? What now?",
     "Nothing's lost. First we check the {item}, then we redo the last step.", (0.5, 0.5)),
    (("ENCOURAGE", "PLAN"), "I keep hitting a wall with the {task}.",
     "That's normal at this point. Break the {task} into one piece and start there.", (0.5, 0.5)),
    (("CONFIRM", "STATUS"), "So the {item} is done — that's right, isn't it?",
     "That's right. The {item} is finished and nothing is pending.", (0.5, 0.5)),
    (("PLAYFUL", "SMALLTALK"), "Tell me a joke — how's your day going, by the way?",
     "I'd tell you a UDP joke, but you might not get it. Quiet here, which is how I like it. You?", (0.5, 0.5)),
]

ABSENCE = [
    ("I need to finish the {task} but I haven't told you when it's due.", "deadline",
     "When is the {task} due? I don't have a date from you yet."),
    ("Can we bake a batch with what's left?", "flour",
     "I don't have a flour count yet — how much flour is left?"),
    ("Is the {item} ready to ship?", "tracking number",
     "I don't have a tracking number, so I can't confirm the {item}."),
    ("How long will the {item} take to arrive?", "address",
     "I don't know the delivery address, so I can't estimate the time."),
    ("Can you check whether the {task} passed?", "test result",
     "I don't have the test result yet — where should I look for it?"),
    ("Should I take the {choice}?", "salary",
     "I don't know the salary, so I can't weigh it properly. What's on offer?"),
    ("Is the tank full enough for the {item}?", "tank level",
     "I don't have a tank reading. What does the gauge say?"),
    ("Can we start the batch now?", "water",
     "I don't have a water count, and water decides the batch. How much is there?"),
    ("Will the {task} be done by {day}?", "start date",
     "I don't know when it starts, so I can't say whether {day} is realistic."),
    ("Did the payment for the {item} go through?", "receipt",
     "I don't have a receipt, so I can't confirm that payment."),
    ("How many can we make?", "stock level",
     "I don't have the stock level yet. What's on hand?"),
    ("Is the build green for the {task}?", "build log",
     "I don't have the build log, so I can't say whether it passed."),
]


def fill(text: str, chosen: dict) -> str:
    for k, val in chosen.items():
        text = text.replace("{" + k + "}", val)
    return text


def main() -> int:
    rng = random.Random(20261026)
    rows = []
    for comps, ut, rt, weights in TEMPLATES:
        for i in range(24):
            chosen = {k: rng.choice(v) for k, v in SLOTS.items()}
            user, reply = fill(ut, chosen), fill(rt, chosen)
            situation = " ".join(f"{c.lower()} {w}" for c, w in zip(comps, weights))
            ok, _ = check.check("SMALLTALK", user, reply, set(), None)
            if ok:
                rows.append({"situation": situation, "tone": ["^1", "|f"] if i % 2 else ["^1", "|A"],
                             "input_text": user, "target": reply, "style": None, "context": None,
                             "absence": None, "components": list(comps), "source": "compound"})
    for ut, absent, rt in ABSENCE:
        for i in range(8):
            chosen = {k: rng.choice(v) for k, v in SLOTS.items()}
            user, reply = fill(ut, chosen), fill(rt, chosen)
            ok, _ = check.check("CLARIFY", user, reply, set(), None)
            if ok:
                rows.append({"situation": "clarify 1.0", "tone": ["^1", "|f"] if i % 2 else ["^1", "|A"],
                             "input_text": user, "target": reply, "style": None, "context": None,
                             "absence": absent, "components": ["CLARIFY"], "source": "absence"})
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    by = {}
    for r in rows:
        by[r["source"]] = by.get(r["source"], 0) + 1
    print(json.dumps({"rows": len(rows), "by_source": by,
                      "with_absence": sum(1 for r in rows if r["absence"]), "file": str(OUT)}, indent=1))
    for r in rows[:5]:
        print("\nSIT:", r["situation"], "| ABS:", r["absence"])
        print("  U:", r["input_text"])
        print("  R:", r["target"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
