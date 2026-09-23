"""For each analogy row at pass 10: is the single alias whose score differs from the run's modal vector
the FOCUS world (alias = index in sorted bank world ids)? Also: is the constant answer the focus's own world?"""
import json, sys, os
from collections import Counter
ROOT = sys.argv[1]
pub = json.load(open(os.path.join(ROOT, "records/typed_course_001/checks_002/public_course.json"), encoding="utf-8"))
focus = {r["record_id"]: r["query"]["focus_world_id"] for r in pub["registry"]}
ids = sorted(w["world_id"] for w in pub["bank"]["worlds"])
alias_of = {w: "W%d" % i for i, w in enumerate(ids)}
base = os.path.join(ROOT, "records", "typed_pointer_001")
for rdir in ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")]:
    pred = json.load(open(os.path.join(base, rdir, "checkpoints", "course_p10_predictions.json"), encoding="utf-8"))["predictions"]
    an = [p for p in pred if p["answer"]["kind"] == "analogy"]
    vecs = [(p, {a: v for a, v in list(p["scores"].values())[0].items() if a != "NO_MATCH"}) for p in an]
    modal = {a: Counter(v[a] for _, v in vecs).most_common(1)[0][0] for a in vecs[0][1]}
    is_focus = Counter(); focus_lower = Counter(); answered_is_focus = 0
    for p, v in vecs:
        diff = [a for a in v if v[a] != modal[a]]
        f = alias_of[focus[p["record_id"]]]
        is_focus[diff == [f]] += 1
        focus_lower[v[f] < modal[f]] += 1
        answered_is_focus += p["answer"]["value"]["world_id"] == focus[p["record_id"]]
    print("%s: rows %d | the only differing alias IS the focus world: %s | focus score lower than its non-focus score: %s | answer == focus world: %d | distinct focus worlds %d"
          % (rdir, len(vecs), dict(is_focus), dict(focus_lower), answered_is_focus, len({focus[p['record_id']] for p, _ in vecs})))
