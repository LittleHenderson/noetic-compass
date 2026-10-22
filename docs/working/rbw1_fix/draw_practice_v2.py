"""RB-W1 dish-name fix: a NEW builder practice draw (published), 0 USD, laptop, no exam file opened.

    python -X utf8 -I -B draw_practice_v2.py <RB-W1T package dir> <frames dir> <out dir>

Uses the RB-W1T package's own frame / draw / key code (exam_rbw1t, keys_rbw1t) with a PUBLISHED seed text.
Excluded by id: X-REAL's 128 used recipes (contract/EXCLUDE_XREAL_USED.json, ids only) and the old RB-W1T practice
draw (practice/PRACTICE_DRAW_RBW1T.json). The RB-W1T exam's 128 ids are NOT listed in its manifest or sealed handoff,
so they could not be excluded; the seed text is a non-numeric string unlike the exam's numeric band seed (1,950,xxx,xxx).
"""
import json
import sys
from pathlib import Path

PKG, FRAMES, OUT = (Path(x).resolve() for x in sys.argv[1:4])
sys.path.insert(0, str(PKG))
from rbw1t import common_rbw1t as C      # noqa: E402
from rbw1t import custody_rbw1t as CU    # noqa: E402
from rbw1t import exam_rbw1t as X        # noqa: E402

SEED_TEXT = "RBW1-DISHNAME-FIX-PRACTICE-V2-20261020-builder-published"


def main():
    recipes = X.load_frames(FRAMES)
    excl = CU.exclusion_ids(include_practice=True)
    exam = CU.make_exam(recipes, excl, SEED_TEXT)
    old = {it["frame_id"] for it in json.loads(CU.PRACTICE_DRAW.read_text(encoding="utf-8"))["items"]}
    xr = set(json.loads(CU.EXCLUDE_XREAL.read_text(encoding="utf-8"))["frame_ids"])
    ids = [it["frame_id"] for it in exam["items"]]
    doc = {"schema": "helm.rbw1.practice-draw-v2/1", "seed_text": SEED_TEXT, "published": True,
           "excluded_by_id": {"xreal_used": len(xr), "old_rbw1t_practice": len(old)},
           "not_excluded": "RB-W1T exam ids: not listed in MANIFEST_RBW1T.json or the sealed handoff; a v3 reseal must "
                           "exclude THIS draw's ids",
           "overlap_check": {"with_xreal_ids": len(set(ids) & xr), "with_old_practice_ids": len(set(ids) & old)},
           "counts": CU.summary_counts(exam), "frame_ids": sorted(ids), "items": exam["items"], "keys": exam["keys"]}
    sha = C.write_json(OUT / "PRACTICE_DRAW_V2.json", doc)
    inputs = {"schema": "helm.rbw1t.inputs/1", "seed_text": SEED_TEXT, "items": [X.host_view(it) for it in exam["items"]]}
    sha_in = C.write_json(OUT / "INPUTS_PRACTICE_V2.json", inputs)
    print(json.dumps({"practice_draw_sha256": sha, "inputs_sha256": sha_in, "overlap_check": doc["overlap_check"],
                      "counts": doc["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
