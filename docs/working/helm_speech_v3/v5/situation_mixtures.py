"""Situations are mixtures, not labels — measure how much our single-tag corpus throws away.

A turn like "I'm exhausted but I have to finish this report by Friday" is not EMPATHY. It is a compound: EMPATHY for the
state, ENCOURAGE for the persistence, STATUS/PLAN for the deadline. The recipe brain already models states this way
(Θ(Ω) = a·X + b·Y → Ω, with a limiting reagent). Our corpus tagging used one label per turn; this script measures the
loss and proposes the mixture representation.

    python situation_mixtures.py
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "data" / "public_corpus" / "public_turns_clean.jsonl"
OUT = HERE / "data" / "public_corpus" / "situation_mixtures_sample.json"

CUES = {
    "EMPATHY": r"\b(tired|exhausted|sad|angry|upset|lonely|depress\w*|anxious|worried|stressed|rough day|awful|"
               r"terrible|hurt|scared|afraid|frustrat\w*|struggl\w*|worn down|draining)\b",
    "ENCOURAGE": r"\b(can'?t do|give up|too hard|stuck|failing|not good enough|never finish|hitting a wall)\b",
    "PLAN": r"\b(need to|have to|must|deadline|by (monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
            r"before \w+day|next step|plan)\b",
    "STATUS": r"\b(still|yet|almost|nearly|halfway|done|finished|progress|status)\b",
    "APOLOGY": r"\b(sorry|apolog|my fault|my mistake|late)\b",
    "EXPLAIN": r"\b(because|since|due to|the reason|explain|cancel\w*|traffic)\b",
    "THANKS": r"\b(thanks?|thank you|appreciate)\b",
    "CLARIFY": r"\b(which one|not sure|confused|what do you mean|the other)\b",
    "CONDOLENCE": r"\b(passed away|died|funeral|loss|grief|bereave)\b",
    "CONGRATS": r"\b(congrat\w*|we did it|got the job|passed|shipped|worked)\b",
    "SUGGEST": r"\b(should i|would you|recommend|suggest|any ideas|what would you)\b",
    "HEDGE": r"\b(maybe|perhaps|not sure|probably|might|unsure|uncertain)\b",
}

WEIGHT = 0.5          # every detected component starts at the same weight; the top component gets the remainder
MAX_COMPONENTS = 3


def mixture(text: str) -> list[tuple[str, float]]:
    found = []
    for tag, rx in CUES.items():
        if re.search(rx, text, re.I):
            found.append(tag)
    if not found:
        return [("SMALLTALK", 1.0)]
    found = found[:MAX_COMPONENTS]
    if len(found) == 1:
        return [(found[0], 1.0)]
    # weights: first component dominant, the rest share the remainder
    rest = round((1.0 - 0.5) / (len(found) - 1), 3)
    return [(found[0], 0.5)] + [(t, rest) for t in found[1:]]


def main() -> int:
    rows = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    single, multi = 0, 0
    combos = Counter()
    samples = []
    for r in rows:
        mix = mixture(r["user"])
        if len(mix) == 1:
            single += 1
        else:
            multi += 1
            combos[" + ".join(t for t, _ in mix)] += 1
        if len(mix) > 1 and len(samples) < 12:
            samples.append({"user": r["user"][:160], "single_tag": r["situation"],
                            "mixture": [{"tag": t, "weight": w} for t, w in mix]})
    stats = {"rows": len(rows), "single_component": single, "multi_component": multi,
             "multi_fraction": round(multi / max(1, len(rows)), 4),
             "top_combinations": combos.most_common(10), "samples": samples}
    OUT.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("rows", "single_component", "multi_component", "multi_fraction")}, indent=1))
    print("top combinations:", stats["top_combinations"][:6])
    for s in samples[:6]:
        print("\nTURN:", s["user"])
        print("  single tag :", s["single_tag"])
        print("  mixture    :", s["mixture"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
