# Per-kind held-back accuracy from the SAVED ablation scoring files (records only; no model, no torch).
import json, collections
from pathlib import Path
R = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001")
receipts = [("Helm 2.0-exp", "receipt_2026091%d" % s) for s in (7, 8, 9)] + [("Helm 1.0", "receipt_helm1_certified_2026091%d" % s) for s in (7, 8, 9)]
phases = ("baseline", "core_block", "round_mix", "heads", "query_and_readout")
for label, name in receipts:
    per = {}
    for ph in phases:
        d = json.loads((R / name / "checkpoints" / ("ablation_%s_scoring.json" % ph)).read_text(encoding="utf-8"))
        c = collections.defaultdict(lambda: [0, 0])
        for row in d["rows"]:
            c[row["kind"]][0] += bool(row["correct"]); c[row["kind"]][1] += 1
        per[ph] = (d["correct"], d["total"], dict(c))
    kinds = sorted(per["baseline"][2])
    print("%s %s: total baseline %d/%d | core_block reset %d | round_mix reset (no message passing) %d | heads reset %d | query_and_readout reset %d"
          % (label, name, per["baseline"][0], per["baseline"][1], per["core_block"][0], per["round_mix"][0], per["heads"][0], per["query_and_readout"][0]))
    for k in kinds:
        print("   %-15s n=%3d  base %3d  core_reset %3d  no_msg_passing %3d" % (k, per["baseline"][2][k][1], per["baseline"][2][k][0], per["core_block"][2][k][0], per["round_mix"][2][k][0]))
