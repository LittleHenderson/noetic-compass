# R4 meeting: are Helm's analogy answers invariant to the focus world? JSON only, no model.
import json, collections, sys
from pathlib import Path
T = Path(sys.argv[1]) / "records/typed_pointer_001"
runs = [("helm2.0", "receipt_%s" % s) for s in ("20260917", "20260918", "20260919")] + \
       [("helm1.0", "receipt_helm1_certified_%s" % s) for s in ("20260917", "20260918", "20260919")]
for label, rd in runs:
    for phase in ("course_p00", "course_p10"):
        base = T / rd / "checkpoints"
        if not (base / ("%s_predictions.json" % phase)).is_file():
            base = T / rd / "collected/results/artifacts"
        preds = json.load(open(base / ("%s_predictions.json" % phase), encoding="utf-8"))["predictions"]
        scor = json.load(open(base / ("%s_scoring.json" % phase), encoding="utf-8"))["rows"]
        correct = {r["prediction_id"]: r["correct"] for r in scor}
        ana = [p for p in preds if p["answer"]["kind"] == "analogy"]
        vals = collections.Counter(json.dumps(p["answer"]["value"], sort_keys=True) for p in ana)
        recs = {p["record_id"] for p in ana}
        ncorr = sum(1 for p in ana if correct.get(p["prediction_id"]))
        top = vals.most_common(3)
        print("%s %s %s: analogy records %d, distinct answers %d, correct %d; top answers %s" % (
            label, rd[-8:], phase, len(ana), len(vals), ncorr, [(v[:90], c) for v, c in top]))
