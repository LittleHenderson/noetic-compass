"""mine_sdg_phrasings.py -- stream the 5,268-row SDG English corpus and count natural phrase frames.

Stdlib only. Streams line by line (never loads the corpus). For each frame it keeps the count and the first
five seed_ids where it appears, so phrasebook.json can cite the rows a phrasing was modelled on.

Usage:  python -X utf8 -B mine_sdg_phrasings.py [corpus_dir]
Writes: SDG_PHRASE_MINING.json next to this file.
"""
import hashlib
import json
import os
import re
import sys

DEFAULT_DIR = r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\path_d"
# The 5,268 rows = the big wave-3 step-2.5 file plus the two small follow-up files.
FILES = ["wave3_step2_5_english_descriptions_20260508T203848Z.jsonl",
         "wave3_step2_5_english_descriptions_20260509T002355Z.jsonl",
         "wave3_step2_5_english_descriptions_20260509T002541Z.jsonl"]

FRAMES = {
    "open_to_produce": r"^To produce\b",
    "open_to_build": r"^To build\b",
    "open_to_make": r"^To (make|create)\b",
    "combine_with": r"\bcombine\b[^.]{0,160}\bwith\b",
    "take_and_add": r"\btake\b[^.]{0,160}\band add\b",
    "blend_in": r"\bblend in\b",
    "together_these_produce": r"\btogether these (inputs )?(produce|yield|create|make)\b",
    "these_inputs_together_yield": r"\bthese inputs together yield\b",
    "together_create": r"\btogether (these )?(create|build)\b",
    "you_arrive_at": r"\byou arrive at\b",
    "fuse_into": r"\bfuse into\b",
    "leads_to": r"\bleads to\b",
    "then_leads_to": r"\bthen leads to\b",
    "side_effect_feeds_into": r"\bside effect\b",
    "plus_an_additional": r"\bplus an additional\b",
    "transforms_into": r"\btransforms into\b",
    "n_of_something": r"\b\d+(\.\d+)? of (what|something|a|the|being|who|paying)\b",
}
CATS = {"recipe", "cross_register_omega", "rpm_chain", "inversion"}


def main(corpus_dir=DEFAULT_DIR):
    rx = {k: re.compile(v, re.I) for k, v in FRAMES.items()}
    out = {k: {"pattern": FRAMES[k], "count": 0, "seed_ids": [], "example": None} for k in FRAMES}
    rows = 0
    by_cat = {}
    digests = {}
    for name in FILES:
        path = os.path.join(corpus_dir, name)
        h = hashlib.sha256()
        with open(path, "rb") as fb:
            for chunk in iter(lambda: fb.read(1 << 16), b""):
                h.update(chunk)
        digests[name] = h.hexdigest()
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                rows += 1
                cat = r.get("grammar_category")
                by_cat[cat] = by_cat.get(cat, 0) + 1
                if cat not in CATS:
                    continue
                text = r.get("english_description") or ""
                for k, p in rx.items():
                    if p.search(text):
                        o = out[k]
                        o["count"] += 1
                        if len(o["seed_ids"]) < 5:
                            o["seed_ids"].append(r["seed_id"])
                        if o["example"] is None:
                            o["example"] = {"seed_id": r["seed_id"], "text": text[:300]}
    res = {"schema": "helm.voice.sdg_mining/1", "corpus_dir": corpus_dir, "files_sha256": digests,
           "rows_streamed": rows, "rows_by_category": dict(sorted(by_cat.items())),
           "categories_mined": sorted(CATS), "frames": out}
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SDG_PHRASE_MINING.json")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("rows", rows, "->", dst)
    for k, o in out.items():
        print("  %-28s %5d  %s" % (k, o["count"], ",".join(o["seed_ids"][:2])))


if __name__ == "__main__":
    main(*sys.argv[1:])
