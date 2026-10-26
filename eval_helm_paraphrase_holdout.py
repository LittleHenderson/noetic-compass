"""HELM paraphrase ROBUSTNESS — held-out set. Authored before any fix; do not tune against it.

Same 7 families, 3 new phrasings each, different syntax and vocabulary from the dev set. Acceptance (frozen in
docs/working/HELM_NUANCE_UPGRADE_PLAN.md): accuracy >= 0.80 and mean distinctness >= 0.70, with the 15-check
behavioural baseline not falling below 9/15.

    python eval_helm_paraphrase_holdout.py [--json out.json]
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import helm_chat as hc  # noqa: E402


def one_reply(turn, pre=()):
    s = hc.HELMConversationalSession(mode="everyday", session_id="holdout_probe")
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
    "greeting": {"pre": (), "variants": ["Howdy.", "Morning!", "Well hello."],
                 "ok": lambda r: low(r).startswith("hello")},
    "affect": {"pre": (), "variants": ["Today has been draining.", "I'm running on empty.", "Not feeling my best."],
               "ok": lambda r: ("sorry" in low(r)) or ("hear" in low(r))},
    "preference": {"pre": (), "variants": ["Keep it short, please.", "Brief answers work best for me.",
                                           "I'd rather have concise responses."],
                   "ok": lambda r: ("noted" in low(r)) or ("prefer" in low(r)) or ("brief" in low(r)) or ("concise" in low(r))},
    "recipe_valid": {"pre": (),
                     "variants": ["10 Flour plus 8 Water — how many batches?",
                                  "What's the max batch from 10 Flour and 8 Water?",
                                  "We've got 10 Flour and 8 Water. How much can we make?"],
                     "ok": lambda r: ("units" in low(r)) or ("produce" in low(r)) or ("batch" in low(r))},
    "recipe_missing": {"pre": (),
                       "variants": ["No Water, just 10 Flour — can we still bake?",
                                    "Can we make a batch with 10 Flour and zero Water?",
                                    "Bake without Water using 10 Flour?"],
                       "ok": lambda r: ("water" in low(r)) and (("need" in low(r)) or ("can't" in low(r))
                                                                or ("cannot" in low(r)) or ("missing" in low(r))
                                                                or ("absent" in low(r)))},
    "recall": {"pre": ("My grandfather kept bees in the south of France.",),
               "variants": ["What do you know about my grandfather?", "Remind me about my grandfather.",
                            "My grandfather — what did I say?"],
               "ok": lambda r: ("bee" in low(r)) or ("france" in low(r))},
    "ood": {"pre": (), "variants": ["Portugal's capital, which city?", "What's Portugal's capital?",
                                    "Capital city of Portugal?"],
            "ok": lambda r: "lisbon" not in low(r)},
}


def main() -> int:
    rows = []
    for fam, spec in FAMILIES.items():
        replies = [one_reply(v, spec["pre"]) for v in spec["variants"]]
        correct = [bool(spec["ok"](r)) for r in replies]
        rows.append({"family": fam, "variants": len(replies), "correct": sum(correct),
                     "distinct": len(set(replies)), "replies": replies,
                     "failed": [v for v, c in zip(spec["variants"], correct) if not c]})
        print(f"{fam}: {sum(correct)}/{len(replies)} correct, {len(set(replies))} distinct", flush=True)
    total = sum(r["correct"] for r in rows)
    of = sum(r["variants"] for r in rows)
    out = {"families": rows, "correct": total, "of": of, "score": round(total / of, 4),
           "mean_distinct_fraction": round(sum(r["distinct"] / r["variants"] for r in rows) / len(rows), 4)}
    print(json.dumps({k: out[k] for k in ("correct", "of", "score", "mean_distinct_fraction")}, indent=1))
    if "--json" in sys.argv:
        p = Path(sys.argv[sys.argv.index("--json") + 1])
        p.write_text(json.dumps(out, indent=1), encoding="utf-8")
        print("written", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
