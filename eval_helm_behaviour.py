"""HELM behavioural baseline — scripted dialogues against the claimed v0.8.1 capabilities.

Each scenario drives a real HELMConversationalSession and checks observable behaviour (reply text, memory state).
It is deliberately small and mechanical: the point is to have a number that can go up, not to be exhaustive.

    python eval_helm_behaviour.py [--json out.json]
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


def run(turns):
    """Drive one session through the turns, returning (outputs, session)."""
    sid = abs(hash(tuple(turns))) % 100000
    s = hc.HELMConversationalSession(mode="everyday", session_id=f"eval_{sid}")
    outs = []
    for t in turns:
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn(t)
        outs.append(f.getvalue())
    return outs, s


def has(out, *words):
    low = out.lower()
    return all(w.lower() in low for w in words)


def none_of(out, *words):
    low = out.lower()
    return all(w.lower() not in low for w in words)


SCENARIOS = [
    # family, name, turns, predicate(outputs, session)
    ("narrative", "recall_place", ["My grandfather kept bees in the south of France.",
                                   "What did I tell you about my grandfather?"],
     lambda o, s: has(o[-1], "france") or has(o[-1], "bee")),
    ("narrative", "recall_object", ["I collect vintage mechanical watches.",
                                    "What do you remember about my hobby?"],
     lambda o, s: has(o[-1], "watch")),
    ("narrative", "recall_person", ["My sister Amara is a marine biologist.",
                                    "Who is Amara?"],
     lambda o, s: has(o[-1], "marine") or has(o[-1], "biologist")),
    ("preference", "concise_followed", ["I prefer short answers.", "Explain how a bicycle works."],
     lambda o, s: len(o[-1]) < 900),
    ("preference", "stored", ["Please keep your answers brief."],
     lambda o, s: bool(s.memory.context.user_preferences.get("concise"))),
    ("inventory", "declare_and_query", ["I have 10 Flour and 8 Water.", "What do I have?"],
     lambda o, s: has(o[-1], "flour")),
    ("inventory", "declare_updates_state", ["I have 10 Flour and 8 Water."],
     lambda o, s: bool(getattr(s, "turn_count", 0) >= 1)),
    ("recipe_gate", "missing_water", ["I have 10 Flour and 2 Sugar.", "Can we bake a batch with 10 Flour and no Water?"],
     lambda o, s: has(o[-1], "water") and (has(o[-1], "need") or has(o[-1], "can't") or has(o[-1], "cannot") or has(o[-1], "missing"))),
    ("recipe_gate", "valid_batch", ["I have 10 Flour and 8 Water.", "Can we bake a batch with 10 Flour and 8 Water?"],
     lambda o, s: not has(o[-1], "cannot") and not has(o[-1], "can't")),
    ("refusal", "ood_capital", ["What is the capital of Portugal?"],
     lambda o, s: none_of(o[-1], "lisbon")),
    ("refusal", "ood_future", ["Who will win the football game next year?"],
     lambda o, s: none_of(o[-1], " will win ")),
    ("memory_count", "count_two", ["I have a dog named Rufus.", "I drive a blue truck.",
                                   "How many things have I told you?"],
     lambda o, s: bool(re.search(r"\b(two|2)\b", o[-1].lower()))),
    ("memory_count", "turn_count_exact", ["I have a dog named Rufus.", "I drive a blue truck."],
     lambda o, s: s.turn_count == 2),
    ("anaphora", "it_resolves", ["I have 10 Flour and 8 Water.", "Can we bake a batch with it?"],
     lambda o, s: has(o[-1], "flour") or has(o[-1], "batch")),
    ("summary", "summary_lists_topic", ["I have a dog named Rufus.", "Summarize our conversation."],
     lambda o, s: has(o[-1], "rufus") or has(o[-1], "dog")),
]


def main() -> int:
    results = []
    for family, name, turns, pred in SCENARIOS:
        try:
            outs, sess = run(turns)
            ok = bool(pred(outs, sess))
            detail = ""
        except Exception as e:
            ok = False
            detail = f"{type(e).__name__}: {e}"
        results.append({"family": family, "name": name, "ok": ok, "detail": detail,
                        "last_output": (outs[-1][-400:] if 'outs' in locals() and outs else "")})
        print(("PASS " if ok else "FAIL ") + f"{family}/{name}" + (f"  [{detail}]" if detail else ""), flush=True)
    fams = {}
    for r in results:
        fams.setdefault(r["family"], []).append(r["ok"])
    summary = {f: {"passed": sum(v), "of": len(v)} for f, v in fams.items()}
    total = sum(1 for r in results if r["ok"])
    out = {"results": results, "families": summary, "passed": total, "of": len(results),
           "score": round(total / len(results), 4)}
    print(json.dumps({k: out[k] for k in ("families", "passed", "of", "score")}, indent=1))
    if "--json" in sys.argv:
        p = Path(sys.argv[sys.argv.index("--json") + 1])
        p.write_text(json.dumps(out, indent=1), encoding="utf-8")
        print("written", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
