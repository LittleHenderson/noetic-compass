# R4 meeting: Helm analogy answers vs focus worlds. JSON only, no model.
import json, collections, sys
from pathlib import Path
ROOT = Path(sys.argv[1]); T = ROOT / "records/typed_pointer_001"
reg = json.load(open(ROOT / "records/typed_course_001/checks_002/public_course.json", encoding="utf-8"))["registry"]
focus = {r["query"]["query_id"]: r["query"]["focus_world_id"] for r in reg}
kind = {r["query"]["query_id"]: r["query"]["kind"] for r in reg}
aq = [q for q in focus if kind[q] == "analogy"]
print("analogy queries in registry:", len(aq), "distinct focus worlds:", len({focus[q] for q in aq}))
runs = [("helm2.0", "receipt_%s" % s) for s in ("20260917", "20260918", "20260919")] + \
       [("helm1.0", "receipt_helm1_certified_%s" % s) for s in ("20260917", "20260918", "20260919")]
for label, rd in runs:
    for phase in ("course_p00", "course_p10"):
        base = T / rd / "checkpoints"
        preds = json.load(open(base / ("%s_predictions.json" % phase), encoding="utf-8"))["predictions"]
        ana = [p for p in preds if p["answer"]["kind"] == "analogy"]
        vals = collections.Counter(p["answer"]["value"]["world_id"] for p in ana)
        modal = vals.most_common(1)[0][0]
        minority = [p for p in ana if p["answer"]["value"]["world_id"] != modal]
        eq_focus = sum(1 for p in minority if p["answer"]["value"]["world_id"] == focus[p["answer"]["query_id"]])
        focus_of_modal = sum(1 for p in ana if focus[p["answer"]["query_id"]] == modal)
        print("%s %s %s: distinct answers %d; records whose focus IS the modal answer %d; minority %d, of which answer==own focus %d" % (
            label, rd[-8:], phase, len(vals), focus_of_modal, len(minority), eq_focus))
