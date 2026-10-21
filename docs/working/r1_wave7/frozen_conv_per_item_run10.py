"""Builder tool (NOT sealed): the FROZEN dialogue scorer's own per-item verdicts (wave 6's `score_conv` through the sealed v8
package, `common_w7.setup(helm=False)`) for run10 (v8 cut, reader v7.1), run9 (v7 cut) and run8 (v6 cut): which items are
WRONG / RIGHT / UNDETERMINED in each, the items that moved, and WRONG per dialogue family. Practice data only.

    python -X utf8 -B -I frozen_conv_per_item_run10.py <sealed v8 extract pkg> <run10 dir> <run9 dir> <run8 dir> <practice inputs dir> <out json>
"""
import json
import sys
from pathlib import Path

pkg, run10, run9, run8, prac, out = [Path(a).resolve() for a in sys.argv[1:7]]
sys.path.insert(0, str(pkg))
from r1w7 import common_w7 as C  # noqa: E402

ns = C.setup(helm=False)
keys = json.loads((prac / "exam" / "KEYS_CONV_X7.json").read_text(encoding="utf-8"))["keys"]
fam = {k["id"]: k["family"] for k in keys}
res = {"schema": "helm.r1w7.frozen-conv-per-item/2", "units": {}}
for name in ("W7_X7_CONV_CHAT_ON", "W7_X7_CONV_LOOP_ON", "W7_X7_NOISE_CHAT_ON", "W7_X7_CONV_CHAT_OFF", "W7_X7_CONV_CHAT_ON_REPLAY",
             "W7_X7_CONV_CHAT_DIAG", "W7_X7_NOISE_CHAT_OFF"):
    row = {}
    for tag, d in (("run10", run10), ("run9", run9), ("run8", run8)):
        doc = json.loads((d / "units" / f"{name}.json").read_text(encoding="utf-8"))
        s = ns.SC6.score_conv(ns, keys, doc)
        row[tag] = {"totals": s["totals"], "per_item": {p["id"]: p["score"] for p in s["per_item"]}}
    moved = {i: {"run8": row["run8"]["per_item"].get(i), "run9": row["run9"]["per_item"].get(i), "run10": v, "family": fam[i]}
             for i, v in row["run10"]["per_item"].items() if row["run9"]["per_item"].get(i) != v}
    wrong10 = sorted(i for i, v in row["run10"]["per_item"].items() if v == "WRONG")
    by_fam = {}
    for i, v in row["run10"]["per_item"].items():
        f = by_fam.setdefault(fam[i], {"items": 0, "RIGHT": 0, "WRONG": 0, "UNDETERMINED": 0})
        f["items"] += 1
        f[v] += 1
    res["units"][name] = {"run10_totals": row["run10"]["totals"], "run9_totals": row["run9"]["totals"], "run8_totals": row["run8"]["totals"],
                          "run10_wrong_items": [(i, fam[i], row["run9"]["per_item"].get(i), row["run8"]["per_item"].get(i)) for i in wrong10],
                          "run10_by_family": by_fam,
                          "run10_wrong_per_family": {f: v["WRONG"] for f, v in sorted(by_fam.items())},
                          "moved_items_run9_to_run10": moved,
                          "moved_counts_run9_to_run10": {k: sum(1 for m in moved.values() if f"{m['run9']}->{m['run10']}" == k)
                                                         for k in sorted({f"{m['run9']}->{m['run10']}" for m in moved.values()})}}
out.write_bytes((json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({n: {k: v[k] for k in ("run10_totals", "run9_totals", "run8_totals", "run10_wrong_items", "run10_wrong_per_family",
                                        "moved_items_run9_to_run10", "moved_counts_run9_to_run10")}
                  for n, v in res["units"].items()}, indent=1))
