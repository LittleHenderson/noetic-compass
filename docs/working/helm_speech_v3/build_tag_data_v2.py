"""Build v2 mouth training data for the broadened situation tags.

Only the new social/relational/conversational tags are generated here; the fact tags (ANSWER/SAYBACK/ASK) keep their
existing rows. Every candidate pair is run through the real guard first, so the model is not trained on replies the
guard would reject.

    python build_tag_data_v2.py [--per-tag 120]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mouth_task import check  # noqa: E402
from speech_tags_v2 import TAGS, TONES  # noqa: E402

FACT_TAGS = {"ANSWER", "SAYBACK", "ASK"}          # keep the existing rows for these
OUT = HERE / "data" / "mouth_train_v2_new_tags.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-tag", type=int, default=120)
    a = ap.parse_args()
    rng = random.Random(20261025)
    fact_words = set(json.load(open(HERE / "data" / "FACT_WORDS.json", encoding="utf-8")))
    rows, stats = [], {}
    for tag, spec in TAGS.items():
        if tag in FACT_TAGS:
            continue
        triggers, replies = spec["triggers"], spec["replies"]
        kept, rejected = [], []
        for i in range(a.per_tag):
            trig = triggers[i % len(triggers)]
            rep = replies[(i * 7 + i // len(triggers)) % len(replies)]
            ok, why = check.check(tag, trig, rep, fact_words, None)
            if not ok:
                rejected.append({"trigger": trig, "reply": rep, "why": why})
                continue
            state, register = TONES[i % len(TONES)]
            kept.append({"situation": tag, "tone": [state, register], "input_text": trig,
                         "target": rep, "style": None, "source": "v2_social"})
        stats[tag] = {"kept": len(kept), "rejected": len(rejected),
                      "distinct_replies": len({r["target"] for r in kept})}
        rows.extend(kept)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    out = {"tags": len(stats), "rows": len(rows), "per_tag": stats, "file": str(OUT)}
    (HERE / "data" / "TAG_DATA_V2_STATS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"tags": len(stats), "rows": len(rows)}, indent=1))
    for t, s in stats.items():
        print(f"  {t:14s} kept={s['kept']:3d} rejected={s['rejected']:3d} distinct={s['distinct_replies']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
