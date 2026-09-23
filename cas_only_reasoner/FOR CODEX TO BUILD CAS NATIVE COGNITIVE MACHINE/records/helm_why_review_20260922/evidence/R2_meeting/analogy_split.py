"""Analogy at pass 10: split the correct answers by trained / held / excluded, and check that within one run,
each row differs from the run's modal score vector in at most ONE world alias (the focus). Pure JSON."""
import json, sys, os
from collections import Counter
ROOT = sys.argv[1]
base = os.path.join(ROOT, "records", "typed_pointer_001")
runs = [("Helm 2.0", "receipt_%s" % s) for s in ("20260917", "20260918", "20260919")] + \
       [("Helm 1.0", "receipt_helm1_certified_%s" % s) for s in ("20260917", "20260918", "20260919")]
for label, rdir in runs:
    ck = os.path.join(base, rdir, "checkpoints")
    pm = json.load(open(os.path.join(ck, "protocol_material.json"), encoding="utf-8"))
    split = {}
    for name, key in (("trained", "trained_record_ids"), ("held", "held_back_record_ids"), ("excluded", "excluded_record_ids")):
        for rid in pm[key]:
            split[rid] = name
    pred = json.load(open(os.path.join(ck, "course_p10_predictions.json"), encoding="utf-8"))["predictions"]
    scor = {r["record_id"]: r for r in json.load(open(os.path.join(ck, "course_p10_scoring.json"), encoding="utf-8"))["rows"]}
    an = [p for p in pred if p["answer"]["kind"] == "analogy"]
    vecs = []
    for p in an:
        (slot, sc), = p["scores"].items()
        vecs.append({a: v for a, v in sc.items() if a != "NO_MATCH"})
    modal = {a: Counter(v[a] for v in vecs).most_common(1)[0][0] for a in vecs[0]}
    dev_per_row = Counter(sum(1 for a in v if v[a] != modal[a]) for v in vecs)
    by_split = Counter(); tot_split = Counter(); worlds = set(); nm_admissible = 0
    for p in an:
        s = split.get(p["record_id"], "unlisted"); tot_split[s] += 1
        if scor[p["record_id"]]["correct"]:
            by_split[s] += 1
        worlds.add(p["answer"]["value"]["world_id"])
    print("%s %s: analogy records %d by split %s | correct by split %s | distinct answered world ids %d | "
          "aliases differing from the run's modal score vector, per row (count: rows) %s"
          % (label, rdir, len(an), dict(tot_split), dict(by_split), len(worlds), dict(sorted(dev_per_row.items()))))
