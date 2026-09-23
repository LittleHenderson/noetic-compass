# R6 meeting: which reach answer does each saved ablation emit on the 26 held-back reach records?
# Pure JSON over saved prediction + scoring files. No model.
import json, collections
from pathlib import Path
T = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001")
runs = [("2.0", "receipt_%s" % s) for s in ("20260917", "20260918", "20260919")] + \
       [("1.0", "receipt_helm1_certified_%s" % s) for s in ("20260917", "20260918", "20260919")]
for ver, rd in runs:
    ck = T / rd / "checkpoints"
    for comp in ("baseline", "round_mix", "heads"):
        preds = json.load(open(ck / ("ablation_%s_predictions.json" % comp), encoding="utf-8"))["predictions"]
        rows = json.load(open(ck / ("ablation_%s_scoring.json" % comp), encoding="utf-8"))["rows"]
        ok = {r["prediction_id"]: bool(r["correct"]) for r in rows}
        c = collections.Counter(); cc = collections.Counter()
        for p in preds:
            if p["answer"]["kind"] != "reach": continue
            sel = list(p["decisions"]["selected"].values())[0]
            c[sel] += 1
            if ok.get(p["prediction_id"]): cc[sel] += 1
        print(ver, rd[-8:], comp.ljust(9), "emitted", dict(sorted(c.items())), "| correct among them", dict(sorted(cc.items())))
