# R6 meeting: are the two above-floor frozen questions (7a391350, a3e70de9) still answered
# when a component is reset to its initial weights? Reads saved ablation scoring files only.
import json, collections
from pathlib import Path
T = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001")
TARGET = ("7a391350", "a3e70de9")
runs = [("Helm 2.0", "receipt_%s" % s) for s in ("20260917", "20260918", "20260919")] + \
       [("Helm 1.0", "receipt_helm1_certified_%s" % s) for s in ("20260917", "20260918", "20260919")]
for ver, rd in runs:
    ck = T / rd / "checkpoints"
    line = []
    for comp in ("baseline", "core_block", "round_mix", "query_and_readout", "heads"):
        f = ck / ("ablation_%s_scoring.json" % comp)
        if not f.exists():
            line.append("%s:MISSING" % comp); continue
        rows = json.load(open(f, encoding="utf-8"))["rows"]
        per = collections.defaultdict(list)
        reach_ok = 0; reach_n = 0
        for r in rows:
            q = r.get("query_id", "")
            for t in TARGET:
                if t in q: per[t].append(bool(r["correct"]))
            if r["kind"] == "reach":
                reach_n += 1; reach_ok += bool(r["correct"])
        s = " ".join("%s=%d/%d" % (t, sum(per[t]), len(per[t])) for t in TARGET)
        line.append("%s[%s reach %d/%d]" % (comp, s, reach_ok, reach_n))
    print(ver, rd.split("_")[-1]); [print("   ", x) for x in line]
