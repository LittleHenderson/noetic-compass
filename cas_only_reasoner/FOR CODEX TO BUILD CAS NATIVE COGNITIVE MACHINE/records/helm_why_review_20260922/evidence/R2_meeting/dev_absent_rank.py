"""Saved dev scores only: on the 42 dev reach questions whose true answer is ABSENT, where does the ABSENT
option rank, and how far below the top option is it? Pure JSON; no model run."""
import json, sys, os
from collections import Counter
ROOT = sys.argv[1]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev_panel_rules.py"), encoding="utf-8").read().split("ans = {rid")[0]
ns = {"__name__": "lib"}; sys.argv = [sys.argv[0], ROOT]; exec(compile(src, "dp", "exec"), ns)
packets, checker = ns["packets"], ns["checker"]
base = os.path.join(ROOT, "records", "typed_pointer_001")
for rdir in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]:
    pred = json.load(open(os.path.join(base, rdir, "checkpoints", "development_p10_predictions.json"), encoding="utf-8"))["predictions"]
    ranks = Counter(); gaps = []
    for p in pred:
        if checker(packets[p["record_id"]])[0] != "ABSENT": continue
        (slot, sc), = [(k, v) for k, v in p["scores"].items() if "ABSENT" in v]
        order = sorted(sc, key=lambda k: -sc[k])
        ranks[order.index("ABSENT") + 1] += 1
        gaps.append(sc[order[0]] - sc["ABSENT"])
    gaps.sort()
    print("%s: ABSENT-truth questions %d | rank of ABSENT option (rank: count) %s | top-minus-ABSENT score gap min %.6f median %.6f max %.6f"
          % (rdir, sum(ranks.values()), dict(sorted(ranks.items())), gaps[0], gaps[len(gaps) // 2], gaps[-1]))
