"""What did Helm answer on the 53 dev reach questions (truth: ABSENT 42, DIRECT 8, VIA 3), and what answer mix
did the 107 course reach records teach? Pure JSON."""
import json, sys, os
from collections import Counter
ROOT = sys.argv[1]
base = os.path.join(ROOT, "records", "typed_pointer_001")
pub = json.load(open(os.path.join(ROOT, "records/typed_course_001/checks_002/public_course.json"), encoding="utf-8"))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "reach_hops.py"), encoding="utf-8").read().split("base = os.path.join")[0]
ns = {"__name__": "lib"}; sys.argv = [sys.argv[0], ROOT]; exec(compile(src, "rh", "exec"), ns)
reg, answer = ns["reg"], ns["answer"]
pm0 = json.load(open(os.path.join(base, "receipt_20260918", "checkpoints", "protocol_material.json"), encoding="utf-8"))
tr = set(pm0["trained_record_ids"])
print("course reach answer mix, trained records:", dict(Counter(answer(reg[r])[0] for r in tr if reg[r]["query"]["kind"] == "reach")),
      "| all course reach:", dict(Counter(answer(r)[0] for r in reg.values() if r["query"]["kind"] == "reach")))
for rdir in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]:
    ck = os.path.join(base, rdir, "checkpoints")
    pred = json.load(open(os.path.join(ck, "development_p10_predictions.json"), encoding="utf-8"))["predictions"]
    mix = Counter(p["answer"]["value"].get("state") for p in pred if p["answer"]["kind"] == "reach")
    print("  %s dev reach predicted states: %s" % (rdir, dict(mix)))
