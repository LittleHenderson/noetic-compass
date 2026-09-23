"""Is Helm's analogy (world_id) head blind to the focus world? Pure JSON, no torch.
For every receipt: over all analogy prediction rows at pass 10, count distinct scores per world alias."""
import json, sys, os
from collections import defaultdict, Counter
ROOT = sys.argv[1]
base = os.path.join(ROOT, "records", "typed_pointer_001")
runs = [("Helm 2.0", "receipt_%s" % s) for s in ("20260917", "20260918", "20260919")] + \
       [("Helm 1.0", "receipt_helm1_certified_%s" % s) for s in ("20260917", "20260918", "20260919")]
for label, rdir in runs:
    ck = os.path.join(base, rdir, "checkpoints")
    for phase in ("course_p00", "course_p10"):
        pred = json.load(open(os.path.join(ck, phase + "_predictions.json"), encoding="utf-8"))["predictions"]
        scor = json.load(open(os.path.join(ck, phase + "_scoring.json"), encoding="utf-8"))["rows"]
        correct = {r["record_id"]: r["correct"] for r in scor}
        an = [p for p in pred if p["answer"]["kind"] == "analogy"]
        per_alias = defaultdict(list)
        argmax = Counter(); chosen = Counter(); nm_correct = 0; n_correct = 0
        for p in an:
            (slot, sc), = p["scores"].items()
            for a, v in sc.items():
                if a != "NO_MATCH":
                    per_alias[a].append(round(v, 5))
            chosen[p["decisions"]["selected"][slot]] += 1
            if correct[p["record_id"]]:
                n_correct += 1
                if p["answer"]["value"]["world_id"] is None:
                    nm_correct += 1
        distinct = Counter(len(set(v)) for v in per_alias.values())
        # the most common value for each alias = its score whenever it is NOT the focus (if invariant)
        modal = {a: Counter(v).most_common(1)[0] for a, v in per_alias.items()}
        rows_at_modal = Counter(c for _, c in modal.values())
        print("%s %s %s: analogy rows %d | aliases %d | distinct scores per alias across rows: %s | "
              "rows where alias takes its modal score (min, max over aliases): %d, %d | chosen symbols: %s | correct %d (NO_MATCH-correct %d)"
              % (label, rdir, phase, len(an), len(per_alias), dict(sorted(distinct.items())),
                 min(rows_at_modal), max(rows_at_modal), dict(chosen.most_common(6)), n_correct, nm_correct))
